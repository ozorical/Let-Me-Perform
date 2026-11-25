import types

import pytest
from fake_endstone import GameMode

from endstone_let_me_perform.features import afk
from endstone_let_me_perform.features.afk import SAMPLE_TICKS


@pytest.fixture
def clock(monkeypatch):
    held = types.SimpleNamespace(now=1000.0)
    monkeypatch.setattr(afk, "monotonic", lambda: held.now)
    return held


@pytest.fixture
def mover(plugin, switch_on, clock):
    switch_on("afk", afk__idle_minutes=2, afk__warn_seconds=30, afk__x=500, afk__y=70, afk__z=-500)
    return plugin.afk


def wait(server, clock, seconds):
    for _ in range(seconds // 10):
        clock.now += 10
        server.scheduler.advance(SAMPLE_TICKS)


def test_a_still_player_is_warned_then_moved(mover, server, clock):
    player = server.join("Ada", 3, 64, 3)
    player.location.yaw = 90.0

    wait(server, clock, 90)
    assert not player.messages
    assert mover.report() == []

    wait(server, clock, 10)
    assert len(player.messages) == 1
    assert "30 seconds" in player.messages[0]

    wait(server, clock, 20)
    assert player.location.x == 3

    wait(server, clock, 10)
    spot = player.location
    assert (spot.dimension.name, spot.x, spot.y, spot.z) == ("Overworld", 500.5, 70, -499.5)
    assert spot.yaw == 90.0
    assert len(player.messages) == 2
    assert mover.report() == [("Players moved", 1), ("Idle now", 1)]


def test_landing_at_the_spot_is_not_activity(mover, server, clock):
    server.join("Ada", 3, 64, 3)
    wait(server, clock, 130)
    assert mover.moves == 1

    wait(server, clock, 60)
    assert mover.report() == [("Players moved", 1), ("Idle now", 1)]


def test_the_move_waits_out_the_whole_warning(mover, server, clock):
    builder = server.join("Ada", 3, 64, 3)
    builder.game_mode = GameMode.CREATIVE
    wait(server, clock, 300)
    assert not builder.messages

    builder.game_mode = GameMode.SURVIVAL
    wait(server, clock, 10)
    assert len(builder.messages) == 1

    wait(server, clock, 20)
    assert builder.location.x == 3
    wait(server, clock, 10)
    assert builder.location.x == 500.5


def test_a_player_who_walks_or_turns_is_left_alone(mover, server, clock):
    walker = server.join("Walker", 3, 64, 3)
    turner = server.join("Turner", 9, 64, 9)
    for step in range(30):
        walker.location = server.at(3 + step, 64, 3)
        turner.location.yaw += 15
        wait(server, clock, 10)

    assert not walker.messages
    assert not turner.messages
    assert mover.moves == 0


def test_moving_after_the_warning_calls_the_move_off(mover, server, clock):
    player = server.join("Ada", 3, 64, 3)
    wait(server, clock, 100)
    assert len(player.messages) == 1

    player.location.pitch = 20.0
    wait(server, clock, 90)
    assert len(player.messages) == 1
    assert player.location.x == 3

    wait(server, clock, 10)
    assert len(player.messages) == 2
    assert mover.moves == 0


def test_creative_and_spectator_players_stay_put(mover, server, clock):
    builder = server.join("Builder", 3, 64, 3)
    builder.game_mode = GameMode.CREATIVE
    watcher = server.join("Watcher", 3, 64, 3)
    watcher.game_mode = GameMode.SPECTATOR

    wait(server, clock, 600)
    assert not builder.messages
    assert not watcher.messages
    assert mover.moves == 0


def test_a_player_already_at_the_spot_stays_put(mover, server, clock):
    parked = server.join("Parked", 510, 70, -505)
    wait(server, clock, 600)

    assert not parked.messages
    assert parked.location.x == 510
    assert mover.report() == [("Players moved", 0), ("Idle now", 1)]


def test_the_spot_only_counts_in_its_own_dimension(mover, server, clock):
    player = server.join("Ada", 500, 70, -500, server.level.get_dimension("nether"))
    wait(server, clock, 130)

    assert player.location.dimension.name == "Overworld"
    assert mover.moves == 1


def test_a_moved_player_is_not_moved_again_until_active(mover, server, clock):
    player = server.join("Ada", 3, 64, 3)
    asked = []

    def start_a_move_that_has_not_landed(spot):
        asked.append(spot)
        return True

    player.teleport = start_a_move_that_has_not_landed
    wait(server, clock, 600)
    assert len(asked) == 1
    assert len(player.messages) == 2

    player.location.yaw = 45.0
    wait(server, clock, 130)
    assert len(asked) == 2


def test_a_move_that_fails_is_tried_again(mover, server, clock):
    player = server.join("Ada", 3, 64, 3)
    player.teleport = lambda spot: False
    wait(server, clock, 130)
    assert mover.moves == 0

    del player.teleport
    wait(server, clock, 10)
    assert mover.moves == 1
    assert player.location.x == 500.5


def test_leaving_forgets_the_player(mover, server, clock):
    player = server.join("Ada", 3, 64, 3)
    wait(server, clock, 100)
    assert len(player.messages) == 1

    server.quit(player)
    assert not mover.watched

    back = server.join("Ada", 3, 64, 3)
    wait(server, clock, 90)
    assert not back.messages
