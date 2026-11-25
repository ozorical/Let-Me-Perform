import types

import pytest
from fake_endstone import Block, BlockPistonExtendEvent, BlockPistonRetractEvent

from endstone_let_me_perform.features import piston_guard
from endstone_let_me_perform.features.piston_guard import PRUNE_TICKS, TRACK_LIMIT


@pytest.fixture
def clock(monkeypatch):
    held = types.SimpleNamespace(now=1000.0)
    monkeypatch.setattr(piston_guard, "monotonic", lambda: held.now)
    return held


def move(server, x=0, y=64, z=0, dimension=None, event_type=BlockPistonExtendEvent):
    block = Block(dimension or server.overworld, x, y, z, "minecraft:piston")
    return server.fire(event_type(block))


def test_moves_up_to_the_limit_pass(server, switch_on, clock):
    switch_on(piston_guard__moves_per_window=10)

    assert not any(move(server).is_cancelled for _ in range(5))
    assert not any(move(server, event_type=BlockPistonRetractEvent).is_cancelled for _ in range(5))


def test_the_move_over_the_limit_pauses_the_piston(plugin, server, switch_on, clock):
    switch_on(piston_guard__moves_per_window=10, piston_guard__suspend_seconds=30)
    for _ in range(10):
        move(server, 7, 70, -3)

    assert move(server, 7, 70, -3).is_cancelled
    clock.now += 29
    assert move(server, 7, 70, -3).is_cancelled
    assert move(server, 7, 70, -3, event_type=BlockPistonRetractEvent).is_cancelled

    warnings = server.logger.said("warning")
    assert len(warnings) == 1
    assert "7 70 -3 in Overworld" in warnings[0]
    assert plugin.piston_guard.report() == [("Pistons paused", 1), ("Paused now", 1)]


def test_the_piston_runs_again_after_the_pause(plugin, server, switch_on, clock):
    switch_on(piston_guard__moves_per_window=10, piston_guard__suspend_seconds=30)
    for _ in range(11):
        move(server)

    clock.now += 30
    assert not any(move(server).is_cancelled for _ in range(10))
    assert plugin.piston_guard.report() == [("Pistons paused", 1), ("Paused now", 0)]

    assert move(server).is_cancelled
    assert plugin.piston_guard.pauses == 2


def test_a_slow_piston_is_never_paused(plugin, server, switch_on, clock):
    switch_on(piston_guard__moves_per_window=10, piston_guard__window_seconds=10)
    for _ in range(5):
        assert not any(move(server).is_cancelled for _ in range(10))
        clock.now += 11

    assert plugin.piston_guard.report() == []


def test_two_pistons_are_counted_apart(server, switch_on, clock):
    switch_on(piston_guard__moves_per_window=10)
    nether = server.level.get_dimension("nether")
    for _ in range(10):
        assert not move(server, 1, 64, 1).is_cancelled
        assert not move(server, 2, 64, 1).is_cancelled
        assert not move(server, 1, 64, 1, nether).is_cancelled

    assert move(server, 1, 64, 1).is_cancelled
    assert move(server, 1, 64, 1, nether).is_cancelled
    assert not move(server, 1, 65, 1).is_cancelled


def test_tracking_stops_at_the_limit(plugin, server, switch_on, clock):
    switch_on(piston_guard__moves_per_window=10)
    guard = plugin.piston_guard
    for filler in range(TRACK_LIMIT):
        guard.windows[("Overworld", filler, 0, 0)] = (clock.now, 1)

    assert not any(move(server).is_cancelled for _ in range(50))
    assert len(guard.windows) == TRACK_LIMIT


def test_prune_forgets_quiet_pistons_and_finished_pauses(plugin, server, switch_on, clock):
    switch_on(piston_guard__moves_per_window=10, piston_guard__suspend_seconds=30)
    guard = plugin.piston_guard
    move(server, 1, 64, 1)
    for _ in range(11):
        move(server, 2, 64, 2)
    assert len(guard.windows) == 1
    assert len(guard.paused) == 1

    clock.now += 31
    server.scheduler.advance(PRUNE_TICKS)
    assert not guard.windows
    assert not guard.paused


def test_a_settings_change_lets_a_paused_piston_run(plugin, server, switch_on, clock):
    switch_on(piston_guard__moves_per_window=10)
    for _ in range(11):
        move(server)

    plugin.apply_settings()
    assert not move(server).is_cancelled
