from endstone_let_me_perform.core.tables import PROTECTED_TYPES

TOGGLE = "toggle"
WHOLE = "whole"
DECIMAL = "decimal"
CHOICE = "choice"
LISTING = "listing"

WORLD_LIMIT = 30000000


class Option:
    __slots__ = ("key", "label", "kind", "default", "lowest", "highest", "step", "choices", "hint")

    def __init__(self, key, label, kind, default, hint, lowest=0, highest=0, step=1, choices=()):
        self.key = key
        self.label = label
        self.kind = kind
        self.default = default
        self.hint = hint
        self.lowest = lowest
        self.highest = highest
        self.step = step
        self.choices = choices


class Section:
    __slots__ = ("key", "title", "summary", "options")

    def __init__(self, key, title, summary, options):
        self.key = key
        self.title = title
        self.summary = summary
        self.options = options

    @property
    def has_switch(self) -> bool:
        return self.options[0].key == "enabled"

    def option(self, key: str) -> Option:
        for option in self.options:
            if option.key == key:
                return option
        raise KeyError(f"{self.key} has no option called {key}")


def toggle(key, label, default, hint):
    return Option(key, label, TOGGLE, default, hint)


def whole(key, label, default, lowest, highest, step, hint):
    return Option(key, label, WHOLE, default, hint, lowest, highest, step)


def decimal(key, label, default, lowest, highest, step, hint):
    return Option(key, label, DECIMAL, default, hint, lowest, highest, step)


def choice(key, label, default, choices, hint):
    return Option(key, label, CHOICE, default, hint, choices=choices)


def listing(key, label, default, hint):
    return Option(key, label, LISTING, default, hint)


def switch(default):
    return toggle("enabled", "Enabled", default, "Turns this module on or off.")


SECTIONS = (
    Section("general", "General", "Settings every module shares.", (
        decimal("sweep_budget_ms", "Sweep budget in ms", 3.0, 0.5, 10.0, 0.5, "The most time one background pass may spend in a single tick. A pass that runs out carries on next time."),
        listing("protected_types", "Protected mobs", PROTECTED_TYPES, "Mob ids no module ever caps, stacks or clears. Mobs from other add-ons are always left alone."),
    )),
    Section("mob_cap", "Mob cap", "Stops new mobs spawning in a chunk that is already full.", (
        switch(False),
        whole("per_chunk", "Mobs per chunk", 30, 5, 200, 5, "A spawn in a chunk already holding this many mobs is cancelled. This also trims a chunk that loads with more."),
    )),
    Section("projectile_cap", "Projectile cap", "Bounds how many arrows, snowballs and other thrown things one chunk can hold.", (
        switch(True),
        whole("per_chunk", "Projectiles per chunk", 200, 20, 1000, 10, "A projectile fired in a chunk already holding this many is cancelled."),
    )),
    Section("vehicle_cap", "Vehicle cap", "Limits boats and minecarts placed by hand in one chunk.", (
        switch(False),
        whole("per_chunk", "Vehicles per chunk", 16, 1, 64, 1, "Placing a boat or minecart in a chunk already holding this many is refused, and the item stays in the hand."),
    )),
    Section("item_merge", "Item merging", "Joins matching dropped items that lie close together into one stack.", (
        switch(True),
        whole("interval_seconds", "Seconds between passes", 5, 1, 60, 1, "How often dropped items are checked for neighbours to merge with."),
        whole("radius", "Merge distance in blocks", 4, 1, 16, 1, "Items inside the same cube of this size are merged."),
    )),
    Section("mob_stacker", "Mob stacker", "Folds crowds of the same mob into one mob that carries a count.", (
        switch(False),
        whole("interval_seconds", "Seconds between passes", 3, 1, 60, 1, "How often chunks are checked for mobs to stack."),
        whole("max_stack", "Largest stack", 20, 2, 100, 1, "The most mobs one stacked mob can stand for."),
        whole("chunk_limit", "Mobs left per chunk", 30, 0, 200, 5, "After stacking, mobs past this number in a chunk are removed. 0 removes nothing."),
    )),
    Section("lag_clear", "Lag clear", "Sweeps away dropped items and stray mobs on a timer, with a warning first.", (
        switch(False),
        whole("interval_minutes", "Minutes between clears", 20, 5, 240, 5, "How long the timer waits between one clear and the next."),
        whole("warning_seconds", "Warning in seconds", 30, 5, 120, 5, "How long players are warned in chat before a clear runs."),
        toggle("clear_items", "Clear dropped items", True, "Removes items lying on the ground."),
        toggle("clear_xp", "Clear XP orbs", True, "Removes experience orbs nobody picked up."),
        toggle("clear_arrows", "Clear arrows", True, "Removes arrows stuck in the ground. Thrown tridents are never removed."),
        toggle("clear_hostiles", "Clear hostile mobs", True, "Removes hostile mobs that have no name tag."),
        toggle("clear_passives", "Clear farm animals", False, "Removes unnamed bats, chickens, cows, mooshrooms, pigs, polar bears and sheep."),
        toggle("emergency", "Emergency clear", True, "Runs a clear at once, with no warning, when the counts below are passed."),
        whole("emergency_mobs", "Emergency mob count", 500, 100, 5000, 50, "Hostile mobs loaded at once before an emergency clear."),
        whole("emergency_drops", "Emergency drop count", 300, 100, 5000, 50, "Dropped items and XP orbs loaded at once before an emergency clear."),
        whole("emergency_cooldown_seconds", "Emergency cooldown in seconds", 120, 30, 1800, 30, "The shortest gap between two emergency clears."),
    )),
    Section("piston_guard", "Piston guard", "Pauses a piston that fires too fast, without breaking anything.", (
        switch(True),
        whole("moves_per_window", "Moves allowed", 40, 10, 1000, 10, "How many times one piston may move inside the window. A piston cannot move more than about 10 times a second."),
        whole("window_seconds", "Window in seconds", 10, 1, 60, 1, "The stretch of time the moves are counted over."),
        whole("suspend_seconds", "Pause in seconds", 30, 5, 600, 5, "How long a piston that went over is held still."),
    )),
    Section("tnt_guard", "TNT chain guard", "Stops a TNT blast from setting off an endless chain.", (
        switch(True),
        whole("chain_limit", "Blasts before damping", 16, 1, 200, 1, "After this many blasts in one area, further blasts stop lighting more TNT."),
        whole("hard_limit", "Blasts before cancelling", 48, 1, 500, 1, "After this many blasts in one area, further blasts are cancelled outright."),
        whole("window_seconds", "Window in seconds", 5, 1, 30, 1, "The stretch of time the blasts are counted over."),
        whole("cell_size", "Area size in blocks", 16, 4, 64, 4, "Blasts are counted per cube of this size."),
    )),
    Section("travel_cooldown", "Travel cooldowns", "Spaces out elytra rockets and Riptide launches, which load chunks fastest.", (
        switch(False),
        whole("rocket_seconds", "Rocket cooldown in seconds", 3, 0, 30, 1, "The wait between two firework boosts while gliding. 0 turns it off."),
        whole("riptide_seconds", "Riptide cooldown in seconds", 2, 0, 30, 1, "The wait between two Riptide trident launches. 0 turns it off."),
    )),
    Section("afk", "AFK move", "Moves idle players to one shared spot so they stop holding chunks loaded.", (
        switch(False),
        whole("idle_minutes", "Minutes idle", 10, 1, 120, 1, "How long a player must stand still before being moved."),
        whole("warn_seconds", "Warning in seconds", 60, 10, 300, 10, "How long before the move the player is warned in chat."),
        choice("dimension", "Dimension", "overworld", ("overworld", "nether", "the_end"), "The dimension of the spot idle players are moved to. Set the spot before turning this on: the menu can use where you are standing."),
        whole("x", "X", 0, -WORLD_LIMIT, WORLD_LIMIT, 1, "The X coordinate of the spot."),
        whole("y", "Y", 100, -64, 320, 1, "The Y coordinate of the spot."),
        whole("z", "Z", 0, -WORLD_LIMIT, WORLD_LIMIT, 1, "The Z coordinate of the spot."),
    )),
    Section("report", "Reports", "What the /lag report samples and what the server log is told at start up.", (
        toggle("boot_audit", "Check settings at start up", True, "Reads server.properties when the server starts and logs anything worth changing."),
        whole("chunk_sample_seconds", "Seconds between chunk counts", 60, 10, 600, 10, "How often loaded chunks are counted for the /lag report."),
        toggle("public_tps", "Let everyone use /tps", True, "When off, /tps answers operators only."),
    )),
)

SECTION_KEYS = tuple(section.key for section in SECTIONS)


def section_named(key: str) -> Section:
    for section in SECTIONS:
        if section.key == key:
            return section
    raise KeyError(f"There is no settings section called {key}")


def clamp(value, lowest, highest):
    return max(lowest, min(highest, value))


def fresh(default):
    return list(default) if isinstance(default, (list, tuple)) else default


def read_value(option: Option, raw, fallback):
    if option.kind == TOGGLE:
        return raw if isinstance(raw, bool) else fallback

    if option.kind == WHOLE:
        if isinstance(raw, bool):
            return fallback
        try:
            return clamp(int(float(raw)), option.lowest, option.highest)
        except (TypeError, ValueError):
            return fallback

    if option.kind == DECIMAL:
        if isinstance(raw, bool):
            return fallback
        try:
            return clamp(float(raw), option.lowest, option.highest)
        except (TypeError, ValueError):
            return fallback

    if option.kind == CHOICE:
        text = str(raw).strip().lower()
        return text if text in option.choices else fallback

    return read_listing(raw, fallback)


def read_listing(raw, default) -> list:
    if isinstance(raw, str):
        raw = raw.replace("\n", ",").split(",")
    if not isinstance(raw, (list, tuple)):
        return list(default)

    cleaned = []
    for entry in raw:
        text = str(entry).strip().lower()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


class Values:
    def __init__(self, section: Section):
        for option in section.options:
            setattr(self, option.key, fresh(option.default))


class Settings:
    def __init__(self):
        self.sections = {section.key: Values(section) for section in SECTIONS}
        for key, values in self.sections.items():
            setattr(self, key, values)

    def section(self, key: str) -> Values:
        return self.sections[key]

    def apply_from(self, raw) -> int:
        data = raw.unwrap() if hasattr(raw, "unwrap") else raw
        if not isinstance(data, dict):
            data = {}

        missing = 0
        for section in SECTIONS:
            table = data.get(section.key)
            if not isinstance(table, dict):
                table = {}

            values = self.sections[section.key]
            for option in section.options:
                if option.key not in table:
                    missing += 1
                default = fresh(option.default)
                setattr(values, option.key, read_value(option, table.get(option.key, default), default))
        return missing

    def write_into(self, document) -> None:
        for section in SECTIONS:
            if section.key not in document:
                document[section.key] = {}

            table = document[section.key]
            values = self.sections[section.key]
            for option in section.options:
                table[option.key] = fresh(getattr(values, option.key))

    def change(self, section_key: str, option_key: str, raw) -> None:
        option = section_named(section_key).option(option_key)
        values = self.sections[section_key]
        setattr(values, option_key, read_value(option, raw, getattr(values, option_key)))

    def reset(self, section_key: str) -> None:
        values = self.sections[section_key]
        for option in section_named(section_key).options:
            setattr(values, option.key, fresh(option.default))

    def is_default(self, section_key: str) -> bool:
        values = self.sections[section_key]
        return all(getattr(values, option.key) == fresh(option.default) for option in section_named(section_key).options)
