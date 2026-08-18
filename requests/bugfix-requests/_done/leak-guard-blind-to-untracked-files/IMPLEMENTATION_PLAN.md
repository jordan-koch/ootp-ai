> **Status:** planned · created 2026-08-17 · decided · next: implement

# Implementation Plan — Give the leak guard sight of files that are not yet staged

> **One-line goal:** the repo's only leak protection stops enumerating the git index and starts
> seeing files that exist · **Target component:** `tests/test_no_leaks.py` (both of its
> enumerations), with a regression module, a `.gitignore` tightening, and three prose corrections.

> **Every path in this document is repo-relative, and that is load-bearing.** The planning
> panel's own draft wrote all 24 of its citations as absolute drive paths, and the guard being
> fixed bans exactly that shape (`tests/test_no_leaks.py:24`) — the plan to fix the leak guard
> would have failed the leak guard. Both adversaries and the meta-audit raised it independently.
> `tests/test_no_leaks.py` also has **no fenced-code exemption** (§5 D3), so a banned string
> cannot be quoted here even inside a fence. Describe, never quote.

## 1. Onboarding — read these first

`tests/test_no_leaks.py` is the **only** leak protection in this public repo. `CLAUDE.md` names
it as the enforcement mechanism for ADR 0006, there are no git hooks, and no secret scanner
exists. It builds its candidate list by shelling out to `git ls-files`, which enumerates the
**index** — so a file that exists on disk but has not been staged is never opened, and none of
its patterns are ever applied to it. Its first possible warning arrives at `git add`, the moment
content becomes committable. It failed three times in one session on 2026-08-17 while the full
offline suite ran green.

| # | File | Why |
|---|---|---|
| 1 | `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/ROOT_CAUSE_ANALYSIS.md` | **The decided artifact — consume it, don't re-open it.** Verdict, the measured enumeration table, and the tiered fix posture whose gated block disposes the four directions. **Two of its statements are now known wrong and are corrected here, not inherited** — see §5 D6 |
| 2 | `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/BUGFIX_REQUEST.md` | Context only. Its Open Questions were all disposed by the RCA; do not re-litigate them |
| 3 | `tests/test_no_leaks.py` | The file being fixed. 117 lines carrying **two independent enumerations**: `tracked_text_files()` at `:31` (shelling out at `:33`) and `test_game_data_is_not_tracked()` at `:97` (shelling out at `:100`). Also `EXEMPT` `:16`, `EXEMPT_PREFIXES` `:18` (empty), `PATTERNS` `:24`, the `keep` suffix set `:39`, the exempt filter `:43`, and the **in-module call site at `:83`** |
| 4 | `tests/test_leak_guard_scope.py` | **The committed red repro and the acceptance contract.** 7 tests; `test_an_untracked_file_is_visible_to_the_leak_guard` at `:62` is the red one, the other six are counterweights a naive widening breaks. `untracked_file()` at `:38` is the fixture every new test reuses; `LEAK` at `:35` is assembled at runtime so the module never holds a literal banned string |
| 5 | `.gitignore` | What `--exclude-standard` actually reads, so it *is* the fix's exclusion set. Load-bearing: `*.lg/` at `:25` (directories only), and the two **later** negations `!datasets/**` at `:61` and `!tests/fixtures/**` at `:62` that punch holes through the game-data block, because git is last-match-wins |
| 6 | `pyproject.toml` | `addopts` at `:100` already carries `-q`. **A second `-q` on the command line removes the summary line**, which is how several earlier measurements in this repo came to be dot-counted and wrong. mypy is `strict` over `src` **and** `tests`; `gamedata` is the only declared marker and `--strict-markers` makes a second one a hard collection error |
| 7 | `.claude/agents/data-engineer.md` | **Decisive for how this is built.** Its repo-level deny set forbids the write-capable subagent from touching `tests/`, `.github/` and `.claude/` — 100% of this fix's targets. **Build on the main thread; do not spawn it.** |
| 8 | `.claude/agents/data-engineer-memory.md` | The entry at `:78-84` is a `measured` claim this fix **falsifies** — it teaches agents the guard is blind and to hand-run `PATTERNS` instead. Correcting it is part of landing the fix. Append-never-prune |
| 9 | `tests/test_doc_links.py` | The sibling guard and the counter-example: its `markdown_files()` uses `rglob` with a hand-written exclusion list and has always seen untracked files. Read it to see why the two diverged — and why this fix moves toward git's exclusion machinery rather than copying it |
| 10 | `.claude/skills/commit/SKILL.md` | Where §5 D8's ordering sentence lands (the manual eyeball at `:77`), and where the false `gitleaks` claim lives at `:78`. The hard rails are at `:212`, `:213` and `:231` — **not** in Step 4, which the panel's draft miscited |

## 2. Architecture map

Everything is `tests/`, one `.gitignore` line, and three prose corrections. No `src/`, no parser,
no dbt, no dataset, no save file. The parser conventions have no surface here and must not be
padded in.

**The one-line cause.** `tracked_text_files()` at `:31-48` runs `git ls-files` at `:33`, filters
out `EXEMPT`/`EXEMPT_PREFIXES` at `:43`, keeps a suffix set at `:39`, and returns paths. The
scan at `:83` then opens only what that returned. `git ls-files` lists the index; a new file is
absent from it; the patterns never run.

**The fix is the argv.** `git ls-files --cached --others --exclude-standard` is the canonical
"tracked plus untracked, minus ignored" form. Measured on this branch:

| Check | Result |
|---|---|
| Clean tree | identical set to `git ls-files` — the widening adds zero junk |
| With an untracked probe present | the probe **is** included |
| `.venv/`, `__pycache__/`, `node_modules/`, `var/` | **0 entries each** |
| A probe under `var/tmp/` | absent — `.gitignore` respected |
| `.env` | absent (gitignored); `.env.example` present (the `!` negation is honoured) |

**Two failure modes the widening makes live**, both measured and both handled in Phase 2:

- **Encoding.** Default `git ls-files` C-quotes a non-ASCII path, and the existing call at
  `:32-38` uses `text=True` with **no `encoding=`** — which on this machine decodes as
  **cp1252, not UTF-8**. Passing `-z` alone does *not* fix it; the decode has to be pinned.
  Otherwise a file with an accented name mojibakes, fails the `keep` suffix test at `:39`, and
  is dropped **silently** — one blind spot traded for a subtler one.
- **Deleted paths.** `--cached` still lists a tracked-but-deleted file, and `:86` would raise an
  uncaught `FileNotFoundError` where it currently catches only `UnicodeDecodeError`.

**The second enumeration is blind the same way**, and the holes are real rather than theoretical.
Measured with `git check-ignore --no-index`: `players.csv` and `x/players.dat` at the repo root
**are** ignored, but `tests/fixtures/players.csv`, `tests/fixtures/x.dat` and `datasets/x.dat`
are **not** — the `!` negations at `.gitignore:61-62` are later rules and git is last-match-wins.
A plain `foo.lg` **file** is not ignored either, because `*.lg/` at `:25` matches directories
only. So `test_game_data_is_not_tracked` is the only thing standing between this repo and a
committed game-data fixture, and it cannot see one until it is staged.

## 3. Phased implementation

Six phases, each ending at a `/commit`-gated checkpoint on a green local run. **Run pytest
without an extra `-q`** — `addopts` already carries one, and a second suppresses the count.

---

### Phase 0 — Baseline, on a genuinely clean tree

**Goal.** Capture the numbers first, so every later "it moved" is a measured delta.

**Steps.**
1. **Confirm the tree is clean.** *This phase's first job, because the panel's own re-measurement
   was taken on a dirty tree and its "identical set" arithmetic was therefore unverifiable.* If
   the first-sight baseball artifacts are still uncommitted, land them first or stash nothing —
   just record what is outstanding and account for it.
2. Record `git branch --show-current` and `git rev-parse --short HEAD`.
3. `uv run pytest -m "not gamedata" --tb=no` — **no extra `-q`**. Baseline measured 2026-08-17:
   **`1 failed, 196 passed, 62 deselected`**. The single failure is the repro at
   `tests/test_leak_guard_scope.py:62`.
4. Record `git ls-files | Measure-Object` and the same for
   `git ls-files --cached --others --exclude-standard`. On a clean tree they must be equal.
5. `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, and the five `.mjs`
   skill guards — all green before anything changes.

**Acceptance.** The tally, both enumeration counts, branch and SHA written down. Tree clean.

**Commit note.** No commit.

---

### Phase 1 — The argv swap (RCA Minimal)

**Goal.** The committed red repro goes green **without touching `tests/test_leak_guard_scope.py`**.
That restraint is what makes "the repro passed on its own terms" a checkable claim.

**Steps.**
1. In `tests/test_no_leaks.py`, change the argv at `:33` from `["git", "ls-files"]` to
   `["git", "ls-files", "--cached", "--others", "--exclude-standard"]`.
2. Change nothing else — not `EXEMPT`, not `keep`, not the scan loop. Phase 2 owns the hardening.
3. Leave `test_game_data_is_not_tracked`'s call at `:100` alone; Phase 3 owns it.
4. **Do not edit `tests/test_leak_guard_scope.py`.**

**Acceptance.**
1. `uv run pytest tests/test_leak_guard_scope.py --tb=short` → **7 passed**. The red repro is
   green and all six counterweights still hold, which is the bugfix track's definition of done.
2. `uv run pytest -m "not gamedata" --tb=no` → **`197 passed, 62 deselected`**, zero failures.
3. `git diff --stat` lists exactly one file, and `tests/test_leak_guard_scope.py` is not in it.
4. On a clean tree, both enumerations still return the same count as Phase 0 — the widening
   added no junk.
5. ruff / format / mypy green; five `.mjs` guards still exit 0.

**Commit note.** `/commit`. **This is the commit that satisfies the acceptance contract**;
everything after it is hardening and hygiene. Suggested subject: *"Let the leak guard see files
that are not yet staged."*

---

### Phase 2 — Harden the widened enumeration (bundled per §5 D7)

**Goal.** Close the two failure modes the widening makes live, before either can be mistaken for
the guard working.

**Steps.**
1. Extract a small helper — `git_paths(*args: str) -> list[str]` — used by **both** enumerations.
   Full annotations; mypy is strict over `tests/`.
2. Pass `-z` so git emits NUL-separated raw bytes and never C-quotes.
3. **Pin the decode explicitly.** Do not rely on `text=True`: capture bytes and
   `decode("utf-8", errors="surrogateescape")`, or pass `encoding="utf-8"`. On this machine the
   default is cp1252, so `-z` alone leaves the bug in place with a different shape. **Verify by
   measurement, not by reading** — an adversary confirmed the cp1252 default here.
4. Split on `\0` and drop the trailing empty element.
5. Guard the read at `:86`: skip a path that is not a regular file, so a tracked-but-deleted
   entry cannot raise `FileNotFoundError`. Catch it **narrowly** — a bare `except Exception`
   would re-create silent blindness.
6. Add regression tests to `tests/test_leak_guard_scope.py`, reusing `untracked_file()` at `:38`:
   a **nested** untracked directory (the actual shape of all three real leaks — none was at the
   repo root); a non-ASCII filename; a tracked-but-deleted path; a file whose suffix is outside
   `keep`; and the trailing-NUL edge.

**Acceptance.**
1. All new tests green, and the seven pre-existing ones unchanged.
2. **Prove the encoding fix bites:** create a probe with a non-ASCII name containing a banned
   string, confirm it is reported. Then temporarily revert to `text=True` with no encoding,
   confirm it is **silently missed**, and restore. A guard that has not been seen to fail here
   has not been tested here.
3. `uv run pytest -m "not gamedata" --tb=no` green with the new count recorded.
4. ruff / format / mypy green.

**Commit note.** `/commit`. Its own commit, so the bisect boundary a purist wants survives.

---

### Phase 3 — The second enumeration, and the `.gitignore` hole (per §5 D1, D2)

**Goal.** `test_game_data_is_not_tracked` stops being blind in exactly the same way, and the
measured `.gitignore` holes stop being reachable.

**Steps.**
1. Route `:100` through `git_paths("--cached", "--others", "--exclude-standard")`.
2. **Extract a seam.** The test currently computes `offenders` inline and asserts on it, so there
   is nothing for a regression test to call. Extract `game_data_offenders() -> list[str]` (or
   equivalent) and have the test assert on it — mirroring how
   `tests/test_leak_guard_scope.py` asserts against `tracked_text_files()`.
3. Tighten `.gitignore:25` so a plain `*.lg` **file** is ignored as well as a `*.lg/` directory.
   Strictly a tightening — the directory case is already covered.
4. Regression tests: an untracked `.dat` probe under `tests/fixtures/` **is** reported as an
   offender; a probe under `var/tmp/` is **not**; and a plain `.lg` file is now ignored.
5. **Comment the measurement in the source**, naming the three paths that are not ignored and
   why (`.gitignore:61-62` are later negations, last-match-wins), so the next reader does not
   "simplify" the widening away.

**Acceptance.**
1. The new tests green; `git check-ignore --no-index` confirms the `.lg` tightening.
2. Full suite green; ruff / format / mypy green.
3. The source comment names the three measured holes.

**Commit note.** `/commit`. Suggested subject: *"Widen the game-data guard too, and close the
plain-`.lg` hole."*

---

### Phase 4 — Rename, and correct the memory entry (per §5 D4)

**Goal.** A function called `tracked_*` that scans untracked files re-arms the very argument the
RCA rejected — that a guard's narrow self-description is the authority on its scope. The next
agent would read the name, conclude the widening was a mistake, and narrow it back.

**Steps.**
1. Rename `tracked_text_files` at `:31` to something scope-accurate (`scannable_text_files` or
   similar).
2. Update **four** call sites, not three: `tests/test_no_leaks.py:83` — the in-module one the
   panel's draft missed — plus `tests/test_leak_guard_scope.py:71`, `:88` and `:99`.
3. **Every assertion message stays byte-identical.** The rename must not launder a weakened test.
4. Append a correcting entry to `.claude/agents/data-engineer-memory.md`. The entry at `:78-84`
   is `measured` and now false: it tells agents the guard cannot see new files and to hand-run
   `PATTERNS` instead. Append-never-prune; carry an epistemic label; state what changed and when.

**Acceptance.**
1. `git grep -n 'tracked_text_files' -- tests/` returns **zero hits**. *Scoped to `tests/`
   deliberately: the identifier also appears across `requests/` artifacts — the RCA, this plan,
   the panel trail — which are historical records this plan may not rewrite. The panel's draft
   asked for a repo-wide zero and that is unsatisfiable; ~24 hits exist.*
2. Full suite green with messages unchanged; mypy green.
3. `uv run pytest tests/test_agent_contract.py` green — the appended memory entry carries a
   valid epistemic label.

**Commit note.** `/commit`. Expect the doc gate to trigger on the memory file appearing in the
staged diff — that trigger is by design.

---

### Phase 5 — The three prose corrections (per §5 D5, D6, D8)

**Goal.** Nothing in the repo still teaches a workaround for a defect that is now fixed.

**Steps.**
1. **`/commit`'s ordering sentence** (RCA direction (d), reinterpreted per §5 D8). Replace the
   manual eyeball at `.claude/skills/commit/SKILL.md:77` with a concrete
   `uv run pytest tests/test_no_leaks.py` **after** staging. One sentence, not a restructure —
   Step 2 is already the skill's longest, and a gate people route around is worse than a light one.
2. **first-sight's two stale lines** (§5 D5, operator-disposed **yes**). Correct
   `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md` at `:757` (risk 15, *"the leak
   guard is blind to unstaged files"*) and `:561`. Mark them as amendments with today's date,
   following that document's own dated-amendment convention — do not delete the history.
3. **The second `gitleaks` promise.** Add one line to
   `requests/bugfix-requests/port-residue-sweep/BUGFIX_REQUEST.md` recording that the false claim
   appears **twice** — `.claude/skills/commit/SKILL.md:78` and
   `.claude/skills/update-docs/SKILL.md:25`. **Do not fix either occurrence here**; that request
   owns them. One finding, one tracker.

**Acceptance.**
1. `git grep -n 'gitleaks' -- .claude/` still returns both occurrences, untouched.
2. first-sight's plan no longer instructs a reader to work around this defect.
3. `uv run pytest tests/test_doc_links.py tests/test_skill_references.py` green.

**Commit note.** `/commit`.

---

### Phase 6 — Record and close

**Goal.** The paper trail matches what landed, and the one direction this fix deliberately does
**not** take is filed rather than evaporating.

**Steps.**
1. Write `IMPLEMENTATION_REPORT.md` in this directory: the acceptance ledger, the before/after
   baseline, and the encoding demonstration from Phase 2 pasted verbatim.
2. Advance this request's Index row and artifact statuses to the track's terminal word, and move
   the directory into `_done/` with the Index link repointed. **Expect the bare-token scan to
   name every stale reference** — that is the archive workflow working, not a problem.
3. **File the secret scanner as a feature request.** The RCA routes direction (c) to the feature
   track and the meta-audit caught that the draft carried only the negative half — so closing
   without filing loses it. **Nothing in this repo scans for credentials at all**; the patterns
   cover machine paths, home directories and email addresses only.
4. State what stays open: the `gitleaks` prose (owned by `port-residue-sweep`), and the fence
   exemption refused in §5 D3.

**Acceptance.** Report written; statuses and Index agree; the feature request exists; full local
gate green.

**Commit note.** `/commit`, then stop. Opening the PR is the operator's.

## 4. Testing & verification

**The acceptance contract is the bugfix track's** — the red repro goes green, a regression test
is left behind, nothing else regresses. Concretely: `1 failed, 196 passed` becomes `197 passed`
at Phase 1, then grows as Phases 2–3 add tests.

**Every guard this plan ships or widens must be *seen to fail*.** Phase 2's encoding
demonstration is the sharpest: revert the decode, watch a non-ASCII probe be silently missed,
restore. A widened guard that has never been observed dropping a file is exactly the
unfalsified-confidence this request exists to end.

**Measurement hygiene.** Run pytest **without an extra `-q`**. `addopts` at `pyproject.toml:100`
already carries one, and a second removes the summary line — several counts reported earlier in
this repo were dot-counted from progress output and were wrong as a result.

## 5. Decisions

**D1 — The second enumeration is folded in.** *Operator, 2026-08-17.* On measurement, not
symmetry: `tests/fixtures/players.csv`, `tests/fixtures/x.dat` and `datasets/x.dat` are **not**
gitignored, so `test_game_data_is_not_tracked` is the only thing stopping a committed game-data
fixture — and it cannot see one until staged. Lands as its own commit (Phase 3).

**D2 — `.gitignore:25` is tightened to cover a plain `*.lg` file.** Accepted en bloc. Measured:
`foo.lg` as a file is not ignored today while `roster.lg/x.txt` is. Strictly a tightening, and
Phase 3 is what enforces it — an unenforced `.gitignore` line is a comment.

**D3 — No fenced-code exemption for the leak guard.** *Operator, 2026-08-17*, with all three
planners agreeing independently. A fence exemption in a **leak** guard is a channel for smuggling
a credential past it — not true of a link checker, which is why the sibling guard's opposite
choice is not an inconsistency. The cost is real and was paid four times today: the intake, the
RCA, this plan and the panel trail all had to describe banned strings rather than quote them.
**Record the refusal in a comment near `tests/test_no_leaks.py:16`** so it does not drift back.
The narrower alternative — adding the bugfix directory to `EXEMPT_PREFIXES` at `:18` — has the
same smuggling shape in a smaller box and is declined too.

**D4 — `tracked_text_files` is renamed**, accepted en bloc, in Phase 4 with byte-identical
assertion messages. Deferring it past Phase 1 keeps *"the repro went green untouched"* checkable.

**D5 — This fix may correct first-sight's live plan.** *Operator, 2026-08-17.* The panel
recommended flag-only, before the operator had already directed an amendment to that same
document earlier the same day. A live execution document teaching a workaround for a fixed
defect is the drift class this repo files bugs about. Corrections are marked as dated amendments,
not silent edits.

**D6 — Two RCA statements are corrected rather than inherited.** The RCA says `gitleaks` is
promised *once*; it is promised **twice** (`.claude/skills/commit/SKILL.md:78` and
`.claude/skills/update-docs/SKILL.md:25`), so the intake was right and the RCA's "correction" was
wrong. And the RCA says the repro is "not yet committed"; it landed in this branch's first
commit. Neither changes the verdict or the cause.

**D7 — The `-z` / encoding / `is_file` hardening is bundled**, *operator, 2026-08-17*, as its own
commit rather than a separate request. Both failure modes are **made live by the widening** and
both sit in the six lines the fix already touches. Splitting would mean filing a request whose
entire content is *"the fix we just shipped drops files with accented names"*.

**D8 — Direction (d) lands as one sentence, not a restructure.** Accepted en bloc, with the
reinterpretation stated: (d)'s literal words were *"stage before you verify"*, which after (a)
buys nothing for detection and nudges toward the `git add -A` habit the skill exists to forbid.
The value is a concrete command replacing a manual eyeball.

## 6. Risks & gotchas

| Risk | Mitigation |
|---|---|
| **`-z` alone looks like it fixes the encoding hole and does not** — `text=True` decodes cp1252 here | Phase 2 step 3 pins the decode and step 2 of its acceptance requires *watching* the unfixed version miss a file |
| **A bare `except` while adding the deleted-path guard** would restore silent blindness in a new place | Phase 2 step 5: catch narrowly |
| **The rename tempts a "while I'm here" assertion tweak** | Phase 4 step 3: messages byte-identical, full suite green |
| **Phase 4's grep acceptance is unsatisfiable if scoped repo-wide** — ~24 hits live in decided artifacts | Scoped to `tests/` with the reason stated in the criterion itself |
| **An extra `-q` hides the count**, which has already produced wrong numbers in this repo | Stated in §4 and in every acceptance criterion that reads a tally |
| **The panel's baseline was taken on a dirty tree** | Phase 0 step 1 makes tree-cleanliness the first check rather than an assumption |
| **Archiving in Phase 6 will break every reference to this directory** | Expected; the bare-token scan enumerates them. Budget a pass for it |
| **The write-capable subagent may not build any of this** — every target is in its deny set | Main thread only |

## 7. Files to touch (checklist)

- [ ] `tests/test_no_leaks.py` — argv `:33` (P1); `git_paths` + decode + `is_file` (P2); second enumeration `:100` + seam (P3); rename `:31` and call site `:83` (P4); the D3 refusal comment near `:16`
- [ ] `tests/test_leak_guard_scope.py` — **untouched in P1**; new regression tests in P2/P3; call sites `:71`, `:88`, `:99` renamed in P4
- [ ] `.gitignore` — `:25`, plain `*.lg` files (P3)
- [ ] `.claude/agents/data-engineer-memory.md` — **append** a correction to the entry at `:78-84` (P4)
- [ ] `.claude/skills/commit/SKILL.md` — the ordering sentence at `:77` (P5). **Not** the `gitleaks` line at `:78`
- [ ] `requests/feature-requests/first-sight/IMPLEMENTATION_PLAN.md` — `:757` and `:561`, as dated amendments (P5)
- [ ] `requests/bugfix-requests/port-residue-sweep/BUGFIX_REQUEST.md` — one line recording the second `gitleaks` occurrence (P5)
- [ ] `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/` — `IMPLEMENTATION_REPORT.md`, statuses, the `_done/` move (P6)
- [ ] a new feature request for the credential scanner (P6)
- [ ] **NOT** `.claude/skills/update-docs/SKILL.md` — its `gitleaks` claim belongs to `port-residue-sweep`

## 8. Conventions (bake these in)

- **Commits go through `/commit` only.** Never push `main` (`:231`), never force-push, never
  `--amend` (`:213`), never `--no-verify` (`:212`). **Agents never open the PR.**
- **The write-capable subagent may not build this** — `tests/`, `.github/` and `.claude/` are all
  in its deny set. Main thread.
- **Never write an absolute or drive-letter path into a tracked file.** This plan's own subject
  matter; the panel's draft violated it 24 times.
- **Describe banned strings, never quote them** — there is no fence exemption (D3).
- **No new pytest markers** — `--strict-markers` with `gamedata` as the only declared one.
- **mypy strict covers `tests/`** — annotate every new helper and test.
- The parser conventions (read-only game, sequential walking, `players.csv` ground truth,
  ADR 0006 data rules) **have no surface in this change** and must not be padded in.

## 9. Code-grounding verification

The two adversaries and the meta-audit returned **44 findings — 6 blockers, 13 majors** — against
a draft whose citations were largely absolute paths. Panel health: `planners_ok` 3,
`adversaries_ok` 2, `meta_audit_ok` 1, `degraded_lenses` empty. Corrections applied here:

| Cited in the draft | Verified / corrected |
|---|---|
| All 24 path citations, as absolute drive paths | **Corrected** — repo-relative throughout; the originals would have turned the guard red |
| "`-z` closes the non-ASCII hole" | **Corrected** — `text=True` decodes cp1252 on this machine; the decode must be pinned |
| Phase 4: "`grep -rn tracked_text_files .` returns zero hits" | **Corrected** — ~24 hits exist in decided artifacts; scoped to `tests/` |
| Rename touches "three call sites" | **Corrected** — four; `tests/test_no_leaks.py:83` was missed |
| Acceptance commands using `-q` | **Corrected** — `addopts` already carries `-q`; a second hides the count |
| Phase 3's regression tests assert against a helper | **Corrected** — no such seam exists; Phase 3 step 2 extracts one |
| "Clean tree, identical set" baseline | **Corrected** — measured on a dirty tree; Phase 0 now checks cleanliness first |
| Conventions citing the rails at Step 4 | **Corrected** — the rails are at `:212`, `:213`, `:231` |
| Phase 2 unconditional *and* gated; Phase 4 likewise | **Corrected** — both disposed in §5 (D7, D4) and now unconditional |
| Secret-scanner follow-up dropped at closure | **Corrected** — Phase 6 step 3 files it |
| RCA: "`gitleaks` promised once" | **Corrected** — twice (D6) |
| `.gitignore` negation behaviour; `*.lg/` matching directories only | **Verified** by `git check-ignore --no-index` |
| `tests/test_no_leaks.py` anchors `:16`, `:18`, `:24`, `:31`, `:33`, `:39`, `:43`, `:83`, `:97`, `:100` | **Verified** by direct read |

## References

- `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/ROOT_CAUSE_ANALYSIS.md` — the decided upstream artifact
- `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/reviews/plan-proposals.md` — the three planners, raw
- `requests/bugfix-requests/_done/leak-guard-blind-to-untracked-files/reviews/plan-adversarial.md` — 25 adversary + 19 meta-audit findings
- `requests/bugfix-requests/README.md` — the track contract and status grammar
- `.claude/agents/data-engineer.md` — the deny set that puts every path here on the main thread
