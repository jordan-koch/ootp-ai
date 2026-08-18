> **Status:** diagnosed · created 2026-08-17 · decided · next: plan

# Root Cause Analysis — The ported guards describe a repo that does not exist here

> **Joint diagnosis**, at the operator's direction: one analysis covering the port
> itself rather than two covering symptoms. The primary target is
> `verify_batching_guard.mjs`; `requests/bugfix-requests/_done/doc-link-guard-mismatch/` is
> in scope as the second instance and carries its own RCA for its own gated decision.
> That request's third Open Question — *"is the same drift present in the other ported
> guards?"* — is answered here: **yes, and a third instance turned up while writing this.**
>
> **Citation convention.** Every `file:line` below is a code span, never a Markdown
> link. `tests/test_doc_links.py` resolves relative link targets with no fence
> awareness and no line-suffix handling, so the ordinary shape would turn CI red — a
> defect this document is partly about. Working around it, not fixing it here.

## Verdict

**confirmed-bug** — and the load-bearing question is settled by experiment rather than
by argument: **the ported artifact is the wrong side, the code under test is correct.**
All six of the batching guard's failure lines follow from **one** cause, including the
under-merge/over-merge pair that reads like two. Needs the full track: the minimal fix
is two words, but the reason the defect was invisible is not, and the second instance
carries a genuine either-way decision.

## Reproduction (red)

`tests/test_skill_references.py` — two tests, both RED on today's tree, both offline, both
in CI's `-m "not gamedata"` selection. **Written before this document and not yet
committed** (agents don't commit; land it with this RCA).

```
uv run pytest tests/test_skill_references.py
```

```
FF
test_every_test_file_a_skill_names_exists
  AssertionError: skills name test files that do not exist in this repo:
    .claude/skills/commit/SKILL.md:104 -> tests/test_request_links.py
    .claude/skills/create-implementation-plan/SKILL.md:251 -> tests/test_request_links.py
    .claude/skills/diagnose-bug/SKILL.md:117 -> tests/test_extract_pagination.py
    .claude/skills/diagnose-bug/SKILL.md:176 -> tests/test_request_links.py
    .claude/skills/make-bugfix-request/SKILL.md:199 -> tests/test_request_links.py
    .claude/skills/make-feature-request/SKILL.md:246 -> tests/test_request_links.py
    .claude/skills/update-docs/SKILL.md:56 -> tests/test_request_links.py

test_the_batching_guard_is_keyed_by_lenses_the_panel_actually_defines
  AssertionError: the batching guard's fixture is keyed by lenses the panel does not
  define: ['data-contract', 'extraction']
    the panel's lenses are: ['acceptance', 'builder', 'correctness', 'edgecases',
    'fidelity', 'infra-cost', 'parser', 'skill-quality', 'warehouse']
```

**Both assertions are direction-independent** — this is deliberate. Each asserts only
that an artifact's references resolve against the repo it lives in, which must hold
whichever way the fix goes. Neither presumes the answer to the doc-link request's
"which side is wrong", so neither has to be rewritten once that is decided.

The original symptom reproduces unchanged and stays the human-readable check:
`node .claude/skills/implement-plan/tests/verify_batching_guard.mjs` → exit 1, the six
failure lines quoted in the request. *(measured 2026-08-17, Node v24.15.0, Windows 11)*

## Evidence (the cause)

### The batching guard: two fixture keys that name a sibling repo's lenses

`verify_batching_guard.mjs:40-64` keys its synthetic finding set by reviewer lens:
`fidelity`, `correctness`, `edgecases`, **`data-contract`**, **`extraction`**,
`skill-quality`. The stub agent at `:172` dispatches on the panel's real label —
`reviewFor(label.slice('review:'.length))` — and `reviewFor` at `:78` resolves the key
with `FINDINGS_BY_LENS[lensKey] || []`.

This repo's panel defines no such lenses. `acceptance_panel.js:196-202` names its
specialists `parser`, `warehouse`, `builder`, `skill-quality`, `infra-cost`, and
`:203-208` maps the guard's `touchedAreas: ['transform','src','skills']` to
**`warehouse`, `parser`, `skill-quality`**. `data-contract` and `extraction` are the
sibling repo's vocabulary; they were never renamed when the specialists were adapted to
this project's domain. The guard's own comment at `:150` still teaches the wrong names.

**The `|| []` is why nobody noticed.** An unknown key does not raise, does not warn, and
does not return undefined — it returns an empty review. The two lenses contribute
**3 of the fixture's 11 findings** (`data-contract` 2, `extraction` 1) and those three
vanish before dedupe ever runs.

Every failure line follows, in order:

| Guard's complaint | What actually happened |
|---|---|
| `raw=8, expected 11` | the 3 findings under unknown keys never entered the run |
| `deduped=7, expected 9` | 8 raw − 1 surviving merge |
| `expected 2 merged findings, got 1` | one of the two duplicate pairs had its partner in `data-contract` (`fact_player_game.sql:88`), so only the `writer.py:42` pair could merge |
| `over-merged land/writer.py — 2 distinct bugs expected, got 1` | **not an over-merge.** The second `writer.py` bug lived in `extraction` (`:59`) and was never raised. The panel merged nothing it shouldn't have |
| `verified_findings=7, expected 9` | the same 7 survivors, correctly adjudicated |
| `verifyCap: a tighter cap changed how many findings survived dedupe` | it did not; the assertion compares against the same unreachable 9 |

That resolves the request's Open Questions directly: **one bug, not two** — the
under-merge and the over-merge are the same missing lenses seen from two assertions;
the three missing raw findings are `extraction`'s one and `data-contract`'s two; and
`raw=8 vs 11` being upstream of everything else is exactly right.

**The decisive experiment.** Re-keying those two fixture entries to `warehouse` and
`parser` — **with `acceptance_panel.js` untouched** — turns the whole guard green:

```
[cap+dedupe] raw=11 deduped=9 batches=4/4 verifiers=5/5 unverified=0
[dead-batch] verifiers=4/5 unverified=3/9 note="verify:b1 (3 findings left unverified)"
[rubberstmp] b1Calls=2 verifiers=4/5 unverified=3
[verifyCap ] cap=2 batches=2 unverified=0/9
GREEN: verify batching stays under the cap, merges only true duplicates, groups by
location, adjudicates every finding against its own id, and degrades honestly ...
```

*(measured 2026-08-17; run from a scratchpad copy with the guard's `HERE` repointed at
the real skill directory, so the panel under test is the tracked one.)*

The panel's dedupe is independently correct on inspection, which is why it survives the
re-key: `acceptance_panel.js:298-301` normalizes away a trailing `:line`, but `:317`
additionally requires `jaccard(titleTokens) >= 0.5` before merging. `writer.py:42`
*"landed payload is overwritten instead of written once"* and `writer.py:60` *"no
checkpoint, so a failed backfill restarts from zero"* share a normalized location and
almost no title tokens, so they are kept apart — the exact property the guard accused it
of violating. **Fixing the panel to satisfy the guard as written would have renamed this
repo's `parser` and `warehouse` lenses into a sibling's vocabulary and, worse, loosened a
dedupe that was already right.** That is the outcome the request named as the worst
available, and it was one plausible reading away.

### The doc-link guard: the same class, a different mechanism

Confirmed as a genuine second instance, not a coincidence. Full analysis and its gated
decision live in `requests/bugfix-requests/_done/doc-link-guard-mismatch/ROOT_CAUSE_ANALYSIS.md`;
in brief:

- **Symptom A** — six skills name `tests/test_request_links.py`, which has never existed
  here. Enumerated in the red repro above. *(measured)*
- **Symptom B** — `tests/test_doc_links.py:10-33` implements exactly four exemptions
  (`http://`, `https://`, `mailto:`, `#`) plus an angle-bracket placeholder skip. The
  three the skills promise — fenced content, a `file.py:123` citation suffix, a `var/`
  target — are all absent. Note `:15` excludes `var/` from the files it *scans*, which is
  not the same thing as exempting `var/` as a link *target*. *(measured, by reading)*
- The skills also describe a scanner that reads **bare `requests/...` tokens**, not just
  Markdown link syntax. `test_doc_links.py` has no such capability at all — so this is a
  dropped check, not only a missing exemption. That answers that request's "one guard or
  two?" in favour of two.

### A third instance, found while writing this document

`diagnose-bug/SKILL.md:107` and `:150` instruct the RCA author to write the status word
**`root-cause`**. The track's contract at `requests/bugfix-requests/README.md:45` and
`commit/SKILL.md:133` both give the grammar as `intake → diagnosed → planned → fixed`.
Two artifacts against one, and the track README is the contract per
`requests/README.md:12`, so **this document uses `diagnosed`** — but the skill will keep
producing `root-cause` until it is corrected, and `/commit`'s doc gate matches Index rows
against these status headers.

`diagnose-bug/SKILL.md:117` is smaller and of the same kind: its worked example cites
`tests/test_extract_pagination.py::test_all_pages_landed` failing with *"expected 1230
games, got 1000"*. There is no pagination in a save-file parser, and 1,230 is an NBA
regular season. Sibling-repo residue in a template a cold agent copies from.

### The cause underneath all three

Nothing in this repo resolves a ported artifact's references against the repo it now
lives in. The skills arrived by adaptation, the adaptation was uneven, and **both failure
directions are silent**: a named file that does not exist fails only when an agent
follows the instruction literally, and an unknown fixture key fails as a miscount
attributed to the code under test. `CLAUDE.md`'s own note that the batching guard was
known-red is the record of the project stepping over it rather than resolving it.

The repro module is the first check of this class. It covers two token classes; it does
not cover the general case.

## Fix posture (tiered)

**Minimal** — makes the red repro green without regressing the baseline:

1. `verify_batching_guard.mjs:54` `'data-contract':` → `'warehouse':` and `:58`
   `extraction:` → `parser:`, plus the stale comment at `:150`. **Proven green above.**
   `acceptance_panel.js` is not touched.
2. Point the six `tests/test_request_links.py` references at the guard that exists —
   **but see the gated decision below; this is the one step that must not move first.**
3. Re-ground the `test_extract_pagination.py` example in this repo's domain.

**Root** — the minimal fix leaves the mechanism that hid it:

4. `reviewFor()` at `verify_batching_guard.mjs:78` must **fail loudly** on a key the
   panel does not define, rather than returning `[]`. Better still, derive the fixture's
   expected lens keys from `acceptance_panel.js` so the roster has one home — the same
   one-declaration-many-consumers shape the first-sight plan uses for its contracts.
   Without this, the next roster rename reproduces this bug exactly.
5. Settle the `root-cause` / `diagnosed` grammar in `diagnose-bug/SKILL.md` against the
   track README.

**Gated decision — for the plan stage, not for the fix** (this is the doc-link request's
first Open Question, and both requests are explicit that guessing it is the worst
outcome): does `tests/test_doc_links.py` grow the three promised exemptions plus the
bare-token scan, or do the six skills get corrected to describe the stricter guard that
exists? My recommendation is **extend the guard and keep its name**: each exemption is
correct on the merits here — stage-1 artifacts routinely forward-reference files later
stages create, `file.py:123` is this repo's dominant citation form (the entire
first-sight plan is written in it, and adopted code spans specifically to dodge this
defect), and `var/` is gitignored so its targets can never resolve in CI. Renaming the
guard to `test_request_links.py` would be wrong independently: it scans all Markdown, not
just `requests/`. **Recommendation, not a ruling** — it is the plan panel's to settle.

**Hardening** — worth considering, not assumed:

6. Generalise the repro from two token classes to every repo path a skill names.
7. Run the `.mjs` guards in CI. `ci.yml:37-49` has no node step today; GitHub's
   `ubuntu-latest` image ships node, so this is plausibly a one-line step — *unconfirmed*,
   and it should be measured rather than asserted.
8. Sweep the remaining ported artifacts for domain residue of the `1230 games` kind. Two
   instances found by accident in one sitting is weak evidence that a deliberate pass
   would find none.

## What stays open after the minimal fix

The batching guard goes green and stage 4's Verify phase becomes proven — but the
**doc-link guard's direction is undecided**, so `tests/test_doc_links.py` still rejects
content six skills promise is safe, and the code-span workaround stays load-bearing for
every artifact written until it lands. `requests/bugfix-requests/leak-guard-blind-to-untracked-files/`
is a separate defect and is untouched by any of this.
