export const meta = {
  name: 'implement-acceptance-panel',
  description: 'Context-aware adversarial acceptance panel over a COMPLETED implementation: 4 core reviewers + auto-scaled specialists -> execution-based verify -> meta-audit',
  phases: [
    { title: 'Review', detail: 'core reviewers (acceptance / fidelity / correctness / edge-cases) + specialists matched to the touched areas, all read-only over the uncommitted diff' },
    { title: 'Verify', detail: 'independently confirm/refute the deduped blocker+major findings BY RUNNING them (location-grouped into at most verifyCap batch agents), and re-derive the acceptance ledger from scratch' },
    { title: 'Synthesize', detail: 'reconcile into one acceptance ledger + verdict, then a meta-audit checks the synthesis dropped nothing' },
  ],
}

// args (from the implement-plan skill): { planPath, scopePath, slug, touchedAreas, verifyCap? }
// The harness may deliver args as a JSON string rather than an object — coerce both.
let A = {}
if (args && typeof args === 'object') { A = args }
else if (typeof args === 'string') { try { A = JSON.parse(args) } catch (e) { A = {} } }
const PLAN = A.planPath || 'requests/feature-requests/<slug>/IMPLEMENTATION_PLAN.md'
const SCOPE = A.scopePath || ''
const SLUG = A.slug || '(unknown)'
const AREAS = Array.isArray(A.touchedAreas) ? A.touchedAreas : []
// Verify-phase fan-out cap. Phase 2 used to spawn ONE agent per blocker/major finding, which made
// it ~65% of the panel's agents and effectively all of its variance (a 6-lens roster raising 2-3
// findings apiece = 12-18 verifiers). Worse, EVERY one of those agents re-paid the full grounding
// preamble — read the diff in full, read the plan in full, read CLAUDE.md — to adjudicate a single
// finding. Findings are now deduped, grouped by location, and packed into at most VERIFY_CAP batch
// agents, so that fixed grounding cost is paid once per batch instead of once per finding. The
// independent ledger verifier stays OUTSIDE the cap (it is the double-ledger cross-check).
const VERIFY_CAP = Number.isFinite(Number(A.verifyCap)) && Number(A.verifyCap) > 0
  ? Math.max(1, Math.floor(Number(A.verifyCap)))
  : 4

// Fail loud instead of reviewing a random feature: if no real plan path arrived, the
// reviewers would wander requests/feature-requests/ and silently review whichever plan they find.
if (PLAN.includes('<slug>')) {
  return { error: `no planPath reached the panel (args arrived as ${typeof args}) — aborting to avoid reviewing the wrong feature`, argsType: typeof args }
}

// ── Stub-degeneration guard (adapted from the sibling pipeline panels, plus a ────
//    safeAgent throw-guard the siblings lack, so a hard StructuredOutput failure in a
//    direct-await lens degrades instead of crashing the run) ──────────────────────
// StructuredOutput review agents intermittently degenerate into placeholder stubs
// (e.g. summary "test", single-char findings) that are still truthy and would otherwise
// count as a successful lens — silently gutting the adversarial premise. Detect a stub,
// retry the agent ONCE with reinforcement, and if it still stubs, report the lens as NOT
// ok so stats stay honest (the skill's Step-5 health check trusts the *_ok counts).
const ANTISTUB = 'Your StructuredOutput MUST contain your real, grounded analysis — NEVER a placeholder/stub value (e.g. "test", "probe", single-letter fields). A stub output fails the run and wastes it; if you are unsure, still write your real best-effort content.'
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
// A findings-style review is a stub when its summary is empty/placeholder AND it has
// either no findings or only placeholder findings (a real clean review still explains
// itself, so this won't false-positive a genuine zero-findings pass).
function reviewIsStub(r) {
  if (!r) return true
  const f = r.findings || []
  return looksStub(r.lens_summary) && (f.length === 0 || f.every(stubFinding))
}
// The acceptance lens is a stub when it produced no criteria results AND a stub summary —
// a real audit of a planned feature always enumerates at least one criterion.
// A criteria ledger is degenerate when it has NO rows, or every row is a
// placeholder (stub criterion AND stub evidence) — e.g. a single {criterion:'shape
// check', evidence:'probe'} row. The earlier length===0 check missed that case, so a
// dead independent cross-check counted as a healthy verifier and the *_ok stats lied.
function ledgerRowsDegenerate(rows) {
  if (!rows || rows.length === 0) return true
  return rows.every(c => looksStub(c && c.criterion) && looksStub(c && c.evidence))
}
function acceptanceIsStub(r) {
  if (!r) return true
  return ledgerRowsDegenerate(r.criteria_results)
}
// A BATCH verify result is degenerate when it returned no verdicts at all, when every verdict is
// evidence-free, or — the batching-specific failure mode — when a multi-finding batch stamped every
// row with the IDENTICAL evidence AND command. That last one is the tell that the agent adjudicated
// the batch as one blob instead of each finding on its own, which is exactly the quality the
// per-finding fan-out used to buy for free.
function verifyBatchIsStub(v) {
  const rows = v && Array.isArray(v.verdicts) ? v.verdicts : null
  if (!rows || rows.length === 0) return true
  if (rows.every(r => !r || (!r.verdict && looksStub(r.evidence)))) return true
  if (rows.length > 1 && rows.every(r => r && r.evidence === rows[0].evidence && r.ran === rows[0].ran)) return true
  return false
}
function ledgerIsStub(r) {
  if (!r) return true
  return ledgerRowsDegenerate(r.criteria_results)
}
function mergeIsStub(m) {
  if (!m || !m.verdict) return true
  return looksStub(m.summary) || (m.acceptance_ledger || []).length === 0
}
// Deterministic, LLM-free assembly of a usable (degraded) acceptance report when the forced
// synthesis fails. SHAPE-APPROPRIATE for stage 4 (an acceptance_ledger + verdict, not phases):
// the ledger is taken VERBATIM from the surviving cross-check — the independent verifier's
// ledger if it ran, else the auditor's — and the verdict is forced to 'fix' (NEVER a false
// 'go' from a report nobody synthesized). Refuted findings are dropped. Carries every key the
// final return + the Synthesis log read.
function assembleAcceptanceReport(okReviews, verifiedFindings, auditorLedger, verifierLedger, prose) {
  const usedVerifier = !!(verifierLedger && verifierLedger.length)
  const src = usedVerifier ? verifierLedger : (auditorLedger || [])
  const fromLabel = usedVerifier ? 'independent verifier' : 'auditor'
  let acceptance_ledger = src.map(r => ({
    id: r.id, criterion: r.criterion, source: r.source, verdict: r.verdict, evidence: r.evidence,
    reconciliation: `[DEGRADED] taken verbatim from the ${fromLabel} ledger; the synthesis did not run to reconcile the two.`,
  }))
  if (!acceptance_ledger.length) {
    acceptance_ledger = [{
      id: 'recovery-1',
      criterion: 'Acceptance ledger could not be rebuilt — neither the auditor nor the independent verifier produced a ledger.',
      source: 'recovery', verdict: 'not-verifiable',
      evidence: 'See reviews + verified_findings in the panel output; rebuild the ledger by hand from the acceptance criteria.',
      reconciliation: '[DEGRADED] synthesis failed and no upstream ledger survived.',
    }]
  }
  const DEG = '[DEGRADED] deterministic assembly — the structured synthesis failed, so this report is reconciliation-free (ledger taken verbatim from the surviving cross-check, refuted findings dropped, verdict forced to fix). Re-run the panel for a true synthesis before trusting the verdict.'
  return {
    summary: prose || DEG,
    verdict: 'fix',                                    // never 'go' on a degraded synthesis
    verdict_rationale: prose
      ? "[DEGRADED] verdict forced to 'fix' (the structured synthesis did not run); see the prose recovery + the ledger and re-derive a real verdict."
      : DEG,
    acceptance_ledger,
    confirmed_findings: (verifiedFindings || []).filter(f => f && f.verdict !== 'refuted'),
    gated_decisions: [],
  }
}
// agent() can fail two ways: a schema-VALID placeholder stub (caught by isStub),
// OR a hard StructuredOutput failure where the harness exhausts its retry cap and
// THROWS. A throw from a direct-await call (synthesis/meta-audit) escapes parallel()
// and would kill the whole panel — so swallow it here and treat the lens as failed.
// A dead lens must DEGRADE (honest degraded_lenses), never crash the run.
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

// Read-only, but verification-capable: reviewers MUST be able to RUN the checks (that is
// the whole point — execution, not assertion), while never mutating the tree.
const READONLY = "YOU ARE READ-ONLY-BUT-VERIFICATION-CAPABLE. You MAY read/grep any file and you MAY RUN read-only verification commands to ground your judgment: 'uv run pytest', 'uv run ruff check', 'uv run mypy', the parser against a committed fixture, 'git diff HEAD', 'git status', 'git log'. You MUST NOT modify any file (no Edit/Write) and MUST NOT run any git command that changes the working tree or history (no checkout/reset/restore/clean/stash/commit/add/rm). Do NOT run anything that writes to var/, and NEVER write to anything under the OOTP saved-games directory or the game install — the game's files are READ-ONLY to this entire project (ADR 0001), and a Challenge Mode save carries an integrity hash that a single write destroys irreversibly. Prefer tests/fixtures/ over a real save. If a change is needed, DESCRIBE it as a finding — never make it. (A write-capable review agent once ran 'git checkout' and silently reverted all uncommitted work; that is why this rule is absolute.)"

const SHARED = `You are REVIEWING a COMPLETED implementation of a DECIDED plan, for an AI front office for Out of the Park Baseball 25: a parser reads the game's proprietary save binaries read-only, lands them in a MySQL warehouse as per-sim-date snapshots, and specialist advisors recommend moves that a human GM executes. Python (src/ootp_ai) + dbt medallion. The system NEVER writes to the game. Working directory = repo root. The code has ALREADY been written and sits UNCOMMITTED in the working tree.

THE PLAN THAT WAS IMPLEMENTED: ${PLAN}   (slug: ${SLUG})
${SCOPE ? `THE UPSTREAM ARTIFACT WITH ITS ACCEPTANCE CONTRACT (a PROJECT_SCOPE's numbered Acceptance Criteria, OR a ROOT_CAUSE_ANALYSIS's "the red repro goes GREEN + a regression test is left behind + nothing else regresses"): ${SCOPE}` : '(no separate upstream-artifact path was passed — take the acceptance criteria from the plan itself.)'}

GROUND YOURSELF FIRST, before judging anything:
- Run 'git diff HEAD' and 'git status --porcelain' to see EXACTLY what changed (the implementation is uncommitted). Read the changed files IN FULL, not just the diff hunks.
- READ THE PLAN IN FULL: its phased section carries per-phase ACCEPTANCE criteria; its files-to-touch checklist is what SHOULD have changed; its conventions section is the rules the code must honor.
- READ THE ACCEPTANCE CRITERIA — the upstream artifact's (a scope's numbered Acceptance Criteria, OR an RCA's "red repro goes green + regression test left behind + no audit/test regresses" contract) PLUS each plan phase's — together they are the contract the implementation must satisfy.
- CLAUDE.md — the conventions: the game is READ-ONLY (ADR 0001 — any code path that writes a save, a roster import file, or automates the game UI is a BLOCKER); the parser walks records SEQUENTIALLY and NEVER seeks to a fixed offset (records carry variable-length regions, so a fixed-offset read passes on day-0 data and silently corrupts everything after); ground truth is players.csv, NEVER an in-game screenshot (displayed ratings are scale-converted AND scout-filtered); no OOTP game data may ever be tracked in git (ADR 0006); paths resolve from .env, never hardcoded; epistemic labels are load-bearing; commits go through /commit only.

Your stance is ADVERSARIAL: assume the implementation is INCOMPLETE or SUBTLY WRONG until you have verified otherwise BY RUNNING IT. A green test run or a tidy diff is NOT proof — re-run the checks yourself and read the real output. For a data change, "the models built" is NOT the same as "the models are right": check that every declared grain has a passing uniqueness test, that nothing silently fanned out a join, and that era-bounded columns are handled rather than averaged across their boundary. GROUND EVERY claim in concrete evidence: a real file:line you read, or the actual output of a command you ran. A fabricated "verified" is worse than an honest "couldn't verify".

${READONLY}

${ANTISTUB}`

// Free-text (no-schema) recovery mandate. Used ONLY when the forced-StructuredOutput
// synthesis fails: free-text stays reliable where forced StructuredOutput degenerates
// (see memory `review_harness_reliability`). It only ENRICHES the deterministic assembly.
const SYNTH_FREETEXT_MANDATE = 'The structured synthesis just failed. As a best-effort recovery, reconcile the panel into a PROSE acceptance report: an acceptance ledger (one line per criterion with met / partial / unmet + the evidence), the confirmed findings (DROP refuted ones), an overall verdict (go / fix / no-go) with rationale, and any genuine gated decisions. Write PLAIN TEXT only — NO JSON, NO schema. Ground every line in the reviews, verify verdicts, and ledgers below.'

// ── Reviewer roster ────────────────────────────────────────────────────────────
// 4 core reviewers (always) + specialists matched to the touched areas.
const CORE = [
  { key: 'acceptance', schema: 'acceptance', mandate: `REVIEWER — ACCEPTANCE-CRITERIA AUDITOR (this stage's defining rigor). Enumerate EVERY acceptance criterion: the upstream artifact's acceptance criteria (a scope's acceptance_criteria, OR — for a bugfix run whose upstream is a ROOT_CAUSE_ANALYSIS — its "red repro goes green + regression test left behind + no audit/test regresses" contract, in which case the ledger MUST carry a 'red repro now green + regression test present' row) AND each plan phase's acceptance list. For EACH, determine its verdict by VERIFICATION, preferring EXECUTION: run 'uv run pytest' / the domain core against a committed fixture, and read the output; or, where execution genuinely can't cover it, cite the exact file:line that satisfies it. Record each as met / partial / unmet / not-verifiable with the concrete EVIDENCE (the command output you saw, or the file:line) and how you checked it. A criterion you cannot actually verify is 'not-verifiable' (say why) — NEVER guess 'met'. Be exhaustive: a silently-unmet criterion shipping as 'done' is the exact failure this stage exists to catch.` },
  { key: 'fidelity', schema: 'findings', mandate: `REVIEWER — PLAN-FIDELITY & COMPLETENESS. Compare the diff against the plan. (1) Was every ACTIVE phase actually implemented, and every item in the files-to-touch checklist addressed (or its omission justified)? Flag silently-skipped work. (2) Are there DEVIATIONS from the plan — a different approach, extra files, fewer — and is each a conscious, defensible choice or an accidental gap? (3) Did the implementation add work BEYOND the plan (implement-time scope-creep), or build a DEFERRED phase the plan said to leave out? (4) Are the plan's conventions actually honored in the code? Each finding names the plan element and the diff location.` },
  { key: 'correctness', schema: 'findings', mandate: `REVIEWER — CORRECTNESS / BUG HUNTER. Hunt for REAL bugs in the changed code: logic errors, off-by-one, unhandled None/empty, wrong API or argument use, broken control flow, a regression in a function the diff touched. This project's highest-value bug classes: (a) FIXED-OFFSET SEEKING — does any read compute a field position as a constant offset from a record start or an anchor? Records carry VARIABLE-LENGTH regions (contract arrays, stat history, strings), so this passes on day-0 data and silently returns the wrong field forever after. BLOCKER. (b) UNVALIDATED FIELD MAPPING — is a newly-claimed field asserted without being checked against players.csv or another independent source? A mis-mapped u16 returns a plausible number, not an error, and flows into a recommendation. (c) TRUE vs SCOUTED RATINGS — does the code conflate them, or use an in-game display value as ground truth? Displayed ratings are scale-converted (20-80 / 1-100 vs ~1-1000 storage) AND possibly scout-filtered. (d) KEY CONFUSION — OOTP's internal player_id and the real-world Lahman ID are DIFFERENT keys with DIFFERENT coverage (only ~1,712 players have a Lahman ID; fictional players have none). A join on the wrong one silently drops most of the league. (e) AS-OF RESOLUTION — a player's team is a function of the snapshot date, not of today; resolving affiliation as-of the wrong date is the most likely source of a silently wrong join. For Python, check timezone-aware datetimes and pathlib usage. Read the surrounding code, not just the diff hunk. Each finding needs a real file:line AND a concrete failure scenario (the input that breaks it) — reproduce it by running it where you can. Do not invent bugs to pad.` },
  { key: 'edgecases', schema: 'findings', mandate: `REVIEWER — TEST & EDGE-CASE. (1) Does the change carry tests for its new behavior, and do they actually exercise it (read them — a test that asserts nothing is theatre)? A parser change with no pinned fixture is UNTESTED regardless of how many other tests exist. (2) ADVERSARIALLY GENERATE edge cases the implementation might mishandle, and CHECK each by running or tracing it. This project's known breakers: a FICTIONAL player (no Lahman ID at all — the majority of the ~18,000 players); a player with a 1-year contract vs a 10-year one (the variable-length array that breaks fixed offsets); a rookie with NO stat history (every year-keyed block empty — this is the day-0 shape that hides bugs); a player traded mid-season (affiliation as-of); a minor leaguer missing fields the majors carry; a name index pointing outside names.dat; a retired player (retired.dat, a different and much larger file); two snapshots of the SAME league at different sim dates (the snapshot key must distinguish them); a save whose header version byte is NOT 0x19 (a patched game — the field map may no longer apply and the code must refuse rather than misparse). (3) Regression risk to an already-validated field mapping? Ground each finding in a real input + the observed or traced behavior.` },
]

const SPEC_DEFS = {
  'parser': { key: 'parser', schema: 'findings', mandate: `SPECIALIST — PARSER INTEGRITY (src/ootp_ai parser or landing touched). This reads a REVERSE-ENGINEERED binary format with no schema, no vendor contract, and no error on a wrong read. (1) FIXED OFFSETS: does any read seek to a constant offset from a record start or an anchor? BLOCKER — records carry variable-length regions, so this passes on day-0 data and returns wrong fields forever after. Parsing must be SEQUENTIAL. (2) GROUND TRUTH: is every newly-claimed field validated against players.csv or another independent source, with the check RUNNABLE as a test? An unvalidated field map is 'unconfirmed' and must be labelled so, not asserted. (3) THE GAME IS READ-ONLY: does any code path open a save file for writing, or write anywhere under the install or saved-games directories? BLOCKER (ADR 0001) — a Challenge Mode save carries an integrity hash that one write destroys irreversibly. (4) VERSION GUARD: does the parser check the header version byte (0x19 = OOTP 25) and REFUSE rather than misparse an unrecognized one? A patched game silently invalidates the field map. (5) SNAPSHOT IMMUTABILITY: is a landed snapshot ever mutated or overwritten in place? It is the only re-derivable copy of a sim date. (6) NO GAME DATA IN GIT: does any fixture embed OOTP's shipped data rather than our own derived observation (ADR 0006)? Ground each with file:line.` },
  'warehouse': { key: 'warehouse', schema: 'findings', mandate: `SPECIALIST — WAREHOUSE & MODELING (transform/ or warehouse loading touched). (1) GRAIN DECLARED AND PROVEN: does every model state its grain in prose AND enforce it with a uniqueness test whose columns AGREE with the prose? A grain claimed but not tested is a grain that will quietly break — and 'player per snapshot' vs 'player per team-stint per snapshot' differ exactly when a mid-season trade happens. (2) BRONZE FIDELITY: is bronze 1:1 with parser output — typing, casing, dedup only? Joins, filtering, and semantic renaming belong in silver where they can be documented. (3) SNAPSHOT SEMANTICS: is snapshot date part of the key everywhere it must be? Two snapshots of the same league MUST NOT collapse into one row, and a rebuild must not restate history it should have preserved. (4) KEY COVERAGE: does any join use the Lahman ID where the internal player_id was meant? Only ~1,712 of ~18,000 players carry a Lahman ID, so that join silently drops the fictional majority. (5) STRUCTURAL ABSENCE: are fields that a population genuinely lacks (minor leaguers, fictional players, day-0 stat blocks) handled as absent rather than averaged as zero? (6) LAYER PROMOTION: does a layer that fails its tests still feed the next? Ground each with file:line.` },
  'builder': { key: 'builder', schema: 'findings', mandate: `SPECIALIST — DATASET BUILDER (build/ or datasets/ touched — the STATIC reference pattern, ADR 0005). (1) RIGHT PATTERN: does this artifact actually belong here? The rule is 'does it change when the league is simulated?' — No means builder + datasets/; Yes means parser + dbt. A fact snapshot smuggled in as reference data will serve stale values forever. (2) RESOLVE BY NAME: does every consumer resolve through datasets/manifest.json rather than a literal path or a parents[N] walk? Is the new dataset registered with its provenance? (3) NO GAME DATA IN GIT: does the builder OUTPUT contain OOTP's shipped data, or only our derived observations (ADR 0006)? Copying players.csv into datasets/ is a BLOCKER; deriving a field-offset map from it is exactly right. (4) EPISTEMICS: does any code or doc assert a source's shape NOBODY has verified? Label it and make it a task. (5) TESTS AGAINST FIXTURES: do the builder's tests run against a committed trimmed payload rather than requiring a local game install? A test needing the install belongs behind the 'gamedata' marker, which CI excludes. Ground each with file:line.` },
  'skill-quality': { key: 'skill-quality', schema: 'findings', mandate: `SPECIALIST — SKILL QUALITY (.claude/skills touched; the feature is or edits a skill). (1) Does SKILL.md have valid frontmatter (name + a trigger-rich description), and does the DESCRIPTION match what the skill now does — a drifted description is a triggering bug? (2) Progressive disclosure — is the body reasonably scoped, with heavy logic in a sibling script rather than inlined? (3) Is the skill registered where the repo expects: CLAUDE.md "How to help", and — for a pipeline skill — the appropriate track README (requests/feature-requests/README.md, requests/bugfix-requests/README.md, or requests/data-incidents/README.md)? (4) Does it honor the conventions: read-only-git subagents, resolve-by-name, agents-never-commit? (5) Does any residual text still describe a SIBLING project rather than this one — these skills were ported, and a stale reference to another repo's roadmap, tracks, or domain is a real finding? (6) Do its relative links resolve? tests/test_doc_links.py is the mechanical check — RUN it. Flag each with the file:line.` },
  'infra-cost': { key: 'infra-cost', schema: 'findings', mandate: `SPECIALIST — CI, SECRETS & REPO HYGIENE (CI or project config touched). (1) SECRETS: this repo is PUBLIC. Does the diff introduce any credential, token, account id, personal email, or machine-specific absolute path in a tracked file? Check that new config reads from env vars rather than literals and that .env stays gitignored. A leaked secret is a BLOCKER. (2) GAME DATA: does the diff track any OOTP file — players.csv, a .dat, an .xml reference file, a save snapshot, an export? BLOCKER (ADR 0006): that data is Out of the Park Developments' IP and must never enter this repo. tests/test_no_leaks.py checks both this and the paths — RUN it. (3) GITIGNORE INVARIANTS: var/ must stay ignored (snapshots are ~600MB each), and no new rule may un-ignore the game-data patterns. tests/test_repo_structure.py checks var/ — RUN it. (4) CI INTEGRITY: does the workflow actually FAIL on the condition it claims to check? A step that passes vacuously (an empty selection, a swallowed exit code, a skipped leg) is worse than no check. Does anything in CI require a local OOTP install? It must not — those tests belong behind the 'gamedata' marker. Read the workflow, not the step names. (5) BRANCH PROTECTION: if a CI job display name changed, was ops/branch-protection.json updated in the SAME commit? A rename silently makes PRs wait forever for a check that never reports. (6) REPRODUCIBILITY: is the lockfile updated alongside pyproject.toml? Ground each finding.` },
}
const AREA_TO_SPEC = {
  src: ['parser', 'warehouse'], transform: ['warehouse'],
  datasets: ['builder'], build: ['builder'], tests: ['parser'],
  skills: ['skill-quality'], ci: ['infra-cost'], config: ['infra-cost'], docs: [],
}
const specKeys = [...new Set(AREAS.flatMap(a => AREA_TO_SPEC[a] || []))]
const ROSTER = [...CORE, ...specKeys.map(k => SPEC_DEFS[k]).filter(Boolean)]

// ── Schemas ──────────────────────────────────────────────────────────────────
const FINDING_ITEM = { type: 'object', properties: {
  id: { type: 'string' }, title: { type: 'string' },
  severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit', 'question'] },
  confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  category: { type: 'string' },
  location: { type: 'string', description: 'a REAL repo file:line you checked, or the plan/diff element' },
  problem: { type: 'string' }, proposed_fix: { type: 'string' },
}, required: ['id', 'title', 'severity', 'confidence', 'category', 'location', 'problem', 'proposed_fix'] }

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: { lens_summary: { type: 'string' }, findings: { type: 'array', items: FINDING_ITEM } },
  required: ['lens_summary', 'findings'],
}

const CRITERION_ITEM = { type: 'object', properties: {
  id: { type: 'string' },
  criterion: { type: 'string', description: 'the acceptance criterion text' },
  source: { type: 'string', description: 'where it came from: scope, or plan-phase-<n>' },
  verdict: { type: 'string', enum: ['met', 'partial', 'unmet', 'not-verifiable'] },
  evidence: { type: 'string', description: 'the command output you saw, or the real file:line that proves it' },
  how_checked: { type: 'string', description: 'execution (what you ran) or static (what you read)' },
}, required: ['id', 'criterion', 'source', 'verdict', 'evidence', 'how_checked'] }

const ACCEPTANCE_SCHEMA = {
  type: 'object',
  properties: {
    lens_summary: { type: 'string' },
    criteria_results: { type: 'array', items: CRITERION_ITEM },
    findings: { type: 'array', items: FINDING_ITEM, description: 'acceptance problems beyond a single criterion (e.g. an undefined/untestable criterion)' },
  },
  required: ['lens_summary', 'criteria_results'],
}

// ---------- Phase 1: reviewers ----------
phase('Review')
log(`Reviewing "${SLUG}" — ${ROSTER.length} lenses (${CORE.length} core + ${specKeys.length} specialist: ${specKeys.join(', ') || 'none'}) over the uncommitted diff ...`)
const revRaw = await parallel(ROSTER.map(r => () => {
  const schema = r.schema === 'acceptance' ? ACCEPTANCE_SCHEMA : FINDINGS_SCHEMA
  const isStub = r.schema === 'acceptance' ? acceptanceIsStub : reviewIsStub
  return runChecked(
    `${SHARED}\n\n${r.mandate}\n\nRecord your output grounded in the actual diff/repo — every finding with severity, confidence, a real location, and a concrete proposed fix; do not pad with invented problems.`,
    { label: `review:${r.key}`, phase: 'Review', schema, effort: 'high' },
    isStub
  )
}))
const reviews = revRaw.map((c, i) => ({ key: ROSTER[i].key, schema: ROSTER[i].schema, ok: c.ok, attempts: c.attempts, ...(c.result || {}) }))
const okReviews = reviews.filter(r => r.ok)
const acceptanceReview = reviews.find(r => r.key === 'acceptance' && r.ok) || null
const auditorLedger = acceptanceReview ? (acceptanceReview.criteria_results || []) : []
const allFindings = okReviews.flatMap(r => (r.findings || []).map(f => ({ ...f, reviewer: r.key })))
log(`${okReviews.length}/${ROSTER.length} lenses returned; auditor enumerated ${auditorLedger.length} criteria; ${allFindings.length} findings raised.`)
if (!okReviews.length) return { error: 'all reviewers failed', reviews }

// ---------- Phase 2: verify (execution-grounded) ----------
// Independently confirm/refute the blocker+major findings, and re-derive the ledger.
// The findings are DEDUPED first, then location-grouped and packed into at most VERIFY_CAP batch
// agents; the ledger verifier stays a standalone agent outside the cap (it is the independent
// double-ledger cross-check, and the skill's Step-5 health check names it directly).
const VERIFY_BATCH_SCHEMA = {
  type: 'object',
  properties: {
    verdicts: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string', description: 'the FINDING ID exactly as given to you' },
      verdict: { type: 'string', enum: ['confirmed', 'refuted', 'inconclusive'] },
      evidence: { type: 'string', description: 'the actual output you saw / the file:line you read, FOR THIS FINDING' },
      ran: { type: 'string', description: 'exactly what you executed or inspected FOR THIS FINDING' },
    }, required: ['id', 'verdict', 'evidence', 'ran'] } },
  },
  required: ['verdicts'],
}
const LEDGER_VERIFY_SCHEMA = {
  type: 'object',
  properties: {
    lens_summary: { type: 'string' },
    criteria_results: { type: 'array', items: CRITERION_ITEM },
  },
  required: ['lens_summary', 'criteria_results'],
}

// ── Deterministic (LLM-free) dedupe of the blocker/major findings ──────────────
// Independent lenses routinely raise the SAME underlying defect from different angles; verifying it
// once per lens costs an agent apiece and adds no signal. Merge only WITHIN a normalized location,
// and only when the titles genuinely overlap — so two distinct bugs that merely share a file are
// never collapsed. Nothing is lost: the merged finding carries every raising reviewer and the
// originals' ids, and the meta-audit still receives all raw findings via the reviews.
function normLocation(s) {
  return String(s || '').toLowerCase().replace(/\\/g, '/').replace(/\s+/g, ' ')
    .replace(/[:#]\s*l?\d+(?:\s*[-–]\s*\d+)?\s*$/, '').trim()   // drop a trailing :line / :12-20
}
function titleTokens(s) {
  return new Set(String(s || '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim().split(' ').filter(w => w.length > 2))
}
function jaccard(a, b) {
  if (!a.size || !b.size) return 0
  let hit = 0
  for (const t of a) if (b.has(t)) hit++
  return hit / (a.size + b.size - hit)
}
const SEV_RANK = { blocker: 2, major: 1 }
function dedupeFindings(items) {
  const out = []
  for (const f of items) {
    const loc = normLocation(f.location)
    const toks = titleTokens(f.title)
    const hit = out.find(o => o._loc === loc && jaccard(o._toks, toks) >= 0.5)
    if (!hit) { out.push({ ...f, _loc: loc, _toks: toks, reviewers: [f.reviewer], merged_from: [f.id] }); continue }
    if ((SEV_RANK[f.severity] || 0) > (SEV_RANK[hit.severity] || 0)) hit.severity = f.severity   // keep the worst
    if (f.confidence === 'high') hit.confidence = 'high'
    if (!hit.reviewers.includes(f.reviewer)) hit.reviewers.push(f.reviewer)
    hit.merged_from.push(f.id)
  }
  return out.map(({ _loc, _toks, ...f }, i) => ({
    ...f,
    // Reviewer-assigned ids are only unique WITHIN a lens (two lenses both emit 'f1'), so stamp a
    // panel-unique id — the batch verdicts are keyed on it and a collision would cross-assign them.
    vid: `V${i + 1}`,
    ...(f.merged_from.length > 1
      ? { problem: `${f.problem}\n\n[merged duplicate: also raised by ${f.reviewers.join(', ')} as ${f.merged_from.join(', ')}]` }
      : {}),
  }))
}

// ── Location-grouped, capped bucketing ────────────────────────────────────────
// Findings at the same location go to the SAME verifier: it reads that file once, so the marginal
// cost of its 2nd..Nth finding there is near zero. Location groups are then packed largest-first
// into the emptiest bucket, which keeps the buckets balanced (wall-clock is the slowest bucket).
function bucketByLocation(items, cap) {
  const groups = new Map()
  for (const f of items) {
    const k = normLocation(f.location) || '(unlocated)'
    if (!groups.has(k)) groups.set(k, [])
    groups.get(k).push(f)
  }
  const ordered = [...groups.values()].sort((a, b) => b.length - a.length)
  const buckets = []
  for (const g of ordered) {
    if (buckets.length < cap) { buckets.push([...g]); continue }
    let smallest = 0
    for (let i = 1; i < buckets.length; i++) if (buckets[i].length < buckets[smallest].length) smallest = i
    buckets[smallest].push(...g)
  }
  return buckets
}

const blockerMajorRaw = allFindings.filter(f => f.severity === 'blocker' || f.severity === 'major')
const blockerMajor = dedupeFindings(blockerMajorRaw)
const dupesMerged = blockerMajorRaw.length - blockerMajor.length
const buckets = bucketByLocation(blockerMajor, VERIFY_CAP)
phase('Verify')
log(`Verifying ${blockerMajor.length} blocker/major findings (${dupesMerged} duplicate${dupesMerged === 1 ? '' : 's'} merged) by execution across ${buckets.length} batch verifier${buckets.length === 1 ? '' : 's'} (cap ${VERIFY_CAP}) + re-deriving the acceptance ledger independently ...`)

function verifyBatchPrompt(batch) {
  const list = batch.map(f => `--- FINDING ${f.vid} ---\nTITLE: ${f.title}\nSEVERITY: ${f.severity} (raised by: ${(f.reviewers || [f.reviewer]).join(', ')})\nLOCATION: ${f.location}\nPROBLEM: ${f.problem}\nPROPOSED FIX: ${f.proposed_fix}`).join('\n\n')
  return `${SHARED}\n\nYou are an INDEPENDENT VERIFIER. Other reviewers raised the ${batch.length} finding${batch.length === 1 ? '' : 's'} below. They were grouped for you because they touch the same area of the change, so you can ground yourself ONCE and then adjudicate each of them.\n\n${list}\n\nCONFIRM or REFUTE **EACH** finding, independently and adversarially, BY CHECKING THE ACTUAL CODE/BEHAVIOR — read each cited location, and where a claim is about behavior, RUN it (the test, the model build, the extractor against the triggering fixture) and read the output.\n\nADJUDICATE EACH ONE ON ITS OWN MERITS. These findings arrived together for cost reasons ONLY — they are not a set, and one of them being real is NO evidence that the next one is. Do not let a confirmed finding pull the others along with it, and do not batch-refute the remainder once you have dispatched the first. Every verdict needs its OWN evidence and its OWN 'ran': a batch whose rows all share one blob of evidence is rejected as a non-answer and the whole batch is wasted.\n\nDefault to 'inconclusive' for any finding you genuinely cannot determine: do NOT confirm one you could not reproduce, and do NOT refute one you could not actually check.\n\nReturn ONE verdict per finding, keyed by the FINDING ID exactly as given (${batch.map(f => f.vid).join(', ')}). Return a row for EVERY id — an id you omit is recorded as unverified and the finding it belongs to loses its check.`
}
const LEDGER_VERIFY_PROMPT = `${SHARED}\n\nYou are the INDEPENDENT ACCEPTANCE VERIFIER. Do NOT trust any other reviewer's ledger — build your OWN from scratch. Enumerate every acceptance criterion (the upstream artifact's — a scope's acceptance_criteria, OR an RCA's "red repro goes green + regression test left behind + no audit/test regresses" contract — plus each plan phase's acceptance) and verify each YOURSELF, preferring EXECUTION (run 'uv run pytest' / the domain core against a committed fixture; read the output). For each, return met / partial / unmet / not-verifiable with the evidence and what you ran. Where you genuinely cannot execute a check, say so honestly ('not-verifiable'). This independent ledger is cross-checked against the auditor's to catch a falsely-'met' criterion.`

const verifyThunks = buckets.map((b, i) => () => runChecked(verifyBatchPrompt(b), { label: `verify:b${i + 1}`, phase: 'Verify', schema: VERIFY_BATCH_SCHEMA, effort: 'high' }, verifyBatchIsStub))
verifyThunks.push(() => runChecked(LEDGER_VERIFY_PROMPT, { label: 'verify:ledger', phase: 'Verify', schema: LEDGER_VERIFY_SCHEMA, effort: 'high' }, ledgerIsStub))
const verRaw = await parallel(verifyThunks)
const verResults = verRaw.map(c => (c && c.ok) ? { ok: true, ...c.result } : { ok: false })
const batchResults = verResults.slice(0, buckets.length)   // same order as buckets
const ledgerRes = verResults[verResults.length - 1]

// Fold every surviving batch's verdicts into one vid -> verdict map. Batching means one dead agent
// takes a whole bucket's findings down with it, so report that honestly (with the count) rather
// than letting the findings quietly read as checked-and-clean.
const verdictByVid = new Map()
const verifyDegraded = []
batchResults.forEach((res, i) => {
  const n = buckets[i].length
  if (!res.ok) { verifyDegraded.push(`verify:b${i + 1} (${n} finding${n === 1 ? '' : 's'} left unverified)`); return }
  const returned = new Set()
  for (const v of (res.verdicts || [])) {
    if (!v || !v.id) continue
    returned.add(String(v.id))
    verdictByVid.set(String(v.id), v)
  }
  const missing = buckets[i].filter(f => !returned.has(String(f.vid)))
  if (missing.length) verifyDegraded.push(`verify:b${i + 1} (no verdict returned for ${missing.map(f => f.vid).join(', ')})`)
})
if (!ledgerRes || !ledgerRes.ok) verifyDegraded.push('verify:ledger')

const verifiedFindings = blockerMajor.map(f => {
  const v = verdictByVid.get(String(f.vid))
  return {
    ...f,
    verdict: v && v.verdict ? v.verdict : 'unverified',
    verify_evidence: v ? (v.evidence || '') : '',
    verify_ran: v ? (v.ran || '') : '',
  }
})
const verifierLedger = ledgerRes && ledgerRes.ok ? (ledgerRes.criteria_results || []) : []
const lowFindings = allFindings.filter(f => f.severity !== 'blocker' && f.severity !== 'major')
log(`Verified: ${verifiedFindings.filter(f => f.verdict === 'confirmed').length} confirmed, ${verifiedFindings.filter(f => f.verdict === 'refuted').length} refuted; independent ledger covers ${verifierLedger.length} criteria.`)

// ---------- Phase 3: synthesize + meta-audit ----------
const MERGE_SCHEMA = {
  type: 'object',
  properties: {
    summary: { type: 'string' },
    verdict: { type: 'string', enum: ['go', 'fix', 'no-go'], description: 'go = all core criteria met + no confirmed blocker; fix = confirmed blockers/unmet criteria to resolve; no-go = fundamentally off-plan' },
    verdict_rationale: { type: 'string' },
    acceptance_ledger: { type: 'array', items: { type: 'object', properties: {
      id: { type: 'string' }, criterion: { type: 'string' }, source: { type: 'string' },
      verdict: { type: 'string', enum: ['met', 'partial', 'unmet', 'not-verifiable'] },
      evidence: { type: 'string' },
      reconciliation: { type: 'string', description: 'note where the auditor and the independent verifier disagreed, and which you trust + why' },
    }, required: ['id', 'criterion', 'source', 'verdict', 'evidence'] } },
    confirmed_findings: { type: 'array', items: FINDING_ITEM, description: 'verify-confirmed blockers/majors + the minor/nit findings worth carrying; drop refuted ones (note them in summary)' },
    gated_decisions: { type: 'array', items: { type: 'object', properties: {
      question: { type: 'string' }, recommendation: { type: 'string' }, related: { type: 'array', items: { type: 'string' } },
    }, required: ['question', 'recommendation'] } },
  },
  required: ['summary', 'verdict', 'verdict_rationale', 'acceptance_ledger', 'confirmed_findings', 'gated_decisions'],
}

phase('Synthesize')
const mergeInput = `THE REVIEWERS' FINDINGS (JSON):\n${JSON.stringify(okReviews.map(r => ({ key: r.key, lens_summary: r.lens_summary, findings: r.findings || [], criteria_results: r.criteria_results || [] })), null, 1)}\n\nTHE INDEPENDENT VERIFY VERDICTS on the blocker/major findings (JSON):\n${JSON.stringify(verifiedFindings, null, 1)}\n\nTHE AUDITOR'S ACCEPTANCE LEDGER (JSON):\n${JSON.stringify(auditorLedger, null, 1)}\n\nTHE INDEPENDENT VERIFIER'S LEDGER (JSON):\n${JSON.stringify(verifierLedger, null, 1)}`
let synthDegraded = false
const mergeChecked = await runChecked(
  `${SHARED}\n\nYou are the SYNTHESIS agent. Reconcile the panel into ONE acceptance report.\n\n${mergeInput}\n\nProduce:\n1. ACCEPTANCE_LEDGER — one row per acceptance criterion, RECONCILING the auditor's verdict with the independent verifier's. Where they DISAGREE, trust the one with stronger EXECUTION evidence and say so in 'reconciliation'; a criterion only 'met' if the evidence actually shows it. If the auditor lens dropped, build the ledger from the verifier's. This is the spine.\n2. CONFIRMED_FINDINGS — keep blocker/major findings whose verify verdict is 'confirmed', plus 'inconclusive' or 'unverified' ones the raising reviewer held at HIGH confidence (a verifier that could not RUN the check does not clear a high-confidence blocker); DROP 'refuted' ones (name them in the summary). Carry the minor/nit/question findings as-is. Where you keep a finding at a different severity than the reviewer assigned (e.g. one lens said major, others blocker), say so in its body so the change is transparent, not a silent edit.\n3. VERDICT — 'go' only if every CORE-path acceptance criterion is met and no confirmed blocker remains; 'fix' if there are confirmed blockers or unmet/partial core criteria to resolve; 'no-go' if the implementation is fundamentally off-plan. Justify it against the evidence — a 'go' with an unmet core criterion or a confirmed blocker is dishonest.\n4. GATED_DECISIONS — only GENUINE judgment calls for the human (a plan deviation that might be intentional, a trade-off, an above-and-beyond fold-in), each with YOUR recommendation. Objective must-fixes are NOT gated decisions — they go in confirmed_findings to be applied.\nGround every claim; do not launder a refuted finding forward or inflate a 'met'.`,
  { label: 'synthesize', phase: 'Synthesize', schema: MERGE_SCHEMA, effort: 'high' },
  mergeIsStub
)
let merged = mergeChecked.result
if (!merged) {
  synthDegraded = true
  log('  synthesis failed — recovering (free-text best-effort + deterministic ledger assembly from the reviews/verify verdicts/ledgers)')
  let prose = null
  // NON-'synthesize' label: the synthesize label throws on a retry-cap condition, so reusing it re-throws the recovery.
  const ft = await safeAgent(`${SHARED}\n\nYou are the SYNTHESIS agent (free-text recovery).\n\n${SYNTH_FREETEXT_MANDATE}\n\n${mergeInput}`,
                             { label: 'synthesize:fallback', phase: 'Synthesize', effort: 'high' })
  if (typeof ft === 'string' && ft.trim().length > 40) prose = ft
  merged = assembleAcceptanceReport(okReviews, verifiedFindings, auditorLedger, verifierLedger, prose)
}

// The meta-audit audits the SYNTHESIS's reasoning; the degraded assembly deliberately has
// none (it's a deterministic union, not a synthesis), so SKIP it on the degraded path —
// recorded honestly as meta:skipped-degraded — rather than auditing a reasoning-free report
// as if it were a real synthesis.
let metaRes = null
let metaFindings = []
if (!synthDegraded) {
  const META_SCHEMA = FINDINGS_SCHEMA
  const metaChecked = await runChecked(
    `${SHARED}\n\nMETA-AUDIT — audit the SYNTHESIS, not the repo. You are given the reviewers' findings, the auditor + independent ledgers, the verify verdicts, and the MERGED report:\n\n${mergeInput}\n\nTHE MERGED REPORT (JSON):\n${JSON.stringify(merged, null, 1)}\n\nCheck and flag as findings: (a) DROPPED SIGNAL — did the merge drop a verify-CONFIRMED blocker/major, or a criterion a reviewer marked unmet, or quietly upgrade a 'partial'/'unmet' to 'met'? (b) COVERAGE GAP (completeness critic) — is any acceptance criterion verified by NOBODY (neither auditor nor independent verifier actually executed/located it), or any touched area missing its specialist lens? (c) VERDICT HONESTY — does go/fix/no-go match the evidence? (d) FALSE-CLEAN — any reviewer that returned no findings on a substantial diff without evidence it actually looked. Each finding with a location and a concrete fix.`,
    { label: 'meta', phase: 'Synthesize', schema: META_SCHEMA, effort: 'high' },
    reviewIsStub
  )
  metaRes = metaChecked.result
  metaFindings = metaRes ? (metaRes.findings || []).map(f => ({ ...f, reviewer: 'meta-audit' })) : []
}
const degraded = [
  ...reviews.filter(r => !r.ok).map(r => `review:${r.key}`),
  ...verifyDegraded,
  ...(synthDegraded ? ['synthesize:fallback', 'meta:skipped-degraded'] : (metaRes ? [] : ['meta-audit'])),
]
log(`Synthesis: verdict=${merged.verdict}; ${merged.confirmed_findings.length} confirmed findings; meta-audit raised ${metaFindings.length}${degraded.length ? ` (degraded: ${degraded.join(', ')})` : ''}.`)

const ledger = merged.acceptance_ledger || []
return {
  summary: merged.summary,
  verdict: merged.verdict,
  verdict_rationale: merged.verdict_rationale,
  acceptance_ledger: ledger,
  confirmed_findings: merged.confirmed_findings,
  gated_decisions: merged.gated_decisions,
  meta_findings: metaFindings,
  verified_findings: verifiedFindings,
  low_findings: lowFindings,
  auditor_ledger: auditorLedger,
  verifier_ledger: verifierLedger,
  reviewer_summaries: okReviews.map(r => ({ reviewer: r.key, summary: r.lens_summary })),
  roster: ROSTER.map(r => r.key),
  degraded_lenses: degraded,
  stats: {
    reviewers_ok: okReviews.length,
    reviewers_total: ROSTER.length,
    // verifiers_* count AGENTS (<= VERIFY_CAP batches + 1 ledger verifier), not findings —
    // findings_* below are what tell you whether every finding actually got adjudicated.
    verifiers_ok: verResults.filter(v => v.ok).length,
    verifiers_total: verResults.length,
    verify_batches: buckets.length,
    verify_cap: VERIFY_CAP,
    findings_blocker_major_raw: blockerMajorRaw.length,
    findings_blocker_major_deduped: blockerMajor.length,
    findings_unverified: verifiedFindings.filter(f => f.verdict === 'unverified').length,
    meta_ok: metaRes ? 1 : 0,
    criteria_total: ledger.length,
    criteria_met: ledger.filter(c => c.verdict === 'met').length,
    criteria_unmet: ledger.filter(c => c.verdict === 'unmet' || c.verdict === 'partial').length,
    criteria_unverifiable: ledger.filter(c => c.verdict === 'not-verifiable').length,
    confirmed_findings: merged.confirmed_findings.length,
    blockers: merged.confirmed_findings.filter(f => f.severity === 'blocker').length,
    majors: merged.confirmed_findings.filter(f => f.severity === 'major').length,
  },
}
