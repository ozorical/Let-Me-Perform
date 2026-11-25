import json

import fake_endstone
import pytest
from fake_endstone import ActorExplodeEvent, Block, BlockPistonExtendEvent, Command, ItemStack, PlayerInteractEvent

from endstone_let_me_perform.core.index import MOB, PROJECTILE, VEHICLE
from endstone_let_me_perform.settings import SECTIONS

COMMANDS = (
    ("lag", []),
    ("lag", ["entities"]),
    ("tps", []),
    ("lagclear", []),
    ("lagclear", ["cancel"]),
    ("lagclear", ["now"]),
    ("config-lmp", []),
)


@pytest.fixture
def admin(server):
    player = server.join("Ozz", 8, 64, 8)
    player.is_op = True
    return player


@pytest.fixture
def busy(plugin, server, admin):
    for section in SECTIONS:
        if section.has_switch:
            plugin.settings.change(section.key, "enabled", True)
    plugin.apply_settings()

    server.join("Visitor", 300, 64, 300)
    for number in range(120):
        server.spawn_mob("minecraft:zombie", number % 48, 64, number % 5)
    for number in range(60):
        server.spawn_mob("minecraft:cow", 100 + number % 16, 64, number % 16)
    for number in range(80):
        server.drop("minecraft:cobblestone", 3, number % 20, 64, 40)
        server.spawn_plain("minecraft:xp_orb", number % 20, 64, 41)
        server.spawn_plain("minecraft:arrow", number % 20, 64, 42)
    for number in range(20):
        server.spawn_plain("minecraft:boat", 200, 64, number)
    return plugin


def shown(server, player):
    server.scheduler.advance(1)
    return player.forms[-1]


def untouched(form) -> list:
    answers = []
    for control in form.controls:
        if isinstance(control, fake_endstone.Label):
            answers.append(None)
        elif isinstance(control, fake_endstone.Dropdown):
            answers.append(control.default_index)
        else:
            answers.append(control.default_value)
    return answers


def answer(form, player) -> None:
    if isinstance(form, fake_endstone.ModalForm):
        form.on_submit(player, json.dumps(untouched(form)))
    elif isinstance(form, fake_endstone.MessageForm):
        form.on_submit(player, 0)


def test_every_module_runs_side_by_side_for_a_long_stretch(busy, server, admin):
    piston = Block(server.overworld, 4, 64, 4, "minecraft:piston")
    tnt = server.spawn_plain("minecraft:tnt", 60, 64, 60)
    blast = [Block(server.overworld, 60 + offset, 63, 60, "minecraft:tnt") for offset in range(4)]
    boat = ItemStack("minecraft:oak_boat")
    rocket = ItemStack("minecraft:firework_rocket")
    admin.is_gliding = True

    for _ in range(40):
        server.scheduler.advance(100)
        server.spawn_mob("minecraft:skeleton", 20, 64, 20)
        server.drop("minecraft:dirt", 1, 30, 64, 30)
        for _ in range(60):
            server.fire(BlockPistonExtendEvent(piston))
        for _ in range(30):
            server.fire(ActorExplodeEvent(tnt, block_list=blast))
        server.fire(PlayerInteractEvent(admin, PlayerInteractEvent.RIGHT_CLICK_BLOCK, boat, Block(server.overworld, 200, 64, 4)))
        server.fire(PlayerInteractEvent(admin, PlayerInteractEvent.RIGHT_CLICK_AIR, rocket))

        stacked = next((entry.actor for entry in busy.index.of(MOB).values() if entry.alive and entry.actor.name_tag), None)
        if stacked is not None:
            server.kill(stacked)

    index = busy.index
    assert server.logger.said("error") == []
    assert all(entry.alive for entry in index.entries.values())
    for kind in (MOB, PROJECTILE, VEHICLE):
        assert sum(index.counts[kind].values()) == index.total(kind)
    assert index.total(MOB) < 180
    assert busy.piston_guard.pauses > 0
    assert busy.tnt_guard.cancelled > 0
    assert busy.vehicle_cap.refused > 0


def test_every_command_answers_with_every_module_on(busy, server, admin):
    console = server.command_sender
    for sender in (admin, console):
        for name, args in COMMANDS:
            assert busy.on_command(sender, Command(name), args) is True
        server.scheduler.advance(40)

    assert server.logger.said("error") == []
    assert admin.messages and console.messages
    assert admin.forms == [] or shown(server, admin).title == "Let Me Perform"


def test_every_menu_button_opens_or_acts_without_an_error(busy, server, admin):
    busy.menus.open(admin)
    main = shown(server, admin)
    assert all(button.icon for button in main.buttons)

    pressed = 0
    for main_index in range(len(main.buttons)):
        main.press(admin, main_index)
        page = shown(server, admin)
        answer(page, admin)
        if not isinstance(page, fake_endstone.ActionForm):
            continue

        assert all(button.icon for button in page.buttons)
        for page_index in range(len(page.buttons)):
            main.press(admin, main_index)
            current = shown(server, admin)
            if page_index >= len(current.buttons):
                continue
            current.press(admin, page_index)
            answer(shown(server, admin), admin)
            server.scheduler.advance(2)
            pressed += 1

    assert pressed > 60
    assert server.logger.said("error") == []
