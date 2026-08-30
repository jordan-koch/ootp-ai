"""AC8 — Tier A. The names join validated on the league we actually manage.

Challenge Mode has no export (ADR 0003), so `OOTP-AI.lg` can never be diffed row-for-row
the way the standard probe can. Tier A is the substitute: `players.csv` ships with the
game, carries `LahmanID`/`FirstName`/`LastName`, and `players.dat` embeds the same Lahman
ID per real player — so the two can be joined offline, exactly, on the managed save.

## AC8 said "100% exact". That is unachievable on correct data, and here is the proof

The criterion was written before anyone had read `players.csv`'s bytes. Measured:

1. **`players.csv` is pure ASCII.** It ships with every accented character already
   replaced by `?` — the file literally contains `Rod?n`. Zero bytes above 0x7f in the
   first 2 MB. So 25 players per save cannot match a correctly-parsed accented name.
2. **Five further players disagree outright**, in ways `players.csv` and the save simply
   render differently: a short-form given name against a formal one, a generational
   suffix present in one and not the other, a surname particle capitalised differently,
   and two Korean players whose save identities are fictionalised.
3. **The managed save adds a block of ~28 more**, all in one league — OOTP ships the KBO
   without real player identities, so its players keep a real Lahman ID while carrying a
   generated name.

None of that is the parser. **The proof that it is not** is the whole reason this module
compares two saves rather than one: the standard-mode probe, whose parse is independently
verified at **18,072/18,072 against the export** by `test_names_join.py`, shows *the same
residual disagreements*. A disagreement that survives on a save proven correct is a
property of the shipped CSV, not of the walk.

So this module asserts something stronger than a softened percentage: after the one
mechanical normalization `players.csv` provably applies, **every** remaining disagreement
must be either inside a league whose identities the data itself shows to be fictionalised,
or a member of a residual set that is *identical on both saves*. A real parser fault —
a swapped slot, an off-by-one index, a stale table — cannot satisfy that, because it
would disagree on thousands of rows and the two saves' residuals would not line up.

## Nothing here is written down

`tests/test_no_leaks.py:106` catches `players.csv` by **filename only**, so a renamed
derived copy would sail into a public repo. This module therefore holds **no** name data:
no allowlist of players, no Lahman-ID-to-name mapping, not one literal name. Both sides
of every comparison are read at runtime, and the residual sets are compared to *each
other* rather than to anything committed. The only constants are counts.
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest

from ootp_ai.config import ConfigError, SaveRef, Settings, load_settings
from ootp_ai.parser.names import NAMES_FILE, NameTable, build_name_table
from ootp_ai.parser.players import PLAYERS_FILE, PlayerRecord, read_players
from ootp_ai.parser.teams import TEAMS_FILE, read_teams

pytestmark = pytest.mark.gamedata

#: Where `players.csv` sits under the install. A game-layout constant, not a machine
#: path — the install root itself resolves from `.env` like everything else.
PLAYERS_CSV = ("data", "database", "players.csv")

#: `players.csv` ships pure ASCII. Read as ASCII deliberately: if OOTP ever starts
#: shipping real accents, this raises instead of silently changing what the fold means.
CSV_ENCODING = "ascii"

#: Rows of `players.csv` carrying a non-empty `LahmanID`. `measured` 2026-08-18.
CSV_ROWS_WITH_A_LAHMAN_ID = 1_777

#: Players joined on both sides. Lower than the save's `historical_id` population because
#: `players.csv` covers the shipped real-player database and the saves carry Lahman IDs
#: for players it does not list (511 in the managed league, 376 in the probe).
MANAGED_JOINED = 1_626
PROBE_JOINED = 1_544

#: Players whose save name carries a character `players.csv` cannot represent, and which
#: therefore match only after the fold. **This must be nonzero** or the fold is untested
#: and could be a no-op hiding real mismatches. `measured` — 25 on every save.
FOLD_ONLY_MATCHES = 25

#: Disagreements left after the fold, outside any fictionalised-identity league. The same
#: five renderings on both saves — which is what makes them shipped-data drift rather
#: than a parse error, since the probe's parse is export-verified at 18,072/18,072.
RESIDUAL_DISAGREEMENTS = 5

#: A league is treated as carrying fictionalised identities when most of its Lahman-ID
#: players disagree. Derived from the data rather than hardcoded to a league id: the
#: point is the *shape* (a league is either ~all-agree or ~all-disagree), and a threshold
#: naming a specific league would be fitting the test to today's save.
FICTIONALISED_LEAGUE_SHARE = 0.5

#: A league below this is too small for its rate to mean anything.
MIN_LEAGUE_POPULATION = 10

#: **The size of the carve-out, pinned.** The rule above is derived from the data, which
#: makes it robust to a league renumbering — and also makes it an escape hatch that grows
#: silently. `measured` 2026-08-18: exactly one league qualifies in the managed save and
#: it absorbs 28 disagreements. Without these two constants a parse fault confined to a
#: single affiliate would *classify that affiliate as fictionalised and excuse itself*,
#: while the residual comparison still held at five and the bimodality guard stayed blind
#: (it only flags rates between 5% and 50%, and a broken league sits near 100%).
MANAGED_FICTIONALISED_LEAGUES = 1
MANAGED_FICTIONALISED_ROWS = 28


def _settings() -> Settings:
    try:
        return load_settings()
    except ConfigError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"save configuration unavailable: {exc}")


def csv_fold(text: str) -> str:
    """Render `text` the way `players.csv` does: every non-ASCII character becomes `?`.

    The single declared normalization in this module. It is mechanical, it is derived
    from a measured property of the shipped file, and it is applied to the **save** side
    so the CSV is never altered to fit the parser.
    """
    return "".join(character if ord(character) < 128 else "?" for character in text)


def _csv_names(settings: Settings) -> dict[str, tuple[str, str]]:
    """`LahmanID -> (FirstName, LastName)`, read at runtime and never persisted."""
    path = settings.install.joinpath(*PLAYERS_CSV)
    if not path.is_file():
        pytest.skip(
            f"{Path(*PLAYERS_CSV).as_posix()} is not present under OOTP_INSTALL, so the "
            "only Tier-A answer key for the managed league is unavailable. AC8 is "
            "unproven, not satisfied."
        )
    with path.open(encoding=CSV_ENCODING, newline="") as handle:
        reader = csv.reader(handle)
        # The header line is `//`-prefixed and its fields carry a leading space
        # (`docs/data-access.md` §2 records the prefix; the spacing is measured here).
        header = [column.strip() for column in next(reader)]
        header[0] = header[0].removeprefix("//").strip()
        columns = {name: header.index(name) for name in ("LahmanID", "FirstName", "LastName")}
        widest = max(columns.values())

        names: dict[str, tuple[str, str]] = {}
        for row in reader:
            if len(row) <= widest:
                continue
            key = row[columns["LahmanID"]].strip()
            if key:
                names[key] = (
                    row[columns["FirstName"]].strip(),
                    row[columns["LastName"]].strip(),
                )
    return names


def _table(save: SaveRef) -> NameTable:
    path = save.path / NAMES_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {NAMES_FILE} on this machine")
    return build_name_table(save.save_id, path.read_bytes())


def _players(save: SaveRef) -> tuple[PlayerRecord, ...]:
    path = save.path / PLAYERS_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {PLAYERS_FILE} on this machine")
    return read_players(path.read_bytes()).players


def _league_of_team(save: SaveRef) -> dict[int, int]:
    path = save.path / TEAMS_FILE
    if not path.is_file():
        pytest.skip(f"{save.league} has no {TEAMS_FILE} on this machine")
    return {team.team_id: team.league_id for team in read_teams(path.read_bytes()).teams}


class _Comparison:
    """One save's Tier-A join, partitioned the way the module docstring describes."""

    def __init__(self, save: SaveRef, csv_names: dict[str, tuple[str, str]]) -> None:
        table = _table(save)
        leagues = _league_of_team(save)

        self.save = save
        self.exact: list[int] = []
        self.fold_only: list[int] = []
        #: `(csv_name, resolved_name)` for each disagreement — the *rendering signature*,
        #: carrying no player id, so two saves that renumber their players can still be
        #: compared. Held in memory for the length of a test and written nowhere.
        self.disagreement: dict[int, tuple[tuple[str, str], tuple[str, str]]] = {}
        self.unresolved: list[str] = []
        self.blank: list[str] = []
        self.league_of_player: dict[int, int | None] = {}

        for player in _players(save):
            want = csv_names.get(player.historical_id or "")
            if want is None:
                continue

            first = table.entries.get(player.first_name_index)
            last = table.entries.get(player.last_name_index)
            if first is None or last is None:
                self.unresolved.append(
                    f"player {player.player_id}: indices "
                    f"({player.first_name_index}, {player.last_name_index})"
                )
                continue
            if not first.strip() or not last.strip():
                self.blank.append(f"player {player.player_id}: resolved ({first!r}, {last!r})")

            self.league_of_player[player.player_id] = (
                leagues.get(player.team_id) if player.team_id is not None else None
            )
            got = (first, last)
            folded = (csv_fold(first), csv_fold(last))
            if got == want:
                self.exact.append(player.player_id)
            elif folded == want:
                self.fold_only.append(player.player_id)
            else:
                self.disagreement[player.player_id] = (want, got)

    @property
    def joined(self) -> int:
        return len(self.exact) + len(self.fold_only) + len(self.disagreement)

    def fictionalised_leagues(self) -> set[int]:
        """Leagues whose Lahman-ID players mostly disagree — derived, not named.

        **`None` is excluded deliberately, and it is the difference between a bounded
        carve-out and an unbounded one.** `None` is not a league: it is every player with
        no team assignment at all — free agents, the draft-eligible, the unassigned — a
        population of ~10,700 in the managed save. Letting that bucket qualify would mean
        one hypothetical rate crossing the threshold exempts the whole unassigned world
        from the join check in a single step.
        """
        total: Counter[int | None] = Counter(self.league_of_player.values())
        bad: Counter[int | None] = Counter(
            self.league_of_player[player_id] for player_id in self.disagreement
        )
        return {
            league
            for league, count in bad.items()
            if league is not None
            and total[league] >= MIN_LEAGUE_POPULATION
            and count / total[league] > FICTIONALISED_LEAGUE_SHARE
        }

    def excused(self) -> list[int]:
        """Players whose disagreement the fictionalised-league rule absorbs."""
        fictionalised = self.fictionalised_leagues()
        return [
            player_id
            for player_id in self.disagreement
            if self.league_of_player[player_id] in fictionalised
        ]

    def residual(self) -> set[tuple[tuple[str, str], tuple[str, str]]]:
        """Disagreement signatures outside any fictionalised league."""
        fictionalised = self.fictionalised_leagues()
        return {
            signature
            for player_id, signature in self.disagreement.items()
            if self.league_of_player[player_id] not in fictionalised
        }

    def population_in(self, leagues: set[int]) -> int:
        """How many joined players sit in `leagues`. Used to check the carve-out's reach."""
        return sum(1 for league in self.league_of_player.values() if league in leagues)


def _managed(settings: Settings) -> _Comparison:
    return _Comparison(settings.managed, _csv_names(settings))


def _probe(settings: Settings) -> _Comparison:
    if settings.truth_save is None:
        pytest.skip("OOTP_TRUTH_LEAGUE unset — the export-verified control save is absent")
    return _Comparison(settings.truth_save, _csv_names(settings))


def test_the_answer_key_is_the_shipped_real_player_database() -> None:
    """Pins the key's size so a narrowed CSV cannot make the join look easy."""
    rows = len(_csv_names(_settings()))
    assert rows == CSV_ROWS_WITH_A_LAHMAN_ID, (
        f"players.csv now yields {rows:,} rows with a LahmanID, not "
        f"{CSV_ROWS_WITH_A_LAHMAN_ID:,}. Either the game shipped a new real-player "
        "database — in which case every count in this module needs re-measuring — or the "
        "header parsing above picked the wrong columns."
    )


def test_players_csv_ships_pure_ascii_which_is_why_the_fold_exists() -> None:
    """The measurement the whole module rests on, asserted rather than asserted-about.

    If OOTP ever ships real accents, `_csv_names` raises on the ASCII decode and this
    test is where a reader is told the fold has become wrong rather than merely unused.
    """
    settings = _settings()
    path = settings.install.joinpath(*PLAYERS_CSV)
    if not path.is_file():
        pytest.skip("players.csv is not present under OOTP_INSTALL")

    blob = path.read_bytes()
    high = [byte for byte in blob if byte > 0x7F]
    assert not high, (
        f"players.csv now carries {len(high)} non-ASCII bytes. It shipped pure ASCII with "
        "every accent replaced by '?', which is the only reason csv_fold is applied to "
        "the save side. Re-derive the normalization before trusting this module."
    )


def test_every_managed_name_index_resolves() -> None:
    """AC8's precondition and the clause that catches a genuinely broken join.

    A swapped slot or a stale table shows up here first: indices that point nowhere.
    """
    managed = _managed(_settings())
    assert not managed.unresolved, (
        f"{len(managed.unresolved)} managed-league players point at an index the name "
        "table does not hold:\n" + "\n".join(managed.unresolved[:20])
    )


def test_no_resolved_name_is_blank() -> None:
    """A blank name would reach a roster report as a nameless row. AC9 forbids it."""
    managed = _managed(_settings())
    assert not managed.blank, "names resolved to blank or whitespace:\n" + "\n".join(
        managed.blank[:20]
    )


def test_the_join_covers_the_population_it_is_supposed_to() -> None:
    """Guards the tests below from passing on a quietly shrunken comparison."""
    settings = _settings()
    assert _managed(settings).joined == MANAGED_JOINED
    assert _probe(settings).joined == PROBE_JOINED


def test_the_fold_is_load_bearing_rather_than_a_no_op() -> None:
    """A normalization that changes nothing would silently widen what "matches" means."""
    settings = _settings()
    for comparison in (_managed(settings), _probe(settings)):
        assert len(comparison.fold_only) == FOLD_ONLY_MATCHES, (
            f"{comparison.save.league}: {len(comparison.fold_only)} players match only "
            f"after the accent fold, not {FOLD_ONLY_MATCHES}. If this reaches zero the "
            "fold is doing nothing and should be removed rather than left as decoration."
        )


def test_the_export_verified_save_shows_the_same_residual_as_the_managed_one() -> None:
    """The load-bearing assertion, and the reason AC8 is not merely softened.

    The standard probe's parse is proven exact against the export — 18,072/18,072, by
    `test_names_join.py`. So any disagreement it shows against `players.csv` is the CSV
    disagreeing with the game, full stop. Requiring the managed league's residual to be
    *the same set of renderings* is what converts an allowlist into a finding: a parser
    fault on the managed save would produce a residual the verified save does not share.

    Compared as rendering signatures rather than player ids, because the two universes
    number their players differently.
    """
    settings = _settings()
    managed = _managed(settings)
    probe = _probe(settings)

    assert managed.residual() == probe.residual(), (
        "the managed league's residual disagreements are not the same renderings the "
        "export-verified probe shows.\n"
        f"  only in the managed league: {len(managed.residual() - probe.residual())}\n"
        f"  only in the verified probe: {len(probe.residual() - managed.residual())}\n"
        "A difference here is the parser, not the shipped CSV — the probe is proven "
        "exact against the export, so whatever it agrees on is not in question."
    )
    assert len(managed.residual()) == RESIDUAL_DISAGREEMENTS, (
        f"{len(managed.residual())} residual renderings, not {RESIDUAL_DISAGREEMENTS}. "
        "Both saves moving together is still a change worth a human look: it means OOTP "
        "shipped different data, and the fold or the classification may need re-deriving."
    )


def test_every_other_disagreement_is_confined_to_a_fictionalised_league() -> None:
    """The rest of the managed league's disagreements, bounded structurally.

    OOTP ships some leagues without real player identities: the players keep a real
    Lahman ID and carry a generated name. That is visible in the data as a league where
    *most* Lahman-ID players disagree, against ~0% everywhere else — so the boundary is
    derived from the bimodality rather than from a league id written down here.
    """
    settings = _settings()
    managed = _managed(settings)
    fictionalised = managed.fictionalised_leagues()

    total: Counter[int | None] = Counter(managed.league_of_player.values())
    bad: Counter[int | None] = Counter(
        managed.league_of_player[player_id] for player_id in managed.disagreement
    )
    borderline = [
        f"league {league}: {bad[league]}/{total[league]}"
        for league in bad
        if total[league] >= MIN_LEAGUE_POPULATION
        and 0.05 < bad[league] / total[league] <= FICTIONALISED_LEAGUE_SHARE
    ]
    assert not borderline, (
        "a league disagrees at a rate that is neither ~none nor ~all, so the "
        "fictionalised/real split is no longer bimodal and the structural argument for "
        f"ignoring those rows does not hold: {borderline}"
    )
    assert fictionalised, (
        "no league was classified as carrying fictionalised identities. The managed "
        "league carries one; if that stopped being true, the residual assertion above is "
        "now doing all the work and this test is vacuous."
    )

    probe_residual = _probe(settings).residual()
    stray = [
        player_id
        for player_id in managed.disagreement
        if managed.league_of_player[player_id] not in fictionalised
        and managed.disagreement[player_id] not in probe_residual
    ]
    assert not stray, (
        f"{len(stray)} managed-league players disagree with players.csv and are neither "
        "in a fictionalised league nor part of the residual the export-verified probe "
        f"shares: {stray[:20]}. That is the shape a real parse error takes."
    )


def test_the_carve_out_cannot_grow_without_saying_so() -> None:
    """The bound on the escape hatch, and the reason it needs one.

    `fictionalised_leagues()` is derived from the save's own disagreement rates, which is
    what keeps it honest across a league renumbering — and is also what makes it able to
    excuse *new* rows silently. A parse fault confined to one affiliate, hitting 10-80
    Lahman-ID players, would push that league over the threshold, classify it as
    fictionalised, and drop itself out of `residual()`. The residual comparison would
    still hold at five, and the bimodality guard would not see it: that guard only flags
    rates between 5% and 50%, while a broken league sits near 100%.

    So the *size* of the carve-out is pinned exactly, the same way every other constant
    in this module is. Neither assertion names a league id.
    """
    managed = _managed(_settings())
    fictionalised = managed.fictionalised_leagues()

    assert len(fictionalised) == MANAGED_FICTIONALISED_LEAGUES, (
        f"{len(fictionalised)} leagues are being excused, not "
        f"{MANAGED_FICTIONALISED_LEAGUES}. A second league qualifying is either OOTP "
        "shipping more fictionalised identities or a parse fault excusing itself, and the "
        "two are told apart by a human, not by a threshold."
    )
    assert len(managed.excused()) == MANAGED_FICTIONALISED_ROWS, (
        f"the carve-out now absorbs {len(managed.excused())} disagreements, not "
        f"{MANAGED_FICTIONALISED_ROWS}. Growth here is the signature of a regression "
        "hiding inside the exemption."
    )


def test_the_carve_out_covers_rows_the_verified_probe_cannot_speak_for() -> None:
    """Scopes the module's central claim honestly, rather than overstating its reach.

    The docstring's argument — *the export-verified probe shows the same disagreements,
    so they are the CSV's fault* — covers the five residual renderings. It does **not**
    cover the excused league: measured, the probe carries no meaningful population there
    at all, so it has nothing to corroborate with. Asserting that asymmetry in code keeps
    a reader from taking the verified-control argument to cover more than it does, and is
    why the constants above have to carry the weight instead.
    """
    settings = _settings()
    managed = _managed(settings)
    probe = _probe(settings)
    fictionalised = managed.fictionalised_leagues()

    assert probe.population_in(fictionalised) < MIN_LEAGUE_POPULATION, (
        "the export-verified probe now carries a real population in the excused league, "
        "so it CAN speak to those rows. Fold them into the residual comparison — which is "
        "a much stronger check — instead of leaving them to the carve-out."
    )
    assert not probe.fictionalised_leagues(), (
        "the export-verified control save now classifies a league as fictionalised. Since "
        "its parse is proven exact at 18,072/18,072, that means the rule is firing on "
        "something other than fictionalised identities and needs re-deriving."
    )


def test_the_agreement_is_overwhelming_and_named_where_it_is_not() -> None:
    """The blunt end of AC8: what actually matched, and everything that did not.

    Deliberately last. The tests above are the ones with teeth; this one exists so a
    reader can see the size of the claim, and so a failure prints the disagreements by
    player rather than as a rate.
    """
    settings = _settings()
    managed = _managed(settings)
    accounted = len(managed.exact) + len(managed.fold_only)
    fictionalised = managed.fictionalised_leagues()

    probe_residual = _probe(settings).residual()
    unexplained = [
        f"player {player_id}: csv {want!r} vs resolved {got!r}"
        for player_id, (want, got) in managed.disagreement.items()
        if managed.league_of_player[player_id] not in fictionalised
        and (want, got) not in probe_residual
    ]
    assert not unexplained, (
        f"{len(unexplained)} managed-league players disagree with players.csv in a way "
        "neither the fold, the verified probe's residual, nor the fictionalised-league "
        "carve-out explains:\n" + "\n".join(unexplained[:25])
    )
    assert accounted == MANAGED_JOINED - len(managed.disagreement)
    assert accounted > managed.joined * 0.95, (
        f"only {accounted} of {managed.joined} managed-league players match players.csv "
        "even after the fold. The residual is supposed to be a handful of renderings and "
        "one fictionalised league, not a substantial fraction of the club."
    )
