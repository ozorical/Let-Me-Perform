import json

import fake_endstone
import pytest
import tomlkit

from endstone_let_me_perform.menus import icons
from endstone_let_me_perform.menus.editor import TEXT_BOX_LENGTH
from endstone_let_me_perform.menus.guide import TOPICS, topic_named
from endstone_let_me_perform.settings import SECTION_KEYS, SECTIONS, read_listing, section_named

MAIN_EXTRAS = ["Server report", "Entity census", "Guide", "Reload from file"]
SAMPLE_TABLES = [("Timings", [("MSPT", "12.5"), ("TPS", "20.0")]), ("Chunks", [("Loaded", 1400)])]


class Countdown:
    def __init__(self):
        self.counting_down = False
        self.started = 0
        self.cancelled = 0

    def start_countdown(self) -> bool:
        self.started += 1
        self.counting_down = True
        return True

    def cancel_countdown(self) -> bool:
        self.cancelled += 1
        self.counting_down = False
        return True


@pytest.fixture
def admin(server):
    player = server.join("Ozz")
    player.is_op = True
    return player


@pytest.fixture
def countdown(plugin, monkeypatch):
    stand_in = Countdown()
    monkeypatch.setattr(plugin, "lag_clear", stand_in)
    return stand_in


def shown(server, player):
    server.scheduler.advance(1)
    return player.forms[-1]


def labels(form) -> list:
    return [button.text.split("\n")[0].removeprefix("§0") for button in form.buttons]


def button_named(form, label: str):
    for button in form.buttons:
        if button.text.startswith(f"§0{label}\n"):
            return button
    raise AssertionError(f"There is no button called {label}")


def press(form, player, label: str) -> None:
    form.press(player, form.buttons.index(button_named(form, label)))


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


def slot(form, label: str) -> int:
    for index, control in enumerate(form.controls):
        if getattr(control, "label", None) == label:
            return index
    raise AssertionError(f"There is no control called {label}")


def submit(form, player, answers: list) -> None:
    form.on_submit(player, json.dumps(answers))


def written(tmp_path) -> dict:
    return tomlkit.parse((tmp_path / "config.toml").read_text(encoding="utf-8")).unwrap()


def edit_file(tmp_path, section: str, option: str, value) -> None:
    path = tmp_path / "config.toml"
    document = tomlkit.parse(path.read_text(encoding="utf-8"))
    document[section][option] = value
    path.write_text(tomlkit.dumps(document), encoding="utf-8")


def test_main_page_lists_every_section_with_an_icon(plugin, server, admin):
    plugin.on_command(admin, fake_endstone.Command("config-lmp"), [])
    assert admin.forms == []

    form = shown(server, admin)
    assert labels(form) == [section.title for section in SECTIONS] + MAIN_EXTRAS
    assert [button.icon for button in form.buttons[: len(SECTIONS)]] == [icons.SECTIONS[key] for key in SECTION_KEYS]
    assert all(button.icon.startswith("textures/") for button in form.buttons)
    assert "§e4§7 of §e10" in form.content


def test_section_rows_show_the_live_state(plugin, server, admin, switch_on):
    plugin.menus.open(admin)
    form = shown(server, admin)
    assert button_named(form, "Mob cap").text == "§0Mob cap\n§8[ §4Off§8, 30 per chunk §8]"
    assert button_named(form, "Projectile cap").text == "§0Projectile cap\n§8[ §2On§8, 200 per chunk §8]"
    assert button_named(form, "General").text == "§0General\n§8[ Budget and protected mobs §8]"

    switch_on("mob_cap", mob_cap__per_chunk=45)
    plugin.menus.open(admin)
    form = shown(server, admin)
    assert button_named(form, "Mob cap").text == "§0Mob cap\n§8[ §2On§8, 45 per chunk §8]"
    assert "§e5§7 of §e10" in form.content


def test_section_page_shows_the_summary_and_every_option(plugin, server, admin):
    plugin.menus.open_section(admin, "tnt_guard")
    form = shown(server, admin)
    assert form.title == "TNT chain guard"
    assert form.content.startswith("§7Stops a TNT blast from setting off an endless chain.\n\n")
    assert "§7Enabled: §f§aOn" in form.content
    assert "§7Blasts before damping: §f16" in form.content
    assert labels(form) == ["Turn off", "Change settings", "How it works", "Reset to defaults", "Back"]

    plugin.menus.open_section(admin, "general")
    assert labels(shown(server, admin)) == ["Change settings", "How it works", "Reset to defaults", "Back"]


def test_switch_saves_and_restarts_the_modules(plugin, server, admin, tmp_path, monkeypatch):
    starts = []
    monkeypatch.setattr(plugin.item_merge, "start", lambda: starts.append("item_merge"))

    plugin.menus.open_section(admin, "mob_cap")
    press(shown(server, admin), admin, "Turn on")

    assert plugin.settings.mob_cap.enabled is True
    assert written(tmp_path)["mob_cap"]["enabled"] is True
    assert starts == ["item_merge"]
    assert plugin.mob_cap.admit in plugin.listeners.spawn_gates
    assert admin.messages[-1].endswith("§aMob cap is now on.")

    page = shown(server, admin)
    assert labels(page)[0] == "Turn off"
    press(page, admin, "Turn off")
    assert plugin.settings.mob_cap.enabled is False
    assert written(tmp_path)["mob_cap"]["enabled"] is False


def test_editor_picks_a_control_for_each_kind(plugin, server, admin):
    plugin.menus.open_editor(admin, "afk")
    form = shown(server, admin)
    options = section_named("afk").options[1:]
    assert [control.text for control in form.controls[0::2]] == [f"§7{option.hint}" for option in options]

    inputs = dict(zip((option.key for option in options), form.controls[1::2], strict=True))
    assert isinstance(inputs["idle_minutes"], fake_endstone.TextInput)
    assert isinstance(inputs["warn_seconds"], fake_endstone.Slider)
    assert isinstance(inputs["dimension"], fake_endstone.Dropdown)
    assert isinstance(inputs["x"], fake_endstone.TextInput)
    assert (inputs["warn_seconds"].min, inputs["warn_seconds"].max, inputs["warn_seconds"].step) == (10, 300, 10)
    assert inputs["warn_seconds"].default_value == 60
    assert inputs["dimension"].options == ["overworld", "nether", "the_end"]
    assert inputs["dimension"].default_index == 0
    assert inputs["x"].default_value == "0"
    assert inputs["x"].placeholder == "-30000000 to 30000000"

    plugin.menus.open_editor(admin, "lag_clear")
    form = shown(server, admin)
    assert "Enabled" not in [getattr(control, "label", None) for control in form.controls]
    assert isinstance(form.controls[slot(form, "Clear farm animals")], fake_endstone.Toggle)
    assert form.controls[slot(form, "Clear farm animals")].default_value is False
    assert isinstance(form.controls[slot(form, "Emergency mob count")], fake_endstone.Slider)

    plugin.menus.open_editor(admin, "general")
    form = shown(server, admin)
    budget = form.controls[slot(form, "Sweep budget in ms")]
    assert isinstance(budget, fake_endstone.Slider)
    assert (budget.min, budget.max, budget.step, budget.default_value) == (0.5, 10.0, 0.5, 3.0)


def test_a_long_list_is_split_into_boxes_that_fit(plugin, server, admin, tmp_path):
    plugin.menus.open_editor(admin, "general")
    form = shown(server, admin)
    boxes = [control for control in form.controls if isinstance(control, fake_endstone.TextInput)]
    assert len(boxes) > 2
    assert all(len(box.default_value) <= TEXT_BOX_LENGTH for box in boxes)
    assert boxes[-1].default_value == ""
    assert read_listing(",".join(box.default_value for box in boxes), []) == plugin.settings.general.protected_types

    answers = untouched(form)
    answers[-1] = "Minecraft:Cow, minecraft:pig"
    submit(form, admin, answers)
    protected = plugin.settings.general.protected_types
    assert protected[:2] == ["minecraft:villager", "minecraft:villager_v2"]
    assert protected[-2:] == ["minecraft:cow", "minecraft:pig"]
    assert written(tmp_path)["general"]["protected_types"] == protected

    answers[-1] = 5
    submit(form, admin, answers)
    assert plugin.settings.general.protected_types == protected


def test_saving_clamps_and_writes_the_file(plugin, server, admin, tmp_path):
    plugin.menus.open_editor(admin, "mob_cap")
    form = shown(server, admin)
    answers = untouched(form)
    answers[slot(form, "Mobs per chunk")] = 9999.0
    submit(form, admin, answers)

    assert plugin.settings.mob_cap.per_chunk == 200
    assert written(tmp_path)["mob_cap"]["per_chunk"] == 200
    assert admin.messages[-1].endswith("§aSaved 1 change to Mob cap.")

    page = shown(server, admin)
    assert page.title == "Mob cap"
    assert "§7Mobs per chunk: §f200" in page.content


def test_saving_the_same_values_restarts_nothing(plugin, server, admin, monkeypatch):
    starts = []
    monkeypatch.setattr(plugin.item_merge, "start", lambda: starts.append("item_merge"))

    plugin.menus.open_editor(admin, "piston_guard")
    form = shown(server, admin)
    submit(form, admin, untouched(form))

    assert starts == []
    assert admin.messages[-1].endswith("§7Nothing in Piston guard changed.")
    assert shown(server, admin).title == "Piston guard"


def test_answers_without_label_slots_still_line_up(plugin, server, admin):
    plugin.menus.open_editor(admin, "item_merge")
    submit(shown(server, admin), admin, [20.0, 8.0])

    assert plugin.settings.item_merge.interval_seconds == 20
    assert plugin.settings.item_merge.radius == 8


def test_junk_answers_leave_the_setting_as_it_was(plugin, server, admin, switch_on):
    switch_on(
        afk__idle_minutes=45,
        afk__warn_seconds=120,
        afk__dimension="nether",
        afk__x=500,
        afk__y=70,
        afk__z=-500,
    )
    plugin.menus.open_editor(admin, "afk")
    submit(shown(server, admin), admin, [None, "soon", None, {}, None, 7, None, "east", None, None, None, []])

    afk = plugin.settings.afk
    assert (afk.idle_minutes, afk.warn_seconds, afk.dimension) == (45, 120, "nether")
    assert (afk.x, afk.y, afk.z) == (500, 70, -500)


def test_closing_the_editor_goes_back_to_the_section(plugin, server, admin):
    plugin.menus.open_editor(admin, "vehicle_cap")
    shown(server, admin).on_close(admin)
    assert shown(server, admin).title == "Vehicle cap"


def test_reset_asks_first_and_needs_the_first_button(plugin, server, admin, switch_on, tmp_path):
    switch_on(tnt_guard__chain_limit=3)
    plugin.menus.open_section(admin, "tnt_guard")
    press(shown(server, admin), admin, "Reset to defaults")

    question = shown(server, admin)
    assert isinstance(question, fake_endstone.MessageForm)
    assert (question.button1, question.button2) == ("§2Yes", "§4No")
    assert plugin.settings.tnt_guard.chain_limit == 3

    question.on_submit(admin, 1)
    assert plugin.settings.tnt_guard.chain_limit == 3
    assert shown(server, admin).title == "TNT chain guard"

    question.on_submit(admin, 0)
    assert plugin.settings.is_default("tnt_guard")
    assert written(tmp_path)["tnt_guard"]["chain_limit"] == 16
    assert button_named(shown(server, admin), "Reset to defaults").text.endswith("[ Already at the defaults §8]")


def test_use_where_i_am_standing_writes_the_position(plugin, server, tmp_path):
    player = server.join("Ozz", 12.7, 70.2, -3.4, server.level.get_dimension("Nether"))
    player.is_op = True
    plugin.menus.open_section(player, "afk")
    press(shown(server, player), player, "Use where I am standing")

    afk = plugin.settings.afk
    assert (afk.dimension, afk.x, afk.y, afk.z) == ("nether", 12, 70, -4)
    assert written(tmp_path)["afk"]["z"] == -4
    assert player.messages[-1].endswith("§aIdle players will be moved to 12, 70, -4 in the Nether.")


def test_a_dimension_the_setting_cannot_name_is_refused(plugin, server):
    player = server.join("Ozz", 5, 80, 5, fake_endstone.Dimension(server.level, "Aether"))
    player.is_op = True
    plugin.menus.open_section(player, "afk")
    press(shown(server, player), player, "Use where I am standing")

    assert plugin.settings.is_default("afk")
    assert len(player.errors) == 1


def test_lag_clear_page_starts_and_cancels_a_countdown(plugin, server, admin, countdown):
    plugin.menus.open_section(admin, "lag_clear")
    press(shown(server, admin), admin, "Clear now")
    assert countdown.started == 1

    page = shown(server, admin)
    assert "Clear now" not in labels(page)
    press(page, admin, "Cancel the countdown")
    assert countdown.cancelled == 1
    assert "Clear now" in labels(shown(server, admin))


def test_a_player_without_the_permission_changes_nothing(plugin, server, admin, countdown, monkeypatch, tmp_path):
    guest = server.join("Guest")
    menus = plugin.menus
    reloads = []
    monkeypatch.setattr(plugin, "reload_settings", lambda: reloads.append("reload") or True)
    plugin.settings.change("tnt_guard", "chain_limit", 3)
    on_disk = (tmp_path / "config.toml").read_text(encoding="utf-8")

    menus.command(guest, [])

    menus.open(admin)
    button_named(shown(server, admin), "Reload from file").on_click(guest)

    menus.open_section(admin, "mob_cap")
    button_named(shown(server, admin), "Turn on").on_click(guest)

    menus.open_editor(admin, "mob_cap")
    submit(shown(server, admin), guest, [None, 100])

    menus.confirm_reset(admin, "tnt_guard")
    shown(server, admin).on_submit(guest, 0)

    menus.open_section(admin, "afk")
    button_named(shown(server, admin), "Use where I am standing").on_click(guest)

    menus.open_section(admin, "lag_clear")
    button_named(shown(server, admin), "Clear now").on_click(guest)

    countdown.counting_down = True
    menus.open_section(admin, "lag_clear")
    button_named(shown(server, admin), "Cancel the countdown").on_click(guest)

    server.scheduler.advance(1)
    assert guest.forms == []
    assert len(guest.errors) == 8
    assert reloads == []
    assert (countdown.started, countdown.cancelled) == (0, 0)
    assert plugin.settings.mob_cap.enabled is False
    assert plugin.settings.mob_cap.per_chunk == 30
    assert plugin.settings.tnt_guard.chain_limit == 3
    assert plugin.settings.is_default("afk")
    assert (tmp_path / "config.toml").read_text(encoding="utf-8") == on_disk


def test_the_console_reloads_the_file(plugin, server, tmp_path):
    edit_file(tmp_path, "piston_guard", "suspend_seconds", 90)
    console = server.command_sender
    plugin.menus.command(console, [])

    assert plugin.settings.piston_guard.suspend_seconds == 90
    assert console.messages[-1].endswith("§aconfig.toml was read again and every module restarted.")


def test_reload_from_file_picks_up_a_hand_edit(plugin, server, admin, tmp_path):
    plugin.menus.open(admin)
    form = shown(server, admin)
    edit_file(tmp_path, "mob_cap", "per_chunk", 75)
    press(form, admin, "Reload from file")

    assert plugin.settings.mob_cap.per_chunk == 75
    assert button_named(shown(server, admin), "Mob cap").text.endswith("75 per chunk §8]")


def test_report_pages_draw_tables_and_an_empty_list(plugin, server, admin, monkeypatch):
    monkeypatch.setattr(plugin.report, "summary", lambda: SAMPLE_TABLES)
    monkeypatch.setattr(plugin.report, "census", lambda: [], raising=False)
    plugin.menus.open(admin)
    main = shown(server, admin)

    press(main, admin, "Server report")
    report = shown(server, admin)
    assert report.title == "Server report"
    assert report.content == "§6Timings\n§7MSPT: §f12.5\n§7TPS: §f20.0\n\n§6Chunks\n§7Loaded: §f1400"
    assert labels(report) == ["Refresh", "Back"]

    monkeypatch.setattr(plugin.report, "summary", lambda: [])
    press(report, admin, "Refresh")
    assert shown(server, admin).content == "§7There is nothing to show yet."

    press(main, admin, "Entity census")
    census = shown(server, admin)
    assert census.title == "Entity census"
    assert census.content == "§7There is nothing to show yet."

    monkeypatch.setattr(plugin.report, "census", lambda: SAMPLE_TABLES)
    press(census, admin, "Refresh")
    census = shown(server, admin)
    assert census.content.startswith("§6Timings\n§7MSPT: §f12.5")
    press(census, admin, "Back")
    assert shown(server, admin).title == "Let Me Perform"


def test_guide_has_a_page_for_every_section(plugin, server, admin):
    plugin.menus.open_guide(admin)
    guide = shown(server, admin)
    titles = [section.title for section in SECTIONS]
    assert labels(guide) == ["Start here", "Reading /lag", *titles, "What it cannot do", "Back"]

    press(guide, admin, "Mob stacker")
    page = shown(server, admin)
    assert page.title == "Mob stacker"
    assert "§7A stacked mob dies one at a time." in page.content
    assert labels(page) == ["Back"]

    press(page, admin, "Back")
    assert shown(server, admin).title == "Guide"


def test_how_it_works_returns_to_its_section(plugin, server, admin):
    plugin.menus.open_section(admin, "piston_guard")
    press(shown(server, admin), admin, "How it works")
    page = shown(server, admin)
    assert page.title == "Piston guard"
    assert "more than 40 times in 10 seconds is held still for 30 seconds" in page.content
    assert button_named(page, "Back").text == "§0Back\n§8[ Piston guard §8]"

    press(page, admin, "Back")
    assert labels(shown(server, admin))[0] == "Turn off"


def test_guide_text_is_filled_in_and_safe_in_a_form():
    for topic in TOPICS:
        text = " ".join(topic.paragraphs)
        assert not any(mark in text for mark in "{}%§"), topic.key

    assert topic_named("mob_cap").paragraphs[0].startswith("A spawn in a chunk that already holds 30 mobs")


def test_every_icon_is_a_texture_path():
    paths = []
    for name, value in vars(icons).items():
        if name.startswith("_"):
            continue
        paths.extend(value.values() if isinstance(value, dict) else [value])

    assert len(paths) > len(SECTIONS)
    assert all(path.startswith("textures/") and "." not in path for path in paths)


def test_no_page_uses_one_icon_twice(plugin, server, admin, countdown, monkeypatch):
    monkeypatch.setattr(plugin.report, "summary", lambda: SAMPLE_TABLES)
    monkeypatch.setattr(plugin.report, "census", lambda: [], raising=False)
    menus = plugin.menus
    openers = [menus.open, menus.open_guide, menus.open_summary, menus.open_census]
    pages = []
    for opener in openers:
        opener(admin)
        pages.append(shown(server, admin))

    for key in SECTION_KEYS:
        menus.open_section(admin, key)
        pages.append(shown(server, admin))

    countdown.counting_down = True
    menus.open_section(admin, "lag_clear")
    pages.append(shown(server, admin))

    for page in pages:
        used = [button.icon for button in page.buttons]
        assert all(icon.startswith("textures/") for icon in used), page.title
        assert len(set(used)) == len(used), page.title


def test_a_form_is_not_sent_to_a_player_who_left(plugin, server, admin):
    plugin.menus.open(admin)
    server.quit(admin)
    server.scheduler.advance(1)
    assert admin.forms == []
