import pytest
from fake_endstone import Actor, Block, BlockFace, ItemStack, Mob, PlayerInteractEvent

from endstone_let_me_perform.core.index import MOB, PROJECTILE, VEHICLE
from endstone_let_me_perform.features.vehicle_cap import RECOUNT_TICKS

HOME = ("Overworld", 0, 0)


class Allowance:
    def __init__(self, checks):
        self.left = checks

    def spent(self):
        self.left -= 1
        return self.left < 0


def click_block(server, player, item_id, x, z, face=BlockFace.UP, action=PlayerInteractEvent.RIGHT_CLICK_BLOCK, dimension=None):
    block = Block(dimension or server.overworld, x, 64, z)
    return server.fire(PlayerInteractEvent(player, action, ItemStack(item_id), block, face))


def click_air(server, player, item_id, action=PlayerInteractEvent.RIGHT_CLICK_AIR):
    return server.fire(PlayerInteractEvent(player, action, ItemStack(item_id)))


def test_mob_cap_refuses_the_first_spawn_past_the_limit(plugin, server, switch_on):
    switch_on("mob_cap", mob_cap__per_chunk=5)

    zombies = [server.spawn_mob("minecraft:zombie", 3, 64, 3) for _ in range(5)]
    assert all(zombie.is_valid for zombie in zombies)
    assert plugin.mob_cap.report() == [("Spawns refused", 0)]

    assert not server.spawn_mob("minecraft:zombie", 12, 64, 12).is_valid
    assert plugin.index.count(MOB, HOME) == 5
    assert plugin.mob_cap.report() == [("Spawns refused", 1)]

    assert server.spawn_mob("minecraft:zombie", 16, 64, 3).is_valid
    assert server.spawn_mob("minecraft:zombie", 3, 64, 3, server.level.get_dimension("Nether")).is_valid
    assert plugin.mob_cap.refused == 1


def test_removing_a_mob_frees_its_place(plugin, server, switch_on):
    switch_on("mob_cap", mob_cap__per_chunk=5)
    cows = [server.spawn_mob("minecraft:cow") for _ in range(5)]
    assert not server.spawn_mob("minecraft:cow").is_valid

    server.kill(cows[0])
    assert server.spawn_mob("minecraft:cow").is_valid
    assert not server.spawn_mob("minecraft:cow").is_valid


def test_named_mob_is_let_into_a_full_chunk(plugin, server, switch_on):
    switch_on("mob_cap", mob_cap__per_chunk=5)
    for _ in range(5):
        server.spawn_mob("minecraft:sheep")

    pet = Mob("minecraft:sheep", server.at(0, 64, 0))
    pet.name_tag = "Dolly"
    server.spawn(pet)

    assert pet.is_valid
    assert plugin.index.count(MOB, HOME) == 6
    assert plugin.mob_cap.refused == 0
    assert not server.spawn_mob("minecraft:sheep").is_valid


def test_protected_and_addon_mobs_never_count(plugin, server, switch_on):
    switch_on("mob_cap", mob_cap__per_chunk=5)
    for _ in range(8):
        assert server.spawn_mob("minecraft:villager_v2").is_valid
        assert server.spawn_mob("myaddon:robot").is_valid
    assert plugin.index.count(MOB, HOME) == 0

    for _ in range(5):
        assert server.spawn_mob("minecraft:zombie").is_valid
    assert not server.spawn_mob("minecraft:zombie").is_valid
    assert server.spawn_mob("minecraft:villager_v2").is_valid
    assert server.spawn_mob("myaddon:robot").is_valid
    assert plugin.mob_cap.refused == 1


def test_projectile_cap_refuses_the_first_shot_past_the_limit(plugin, server, switch_on):
    switch_on(projectile_cap__per_chunk=20)

    arrows = [server.spawn_plain("minecraft:arrow") for _ in range(20)]
    assert all(arrow.is_valid for arrow in arrows)
    assert plugin.projectile_cap.report() == [("Projectiles refused", 0)]

    assert not server.spawn_plain("minecraft:snowball").is_valid
    assert plugin.index.count(PROJECTILE, HOME) == 20
    assert plugin.projectile_cap.report() == [("Projectiles refused", 1)]

    assert server.spawn_plain("minecraft:thrown_trident").is_valid
    assert server.spawn_plain("minecraft:arrow", 20, 64, 0).is_valid

    arrows[0].remove()
    assert server.spawn_plain("minecraft:arrow").is_valid


def test_named_projectile_gets_no_way_past_the_cap(plugin, server, switch_on):
    switch_on(projectile_cap__per_chunk=20)
    for _ in range(20):
        server.spawn_plain("minecraft:egg")

    named = Actor("minecraft:egg", server.at(0, 64, 0))
    named.name_tag = "Humpty"
    server.spawn(named)
    assert not named.is_valid


def test_projectiles_and_mobs_are_capped_apart(plugin, server, switch_on):
    switch_on("mob_cap", mob_cap__per_chunk=5, projectile_cap__per_chunk=20)
    for _ in range(5):
        server.spawn_mob("minecraft:skeleton")

    arrows = [server.spawn_plain("minecraft:arrow") for _ in range(20)]
    assert all(arrow.is_valid for arrow in arrows)

    assert not server.spawn_plain("minecraft:arrow").is_valid
    assert (plugin.mob_cap.refused, plugin.projectile_cap.refused) == (0, 1)

    assert not server.spawn_mob("minecraft:skeleton").is_valid
    assert (plugin.mob_cap.refused, plugin.projectile_cap.refused) == (1, 1)


def test_vehicle_placement_is_refused_in_a_full_chunk(plugin, server, switch_on):
    switch_on("vehicle_cap", vehicle_cap__per_chunk=2)
    player = server.join("Sailor", 100, 64, 100)
    server.spawn_plain("minecraft:minecart", 2, 64, 2)

    assert not click_block(server, player, "minecraft:minecart", 5, 5).is_cancelled
    assert plugin.vehicle_cap.report() == [("Placements refused", 0)]

    server.spawn_plain("minecraft:chest_boat", 9, 64, 9)
    assert click_block(server, player, "minecraft:oak_boat", 5, 5).is_cancelled
    assert player.tips == ["§cThis chunk is full. Boats and minecarts here: §e2"]
    assert plugin.vehicle_cap.report() == [("Placements refused", 1)]

    assert not click_block(server, player, "minecraft:oak_boat", 20, 5).is_cancelled
    assert not click_block(server, player, "minecraft:oak_boat", 5, 5, dimension=server.level.get_dimension("Nether")).is_cancelled
    assert plugin.vehicle_cap.refused == 1


def test_vehicles_nobody_placed_by_hand_are_counted_and_kept(plugin, server, switch_on):
    switch_on("vehicle_cap", vehicle_cap__per_chunk=2)
    player = server.join("Sailor", 100, 64, 100)
    carts = [server.spawn_plain("minecraft:hopper_minecart", 4, 64, 4) for _ in range(3)]

    assert all(cart.is_valid for cart in carts)
    assert click_block(server, player, "minecraft:minecart", 4, 4).is_cancelled
    assert player.tips == ["§cThis chunk is full. Boats and minecarts here: §e3"]


@pytest.mark.parametrize(
    ("x", "z", "face", "refused"),
    [
        (0, -8, BlockFace.WEST, True),
        (0, -8, BlockFace.EAST, False),
        (0, -8, BlockFace.UP, False),
        (0, -8, BlockFace.DOWN, False),
        (-1, -8, BlockFace.EAST, True),
        (-17, -8, BlockFace.EAST, True),
        (-17, -8, BlockFace.WEST, False),
        (-17, -8, BlockFace.UP, False),
        (-17, -8, BlockFace.DOWN, False),
        (-8, 0, BlockFace.NORTH, True),
        (-8, 0, BlockFace.SOUTH, False),
        (-8, -17, BlockFace.SOUTH, True),
        (-8, -17, BlockFace.NORTH, False),
    ],
)
def test_vehicle_placement_looks_at_the_chunk_the_face_points_into(plugin, server, switch_on, x, z, face, refused):
    switch_on("vehicle_cap", vehicle_cap__per_chunk=1)
    player = server.join("Sailor", 100, 64, 100)
    server.spawn_plain("minecraft:boat", -8, 64, -8)

    assert click_block(server, player, "minecraft:bamboo_raft", x, z, face).is_cancelled is refused


def test_vehicle_placement_in_the_air_looks_at_the_players_chunk(plugin, server, switch_on):
    switch_on("vehicle_cap", vehicle_cap__per_chunk=1)
    server.spawn_plain("minecraft:boat", 40, 63, 40)
    sailor = server.join("Sailor", 35, 64, 35)
    walker = server.join("Walker", 0, 64, 0)

    assert click_air(server, sailor, "minecraft:oak_boat").is_cancelled
    assert sailor.tips == ["§cThis chunk is full. Boats and minecarts here: §e1"]

    assert not click_air(server, walker, "minecraft:oak_boat").is_cancelled
    assert walker.tips == []


def test_other_items_and_left_clicks_are_left_alone(plugin, server, switch_on):
    switch_on("vehicle_cap", vehicle_cap__per_chunk=1)
    player = server.join("Sailor")
    server.spawn_plain("minecraft:minecart")

    assert not click_block(server, player, "minecraft:rail", 0, 0).is_cancelled
    assert not click_air(server, player, "minecraft:fishing_rod").is_cancelled
    assert not click_block(server, player, "minecraft:minecart", 0, 0, action=PlayerInteractEvent.LEFT_CLICK_BLOCK).is_cancelled
    assert not click_air(server, player, "minecraft:oak_boat", PlayerInteractEvent.LEFT_CLICK_AIR).is_cancelled
    assert plugin.vehicle_cap.refused == 0
    assert player.tips == []


def test_recount_follows_a_vehicle_into_another_chunk(plugin, server, switch_on):
    switch_on("vehicle_cap", vehicle_cap__per_chunk=1)
    player = server.join("Sailor", 100, 64, 100)
    cart = server.spawn_plain("minecraft:minecart", 0, 64, 0)

    cart.location = server.at(50, 64, 0)
    assert click_block(server, player, "minecraft:minecart", 0, 0).is_cancelled

    server.scheduler.advance(RECOUNT_TICKS)
    assert plugin.index.count(VEHICLE, HOME) == 0
    assert plugin.index.count(VEHICLE, ("Overworld", 3, 0)) == 1
    assert not click_block(server, player, "minecraft:minecart", 0, 0).is_cancelled
    assert click_block(server, player, "minecraft:minecart", 50, 0).is_cancelled


def test_recount_carries_on_next_tick_when_the_budget_runs_out(plugin, server, switch_on, monkeypatch):
    switch_on("vehicle_cap")
    for _ in range(5):
        server.spawn_plain("minecraft:minecart").location = server.at(50, 64, 0)
    monkeypatch.setattr(plugin.vehicle_cap, "budget", lambda: Allowance(2))

    server.scheduler.advance(RECOUNT_TICKS)
    assert plugin.index.count(VEHICLE, ("Overworld", 3, 0)) == 2

    server.scheduler.advance(1)
    assert plugin.index.count(VEHICLE, ("Overworld", 3, 0)) == 4

    server.scheduler.advance(1)
    assert plugin.index.count(VEHICLE, ("Overworld", 3, 0)) == 5
    assert plugin.index.count(VEHICLE, HOME) == 0


def test_recount_skips_vehicles_that_left_meanwhile(plugin, server, switch_on, monkeypatch):
    switch_on("vehicle_cap")
    carts = [server.spawn_plain("minecraft:minecart") for _ in range(3)]
    for cart in carts:
        cart.location = server.at(50, 64, 0)
    monkeypatch.setattr(plugin.vehicle_cap, "budget", lambda: Allowance(1))

    server.scheduler.advance(RECOUNT_TICKS)
    carts[1].remove()
    del carts[0].location
    server.scheduler.advance(2)

    assert plugin.index.total(VEHICLE) == 2
    assert plugin.index.count(VEHICLE, ("Overworld", 3, 0)) == 1
    assert plugin.index.count(VEHICLE, HOME) == 1


def test_a_settings_change_starts_the_refusal_counts_again(plugin, server, switch_on):
    switch_on("mob_cap", "vehicle_cap", mob_cap__per_chunk=5, projectile_cap__per_chunk=20, vehicle_cap__per_chunk=1)
    player = server.join("Sailor")
    for _ in range(6):
        server.spawn_mob("minecraft:zombie")
    for _ in range(21):
        server.spawn_plain("minecraft:arrow")
    server.spawn_plain("minecraft:minecart")
    click_block(server, player, "minecraft:minecart", 0, 0)
    assert (plugin.mob_cap.refused, plugin.projectile_cap.refused, plugin.vehicle_cap.refused) == (1, 1, 1)

    plugin.apply_settings()
    assert (plugin.mob_cap.refused, plugin.projectile_cap.refused, plugin.vehicle_cap.refused) == (0, 0, 0)


def test_a_settings_change_drops_a_recount_in_progress(plugin, server, switch_on, monkeypatch):
    switch_on("vehicle_cap")
    for _ in range(3):
        server.spawn_plain("minecraft:minecart").location = server.at(50, 64, 0)
    monkeypatch.setattr(plugin.vehicle_cap, "budget", lambda: Allowance(1))

    server.scheduler.advance(RECOUNT_TICKS)
    plugin.apply_settings()
    server.scheduler.advance(1)

    assert plugin.index.count(VEHICLE, ("Overworld", 3, 0)) == 1
    assert plugin.index.count(VEHICLE, HOME) == 2
