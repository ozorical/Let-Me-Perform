from functools import partial

from endstone import Player
from endstone.form import ActionForm, MessageForm, ModalForm

from endstone_let_me_perform.core.messages import tell, tell_failure, tell_success
from endstone_let_me_perform.menus import icons, theme
from endstone_let_me_perform.menus.editor import Editor
from endstone_let_me_perform.menus.guide import TOPICS, topic_named
from endstone_let_me_perform.settings import LISTING, SECTIONS, TOGGLE, Option, Section, section_named

PERMISSION = "lmp.command.config"
TITLE = "Let Me Perform"

ROW_HINTS = {
    "general": "Budget and protected mobs",
    "mob_cap": "{per_chunk} per chunk",
    "projectile_cap": "{per_chunk} per chunk",
    "vehicle_cap": "{per_chunk} per chunk",
    "item_merge": "every {interval_seconds} seconds",
    "mob_stacker": "stacks of {max_stack}",
    "lag_clear": "every {interval_minutes} minutes",
    "piston_guard": "pauses for {suspend_seconds} seconds",
    "tnt_guard": "damps after {chain_limit} blasts",
    "travel_cooldown": "rockets {rocket_seconds}s, Riptide {riptide_seconds}s",
    "afk": "after {idle_minutes} minutes idle",
    "report": "What /lag and /tps show",
}

DIMENSIONS = {
    "Overworld": ("overworld", "the Overworld"),
    "Nether": ("nether", "the Nether"),
    "TheEnd": ("the_end", "the End"),
}


class Menus:
    def __init__(self, plugin):
        self.plugin = plugin

    def command(self, sender, args: list) -> None:
        if not self.allowed(sender):
            return

        if not isinstance(sender, Player):
            tell(sender, "The menu only opens in game, so this reloads config.toml.")
            self.reload(sender)
            return

        self.open(sender)

    def open(self, player) -> None:
        settings = self.plugin.settings
        switched = [section for section in SECTIONS if section.has_switch]
        running = sum(settings.section(section.key).enabled for section in switched)
        content = "\n".join((
            theme.prose(self.plugin.report.headline()),
            theme.prose(f"Modules on: {theme.count(running)} of {theme.count(len(switched))}"),
        ))

        form = ActionForm(title=TITLE, content=content)
        for section in SECTIONS:
            form.add_button(
                theme.button(section.title, self.row_hint(section)),
                icons.SECTIONS[section.key],
                partial(self.open_section, key=section.key),
            )
        form.add_button(theme.button("Server report", "Timings, chunks and guards"), icons.SERVER_REPORT, self.open_summary)
        form.add_button(theme.button("Entity census", "What is loaded, by type"), icons.ENTITY_CENSUS, self.open_census)
        form.add_button(theme.button("Guide", "How each module works"), icons.GUIDE, self.open_guide)
        form.add_button(theme.button("Reload from file", "Reads config.toml again"), icons.RELOAD, self.reload_from_file)
        self.show(player, form)

    def row_hint(self, section: Section) -> str:
        values = self.plugin.settings.section(section.key)
        detail = ROW_HINTS[section.key].format(**vars(values))
        if not section.has_switch:
            return detail
        return f"{theme.switch(values.enabled)}, {detail}"

    def open_section(self, player, key: str) -> None:
        section = section_named(key)
        values = self.plugin.settings.section(key)
        lines = [theme.prose(section.summary), ""]
        lines.extend(theme.line(option.label, describe(option, getattr(values, option.key))) for option in section.options)

        form = ActionForm(title=section.title, content="\n".join(lines))
        if section.has_switch:
            on = values.enabled
            form.add_button(
                theme.button("Turn off" if on else "Turn on", f"{theme.switch(on)} now"),
                icons.TURN_OFF if on else icons.TURN_ON,
                partial(self.set_switch, key=key, on=not on),
            )

        form.add_button(theme.button("Change settings", "Edit the values above"), icons.CHANGE_SETTINGS, partial(self.open_editor, key=key))

        if key == "afk":
            form.add_button(theme.button("Use where I am standing", "Sets the dimension and X, Y, Z"), icons.USE_MY_POSITION, self.use_position)

        if key == "lag_clear":
            if self.plugin.lag_clear.counting_down:
                form.add_button(theme.button("Cancel the countdown", "A clear is on its way"), icons.CANCEL_COUNTDOWN, self.cancel_clear)
            else:
                form.add_button(theme.button("Clear now", f"Starts the {values.warning_seconds} second warning"), icons.CLEAR_NOW, self.start_clear)

        reopen = partial(self.open_section, key=key)
        read_guide = partial(self.open_topic, key=key, back=reopen, back_to=section.title)
        reset_hint = "Already at the defaults" if self.plugin.settings.is_default(key) else "Asks first"
        form.add_button(theme.button("How it works", "Its page in the guide"), icons.GUIDE, read_guide)
        form.add_button(theme.button("Reset to defaults", reset_hint), icons.RESET, partial(self.confirm_reset, key=key))
        form.add_button(theme.button("Back", "Main menu"), icons.BACK, self.open)
        self.show(player, form)

    def set_switch(self, player, key: str, on: bool) -> None:
        if not self.allowed(player):
            return

        self.plugin.settings.change(key, "enabled", on)
        self.commit(player, f"{section_named(key).title} is now {'on' if on else 'off'}.")
        self.open_section(player, key)

    def open_editor(self, player, key: str) -> None:
        section = section_named(key)
        editor = Editor(section, self.plugin.settings.section(key))
        form = ModalForm(
            title=section.title,
            controls=editor.controls,
            submit_button="Save",
            on_submit=partial(self.save_answers, key=key, editor=editor),
            on_close=partial(self.open_section, key=key),
        )
        self.show(player, form)

    def save_answers(self, player, data: str, key: str, editor: Editor) -> None:
        if not self.allowed(player):
            return

        settings = self.plugin.settings
        values = settings.section(key)
        changed = 0
        for option, raw in editor.read(data).items():
            before = getattr(values, option.key)
            settings.change(key, option.key, raw)
            changed += getattr(values, option.key) != before

        title = section_named(key).title
        if changed:
            self.commit(player, f"Saved {changed} {'change' if changed == 1 else 'changes'} to {title}.")
        else:
            tell(player, f"Nothing in {title} changed.")
        self.open_section(player, key)

    def confirm_reset(self, player, key: str) -> None:
        section = section_named(key)
        question = f"Put every setting in {section.title} back to its default?"
        if section.has_switch:
            question += f" That includes the switch, which starts {'on' if section.option('enabled').default else 'off'}."

        form = MessageForm(
            title="Reset to defaults",
            content=theme.prose(question),
            button1=theme.YES,
            button2=theme.NO,
            on_submit=partial(self.answer_reset, key=key),
            on_close=partial(self.open_section, key=key),
        )
        self.show(player, form)

    def answer_reset(self, player, selection: int, key: str) -> None:
        if selection != 0:
            self.open_section(player, key)
            return

        if not self.allowed(player):
            return

        self.plugin.settings.reset(key)
        self.commit(player, f"{section_named(key).title} is back to its defaults.")
        self.open_section(player, key)

    def use_position(self, player) -> None:
        if not self.allowed(player):
            return

        location = player.location
        dimension = DIMENSIONS.get(location.dimension.name)
        if dimension is None:
            tell_failure(player, "The AFK spot has to be in the Overworld, the Nether or the End.")
            self.open_section(player, "afk")
            return

        choice, spoken = dimension
        settings = self.plugin.settings
        settings.change("afk", "dimension", choice)
        settings.change("afk", "x", location.block_x)
        settings.change("afk", "y", location.block_y)
        settings.change("afk", "z", location.block_z)

        spot = settings.afk
        self.commit(player, f"Idle players will be moved to {spot.x}, {spot.y}, {spot.z} in {spoken}.")
        self.open_section(player, "afk")

    def start_clear(self, player) -> None:
        if not self.allowed(player):
            return

        if self.plugin.lag_clear.start_countdown():
            tell_success(player, "The lag clear countdown has started.")
        else:
            tell_failure(player, "A lag clear is already on its way.")
        self.open_section(player, "lag_clear")

    def cancel_clear(self, player) -> None:
        if not self.allowed(player):
            return

        if self.plugin.lag_clear.cancel_countdown():
            tell_success(player, "The lag clear countdown was cancelled.")
        else:
            tell_failure(player, "There is no countdown to cancel.")
        self.open_section(player, "lag_clear")

    def open_summary(self, player) -> None:
        self.show_tables(player, "Server report", self.plugin.report.summary(), self.open_summary)

    def open_census(self, player) -> None:
        self.show_tables(player, "Entity census", self.plugin.report.census(), self.open_census)

    def show_tables(self, player, title: str, blocks: list, refresh) -> None:
        content = theme.tables(blocks) if blocks else theme.prose("There is nothing to show yet.")
        form = ActionForm(title=title, content=content)
        form.add_button(theme.button("Refresh", "Reads the numbers again"), icons.REFRESH, refresh)
        form.add_button(theme.button("Back", "Main menu"), icons.BACK, self.open)
        self.show(player, form)

    def open_guide(self, player) -> None:
        form = ActionForm(title="Guide", content=theme.prose("What each module does, why it is there, and what no plugin can do."))
        for topic in TOPICS:
            form.add_button(
                theme.button(topic.title, topic.hint),
                icons.TOPICS[topic.key],
                partial(self.open_topic, key=topic.key, back=self.open_guide, back_to="Guide"),
            )
        form.add_button(theme.button("Back", "Main menu"), icons.BACK, self.open)
        self.show(player, form)

    def open_topic(self, player, key: str, back, back_to: str) -> None:
        topic = topic_named(key)
        form = ActionForm(title=topic.title, content=theme.paragraphs(topic.paragraphs))
        form.add_button(theme.button("Back", back_to), icons.BACK, back)
        self.show(player, form)

    def reload_from_file(self, player) -> None:
        if not self.allowed(player):
            return

        self.reload(player)
        self.open(player)

    def reload(self, sender) -> None:
        if self.plugin.reload_settings():
            tell_success(sender, "config.toml was read again and every module restarted.")
        else:
            tell_failure(sender, "config.toml could not be read, so the settings in memory were kept. The console has the details.")

    def commit(self, player, text: str) -> None:
        saved = self.plugin.save_settings()
        self.plugin.apply_settings()
        if saved:
            tell_success(player, text)
        else:
            tell_failure(player, f"{text} It could not be written to config.toml, so it will be lost at the next restart.")

    def allowed(self, sender) -> bool:
        if sender.has_permission(PERMISSION):
            return True

        tell_failure(sender, f"Changing these settings needs the {PERMISSION} permission.")
        return False

    def show(self, player, form) -> None:
        name = player.name

        def deliver() -> None:
            target = self.plugin.server.get_player(name)
            if target is not None:
                target.send_form(form)

        self.plugin.server.scheduler.run_task(self.plugin, deliver, delay=1)


def describe(option: Option, value) -> str:
    if option.kind == TOGGLE:
        return theme.state(value)
    if option.kind == LISTING:
        return ", ".join(value) or "none"
    return str(value)
