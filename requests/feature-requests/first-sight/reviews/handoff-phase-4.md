<!-- handoff: v1 -->

# Handoff — Phase 4: snapshot copy, provenance from data, ADR 0001 read-only proof

## track
`feature`

## built
Three new modules, nothing else touched.

`src/ootp_ai/snapshot.py` — the immutable copy layer, and the only module allowed to create
a file. Path is `<snapshot_root>/<save_id>/<sim_date>/<ingest_seq>/`, matching the bronze
key component for component; the sim date comes from `teams.dat`'s own header. Each file is
digested on the source side, copied with `shutil.copy2`, re-digested on the destination side
and compared before the manifest is written, so a torn copy raises at copy time rather than
downstream. Manifest is stdlib JSON with `sort_keys` and an explicit LF newline, so it is
byte-comparable across Windows and CI. `take_snapshot` allocates the next seq from the
filesystem; an existing directory raises `SnapshotExists`. `verify_snapshot` re-digests and
names the offending file.

`src/ootp_ai/parser/saved_games.py` — a real sequential walk of the saved-games index,
replacing the "plaintext, readable without parsing" claim: header through
`read_header_from`, a 74-byte file-level tail, then one variable-length record per save. The
four embedded absolute paths per record are consumed by `_drop_path` and have no field to
land in. Discarded strings decode `latin-1`; the returned league name keeps strict ASCII.

`src/ootp_ai/ingest.py` — `IngestRun` / `SourceFile` and `ingest_save`, the pipeline entry
point. It snapshots, reads each header version off the snapshot copy rather than re-opening
the save, resolves the human team from the index beside it, writes nothing, opens no DB.

## verified
| Claim | Command and actual output |
|---|---|
| Offline suite green, no game, no MySQL | `uv run pytest -m "not gamedata" -q` → 136 dots, no F/E, exit 0 |
| Lint / format / types clean | `uv run ruff check .` → `All checks passed!`; `uv run ruff format --check .` → `95 files already formatted`; `uv run mypy` → `Success: no issues found in 29 source files` |
| Snapshot semantics on the real probe | `uv run pytest -m gamedata -q tests/test_snapshot_semantics.py tests/test_provenance.py` → all 4 gamedata snapshot tests pass: root untracked, exactly three files copied, 20–120 MB band, sim date read from the header |
| Index lists the saves, carries no path, dates differ | same run: `..._lists_the_saves_on_disk`, `..._no_entry_carries_a_drive_letter_or_home_directory`, `..._sim_dates_differ_across_saves_as_measured` all pass — managed `2024-03-07`, probe `2024-03-18`, both from record bytes |
| Human team does **not** resolve | same run: 2 failures — `a human team failed to resolve: [None, None, None]` and `assert None is not None` on `run.human_team_id`. Honest red, see `could-not-do` |
| Zero-residual walk of the index | scratchpad probe: `records: 3 residual: 0 exhausted: True` over 2,070 bytes |
| No numeric slot holds the true team ids | scratchpad probe enumerated every u8/u16/u32 slot in all 4 unclassified regions of all 3 records against `(4, 4, 6)`: zero matches; the only Boston/Chicago-separating slot reads `(2, 2, 1)` |
| Ground truth for the club ids | `ootp_truth_real`: `team_id 4 = Boston Red Sox`, `team_id 6 = Chicago Cubs`; `human_team <> 0` returns only `team_id 6` |
| Fixed-offset ban and write allowlist hold | inside the offline run: `test_no_fixed_offsets.py` green over the enlarged tree; `test_read_only.py` offline half green — `snapshot.py` is the only writer, no destructive call anywhere |
| New files carry no leak pattern | imported the real `PATTERNS` from `tests/test_no_leaks.py`, ran it over the three modules and this handoff → `leak hits: []` |

## assumed
- The 74-byte tail between the shared header and the first index record is a fixed width for
  this file. Measured against the only `saved_games.dat` on disk; the zero-residual walk
  checks it, since a wrong width desynchronises the very next length prefix.
- All three snapshot files in a save carry the same sim date in their headers, so `teams.dat`
  alone suffices. Not cross-checked file-to-file this phase.
- `saved_games.dat` sits at the root of each save's own saved-games directory, so `ingest.py`
  looks for it at `save.root`. True for all three saves configured today.
- A partial snapshot directory is left on disk — this module deletes nothing by design, and
  it has no manifest, so `read_manifest` refuses it.
- `ingest_save` does **not** call `assert_challenge_mode`: a hard requirement would block
  Phase 9, which must ingest the standard-mode probe. Built the smaller interpretation.

## surprised-me
- `verified` · **"It varies across saves" is not "it is the field."** The human-team
  candidate reads `2, 2, 1`, which satisfies the anti-hardcoding test outright — but ground
  truth says the clubs are `4, 4, 6` and the split falls along Challenge/Challenge/Standard.
  Enumerate every numeric slot at u8/u16/u32 and match the **actual expected values**.
- `verified` · A `skip(N)` width constant is defensible only inside a **strictly
  byte-accounted** walk: run to `cursor.exhausted()` and let a wrong width raise on the next
  length prefix. That turns an unverifiable constant into one the file checks itself.
- Smaller: strict-ASCII `Cursor.string()` is right for a name, wrong for a discarded field.
- The first two are memory candidates; writing the memory file was denied (`could-not-do`).

## could-not-do
- **`human_team_id` is not recoverable from `saved_games.dat`, and I stopped rather than
  invent one.** The index identifies the human club by **display name and logo filename
  only**; there is no team id in it. Every numeric slot in all three records was enumerated
  at u8/u16/u32 against ground truth (`4, 4, 6`) — no match. The one slot separating the
  Boston saves from the Cubs save is the last u32 of the 23-byte region before the team
  name, reading `2, 2, 1`; it splits Challenge/Challenge/Standard, corroborated by a `u8`
  earlier reading `0, 0, 1` on the same boundary. Using it would have turned both failing
  tests green with a confidently wrong club. So `..._human_team_is_read_from_data_not_hardcoded`
  and `..._ingest_run_resolves_its_own_provenance` are **red**, by design. The id exists in
  `teams.dat` (`human_team` / `human_id` in the export schema), so it resolves in Phase 5.
  **Needs a decision before Phase 5 starts.**
- **Writing `.claude/agents/data-engineer-memory.md` was denied by the harness classifier.**
  My definition names it the sole `.claude/` carve-out; I did not work around the refusal.
  The entries are in `surprised-me` — please append them.
- `docs/game-mechanics.md` shows as modified in `git status`. **Not mine** — already modified
  when I first ran `git status`, and it is in my deny set.
- Did not run `tests/test_read_only.py`'s gamedata half as instructed (~6.4 GB, hashed three
  times). Its offline half is green inside the `not gamedata` run.

## docs-delta
For `/update-docs` to route. All concern `docs/data-access.md` §1.

1. **Downgrade the `verified` claim that `saved_games.dat` is "plaintext … readable without
   parsing".** It is false. Proposed label `measured`: standard OOTP header (version 25,
   four constants, self-declared filename, two wide dates), then one variable-length record
   per save of u32-LE length-prefixed strings at unaligned offsets. Confirms finding F19.
2. **`measured`** — the index's own header sim date is `(0, 0, 0)`: structural absence, not
   a date. The per-save sim dates are a separate field inside the records.
3. **`measured`** — the record's field order, twenty-one fields, walked with zero residual
   over 2,070 bytes across three saves. Full table is in the module docstring of
   `src/ootp_ai/parser/saved_games.py`; carry the summary plus the three-records caveat.
4. **`measured`, load-bearing** — the index carries **no team id**; it names the human club
   by display string and logo filename, so an id must come from `teams.dat`. The `2, 2, 1`
   field is `unconfirmed` and mode-shaped, **not** a team id — record it as a named trap.
5. **`measured`** — the index embeds an absolute user-profile path **four times per save
   record**, not once. The scope said "per save"; the count matters for the leak argument.
6. **`unconfirmed`** — a u32 in the file-level tail reads `3` against three listed saves and
   may be a record count. Not asserted on: a single observation.

## still-open
- **Decide how Phase 5 resolves the human team**, since this phase proved the index cannot.
  Suggested: the `teams.dat` walk yields `human_team` / `human_id` and `_resolve_human_team`
  moves behind it. The two red tests unblock there.
- `SavedGameEntry`'s pinned three fields leave the human club's **display name** nowhere to
  go, though it is the one human-team fact the index holds. Changing that edits a test.
- `ingest_save` does not cross-check the index's sim date against `teams.dat`'s header (both
  `2024-03-18` for the probe here). A stale index is worth surfacing, probably not worth
  failing an ingest over. Needs a ruling.
- USER-RUN, unchanged from the plan: `uv run pytest -m gamedata tests/test_read_only.py`
  against the probe and then the managed league, and AC21 — confirming `OOTP-AI.lg`'s file
  set, sizes and mtimes by hand against the recorded manifest. Neither run by me.
