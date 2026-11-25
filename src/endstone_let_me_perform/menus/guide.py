from endstone_let_me_perform.settings import section_named


class Topic:
    __slots__ = ("key", "title", "hint", "paragraphs")

    def __init__(self, key, title, hint, paragraphs):
        self.key = key
        self.title = title
        self.hint = hint
        self.paragraphs = paragraphs


def about(section_key: str, hint: str, *paragraphs: str) -> Topic:
    section = section_named(section_key)
    defaults = {option.key: option.default for option in section.options}
    return Topic(section_key, section.title, hint, tuple(text.format(**defaults) for text in paragraphs))


TOPICS = (
    Topic("start", "Start here", "What it is for, first steps", (
        "Let Me Perform keeps entity counts down and stops machines that run away with the tick: caps for mobs, projectiles and vehicles, item merging, mob stacking, a timed clear, and guards for pistons and TNT.",
        "A fresh install turns on only the projectile cap, item merging, the piston guard and the TNT guard. Everything that removes mobs or items, or restricts players, starts off.",
        "Only vanilla mobs are ever capped, stacked or cleared. Mobs from other add-ons, mobs on the protected list and mobs a player has named are left alone.",
        "To begin, run /lag and /lag entities to see what the server is full of, then turn on one module at a time.",
        "/config-lmp opens this menu. /lag is the server report and /lag entities the census. /lagclear starts a clear with a warning, /lagclear now clears at once and /lagclear cancel stops a countdown. /tps shows the tick rate.",
    )),
    Topic("lag", "Reading /lag", "What the numbers mean", (
        "/lag shows tick timings, loaded chunks, entity counts and what each guard has done. Server report on the main menu shows the same.",
        "The server has 50 ms for each tick. MSPT is how long a tick takes, and TPS stays at 20 while ticks fit. Players feel the odd long tick far more than a high average.",
        "Look at loaded chunks first. The engine's work follows the number of loaded chunks much more closely than the number of players. Chunks are counted on a timer, so that figure can be a little old.",
        "/lag entities counts every loaded entity. Run it before changing a cap or a stack size, to see whether a busy chunk is full of animals, hostile mobs, items or villagers.",
    )),
    about(
        "general",
        "What the shared settings do",
        "These settings are shared by every module.",
        "Sweep budget is the most time one background pass may spend in a single tick, {sweep_budget_ms} ms by default. A pass that runs out stops there and carries on next time, so a big job never holds a tick up.",
        "Protected mobs lists the mob ids no module ever caps, stacks or clears. It starts with villagers, traders, golems, bosses, pets, mounts and armour stands. Write ids in full, such as minecraft:cow, with commas between them.",
        "Mobs from other add-ons are always left alone, whether they are on the list or not.",
    ),
    about(
        "mob_cap",
        "Spawns, chunk loads and pens",
        "A spawn in a chunk that already holds {per_chunk} mobs is cancelled. It works in every loaded chunk, whether or not a player is standing in it.",
        "It also trims a chunk that loads holding more than the cap, because Endstone cannot tell a fresh spawn from a chunk load. Check your biggest animal pen with /lag entities and set the cap above it before turning this on.",
        "Only vanilla mobs count. Protected mobs, named mobs and mobs from other add-ons are left alone.",
        "It starts off because it removes mobs.",
    ),
    about(
        "projectile_cap",
        "What counts and what never does",
        "A projectile fired in a chunk that already holds {per_chunk} is cancelled. That never bites in normal play, since an archer keeps about 60 arrows alive, but it stops a dispenser machine filling a chunk.",
        "It counts arrows, snowballs, eggs, splash and lingering potions, XP bottles, fire charges and wind charges.",
        "Tridents, fishing hooks, ender pearls and firework rockets are never counted. A cancelled throw could cost a player the trident, and an elytra boost is a rocket.",
        "It is on from the start.",
    ),
    about(
        "vehicle_cap",
        "Never removes a vehicle",
        "Placing a boat or minecart in a chunk that already holds {per_chunk} is refused, and the item stays in the hand.",
        "It only refuses placing by hand. It never removes a vehicle, so a build that already has more keeps them and cannot add to them.",
        "The cap is not applied when a vehicle appears, because Endstone reports a chunk loading the same way as a fresh spawn. Cancelling there would delete parked chest and hopper minecarts with what they hold.",
        "It starts off because it restricts players.",
    ),
    about(
        "item_merge",
        "Which drops join up",
        "Matching dropped items that lie close together are joined into one stack, so a farm's output is a handful of entities and not hundreds.",
        "Every {interval_seconds} seconds, items of the same kind inside the same cube of {radius} blocks are merged.",
        "No items are taken away, only joined, which is why it is on from the start.",
    ),
    about(
        "mob_stacker",
        "Loot, XP and what merges",
        "Crowds of the same mob in a chunk are folded into one mob that carries a count, up to {max_stack} in a stack. A pen of cows becomes a few stacked cows.",
        "A stacked mob dies one at a time. Each kill drops one mob's normal loot and XP, and the stack comes back one smaller.",
        "Endstone cannot see baby, colour or variant, so unlike mobs of one type merge: sheep of every colour share a stack, and babies stack with adults. Put a type on the protected list in General to keep it out.",
        "After stacking, mobs past {chunk_limit} in a chunk are removed; set that to 0 to remove nothing. Named mobs, protected mobs and mobs from other add-ons are never stacked.",
        "It starts off because it changes farms and removes mobs.",
    ),
    about(
        "lag_clear",
        "What goes and when",
        "Every {interval_minutes} minutes players get a {warning_seconds} second warning in chat, then dropped items and stray mobs are swept away.",
        "You choose what goes: dropped items, XP orbs, arrows stuck in the ground, hostile mobs with no name tag and, if you turn it on, unnamed farm animals. Thrown tridents are never removed.",
        "The emergency clear runs at once, with no warning, when more than {emergency_mobs} hostile mobs or {emergency_drops} drops are loaded. It then waits {emergency_cooldown_seconds} seconds before it can run again.",
        "/lagclear starts a countdown by hand, /lagclear now clears at once and /lagclear cancel stops a countdown. It starts off because it removes things players may want.",
    ),
    about(
        "piston_guard",
        "Pauses, never breaks",
        "Bedrock has no redstone event, so a piston is the one place a runaway clock can be seen.",
        "A piston that moves more than {moves_per_window} times in {window_seconds} seconds is held still for {suspend_seconds} seconds, then works again.",
        "It only pauses the piston. No block is ever broken, so the machine survives.",
        "A redstone budget and a hopper guard are not possible, because Endstone has no redstone or hopper event.",
    ),
    about(
        "tnt_guard",
        "Damping, then cancelling",
        "TNT blasts are counted per area, a cube of {cell_size} blocks, over {window_seconds} seconds.",
        "The first {chain_limit} blasts in an area are left alone. After that, further blasts stop lighting more TNT, and after {hard_limit} they are cancelled outright.",
        "It is on from the start, since it does nothing until a chain has already passed the first limit.",
    ),
    about(
        "travel_cooldown",
        "Rockets and Riptide",
        "Fast travel loads and generates chunks faster than anything else a player does, and chunk loading is the leading suspect for long ticks.",
        "With this on, a firework boost while gliding has to wait {rocket_seconds} seconds after the last one, and a Riptide launch {riptide_seconds} seconds. Set either to 0 to turn that one off.",
        "It starts off because it restricts players.",
    ),
    about(
        "afk",
        "Set the spot first",
        "An idle player out in the world keeps a whole view distance of chunks loaded alone. This moves idle players to one shared spot, so they stop holding those chunks.",
        "A player who has stood still for {idle_minutes} minutes is moved, with a warning in chat {warn_seconds} seconds before.",
        "Set the spot before you turn this on. Stand where idle players should go, open AFK move and press Use where I am standing.",
        "It starts off because it moves players.",
    ),
    about(
        "report",
        "The three report settings",
        "Check settings at start up reads server.properties when the server starts and logs anything worth changing.",
        "Seconds between chunk counts sets how often loaded chunks are counted for /lag, every {chunk_sample_seconds} seconds by default. Counting walks every loaded chunk, so it runs on a timer and not each time someone asks.",
        "Let everyone use /tps decides who /tps answers. When it is off, only operators get an answer.",
    ),
    Topic("limits", "What it cannot do", "And why not", (
        "Most of a Bedrock server's tick is the engine's own work on loaded chunks and entities. On the server these modules were written for, a day of measurements put that at about 96 per cent of the tick.",
        "So view-distance in server.properties and the number of entities matter far more than anything a plugin can tune. This plugin works on the entities. The view distance is yours to set, and it cannot change while the server runs.",
        "Endstone has no redstone or hopper event, no way to unload a chunk and no switch for mob AI. That is why there is no redstone budget, hopper guard, chunk limiter or AI reducer here.",
        "Endstone also cannot tell a fresh spawn from a chunk load, or see whether a mob is a baby or which colour it is. That is why the mob cap trims loaded chunks, the vehicle cap only refuses placing, and stacks mix colours.",
    )),
)


def topic_named(key: str) -> Topic:
    for topic in TOPICS:
        if topic.key == key:
            return topic
    raise KeyError(f"The guide has no topic called {key}")
