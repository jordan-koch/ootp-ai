<!-- handoff: v1 -->

## track

feature

## built

**Amended after the coordinator's corrections landed** — this supersedes the first version
of this file. All three escalations were resolved in `tests/`; I rebuilt against the
updated spec and every gate is now green, including `-m gamedata`.

**Phase 3, steps 1-3 — the parser spine**, in `src/ootp_ai/`. `parser/primitives.py` holds
the forward-only `Cursor` (`u8/u16/u32/i32/f64/string/date/color/skip/take/remaining`) over
an in-memory buffer. The ban is structural, not conventional: `__slots__` plus a
getter-only `position` property means there is no `seek`, no setter and no absolute read to
find, and every `unpack_from` offset is the cursor's own name rather than a literal, so the
AST guard covers the tree with **zero exemptions**. `SaveDate` keeps day/month/year as
integers with `as_date() -> date | None`, because a save writes 0/0/0 where a date does not
apply and collapsing that into a real date would turn structural absence into a wrong
value.

`parser/header.py` reads the header **through that same cursor** — no indexed offsets — and
refuses on: a non-null leading byte, wrong magic, any version other than 25, header
constants other than (11, 104, 84, 1), a filename field that is not null-padded, a declared
filename that disagrees with the file opened, and truncation. It now reads the two dates at
75 and 87 as three u32s each (**not** the u8/u8/u16 body primitive) and exposes them as
`sim_date` and `written_date`. It exposes **no** length, end or body offset. Because a
walker still has to continue somewhere, `read_header_from(cursor, name)` reads off a
caller's own cursor and leaves it positioned after the header — the handoff is the cursor,
never a number nobody has measured. `parser/errors.py` is the taxonomy the tests pin.

`saves.py` is `is_save_dir` (both `players.dat` and `teams.dat`), `enumerate_saves` (raises
`FileNotFoundError` on a bad root rather than returning `[]`), `is_challenge_mode` /
`assert_challenge_mode` / `NotChallengeMode` on a 241-byte `challenge.dat`, and
`is_record_file`, now load-bearing in the cross-mode test. Every read is `"rb"`; nothing in
`parser/` opens a file at all.

## verified

| Claim | Command | Actual output |
|---|---|---|
| Offline suite fully green, no game, no MySQL (AC1, AC2, AC3) | `uv run pytest -m "not gamedata"` | `108 passed, 9 deselected in 0.40s` |
| Lint clean | `uv run ruff check .` | `All checks passed!` |
| Format clean | `uv run ruff format --check .` | `82 files already formatted` |
| Strict types clean over `src` **and** `tests` | `uv run mypy` | `Success: no issues found in 23 source files` |
| Every `gamedata` test green — enumerator, Challenge pre-flight, cross-mode | `uv run pytest -m gamedata` | `9 passed, 108 deselected in 0.35s` |
| AC3's guard can go **red** on the reworked module | added `handle.seek(128)` to `header.py`, `uv run pytest tests/test_no_fixed_offsets.py` | `...F` and `src/ootp_ai/parser/header.py:176: .seek(128) — a fixed offset` |
| …and is green once reverted | same command | `....` — 4 passed |
| The parsed sim dates match the leagues they came from | scratch script over all record files in three saves | `OOTP-AI sim_date=['2024-03-07'] written_date=['2026-08-16']`; `Test Save - Challenge Mode sim_date=['2024-03-18'] written_date=['2026-08-15']`; `Test Save - Standard Mode sim_date=['2024-03-18'] written_date=['2026-08-16']` |
| One date per save, not per file — 17/17/16 files agree | same script | `record files parsed: 50`, one distinct `sim_date` per save |
| An absent sim date stays absent | same script, on `saved_games.dat` | `sim_date=0000-00-00 as_date=None written_date=2026-08-16` |
| New and changed files carry no machine path and no CRLF | scratch script importing `PATTERNS` from `tests/test_no_leaks.py` | `leak violations: none`; `CRLF=False` for all seven |

## assumed

- **The four header constants are format, not content, so a mismatch is refused.** Measured
  identical in all 50 record files across three saves. The spec listed them without saying
  whether to enforce; I enforce, per the version-guard doctrine. Given how `TRAILING_U32`
  went wrong, note this is the same *class* of claim — but tested across three saves rather
  than one, which is the distinction that matters.
- **`Cursor.string()` decodes strict ASCII by default**, with `encoding` a parameter because
  the `names.dat` encoding is `unconfirmed`. A non-ASCII byte raises rather than being
  replaced — a mangled name is a wrong name.
- **Reading the saves to answer design questions is in scope.** Every probe was
  `Path.read_bytes()` / `open("rb")`; nothing under the game roots was opened for writing.

## surprised-me

- The `.dat` extension is not a format. `flag_save_completed.dat` is a plain-text log and
  `text_data.dat` is a ZIP; both fail the magic check, correctly.
- `challenge.dat` and the root `saved_games.dat` both carry the full standard header and
  self-declare their filenames — the mode marker is a record file, not an opaque blob.
- mypy's duplicate-module error aborts the run before it checks anything, so a green `ruff`
  plus a red `mypy` says nothing at all about type errors in the code you just wrote.
- The strongest evidence for the two dates was a file with *no* league: `saved_games.dat`
  carries `(0, 0, 0)` for the sim date and a real write date. A field that is zero exactly
  where the semantics say it should be is worth more than three files that agree.

## could-not-do

- Nothing outstanding. The three blockers in the first version of this handoff — the mypy
  duplicate module, the two unsatisfiable cross-mode assertions, and the wrong
  `TRAILING_U32` fixture constant — were all fixed by the coordinator in `tests/`, which is
  my deny set, and I rebuilt against them. No denied path was written, no destructive git
  operation was needed, no package missing.

## docs-delta

Route through `/update-docs`; I wrote nothing in `docs/`.

1. **§4 header table — replace it. `measured` 2026-08-16, three saves plus the index.**
   Offset 0 `u8` null · 1 `char[4]` "OOTP" · 5 `u32` version (25) · 9/13/17/21 `u32`
   (11, 104, 84, 1) · 25 `char[50]` **null-padded filename — the 50-byte width is new** ·
   **75 sim date as three u32s (day, month, year)** · **87 written date, same encoding**.
   Note the header's date encoding is *not* the `u8/u8/u16` Date primitive of §4.
   Measured values: managed `(7, 3, 2024)` then `(16, 8, 2026)`; both probes `(18, 3, 2024)`
   then `(15, 8, 2026)` / `(16, 8, 2026)`; `saved_games.dat` `(0, 0, 0)` then
   `(16, 8, 2026)`. Two independent keys agree — the plan's §2.5 sim dates and each save's
   own `flag_save_completed.dat` wall-clock timestamps.
2. **§4 — the header does not end at 99, and its end is `unconfirmed`.** Bytes 99-110 vary
   per save, byte 111 is constant per *file type*, byte 115 varies per save. **Where records
   begin is unmeasured**; no walker may assume an offset, and the earlier "79" was wrong.
3. **§4 — a correction worth recording as a lesson, not just a value.** `TRAILING_U32 = 7`
   was recorded as a header constant from five files sampled in **one** save. It is the
   sim-date day. A constant confirmed against a single save is not a constant.
4. **§1/§4 — every record file carries the sim date in its own header (`measured`).** A
   snapshot can key itself from the file it is already reading, and specifically *without*
   `saved_games.dat`, which embeds an absolute user-profile path this public repo must never
   render. One distinct sim date per save across all 17/17/16 record files.
5. **§1 — a `*.dat` glob is not a list of record files (`measured`).**
   `flag_save_completed.dat` is a plain-text log (leading byte `0x32`) and `text_data.dat`
   is a ZIP (`PK\x03\x04`) wrapping `text_data.sqlite3`. Saves hold 19 `.dat` files in
   Challenge Mode and 18 in Standard; 17 and 16 respectively are OOTP record files.
6. **§1/§4 — `challenge.dat` is a record file (`measured`)**: 241 bytes, standard header,
   self-declared filename. `saved_games.dat` likewise — which **confirms scope finding F19**
   against §1's `verified` claim that it is "plaintext … readable without parsing".
7. **§4 — cross-mode format equivalence, header level (`verified`, up from `assumed`).** All
   50 record files across the Challenge, Standard and managed saves parse with one reader at
   version 25 with matching self-declared filenames, and the 16 shared files are
   byte-identical over the 75-byte stable prefix. Record-level equivalence is Phase 5+.

## still-open

- **`is_record_file()` still has no offline test.** It is exercised by the `gamedata`
  cross-mode module and by my scratch verification, so a game-less CI run does not cover it.
  A synthetic case would be three lines.
- **The header's true end is the next thing worth measuring**, and Phase 4 needs it before
  any walker starts. Bytes 99-115 are the frontier; `read_header_from` exists so that work
  extends the reader rather than bolting an offset onto it.
- **Smaller interpretation taken:** the u32-triple date reader is private to `header.py`
  rather than a `Cursor` primitive, since the header is the only place it has been measured.
  Promote it if a body walker meets the same encoding.
