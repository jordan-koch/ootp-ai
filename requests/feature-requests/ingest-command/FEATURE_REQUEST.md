> **Status:** scoped · created 2026-08-29 · open · next: plan

# Feature Request — An ingest command: the pipeline has no way to be run

## Problem / Motivation

**Nothing outside the test suite can put data in the warehouse.** The parse-and-land path
is built, proven and documented — and it has no caller but `pytest`.

Concretely, measured against the tree at `a78321e`:

1. **`ingest_save` and `land_snapshot` have no `__main__`.** `src/ootp_ai/` ships exactly
   two entry points, `reports/__main__.py` and `catalog/__main__.py`, and both **read** a
   landing that already exists. `reports render` resolves a triple and renders it; it
   creates nothing.
2. **The `-m gamedata` suite is the only caller.** `tests/fixtures/warehouse.py` wraps
   `land_snapshot`, and `tests/test_read_only.py` composes
   `parse_snapshot(ingest_save(...).snapshot)` by hand. The two universes currently in the
   warehouse were put there by running the tests.
3. **`ops/` holds no script either** — `branch-protection.json`, `mysql-bootstrap.sql` and
   a README. There is no shell-level alternative hiding outside the package.

The practical shape of the gap: on a fresh machine, after `uv sync` and the MySQL
bootstrap, **the only documented way to populate the warehouse is to run the gamedata test
suite** — and then `reports render` works. That is a test suite doing production work, and
it is now written down as such in [`README.md`](../../../README.md)'s setup section, which
is where it was found while truing the docs up in `first-sight` Phase 12.

Two costs, and the second is the one that matters:

- **The operator has no supported way to refresh the club.** Every future sim day needs a
  landing, and today that means remembering which test to run.
- **A test suite that is load-bearing stops being free to change.** The moment someone
  refactors `tests/fixtures/warehouse.py` for a test's convenience, they are editing the
  ingestion path, with nothing to tell them so. The repo already treats this class of
  confusion as a defect — [ADR 0002](../../../docs/decisions/0002-parse-binaries-not-export.md)
  bars a manual click from any automated path, and a manual `pytest` invocation is the
  same shape wearing different clothes.

**This was withheld deliberately, not forgotten**, which is why it is a request rather than
a bug. `src/ootp_ai/reports/__main__.py:1-11` records the rule: entry points are scarce and
patterned — *"Deliberately the only one. Phase 9 declined to give the differential a
`__main__` so that this would be the first, and the pattern it sets is the one every later
report follows."* Nothing failed here. The capability was never built.

## Desired Outcome

**The operator can land a save from the command line, and the test suite stops being the
ingestion path.**

"Done" looks like:

- A documented command takes a save and leaves a landed snapshot in the warehouse, printing
  the `(save_id, sim_date, ingest_seq)` triple it created — the same three facts
  `reports render` prints, so a landing and a render can be tied together in a
  `gm/decisions/` record afterwards.
- [`README.md`](../../../README.md)'s setup section names that command instead of
  documenting the gap, and a fresh clone can go from `uv sync` to a rendered roster without
  running `pytest`.
- `tests/fixtures/warehouse.py` calls the same path the operator does, rather than being
  the path.
- Re-landing an already-landed triple still refuses loudly, and a second look at an
  unchanged sim date still takes the next `ingest_seq`
  ([ADR 0021](../../../docs/decisions/0021-bronze-landing-is-append-only.md)). The command
  surfaces that behaviour; it does not soften it.

Observable signal: on a machine whose warehouse is empty, one documented command followed
by `reports render` produces a roster page.

## Rough Ideas (non-binding)

- **`reports/__main__.py` is the pattern to copy, and it says so itself** — resolve
  settings, resolve the target explicitly, act, print what it did. Following it is probably
  more valuable than any design decision here.
- **The three operations are already separable and that is deliberate.**
  `src/ootp_ai/ingest.py:10-12`: *"`ingest_save` still returns the empty shape. It snapshots
  and resolves provenance and stops there … parsing is a separate, more expensive act and
  the two are worth being able to do apart."* Whether the command mirrors that split or
  hides it is open.
- **`--save-id` should probably exist from day one.** `reports render` already defaults to
  the managed league and stays overridable so the disposable Challenge twin can be used for
  rehearsal (SD-20 sequences every filesystem-touching operation against the twin first).
  An ingest command has the same need, more sharply.

All non-binding.

## Scope Signals

- **In:** a command-line entry point that takes a save from disk to a landed bronze
  snapshot — snapshot, parse, land — and prints the triple it created; the `.env`-resolved
  target with an explicit override; `README.md`'s setup section updated to name it;
  `tests/fixtures/warehouse.py` re-pointed at whatever the operator runs, so the two cannot
  drift; the writer-allowlist entry the new module needs.
- **Explicitly out:**
  - **Rendering.** `reports render` exists and is the render entry point. This command
    lands; it does not draw. *(Operator's disposition at intake: "just landing".)*
  - **The sim-forward-and-re-land procedure, and the two-date proof.** Both are already
    claimed by [`incremental-loading`](../incremental-loading/). This request builds the
    vehicle; that one drives it.
  - **Scheduling, watching, or automating a run.** No daemon, no file watcher, no cron. The
    operator decides when a save is worth landing.
  - **Anything that writes to a save**
    ([ADR 0001](../../../docs/decisions/0001-read-only-no-write-back.md)). Permanent.
  - **Changing landing semantics.** Append-only, the refusal on a re-landed triple, and the
    `ingest_seq` allocation are settled
    ([ADR 0021](../../../docs/decisions/0021-bronze-landing-is-append-only.md)). This
    exposes them; it does not renegotiate them.
  - **A `[project.scripts]` console entry point.** `uv run python -m ootp_ai.<x>` is the
    established invocation for both existing commands; introducing a second convention is a
    decision this request has no reason to make.
- **Not now / later:** landing more than one save in a single invocation; a `--dry-run` that
  parses without landing (the library already separates these, so it may fall out for free —
  but it is not a goal); progress output for the ~2.2 s parse.

## Affected Area & Pointers

**Subsystem:** `src/ootp_ai/` — a new entry point over existing ingest and warehouse code —
plus `tests/` and `README.md`. **No parser change and no new landed data**: every byte this
moves is already read and already landed by code under test.

A cold scoping agent should open, in this order:

| # | File | Why |
|---|---|---|
| 1 | `src/ootp_ai/reports/__main__.py` | The pattern, and its docstring's rule that entry points are deliberate. 155 lines, argparse, one subcommand — the whole shape to match |
| 2 | `src/ootp_ai/ingest.py` `:436` | `ingest_save()` — snapshots and resolves provenance, then stops. Its docstring explains why that boundary exists |
| 3 | `src/ootp_ai/warehouse/load.py` `:195` | `land_snapshot()` — how a landing is claimed, retried and written, and where the append-only refusal lives |
| 4 | `tests/fixtures/warehouse.py` `:47` | The de facto current caller — what a test does today that the operator cannot |
| 5 | `tests/test_read_only.py` `:254` | Composes `parse_snapshot(ingest_save(...))` by hand, and carries the `WRITERS` allowlist at `:299-320` whose comment explains why a bare `__main__.py` was **not** allowlisted |
| 6 | [ADR 0021](../../../docs/decisions/0021-bronze-landing-is-append-only.md) | The semantics the command surfaces without changing |
| 7 | `requests/feature-requests/incremental-loading/FEATURE_REQUEST.md` | The downstream consumer, and the boundary this request stops at |

Also relevant: `first-sight`'s `IMPLEMENTATION_PLAN.md:275`, which instructs AC11 to *"run
the full pipeline entry point"* — language that assumed this existed. The test composes the
library calls instead, which is how the gap survived a fourteen-phase plan.

## Constraints / Non-negotiables

- **The game is read-only** ([ADR 0001](../../../docs/decisions/0001-read-only-no-write-back.md)).
  `tests/test_read_only.py` proves it by manifest diff, and this adds a caller that must
  stay inside that proof.
- **`snapshot.py` is the only module allowed to create a file**, enforced per-path by
  `WRITERS` in `tests/test_read_only.py`. Its comment records that allowlisting a bare
  `__main__.py` would have released every `__main__.py` in the tree, so a new entry point
  needs its own explicit entry — the same way `catalog/__main__.py` got one in Phase 11.
- **Bronze is append-only** ([ADR 0021](../../../docs/decisions/0021-bronze-landing-is-append-only.md)).
  No upsert, no fix-in-place, no `--force` that overwrites a triple.
- **No absolute path may reach a tracked file or a rendered artifact** (ADR 0006).
  `saved_games.dat` embeds a user-profile path per save, and an ingest run is the record
  most likely to be printed; `ingest.py:25-27` notes the type deliberately has nowhere to
  put one.
- **Every filesystem-touching operation runs against the disposable Challenge twin first**
  (SD-20), which makes the target override a safety feature rather than a convenience.
- **`uv run python -m ootp_ai.<package>`** is the established invocation.

## Open Questions for Scoping

1. **One command or three?** The library deliberately separates snapshot / parse / land,
   with a documented reason. A single `land` that does all three is what the operator wants
   to type; three subcommands are what the design suggests. A combined command with the
   split available underneath is a third answer, and the choice pins the operator-facing
   contract that `incremental-loading` will build a written procedure on.
2. **Where does it live?** `ootp_ai.ingest` is a module, not a package, so `python -m
   ootp_ai.ingest` cannot host a `__main__.py` without restructuring. Options: promote
   `ingest/` to a package, put the entry point under `warehouse/`, or add a top-level one.
   CLAUDE.md forbids speculative directories, so this needs deciding rather than defaulting.
3. **What does it do when the triple is already landed?** ADR 0021 says re-landing refuses
   and an unchanged date takes the next seq. Which of those is the *default* for an
   operator who just re-ran the command by habit? Refusing is safer; auto-allocating is what
   a second genuine look wants. Getting this backwards either blocks routine work or fills
   the warehouse with duplicate landings nobody meant to make.
4. **Does `tests/fixtures/warehouse.py` get re-pointed, and does anything then go
   untested?** The fixture exists partly to control `ingest_seq` and purge afterwards. If
   the CLI becomes the shared path, scoping should check that the fixture's extra powers do
   not quietly become production surface area.
5. **Is AC11's manifest-diff proof extended to cover the new entry point?** It currently
   brackets the library calls. If the operator's command is a different code path, the
   read-only proof should bracket *that* — otherwise the thing the operator actually runs is
   the one thing ADR 0001's guard never watched.

## Stage plan

**Full pipeline.** Two of the three hard triggers fire:

1. **Open Questions came out non-empty** — five, and question 3 alone decides an
   operator-facing default that is expensive to change once the procedure is written down.
2. **Explicitly out is filled**, so this trigger is *cleared*. It does not save the others.
3. **It touches something expensive to reverse.** The command becomes the operator's
   interface to the pipeline and the contract
   [`incremental-loading`](../incremental-loading/) writes its procedure against; it pins
   ADR 0021's append-only semantics into an operator-facing default; and it extends the
   `WRITERS` allowlist that ADR 0001's proof rests on.

No skip is available and none is proposed. The work is small — the diff is plausibly one
module and a README section — but "small diff, large decision surface" is exactly the case
[ADR 0008](../../../docs/decisions/0008-panels-by-default.md) puts the burden of proof on.
