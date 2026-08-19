<!-- handoff: v1 -->

# Phase 6b, job 1 of 2 — the `players.dat` identity tail

## track

feature

## built

**Three of the five requested fields land `verified` — `bats`, `throws` and
`historical_id` (the AC8 priority) — each exact on every `retired = 0` export row.
`position` and `role` do not land**, per the exact-or-nothing standard; what was measured
about them is recorded under `could-not-do` and in the field map so the next attempt
starts from evidence rather than zero.

`src/ootp_ai/parser/players.py` — the walk now continues past the club-assignment run
through a decoded **identity tail**. The blocker the spec named — "the undecoded variable
region between the anchors" — turned out to be *presence-mask-governed all the way down*:

- **The mask at record+56 was only decoded at bit 0 (`free_agent`); its bits 2–7 govern
  six optional fields, written in ascending bit order**: nickname `names.dat` index
  (`u32`), `second_nation_id` (`u32`), `language_ids0` (`u16`), `language_ids1` (`u16`),
  `bats` (`u8`), `throws` (`u8`).
- **`bats` and `throws` are drop-DEFAULT, not drop-zero** — the writer elides the
  majority value 1 (right-handed), so bit clear means the value *is* 1 and a written byte
  is 2/3 (`bats`) or 2 (`throws`). This is why every drop-zero sweep missed them and why
  the prior brute force plateaued at a coincidence rate.
- **The unclassified byte at record+57 is a third mask** (values 2, 6, 14, 34, 38
  decompose on bits): bit 1 is set on all 58,200 records of all three saves (unknown
  meaning, required as a sentinel), bit 2 governs one unclassified `u8` (withheld), bit 5
  a `u32` matching `loan_league_id`, bit 3 no bytes at all.
- **Then `historical_id` and `historical_team_id` follow back to back** as
  length-prefixed strings — empty-string, not absent, for the fictional ~90%.

The tail is **validated by lookahead before the cursor consumes it** (`_scan_tail`,
decide-then-consume, the `teams.py` pattern, everything through the ADR 0020 seam — no
new seam helper was needed). A record whose tail fails any check — unknown mask bit,
written value outside its measured set, non-ASCII string — is consumed only through the
assignment run, reports `bats`/`throws`/`historical_id` as `None`, and is counted in the
new `PlayersFile.undecoded_tails`. That count is **zero on every save on disk**; nonzero
means a format change and the landing gate must refuse. This design is also what keeps
the offline suite green without touching the deny-set fixture: every existing synthetic
record deterministically takes the `None` path (its record+57 byte lacks sentinel bit 1).

`src/ootp_ai/contracts/field_map.toml` — three new `verified` field entries (`bats`,
`throws`, `historical_id`); seven crossed-and-classified entries for the fields the walk
must decode but deliberately does not expose (nickname index, `second_nation_id`, the two
language ids, the unclassified tail byte, `loan_league_id`, `historical_team_id`); the
record+57 entry rewritten from "unclassified byte" to the decoded `tail_mask`; the
`historical_id` withheld entry retired; the `position, role` withheld entry rewritten with
the full measurement trail.

`.claude/agents/data-engineer-memory.md` — five entries appended (mask-bit correlation
technique, the fixture/deny-set degrade pattern, a fixed-offset-guard trap, the
value-needle gap-histogram technique).

Research scripts under `var/tmp/p6b/` (gitignored, throwaway): `common.py` plus numbered
scripts 01–23; method summarised under `verified` and in this section, which is what makes
them re-runnable.

## verified

Every row cites a command run in this session and its actual output. Scripts live in
`var/tmp/p6b/` and run as `uv run --project <repo-root> python <script>` from that
directory; repo commands run from the repo root.

| # | Claim | Command | Actual output |
|---|---|---|---|
| 1 | `bats`, `throws`, `historical_id` exact on **every** `retired = 0` export row, through the shipped parser | `python 23_verify_parser.py` | `standard: 18077 records, undecoded_tails=0` / `{'bats_exact': 18072, 'throws_exact': 18072, 'historical_id_exact': 18072}` — zero `_BAD` |
| 2 | Same structural rule holds on the other two saves, zero refusals | `python 23_verify_parser.py` | `challenge: 18077 records, undecoded_tails=0`, `managed: 22046 records, undecoded_tails=0` |
| 3 | Managed-league `historical_id` is ~1,712-shaped: real-player-sized, distinct, Lahman-format | `python 21_crosssave.py` | managed: `hist nonempty: 2137, distinct: 2137`, `non-Lahman-shaped: []`, `duplicate hist ids within save: []`; lengths 6–9 |
| 4 | Tail grammar parses every record of every save with plausibility checks on (raw-scan version) | `python 21_crosssave.py` | `parse-failures=0` on 18,077 / 18,077 / 22,046; bats ∈ {1,2,3}, throws ∈ {1,2} everywhere |
| 5 | The tail parse never crosses the next record's start | `python 22_bounds.py` | `overruns=0`, smallest margins 937 / 893 / 937 bytes on standard / challenge / managed |
| 6 | Mask2 bits 2–5 are presence bits for nickname / nat2 / lang0 / lang1 | `python 08_maskbits.py` | `bit 2 ~ nick: agree 1874/1874`, `bit 3 ~ nat2: 1874/1874`, `bit 4 ~ lang0: 1874/1874`, `bit 5 ~ lang1: 1874/1874` |
| 7 | The three optional-u8 run length equals popcount of (m2 bit6, m2 bit7, b57 bit2) | `python 09_three.py` | `1874 records where popcount(F6,F7,F2) == run length` (all parsed records) |
| 8 | `bats` = written-unless-1, `throws` = written-unless-1 (discovery pass, real players) | `python 10_default.py` | `F6: bats(d=1)=1874/1874`; `F7: throws(d=1)=1874/1874` |
| 9 | Full-population check incl. fictional: bats/throws/hist/nick-presence/loan exact | `python 11_forward.py` | `bats_ok: 18072, throws_ok: 18072, hist_ok: 18072, nickpresence_ok: 18072, loan_league_id_ok: 18072` |
| 10 | Ascending-bit-order correction: nat2 precedes the languages; wrong order is a 99% trap | `python 11_forward.py` vs `python 12_posthist.py` | wrong order: `lang0_ok: 17903 … nat2_BAD: 173`; corrected: `lang0_ok: 18072, lang1_ok: 18072, nat2_ok: 18072` |
| 11 | `historical_team_id` is the second string, exact on all rows | `python 12_posthist.py` | `histteam_ok: 18072` (161 nonempty per oracle) |
| 12 | `prone_overall/leg/back/arm` sit 13 bytes past `historical_team_id`, byte-exact | `python 13_region13.py` | `prone at +13 order (0, 1, 2, 3): 18072/18072` |
| 13 | Export `role = 13` (closer) is not stored in the role byte | `python 16_rolepos.py` | of 229 closers, 197 have **no** byte 13 within prone+70; dumps show `fa 0c 0c` (12) at the role spot |
| 14 | Role is exact *within* fixed-shape groups, so the blocker is the shape rule, not the field | `python 18_shapes.py` | groups `('00','00','20','65')` 2872/2872 at +17, `('00','00','a0','65')` 371/371 at +21, `('0c','7e','20','7e')` 317/317 at +23; mixed groups below 100% |
| 15 | No fixed offset reaches position/role from the post-prone anchor | `python 14_sweep.py` | best full-population hits: role-remap 9694/18072 (53.6%), everything else ≤ 48.4% |
| 16 | `hsc_status` sits beside role in the one fully-mapped shape group | `python 19_group_map.py` | `+16: u8==hsc_status 2872/2872`, `+17: u8==role 2872/2872` |
| 17 | Offline suite green, unchanged fixture | `uv run pytest -m "not gamedata"` | `309 passed, 82 deselected in 2.41s` |
| 18 | Spec-named gamedata files green | `uv run pytest -m gamedata tests/test_parse_players.py tests/test_cross_mode_format.py tests/test_read_only.py` | `26 passed, 35 deselected in 67.67s` |
| 19 | Residual-sensitive gamedata files green after the walk consumes further | `uv run pytest -m gamedata tests/test_byte_accounting.py tests/test_snapshot_semantics.py` | `18 passed, 1 skipped, 16 deselected` |
| 20 | Entire gamedata suite green | `uv run pytest -m gamedata` | `81 passed, 1 skipped, 309 deselected in 84.08s` |
| 21 | Lint, format, types | `uv run ruff check .` ; `uv run ruff format --check .` ; `uv run mypy` | `All checks passed!` ; `144 files already formatted` ; `Success: no issues found in 45 source files` |
| 22 | Contracts file is valid TOML | `uv run python -c "import tomllib, …"` | `fields: 35 withheld: 2` |
| 23 | Guards over memory/leaks/links green after memory append | `uv run pytest -m "not gamedata" tests/test_agent_contract.py tests/test_no_leaks.py tests/test_doc_links.py` | `10 passed in 0.67s` |
| 24 | Oracle scoring covered ALL rows, never a sample | `python 01_oracle.py` | `historical_id: total=18072 notnull=18072 nonempty=1920`; every scoring loop keyed on the full `retired = 0` dict |
| 25 | Final offline run with this handoff on disk | `uv run pytest -m "not gamedata"` | first run `1 failed, 308 passed` — `test_no_machine_paths_or_identifiers` caught a Windows drive path in THIS file's row about scratch commands; path genericised, re-run `309 passed, 82 deselected in 2.45s` |

## assumed

- **The language ids are `u16`.** Verified exact for every export value on these saves,
  but no export value approaches 0xFFFF, so `u16` vs a wider field is untested at the
  top of the range. A wider value would desynchronise the strings and fail the tail
  validation loudly rather than misread.
- **The loan block is a single `u32` (`loan_league_id`).** `loan_team_id` is 0 for every
  loaned player in every save on disk (3 + 3 + 11 records), so whether a second `u32`
  appears when it is nonzero is **unobserved**. If it does, those records land `None` +
  `undecoded_tails` rather than corrupting the strings. Recorded in the field map.
- **b57 bit 1 as a required sentinel.** Its *meaning* is unknown; requiring it is backed
  by 58,200/58,200 observations and is what makes a future format change degrade loudly.
- **The five non-export ids (42001, 49008, 50468, 50469, 132324) were excluded from
  scoring by the oracle join**, per the spec — they parse fine and are included in all
  structural checks.
- **Scratch framing reused the parser's own helpers** (`_looks_like_record`,
  `_next_record_start`), so research offsets and the shipped walk cannot disagree about
  where records start. The shipped-parser scoring (row 1) closes the loop independently.

## surprised-me

- **The spec's premise "position, role, bats, throws are never zero in the export" is
  one-quarter wrong: `role` is 0 for exactly the 8,611 non-pitchers** (11/12/13 =
  SP/RP/CL for the 9,461 pitchers). It didn't change the outcome, but a later reader
  trusting that line would mis-design a role probe.
- **Drop-DEFAULT encoding exists.** Everything decoded before today was drop-zero; `bats`
  and `throws` are written-unless-1. A field can be invisible to every zero-based
  technique and still be mask-governed — the presence bit, not the value rule, is the
  invariant worth hunting first.
- **The export's `role = 13` is apparently derived, not stored.** The save holds 12 (RP)
  in the role byte for 197 of 229 closers. Export-exact `role` may be structurally
  impossible from `players.dat` alone — the closer designation likely lives in
  depth-chart data (plausibly `teams.dat`, which the rosters job owns).
- **0xfa (250) recurs through the ratings region as a value**, so "anchor on the byte
  before role" fails at ~45% — first-marker anchoring on a byte that is also a legal
  rating value is a trap.
- **The record repeats its own `player_id` deep in the tail** (u16-verified 2,872/2,872
  within one shape group, inside a `02`-tagged u32 triple whose third member is 203, the
  league id) — a potential future landmark for decoding the position/role piece.

## could-not-do

- **`position` and `role` are not landed.** The exact-or-nothing standard was not met,
  and the spec forbids landing a 97–99% rule. Best rules found and where they break:
  - Within fixed-shape groups keyed on the flag bytes at prone+5/+6/+11/+12, the role
    byte is **exact** (2,872/2,872; 371/371; 317/317 at group offsets +17/+21/+23), but
    165 such groups exist, the four-byte key does not determine the shape for the large
    mixed groups (e.g. 3,263/3,542), and the shape rule — which flag bits govern which
    widths — is underived. A 165-entry shape lookup would be a fit to two saves, not a
    decode.
  - Best fixed-offset rule across the population: role-remap 9,694/18,072 (53.6%) —
    the ~48–54% coincidence plateau the plan already knew.
  - Even a perfect shape rule reproduces export `role` only for 11/12: **the save stores
    12 where the export says 13** for 197 of 229 closers (row 13). Landing export-exact
    `role` likely requires the depth-chart source, not this file.
  - `position` for pitchers is derivable (`role != 0` → 1), but deriving membership-like
    facts is what this plan explicitly rejects; for position players the field sits in
    the same underived piece (best group hit 1,337/1,389 — not exact).
- Nothing else was blocked: no deny-path collisions, no missing packages, no
  destructive-git needs.

## docs-delta

All for `docs/data-access.md`, routed through `/update-docs` by the main thread:

1. **§2 Cross-reference IDs — correct the count** (proposed label: `measured`, with the
   export cross-check `verified`): "~1,712 unique values, each appearing twice" →
   the probe save holds **1,920** nonempty `historical_id` strings, matching the export's
   1,920 exactly; the managed league holds **2,137**, all distinct, all Lahman-shaped.
   Each value's *second* occurrence sits ~300–450 bytes into the same record, not
   elsewhere in the file.
2. **§4 `players.dat` — the drop-zero boundary moved** (proposed: `verified`): `bats`,
   `throws` and `historical_id` are now readable; the sentence listing them among
   not-yet-readable fields should shrink to `position`, `role`. The tail structure:
   mask at record+56 bits 2–7 govern nickname-index u32 / second_nation u32 / two
   language u16s / bats u8 / throws u8 **in ascending bit order**; record+57 is a third
   mask (bit 2 → one unclassified u8, bit 5 → loan u32, bit 1 always set); then
   `historical_id` and `historical_team_id` as consecutive length-prefixed strings,
   empty-string for players without one.
3. **A second encoding pattern exists: drop-DEFAULT** (proposed: `verified`): `bats` and
   `throws` are written only when ≠ 1, with the presence bit carrying the elision. A
   drop-zero scorer structurally cannot find such a field; the mask bit is the invariant.
4. **Export `role` 13 is not stored in the role byte** (proposed: `measured`, the
   depth-chart reading `inferred`): the save stores 12 for 197 of 229 closers; the
   export's closer designation appears derived from data outside this field.
5. **`prone_overall/leg/back/arm` sit as four consecutive u8s** 13 bytes past
   `historical_team_id` (proposed: `measured` — located and byte-exact on all 18,072,
   but not landed; ratings-adjacent, withheld posture applies).
6. **`hsc_status` located** beside the role byte within one shape group, 2,872/2,872
   (proposed: `measured`, not landed).

## still-open

- **AC8 is now attemptable** — `historical_id` exists on `PlayerRecord`, verified against
  the full export and structure-checked on the managed league.
- **Main-thread test work this change earns** (tests are deny-set for me):
  gamedata pins for `bats`/`throws`/`historical_id` against the export (the scoring in
  row 1 is the template), `undecoded_tails == 0` on every save, and the offline half —
  which needs `tests/fixtures/synthetic.py` extended: set bit 1 in the record+57 byte and
  append a valid tail (optionally masked fields + two length-prefixed strings). Until
  then every synthetic record deliberately takes the documented `None` path, which is
  why the current suite passes unmodified — worth an explicit offline test that a legacy
  tail yields `None` + a counted record, so the degrade path itself is pinned.
- **Smaller-interpretation flag (escalation case 3):** the spec asked for five fields;
  I verified but did **not** expose `second_nation_id`, the language ids, the nickname
  index, `loan_league_id` and `historical_team_id`, since the plan warns every exposed
  field is a re-validation liability. Each is a few-line change to expose if a later
  phase wants it; the field map records the verified mappings so nothing is re-derived.
- **The unclassified tail byte (b57 bit 2)** tracks the real-player minority (1,045 of
  1,874 parseable real players vs 61 fictional) and matches no `players` column under
  identity/minus-one/role-remap transforms. Next probe: the other export tables —
  `players_roster_status` and `players_value` are the shaped candidates.
- **Position/role next steps, in order of expected yield:** derive the flag-byte shape
  rule for the piece after the proneness quad (the `02`-tagged triple carrying
  `player_id` and league id 203 is a candidate right-side landmark, verified within one
  group); and check `teams.dat` depth-chart data for the closer designation before
  spending more on the role byte, since export-exact `role` appears unreachable from
  `players.dat` alone.
- **Residual note for byte accounting:** the walk now consumes ~30–60 more bytes of the
  last record, so `residual_bytes` shrank slightly; all byte-accounting tests pass
  unchanged (row 19), and the tier stays `diagnostic` with an updated rationale.
