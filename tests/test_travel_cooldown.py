import types

import pytest
from fake_endstone import GameMode, ItemStack, PlayerInteractEvent

from endstone_let_me_perform.features import travel_cooldown

ROCKET = "minecraft:firework_rocket"
TRIDENT = "minecraft:trident"


@pytest.fixture
def clock(monkeypatch):
    held = types.SimpleNamespace(now=1000.0)
    monkeypatch.setattr(travel_cooldown, "monotonic", lambda: held.now)
    return held


def glider(server, name="Ada"):
    player = server.join(name)
    player.is_gliding = True
    return player


def press(server, player, item_id, riptide=False, action=PlayerInteractEvent.RIGHT_CLICK_AIR):
    item = ItemStack(item_id)
    if riptide:
        item.item_meta.enchants["minecraft:riptide"] = 3
    return server.fire(PlayerInteractEvent(player, action, item))


def test_a_rocket_while_gliding_waits_between_boosts(server, switch_on, clock):
    switch_on("travel_cooldown", travel_cooldown__rocket_seconds=3)
    player = glider(server)

    assert not press(server, player, ROCKET).is_cancelled
    clock.now += 1
    assert press(server, player, ROCKET).is_cancelled
    assert player.tips == ["§cRocket boost is ready in §f2s§c."]

    clock.now += 2
    assert not press(server, player, ROCKET).is_cancelled
    assert press(server, player, ROCKET).is_cancelled


def test_a_rocket_on_the_ground_is_ignored(plugin, server, switch_on, clock):
    switch_on("travel_cooldown")
    player = server.join("Ada")

    assert not any(press(server, player, ROCKET).is_cancelled for _ in range(3))
    assert not plugin.travel_cooldown.rocket_ready


def test_riptide_tridents_wait_and_plain_tridents_do_not(server, switch_on, clock):
    switch_on("travel_cooldown", travel_cooldown__riptide_seconds=2)
    player = server.join("Ada")

    assert not press(server, player, TRIDENT, riptide=True).is_cancelled
    assert press(server, player, TRIDENT, riptide=True).is_cancelled
    assert player.tips == ["§cRiptide is ready in §f2s§c."]
    assert not any(press(server, player, TRIDENT).is_cancelled for _ in range(3))

    clock.now += 2
    assert not press(server, player, TRIDENT, riptide=True).is_cancelled


def test_rockets_and_riptide_wait_apart(server, switch_on, clock):
    switch_on("travel_cooldown")
    player = glider(server)

    assert not press(server, player, ROCKET).is_cancelled
    assert not press(server, player, TRIDENT, riptide=True).is_cancelled


def test_each_player_waits_alone(server, switch_on, clock):
    switch_on("travel_cooldown")
    first = glider(server, "Ada")
    second = glider(server, "Grace")

    assert not press(server, first, ROCKET).is_cancelled
    assert not press(server, second, ROCKET).is_cancelled
    assert press(server, first, ROCKET).is_cancelled


def test_only_survival_and_adventure_players_wait(server, switch_on, clock):
    switch_on("travel_cooldown")
    builder = glider(server, "Builder")
    builder.game_mode = GameMode.CREATIVE
    explorer = glider(server, "Explorer")
    explorer.game_mode = GameMode.ADVENTURE

    assert not any(press(server, builder, ROCKET).is_cancelled for _ in range(3))
    assert not any(press(server, builder, TRIDENT, riptide=True).is_cancelled for _ in range(3))
    assert not press(server, explorer, ROCKET).is_cancelled
    assert press(server, explorer, ROCKET).is_cancelled


def test_zero_turns_the_rocket_wait_off(server, switch_on, clock):
    switch_on("travel_cooldown", travel_cooldown__rocket_seconds=0)
    player = glider(server)

    assert not any(press(server, player, ROCKET).is_cancelled for _ in range(3))
    assert not press(server, player, TRIDENT, riptide=True).is_cancelled
    assert press(server, player, TRIDENT, riptide=True).is_cancelled


def test_zero_turns_the_riptide_wait_off(server, switch_on, clock):
    switch_on("travel_cooldown", travel_cooldown__riptide_seconds=0)
    player = glider(server)

    assert not any(press(server, player, TRIDENT, riptide=True).is_cancelled for _ in range(3))
    assert not press(server, player, ROCKET).is_cancelled
    assert press(server, player, ROCKET).is_cancelled


def test_only_using_the_item_counts(plugin, server, switch_on, clock):
    switch_on("travel_cooldown")
    player = glider(server)
    other_clicks = (
        PlayerInteractEvent.LEFT_CLICK_AIR,
        PlayerInteractEvent.LEFT_CLICK_BLOCK,
        PlayerInteractEvent.RIGHT_CLICK_BLOCK,
    )

    for action in other_clicks:
        assert not any(press(server, player, ROCKET, action=action).is_cancelled for _ in range(2))
        assert not any(press(server, player, TRIDENT, True, action).is_cancelled for _ in range(2))
    assert not plugin.travel_cooldown.rocket_ready
    assert not plugin.travel_cooldown.riptide_ready


def test_leaving_forgets_the_waits(plugin, server, switch_on, clock):
    switch_on("travel_cooldown")
    player = glider(server)
    press(server, player, ROCKET)
    press(server, player, TRIDENT, riptide=True)

    server.quit(player)
    assert not plugin.travel_cooldown.rocket_ready
    assert not plugin.travel_cooldown.riptide_ready
    assert not press(server, glider(server), ROCKET).is_cancelled
