from endstone_let_me_perform.core.index import ITEM, KIND_LIMIT, MOB, PROJECTILE, VEHICLE, XP


def test_index_sorts_spawns_into_kinds(plugin, server):
    index = plugin.index
    assert index.active

    server.spawn_mob("minecraft:zombie", 5, 64, 5)
    server.spawn_mob("minecraft:villager_v2", 5, 64, 5)
    server.spawn_mob("myaddon:robot", 5, 64, 5)
    server.spawn_plain("minecraft:arrow", 5, 64, 5)
    server.spawn_plain("minecraft:boat", 40, 64, 5)
    server.spawn_plain("minecraft:xp_orb", 5, 64, 5)
    server.spawn_plain("minecraft:falling_block", 5, 64, 5)
    server.drop("minecraft:dirt", 3, 5, 64, 5)

    assert index.total(MOB) == 1
    assert index.total(PROJECTILE) == 1
    assert index.total(VEHICLE) == 1
    assert index.total(XP) == 1
    assert index.total(ITEM) == 1
    assert index.count(MOB, ("Overworld", 0, 0)) == 1
    assert index.count(VEHICLE, ("Overworld", 2, 0)) == 1


def test_removal_gives_the_chunk_its_slot_back(plugin, server):
    index = plugin.index
    zombie = server.spawn_mob("minecraft:zombie", -1, 64, -1)
    assert index.count(MOB, ("Overworld", -1, -1)) == 1

    zombie.remove()
    assert index.total(MOB) == 0
    assert index.count(MOB, ("Overworld", -1, -1)) == 0
    assert ("Overworld", -1, -1) not in index.counts[MOB]


def test_a_second_spawn_event_for_one_entity_is_counted_once(plugin, server):
    index = plugin.index
    zombie = server.spawn_mob("minecraft:zombie", 20, 64, 20)

    server.spawn(zombie)
    assert index.total(MOB) == 1
    assert index.count(MOB, ("Overworld", 1, 1)) == 1


def test_move_follows_an_entity_into_another_chunk(plugin, server):
    index = plugin.index
    cart = server.spawn_plain("minecraft:minecart", 0, 64, 0)
    entry = index.entries[cart.id]

    index.move(entry, ("Overworld", 3, 3))
    assert index.count(VEHICLE, ("Overworld", 0, 0)) == 0
    assert index.count(VEHICLE, ("Overworld", 3, 3)) == 1


def test_prune_reaps_entities_that_left_without_an_event(plugin, server):
    index = plugin.index
    zombie = server.spawn_mob("minecraft:zombie")
    zombie.is_valid = False

    index.prune()
    assert index.total(MOB) == 0


def test_seed_finds_entities_loaded_before_the_plugin(plugin, server):
    index = plugin.index
    index.clear()
    assert index.total(MOB) == 0

    index.active = False
    server.spawn_mob("minecraft:cow")
    index.active = True
    index.seed()
    assert index.total(MOB) == 1


def test_players_are_never_tracked(plugin, server):
    index = plugin.index
    server.join("Ozz")

    index.seed()
    assert index.total(MOB) == 0
    assert index.snapshot() == []


def test_protected_list_comes_from_settings(plugin, server):
    plugin.settings.change("general", "protected_types", ["minecraft:zombie"])
    plugin.apply_settings()

    server.spawn_mob("minecraft:zombie")
    server.spawn_mob("minecraft:villager_v2")
    assert [entry.type for entry in plugin.index.of(MOB).values()] == ["minecraft:villager_v2"]


def test_index_sleeps_when_no_module_needs_it(plugin, server):
    for key in ("projectile_cap", "item_merge"):
        plugin.settings.change(key, "enabled", False)
    plugin.apply_settings()

    assert not plugin.index.active
    server.spawn_mob("minecraft:zombie")
    assert plugin.index.total(MOB) == 0
    assert [entry.type for entry in plugin.index.snapshot()] == ["minecraft:zombie"]


def test_counted_kinds_reset_when_tracking_overflows(plugin, server):
    index = plugin.index
    zombie = server.spawn_mob("minecraft:zombie")
    bucket = index.of(MOB)
    for filler in range(KIND_LIMIT):
        bucket[-filler - 1] = index.entries[zombie.id]

    server.spawn_mob("minecraft:husk")
    assert index.resets == 1
    assert index.total(MOB) == 1
    assert plugin.server.logger.said("warning")


def test_own_spawns_skip_the_gates(plugin, server):
    denied = []
    plugin.listeners.spawn_gates = (lambda entry: denied.append(entry) is not None and False,)

    blocked = server.spawn_mob("minecraft:zombie")
    assert not blocked.is_valid

    allowed = plugin.index.spawn(server.at(0, 64, 0), "minecraft:zombie")
    assert allowed is not None and allowed.is_valid
    assert plugin.index.total(MOB) == 1
