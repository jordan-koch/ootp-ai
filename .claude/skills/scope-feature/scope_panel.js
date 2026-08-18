export const meta = {
  name: 'scope-feature-panel',
  description: 'Adversarial scoping panel over a FEATURE_REQUEST: 3 divergent scopers -> merge/converge -> 2 adversaries',
  phases: [
    { title: 'Scope', detail: '3 distinct-persona scopers propose greedily over the feature request' },
    { title: 'Converge', detail: 'merge into one tiered scope + fit verdict + gated decisions' },
    { title: 'Adversarial', detail: '2 adversaries attack fit, acceptance-criteria testability, and scope discipline' },
  ],
}

// args (passed by the scope-feature skill): { requestPath, featureDir, slug }
// The harness may deliver args as a JSON string rather than an object — coerce both.
let A = {}
if (args && typeof args === 'object') { A = args }
else if (typeof args === 'string') { try { A = JSON.parse(args) } catch (e) { A = {} } }
const REQ = A.requestPath || 'requests/feature-requests/<slug>/FEATURE_REQUEST.md'
const SLUG = A.slug || '(unknown)'
const DIR = A.featureDir || 'requests/feature-requests/<slug>/'

// Fail loud instead of scoping a random request: if no real path arrived, the scopers
// would wander requests/feature-requests/ and silently scope whichever request they stumble on.
if (REQ.includes('<slug>')) {
  return { error: `no requestPath reached the panel (args arrived as ${typeof args}) — aborting to avoid scoping the wrong feature`, argsType: typeof args }
}

// ── Stub-degeneration guard ───────────────────────────────────────────────────
// StructuredOutput review/merge agents intermittently degenerate into placeholder
// stubs (e.g. summary "test", single-char findings) that are still truthy and would
// otherwise count as a successful lens — silently gutting the adversarial premise.
// Detect a stub, retry the agent ONCE with reinforcement, and if it still stubs,
// report the lens as NOT ok so stats stay honest (the skill's health check trusts
// scopers_ok / adversaries_ok).
const ANTISTUB = 'Your StructuredOutput MUST contain your real, grounded analysis — NEVER placeholder/stub values (e.g. "test", "probe", single-letter or one-word fields). A stub fails and wastes the run; if uncertain, still write your real best-effort content.'
const ANTISTUB_RETRY = 'RETRY — your previous response was rejected as a placeholder/stub (empty or near-empty summary/findings). The run is wasted unless you return REAL, specific, grounded content NOW: a substantive multi-sentence summary and real content (or, if a list is genuinely empty, say so concretely with evidence). Do NOT return "test" or single-letter values.'
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
// A findings-style review (adversary) is a stub when its summary is empty/placeholder
// AND it has either no findings or only placeholder findings (a real clean review still
// explains itself in the summary, so this won't false-positive a genuine zero-findings pass).
function reviewIsStub(r) {
  if (!r) return true
  const f = r.findings || []
  return looksStub(r.lens_summary) && (f.length === 0 || f.every(stubFinding))
}
function scoperIsStub(p) {
  if (!p) return true
  return looksStub(p.fit && p.fit.rationale) && (p.goals || []).length === 0 && (p.core_scope || []).length === 0
}
function mergeIsStub(m) {
  if (!m || !m.fit_verdict) return true
  return looksStub(m.summary) || (m.acceptance_criteria || []).length === 0 || ((m.tiered_scope && m.tiered_scope.core) || []).length === 0
}
// Deterministic, LLM-free assembly of a usable (degraded) scope draft from the in-hand
// scoper proposals — the recovery FLOOR when the forced-schema merge fails. Carries EVERY
// key the final return reads. fit_verdict is the MOST-CONSERVATIVE of the scopers' verdicts
// and is NEVER reported 'clean' on a degraded run (floored at 'reshape') — a recovered union
// is not a synthesized fit, so it must invite a human look before planning. Enhancements
// default to the 'gated' tier (never silently folded into core).
function assembleScopeDraft(proposals, prose) {
  const uniq = (xs) => [...new Set((xs || []).filter(Boolean))]
  const order = { clean: 0, reshape: 1, poor: 2 }
  const worst = proposals.map(p => p.fit && p.fit.verdict).filter(Boolean).sort((a, b) => (order[b] || 0) - (order[a] || 0))[0]
  const verdict = worst === 'poor' ? 'poor' : 'reshape'  // never assert 'clean' on a degraded union
  const DEG = '[DEGRADED] deterministic union of the surviving scoper proposals — the structured merge failed, so this is a de-duplicated assembly, NOT a synthesis. Verify the fit and spot-check before planning; consider re-running the panel.'
  let core = uniq(proposals.flatMap(p => p.core_scope || []))
  if (!core.length) core = ['[DEGRADED] no core scope survived the assembly — reconstruct the in-scope core by hand from raw_proposals (goals/acceptance below).']
  const acceptance_criteria = uniq(proposals.flatMap(p => p.acceptance_criteria || []))
  return {
    summary: prose || DEG,
    fit_verdict: { verdict, rationale: '[DEGRADED] recovered union — fit not synthesized; verify before planning.' },
    problem_restatement: prose || DEG,
    goals: uniq(proposals.flatMap(p => p.goals || [])),
    non_goals: uniq(proposals.flatMap(p => p.non_goals || [])),
    acceptance_criteria,
    tiered_scope: { core, cheap_folds: [], gated: [] },
    above_and_beyond: proposals.flatMap(p => (p.enhancements || []).map(e => ({ title: e.title, tier: 'gated', rationale: e.rationale }))),
    risks: uniq(proposals.flatMap(p => p.risks || [])),
    grounding_pointers: ['[DEGRADED] grounding pointers not synthesized — see raw_proposals and the request\'s own Affected Area & Pointers.'],
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

const SHARED = `You are scoping a proposed new feature for an AI front office for Out of the Park Baseball 25: a parser reads the game's proprietary save binaries READ-ONLY, lands them in a MySQL warehouse as per-sim-date snapshots, and specialist advisors recommend moves that a human GM executes. Python (src/ootp_ai) + a dbt medallion. The system NEVER writes to the game. Read docs/decisions/ before proposing anything structural — eight ADRs are settled and re-litigating them is expensive. Your working directory is the repo root.

THE FEATURE REQUEST TO SCOPE: ${REQ}  (slug: ${SLUG})

READ IT IN FULL FIRST. Then ground yourself in the repo before proposing anything — read at minimum:
- the request's own "Affected Area & Pointers" section, and FOLLOW those pointers (the files / models / docs it names)
- requests/feature-requests/README.md — the pipeline contract: the PROJECT_SCOPE.md handoff interface this scope must satisfy, the two standing principles GREEDY-BUT-GATED and GENERATE -> CONVERGE -> TRIAGE -> YOU-DECIDE, and what "testable acceptance criteria" means for data work (a pytest assertion that passes or fails, not a number a human eyeballs)
- CLAUDE.md — the project rules you must scope within: the game is READ-ONLY (ADR 0001 — no save writes, no roster import files, no UI automation); the parser walks records SEQUENTIALLY and never seeks to a fixed offset; ground truth is players.csv, NEVER an in-game screenshot (displayed ratings are scale-converted and possibly scout-filtered); no OOTP game data may be tracked in git (ADR 0006); paths resolve from .env and datasets resolve BY NAME via datasets/manifest.json; epistemic labels are load-bearing; commits go through /commit only; subagents get read-only git
- docs/data-access.md — what the save files actually provide, at what fidelity, and what breaks. NOTE: every claim carries a per-claim epistemic label, so read the label; treat an unconfirmed or assumed one as a claim to verify, not a fact to build on
- docs/decisions/ — the ADRs. A scope that contradicts an accepted ADR must say so explicitly rather than quietly diverging

IF THIS FEATURE TOUCHES A DATASET, the scope must settle five contracts: grain (one row per WHAT — 'player per snapshot' and 'player per team-stint per snapshot' differ exactly when a mid-season trade happens), keys (OOTP's internal player_id and the real-world Lahman ID are DIFFERENT keys with DIFFERENT coverage — only ~1,712 of ~18,000 players carry a Lahman ID), coverage (which populations the source actually contains — fictional players, minor leaguers and retired players each lack fields the majors carry, and structurally-absent is not missing), update semantics (append-only per snapshot, or restated), and WHICH DATA-LAYER PATTERN it belongs to per ADR 0005: does it change when the league is simulated? No means a builder + datasets/; Yes means the parser + dbt. IF IT TOUCHES THE PARSER, it must instead settle: what ground truth validates the new fields, what the epistemic label is until that validation runs, and how the code refuses an unrecognized save version rather than misparsing it.

Ground every claim in concrete repo artifacts — cite files / line numbers / model names. Do NOT invent paths; verify a path resolves before relying on it. LABEL YOUR EPISTEMICS: measured / verified / inferred / assumed / unconfirmed are different words and this repo treats them as different claims. The output of this stage is a PROJECT_SCOPE, not an implementation plan: say WHAT and WHY-IT-FITS and HOW-WE'LL-KNOW-IT-WORKED, and stop short of designing the code.

YOU ARE READ-ONLY: read the repo freely to ground your work, but do NOT modify any file, and never run a git command that changes the working tree (no checkout / reset / restore / clean / stash / commit). If a change is needed, describe it — don't make it.

${ANTISTUB}`

// Free-text (no-schema) recovery mandate. Used ONLY when the forced-StructuredOutput
// merge fails: free-text stays reliable where forced StructuredOutput degenerates (see
// memory `review_harness_reliability`). It only ENRICHES the deterministic assembly below.
const MERGE_FREETEXT_MANDATE = 'The structured merge just failed. As a best-effort recovery, synthesize the scoper proposals below into a PROSE PROJECT_SCOPE: a fit verdict (clean / reshape / poor) with reasons, a problem restatement, goals / non-goals, TESTABLE acceptance criteria, the in-scope core, the above-and-beyond enhancements, risks, and the grounding pointers a stage-3 plan should read first. Write PLAIN TEXT only — NO JSON, NO schema. Be specific and ground every claim in the proposals.'

const SCOPERS = [
  { key: 'fit', label: 'repo-fit',
    mandate: `SCOPER 1 — REPO-FIT & ARCHITECTURE. Scope this feature through the lens of how it fits THIS repo. Decide: does it belong here, and how does it integrate with the existing architecture? Name the concrete modules, datasets (by logical name), warehouse models, and skills it leverages, extends, or joins to; whether it belongs in the parser, the warehouse loader, a dbt layer, a static reference builder, or an advisor, and why (ADR 0005's split: does it change when the league is simulated?); the conventions that constrain it (game-is-read-only, sequential-parsing-never-fixed-offsets, ground-truth-is-players.csv, no-game-data-in-git, resolve-by-name); the integration seams; and where it would conflict with or duplicate something that already exists. Render a frank FIT verdict — clean fit / awkward fit needing reshaping / poor fit — with grounded reasons. Propose the scope that goes with the grain of the repo: goals, non-goals, the in-scope core, and acceptance criteria expressed against real repo artifacts.` },
  { key: 'ambitious', label: 'ambitious',
    mandate: `SCOPER 2 — AMBITIOUS / ABOVE-AND-BEYOND. Implementation here is cheap, so be greedy. Scope the FULLEST genuinely-valuable version: what makes this feature great rather than merely adequate? What complementary enhancements naturally ride along — extra outputs, adjacent capabilities, quality-of-life wins, reuse that also benefits other skills/tools/datasets? Propose EVERY idea worth considering and do NOT self-censor — a downstream merge will tier and gate them; your job is to make sure no good idea is lost. For each enhancement, note how it complements the core and whether it's cheap or grows the build. Still give goals, non-goals (even an ambitious scope has edges), and testable acceptance criteria.` },
  { key: 'minimalist', label: 'minimalist',
    mandate: `SCOPER 3 — RISK / YAGNI / MINIMALIST. Scope the SMALLEST thing that genuinely solves the stated problem. Identify the irreducible core that must exist, and call out any proposed or implied scope that is unjustified gold-plating. Enumerate the real risks, unknowns, and failure modes: era gaps where the source has no data, unverified assumptions about endpoint shape or cost, grain ambiguity that will silently fan out a join, convention conflicts, maintenance burden, anything that could break an existing model, or any assumption in the request that may not hold. Say what to defer or cut outright. Propose tight goals, aggressive non-goals, minimal testable acceptance criteria, and a frank risk list. You are the counterweight to greed — name what NOT to build and why.` },
]

const SCOPER_SCHEMA = {
  type: 'object',
  properties: {
    fit: { type: 'object', properties: {
      verdict: { type: 'string', enum: ['clean', 'reshape', 'poor'] },
      rationale: { type: 'string' },
    }, required: ['verdict', 'rationale'] },
    goals: { type: 'array', items: { type: 'string' } },
    non_goals: { type: 'array', items: { type: 'string' } },
    acceptance_criteria: { type: 'array', items: { type: 'string', description: 'each must be objectively checkable' } },
    core_scope: { type: 'array', items: { type: 'string' } },
    enhancements: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' }, rationale: { type: 'string' },
      cost: { type: 'string', enum: ['cheap', 'grows-build'] },
    }, required: ['title', 'rationale', 'cost'] } },
    risks: { type: 'array', items: { type: 'string' } },
    open_questions: { type: 'array', items: { type: 'string' } },
  },
  required: ['fit', 'goals', 'non_goals', 'acceptance_criteria', 'core_scope', 'enhancements', 'risks'],
}

phase('Scope')
log(`Scoping "${SLUG}" — 3 divergent personas reading ${REQ} ...`)
const proposalsRaw = await parallel(SCOPERS.map(s => () =>
  runChecked(`${SHARED}\n\n${s.mandate}`, { label: `scope:${s.key}`, phase: 'Scope', schema: SCOPER_SCHEMA, effort: 'high' }, scoperIsStub)
))
const proposals = proposalsRaw.map((c, i) => ({ scoper: SCOPERS[i].key, ok: c.ok, ...(c.result || {}) }))
const okProposals = proposals.filter(p => p.ok)
log(`${okProposals.length}/3 scopers returned. Converging ...`)
if (!okProposals.length) return { error: 'all scopers failed', proposals }

const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    fit_verdict: { type: 'object', properties: {
      verdict: { type: 'string', enum: ['clean', 'reshape', 'poor'] },
      rationale: { type: 'string' },
    }, required: ['verdict', 'rationale'] },
    problem_restatement: { type: 'string' },
    goals: { type: 'array', items: { type: 'string' } },
    non_goals: { type: 'array', items: { type: 'string' } },
    acceptance_criteria: { type: 'array', items: { type: 'string', description: 'TESTABLE — each objectively checkable' } },
    tiered_scope: { type: 'object', properties: {
      core: { type: 'array', items: { type: 'string' } },
      cheap_folds: { type: 'array', items: { type: 'string' } },
      gated: { type: 'array', items: { type: 'string' } },
    }, required: ['core', 'cheap_folds', 'gated'] },
    above_and_beyond: { type: 'array', items: { type: 'object', properties: {
      title: { type: 'string' },
      tier: { type: 'string', enum: ['core', 'cheap_fold', 'gated', 'drop'] },
      rationale: { type: 'string' },
    }, required: ['title', 'tier', 'rationale'] } },
    risks: { type: 'array', items: { type: 'string' } },
    grounding_pointers: { type: 'array', items: { type: 'string' }, description: 'the target component(s) plus concrete files/datasets (by manifest name)/docs the stage-3 implementation plan should read first — carried from the request and refined by the repo-fit scoper' },
    convergence_map: { type: 'array', items: { type: 'object', properties: {
      theme: { type: 'string' },
      scopers: { type: 'array', items: { type: 'string' } },
      why_high_signal: { type: 'string' },
    }, required: ['theme', 'scopers', 'why_high_signal'] } },
    gated_decisions: { type: 'array', items: { type: 'object', properties: {
      question: { type: 'string' },
      recommendation: { type: 'string' },
      related: { type: 'array', items: { type: 'string' } },
    }, required: ['question', 'recommendation'] } },
  },
  required: ['summary', 'fit_verdict', 'problem_restatement', 'goals', 'non_goals', 'acceptance_criteria', 'tiered_scope', 'above_and_beyond', 'risks', 'grounding_pointers', 'convergence_map', 'gated_decisions'],
}

phase('Converge')
let scopeDegraded = false
const mergeChecked = await runChecked(
  `${SHARED}\n\nYou are the CONVERGENCE agent. Three scopers proposed scopes from distinct lenses (repo-fit, ambitious, minimalist). Their proposals as JSON:\n\n${JSON.stringify(okProposals, null, 1)}\n\nProduce ONE coherent PROJECT_SCOPE draft that satisfies the requests/feature-requests/README.md handoff interface and obeys GREEDY-BUT-GATED:\n1. FIT VERDICT — synthesize the repo-fit assessment (clean / reshape / poor), grounded. If reshape or poor, this becomes the HEADLINE gated decision.\n2. PROBLEM RESTATEMENT — crisp, faithful to the request.\n3. GOALS / NON-GOALS — reconcile the three (graft the minimalist's honest edges onto the ambitious goals; adjudicate conflicts).\n4. ACCEPTANCE CRITERIA — every one must be TESTABLE (objectively checkable). Reject or rewrite vague ones.\n5. TIERED SCOPE — core (must-have) / cheap_folds (greedy wins low-risk enough to just include) / gated (anything that grows scope or is a genuine judgment call — goes to the human, NEVER silently folded).\n6. ABOVE-AND-BEYOND — tier EVERY enhancement the ambitious scoper raised (core / cheap_fold / gated / drop); drop with a reason rather than laundering a weak idea forward.\n7. RISKS & UNKNOWNS — from the minimalist plus your own read.\n8. GROUNDING POINTERS — the target component(s) and the concrete files/datasets (by manifest name)/docs a cold stage-3 implementation plan must read FIRST; carry the request's "Affected Area & Pointers" forward, refined by the repo-fit scoper's integration findings (the gold IMPLEMENTATION_PLANs open with exactly this).\n9. CONVERGENCE MAP — themes >=2 scopers hit independently (highest signal).\n10. GATED DECISIONS — the genuine judgment calls for the human, each with YOUR recommendation. A non-clean fit verdict is the first gated decision (reshape / drop / proceed-with-caveats).\nBe honest and specific; ground claims in the repo.`,
  { label: 'merge', phase: 'Converge', schema: MERGE_SCHEMA, effort: 'high' },
  mergeIsStub
)
let merged = mergeChecked.result
if (!merged || !merged.fit_verdict) {
  scopeDegraded = true
  log('  merge failed — recovering (free-text best-effort + deterministic assembly from the surviving proposals)')
  let prose = null
  // NON-'merge' label: the merge label throws on a retry-cap condition, so reusing it re-throws the recovery.
  const ft = await safeAgent(`${SHARED}\n\n${MERGE_FREETEXT_MANDATE}\n\nTHE SCOPER PROPOSALS (JSON):\n${JSON.stringify(okProposals, null, 1)}`,
                             { label: 'merge:fallback', phase: 'Converge', effort: 'high' })
  if (typeof ft === 'string' && ft.trim().length > 40) prose = ft
  merged = assembleScopeDraft(okProposals, prose)
}
log(`Merged: fit=${merged.fit_verdict.verdict}; ${merged.acceptance_criteria.length} acceptance criteria; ${merged.gated_decisions.length} gated decisions.`)

const ADVERSARIES = [
  { key: 'fit-ac', label: 'fit+AC',
    mandate: `ADVERSARY 1 — FIT, FRAMING & ACCEPTANCE-CRITERIA TESTABILITY. Attack the merged scope on: (1) Is this the RIGHT problem, framed honestly — or has the scope drifted from the request's actual pain? (2) Is the repo-fit verdict accurate — VERIFY the cited integration points / datasets / patterns actually exist in the repo (resolve them; flag any that don't). (3) Are the acceptance criteria genuinely TESTABLE — for each, state exactly how you'd objectively check it; flag any that are vague or unmeasurable and propose a testable rewrite. (4) Are the non-goals honest, or do they quietly bury a hard part of the problem?` },
  { key: 'scope-completeness', label: 'scope+gaps',
    mandate: `ADVERSARY 2 — SCOPE DISCIPLINE & COMPLETENESS. Attack the merged scope from two sides. (A) SCOPE-CREEP / YAGNI: did greedy ideas get folded into 'core' or 'cheap_folds' that should be 'gated' or 'drop'? Is each 'cheap fold' actually cheap, or does it grow the build? Is the gating honest? (B) COMPLETENESS CRITIC: what is MISSING — an angle not scoped, a risk not named, a non-goal that should exist, a data/dependency gap overlooked, or an existing skill/dataset/tool this would break that the scope never addresses? Be the check on both over-reach AND blind spots.` },
]

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    lens_summary: { type: 'string' },
    findings: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' },
      title: { type: 'string' },
      severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit', 'question'] },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
      category: { type: 'string', description: 'e.g. fit / framing / acceptance / scope-creep / completeness / risk' },
      location: { type: 'string', description: 'which part of the scope, or a repo file:line' },
      problem: { type: 'string' },
      proposed_fix: { type: 'string' },
    }, required: ['id', 'title', 'severity', 'confidence', 'category', 'problem', 'proposed_fix'] } },
  },
  required: ['lens_summary', 'findings'],
}

phase('Adversarial')
const advRaw = await parallel(ADVERSARIES.map(a => () =>
  runChecked(
    `${SHARED}\n\n${a.mandate}\n\nTHE MERGED SCOPE DRAFT (JSON):\n${JSON.stringify(merged, null, 1)}\n\nRecord EVERY finding (blocker -> nit, plus open questions) with NO self-filtering — severity, confidence, a grounded location/evidence, and a concrete proposed fix. Ground claims in the actual request and repo; do not invent problems to pad the list.`,
    { label: `adv:${a.key}`, phase: 'Adversarial', schema: FINDINGS_SCHEMA, effort: 'high' },
    reviewIsStub
  )
))
const adversaries = advRaw.map((c, i) => ({ adversary: ADVERSARIES[i].key, ok: c.ok, ...(c.result || {}) }))
const adversaryFindings = adversaries.filter(a => a.ok).flatMap(a => (a.findings || []).map(f => ({ ...f, adversary: a.adversary })))
const degraded = [...adversaries.filter(a => !a.ok).map(a => a.adversary), ...(scopeDegraded ? ['merge:fallback'] : [])]
log(`Adversaries returned ${adversaryFindings.length} findings across ${adversaries.filter(a => a.ok).length}/2${degraded.length ? ` (degraded after retry: ${degraded.join(', ')})` : ''}.`)

return {
  summary: merged.summary,
  fit_verdict: merged.fit_verdict,
  problem_restatement: merged.problem_restatement,
  goals: merged.goals,
  non_goals: merged.non_goals,
  acceptance_criteria: merged.acceptance_criteria,
  tiered_scope: merged.tiered_scope,
  above_and_beyond: merged.above_and_beyond,
  risks: merged.risks,
  grounding_pointers: merged.grounding_pointers,
  convergence_map: merged.convergence_map,
  gated_decisions: merged.gated_decisions,
  adversary_findings: adversaryFindings,
  adversary_summaries: adversaries.filter(a => a.ok).map(a => ({ adversary: a.adversary, summary: a.lens_summary })),
  raw_proposals: okProposals,
  degraded_lenses: degraded,
  stats: {
    scopers_ok: okProposals.length,
    adversaries_ok: adversaries.filter(a => a.ok).length,
    findings: adversaryFindings.length,
    blockers: adversaryFindings.filter(f => f.severity === 'blocker').length,
    majors: adversaryFindings.filter(f => f.severity === 'major').length,
  },
}
