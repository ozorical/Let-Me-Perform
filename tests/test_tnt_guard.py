import types

import fake_endstone
import pytest
from fake_endstone import ActorExplodeEvent, Block

from endstone_let_me_perform.features import tnt_guard
from endstone_let_me_perform.features.tnt_guard import CELL_LIMIT, Chain

WITH_TNT = ["minecraft:stone", "minecraft:tnt", "minecraft:dirt", "minecraft:tnt"]
WITHOUT_TNT = ["minecraft:stone", "minecraft:dirt"]


@pytest.fixture
def clock(monkeypatch):
    held = types.SimpleNamespace(now=1000.0)
    monkeypatch.setattr(tnt_guard, "monotonic", lambda: held.now)
    return held


def rubble(server):
    return [Block(server.overworld, x, 63, 0, type_id) for x, type_id in enumerate(WITH_TNT)]


def blast(server, x=0, y=64, z=0, dimension=None, source="minecraft:tnt", blocks=None):
    actor = fake_endstone.Actor(source, server.at(x, y, z, dimension))
    return server.fire(ActorExplodeEvent(actor, block_list=blocks or rubble(server)))


def broken(event):
    return [block.type for block in event.block_list]


def test_creeper_blasts_are_not_counted(plugin, server, switch_on, clock):
    switch_on(tnt_guard__chain_limit=1, tnt_guard__hard_limit=2)
    for _ in range(5):
        event = blast(server, source="minecraft:creeper")
        assert not event.is_cancelled
        assert broken(event) == WITH_TNT

    assert not plugin.tnt_guard.chains


def test_blasts_up_to_the_limit_keep_their_tnt(plugin, server, switch_on, clock):
    switch_on(tnt_guard__chain_limit=3)
    for _ in range(3):
        assert broken(blast(server)) == WITH_TNT

    assert plugin.tnt_guard.report() == []


def test_blasts_past_the_limit_light_no_more_tnt(plugin, server, switch_on, clock):
    switch_on(tnt_guard__chain_limit=3)
    for _ in range(3):
        blast(server)

    event = blast(server)
    assert not event.is_cancelled
    assert [(block.type, block.x) for block in event.block_list] == [("minecraft:stone", 0), ("minecraft:dirt", 2)]
    assert broken(blast(server, source="minecraft:tnt_minecart")) == WITHOUT_TNT
    assert plugin.tnt_guard.report() == [("Blasts damped", 2), ("Blasts cancelled", 0)]


def test_blocks_handed_back_are_copies_the_event_does_not_own(server, switch_on, clock):
    switch_on(tnt_guard__chain_limit=1)
    blast(server)

    owned = rubble(server)
    event = blast(server, blocks=owned)
    assert broken(event) == WITHOUT_TNT
    assert not any(block is original for block in event.block_list for original in owned)


def test_a_blast_that_reaches_no_tnt_is_left_as_it_is(plugin, server, switch_on, clock):
    switch_on(tnt_guard__chain_limit=1)
    blast(server)

    stone = [Block(server.overworld, 0, 63, 0, "minecraft:stone")]
    event = blast(server, blocks=stone)
    assert event.block_list == stone
    assert plugin.tnt_guard.report() == []


def test_blasts_past_the_hard_limit_are_cancelled(plugin, server, switch_on, clock):
    switch_on(tnt_guard__chain_limit=2, tnt_guard__hard_limit=4)
    events = [blast(server) for _ in range(6)]

    assert [event.is_cancelled for event in events] == [False, False, False, False, True, True]
    assert [broken(event) for event in events[:4]] == [WITH_TNT, WITH_TNT, WITHOUT_TNT, WITHOUT_TNT]
    assert plugin.tnt_guard.report() == [("Blasts damped", 2), ("Blasts cancelled", 2)]


def test_a_new_window_starts_fresh(server, switch_on, clock):
    switch_on(tnt_guard__chain_limit=2, tnt_guard__window_seconds=5)
    for _ in range(2):
        blast(server)

    clock.now += 4
    assert broken(blast(server)) == WITHOUT_TNT
    clock.now += 1
    assert broken(blast(server)) == WITH_TNT


def test_blasts_in_another_area_are_counted_apart(server, switch_on, clock):
    switch_on(tnt_guard__chain_limit=2, tnt_guard__cell_size=16)
    nether = server.level.get_dimension("nether")
    for _ in range(2):
        blast(server, 8, 64, 8)

    assert broken(blast(server, 15, 79, 15)) == WITHOUT_TNT
    assert broken(blast(server, 16, 64, 8)) == WITH_TNT
    assert broken(blast(server, 8, 80, 8)) == WITH_TNT
    assert broken(blast(server, -1, 64, 8)) == WITH_TNT
    assert broken(blast(server, 8, 64, 8, nether)) == WITH_TNT


def test_nearby_players_are_told_once_for_each_chain(server, switch_on, clock):
    switch_on(tnt_guard__chain_limit=2, tnt_guard__hard_limit=4, tnt_guard__window_seconds=5)
    near = server.join("Near", 20, 64, 0)
    far = server.join("Far", 30, 64, 0)
    elsewhere = server.join("Elsewhere", 0, 64, 0, server.level.get_dimension("nether"))
    for _ in range(6):
        blast(server)

    assert near.tips == ["§cToo much TNT went off at once, so the chain was stopped."]
    assert not far.tips
    assert not elsewhere.tips

    clock.now += 5
    for _ in range(3):
        blast(server)
    assert len(near.tips) == 2


def test_finished_chains_are_dropped_once_the_table_is_full(plugin, server, clock):
    guard = plugin.tnt_guard
    for filler in range(CELL_LIMIT):
        guard.chains[("Overworld", filler, 99, 0)] = Chain(clock.now)

    clock.now += 60
    blast(server)
    assert len(guard.chains) == 1
