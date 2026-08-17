<!-- handoff: v1 -->

## track

feature

## built

`src/ootp_ai/parser/teams.py` — the refusal is gone. Records are framed by a forward search
for nine zero bytes and `0x28` plus an ascending-team-id check; the head is read through the
cursor; each undecoded 1.5–60 KB body is crossed by `skip`ping a width `data.find` computed.
**The decoder inverts the drop-zero encoding** on the domain constraints the module docstring
sets out, narrows what survives against the file's own unambiguous records, and raises
`AmbiguousTeamRecord` otherwise. The signature is 5, 4 or 3 strings, decided by backtracking
against the three-ARGB-colour signature; `parent_team_id` is taken only where two records
reciprocate, never as "the first link below the top level".

`src/ootp_ai/parser/human_managers.py` — new: header, version guard, six-`u32` tail with
`record_count == 1` enforced, the zero pad counted rather than assumed, the `1234` sentinel
checked, then manager id, two name indices, date of birth, then the club — `inferred` as the
first of three consecutive slots. It ends at EOF (zero residual) and reports
`undecoded_bytes`. `snapshot.py` — five named files, `~46 MB` becomes `~55 MB`. `ingest.py` —
`_resolve_human_team` reads the **snapshot copy**, never the save. Memory: five entries.

## verified

| Check | Command and actual output |
|---|---|
| The decoder, against a source I did not write | `uv run pytest -m gamedata tests/test_parse_real_save.py -rA` → `PASSED …::test_every_parsed_team_matches_the_export_field_by_field`. All **259 of 259** records of the standard probe match the export on `abbr, nickname, logo_file_name, level, league_id, sub_league_id, city_id, park_id, nation_id, parent_team_id, human_team`, plus `city` and `historical_id` compared separately. Zero mismatches. |
| The 26 city-less records are the right 26 | same run → `PASSED …::test_exactly_the_minor_league_all_star_sides_carry_no_city_string` — count **and** membership. |
| Both club walks agree on all three saves | same run → `PASSED …::test_the_manager_file_and_the_team_flag_name_the_same_club` and `…::test_the_manager_file_alone_produces_boston_boston_chicago`. Scratch driver: `human club=[4] manager file=4` (managed), `[6]/6` (standard), `[4]/4` (challenge). No disagreement to report. |
| Offline suite | `uv run pytest -m "not gamedata"` → `151 passed, 44 deselected in 0.86s`. |
| Gamedata selector | the six-file selector from the brief → `4 failed, 33 passed, 1 skipped, 35 deselected in 1.64s`. **All four failures are test-side**; each is named under `could-not-do` with its one-line fix. |
| The tier is not an under-claim | `PASSED …test_byte_accounting.py::test_a_diagnostic_claim_is_not_an_under_claim`, `…::test_the_walk_stops_on_a_record_boundary_even_when_it_leaves_bytes`, `…::test_the_team_count_matches_the_export_on_the_only_save_that_has_one` (259). Residuals 1137 / 1137 / 2274 bytes against mean records of ~17.6 KB / ~17.6 KB / ~15.8 KB. |
| Challenge Mode does not change the record | `uv run pytest -m gamedata tests/test_cross_mode_format.py -rA` → 7 PASSED, including `test_the_same_walker_reads_teams_dat_in_both_modes` and `test_the_two_modes_differ_only_in_content_not_in_shape`. |
| Snapshot widening and provenance | `uv run pytest -m gamedata tests/test_snapshot_semantics.py -rA` → 4 PASSED incl. `…carries_the_whole_set` and `…is_the_size_the_measurement_predicts`; measured set size on the managed league `54,930,416` bytes. `uv run pytest -m gamedata tests/test_provenance.py` → `5 passed, 5 deselected in 0.16s`. |
| Fixed-offset ban, and ADR 0001 after a full walk of both new files | `uv run pytest tests/test_no_fixed_offsets.py` → `4 passed in 0.03s`. `uv run pytest -m gamedata tests/test_read_only.py` → `2 passed, 8 deselected in 39.80s` — zero mtime and zero digest differences under both roots. |
| Lint / format | `uv run ruff check .` → `All checks passed!` · `uv run ruff format --check .` → `105 files already formatted`. |
| Types | `uv run mypy` → `Found 3 errors in 2 files (checked 34 source files)`. **All three sit in `tests/`, all caused by `city: str \| None`, which the same test module set requires.** Detail under `could-not-do`. |
| Leak guard over paths `git ls-files` cannot see | imported `PATTERNS` from `tests/test_no_leaks.py`, scanned both parser modules, `snapshot.py`, `ingest.py`, this handoff and the memory file → `no matches`. |
| Determinism and cost | scratch driver: two walks of one buffer return equal records and equal residuals on all three saves, each in `0.01s`. `git status --porcelain` lists only allowlisted paths plus the pre-existing modifications. |

## assumed

- **`park_id` is never zero**, so it is always written — `measured` 259/259 in the export,
  range 1..198, and it is what makes a two-value run decidable. Unverifiable on the managed
  league; a club with no ballpark there would shift a run silently.
- **The first of the three club slots in `human_managers.dat` is `team_id`** — byte-identical
  in all three saves, so no oracle separates them; the walk refuses if they stop agreeing.
  **The `u8` flags before `historical_id` are all `0x01`** across 855 records; a one-character
  franchise code would be eaten by that rule, but it raises rather than misreads.
- The spec was silent on ground truth, so `ootp_truth_real` was the oracle throughout, via
  `connect_truth` (read-only). Nothing here touches ratings, so `players.csv` had nothing to
  bind on.

## surprised-me

- **The "five-string signature" is five strings only when all five are non-empty.** The probes
  drop the *city* on 26 records; the managed league drops the *logo* on **289**, so `.png`
  sniffing finds the logo on two saves of three and the count needs deciding structurally.
- **The organisation array is one field read from both ends.** Turning the integrity check
  into the decoder — keep only reciprocated links — fixed the direction, killed the two
  terminator artefacts (`1`, `257`), and reproduced the export's `parent_team_id` 199/199. It
  also killed "level 1 lists children, everything else lists a parent": the managed league has
  parented clubs eight levels deep, so that was probe-shaped, not a format rule.
- `saved_games.dat`'s display string is the club's **full name** (`Chicago Cubs`), not the
  city; Phase 4 recorded `Chicago` and built a test on it. And the four top-level All-Star
  records carry only **two** distinct abbreviations.

## could-not-do

**Four tests are wrong rather than unsatisfied.** I built nothing around them and edited
nothing in `tests/`. All four follow from fields the same test file pins.

1. `tests/test_byte_accounting.py:205` (`len(team.city)`) and
   `tests/test_parse_real_save.py:275-276` (`root in value`, `":" not in value` over a tuple
   containing `team.city`) use as a `str` the field `test_parse_teams_synthetic.py` requires
   to be `str | None`. They error at runtime on the 26 city-less records and are all three
   mypy errors. Fix: `team.city or ""` at both call sites.
2. `tests/test_parse_real_save.py:166` — `len(abbrs - MLB_ABBREVIATIONS) == 4`. The four
   All-Star sides share two abbreviations, so the difference is `{'AL', 'NL'}`. The parse is
   right: `abbr` matches the export on all 259 rows. Fix: `== 2`, or compare a list.
3. `tests/test_parse_real_save.py:303` — `entry.human_team_name == home.city`. Measured, the
   index holds `Boston Red Sox` / `Boston Red Sox` / `Chicago Cubs` — the **full name** — and
   it equals `home.full_name` exactly in all three saves. Fix: compare `full_name`; the
   docstring's premise ("Chicago is both the Cubs and the White Sox") no longer holds.

No destructive git needed, nothing written outside the allowlist, scratch in the session
scratchpad, and no snapshot taken outside `tmp_path`.

## docs-delta

For `/update-docs` to route into `docs/data-access.md` §4, with proposed labels.

- **`measured`, widening the existing `verified` signature claim** — a team record omits a
  field when its value is falsy, **strings included**: four strings on the 26 minor-league
  All-Star sides of each probe (no city) and **289 managed-league records with no logo**.
- **`measured`** — the head is `u32 team_id`; the signature; the drop-zero run `[city_id,
  park_id, league_id, sub_league_id, nation_id, human]`; **exactly three** `u32` ARGB colours
  with alpha `0xff`; `u32 level` (never zero); a drop-zero `u32` array of organisation links;
  a drop-zero `u8` run whose every written byte is `0x01`; then `historical_id`. Records are
  preceded by nine zero bytes and `0x28`, run in ascending `team_id` order, and were checked
  field-by-field against the export on 259 of 259. `park_id` and `league_id` are never zero
  and `sub_league_id` and the human flag are 0/1 — the facts that make it invertible at all.
- **`measured`** — the link array holds a club's *affiliates* when it is the parent and its
  *parent* when it is the affiliate, in the same slot, so the relation is only decidable where
  two records reciprocate; the managed league has parented clubs at level 8. Separately,
  correcting the Phase 4 note: `saved_games.dat`'s human-club display string is the club's
  **full name** (`Chicago Cubs`), not its city.
- **`measured`** — `human_managers.dat` is the shared header, a six-`u32` tail declaring
  `record_count = 1`, a 46-byte zero pad, the `1234` sentinel, then `u32` manager id, two
  `u32` name indices into `names.dat`, and a `u8/u8/u16` date of birth (the export's
  `Jim Smith`, born 1977-03-15, reads 7632 / 26051 and 15/3/1977). The three consecutive
  `u32`s holding the managed club are the **only** position in any of the three files where
  three `u32`s in a row share a non-zero value, at every bound from 999 to 2**24; which of
  `team_id` / `last_team_id` / `organization_id` each is stays **`inferred`**.

## still-open

- **`world.dat` is untouched** — 5b, as instructed. It is in `SNAPSHOT_FILES` so the snapshot
  stops changing shape; nothing parses it.
- **~85% of `teams.dat` is still undecoded** — the record body, crossed by a frame search;
  `TIER_RATIONALE` says so in those words. The best lead for a strict walk is the ~344-byte
  bit-packed preamble between the header tail and the first record, constant per file type.
- **`human_managers.dat` leaves 634–658 undecoded bytes of 835–859.** The walk reaches EOF so
  the residual is zero, but the scalar run (age, nation, weight, height, personality) is
  unmapped. The spec asked to "account for completely"; what I can defend is "consume
  completely, decode the head", and the docstring says that rather than implying more.
- **Ambiguity read small** (Escalation case 3): one `human_team` flag rather than `human_team`
  plus `human_id`; one `team_id` rather than three club fields; no second franchise code. A
  save with two human managers settles all three at once.
- Nothing outward-facing was produced, so there is nothing for the operator to run.
