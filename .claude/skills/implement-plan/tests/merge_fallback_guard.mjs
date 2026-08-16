// Regression guard — acceptance-panel synthesis fallback (recovery + dormant-on-success)
// ===========================================================================
// Stage 4 is structurally different from stages 2/3: the synthesis throw is only reachable
// AFTER the reviewers AND the Verify phase populate. So this harness stubs the full upstream:
//   - review:acceptance -> a valid ACCEPTANCE ledger (so auditorLedger fills)
//   - review:<other>    -> valid findings (correctness raises one major, so a verify:b thunk runs)
//   - verify:ledger     -> a valid independent ledger with >=1 row (so verifierLedger is
//                          non-empty — else the assembled ledger is empty and GREEN would be
//                          unreachable for the WRONG reason)
//   - verify:b*         -> a valid batch of per-finding verdicts
//   - ONLY 'synthesize' throws (recovery) / returns a valid report (dormant)
//
//   1. RECOVERY  — synthesis throws. The panel must recover with a SHAPE-APPROPRIATE report:
//      a non-empty acceptance_ledger + a verdict, degraded_lenses includes 'synthesize:fallback'
//      AND 'meta:skipped-degraded' (the meta-audit is skipped on the degraded path), meta_ok=0.
//
//   2. DORMANT-ON-SUCCESS — synthesis succeeds: no 'synthesize:fallback' in degraded_lenses,
//      the fallback agent never fires, and the meta-audit RUNS (meta_ok = 1).
//
// Exits non-zero if either scenario fails.
//
// RUN: node .claude/skills/implement-plan/tests/merge_fallback_guard.mjs
// ===========================================================================
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const PANEL = join(HERE, '..', 'acceptance_panel.js')
const SRC = readFileSync(PANEL, 'utf8').replace(/^export\s+const\s+meta/m, 'const meta')

// ---- synthetic, non-stub stand-ins the panel's own guards accept ----------------
function validAcceptanceReview() {
  return {
    lens_summary: 'Acceptance auditor: enumerated every criterion and verified each by execution.',
    criteria_results: [
      { id: 'c1', criterion: 'the committed red repro goes green', source: 'plan-phase-1', verdict: 'met', evidence: 'ran node repro.mjs -> exit 0', how_checked: 'execution: ran the repro' },
    ],
    findings: [],
  }
}
function validReview(key, withMajor) {
  return {
    lens_summary: `Reviewer ${key}: read the diff in full and checked the behavior by running it.`,
    findings: withMajor
      ? [{ id: 'f1', title: 'a real major issue worth verifying', severity: 'major', confidence: 'high', category: 'correctness', location: 'some/file.js:10', problem: 'concrete failure scenario on a real input', proposed_fix: 'apply the concrete fix' }]
      : [],
  }
}
// Verify is BATCHED: one agent adjudicates every finding in its bucket and returns a verdict per
// FINDING ID. The ids are stamped by the panel (V1, V2, ...) and appear in the prompt as
// '--- FINDING <id> ---', so the stub reads them back out rather than guessing.
function validVerifyBatch(prompt) {
  const ids = [...String(prompt || '').matchAll(/--- FINDING (\S+) ---/g)].map(m => m[1])
  return {
    verdicts: (ids.length ? ids : ['V1']).map((id, i) => ({
      id,
      verdict: 'confirmed',
      evidence: `reproduced the failure for ${id} by running the script with its triggering input`,
      ran: `node some/script.mjs --case ${i + 1}`,
    })),
  }
}
function validLedgerVerify() {
  return {
    lens_summary: 'Independent verifier: rebuilt the acceptance ledger from scratch by execution.',
    criteria_results: [
      { id: 'v1', criterion: 'the committed red repro goes green', source: 'plan-phase-1', verdict: 'met', evidence: 'independently ran node repro.mjs -> exit 0', how_checked: 'execution' },
    ],
  }
}
function validMerged() {
  return {
    summary: 'A reconciled acceptance report synthesized from the reviews and the verify verdicts.',
    verdict: 'fix',
    verdict_rationale: 'one confirmed major remains to resolve before go',
    acceptance_ledger: [{ id: 'c1', criterion: 'the committed red repro goes green', source: 'plan-phase-1', verdict: 'met', evidence: 'ran node repro.mjs -> exit 0', reconciliation: 'auditor and verifier agree' }],
    confirmed_findings: [{ id: 'f1', title: 'a real major issue worth verifying', severity: 'major', confidence: 'high', category: 'correctness', location: 'some/file.js:10', problem: 'x', proposed_fix: 'y' }],
    gated_decisions: [{ question: 'q', recommendation: 'r' }],
  }
}
function validMetaFindings() {
  return { lens_summary: 'Meta-audit: the synthesis dropped no confirmed signal; verdict matches the evidence.', findings: [] }
}

const panelArgs = {
  planPath: 'requests/bugfix-requests/synthetic-small/IMPLEMENTATION_PLAN.md',
  scopePath: 'requests/bugfix-requests/synthetic-small/ROOT_CAUSE_ANALYSIS.md',
  slug: 'synthetic-small',
  touchedAreas: [],   // 4 core reviewers only — deterministic roster
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

// Shared upstream routing for everything BEFORE synthesis (identical in both scenarios).
function routeUpstream(label, prompt) {
  if (label === 'review:acceptance') return validAcceptanceReview()
  if (label === 'review:correctness') return validReview(label, true)   // raises one major -> verify:b1
  if (label.startsWith('review:')) return validReview(label, false)
  if (label === 'verify:ledger') return validLedgerVerify()
  if (label.startsWith('verify:b')) return validVerifyBatch(prompt)
  if (label === 'meta') return validMetaFindings()
  return undefined
}

const fails = []

// ── Scenario 1: RECOVERY (synthesis throws) ─────────────────────────────────────
{
  let fallbackCalls = 0
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'synthesize') throw new Error('agent({schema}): StructuredOutput retry cap (5) exceeded — 5 failed calls with no valid output')
    if (label === 'synthesize:fallback') { fallbackCalls++; return `Free-text recovery synthesis for ${label}: a reconciled prose acceptance report.` }
    const up = routeUpstream(label, prompt)
    if (up !== undefined) return up
    if (opts.schema) return validReview(label, false)
    return `Free-text output for ${label}.`
  }
  const r = await runPanel(agent)
  const degraded = (r && r.degraded_lenses) || []
  const ledger = r && Array.isArray(r.acceptance_ledger) ? r.acceptance_ledger.length : 0
  const verdict = r && r.verdict
  const metaOk = r && r.stats ? r.stats.meta_ok : undefined
  if (ledger < 1) fails.push(`recovery: acceptance_ledger empty (got ${ledger})`)
  if (!verdict) fails.push('recovery: verdict missing')
  if (verdict === 'go') fails.push("recovery: verdict must never be 'go' on a degraded synthesis")
  if (!degraded.includes('synthesize:fallback')) fails.push(`recovery: degraded_lenses missing 'synthesize:fallback' (got ${JSON.stringify(degraded)})`)
  if (!degraded.includes('meta:skipped-degraded')) fails.push(`recovery: degraded_lenses missing 'meta:skipped-degraded' (got ${JSON.stringify(degraded)})`)
  if (metaOk !== 0) fails.push(`recovery: meta_ok should be 0 (meta skipped), got ${metaOk}`)
  if (fallbackCalls < 1) fails.push(`recovery: expected the free-text fallback agent to be called, calls=${fallbackCalls}`)
  console.log(`[recovery] ledger=${ledger} verdict=${verdict} meta_ok=${metaOk} degraded=${JSON.stringify(degraded)} fallbackCalls=${fallbackCalls}`)
}

// ── Scenario 2: DORMANT-ON-SUCCESS (synthesis succeeds) ─────────────────────────
{
  let fallbackCalls = 0
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'synthesize') return validMerged()
    if (label === 'synthesize:fallback') { fallbackCalls++; return 'this should never be called on the happy path' }
    const up = routeUpstream(label, prompt)
    if (up !== undefined) return up
    if (opts.schema) return validReview(label, false)
    return `Free-text output for ${label}.`
  }
  const r = await runPanel(agent)
  const degraded = (r && r.degraded_lenses) || []
  const metaOk = r && r.stats ? r.stats.meta_ok : undefined
  if (fallbackCalls !== 0) fails.push(`dormant: fallback agent wrongly fired on a successful synthesis (calls=${fallbackCalls})`)
  if (degraded.includes('synthesize:fallback')) fails.push(`dormant: degraded_lenses wrongly includes 'synthesize:fallback' (got ${JSON.stringify(degraded)})`)
  if (degraded.includes('meta:skipped-degraded')) fails.push(`dormant: meta-audit wrongly skipped on the happy path (got ${JSON.stringify(degraded)})`)
  if (metaOk !== 1) fails.push(`dormant: meta-audit should run (meta_ok=1), got ${metaOk}`)
  if (!(r && r.verdict)) fails.push('dormant: verdict missing')
  console.log(`[dormant ] verdict=${r && r.verdict} meta_ok=${metaOk} degraded=${JSON.stringify(degraded)} fallbackCalls=${fallbackCalls}`)
}

// ── Scenario 3: DOUBLE-FAILURE (synthesis throws AND free-text fallback throws -> prose=null) ──
// The deterministic floor must carry the whole acceptance report (ledger verbatim from the
// surviving cross-check, verdict forced to fix, meta skipped) with NO help from either
// StructuredOutput call.
{
  let fallbackCalls = 0
  const agent = async (prompt, opts = {}) => {
    const label = opts.label || ''
    if (label === 'synthesize') throw new Error('agent({schema}): StructuredOutput retry cap (5) exceeded — 5 failed calls with no valid output')
    if (label === 'synthesize:fallback') { fallbackCalls++; throw new Error('the free-text fallback ALSO exhausted its retry cap') }
    const up = routeUpstream(label, prompt)
    if (up !== undefined) return up
    if (opts.schema) return validReview(label, false)
    return `Free-text output for ${label}.`
  }
  const r = await runPanel(agent)
  const degraded = (r && r.degraded_lenses) || []
  const ledger = r && Array.isArray(r.acceptance_ledger) ? r.acceptance_ledger.length : 0
  const verdict = r && r.verdict
  const metaOk = r && r.stats ? r.stats.meta_ok : undefined
  const summary = r && r.summary
  const summaryDeg = typeof summary === 'string' && summary.startsWith('[DEGRADED]')
  if (ledger < 1) fails.push(`double-failure: acceptance_ledger empty (got ${ledger})`)
  if (verdict !== 'fix') fails.push(`double-failure: verdict must be forced to 'fix' on the degraded floor (got ${verdict})`)
  if (!degraded.includes('synthesize:fallback')) fails.push(`double-failure: degraded_lenses missing 'synthesize:fallback' (got ${JSON.stringify(degraded)})`)
  if (!degraded.includes('meta:skipped-degraded')) fails.push(`double-failure: degraded_lenses missing 'meta:skipped-degraded' (got ${JSON.stringify(degraded)})`)
  if (metaOk !== 0) fails.push(`double-failure: meta_ok should be 0 (meta skipped), got ${metaOk}`)
  if (!summaryDeg) fails.push(`double-failure: expected the [DEGRADED] summary marker when prose=null (got ${JSON.stringify(summary && summary.slice(0, 30))})`)
  if (fallbackCalls < 1) fails.push(`double-failure: expected the free-text fallback agent to be attempted, calls=${fallbackCalls}`)
  console.log(`[2x-fail ] ledger=${ledger} verdict=${verdict} meta_ok=${metaOk} summaryDeg=${summaryDeg} degraded=${JSON.stringify(degraded)} fallbackCalls=${fallbackCalls}`)
}

if (fails.length) {
  console.log('\nRED: acceptance synthesis-fallback guard FAILED:')
  for (const f of fails) console.log(`  - ${f}`)
  process.exit(1)
} else {
  console.log('\nGREEN: recovery yields a usable degraded acceptance report (meta skipped) AND the happy path is inert (fallback never fires, meta runs).')
  process.exit(0)
}
