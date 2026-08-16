// Regression guard — plan-panel merge fallback (recovery + dormant-on-success)
// ===========================================================================
// Locks BOTH halves of the fix, LLM-free, by running the REAL plan_panel.js under
// stubbed Workflow globals twice:
//
//   1. RECOVERY  — the forced 'merge' agent THROWS (the observed StructuredOutput
//      retry-cap exhaustion). The panel must recover: return a plan_draft with >=1
//      phase AND flag degraded_lenses with 'merge:fallback'.
//
//   2. DORMANT-ON-SUCCESS — the 'merge' agent returns a valid merged object. The
//      panel must take the unchanged happy path: return the real (non-[DEGRADED])
//      summary, NOT list 'merge:fallback' in degraded_lenses, and — the strong
//      assertion — NEVER call the fallback agent (mergeFallbackCalls === 0). This is
//      the proof the change is inert on the happy path.
//
// Exits non-zero if either scenario fails.
//
// RUN: node .claude/skills/create-implementation-plan/tests/merge_fallback_guard.mjs
// ===========================================================================
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const PANEL = join(HERE, '..', 'plan_panel.js')
const SRC = readFileSync(PANEL, 'utf8').replace(/^export\s+const\s+meta/m, 'const meta')

// ---- synthetic, non-stub stand-ins the panel's own guards accept ----------------
function validProposal(key) {
  return {
    onboarding_files: [{ path: 'lib/paths.py', why: 'resolve datasets by name' }],
    architecture_notes: `Planner ${key}: the touched area is a single module with a clear seam at the merge stage; the change hooks in where the result is returned.`,
    phases: [{ name: 'Phase 1', goal: 'do the thing', steps: ['step a', 'step b'], acceptance: ['selftest green'], commit_note: 'commit phase 1' }],
    testing: 'run the tool selftest',
    risks: ['none material'],
    files_to_touch: [{ path: 'some/file.js', change: 'edit' }],
    code_references: [{ ref: 'some/file.js:1', claim: 'entry point' }],
    open_questions: [],
  }
}
function validMerged() {
  return {
    summary: 'A coherent cold-handoff plan synthesized from the three planner proposals.',
    onboarding: { what_it_is: 'a real merge', files_to_read: [{ path: 'lib/paths.py', why: 'resolve-by-name' }] },
    architecture_map: 'current structure + where the change hooks in',
    phases: [{ name: 'Phase 1', goal: 'do the thing', steps: ['step a'], acceptance: ['selftest green'], commit_note: 'commit' }],
    testing: 'selftest', decisions: [{ decision: 'd', rationale: 'r' }], risks: ['none'],
    files_to_touch: [{ path: 'some/file.js', change: 'edit' }],
    conventions: ['never commit directly'],
    code_references: [{ ref: 'some/file.js:1', claim: 'entry point' }],
    convergence_map: [{ theme: 't', planners: ['code-grounded'], why_high_signal: 'two agreed' }],
    gated_decisions: [{ question: 'q', recommendation: 'r' }],
  }
}
function validFindings(key) {
  return { lens_summary: `Lens ${key}: verified the cited references; no blockers found.`, findings: [] }
}

const panelArgs = {
  scopePath: 'requests/bugfix-requests/synthetic-small/ROOT_CAUSE_ANALYSIS.md',
  requestPath: 'requests/bugfix-requests/synthetic-small/BUGFIX_REQUEST.md',
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
    if (label === 'merge:fallback') { fallbackCalls++; return `Free-text recovery synthesis for ${label}: a coherent prose plan draft assembled from the proposals.` }
    if (label.startsWith('plan:')) return validProposal(label)
    if (label.startsWith('adv:') || label.startsWith('meta')) return validFindings(label)
    if (opts.schema) return validFindings(label)
    return `Free-text output for ${label}.`
  }
  const r = await runPanel(agent)
  const phases = r && r.plan_draft && Array.isArray(r.plan_draft.phases) ? r.plan_draft.phases.length : 0
  const degraded = (r && r.degraded_lenses) || []
  if (phases < 1) fails.push(`recovery: expected >=1 plan_draft phase, got ${phases}`)
  if (!degraded.includes('merge:fallback')) fails.push(`recovery: degraded_lenses missing 'merge:fallback' (got ${JSON.stringify(degraded)})`)
  if (fallbackCalls < 1) fails.push(`recovery: expected the free-text fallback agent to be called, calls=${fallbackCalls}`)
  console.log(`[recovery] phases=${phases} degraded=${JSON.stringify(degraded)} fallbackCalls=${fallbackCalls}`)
}

// ── Scenario 2: DORMANT-ON-SUCCESS (merge succeeds) ─────────────────────────────
{
  let fallbackCalls = 0
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'merge') return validMerged()
    if (label === 'merge:fallback') { fallbackCalls++; return 'this should never be called on the happy path' }
    if (label.startsWith('plan:')) return validProposal(label)
    if (label.startsWith('adv:') || label.startsWith('meta')) return validFindings(label)
    if (opts.schema) return validFindings(label)
    return `Free-text output for ${label}.`
  }
  const r = await runPanel(agent)
  const degraded = (r && r.degraded_lenses) || []
  const summary = r && r.summary
  if (fallbackCalls !== 0) fails.push(`dormant: fallback agent wrongly fired on a successful merge (calls=${fallbackCalls})`)
  if (degraded.includes('merge:fallback')) fails.push(`dormant: degraded_lenses wrongly includes 'merge:fallback' (got ${JSON.stringify(degraded)})`)
  if (typeof summary === 'string' && summary.startsWith('[DEGRADED]')) fails.push(`dormant: returned the [DEGRADED] marker summary instead of the real merged summary`)
  if (!(r && r.plan_draft && (r.plan_draft.phases || []).length > 0)) fails.push('dormant: expected a normal plan_draft with phases')
  console.log(`[dormant ] phases=${r && r.plan_draft ? (r.plan_draft.phases || []).length : 0} degraded=${JSON.stringify(degraded)} fallbackCalls=${fallbackCalls}`)
}

// ── Scenario 3: DOUBLE-FAILURE (merge throws AND free-text fallback throws -> prose=null) ──
// The most-degraded path the fix must still survive: the deterministic floor carries the
// whole result with NO help from either StructuredOutput call. Robustness must never depend
// on the free-text fallback succeeding.
{
  let fallbackCalls = 0
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'merge') throw new Error('agent({schema}): StructuredOutput retry cap (5) exceeded — 5 failed calls with no valid output')
    if (label === 'merge:fallback') { fallbackCalls++; throw new Error('the free-text fallback ALSO exhausted its retry cap') }
    if (label.startsWith('plan:')) return validProposal(label)
    if (label.startsWith('adv:') || label.startsWith('meta')) return validFindings(label)
    if (opts.schema) return validFindings(label)
    return `Free-text output for ${label}.`
  }
  const r = await runPanel(agent)
  const phases = r && r.plan_draft && Array.isArray(r.plan_draft.phases) ? r.plan_draft.phases.length : 0
  const degraded = (r && r.degraded_lenses) || []
  const summary = r && r.summary
  const summaryDeg = typeof summary === 'string' && summary.startsWith('[DEGRADED]')
  if (phases < 1) fails.push(`double-failure: expected >=1 plan_draft phase from the deterministic floor, got ${phases}`)
  if (!degraded.includes('merge:fallback')) fails.push(`double-failure: degraded_lenses missing 'merge:fallback' (got ${JSON.stringify(degraded)})`)
  if (!summaryDeg) fails.push(`double-failure: expected the [DEGRADED] summary marker when prose=null (got ${JSON.stringify(summary && summary.slice(0, 30))})`)
  if (fallbackCalls < 1) fails.push(`double-failure: expected the free-text fallback agent to be attempted, calls=${fallbackCalls}`)
  console.log(`[2x-fail ] phases=${phases} degraded=${JSON.stringify(degraded)} summaryDeg=${summaryDeg} fallbackCalls=${fallbackCalls}`)
}

if (fails.length) {
  console.log('\nRED: merge-fallback guard FAILED:')
  for (const f of fails) console.log(`  - ${f}`)
  process.exit(1)
} else {
  console.log('\nGREEN: recovery yields a usable degraded plan AND the happy path is inert (fallback never fires).')
  process.exit(0)
}
