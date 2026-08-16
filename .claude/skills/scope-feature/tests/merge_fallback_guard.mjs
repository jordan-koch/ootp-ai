// Regression guard — scope-panel merge fallback (recovery + dormant-on-success)
// ===========================================================================
// Mirror of the plan-panel guard, against the REAL scope_panel.js under stubbed
// Workflow globals, run twice:
//
//   1. RECOVERY  — the forced 'merge' agent THROWS. The panel must recover: return a
//      scope with fit_verdict present + a populated core (tiered_scope.core) and
//      acceptance_criteria, and flag degraded_lenses with 'merge:fallback'.
//
//   2. DORMANT-ON-SUCCESS — the 'merge' agent returns a valid merged object. The panel
//      must take the unchanged path: return the real (non-[DEGRADED]) summary, NOT list
//      'merge:fallback' in degraded_lenses, and NEVER call the fallback agent
//      (mergeFallbackCalls === 0).
//
// Exits non-zero if either scenario fails.
//
// RUN: node .claude/skills/scope-feature/tests/merge_fallback_guard.mjs
// ===========================================================================
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const PANEL = join(HERE, '..', 'scope_panel.js')
const SRC = readFileSync(PANEL, 'utf8').replace(/^export\s+const\s+meta/m, 'const meta')

// ---- synthetic, non-stub stand-ins the panel's own guards accept ----------------
function validScoper(key) {
  return {
    fit: { verdict: key === 'minimalist' ? 'reshape' : 'clean', rationale: `Scoper ${key}: this fits the repo's existing skill/dataset patterns with a clear integration seam.` },
    goals: [`goal from ${key}`],
    non_goals: [`non-goal from ${key}`],
    acceptance_criteria: [`acceptance criterion from ${key} — objectively checkable`],
    core_scope: [`core scope item from ${key}`],
    enhancements: [{ title: `enhancement from ${key}`, rationale: 'complements the core', cost: 'cheap' }],
    risks: [`risk from ${key}`],
    open_questions: [],
  }
}
function validMerged() {
  return {
    summary: 'A coherent PROJECT_SCOPE synthesized from the three scoper proposals.',
    fit_verdict: { verdict: 'clean', rationale: 'fits the repo cleanly with a clear seam' },
    problem_restatement: 'restate the problem faithfully',
    goals: ['g1'], non_goals: ['ng1'],
    acceptance_criteria: ['ac1 — objectively checkable'],
    tiered_scope: { core: ['core1'], cheap_folds: ['fold1'], gated: ['gated1'] },
    above_and_beyond: [{ title: 'enh1', tier: 'cheap_fold', rationale: 'cheap win' }],
    risks: ['r1'],
    grounding_pointers: ['datasets/manifest.json'],
    convergence_map: [{ theme: 't', scopers: ['fit'], why_high_signal: 'two agreed' }],
    gated_decisions: [{ question: 'q', recommendation: 'r' }],
  }
}
function validFindings(key) {
  return { lens_summary: `Lens ${key}: attacked the scope; no blockers found.`, findings: [] }
}

const panelArgs = {
  requestPath: 'requests/feature-requests/synthetic-small/FEATURE_REQUEST.md',
  featureDir: 'requests/feature-requests/synthetic-small/',
  slug: 'synthetic-small',
}

async function parallel(thunks) {
  return Promise.all(thunks.map(t => Promise.resolve().then(t).catch(() => null)))
}
async function pipeline(items, ...stages) {
  return Promise.all(items.map(async (it, i) => {
    let v = it
    for (const s of stages) { try { v = await s(v, it, i) } catch { return null } }
    return v
  }))
}
const noop = () => {}
const budget = { total: null, spent: () => 0, remaining: () => Infinity }

async function runPanel(agent) {
  const runner = new Function(
    'agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget',
    `return (async () => { ${SRC}\n })()`,
  )
  return runner(agent, parallel, pipeline, noop, noop, panelArgs, budget)
}

const fails = []

// ── Scenario 1: RECOVERY (merge throws) ─────────────────────────────────────────
{
  let fallbackCalls = 0
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'merge') throw new Error('agent({schema}): StructuredOutput retry cap (5) exceeded — 5 failed calls with no valid output')
    if (label === 'merge:fallback') { fallbackCalls++; return `Free-text recovery scope for ${label}: a coherent prose PROJECT_SCOPE assembled from the proposals.` }
    if (label.startsWith('scope:')) return validScoper(label)
    if (label.startsWith('adv:')) return validFindings(label)
    if (opts.schema) return validFindings(label)
    return `Free-text output for ${label}.`
  }
  const r = await runPanel(agent)
  const degraded = (r && r.degraded_lenses) || []
  const fit = r && r.fit_verdict
  const core = r && r.tiered_scope && Array.isArray(r.tiered_scope.core) ? r.tiered_scope.core.length : 0
  const ac = r && Array.isArray(r.acceptance_criteria) ? r.acceptance_criteria.length : 0
  if (!fit || !fit.verdict) fails.push('recovery: fit_verdict missing/incomplete')
  if (fit && fit.verdict === 'clean') fails.push("recovery: fit_verdict must never be 'clean' on a degraded union")
  if (core < 1) fails.push(`recovery: tiered_scope.core empty (got ${core})`)
  if (ac < 1) fails.push(`recovery: acceptance_criteria empty (got ${ac})`)
  if (!degraded.includes('merge:fallback')) fails.push(`recovery: degraded_lenses missing 'merge:fallback' (got ${JSON.stringify(degraded)})`)
  if (fallbackCalls < 1) fails.push(`recovery: expected the free-text fallback agent to be called, calls=${fallbackCalls}`)
  console.log(`[recovery] fit=${fit && fit.verdict} core=${core} ac=${ac} degraded=${JSON.stringify(degraded)} fallbackCalls=${fallbackCalls}`)
}

// ── Scenario 2: DORMANT-ON-SUCCESS (merge succeeds) ─────────────────────────────
{
  let fallbackCalls = 0
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'merge') return validMerged()
    if (label === 'merge:fallback') { fallbackCalls++; return 'this should never be called on the happy path' }
    if (label.startsWith('scope:')) return validScoper(label)
    if (label.startsWith('adv:')) return validFindings(label)
    if (opts.schema) return validFindings(label)
    return `Free-text output for ${label}.`
  }
  const r = await runPanel(agent)
  const degraded = (r && r.degraded_lenses) || []
  const summary = r && r.summary
  if (fallbackCalls !== 0) fails.push(`dormant: fallback agent wrongly fired on a successful merge (calls=${fallbackCalls})`)
  if (degraded.includes('merge:fallback')) fails.push(`dormant: degraded_lenses wrongly includes 'merge:fallback' (got ${JSON.stringify(degraded)})`)
  if (typeof summary === 'string' && summary.startsWith('[DEGRADED]')) fails.push('dormant: returned the [DEGRADED] marker summary instead of the real merged summary')
  if (!(r && r.fit_verdict && r.fit_verdict.verdict === 'clean')) fails.push('dormant: expected the real merged fit_verdict (clean)')
  console.log(`[dormant ] fit=${r && r.fit_verdict && r.fit_verdict.verdict} degraded=${JSON.stringify(degraded)} fallbackCalls=${fallbackCalls}`)
}

// ── Scenario 3: DOUBLE-FAILURE (merge throws AND free-text fallback throws -> prose=null) ──
// The deterministic floor must carry the whole scope with NO help from either StructuredOutput call.
{
  let fallbackCalls = 0
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'merge') throw new Error('agent({schema}): StructuredOutput retry cap (5) exceeded — 5 failed calls with no valid output')
    if (label === 'merge:fallback') { fallbackCalls++; throw new Error('the free-text fallback ALSO exhausted its retry cap') }
    if (label.startsWith('scope:')) return validScoper(label)
    if (label.startsWith('adv:')) return validFindings(label)
    if (opts.schema) return validFindings(label)
    return `Free-text output for ${label}.`
  }
  const r = await runPanel(agent)
  const degraded = (r && r.degraded_lenses) || []
  const fit = r && r.fit_verdict
  const core = r && r.tiered_scope && Array.isArray(r.tiered_scope.core) ? r.tiered_scope.core.length : 0
  const ac = r && Array.isArray(r.acceptance_criteria) ? r.acceptance_criteria.length : 0
  const summary = r && r.summary
  const summaryDeg = typeof summary === 'string' && summary.startsWith('[DEGRADED]')
  if (!fit || !fit.verdict) fails.push('double-failure: fit_verdict missing/incomplete')
  if (fit && fit.verdict === 'clean') fails.push("double-failure: fit_verdict must never be 'clean' on a degraded union")
  if (core < 1) fails.push(`double-failure: tiered_scope.core empty (got ${core})`)
  if (ac < 1) fails.push(`double-failure: acceptance_criteria empty (got ${ac})`)
  if (!summaryDeg) fails.push(`double-failure: expected the [DEGRADED] summary marker when prose=null (got ${JSON.stringify(summary && summary.slice(0, 30))})`)
  if (!degraded.includes('merge:fallback')) fails.push(`double-failure: degraded_lenses missing 'merge:fallback' (got ${JSON.stringify(degraded)})`)
  if (fallbackCalls < 1) fails.push(`double-failure: expected the free-text fallback agent to be attempted, calls=${fallbackCalls}`)
  console.log(`[2x-fail ] fit=${fit && fit.verdict} core=${core} ac=${ac} summaryDeg=${summaryDeg} degraded=${JSON.stringify(degraded)} fallbackCalls=${fallbackCalls}`)
}

if (fails.length) {
  console.log('\nRED: scope merge-fallback guard FAILED:')
  for (const f of fails) console.log(`  - ${f}`)
  process.exit(1)
} else {
  console.log('\nGREEN: recovery yields a usable degraded scope AND the happy path is inert (fallback never fires).')
  process.exit(0)
}
