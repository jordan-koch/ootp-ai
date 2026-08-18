export const meta = {
  name: 'plan-feature-panel',
  description: 'Adversarial planning panel over a PROJECT_SCOPE: 3 planners -> merge -> 2 code-grounded adversaries + 1 meta-audit',
  phases: [
    { title: 'Plan', detail: '3 divergent planners draft a cold-handoff implementation plan from the decided scope' },
    { title: 'Converge', detail: 'merge into one plan draft + convergence map + gated decisions' },
    { title: 'Adversarial', detail: '2 code-grounded adversaries verify every cited reference + 1 meta-audit checks the merge' },
  ],
}

// args (from the create-implementation-plan skill): { scopePath, requestPath, featureDir, slug }
// The harness may deliver args as a JSON string rather than an object — coerce both.
let A = {}
if (args && typeof args === 'object') { A = args }
else if (typeof args === 'string') { try { A = JSON.parse(args) } catch (e) { A = {} } }
const SCOPE = A.scopePath || 'requests/feature-requests/<slug>/PROJECT_SCOPE.md'
const REQ = A.requestPath || 'requests/feature-requests/<slug>/FEATURE_REQUEST.md'
const SLUG = A.slug || '(unknown)'

// Fail loud instead of planning a random scope: if no real path arrived, the planners
// would wander requests/feature-requests/ and silently plan whichever scope they stumble on.
if (SCOPE.includes('<slug>')) {
  return { error: `no scopePath reached the panel (args arrived as ${typeof args}) — aborting to avoid planning the wrong feature`, argsType: typeof args }
}

// ── Stub-degeneration guard ───────────────────────────────────────────────────
// StructuredOutput review/merge agents intermittently degenerate into placeholder
// stubs (e.g. summary "test", single-char findings) that are still truthy and would
// otherwise count as a successful lens — silently gutting the adversarial premise.
// Detect a stub, retry the agent ONCE with reinforcement, and if it still stubs,
// report the lens as NOT ok so stats stay honest (the skill's Step-3 health check
// trusts planners_ok / adversaries_ok / meta_audit_ok).
const ANTISTUB_RETRY = 'RETRY — your previous response was rejected as a placeholder/stub (empty or near-empty summary/findings). The run is wasted unless you return REAL, specific, grounded content NOW: a substantive multi-sentence lens_summary and real findings (or, if genuinely none, say so concretely with evidence). Do NOT return "test" or single-letter values.'
const STUB_WORDS = new Set(['test', 'probe', 'stub', 'tbd', 'n/a', 'na', 'none', 'placeholder', 'todo', 'lorem', 'example', 'xxx', 'foo', 'bar'])
function looksStub(s) {
  if (s === null || s === undefined) return true
  if (typeof s !== 'string') return false
  const t = s.trim().toLowerCase()
  return t.length < 12 || STUB_WORDS.has(t)
}
function stubFinding(f) {
  return !f || (looksStub(f.title) && looksStub(f.problem) && looksStub(f.proposed_fix))
}
// A findings-style review (adversary OR meta-audit) is a stub when its summary is
// empty/placeholder AND it has either no findings or only placeholder findings (a real
// clean review still explains itself, so this won't false-positive a genuine zero pass).
function reviewIsStub(r) {
  if (!r) return true
  const f = r.findings || []
  return looksStub(r.lens_summary) && (f.length === 0 || f.every(stubFinding))
}
function plannerIsStub(p) {
  if (!p) return true
  return looksStub(p.architecture_notes) && (p.phases || []).length === 0
}
function mergeIsStub(m) {
  if (!m || !m.phases) return true
  return (m.phases || []).length === 0 || looksStub(m.summary)
}
// Deterministic, LLM-free assembly of a usable (degraded) plan_draft from the in-hand
// planner proposals — the recovery FLOOR when the forced-schema merge fails. It carries
// EVERY key the final return reads. Phase names are disambiguated by planner so the union
// isn't three "Phase 1"s (the un-gated adversaries still run on this draft). The >=1-phase
// guarantee rests on PLANNER_SCHEMA listing `phases` in required (below) AND plannerIsStub
// dropping any empty-phases proposal — so every okProposal carries >=1 phase; the
// RECOVERY PLACEHOLDER is a defensive backstop only.
function assemblePlanDraft(proposals, prose) {
  const dedupeBy = (rows, key) => {
    const seen = new Set(), out = []
    for (const r of (rows || [])) { const k = r && r[key]; if (k && seen.has(k)) continue; if (k) seen.add(k); out.push(r) }
    return out
  }
  const phases = proposals.flatMap(p => (p.phases || []).map(ph => ({ ...ph, name: `[${p.planner}] ${ph.name}` })))
  const code_references = dedupeBy(proposals.flatMap(p => p.code_references || []), 'ref')
  const files_to_touch = dedupeBy(proposals.flatMap(p => p.files_to_touch || []), 'path')
  const files_to_read = dedupeBy(proposals.flatMap(p => p.onboarding_files || []), 'path')
  const risks = [...new Set(proposals.flatMap(p => p.risks || []))]
  const testing = proposals.map(p => p.testing).filter(Boolean).join('\n\n')
  const DEG = '[DEGRADED] deterministic union of the surviving planner proposals — the structured merge failed, so this is a de-duplicated assembly, NOT a synthesis. Spot-check it and consider re-running the merge on a smaller input.'
  if (!phases.length) {
    phases.push({
      name: 'RECOVERY PLACEHOLDER — reconstruct from raw_proposals',
      goal: 'The structured merge failed and no planner phases survived the assembly; rebuild the phased plan by hand from raw_proposals.',
      steps: ['Read raw_proposals in this panel output', 'Hand-merge their phases into one ordered, independently-verifiable sequence'],
      acceptance: ['A human has reconstructed the phased plan from raw_proposals'],
      commit_note: 'n/a — recovery placeholder',
    })
  }
  return {
    summary: prose || DEG,
    onboarding: { what_it_is: prose || DEG, files_to_read },
    architecture_map: prose || DEG,
    phases,
    testing: testing || DEG,
    decisions: [],
    risks,
    files_to_touch,
    conventions: [],
    code_references,
    convergence_map: [],
    gated_decisions: [],
  }
}
// agent() can also HARD-fail: the harness can exhaust its StructuredOutput retry cap
// and THROW (not just return a stub). A throw from a direct-await lens (the merge, not
// inside parallel()) escapes and kills the whole panel — so swallow it here and treat the
// lens as failed/degraded. (Backported from implement-plan/acceptance_panel.js.)
async function safeAgent(prompt, opts) {
  try { return await agent(prompt, opts) }
  catch (e) {
    const msg = e && e.message ? String(e.message).slice(0, 100) : 'error'
    log(`  ${opts.label}: agent threw (${msg}) — treating as a failed/degraded lens`)
    return null
  }
}
// Run an agent; if the result looks like a degenerate stub, retry ONCE with
// reinforcement. Returns { result, ok, attempts } — result is nulled if still a stub.
async function runChecked(prompt, opts, isStub) {
  let result = await safeAgent(prompt, opts)
  let attempts = 1
  if (result && isStub(result)) {
    log(`  ${opts.label}: stub/degenerate output — retrying once`)
    result = await safeAgent(`${prompt}\n\n${ANTISTUB_RETRY}`, opts)
    attempts = 2
  }
  const ok = !!result && !isStub(result)
  return { result: ok ? result : null, ok, attempts }
}

const ANTISTUB = 'Your StructuredOutput MUST contain your real, grounded analysis — NEVER a placeholder/stub value (e.g. "test", "probe", single-letter fields). A stub output fails the run and wastes it; if you are unsure, still write your real best-effort content.'
const READONLY = "YOU ARE READ-ONLY: read/grep the repo freely to ground your work, but modify NO file and run NO git command that changes the working tree (no checkout/reset/restore/clean/stash/commit). If a change is needed, DESCRIBE it — don't make it."

const SHARED = `You are turning a DECIDED upstream artifact into an IMPLEMENTATION PLAN a COLD agent can execute without the author present — for an AI front office for Out of the Park Baseball 25: a parser reads the game's proprietary save binaries READ-ONLY, lands them in a MySQL warehouse as per-sim-date snapshots, and specialist advisors recommend moves that a human GM executes. Python (src/ootp_ai) + a dbt medallion. The system NEVER writes to the game. Working directory = repo root.

THE DECIDED UPSTREAM ARTIFACT TO PLAN FROM: ${SCOPE}   (slug: ${SLUG})
ITS ORIGINATING INTAKE DOC (context only): ${REQ}

The upstream artifact is one of TWO shapes — ground against whichever THIS one actually is:
- a PROJECT_SCOPE (feature track, under requests/feature-requests/): carries a Fit Verdict, Goals/Non-Goals, numbered Acceptance Criteria, and an "Affected Area & Pointers" section.
- a ROOT_CAUSE_ANALYSIS (bugfix track, under requests/bugfix-requests/): carries a verdict, file:line evidence of the cause, a pointer to a red (failing) reproduction, and a tiered fix posture. Its acceptance contract is "the red repro goes GREEN + a regression test is left behind + nothing else regresses." It has NO Fit Verdict and NO "Affected Area & Pointers" section — do not look for them.

READ THE UPSTREAM ARTIFACT IN FULL FIRST. It is DECIDED — CONSUME it; do NOT re-open or re-litigate it (a scope's fit/goals/non-goals/acceptance, or an RCA's verdict/cause — that was the prior stage). Then ground in the repo before drafting:
- the artifact's own pointers — a scope's "Affected Area & Pointers", or an RCA's evidence file:line + committed-repro path — FOLLOW them (read the named files/lines).
- the pipeline contract README (requests/feature-requests/README.md, which requests/bugfix-requests/README.md mirrors); an IMPLEMENTATION_PLAN.md is the stage-3 deliverable on either track.
- the plan template's section MENU in the stage-3 SKILL.md. Include a section only when THIS change needs it — a change touching no data omits the data-contracts section; anything landing a new source must carry it — not a fixed cast.
- CLAUDE.md — the conventions the PLAN must BAKE IN for the cold implementer: the game is READ-ONLY (ADR 0001 — no code path writes a save, a roster import file, or automates the game UI; a Challenge Mode save carries an integrity hash one write destroys irreversibly); the parser walks records SEQUENTIALLY and NEVER seeks to a fixed offset (records carry variable-length regions, so a fixed-offset read passes on day-0 data and silently corrupts everything after); ground truth is players.csv, NEVER an in-game screenshot (displayed ratings are scale-converted and possibly scout-filtered, so matching one to a byte identifies the wrong field with no error raised); a field mapping with no validating test is 'unconfirmed' and must say so; no OOTP game data may be tracked in git (ADR 0006 — it is Out of the Park Developments' IP); paths resolve from .env and datasets resolve BY NAME via datasets/manifest.json; static reference vs snapshot facts split by 'does it change when the league is simulated?' (ADR 0005); commits go through /commit only (never ad hoc, never merge/amend; the PR stays the user's); subagents get read-only git.
- docs/data-access.md — what the save files actually provide and the known gotchas. Every claim in it carries a PER-CLAIM epistemic label (measured / verified / inferred / assumed / unconfirmed), so read the label, not just the claim; a plan that depends on an unconfirmed or assumed one must include a phase that VERIFIES it before the phases that build on it.

GROUND EVERY CLAIM in concrete repo artifacts — cite REAL files / line numbers / function names that you have actually read. Do NOT invent a path or a line number: a cold implementer trusts them literally, so a wrong citation is worse than none. The plan PRESCRIBES a per-phase cadence where each phase ends at a /commit-gated checkpoint, on a green local run (uv run pytest, uv run ruff check, uv run mypy).

${READONLY}

${ANTISTUB}`

// Free-text (no-schema) recovery mandate. Used ONLY when the forced-StructuredOutput
// merge fails: free-text is the mode that stays reliable where forced StructuredOutput
// degenerates (see memory `review_harness_reliability`). It only ENRICHES the
// deterministic assembly below — robustness never depends on this second call.
const MERGE_FREETEXT_MANDATE = 'The structured merge just failed. As a best-effort recovery, synthesize the planner proposals below into a PROSE cold-handoff implementation plan: an architecture map, an ordered sequence of phases (each with goal / steps / its own acceptance / a commit note), a testing+regression-safety section, and the risks. Write PLAIN TEXT only — NO JSON, NO schema. Be substantive and ground every claim in the proposals.'

// ---------- Phase 1: planners ----------
const PLANNERS = [
  { key: 'code-grounded', mandate: `PLANNER 1 — CODE-GROUNDED CORRECTNESS & ARCHITECTURE. READ the component(s) the upstream artifact names — a scope's "Affected Area & Pointers", or an RCA's evidence file:line + committed-repro path — as they ACTUALLY are in the repo. Draft: an architecture map of the touched area (current structure + the exact seams where the change hooks in), a files-to-touch list with REAL paths, and phased steps grounded in the real code (cite functions / files / line ranges you have read). Every code reference you cite MUST resolve — confirm it by reading. This is the spine the adversaries will verify.` },
  { key: 'sequencing', mandate: `PLANNER 2 — SEQUENCING, TESTABILITY & PHASING. Draft the plan as an ORDERED sequence of independently-verifiable phases, each with (a) a crisp goal, (b) concrete steps, (c) its own ACCEPTANCE criteria that actually verify the phase, and (d) a checkpoint note (each phase ends green locally and is handed to the user to commit). Make each phase shippable and reversible; order to de-risk — foundational and highest-uncertainty work first. CRITICAL FOR THIS REPO: any phase that depends on an UNCONFIRMED claim about a source endpoint (its shape, its coverage, its cost) must be preceded by a phase that VERIFIES that claim against real bytes, because docs/data-access.md labels each claim with its epistemic status and an unconfirmed one is a task rather than a fact. Specify how each phase is verified (which pytest selector) and the regression safety.` },
  { key: 'domain-convention', mandate: `PLANNER 3 — DATA-MODEL & CONVENTION CORRECTNESS (auto-scaling). IF the feature touches data: ground the plan in the five contracts — grain (one row per WHAT), keys, coverage (which seasons the source actually has), update semantics, and pull cost (how many requests, at what pacing, what gets cached in var/cache/ so a re-run is free). Name the logical name it takes in datasets/manifest.json and the test that will PROVE each declared grain. Flag any claim about a source NOBODY has pulled — an unconfirmed shape presented as fact is this project's most likely silent-wrongness bug. IF it is a feature with thin/no data surface (a skill, CI, infrastructure): PIVOT this lens to PROJECT-CONVENTION correctness — make sure the plan honors and BAKES IN resolve-by-name, the append-only ledger, agents-never-commit, read-only-git subagents, user-run-for-anything-outward-facing, and the established skill patterns, so the cold implementer can't violate CLAUDE.md by following it. Do not force irrelevant data commentary onto a change that touches no data.` },
]

const PHASE_ITEM = { type: 'object', properties: {
  name: { type: 'string' }, goal: { type: 'string' },
  steps: { type: 'array', items: { type: 'string' } },
  acceptance: { type: 'array', items: { type: 'string' } },
  commit_note: { type: 'string' },
}, required: ['name', 'goal', 'steps', 'acceptance', 'commit_note'] }
const REF_ITEM = { type: 'object', properties: { ref: { type: 'string', description: 'a real file / file:line / function' }, claim: { type: 'string', description: 'what the plan says about it' } }, required: ['ref', 'claim'] }
const TOUCH_ITEM = { type: 'object', properties: { path: { type: 'string' }, change: { type: 'string' } }, required: ['path', 'change'] }

const PLANNER_SCHEMA = {
  type: 'object',
  properties: {
    onboarding_files: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, why: { type: 'string' } }, required: ['path', 'why'] } },
    architecture_notes: { type: 'string' },
    phases: { type: 'array', items: PHASE_ITEM },
    testing: { type: 'string' },
    risks: { type: 'array', items: { type: 'string' } },
    files_to_touch: { type: 'array', items: TOUCH_ITEM },
    code_references: { type: 'array', items: REF_ITEM },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['onboarding_files', 'architecture_notes', 'phases', 'testing', 'risks', 'files_to_touch', 'code_references'],
}

phase('Plan')
log(`Planning "${SLUG}" from ${SCOPE} — 3 divergent planners ...`)
const propRaw = await parallel(PLANNERS.map(p => () =>
  runChecked(`${SHARED}\n\n${p.mandate}`, { label: `plan:${p.key}`, phase: 'Plan', schema: PLANNER_SCHEMA, effort: 'high' }, plannerIsStub)
))
const proposals = propRaw.map((c, i) => ({ planner: PLANNERS[i].key, ok: c.ok, ...(c.result || {}) }))
const okProposals = proposals.filter(p => p.ok)
log(`${okProposals.length}/3 planners returned. Converging ...`)
if (!okProposals.length) return { error: 'all planners failed', raw_proposals: proposals }

// ---------- Phase 2: merge ----------
const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    onboarding: { type: 'object', properties: {
      what_it_is: { type: 'string' },
      files_to_read: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, why: { type: 'string' } }, required: ['path', 'why'] } },
    }, required: ['what_it_is', 'files_to_read'] },
    architecture_map: { type: 'string' },
    phases: { type: 'array', items: PHASE_ITEM },
    testing: { type: 'string' },
    decisions: { type: 'array', items: { type: 'object', properties: { decision: { type: 'string' }, rationale: { type: 'string' } }, required: ['decision', 'rationale'] } },
    risks: { type: 'array', items: { type: 'string' } },
    files_to_touch: { type: 'array', items: TOUCH_ITEM },
    conventions: { type: 'array', items: { type: 'string' }, description: 'the CLAUDE.md conventions the plan bakes in for the cold implementer' },
    code_references: { type: 'array', items: REF_ITEM, description: 'every concrete code ref the plan cites — the adversaries verify these resolve' },
    convergence_map: { type: 'array', items: { type: 'object', properties: { theme: { type: 'string' }, planners: { type: 'array', items: { type: 'string' } }, why_high_signal: { type: 'string' } }, required: ['theme', 'planners', 'why_high_signal'] } },
    gated_decisions: { type: 'array', items: { type: 'object', properties: { question: { type: 'string' }, recommendation: { type: 'string' }, related: { type: 'array', items: { type: 'string' } } }, required: ['question', 'recommendation'] } },
  },
  required: ['summary', 'onboarding', 'architecture_map', 'phases', 'testing', 'decisions', 'risks', 'files_to_touch', 'conventions', 'code_references', 'convergence_map', 'gated_decisions'],
}

phase('Converge')
let mergeDegraded = false
const mergeChecked = await runChecked(
  `${SHARED}\n\nYou are the CONVERGENCE agent. Three planners drafted from distinct lenses (code-grounded/architecture, sequencing/testability, domain/convention). Their proposals as JSON:\n\n${JSON.stringify(okProposals, null, 1)}\n\nProduce ONE coherent cold-handoff IMPLEMENTATION_PLAN draft that a cold agent could execute unaided, and that obeys GREEDY-BUT-GATED. CONSUME the decided scope — do NOT re-open fit/goals/acceptance.\n1. ONBOARDING — what the feature is + the files-to-read-first set (real paths).\n2. ARCHITECTURE MAP — the touched area's current structure + where the change hooks in.\n3. PHASES — an ordered sequence, each with goal / steps / its own ACCEPTANCE criteria / a checkpoint note (green locally, then landed via /commit). Any phase resting on an UNCONFIRMED source claim must be preceded by one that verifies it.\n4. TESTING — how the whole thing is verified + regression safety. For data work, name the pytest selectors.\n5. DECISIONS — the design decisions baked into the plan, with rationale.\n6. RISKS.\n7. FILES_TO_TOUCH — the checklist (real paths).\n8. CONVENTIONS — the CLAUDE.md rules the plan bakes in (game-is-read-only, sequential-parsing-never-fixed-offsets, ground-truth-is-players.csv-never-a-screenshot, unvalidated-mappings-labelled-unconfirmed, no-game-data-in-git, resolve-by-name, agents-never-commit, read-only-git subagents, user-run-for-anything-outward-facing).\n9. CODE_REFERENCES — collect EVERY concrete file/function/line the plan cites into one list (the adversaries will verify each resolves).\n10. CONVERGENCE MAP — themes >=2 planners hit independently.\n11. GATED DECISIONS — genuine judgment calls for the human, each with YOUR recommendation.\nGround every cite in the real repo; drop a weak planner idea with a reason rather than laundering it forward.`,
  { label: 'merge', phase: 'Converge', schema: MERGE_SCHEMA, effort: 'high' },
  mergeIsStub
)
let merged = mergeChecked.result
if (!merged || !merged.phases) {
  mergeDegraded = true
  log('  merge failed — recovering (free-text best-effort + deterministic assembly from the surviving proposals)')
  let prose = null
  // NON-'merge' label: the repro stub (and a real retry-cap condition) throws on the
  // exact 'merge' label, so reusing it would re-throw the recovery itself.
  const ft = await safeAgent(`${SHARED}\n\n${MERGE_FREETEXT_MANDATE}\n\nTHE PLANNER PROPOSALS (JSON):\n${JSON.stringify(okProposals, null, 1)}`,
                             { label: 'merge:fallback', phase: 'Converge', effort: 'high' })
  if (typeof ft === 'string' && ft.trim().length > 40) prose = ft
  merged = assemblePlanDraft(okProposals, prose)
}
log(`Merged: ${merged.phases.length} phases; ${(merged.code_references || []).length} code refs; ${(merged.gated_decisions || []).length} gated decisions.`)

// ---------- Phase 3: adversaries + meta-audit ----------
const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    lens_summary: { type: 'string' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, title: { type: 'string' },
      severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit', 'question'] },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
      category: { type: 'string' },
      location: { type: 'string', description: 'a REAL repo file:line you checked, or the plan section' },
      problem: { type: 'string' }, proposed_fix: { type: 'string' },
    }, required: ['id', 'title', 'severity', 'confidence', 'category', 'location', 'problem', 'proposed_fix'] } },
  },
  required: ['lens_summary', 'findings'],
}

const ADVERSARIES = [
  { key: 'code-grounded', kind: 'adversary', mandate: `ADVERSARY 1 — CODE-GROUNDED VERIFICATION (the stage's defining rigor). For EVERY code reference the merged plan cites — in code_references AND anywhere in onboarding / architecture_map / phases / files_to_touch — ACTUALLY READ/GREP the repo and confirm it resolves to what the plan claims. Flag every reference that: does not exist, points at the wrong line, names a function/symbol that isn't there, or whose claimed reuse ("reuse the existing X", "X already does Y") is fictional. Each finding's \`location\` MUST be a real file:line you checked. A plan that cites a function that isn't there walks the cold implementer into a wall — that is exactly what this stage exists to prevent.` },
  { key: 'executability', kind: 'adversary', mandate: `ADVERSARY 2 — EXECUTABILITY & SEQUENCING. Attack whether a COLD agent could actually execute this plan as written. (1) Are the phases truly ORDERED and independently verifiable, or does a phase depend on later work? (2) Does each phase's acceptance criterion actually VERIFY the phase, or is it vague ("works well")? (3) Missing steps, unstated prerequisites, or environment assumptions? (4) Does the plan BAKE IN the CLAUDE.md conventions (resolve-by-name, never-commit, read-only-git subagents) the implementer needs to not violate the repo's rules? (5) Would the files_to_touch checklist actually produce a working result? Read the cited files to ground your critique.` },
]
const META = { key: 'meta-audit', kind: 'meta_audit', mandate: `META-AUDIT — audit the MERGE ITSELF (not the repo). You are given the 3 raw planner proposals AND the merged plan. Check the convergence quality: (a) SCOPE-CREEP — did the merge add work beyond the decided scope's core/folded tiers, or silently promote a gated item into the plan? (b) COMPLETENESS / DEDUP — did the merge DROP a phase, risk, acceptance criterion, or code reference that a planner raised and the others didn't cover? did it duplicate anything? (c) COST-UNREALISM — does the merged plan assert a "reuse what's there" or a "cheap" step that the proposals (or the repo) show isn't actually present/cheap? Flag each as a finding. You are the check on whether the merge faithfully + completely converged the planners without smuggling in scope or losing signal.` }

phase('Adversarial')
const advInput = `\n\nTHE MERGED PLAN DRAFT (JSON):\n${JSON.stringify(merged, null, 1)}`
const metaInput = `${advInput}\n\nTHE 3 RAW PLANNER PROPOSALS (JSON):\n${JSON.stringify(okProposals, null, 1)}`
const reviewers = [
  ...ADVERSARIES.map(a => ({ ...a, prompt: `${SHARED}\n\n${a.mandate}${advInput}\n\nRecord EVERY finding (blocker -> nit) with severity, confidence, a grounded location, and a concrete proposed fix. Ground claims in the actual repo/plan; do not invent problems to pad.` })),
  { ...META, prompt: `${SHARED}\n\n${META.mandate}${metaInput}\n\nRecord EVERY finding (blocker -> nit) with severity, confidence, a location (which plan element / which dropped proposal item), and a concrete proposed fix.` },
]
const revRaw = await parallel(reviewers.map(r => () =>
  runChecked(r.prompt, { label: `${r.kind === 'meta_audit' ? 'meta' : 'adv'}:${r.key}`, phase: 'Adversarial', schema: FINDINGS_SCHEMA, effort: 'high' }, reviewIsStub)
))
const reviews = revRaw.map((c, i) => ({ key: reviewers[i].key, kind: reviewers[i].kind, ok: c.ok, attempts: c.attempts, ...(c.result || {}) }))
const adversaryFindings = reviews.filter(r => r.ok && r.kind === 'adversary').flatMap(r => (r.findings || []).map(f => ({ ...f, reviewer: r.key })))
const metaFindings = reviews.filter(r => r.ok && r.kind === 'meta_audit').flatMap(r => (r.findings || []).map(f => ({ ...f, reviewer: r.key })))
const degraded = [...reviews.filter(r => !r.ok).map(r => `${r.kind}:${r.key}`), ...(mergeDegraded ? ['merge:fallback'] : [])]
log(`Adversaries: ${adversaryFindings.length} findings; meta-audit: ${metaFindings.length} findings${degraded.length ? ` (degraded after retry: ${degraded.join(', ')})` : ''}.`)

return {
  summary: merged.summary,
  plan_draft: {
    onboarding: merged.onboarding, architecture_map: merged.architecture_map, phases: merged.phases,
    testing: merged.testing, decisions: merged.decisions, risks: merged.risks,
    files_to_touch: merged.files_to_touch, conventions: merged.conventions, code_references: merged.code_references,
  },
  convergence_map: merged.convergence_map,
  gated_decisions: merged.gated_decisions,
  adversary_findings: adversaryFindings,
  meta_audit_findings: metaFindings,
  reviewer_summaries: reviews.filter(r => r.ok).map(r => ({ reviewer: r.key, kind: r.kind, summary: r.lens_summary })),
  raw_proposals: okProposals,
  degraded_lenses: degraded,
  stats: {
    planners_ok: okProposals.length,
    adversaries_ok: reviews.filter(r => r.ok && r.kind === 'adversary').length,
    meta_audit_ok: reviews.filter(r => r.ok && r.kind === 'meta_audit').length,
    findings: adversaryFindings.length + metaFindings.length,
    blockers: [...adversaryFindings, ...metaFindings].filter(f => f.severity === 'blocker').length,
    majors: [...adversaryFindings, ...metaFindings].filter(f => f.severity === 'major').length,
  },
}
