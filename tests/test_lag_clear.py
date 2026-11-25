import re

import fake_endstone
import pytest

from endstone_let_me_perform.core.tables import STACK_TAG
from endstone_let_me_perform.features import lag_clear

SECOND = 20
CLEAR_OPTIONS = ("clear_items", "clear_xp", "clear_arrows", "clear_hostiles", "clear_passives")


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class Allowance:
    def __init__(self, entities):
        self.left = entities

    def spent(self):
        self.left -= 1
        return self.left < 0


@pytest.fixture
def clock(monkeypatch):
    created = Clock()
    monkeypatch.setattr(lag_clear, "monotonic", created)
    return created


def warned_seconds(server):
    return [int(seconds) for seconds in re.findall(r"Lag clear in §e(\d+) §7seconds", "\n".join(server.broadcasts))]


def finish_clear(plugin, server):
    while plugin.lag_clear.clearing:
        server.scheduler.advance(1)


def spawn_crowd(server, type_id, count):
    return [server.spawn_mob(type_id) for _ in range(count)]


def run_command(plugin, sender, *args):
    plugin.on_command(sender, fake_endstone.Command("lagclear"), list(args))


@pytest.mark.parametrize(
    ("warning", "warnings"),
    [(30, [30, 15, 5]), (20, [20, 10, 5]), (10, [10, 5]), (5, [5])],
)
def test_countdown_warns_at_start_halfway_and_five_seconds_then_clears(plugin, server, warning, warnings):
    plugin.settings.change("lag_clear", "warning_seconds", warning)
    clear = plugin.lag_clear
    zombie = server.spawn_mob("minecraft:zombie")

    assert clear.start_countdown()
    assert clear.counting_down
    assert clear.seconds_left == warning

    server.scheduler.advance(warning * SECOND - 1)
    assert warned_seconds(server) == warnings
    assert clear.seconds_left == 1
    assert zombie.is_valid

    server.scheduler.advance(1)
    assert not clear.counting_down
    assert clear.seconds_left == 0

    finish_clear(plugin, server)
    assert not zombie.is_valid
    assert len(server.broadcasts) == len(warnings) + 1
    assert server.broadcasts[-1].endswith("Entities removed: §e1")


@pytest.mark.parametrize("kept", CLEAR_OPTIONS)
def test_each_option_gates_its_own_kind(plugin, server, kept):
    for option in CLEAR_OPTIONS:
        plugin.settings.change("lag_clear", option, option != kept)
    actors = {
        "clear_items": server.drop("minecraft:dirt"),
        "clear_xp": server.spawn_plain("minecraft:xp_orb"),
        "clear_arrows": server.spawn_plain("minecraft:arrow"),
        "clear_hostiles": server.spawn_mob("minecraft:zombie"),
        "clear_passives": server.spawn_mob("minecraft:cow"),
    }

    assert plugin.lag_clear.clear_now() == len(actors) - 1
    finish_clear(plugin, server)
    assert [option for option, actor in actors.items() if actor.is_valid] == [kept]


def test_arrows_are_the_only_projectiles_cleared(plugin, server):
    arrow = server.spawn_plain("minecraft:arrow")
    others = [
        server.spawn_plain(type_id)
        for type_id in ("minecraft:snowball", "minecraft:egg", "minecraft:splash_potion", "minecraft:thrown_trident")
    ]

    assert plugin.lag_clear.clear_now() == 1
    finish_clear(plugin, server)
    assert not arrow.is_valid
    assert all(actor.is_valid for actor in others)


def test_named_mob_survives_and_a_stack_label_does_not(plugin, server):
    plugin.settings.change("lag_clear", "clear_passives", True)
    pet = server.spawn_mob("minecraft:zombie")
    pet.name_tag = "Gerald"
    dinner = server.spawn_mob("minecraft:cow")
    dinner.name_tag = "Dinner"
    stack = server.spawn_mob("minecraft:zombie")
    stack.name_tag = "§ex12"
    stack.add_scoreboard_tag(STACK_TAG)

    plugin.lag_clear.clear_now()
    finish_clear(plugin, server)
    assert pet.is_valid
    assert dinner.is_valid
    assert not stack.is_valid


def test_tagged_item_survives(plugin, server):
    display = server.drop("minecraft:diamond")
    display.add_scoreboard_tag("shop_display")
    loose = server.drop("minecraft:dirt")

    plugin.lag_clear.clear_now()
    finish_clear(plugin, server)
    assert display.is_valid
    assert not loose.is_valid


def test_protected_and_addon_mobs_are_untouched(plugin, server):
    plugin.settings.change("lag_clear", "clear_passives", True)
    kept = [
        server.spawn_mob(type_id)
        for type_id in ("minecraft:villager_v2", "minecraft:iron_golem", "minecraft:wolf", "myaddon:robot")
    ]
    creeper = server.spawn_mob("minecraft:creeper")

    assert plugin.lag_clear.clear_now() == 1
    finish_clear(plugin, server)
    assert not creeper.is_valid
    assert all(mob.is_valid for mob in kept)


def test_clear_works_while_nothing_tracks_entities(plugin, server):
    for key in ("projectile_cap", "item_merge"):
        plugin.settings.change(key, "enabled", False)
    plugin.settings.change("general", "protected_types", ["minecraft:creeper"])
    plugin.apply_settings()
    assert not plugin.index.active

    player = server.join("Alex")
    creeper = server.spawn_mob("minecraft:creeper")
    zombie = server.spawn_mob("minecraft:zombie")
    item = server.drop("minecraft:dirt")

    assert plugin.lag_clear.clear_now() == 2
    finish_clear(plugin, server)
    assert player.is_valid
    assert creeper.is_valid
    assert not zombie.is_valid
    assert not item.is_valid


def test_clear_now_returns_the_queued_count_and_broadcasts_the_removed_count(plugin, server):
    spawn_crowd(server, "minecraft:zombie", 2)
    server.drop("minecraft:dirt")
    server.spawn_mob("minecraft:skeleton").name_tag = "Bones"
    server.drop("minecraft:diamond").add_scoreboard_tag("shop_display")

    assert plugin.lag_clear.clear_now() == 5
    assert server.broadcasts == []

    finish_clear(plugin, server)
    assert len(server.broadcasts) == 1
    assert server.broadcasts[0].endswith("Entities removed: §e3")


def test_clear_carries_on_next_tick_when_the_budget_runs_out(plugin, server, monkeypatch):
    clear = plugin.lag_clear
    monkeypatch.setattr(clear, "budget", lambda: Allowance(2))
    zombies = spawn_crowd(server, "minecraft:zombie", 5)

    assert clear.clear_now() == 5
    for left in (3, 1):
        server.scheduler.advance(1)
        assert sum(zombie.is_valid for zombie in zombies) == left
        assert clear.clearing
        assert not clear.start_countdown()
        assert clear.clear_now() == 0
        assert server.broadcasts == []

    server.scheduler.advance(1)
    assert not clear.clearing
    assert not any(zombie.is_valid for zombie in zombies)
    assert server.broadcasts[0].endswith("Entities removed: §e5")


def test_timer_starts_a_countdown_every_interval(switch_on, plugin, server):
    switch_on("lag_clear", lag_clear__interval_minutes=5)
    interval = 5 * 60 * SECOND

    server.scheduler.advance(interval - 1)
    assert server.broadcasts == []

    server.scheduler.advance(1)
    assert plugin.lag_clear.counting_down
    assert warned_seconds(server) == [30]

    server.scheduler.advance(interval)
    assert warned_seconds(server) == [30, 15, 5, 30]


def test_timer_stays_quiet_while_the_module_is_off(plugin, server):
    plugin.settings.change("lag_clear", "interval_minutes", 5)
    plugin.apply_settings()

    server.scheduler.advance(2 * 5 * 60 * SECOND)
    assert server.broadcasts == []
    assert not plugin.lag_clear.counting_down


def test_emergency_clear_fires_past_the_mob_threshold(switch_on, plugin, server):
    switch_on("lag_clear", lag_clear__emergency_mobs=100, lag_clear__clear_passives=True)
    cows = spawn_crowd(server, "minecraft:cow", 50)
    zombies = spawn_crowd(server, "minecraft:zombie", 100)

    server.scheduler.advance(SECOND)
    assert server.broadcasts == []

    zombies.append(server.spawn_mob("minecraft:zombie"))
    server.scheduler.advance(SECOND)
    assert "§e101 §7hostile mobs" in server.broadcasts[0]

    finish_clear(plugin, server)
    assert not any(mob.is_valid for mob in zombies + cows)
    assert server.broadcasts[-1].endswith("Entities removed: §e151")


def test_emergency_clear_fires_past_the_drop_threshold(switch_on, plugin, server):
    plugin.settings.change("item_merge", "enabled", False)
    switch_on("lag_clear", lag_clear__emergency_drops=100)
    drops = [server.drop("minecraft:dirt") for _ in range(60)]
    drops += [server.spawn_plain("minecraft:xp_orb") for _ in range(40)]

    server.scheduler.advance(SECOND)
    assert server.broadcasts == []

    drops.append(server.spawn_plain("minecraft:xp_orb"))
    server.scheduler.advance(SECOND)
    assert "§e101 §7dropped items and XP orbs" in server.broadcasts[0]

    finish_clear(plugin, server)
    assert not any(drop.is_valid for drop in drops)


def test_emergency_clear_respects_its_cooldown(switch_on, plugin, server, clock):
    switch_on("lag_clear", lag_clear__emergency_mobs=100, lag_clear__emergency_cooldown_seconds=60)
    clear = plugin.lag_clear

    spawn_crowd(server, "minecraft:zombie", 101)
    server.scheduler.advance(SECOND)
    finish_clear(plugin, server)
    assert dict(clear.report())["Emergency clears"] == 1

    zombies = spawn_crowd(server, "minecraft:zombie", 101)
    clock.now += 59
    server.scheduler.advance(SECOND)
    assert all(zombie.is_valid for zombie in zombies)

    clock.now += 1
    server.scheduler.advance(SECOND)
    finish_clear(plugin, server)
    assert not any(zombie.is_valid for zombie in zombies)
    assert dict(clear.report())["Emergency clears"] == 2


def test_emergency_stays_quiet_when_switched_off(switch_on, plugin, server):
    switch_on("lag_clear", lag_clear__emergency=False, lag_clear__emergency_mobs=100)
    zombies = spawn_crowd(server, "minecraft:zombie", 101)

    server.scheduler.advance(5 * SECOND)
    assert server.broadcasts == []
    assert all(zombie.is_valid for zombie in zombies)


def test_emergency_waits_while_a_countdown_runs(switch_on, plugin, server):
    switch_on("lag_clear", lag_clear__emergency_mobs=100)
    plugin.lag_clear.start_countdown()
    zombies = spawn_crowd(server, "minecraft:zombie", 101)

    server.scheduler.advance(10 * SECOND)
    assert len(server.broadcasts) == 1
    assert all(zombie.is_valid for zombie in zombies)


def test_emergency_ignores_a_kind_the_clear_would_leave(switch_on, plugin, server):
    switch_on("lag_clear", lag_clear__emergency_mobs=100, lag_clear__clear_hostiles=False)
    spawn_crowd(server, "minecraft:zombie", 101)

    server.scheduler.advance(5 * SECOND)
    assert server.broadcasts == []


def test_lagclear_starts_a_countdown_and_refuses_a_second(plugin, server):
    sender = server.command_sender
    clear = plugin.lag_clear
    assert not clear.enabled

    run_command(plugin, sender)
    assert clear.counting_down
    assert len(sender.messages) == 1
    assert sender.errors == []

    server.scheduler.advance(3 * SECOND)
    run_command(plugin, sender)
    assert sender.errors[0].endswith("§e27")
    assert not clear.start_countdown()
    assert warned_seconds(server) == [30]


def test_lagclear_cancel_stops_a_countdown_and_refuses_when_idle(plugin, server):
    sender = server.command_sender
    clear = plugin.lag_clear
    zombie = server.spawn_mob("minecraft:zombie")

    run_command(plugin, sender)
    run_command(plugin, sender, "cancel")
    assert not clear.counting_down
    assert clear.seconds_left == 0
    assert len(sender.messages) == 2

    server.scheduler.advance(40 * SECOND)
    assert zombie.is_valid
    assert len(server.broadcasts) == 1

    run_command(plugin, sender, "cancel")
    assert len(sender.errors) == 1


def test_lagclear_now_clears_at_once_and_refuses_while_working(plugin, server):
    sender = server.command_sender
    clear = plugin.lag_clear
    zombies = spawn_crowd(server, "minecraft:zombie", 2)

    run_command(plugin, sender)
    run_command(plugin, sender, "now")
    assert not clear.counting_down
    assert clear.clearing
    assert sender.messages[-1].endswith("Entities queued: §e2")

    run_command(plugin, sender, "now")
    run_command(plugin, sender)
    assert len(sender.errors) == 2
    assert not clear.counting_down

    finish_clear(plugin, server)
    assert not any(zombie.is_valid for zombie in zombies)
    assert len(server.broadcasts) == 2


def test_a_settings_change_cancels_the_countdown(plugin, server):
    clear = plugin.lag_clear
    clear.start_countdown()

    plugin.apply_settings()
    assert not clear.counting_down
    assert clear.seconds_left == 0

    server.scheduler.advance(40 * SECOND)
    assert len(server.broadcasts) == 1


def test_a_settings_change_drops_a_clear_in_progress(plugin, server, monkeypatch):
    clear = plugin.lag_clear
    monkeypatch.setattr(clear, "budget", lambda: Allowance(1))
    zombies = spawn_crowd(server, "minecraft:zombie", 3)

    clear.clear_now()
    server.scheduler.advance(1)
    plugin.apply_settings()
    assert not clear.clearing

    server.scheduler.advance(5)
    assert sum(zombie.is_valid for zombie in zombies) == 2
    assert server.broadcasts == []


def test_report_covers_the_last_clear_the_next_one_and_emergencies(switch_on, plugin, server, clock):
    clear = plugin.lag_clear
    assert clear.report() == []

    switch_on("lag_clear", lag_clear__interval_minutes=5, lag_clear__emergency_mobs=100)
    server.scheduler.advance(30 * SECOND)
    assert clear.report() == [("Next timed clear", "in 4 min")]

    spawn_crowd(server, "minecraft:zombie", 101)
    server.scheduler.advance(SECOND)
    finish_clear(plugin, server)
    clock.now += 2 * 60 * 60 + 5 * 60
    assert clear.report() == [
        ("Last clear", "2 h 5 min ago, 101 removed"),
        ("Next timed clear", "in 4 min"),
        ("Emergency clears", 1),
    ]
