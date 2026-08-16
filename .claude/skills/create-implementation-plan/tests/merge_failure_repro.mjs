// Red reproduction — plan-panel-merge-structuredoutput-crash
// ===========================================================================
// WHAT THIS PROVES (deterministic, LLM-free):
//   The stage-3 planning panel funnels ALL planner work through ONE forced
//   StructuredOutput "merge" agent. When that single call fails (the observed
//   "StructuredOutput retry cap (5) exceeded" THROW, which safeAgent catches ->
//   null), plan_panel.js:180-181 DISCARDS the 3 already-successful planner
//   proposals and returns a planless { error, raw_proposals } — and because the
//   adversaries + meta-audit are gated behind the merge, they never run. The run
//   yields nothing usable even though 3 good proposals are in hand.
//
//   This harness runs the REAL plan_panel.js with stubbed Workflow globals: the
//   3 planners succeed; the forced-schema merge throws the exact field error.
//   It then asserts the DESIRED post-fix contract:
//
//     When the planners succeed but the structured merge fails, the panel must
//     still return a USABLE plan (plan_draft with >=1 phase), not a bare error.
//
//   RED today  : merge failure -> { error, raw_proposals }, no plan_draft  -> exit 1
//   GREEN later: a fallback (free-text merge and/or direct assembly from the
//                proposals) yields plan_draft.phases -> exit 0
//
// WHAT THIS DOES NOT PROVE: *why* StructuredOutput exhausts its retry cap on a
//   large merge (a probabilistic harness behavior, documented in the memory note
//   `review_harness_reliability`). We inject the failure rather than provoke it —
//   the defect we own and can regression-guard is the no-fallback discard, not the
//   harness's StructuredOutput reliability. The trigger was observed in the field
//   on a live full-panel run in the project this pipeline was ported from; this is
//   the deterministic guard for the blast radius.
//
// RUN: node .claude/skills/create-implementation-plan/tests/merge_failure_repro.mjs
// ===========================================================================
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const PANEL = join(HERE, '..', 'plan_panel.js')

// ---- synthetic, non-stub stand-ins the panel's own guards will accept ----------
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
  // Only reached if a FIX routes a structured fallback under a non-"merge" label.
  return {
    summary: 'A coherent cold-handoff plan synthesized from the three planner proposals.',
    onboarding: { what_it_is: 'a recovery merge', files_to_read: [{ path: 'lib/paths.py', why: 'resolve-by-name' }] },
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

// ---- stubbed Workflow globals --------------------------------------------------
const MERGE_ERROR = 'agent({schema}): StructuredOutput retry cap (5) exceeded — 5 failed calls with no valid output'
let mergeThrows = 0
async function agent(prompt, opts = {}) {
  const label = opts.label || ''
  // The forced-StructuredOutput merge is the fragile chokepoint — simulate the
  // observed retry-cap exhaustion as a THROW (safeAgent is expected to catch it).
  if (label === 'merge') { mergeThrows++; throw new Error(MERGE_ERROR) }
  if (label.startsWith('plan:')) return validProposal(label)
  if (label.startsWith('adv:') || label.startsWith('meta')) return validFindings(label)
  // Any other lens (e.g. a future merge fallback) succeeds so a correct fix can reach GREEN.
  if (opts.schema && opts.schema.properties && opts.schema.properties.phases) return validMerged()
  if (opts.schema) return validFindings(label)
  return `Free-text recovery output for ${label}: a coherent synthesized plan draft.`
}
// parallel(): per the Workflow contract a thrown thunk resolves to null, never rejects.
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
const phase = () => {}
const log = () => {}
const budget = { total: null, spent: () => 0, remaining: () => Infinity }
const panelArgs = {
  scopePath: 'requests/bugfix-requests/synthetic-small/ROOT_CAUSE_ANALYSIS.md',
  requestPath: 'requests/bugfix-requests/synthetic-small/BUGFIX_REQUEST.md',
  slug: 'synthetic-small',
}

// ---- load + run the REAL panel body under the stubs ----------------------------
const src = readFileSync(PANEL, 'utf8').replace(/^export\s+const\s+meta/m, 'const meta')
const runner = new Function(
  'agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget',
  `return (async () => { ${src}\n })()`,
)
const result = await runner(agent, parallel, pipeline, phase, log, panelArgs, budget)

// ---- assert the post-fix contract ----------------------------------------------
const recovered = !!(result && result.plan_draft && Array.isArray(result.plan_draft.phases) && result.plan_draft.phases.length > 0)

console.log(`merge agent failures injected: ${mergeThrows}`)
if (recovered) {
  console.log(`GREEN: planners succeeded + merge failed, yet the panel still produced a usable plan (${result.plan_draft.phases.length} phase(s)).`)
  process.exit(0)
} else {
  console.log('RED: the merge failed and the panel discarded all 3 successful planners — no usable plan produced.')
  console.log(`  result.error      = ${JSON.stringify(result && result.error)}`)
  console.log(`  result.plan_draft = ${result && result.plan_draft ? 'present' : 'MISSING'}`)
  console.log(`  raw_proposals kept = ${result && Array.isArray(result.raw_proposals) ? result.raw_proposals.length : 0} (proof the planner work survived but was thrown away)`)
  process.exit(1)
}
