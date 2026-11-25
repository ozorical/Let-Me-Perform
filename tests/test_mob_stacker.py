import pytest
from endstone.actor import Mob

from endstone_let_me_perform.core.index import MOB
from endstone_let_me_perform.core.tables import STACK_TAG
from endstone_let_me_perform.features.mob_stacker import make_label, read_label

PASS_TICKS = 20
ZOMBIE = "minecraft:zombie"
COW = "minecraft:cow"


class CountedMob(Mob):
    writes = 0

    @property
    def name_tag(self):
        return self.label

    @name_tag.setter
    def name_tag(self, label):
        self.label = label
        self.writes += 1


class SpentAfter:
    def __init__(self, checks: int):
        self.left = checks

    def spent(self) -> bool:
        self.left -= 1
        return self.left < 0


@pytest.fixture
def stacker(plugin, switch_on):
    switch_on("mob_stacker", mob_stacker__interval_seconds=1)
    return plugin.mob_stacker


def crowd(server, type_id, size, x=3, z=3, dimension=None):
    return [server.spawn_mob(type_id, x, 64, z, dimension) for _ in range(size)]


def labelled(server, type_id, count):
    mob = server.spawn_mob(type_id, 3, 64, 3)
    mob.name_tag = make_label(type_id, count)
    mob.add_scoreboard_tag(STACK_TAG)
    return mob


def standing(server, type_id):
    return [actor for actor in server.level.held.values() if actor.type == type_id]


def sizes(server, type_id):
    return sorted((read_label(actor.name_tag) or 1 for actor in standing(server, type_id)), reverse=True)


def test_label_and_count_round_trip():
    assert make_label(ZOMBIE, 12) == "§eZombie §7x12"
    assert make_label("minecraft:zombie_villager_v2", 3) == "§eZombie Villager V2 §7x3"

    for count in (2, 20, 100):
        assert read_label(make_label("minecraft:wither_skeleton", count)) == count

    assert read_label("Bessie") == 0
    assert read_label("") == 0


def test_crowd_folds_into_full_stacks_and_a_remainder(plugin, server, stacker):
    crowd(server, ZOMBIE, 45)
    assert stacker.report() == []

    server.scheduler.advance(PASS_TICKS)

    assert sizes(server, ZOMBIE) == [20, 20, 5]
    assert all(STACK_TAG in zombie.scoreboard_tags for zombie in standing(server, ZOMBIE))
    assert plugin.index.total(MOB) == 3
    assert plugin.index.count(MOB, ("Overworld", 0, 0)) == 3
    assert stacker.report() == [("Stacks", 3), ("Mobs in stacks", 45)]


def test_types_chunks_and_dimensions_stay_apart(server, stacker):
    crowd(server, ZOMBIE, 3)
    crowd(server, COW, 2)
    crowd(server, ZOMBIE, 2, x=90, z=90)
    crowd(server, ZOMBIE, 4, dimension=server.level.get_dimension("nether"))

    server.scheduler.advance(PASS_TICKS)

    assert sizes(server, ZOMBIE) == [4, 3, 2]
    assert sizes(server, COW) == [2]


def test_protected_and_add_on_mobs_never_stack(server, stacker):
    crowd(server, "minecraft:villager_v2", 4)
    crowd(server, "myaddon:robot", 4)

    server.scheduler.advance(PASS_TICKS)

    assert sizes(server, "minecraft:villager_v2") == [1, 1, 1, 1]
    assert sizes(server, "myaddon:robot") == [1, 1, 1, 1]


def test_mob_named_by_a_player_is_left_alone(server, stacker):
    bessie = server.spawn_mob(COW, 3, 64, 3)
    bessie.name_tag = "Bessie"
    crowd(server, COW, 3)

    server.scheduler.advance(PASS_TICKS)
    server.scheduler.advance(PASS_TICKS)

    assert bessie.is_valid
    assert STACK_TAG not in bessie.scoreboard_tags
    assert sorted(cow.name_tag for cow in standing(server, COW)) == ["Bessie", make_label(COW, 3)]


def test_mob_named_after_a_pass_saw_it_is_left_alone(server, stacker):
    bessie = server.spawn_mob(COW, 3, 64, 3)
    server.scheduler.advance(PASS_TICKS)

    bessie.name_tag = "Bessie"
    crowd(server, COW, 3)
    server.scheduler.advance(PASS_TICKS)

    assert bessie.is_valid
    assert bessie.name_tag == "Bessie"
    assert sizes(server, COW) == [3, 1]


def test_label_without_the_stack_tag_counts_as_a_name(server, stacker):
    lookalike = server.spawn_mob(COW, 3, 64, 3)
    lookalike.name_tag = make_label(COW, 9)
    crowd(server, COW, 2)

    server.scheduler.advance(PASS_TICKS)

    assert lookalike.is_valid
    assert sizes(server, COW) == [9, 2]

    server.kill(lookalike)
    server.scheduler.advance(1)
    assert sizes(server, COW) == [2]


def test_players_are_never_folded(plugin, server, stacker):
    ada = server.join("Ada", 3, 64, 3)
    grace = server.join("Grace", 4, 64, 4)
    plugin.index.seed()

    server.scheduler.advance(PASS_TICKS)

    assert ada.is_valid and grace.is_valid
    assert ada.name_tag == "" and grace.name_tag == ""


def test_stack_is_read_back_from_its_label_after_a_restart(plugin, server, stacker):
    crowd(server, ZOMBIE, 7)
    server.scheduler.advance(PASS_TICKS)
    assert sizes(server, ZOMBIE) == [7]

    plugin.apply_settings()
    assert stacker.counts == {}

    crowd(server, ZOMBIE, 1)
    server.scheduler.advance(PASS_TICKS)

    assert sizes(server, ZOMBIE) == [8]
    assert stacker.report() == [("Stacks", 1), ("Mobs in stacks", 8)]


def test_stack_drained_to_one_mob_loses_its_label(server, stacker):
    big = labelled(server, ZOMBIE, 19)
    small = labelled(server, ZOMBIE, 2)

    server.scheduler.advance(PASS_TICKS)

    assert big.name_tag == make_label(ZOMBIE, 20)
    assert small.is_valid
    assert small.name_tag == ""
    assert STACK_TAG not in small.scoreboard_tags


def test_label_is_written_only_when_the_count_changes(server, stacker, switch_on):
    switch_on(mob_stacker__max_stack=3)
    for _ in range(5):
        server.spawn(CountedMob(ZOMBIE, server.at(3, 64, 3)))
    server.scheduler.advance(PASS_TICKS)
    full, part = sorted(standing(server, ZOMBIE), key=lambda zombie: zombie.name_tag, reverse=True)
    assert (full.name_tag, part.name_tag) == (make_label(ZOMBIE, 3), make_label(ZOMBIE, 2))
    written = (full.writes, part.writes)

    server.scheduler.advance(3 * PASS_TICKS)
    assert (full.writes, part.writes) == written

    crowd(server, ZOMBIE, 1)
    server.scheduler.advance(PASS_TICKS)
    assert part.name_tag == make_label(ZOMBIE, 3)
    assert (full.writes, part.writes) == (written[0], written[1] + 1)


def test_trim_removes_mobs_past_the_chunk_limit(plugin, server, stacker, switch_on):
    switch_on(mob_stacker__max_stack=2, mob_stacker__chunk_limit=5)
    crowd(server, ZOMBIE, 12)
    crowd(server, COW, 2)
    bessie = server.spawn_mob(COW, 3, 64, 3)
    bessie.name_tag = "Bessie"

    server.scheduler.advance(PASS_TICKS)

    assert bessie.is_valid
    assert plugin.index.count(MOB, ("Overworld", 0, 0)) == 6
    assert set(sizes(server, ZOMBIE)) == {2}


def test_chunk_limit_of_zero_trims_nothing(server, stacker, switch_on):
    switch_on(mob_stacker__max_stack=2, mob_stacker__chunk_limit=0)
    crowd(server, ZOMBIE, 12)

    server.scheduler.advance(PASS_TICKS)

    assert sizes(server, ZOMBIE) == [2, 2, 2, 2, 2, 2]


def test_stack_unwinds_one_mob_for_each_death(server, stacker):
    nether = server.level.get_dimension("nether")
    crowd(server, ZOMBIE, 3, x=5, z=9, dimension=nether)
    server.scheduler.advance(PASS_TICKS)
    (stack,) = standing(server, ZOMBIE)

    server.kill(stack)
    assert standing(server, ZOMBIE) == []

    server.scheduler.advance(1)
    (rest,) = standing(server, ZOMBIE)
    assert rest.name_tag == make_label(ZOMBIE, 2)
    assert STACK_TAG in rest.scoreboard_tags
    assert rest.location.dimension is nether
    assert (rest.location.x, rest.location.y, rest.location.z) == (5, 64, 9)

    server.kill(rest)
    server.scheduler.advance(1)
    (last,) = standing(server, ZOMBIE)
    assert last.name_tag == ""
    assert STACK_TAG not in last.scoreboard_tags

    server.kill(last)
    server.scheduler.advance(1)
    assert standing(server, ZOMBIE) == []


def test_stack_that_dies_before_any_pass_saw_it_still_unwinds(server, stacker):
    stack = labelled(server, ZOMBIE, 4)

    server.kill(stack)
    server.scheduler.advance(1)

    assert sizes(server, ZOMBIE) == [3]


def test_named_mob_that_dies_leaves_nothing_behind(server, stacker):
    bessie = server.spawn_mob(COW, 3, 64, 3)
    bessie.name_tag = "Bessie"

    server.kill(bessie)
    server.scheduler.advance(1)

    assert standing(server, COW) == []


def test_rest_of_a_stack_gets_past_a_full_mob_cap(plugin, server, stacker, switch_on, monkeypatch):
    switch_on("mob_cap", mob_cap__per_chunk=5)
    crowd(server, ZOMBIE, 3)
    server.scheduler.advance(PASS_TICKS)
    (stack,) = standing(server, ZOMBIE)

    monkeypatch.setattr(plugin.mob_cap, "admit", lambda entry: False)
    plugin.listeners.rebind()
    assert not server.spawn_mob(COW, 3, 64, 3).is_valid

    server.kill(stack)
    server.scheduler.advance(1)

    (rest,) = standing(server, ZOMBIE)
    assert rest.name_tag == make_label(ZOMBIE, 2)
    assert plugin.index.total(MOB) == 1


def test_rest_of_a_stack_is_dropped_when_the_spawn_fails(plugin, server, stacker, monkeypatch):
    crowd(server, ZOMBIE, 3)
    server.scheduler.advance(PASS_TICKS)
    (stack,) = standing(server, ZOMBIE)
    monkeypatch.setattr(plugin.index, "spawn", lambda location, type_id: None)

    server.kill(stack)
    server.scheduler.advance(PASS_TICKS)

    assert standing(server, ZOMBIE) == []
    assert stacker.report() == []


def test_pass_follows_a_mob_that_wandered_into_another_chunk(plugin, server, stacker):
    zombie = server.spawn_mob(ZOMBIE, 3, 64, 3)
    zombie.location = server.at(40, 64, 3)

    server.scheduler.advance(PASS_TICKS)

    assert plugin.index.count(MOB, ("Overworld", 0, 0)) == 0
    assert plugin.index.count(MOB, ("Overworld", 2, 0)) == 1


def test_pass_carries_on_tick_by_tick_when_the_budget_runs_out(server, stacker, monkeypatch):
    monkeypatch.setattr(stacker, "budget", lambda: SpentAfter(1))
    crowd(server, ZOMBIE, 30)

    server.scheduler.advance(PASS_TICKS)
    assert len(standing(server, ZOMBIE)) == 30

    server.scheduler.advance(PASS_TICKS)
    assert len(standing(server, ZOMBIE)) == 30

    server.scheduler.advance(PASS_TICKS)
    assert sizes(server, ZOMBIE) == [20, 10]


def test_mob_that_died_while_the_pass_was_paused_is_not_folded(server, stacker, monkeypatch):
    monkeypatch.setattr(stacker, "budget", lambda: SpentAfter(3))
    zombies = crowd(server, ZOMBIE, 3)
    server.scheduler.advance(PASS_TICKS)

    zombies[0].is_valid = False
    server.scheduler.advance(1)

    assert sorted(zombie.name_tag for zombie in zombies) == ["", "", make_label(ZOMBIE, 2)]


def test_switching_off_forgets_the_counts_and_keeps_the_labels(plugin, server, stacker):
    crowd(server, ZOMBIE, 6)
    server.scheduler.advance(PASS_TICKS)

    plugin.settings.change("mob_stacker", "enabled", False)
    plugin.apply_settings()
    crowd(server, ZOMBIE, 2)
    server.scheduler.advance(PASS_TICKS)

    assert stacker.report() == []
    assert sizes(server, ZOMBIE) == [6, 1, 1]
