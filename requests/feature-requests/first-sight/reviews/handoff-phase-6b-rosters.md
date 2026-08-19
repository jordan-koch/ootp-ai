<!-- handoff: v1 -->

# Phase 6b, job 2 of 2 — `list_id` recovered, `parser/rosters.py` landed

## track

feature

## built

**`src/ootp_ai/parser/rosters.py`** (new) — `read_rosters(teams_data, players_data) ->
RostersFile`, producing the full `(team_id, player_id, list_id)` grain. It reproduces
`ootp_truth_real.team_roster` **exactly — all 15,672 rows, no extras, no misses** — and
runs clean, save-blind, on the challenge save and the managed league, where Boston
resolves to the operator-verified 33 / 26 / 30 / 7 over 96 rows and 34 distinct players.
Also exposes the 176 assigned-but-unrostered players (the negative-`league_id`
population) as `RostersFile.unrostered`, and the list-id enum as named constants.

**`src/ootp_ai/parser/teams.py`** (minimal extension) — added `TeamRecordSpan` and
`read_team_record_spans(data)`: the same frame search `read_teams` runs, exposed as
`(team_id, start, end)` positions without decoding records. `read_teams` itself is
byte-untouched; no landed field changed.

**`src/ootp_ai/contracts/field_map.toml`** — a new roster-membership section: the grain
(`verified`), the membership array (`measured`, order documented as non-decodable), the
four status bits (`verified`), the unrostered marker (`measured`, with its day-0
boundary and the refusal that fences it), and the crossed identity-to-status spans.

**How it works, in one paragraph.** The spec's premise — recover `list_id` from the
`teams.dat` array — turned out to be structurally impossible: the array is a multiset in
container order (proof under *surprised-me*). The list assignment lives in stored
per-player facts instead: a **roster-status byte** in `players.dat` 22 bytes past
`historical_team_id` (bit 3 = 40-man, bit 4 = IL, bit 2 = org-top-club active, all
`verified` 18,072/18,072), the landed assignment fields, and — load-bearing, not
optional — the array's **per-player multiplicity**, which is the only thing that
distinguishes a rostered-but-inactive player (`{1}`) from an active one (`{1,2}`); the
managed save carries 154 of the former and no bit marks them. Membership *solves*:
`active = m − 1 − il − (secondary if org == team)`, must be 0 or 1; list 3 lands at the
player's `organization_id` (verified 935/935); `m == 1` players must match exactly one
of two measured signatures (unrostered marker vs. none) or the parse refuses. Finally
every club's array multiset must equal the reconstruction exactly — the two files audit
each other, and every planted corruption I tried was caught by name.

## verified

| claim | command | actual output |
|---|---|---|
| Grain is oracle-exact on the standard save | `uv run --project <repo> python 22_verify_parser.py` (from `var/tmp/p6b-rosters/`) | `vs oracle: 15672 rows; missing 0; extra 0; EXACT True` |
| Per-list totals match the plan's numbers | same run | `by list: {1: 7370, 2: 7037, 3: 935, 4: 330}`; `unrostered count == 176: True` |
| Managed-save Boston equals the operator screenshot table | same run | `managed … team 4: l1=33 l2=26 l3=30 l4=7`, 34 distinct (via script 21: `distinct 34`) |
| League invariants hold on ALL three saves | same run | each save: `list1 1:1: True`, `MLB clubs 30, list2 all 26: True`, `list3 max 37/36/37` (≤ 40) |
| Deterministic parse | same run (parses each save twice, compares dataclasses) | `deterministic: True` ×3; runtime 0.6–0.7 s per save |
| Array reconciliation clean save-blind on every club | `python 21_final_algo.py` | standard/challenge/managed: `run-selection problems 0; solve problems 0; reconcile failures 0` over 229 / 229 / 299 clubs |
| Array multiset = roster rows + unrostered, every club with rows | `python 07_all_clubs.py` | `clubs in team_roster: 229; exact multiset match: 229` |
| Status bit 4 = IL exactly | `python 13_player_flags.py` | `d+22 bit 4: il_4 18072/18072 (bit set on 330)` |
| Status bit 3 = 40-man exactly among in-league players | `python 15_flagbyte.py` | `list-3-but-bit-3-clear: 0`; the 97 extra carriers: `by league {0: 97}`, all team 0 (`18_reconstruct.py`: `bit3 with team 0: 97`) |
| Status bit 2 never disagrees with the multiplicity solve | `python 21_final_algo.py` | `bit2 MLB cross-check {'agree': 959, 'disagree': 0}` / `956, 0` / `2639, 0` |
| Bit 5 = the 60-day IL population | `python 15_flagbyte.py` value cross-tab | `[1,4]` class: `0x30:57` + `0xb0:1` = 58, exactly the plan's 58 league-wide |
| Unrostered marker separates the 176 perfectly today | `python 17_markers_semantics.py` | rostered: `last_org!=0 on 0` of 7,370; unrostered: `176` of 176, all `last_lg` = 234, `last_org == own org` 176/176 |
| List-3 team attribution is `organization_id` | `python 16_marker_hunt.py` | `list-3 rows where team != player's organization_id: 0 of 935`; lists 1/2/4 vs `team_id`: `0 of 7370 / 7037 / 330` |
| `list2 = list1 − list4 − {1}-only` per club (standard) | same run | `clubs where list2 != list1 - list4 - only1: 0 of 229` |
| Refusals actually fire (5 planted offenders) | `python 23_refusals.py` | `PASS` ×5: mixed snapshots → `RosterLayoutMismatch`; IL-bit flip and status-byte zero → `AmbiguousRosterMembership`; array duplicate-entry → `AmbiguousRosterMembership`; array garbage-entry → `RosterLayoutMismatch` (`0 candidate membership arrays`) |
| Offline suite green (incl. both fixed-offset guards) | `uv run pytest -m "not gamedata"` | `313 passed, 84 deselected in 2.03s` |
| Gamedata suite green | `uv run pytest -m gamedata` | `83 passed, 1 skipped, 313 deselected in 75.93s` (skip is pre-existing) |
| Lint / format / types | `uv run ruff check .` ; `uv run ruff format --check .` ; `uv run mypy` | `All checks passed!` ; `146 files already formatted` ; `Success: no issues found in 46 source files` |
| Array order is NOT a function of content | `python 08_order.py` | identical Boston multisets across the two test saves, `positional agreement: 88/97`, differences form local cycles among same-list-set entries |
| No concatenated-lists reading exists | `python 02_slots.py` | id 31499 at slots 6, 9, 12 — three occurrences inside a 7-slot window, incompatible with any duplicate-free sub-array partition at the observed sizes |
| No parallel tag/index structure near the array | `python 09_index_hunt.py` | `97-byte permutations of 0..96 in record: []`; weak windows: `[]` (u8 sweep for values 1..4 was already refuted by the prior session) |
| Flags-only decode is WRONG on the managed save | `python 19_blind_dryrun.py` + `20_diag194.py` | 41 managed clubs fail multiset reconciliation under the flags-only rule; club 194: 7 players `expect 2 got 1` — rostered-but-inactive, a state with zero examples in either test save |

Scratch scripts are under `var/tmp/p6b-rosters/` (gitignored, throwaway); method and
numbers are preserved here and in the module docstring.

## assumed

- **The two probe-save Boston rosters are truly identical in membership**, not just in
  multiset, when I read the 88/97 order comparison as container noise. Supported by the
  plan's near-twin table (same 26 active, same 30, same 7 IL, same diagnoses) and by
  every differing slot holding players of identical list-sets — but the challenge save
  has no export, so identity is corroborated rather than proven.
- **The span walk and `read_teams` frame identical record sets.** They search from
  slightly different resume points; both validated against the declared count on all
  three saves, and any divergence lands in a raise (short-count or reconciliation), but
  I did not add a structural cross-check between the two walks.
- **`_IDENTITY_TO_STATUS_WIDTH` (13+4+5) is fixed on every record of every save.**
  Implied very strongly by the IL bit matching at a constant distance on all 18,072
  scorable rows and by zero solve failures on 58,200 records across three saves; not
  proven byte-by-byte for the 22,046 managed records individually.
- **Spec silence handled per rulebook** (escalation case 2): the spec did not restate
  the version guard or snapshot immutability; both walks go through `read_header_from`
  (which refuses unknown versions) and read snapshots read-only via `.read_bytes()`.

## surprised-me

- **The blocker dissolved by being refuted, not solved.** The array *cannot* carry
  `list_id`: identical content serializes in different orders across saves, so the
  bytes do not determine slot-to-list for anyone, the game included. Every ordering
  hypothesis (concatenation, round-robin, hash homes, bucket order, heap, sorted
  container) was either refuted by a measurement or showed exactly zero signal.
- **The prior session's three recorded leads all resolved as artifacts or dead ends**:
  the "stopped early on 19 of 26 clubs" was a chain-builder alignment artifact (fixed
  by phase-grouped chaining, 229/229 immediately); the u32 run after the array is the
  club's **coaching-staff id array** (all 10 Boston values matched `coaches` rows for
  team 4 by id — Cora, Breslow, Bailey, owner John Henry…); the stride-5 cluster is the
  **lineup block** (see docs-delta).
- **The oracle cannot even ask the question.** `team_roster` stores list-sets per
  player, so any assignment of array occurrences to lists scores 100%. A positional
  decode could never have been validated — worth knowing before anyone re-attempts one.
- **Both test saves validated a wrong rule.** "Rostered ⇒ active unless IL" is exact on
  both 2024-03-18 saves and wrong for 154 players in the managed 2024-03-07 save —
  the state it misses (rostered-but-inactive minors) simply doesn't exist in the
  oracle universe on that date. The save-varying discipline caught it; the multiplicity
  solve replaced it.

## could-not-do

- **Decode `list_id` from the array's order** — impossible in principle, per the
  measurements above. This is a finding, not a shortfall; the spec's fallback ("do not
  write rosters.py") was not taken because the grain *was* recovered exactly, from
  stored structure, with the array as a mandatory reconciliation input. See still-open
  for the interpretation flag.
- **Independent cross-check for IL vs active at minor-league clubs.** At MLB clubs a
  2↔4 mislabel is caught by the redundant bit 2 (proven by mutation). At minors, bit 4
  is the only evidence for 2-vs-4 and the multiset cannot see the difference — a
  corrupted IL bit on a minors player would flow through. Bit 4 is verified
  18,072/18,072 and 330-exact, but the residual is real and is documented in the module
  and the field map.
- **Semantics of status bits 0, 1, 6, 7** and of the `{1}`-only limbo state (the three
  standard-save players are Phillips, McFarland, Honeywell Jr. — DFA-shaped, but n=3).
  Not needed for the grain; the solve handles `{1}` without naming its cause.

## docs-delta

For `docs/data-access.md` via `/update-docs`, each with a proposed label:

1. **`verified`** — The `team_roster` grain is recoverable exactly from save structure:
   per-player roster-status byte in `players.dat` (22 bytes past `historical_team_id`;
   bit 2 = org-top-club active, bit 3 = secondary/40-man, bit 4 = IL, bit 5 = 60-day)
   plus the membership array in each `teams.dat` record consumed as a multiset.
   Reproduces the export 15,672/15,672; walker `ootp_ai.parser.rosters.read_rosters`.
2. **`measured`** — The `teams.dat` membership array (~record+1150..1520, moves per
   team) equals roster rows + unrostered assignees as a multiset on every club of every
   save; its **order is container noise** and carries no information — recorded so no
   later session re-attempts a positional decode.
3. **`measured`** — The 176 negative-`league_id` players are marked in the save by
   `last_organization_id == own organization` + `last_league_id == 234` + status `0x00`;
   the save stores `league_id` positive and the *exporter* renders the sign. Day-0
   boundary: rostered players with `last_organization_id != 0` will exist after
   cross-org transactions; `rosters.py` refuses rather than guesses when signatures
   blur, and the marker should be re-measured at the first post-transaction snapshot.
4. **`measured`** — A club's **coaching staff** is a u32 id array immediately after the
   membership array (Boston standard: 10 ids, exact set match against `coaches` for
   team 4, owner and GM included).
5. **`measured`** — The **depth-chart/lineup region** sits at ~record+260..990: at
   ~record+800 Boston carries four lineup groups of `(u32 player_id, u8 fielding
   position 2..10)` at stride 5. This is the structure the sibling flagged as the
   likely home of the export's derived `role = 13` (closer) — the pitching-role piece
   presumably sits in the same region before the lineups. Location recorded; not
   decoded.
6. **`measured`** — League-wide list-set classes in the export: `[]` 10,702, `[1,2]`
   6,220, `[1,2,3]` 817, `[1,4]` 212, `[1,3,4]` 118, `[1]` 3 — and per club,
   `list2 = list1 − list4 − {1}-only` with zero exceptions.

## still-open

- **Interpretation flag (escalation case 3).** The spec's headline says the grain is
  "read from the array in teams.dat, never derived from player attributes". Measured,
  the array cannot carry the list ids, and the exact recovery reads **stored membership
  bits in players.dat + the array's multiplicities**, reconciled per club. I judged
  this inside the spec's landing standard ("via reading structure, not deriving from
  attributes" — every emitted row traces to a stored bit, a stored field, or a stored
  array occurrence, and none of the plan's rejected correlates is consulted), and the
  spec's "partial landings" clause invited exactly this call. The reading I did *not*
  take: "array-only or nothing", which would have returned a well-evidenced refusal
  instead of a landed grain. If the main thread prefers that reading, `rosters.py` is
  one `git rm` away and every measurement stands on its own.
- **Main-thread tests to write** (tests/ is my deny set): the 6b acceptance criteria —
  the three `list_id` invariants against the standard export, Boston's exact managed
  counts (33/26/30/7, 96 rows, 34 distinct, naming WHICH save), AC10's determinism
  half, and a synthetic-fixture decision for `read_rosters` (it raises
  `RosterLayoutMismatch` on an assigned player whose tail is unreadable — legacy
  synthetic records with team assignments would need either a fixture upgrade or an
  expectation of refusal).
- **Re-measure the unrostered marker at the first snapshot after any cross-org
  transaction** in the managed league (trade, waiver claim, int'l signing). The parser
  fails loud, not wrong, if the marker blurs — but the re-measurement is what retires
  the risk.
- **`rosters.py` imports private names from `players.py`** (framing helpers, gap
  widths, `_ASSIGNMENT_BITS`) as the single source of truth for the head layout,
  because extending `read_players` was the sibling's file and not mine to edit. If the
  main thread prefers a public seam, promoting those few names is a rename, not a
  redesign.
- **AC8 / `historical_id`**: the sibling's job landed it; nothing here blocks AC8 now.
- The five status-byte mysteries (bits 0/1/6/7, the `{1}`-only cause) and the finance
  block in front of the array are recorded but unexplored — none blocks anything
  currently planned.
