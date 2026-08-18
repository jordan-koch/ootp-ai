// Regression guard — acceptance-panel Verify-phase batching (cap + dedupe + honest degradation)
// ===========================================================================
// Phase 2 used to spawn ONE agent per blocker/major finding — ~65% of the panel's agents and all
// of its variance, each re-paying the full grounding preamble to adjudicate a single finding. It
// now DEDUPES the findings, groups them by location, and packs them into at most VERIFY_CAP batch
// agents (+ the standalone ledger verifier, which stays outside the cap).
//
// The savings are worthless if the batching quietly loses findings, so this guard pins the five
// properties that make it safe to trade agents for batches:
//
//   1. CAP + DEDUPE + COVERAGE — N findings raised across the 6 finding-emitting lenses of this
//      run's 7-lens roster (the 7th, `acceptance`, answers a different schema and emits none)
//      collapse to <= cap batch agents, the
//      cross-lens duplicates merge (carrying BOTH raising reviewers), same-location findings land
//      in the SAME batch, and EVERY surviving finding still gets its own verdict. Reviewer ids
//      collide across lenses on purpose (every lens emits 'f1') — the panel's own vid stamping is
//      what keeps verdicts from being cross-assigned, and each verdict is checked against its vid.
//   2. DEAD BATCH — a batch agent that dies takes its whole bucket down, so those findings must
//      read 'unverified' and degraded_lenses must NAME the batch AND how many findings it lost.
//      Findings in the surviving batches must still come back verified.
//   3. RUBBER-STAMP — a batch that stamps every row with one blob of evidence is the batching-
//      specific degeneration (adjudicating the bucket as a set instead of per finding). It must be
//      caught by the stub guard, retried once, and then counted as a FAILED lens — not accepted.
//   4. verifyCap — the cap is overridable per run via args.
//   5. FIXTURE/ROSTER AGREEMENT — every lens this file's fixture is keyed by must be a lens the panel
//      actually requests. An unrequested key contributes nothing (reviewFor resolves it to []), so its
//      findings vanish before dedupe and every count below reads as a defect in the code under test.
//      This guard shipped red from day one for exactly that reason: two fixture keys named a sibling
//      repo's specialists. Checked first, and it exits before the counting assertions can cascade.
//
// Exits non-zero if any scenario fails.
//
// RUN: node .claude/skills/implement-plan/tests/verify_batching_guard.mjs
// ===========================================================================
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const HERE = dirname(fileURLToPath(import.meta.url))
const PANEL = join(HERE, '..', 'acceptance_panel.js')
const SRC = readFileSync(PANEL, 'utf8').replace(/^export\s+const\s+meta/m, 'const meta')

// ---- the synthetic finding set -------------------------------------------------
// Two deliberate cross-lens DUPLICATE pairs (same location, near-identical titles) and two
// deliberate same-file-different-bug pairs (same location, unrelated titles) — the dedupe must
// merge the former and keep the latter apart, while the bucketer sends both to one verifier.
const FINDINGS_BY_LENS = {
  fidelity: [
    { loc: 'src/ootp_ai/land/writer.py:42', title: 'landed payload is overwritten instead of written once' },
    { loc: 'transform/models/silver/fact_player_game.sql:88', title: 'declared grain has no uniqueness test in schema.yml' },
    { loc: 'src/ootp_ai/parse/reader.py:120', title: 'plan phase 3 was never implemented at all' },
  ],
  correctness: [
    { loc: 'src/ootp_ai/land/writer.py:42', title: 'landed payload is overwritten, not written once' },  // dup of fidelity[0]
    { loc: 'transform/models/silver/dim_player.sql:17', title: 'team affiliation resolves as-of today, not as-of the game date' },
  ],
  edgecases: [
    { loc: 'transform/models/silver/dim_player.sql:31', title: 'a mid-season trade produces two open SCD2 intervals' },   // same file, different bug
    { loc: 'tests/test_extract_client.py:9', title: 'the test hits the live API instead of a committed fixture' },
  ],
  warehouse: [
    { loc: 'transform/models/silver/fact_player_game.sql:88', title: 'declared grain has no uniqueness test' },           // dup of fidelity[1]
    { loc: 'transform/models/bronze/schema.yml:12', title: 'the new source is unregistered in sources.yml' },
  ],
  parser: [
    { loc: 'src/ootp_ai/land/writer.py:60', title: 'no checkpoint, so a failed backfill restarts from zero' },       // same file, different bug
  ],
  'skill-quality': [
    { loc: '.claude/skills/foo/SKILL.md:3', title: 'the description drifted from what the skill does' },
  ],
}
const RAW_TOTAL = Object.values(FINDINGS_BY_LENS).reduce((n, a) => n + a.length, 0)   // 11
const DEDUPED_TOTAL = RAW_TOTAL - 2                                                    // 2 duplicate pairs merge

function validAcceptanceReview() {
  return {
    lens_summary: 'Acceptance auditor: enumerated every criterion and verified each by execution.',
    criteria_results: [
      { id: 'c1', criterion: 'the tool emits a plan for a two-generation chain', source: 'scope', verdict: 'met', evidence: 'ran the script -> emitted the expected plan', how_checked: 'execution' },
    ],
    findings: [],
  }
}
function reviewFor(lensKey) {
  const spec = FINDINGS_BY_LENS[lensKey] || []
  return {
    lens_summary: `Reviewer ${lensKey}: read the diff in full and checked each claim by running it.`,
    // NOTE: every lens numbers its findings from f1 — reviewer ids are only unique WITHIN a lens.
    findings: spec.map((s, i) => ({
      id: `f${i + 1}`,
      title: s.title,
      severity: i === 0 ? 'blocker' : 'major',
      confidence: 'high',
      category: 'correctness',
      location: s.loc,
      problem: `a concrete failure scenario at ${s.loc} on a real input`,
      proposed_fix: 'apply the concrete fix described above',
    })),
  }
}
function validLedgerVerify() {
  return {
    lens_summary: 'Independent verifier: rebuilt the acceptance ledger from scratch by execution.',
    criteria_results: [
      { id: 'v1', criterion: 'the tool emits a plan for a two-generation chain', source: 'scope', verdict: 'met', evidence: 'independently ran the script -> same plan', how_checked: 'execution' },
    ],
  }
}
function validMerged() {
  return {
    summary: 'A reconciled acceptance report synthesized from the reviews and the verify verdicts.',
    verdict: 'fix',
    verdict_rationale: 'confirmed blockers remain to resolve before go',
    acceptance_ledger: [{ id: 'c1', criterion: 'the tool emits a plan for a two-generation chain', source: 'scope', verdict: 'met', evidence: 'ran the script -> expected plan', reconciliation: 'auditor and verifier agree' }],
    confirmed_findings: [],
    gated_decisions: [],
  }
}
function validMetaFindings() {
  return { lens_summary: 'Meta-audit: the synthesis dropped no confirmed signal; the verdict matches the evidence.', findings: [] }
}

// Parse the vids the panel put in a batch prompt, so the stub answers the ids it was actually given.
function vidsIn(prompt) {
  return [...String(prompt || '').matchAll(/--- FINDING (\S+) ---/g)].map(m => m[1])
}
function validVerifyBatch(prompt) {
  const ids = vidsIn(prompt)
  return {
    verdicts: ids.map((id, i) => ({
      id,
      verdict: 'confirmed',
      evidence: `reproduced the failure for ${id} by running the triggering input`,
      ran: `node some/script.mjs --case ${id}-${i + 1}`,
    })),
  }
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

function makeArgs(extra) {
  return {
    planPath: 'requests/feature-requests/synthetic-batching/IMPLEMENTATION_PLAN.md',
    scopePath: 'requests/feature-requests/synthetic-batching/PROJECT_SCOPE.md',
    slug: 'synthetic-batching',
    touchedAreas: ['transform', 'src', 'skills'],   // -> warehouse + parser + skill-quality specialists
    ...extra,
  }
}
async function runPanel(agent, panelArgs) {
  const runner = new Function(
    'agent', 'parallel', 'pipeline', 'phase', 'log', 'args', 'budget',
    `return (async () => { ${SRC}\n })()`,
  )
  return runner(agent, parallel, pipeline, noop, noop, panelArgs, budget)
}

// A default agent that succeeds everywhere, recording every call. `override` gets first refusal.
function makeAgent(calls, override) {
  return async (prompt, opts = {}) => {
    const label = opts.label || ''
    calls.push({ label, prompt })
    if (override) {
      const o = await override(label, prompt, calls)
      if (o !== undefined) return o
    }
    if (label === 'review:acceptance') return validAcceptanceReview()
    if (label.startsWith('review:')) return reviewFor(label.slice('review:'.length))
    if (label === 'verify:ledger') return validLedgerVerify()
    if (label.startsWith('verify:b')) return validVerifyBatch(prompt)
    if (label === 'synthesize') return validMerged()
    if (label === 'meta') return validMetaFindings()
    return `Free-text output for ${label}.`
  }
}

const fails = []
const CAP = 4   // the panel's default

// One RED path, called from the fixture check below and from the tail of the file. Two places that
// format failures would drift, and this file is here because comment/fixture drift went unnoticed.
function reportRedAndExit() {
  console.log('\nRED: acceptance verify-batching guard FAILED:')
  for (const f of fails) console.log(`  - ${f}`)
  process.exit(1)
}

// ── Scenario 1: CAP + DEDUPE + COVERAGE ─────────────────────────────────────────
{
  const calls = []
  const r = await runPanel(makeAgent(calls), makeArgs())
  const s = (r && r.stats) || {}
  // FIXTURE/ROSTER AGREEMENT — checked FIRST, because an orphaned lens invalidates every count below.
  // `reviewFor` resolves an unknown key to [] (it must: the panel legitimately requests lenses this
  // fixture does not stock). So a fixture key the panel never asks for contributes nothing and is
  // invisible — which is exactly how this guard shipped red for its whole life, reporting the missing
  // findings as a dedupe miscount in acceptance_panel.js, which turned out to be correct all along.
  // Note this cannot live inside `reviewFor`: acceptance_panel.js's safeAgent catches every throw from
  // the stub and degrades the lens, so the guard would report the wrong thing. It belongs here.
  const requestedLenses = new Set(
    calls.filter(c => c.label.startsWith('review:')).map(c => c.label.slice('review:'.length)),
  )
  if (requestedLenses.size === 0) {
    fails.push('fixture: the panel requested NO review lenses — the harness is broken, not the fixture')
  } else {
    for (const key of Object.keys(FINDINGS_BY_LENS)) {
      if (!requestedLenses.has(key)) {
        fails.push(
          `fixture: FINDINGS_BY_LENS has an orphaned lens '${key}' that the panel never requests — ` +
          `its findings are silently dropped. The panel asked for: ${[...requestedLenses].sort().join(', ')}`,
        )
      }
    }
  }
  // Bail before the counting assertions: they would all cascade off the dropped findings and bury
  // the one line that explains them.
  if (fails.length) reportRedAndExit()

  const batchCalls = calls.filter(c => c.label.startsWith('verify:b'))
  const batchLabels = [...new Set(batchCalls.map(c => c.label))]
  const vf = (r && r.verified_findings) || []

  if (batchLabels.length > CAP) fails.push(`cap: ${batchLabels.length} verify batches spawned, cap is ${CAP}`)
  if (s.verify_batches !== batchLabels.length) fails.push(`cap: stats.verify_batches=${s.verify_batches} disagrees with the ${batchLabels.length} batch agents actually spawned`)
  if (s.verify_cap !== CAP) fails.push(`cap: stats.verify_cap=${s.verify_cap}, expected ${CAP}`)
  if (s.verifiers_total !== batchLabels.length + 1) fails.push(`cap: verifiers_total=${s.verifiers_total}, expected ${batchLabels.length} batches + 1 ledger`)
  if (s.verifiers_ok !== s.verifiers_total) fails.push(`cap: verifiers_ok=${s.verifiers_ok} of ${s.verifiers_total} on an all-green run`)

  if (s.findings_blocker_major_raw !== RAW_TOTAL) fails.push(`dedupe: raw=${s.findings_blocker_major_raw}, expected ${RAW_TOTAL}`)
  if (s.findings_blocker_major_deduped !== DEDUPED_TOTAL) fails.push(`dedupe: deduped=${s.findings_blocker_major_deduped}, expected ${DEDUPED_TOTAL} (the 2 cross-lens duplicate pairs must merge)`)
  const merged = vf.filter(f => (f.merged_from || []).length > 1)
  if (merged.length !== 2) fails.push(`dedupe: expected 2 merged findings, got ${merged.length}`)
  if (!merged.every(f => (f.reviewers || []).length > 1)) fails.push('dedupe: a merged finding lost one of its raising reviewers')
  if (!merged.every(f => f.severity === 'blocker')) fails.push('dedupe: a merge did not keep the WORST severity of the pair')
  // the two same-file-different-bug pairs must NOT have been merged
  const writerFindings = vf.filter(f => String(f.location).startsWith('src/ootp_ai/land/writer.py'))
  const dimPlayerFindings = vf.filter(f => String(f.location).startsWith('transform/models/silver/dim_player.sql'))
  if (writerFindings.length !== 2) fails.push(`dedupe: over-merged land/writer.py — 2 distinct bugs expected, got ${writerFindings.length}`)
  if (dimPlayerFindings.length !== 2) fails.push(`dedupe: over-merged dim_player.sql — 2 distinct bugs expected, got ${dimPlayerFindings.length}`)

  // COVERAGE: every surviving finding adjudicated, and each verdict matched to ITS OWN vid
  if (vf.length !== DEDUPED_TOTAL) fails.push(`coverage: verified_findings=${vf.length}, expected ${DEDUPED_TOTAL}`)
  if (s.findings_unverified !== 0) fails.push(`coverage: ${s.findings_unverified} finding(s) left unverified on an all-green run`)
  const unadjudicated = vf.filter(f => f.verdict === 'unverified')
  if (unadjudicated.length) fails.push(`coverage: ${unadjudicated.length} finding(s) came back 'unverified' on an all-green run`)
  const misrouted = vf.filter(f => !String(f.verify_evidence).includes(f.vid))
  if (misrouted.length) fails.push(`coverage: ${misrouted.length} finding(s) got a verdict belonging to a different finding (colliding reviewer ids not isolated by the vid stamp)`)

  // LOCATION GROUPING: same normalized location -> same batch prompt
  function batchOf(vid) { return batchCalls.find(c => vidsIn(c.prompt).includes(vid)) }
  for (const [file, group] of [['src/ootp_ai/land/writer.py', writerFindings], ['transform/models/silver/dim_player.sql', dimPlayerFindings]]) {
    const labels = [...new Set(group.map(f => (batchOf(f.vid) || {}).label))]
    if (labels.length !== 1) fails.push(`grouping: ${file}'s findings were split across ${labels.length} batches (${labels.join(', ')}) — they must share a verifier`)
  }
  console.log(`[cap+dedupe] raw=${s.findings_blocker_major_raw} deduped=${s.findings_blocker_major_deduped} batches=${batchLabels.length}/${CAP} verifiers=${s.verifiers_ok}/${s.verifiers_total} unverified=${s.findings_unverified}`)
}

// ── Scenario 2: DEAD BATCH degrades honestly ────────────────────────────────────
{
  const calls = []
  const agent = makeAgent(calls, async (label) => {
    if (label === 'verify:b1') throw new Error('agent({schema}): StructuredOutput retry cap (5) exceeded — 5 failed calls with no valid output')
    return undefined
  })
  const r = await runPanel(agent, makeArgs())
  const s = (r && r.stats) || {}
  const degraded = (r && r.degraded_lenses) || []
  const vf = (r && r.verified_findings) || []
  const note = degraded.find(d => String(d).startsWith('verify:b1'))

  if (!note) fails.push(`dead-batch: degraded_lenses does not name the dead batch (got ${JSON.stringify(degraded)})`)
  if (note && !/\d+ finding/.test(note)) fails.push(`dead-batch: the degraded note must say how many findings it lost (got "${note}")`)
  if (s.findings_unverified < 1) fails.push('dead-batch: a dead batch left every finding reading as verified')
  if (s.verifiers_ok !== s.verifiers_total - 1) fails.push(`dead-batch: verifiers_ok=${s.verifiers_ok}/${s.verifiers_total}, expected exactly one failed agent`)
  const unver = vf.filter(f => f.verdict === 'unverified')
  if (unver.length !== s.findings_unverified) fails.push(`dead-batch: stats.findings_unverified=${s.findings_unverified} disagrees with ${unver.length} unverified findings`)
  if (unver.length === vf.length) fails.push('dead-batch: the surviving batches lost their verdicts too — one dead agent must not sink the phase')
  if (unver.some(f => f.verify_evidence)) fails.push('dead-batch: an unverified finding carries verify evidence it never earned')
  console.log(`[dead-batch] verifiers=${s.verifiers_ok}/${s.verifiers_total} unverified=${s.findings_unverified}/${vf.length} note="${note}"`)
}

// ── Scenario 3: RUBBER-STAMP batch is rejected, not accepted ────────────────────
{
  const calls = []
  const agent = makeAgent(calls, async (label, prompt) => {
    if (label !== 'verify:b1') return undefined
    const ids = vidsIn(prompt)
    if (ids.length < 2) return undefined            // needs a multi-finding bucket to be meaningful
    return { verdicts: ids.map(id => ({ id, verdict: 'confirmed', evidence: 'looks right', ran: 'read the diff' })) }
  })
  const r = await runPanel(agent, makeArgs())
  const s = (r && r.stats) || {}
  const degraded = (r && r.degraded_lenses) || []
  const b1Calls = calls.filter(c => c.label === 'verify:b1').length

  if (b1Calls !== 2) fails.push(`rubber-stamp: expected the stub guard to retry the batch once (2 calls), got ${b1Calls}`)
  if (!degraded.some(d => String(d).startsWith('verify:b1'))) fails.push(`rubber-stamp: a one-blob-of-evidence batch was ACCEPTED (degraded=${JSON.stringify(degraded)})`)
  if (s.findings_unverified < 1) fails.push('rubber-stamp: the rejected batch\'s findings still read as verified')
  console.log(`[rubberstmp] b1Calls=${b1Calls} verifiers=${s.verifiers_ok}/${s.verifiers_total} unverified=${s.findings_unverified}`)
}

// ── Scenario 4: args.verifyCap overrides the default ────────────────────────────
{
  const calls = []
  const r = await runPanel(makeAgent(calls), makeArgs({ verifyCap: 2 }))
  const s = (r && r.stats) || {}
  const batchLabels = [...new Set(calls.filter(c => c.label.startsWith('verify:b')).map(c => c.label))]
  if (s.verify_cap !== 2) fails.push(`verifyCap: stats.verify_cap=${s.verify_cap}, expected 2`)
  if (batchLabels.length > 2) fails.push(`verifyCap: ${batchLabels.length} batches spawned under a cap of 2`)
  if (s.findings_unverified !== 0) fails.push(`verifyCap: a tighter cap must not drop findings (${s.findings_unverified} unverified)`)
  if (s.findings_blocker_major_deduped !== DEDUPED_TOTAL) fails.push('verifyCap: a tighter cap changed how many findings survived dedupe')
  console.log(`[verifyCap ] cap=${s.verify_cap} batches=${batchLabels.length} unverified=${s.findings_unverified}/${s.findings_blocker_major_deduped}`)
}

if (fails.length) {
  reportRedAndExit()
} else {
  console.log('\nGREEN: verify batching stays under the cap, merges only true duplicates, groups by location, adjudicates every finding against its own id, and degrades honestly when a batch dies or rubber-stamps.')
  process.exit(0)
}
