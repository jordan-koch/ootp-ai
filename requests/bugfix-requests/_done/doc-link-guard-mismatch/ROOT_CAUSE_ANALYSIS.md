> **Status:** diagnosed · created 2026-08-17 · decided · next: plan

# Root Cause Analysis — The link guard the skills describe was never ported

> **Diagnosed jointly** with `requests/bugfix-requests/_done/verify-batching-guard-red-on-arrival/`,
> at the operator's direction: one analysis of the port rather than two of its symptoms.
> The shared class finding, the red repro and the third instance found along the way live
> in that request's `ROOT_CAUSE_ANALYSIS.md` and are not repeated here. This document
> carries what is specific to this defect — including its own gated decision, which is the
> one call in either request that a fix must not make on its own authority.
>
> **Citations are code spans, never links**, for the reason this document is about.

## Verdict

**confirmed-bug**, both symptoms, cause confirmed by reading. This request's third Open
Question — *"is the same drift present in the other ported guards?"* — is answered **yes**:
`verify_batching_guard.mjs` is the same class, and a third instance (a status-word
mismatch in `diagnose-bug/SKILL.md`) turned up while diagnosing. Needs the full track,
for the reason the request's Stage plan already gave: **which side is wrong is a real
decision here**, and unlike the batching guard it cannot be settled by experiment.

## Reproduction (red)

Symptom A is covered by `tests/test_skill_references.py::test_every_test_file_a_skill_names_exists`
— RED today, naming all six references plus one more. Written for the joint diagnosis,
offline, in CI's selection, and **direction-independent**: "a test file a skill names must
exist" holds whether the guard is renamed or the skills are corrected, so it needs no
rewrite once the decision below is made. Not yet committed.

**Symptom B has deliberately not been given a repro yet, and that is the finding.** A test
asserting *"a fenced link is exempt"* presumes the fix direction — it would be a correct
guard under one reading and a wrong one under the other. Writing it now would quietly
decide the gated call by making one answer cheaper to keep. It is authored at plan time,
against whichever contract is chosen. Until then symptom B reproduces by hand exactly as
the request records: a Markdown file carrying the three constructs turns
`uv run pytest tests/test_doc_links.py` red.

## Evidence (the cause)

**Symptom A — the named guard was never ported, under any name.** Six `SKILL.md` files
instruct the agent to run `tests/test_request_links.py`: `commit:104`,
`create-implementation-plan:251`, `diagnose-bug:176`, `make-bugfix-request:199`,
`make-feature-request:246`, `update-docs:56`. `tests/` holds eighteen modules and none is
that one. *(measured)*

**Symptom B — the guard that exists implements four exemptions and promises none of the
three.** `tests/test_doc_links.py` is 39 lines and its whole exemption logic is visible at
once:

- `:10` — `LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")`, one regex over the raw file text.
  There is no tokenizer and no fence state, so a link inside a ``` block is
  indistinguishable from a live one. **Fenced content cannot be exempt by construction**,
  which is why this is missing behaviour rather than a missing branch.
- `:11` — `SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")`. That is the complete
  list, plus the angle-bracket placeholder skip at `:28`.
- `:30` — `clean = target.split("#", 1)[0]`. A `#fragment` is stripped; a `:123` line
  suffix is not, so a cited line number stays part of the path and `Path.exists()` is
  asked about a file that cannot exist.
- `:15` — `"var" not in p.parts` excludes `var/` from the files **scanned**. It says
  nothing about `var/` as a link **target**, and those are different exemptions. The
  request is right that following the documented guidance produces a red build.

**A capability was dropped, not just exemptions.** The skills describe a scanner that
resolves bare `requests/...` tokens, not only Markdown link syntax — see this skill's own
"What good looks like". `test_doc_links.py` reads link syntax exclusively. So the answer to
*"one guard or two?"* is **two**: the upstream had a `requests/`-scoped token scanner with a
richer exemption set, and this repo has a differently-scoped Markdown link checker that
inherited the job without the contract. The reporter's non-binding hunch is confirmed.

**Scope check on the blast radius.** `test_doc_links.py` is a blocking CI check
(`ci.yml:46-49`), and the workaround is already load-bearing: the entire first-sight
`IMPLEMENTATION_PLAN.md` is written in code spans specifically to dodge this defect, and
says so at its head. Both RCAs in this diagnosis do the same. The defect is currently
shaping how every artifact in the repo is written.

## Fix posture (tiered)

**The gated decision comes first, because every tier below depends on it.** Do not let a
fix pick it up by implication.

> **Which repo do we want?** (a) Extend `tests/test_doc_links.py` to the promised contract
> — fence awareness, `file.py:123` suffixes, `var/` targets — and add the bare-token scan,
> then point the six references at it. (b) Correct the six skills to describe the stricter
> guard that exists, and drop the promises.
>
> **Recommendation: (a), keeping the current name.** Each exemption is correct on the
> merits here — a stage-1 artifact routinely forward-references files a later stage
> creates and needs a way to quote a dead target; `file.py:123` is this repo's dominant
> citation form; `var/` is gitignored, so those targets can never resolve in CI and a
> guard that demands they do is asking for the impossible. Renaming the guard to
> `test_request_links.py` would be wrong on its own terms — it scans all Markdown, not just
> `requests/`, so the ported name misdescribes it. **A recommendation, not a ruling.**

**Minimal**, under (a): the three exemptions plus the six reference corrections. Under (b):
the six skills' "What good looks like" sections lose three promises, and the references
still need correcting — so **step 2 is common to both readings** and is the only part safe
to do early.

**Root:** the bare-token scan is the dropped capability. Without it the guard still cannot
catch a dead `requests/...` pointer in prose, which is the failure the skills actually
describe — a dead pointer misleading the next stage silently.

**Hardening (gated):** generalise `tests/test_skill_references.py` from two token classes
to every repo path a skill names; and settle whether a fence-aware scan should also cover
`docs/` and `gm/`, which are written in the same citation style.

## What stays open

The direction above. Until it is decided, the code-span convention stays mandatory for
every artifact — cheap, but it is a workaround the repo has to remember, and the first
person to forget gets a red build for following the manual.
