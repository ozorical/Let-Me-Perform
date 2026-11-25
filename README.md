# Let Me Perform

Let Me Perform is a performance toolkit for [Endstone](https://endstone.dev) servers. Endstone is a plugin
framework for Minecraft Bedrock Dedicated Server, and this is a plugin for it, written in Python. It carries
the performance features written for the CrabSMP server into one plugin that any server owner can install:
entity caps, mob stacking, item merging, a timed lag clear, guards for pistons and TNT, travel cooldowns, an
AFK move and a `/lag` report. Everything is set up from in game menus through `/config-lmp`, so nobody has to
edit a file to use it.

It is for server owners who want fewer entities and fewer runaway machines, and who would rather read what a
module does before turning it on. This page says what each module does, what it leaves alone and where its
limits are.

The whole plugin is built on one rule: most of a Bedrock server's tick is the engine's own work on loaded
chunks and the entities in them. On the server these modules were written for, a day of measurements put that
at about 96 per cent of the tick. No plugin can make that work faster. A plugin can only give the engine less
of it, so Let Me Perform works on entity counts and on machines that run away with the tick. The number of
loaded chunks follows `view-distance` in `server.properties`, which stays your biggest lever and which nothing
can change while the server runs.

Created by Ozz. Released under the MIT licence.

## Requirements

- Endstone 0.11.14 or newer. Endstone dropped Python 3.10 in that release. On an older build the plugin logs
  a warning at start up that parts of it may not work.
- Python 3.11 or newer.

The plugin is written against Endstone 0.11.16, which targets Minecraft Bedrock 26.65. It has no other
dependencies and needs no resource pack: the menus are ordinary server forms, and their icons are texture
paths from the vanilla pack.

## Installing

1. Open the [Releases page](https://github.com/ozorical/Let-Me-Perform/releases) and download the wheel, a
   file named like `endstone_let_me_perform-1.0.0-py3-none-any.whl`. Pick a tagged release, or the pre-release
   called "Development build", which is rebuilt from the newest commit on `main` each time one is pushed. The
   development build has passed the tests but has not been through a release.
2. Drop the wheel into your server's `plugins` folder.
3. Restart the server. Let Me Perform writes `plugins/let_me_perform/config.toml` on first run, with every
   default in it.

One wheel works on Windows and Linux, because the plugin is pure Python.

To build the wheel yourself:

```
pip install build
python -m build --wheel
```

The wheel lands in `dist/`.

## First steps

A fresh install turns on four modules only: the projectile cap, item merging, the piston guard and the TNT
chain guard. Everything that removes mobs or items, or restricts players, starts off, so installing the plugin
changes very little until you decide otherwise.

1. Run `/lag` to see tick timings, loaded chunks and entity counts.
2. Run `/lag entities` to see what the server is full of, and which chunks hold the most.
3. Open `/config-lmp` and turn on one module at a time. Each settings page has a "How it works" button that
   opens that module's page in the guide.

Give each module a while under real play, and look at `/lag` again, before turning on the next.

## Commands and permissions

| Command | What it does | Permission | Default |
| --- | --- | --- | --- |
| `/config-lmp` | Opens the settings menu. Alias `/lmp`. Run from the console, where no menu can open, it reloads `config.toml`. | `lmp.command.config` | operator |
| `/lag` | Shows the server report: tick timings, loaded chunks, entity counts, what each module has done, and advice on `server.properties`. | `lmp.command.lag` | operator |
| `/lag entities` | Shows the entity census: every loaded entity, counted by dimension, by type and by chunk. | `lmp.command.lag` | operator |
| `/lagclear` | Starts a lag clear countdown, with the warnings in chat. | `lmp.command.lagclear` | operator |
| `/lagclear now` | Runs a lag clear at once, with no warning. | `lmp.command.lagclear` | operator |
| `/lagclear cancel` | Stops a countdown that is running. | `lmp.command.lagclear` | operator |
| `/tps` | Shows TPS and milliseconds a tick, now and on average. | `lmp.command.tps` | everyone |

`lmp.command.config` also guards every change made inside the menu. `/tps` is open to everyone by default.
Turn `public_tps` off on the Reports page and it answers only players who hold `lmp.command.lag`.

## The menu

`/config-lmp` opens the main menu. Its first lines show the average TPS and tick time, and how many of the ten
modules are on. Under that is one button for each settings page, in the order used on this page, showing
whether the module is on and its main value. Four more buttons follow: Server report, Entity census, Guide and
Reload from file.

A settings page shows what the module does and every option with its current value. Its buttons are:

- Turn on or Turn off, on every page that has a switch.
- Change settings, which opens a form with a slider, switch, dropdown or text box for each option. Above each
  one is a line saying what it does. Press Save to keep the answers.
- How it works, which opens the module's page in the guide.
- Reset to defaults, which asks first. The reset includes the switch.
- On the AFK move page, Use where I am standing, which sets the AFK spot to your position.
- On the Lag clear page, Clear now, which starts the warning countdown, or Cancel the countdown while one is
  running.

Every change is written to `config.toml` and applied at once. The server does not need a restart. A number
outside its range is pulled back to the nearest end of the range, and an answer that cannot be read leaves the
old value in place. If the file cannot be written, the change still applies and you are told it will be lost at
the next restart.

Applying a change stops every module and starts it again with the new values. That has a few visible effects:
the refused and merged counters in `/lag` start again from zero, the lag clear timer starts its interval again,
a lag clear countdown or sweep that is under way is dropped, paused pistons are released, TNT counts and travel
cooldowns are forgotten, and every player's idle time starts again.

The Guide has fifteen pages: Start here, Reading /lag, one page for each settings page, and What it cannot do.
Server report and Entity census show what `/lag` and `/lag entities` print, with a Refresh button.

Opening the menu needs `lmp.command.config`, and the permission is checked again on every change, so a player
who loses it with the menu open cannot save anything.

## What is never touched

- Mobs from other add-ons. Only a mob whose id starts with `minecraft:` is ever capped, stacked or cleared. A
  mob from a behaviour pack is left alone by every module, whether or not it is on a list.
- Mobs on the protected list, shown below. No module caps, stacks or clears them, and they do not count
  towards any cap.
- Mobs a player named. The mob cap lets a named mob through, the stacker leaves it out, and the lag clear
  skips it.
- Players.
- Thrown tridents. The projectile cap never counts them and the lag clear never removes them. The same goes
  for fishing hooks, ender pearls and firework rockets.
- Vehicles. Placing one can be refused, but no boat or minecart is ever removed.
- Blocks. No block is ever broken. The piston guard holds a piston still, and the TNT guard only makes a blast
  smaller or cancels it.
- Dropped items that another plugin marked with a scoreboard tag. They are neither merged nor cleared.

The protected list starts with these 29 ids, each written with `minecraft:` in front in the config:

| Group | Ids |
| --- | --- |
| Villagers and traders | `villager`, `villager_v2`, `wandering_trader`, `npc` |
| Golems | `iron_golem`, `snow_golem`, `copper_golem` |
| Bosses | `wither`, `ender_dragon`, `elder_guardian`, `warden` |
| Pets and helpers | `wolf`, `cat`, `ocelot`, `parrot`, `allay` |
| Mounts | `horse`, `donkey`, `mule`, `llama`, `trader_llama`, `skeleton_horse`, `zombie_horse`, `camel`, `camel_husk`, `nautilus`, `zombie_nautilus`, `happy_ghast` |
| Other | `armor_stand` |

Endstone cannot see whether a mob is tamed, saddled or leashed, so protection goes by type and by name tag
only. To keep a mob that is not on the list, name it, or add its type to the list on the General page.

## Modules

Each module has a page in the menu and a section of the same name in `config.toml`. The tables below give
every option with its key, its default, the range the plugin accepts and what it does. The headings follow the
order of the menu.

### General

Settings every module shares. This page has no switch.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `sweep_budget_ms` | `3.0` | 0.5 to 10.0 | The most time, in milliseconds, that one background pass may spend in a single tick. A pass that runs out stops there and carries on next time. |
| `protected_types` | the 29 ids above | a list of mob ids | Mob ids no module ever caps, stacks or clears. |

A server has 50 ms for each tick. The budget applies to each pass separately: index pruning, item merging, the
mob stacker, the vehicle recount and the lag clear sweep each get their own, so two passes that land on the
same tick can each spend it.

Write protected ids in full, such as `minecraft:cow`. In the menu the list is spread over text boxes of 100
characters, with commas between entries and an empty box at the end for new ones.

### Mob cap

Starts off, because it removes mobs.

A mob that spawns in a chunk already holding `per_chunk` mobs is cancelled. A spawner farm or a breeding pen
can pack hundreds of mobs into one chunk, and the engine pays for every one of them on every tick. The cap
works in every loaded chunk, whether or not a player is standing in it.

Every vanilla mob that is not on the protected list counts. A stacked mob counts as one. A named mob counts
towards the total but is never refused itself.

Read these before turning it on:

- **It also trims a chunk that loads holding more than the cap.** Endstone raises the same event for a fresh
  spawn and for a saved mob coming back with its chunk, and nothing in the event tells the two apart. When a
  chunk loads with 50 unnamed mobs and the cap is 30, the mobs past the cap are cancelled as they arrive, and
  a cancelled mob is gone for good. Find your biggest animal pen with `/lag entities` and set the cap above it
  first. This follows from how Endstone is built and has not yet been watched on a live server; see Status.
- The event carries no cause. A natural spawn, a spawner, a spawn egg, breeding and a command are all refused
  alike in a full chunk.
- It never removes a mob that is already loaded. Turning it on in a chunk that holds 100 mobs changes nothing
  there until the chunk unloads and loads again.
- A mob is counted in the chunk it appeared in. The count follows a mob that walks into another chunk only
  while the mob stacker is on, because the stacker's pass is what reads positions again.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `enabled` | `false` | true or false | Turns the module on. |
| `per_chunk` | `30` | 5 to 200 | A spawn in a chunk already holding this many mobs is cancelled. |

### Projectile cap

Starts on.

A projectile fired in a chunk already holding `per_chunk` projectiles is cancelled. The default of 200 is far
above what players reach by hand. It is there to stop a dispenser machine filling a chunk.

It counts eight kinds: arrows, snowballs, eggs, splash potions, lingering potions, XP bottles, fire charges
(`small_fireball`) and wind charges (`wind_charge_projectile`). Tridents, fishing hooks, ender pearls and
firework rockets are never counted. A cancelled throw could cost a player the trident, and an elytra boost is a
rocket.

Like the mob cap, it cannot tell a chunk load from a fresh shot, so a chunk that loads holding more saved
projectiles than the cap is trimmed down to it.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `enabled` | `true` | true or false | Turns the module on. |
| `per_chunk` | `200` | 20 to 1000 | A projectile fired in a chunk already holding this many is cancelled. |

### Vehicle cap

Starts off, because it restricts players.

Placing a boat or minecart by hand in a chunk already holding `per_chunk` vehicles is refused. The item stays
in the hand, and the player sees a short tip saying the chunk is full. Boats, chest boats and every kind of
minecart count as vehicles. The check runs when a player uses an item whose id ends in `_boat`, `_raft` or
`minecart`.

- It only refuses placing by hand. It never removes a vehicle, so a build that already has more keeps them
  and cannot add to them. A vehicle that arrives another way, such as from a dispenser, is not refused.
- The cap is not applied when a vehicle appears, because Endstone reports a chunk loading the same way as a
  fresh spawn. Cancelling there would delete parked chest and hopper minecarts with what they hold.
- A click on a block is checked against two chunks, the one holding the block and the one next to the face
  that was clicked, and the fuller one decides. A click in the air is checked against the chunk the player
  stands in.
- The refusal cancels the whole click. While a player holds a boat or minecart in a full chunk, opening a
  chest or a door there is refused too, because it is the same click. Putting the item away fixes it.
- Vehicle positions are read again every five minutes, so a minecart that has travelled is counted where it
  was last seen until the next reading.
- Two things are still to be confirmed on a live server: which click a boat placed on open water arrives as,
  and that a refused placement leaves the item in the hand. See Status.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `enabled` | `false` | true or false | Turns the module on. |
| `per_chunk` | `16` | 1 to 64 | Placing a boat or minecart in a chunk already holding this many is refused. |

### Item merging

Starts on. It takes no items away; it only joins them.

Matching dropped items that lie close together are joined into one stack, so a farm's output is a handful of
entities and not hundreds. Every `interval_seconds` the plugin goes through the dropped items it tracks. The
world is divided into cubes `radius` blocks on a side, and matching items inside the same cube are merged: one
keeps the total and the other is removed.

- The cubes sit on a fixed grid. Two items in neighbouring cubes are not merged, however close they lie.
- Two stacks merge only when the whole total fits in one stack. Two stacks of 40 cobblestone stay as they are;
  two stacks of 30 become one of 60. Items that do not stack never merge.
- The items must match by Endstone's own check for two stacks being equal apart from the amount.
- An item that still has a pick up delay is left alone, so something that has only now been dropped is not
  pulled into a pile.
- An item that carries a scoreboard tag is left alone, because another plugin put it there for a reason.
- The pass obeys the sweep budget. With a great many drops it works through them over several passes.
- Whether players see the new count on a merged stack at once is still to be confirmed on a live server; see
  Status.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `enabled` | `true` | true or false | Turns the module on. |
| `interval_seconds` | `5` | 1 to 60 | How often dropped items are checked for neighbours to merge with. |
| `radius` | `4` | 1 to 16 | The side of the merge cube, in blocks. Matching items inside the same cube are merged. |

### Mob stacker

Starts off, because it changes how farms behave and removes mobs.

Crowds of the same mob in one chunk are folded into one mob that carries a count. Thirty cows in a pen become
two: one labelled `Cow x20` and one labelled `Cow x10`. The engine then has two mobs to tick and not thirty.

Every `interval_seconds` the stacker groups the mobs it tracks by chunk and by type. Inside a group it fills
the largest stacks first, up to `max_stack`, and removes the mobs that were folded in. The mob left standing
gets the label as its name tag and a scoreboard tag, `lmp_stack`, which is how the plugin tells its own label
from a name a player gave. Mobs are only stacked with others in the same chunk. Named mobs, protected mobs and
mobs from other add-ons are never stacked.

Read these before turning it on:

- A stack dies one mob at a time. Endstone has no loot API, so the plugin cannot drop twenty mobs' loot at
  once. It lets the game handle one ordinary death, which drops one mob's normal loot and XP, and one tick
  later it spawns a new mob of the same type on the spot, carrying the count less one.
- The mob that comes back is a fresh one. It has full health and none of the old one's state.
- In a fall damage farm the rest of the stack is left standing where the first one died. The new mob appears
  at the bottom of the drop and does not fall again, so the farm gets one kill from each stack.
- Babies, colours and variants of one type merge, because Endstone cannot see them. Sheep of every colour
  share a stack, and babies stack with adults. Put a type on the protected list to keep it out.
- A stacked mob has a name tag, which very likely stops it despawning the way an unnamed mob would. Stacks of
  hostile mobs can therefore build up until they are killed or cleared. The lag clear treats a stack as
  unnamed, so a stack of a type it clears is removed whole.
- `chunk_limit` removes mobs outright. After stacking, anything past that number among the stackable mobs in
  a chunk is deleted and drops nothing. A stack counts as one, so a removed stack takes its whole count with
  it. Named mobs are neither counted nor removed. Set it to 0 to remove nothing.
- With the module off, an existing stack keeps its label but dies as one mob, and the rest of its count is
  lost. Kill off the stacks, or accept that loss, before turning the module off for good.
- The mob that replaces a dead one is not refused by the mob cap.
- The count is kept in the label, so a stack is expected to keep its count across a restart. That is still
  to be confirmed on a live server; see Status.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `enabled` | `false` | true or false | Turns the module on. |
| `interval_seconds` | `3` | 1 to 60 | How often chunks are checked for mobs to stack. |
| `max_stack` | `20` | 2 to 100 | The most mobs one stacked mob can stand for. |
| `chunk_limit` | `30` | 0 to 200 | After stacking, mobs past this number in a chunk are removed. 0 removes nothing. |

### Lag clear

Starts off, because it removes things players may want.

Every `interval_minutes` players are warned in chat, and `warning_seconds` later dropped items and stray mobs
are swept away. A warning goes out when the countdown starts, again at the halfway point when the warning is
20 seconds or longer, and again with 5 seconds left. When the sweep is done, chat is told how many entities
were removed. The sweep obeys the sweep budget, so a large clear is spread over several ticks. Whatever is
removed drops nothing.

Each switch decides one kind of thing:

- `clear_items` removes every dropped item, except one that carries a scoreboard tag.
- `clear_xp` removes every XP orb.
- `clear_arrows` removes every loaded arrow, whether it is stuck in a block or still in flight. Thrown
  tridents are never removed.
- `clear_hostiles` removes unnamed mobs of the 35 types listed below.
- `clear_passives` removes unnamed bats, chickens, cows, mooshrooms, pigs, polar bears and sheep.

The hostile types are `blaze`, `bogged`, `breeze`, `cave_spider`, `creeper`, `drowned`, `enderman`,
`endermite`, `evocation_illager`, `ghast`, `guardian`, `hoglin`, `husk`, `magma_cube`, `parched`, `phantom`,
`piglin`, `piglin_brute`, `pillager`, `ravager`, `shulker`, `silverfish`, `skeleton`, `slime`, `spider`,
`stray`, `vex`, `vindicator`, `witch`, `wither_skeleton`, `zoglin`, `zombie`, `zombie_pigman`,
`zombie_villager` and `zombie_villager_v2`. Zombie villagers, piglins and shulkers are on it, so name any you
are keeping, or add the type to the protected list.

A mob whose type is on neither list is never cleared, whatever the switches say. A mob with a name tag is
skipped, unless the name tag is a stack label from the mob stacker, in which case the whole stack goes.

The emergency clear watches once a second while the module is on. It runs a clear at once, with no countdown,
when more than `emergency_mobs` hostile mobs are loaded, or more than `emergency_drops` dropped items and XP
orbs together, and it says in chat which count set it off. It counts only kinds the clear is allowed to
remove: hostile mobs count only while `clear_hostiles` is on, items only while `clear_items` is on and XP orbs
only while `clear_xp` is on. Named hostile mobs are counted even though the clear skips them. After an
emergency clear it waits `emergency_cooldown_seconds` before it can run another, and it never runs while a
countdown or a sweep is under way.

`/lagclear`, `/lagclear now`, `/lagclear cancel` and the Clear now button all work while the module is off.
Only the timer and the emergency clear need it on.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `enabled` | `false` | true or false | Turns the timer and the emergency clear on. |
| `interval_minutes` | `20` | 5 to 240 | How long the timer waits between one clear and the next. |
| `warning_seconds` | `30` | 5 to 120 | How long players are warned in chat before a clear runs. |
| `clear_items` | `true` | true or false | Removes items lying on the ground. |
| `clear_xp` | `true` | true or false | Removes experience orbs nobody picked up. |
| `clear_arrows` | `true` | true or false | Removes loaded arrows. Thrown tridents are never removed. |
| `clear_hostiles` | `true` | true or false | Removes hostile mobs that have no name tag. |
| `clear_passives` | `false` | true or false | Removes unnamed bats, chickens, cows, mooshrooms, pigs, polar bears and sheep. |
| `emergency` | `true` | true or false | Runs a clear at once, with no warning, when the counts below are passed. |
| `emergency_mobs` | `500` | 100 to 5000 | Hostile mobs loaded at once before an emergency clear. |
| `emergency_drops` | `300` | 100 to 5000 | Dropped items and XP orbs loaded at once before an emergency clear. |
| `emergency_cooldown_seconds` | `120` | 30 to 1800 | The shortest gap between two emergency clears. |

### Piston guard

Starts on. It does nothing to a piston that stays under the limit.

Endstone has no redstone event, so a piston is the one place a runaway clock can be seen. The guard counts how
often each piston moves. Extending is one move and retracting is another. A piston that moves more than
`moves_per_window` times inside `window_seconds` is held still for `suspend_seconds`: every move it tries in
that time is cancelled. After that it works again and the count starts fresh.

- It pauses and never breaks. No block is removed, so the machine is still there when the pause ends.
- The window is counted from that piston's first move. Once it has run out, the next move starts a new count.
- The console gets a warning with the piston's coordinates and dimension, so you can go and look at the
  machine. Players are told nothing.
- Up to 4,000 pistons are watched at once. Pistons past that number go unwatched until idle ones are dropped
  from the list, which happens every 10 seconds.

The default is 40 moves in 10 seconds for a reason. A limit only works if a piston can reach it. A piston
cannot move more than about 10 times a second, so a 10 second window holds about 100 moves at most, and a
limit set above that would never trip. Forty is four moves a second, kept up for the whole window. The figure
of 10 a second has not yet been measured on a live server; see Status.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `enabled` | `true` | true or false | Turns the module on. |
| `moves_per_window` | `40` | 10 to 1000 | How many times one piston may move inside the window. |
| `window_seconds` | `10` | 1 to 60 | The stretch of time the moves are counted over. |
| `suspend_seconds` | `30` | 5 to 600 | How long a piston that went over is held still. |

### TNT chain guard

Starts on. It does nothing until a chain has already passed the first limit.

Each TNT blast lights the TNT around it, so a large store of TNT goes off as one long chain. The guard counts
blasts in each area and steps in twice.

- Blasts are counted per area, a cube `cell_size` blocks on a side on a fixed grid, over `window_seconds`
  from the first blast in that area. Once the window has run out, the next blast starts a new count.
- Only primed TNT and TNT minecarts count. A creeper, an end crystal or any other explosion is never counted.
- The first `chain_limit` blasts in an area are left alone.
- After that, a blast is damped: the TNT blocks it would have lit are taken out of the blast, so they stay
  where they are, and the blast breaks everything else as usual. That the TNT left out really stays unlit is
  still to be confirmed on a live server; see Status.
- After `hard_limit` blasts, a blast is cancelled outright.
- The first time a chain is stopped, players within 24 blocks see a short tip saying so.

Keep `hard_limit` above `chain_limit`. If it is lower, the damping step is skipped and blasts are cancelled as
soon as `chain_limit` is passed.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `enabled` | `true` | true or false | Turns the module on. |
| `chain_limit` | `16` | 1 to 200 | After this many blasts in one area, further blasts stop lighting more TNT. |
| `hard_limit` | `48` | 1 to 500 | After this many blasts in one area, further blasts are cancelled outright. |
| `window_seconds` | `5` | 1 to 30 | The stretch of time the blasts are counted over. |
| `cell_size` | `16` | 4 to 64 | Blasts are counted per cube of this size, in blocks. |

### Travel cooldowns

Starts off, because it restricts players.

Fast travel loads and generates chunks faster than anything else a player does, and chunk loading is the
leading suspect for long ticks. With this on, a firework boost has to wait `rocket_seconds` after the last
one, and a Riptide launch `riptide_seconds`. A use that comes too soon is cancelled, and the player sees a
short tip with the seconds left.

- A rocket counts when the player is gliding and the game reports the use as a click in the air. A rocket
  used on a block, or set off from the ground, is never limited.
- A trident enchanted with Riptide counts on every use the game reports as a click in the air, whether or
  not the player is in water or rain.
- Only players in survival and adventure mode are limited. Creative and spectator players are exempt. No
  permission lifts the cooldown, so operators in survival wait like everyone else.
- A refused use does not restart the wait.
- A cooldown is forgotten when the player leaves the server.
- Set either number to 0 to turn that one off.
- That cancelling the use really stops the boost or the launch is still to be confirmed on a live server; see
  Status.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `enabled` | `false` | true or false | Turns the module on. |
| `rocket_seconds` | `3` | 0 to 30 | The wait between two firework boosts while gliding. 0 turns it off. |
| `riptide_seconds` | `2` | 0 to 30 | The wait between two Riptide trident launches. 0 turns it off. |

### AFK move

Starts off, because it moves players.

An idle player out in the world keeps a whole view distance of chunks loaded alone. This module moves idle
players to one shared spot, so they stop holding those chunks. It does not kick anyone.

**Set the spot before turning this on.** The default is X 0, Y 100, Z 0 in the Overworld, which is a
placeholder and may well be in mid air. Stand where idle players should go, open the AFK move page and press
Use where I am standing. That fills in the dimension and the three coordinates.

- Positions are sampled every 10 seconds. A player is idle while their position and the direction they face
  have not changed between samples, so times are accurate to about 10 seconds.
- Anything that moves or turns the player counts as activity. A player carried by water or a minecart is not
  idle.
- A player gets one warning in chat `warn_seconds` before the move. Moving in that time cancels it.
- After `idle_minutes` idle the player is teleported to the spot and told why in chat. They are not moved
  again until they have moved.
- A player already within 16 blocks of the spot is left where they are.
- Only players in survival and adventure mode are moved. Creative and spectator players are exempt. No
  permission exempts anyone.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `enabled` | `false` | true or false | Turns the module on. |
| `idle_minutes` | `10` | 1 to 120 | How long a player must stand still before being moved. |
| `warn_seconds` | `60` | 10 to 300 | How long before the move the player is warned in chat. |
| `dimension` | `overworld` | `overworld`, `nether` or `the_end` | The dimension of the spot idle players are moved to. |
| `x` | `0` | -30000000 to 30000000 | The X coordinate of the spot. |
| `y` | `100` | -64 to 320 | The Y coordinate of the spot. |
| `z` | `0` | -30000000 to 30000000 | The Z coordinate of the spot. |

### Reports

What the `/lag` report samples and what the console is told at start up. This page has no switch.

| Key | Default | Range | Meaning |
| --- | --- | --- | --- |
| `boot_audit` | `true` | true or false | Logs the advice drawn from `server.properties` to the console when the server starts. `/lag` shows the advice either way. |
| `chunk_sample_seconds` | `60` | 10 to 600 | How often loaded chunks are counted for the `/lag` report. |
| `public_tps` | `true` | true or false | When false, `/tps` answers only those who hold `lmp.command.lag`. |

## The `/lag` report

`/lag` prints these sections. A section with nothing to show is left out.

| Section | What it shows |
| --- | --- |
| Timings | Tick time and TPS, now and on average, and the share of the 50 ms tick budget in use. Two more rows appear when they can be read: main thread CPU and process memory. |
| Chunks | Loaded chunks in each dimension, with the peak since the plugin started. |
| Entities | How many mobs, dropped items, XP orbs, projectiles and vehicles are tracked, and the three chunks holding the most mobs. |
| One section for each module that is on | What the module has done: spawns, projectiles and placements refused, items merged, stacks and the mobs in them, the last and next lag clear, pistons paused, blasts damped and cancelled, players moved. |
| Server settings | The CPU cores this process may use, and up to seven values read from `server.properties`. |
| Advice | A line for each of those values worth changing. |

The server has 50 ms for each tick. TPS stays at 20 while ticks fit inside that, and players feel the odd long
tick far more than a high average. Look at loaded chunks first, because the engine's work follows the number
of loaded chunks much more closely than the number of players.

What each part costs to read:

- Timings come straight from Endstone and cost nothing.
- The main thread CPU row appears on Linux only, where the plugin can read the thread's CPU time from `/proc`.
  It shows the share of one core used since the last time anyone read the report.
- The process memory row appears only when the `psutil` package is present in the server's Python.
- Chunk counts are sampled on a timer, every `chunk_sample_seconds`, with the first sample five seconds after
  the plugin starts. Counting walks every loaded chunk, so it is not done each time someone asks, and at the
  default the figure can be up to a minute old.
- Entity counts are read from the index the modules already keep, so they cost nothing. The mob figure covers
  the mobs the plugin tracks: vanilla mobs that are not on the protected list. When no module that needs the
  index is on, the section says tracking is off.
- The settings and advice are read from `server.properties` when the plugin starts and when settings are
  applied, not when the report is asked for.

The advice covers five settings: `view-distance` above 12, `tick-distance` above 4, `max-threads` set to 0 or
to more than the cores the process may use, `player-idle-timeout` set to 0, and `compression-threshold` below
256. The core count respects a container's CPU limit on Linux.

`/lag entities` is the census. It walks every loaded entity once, only when asked, and counts all of them,
protected mobs and mobs from other add-ons included. It shows the total in each dimension, the eight
most common types, and the five fullest chunks with the most common type in each. Run it before changing a cap
or a stack size, to see whether a busy chunk is full of animals, hostile mobs, items or villagers.

## `config.toml`

The settings live in `plugins/let_me_perform/config.toml`. The menu writes this file, so most owners never
open it. If you edit it by hand, run `/config-lmp` from the console, or press Reload from file in the menu, and
the file is read again and every module restarted.

- A key that is missing is filled in with its default, and the file is written back with it at start up.
- A number outside its range is pulled back to the nearest end of the range.
- A value of the wrong kind is read as the default.
- If the file cannot be read at start up, the defaults are used and the console says why. If a reload fails,
  the settings in memory are kept.

This is the file a fresh install writes:

```toml
[general]
sweep_budget_ms = 3.0
protected_types = ["minecraft:villager", "minecraft:villager_v2", "minecraft:wandering_trader", "minecraft:iron_golem", "minecraft:snow_golem", "minecraft:npc", "minecraft:wither", "minecraft:ender_dragon", "minecraft:elder_guardian", "minecraft:warden", "minecraft:wolf", "minecraft:cat", "minecraft:ocelot", "minecraft:parrot", "minecraft:horse", "minecraft:donkey", "minecraft:mule", "minecraft:llama", "minecraft:trader_llama", "minecraft:skeleton_horse", "minecraft:zombie_horse", "minecraft:camel", "minecraft:camel_husk", "minecraft:nautilus", "minecraft:zombie_nautilus", "minecraft:happy_ghast", "minecraft:copper_golem", "minecraft:allay", "minecraft:armor_stand"]

[mob_cap]
enabled = false
per_chunk = 30

[projectile_cap]
enabled = true
per_chunk = 200

[vehicle_cap]
enabled = false
per_chunk = 16

[item_merge]
enabled = true
interval_seconds = 5
radius = 4

[mob_stacker]
enabled = false
interval_seconds = 3
max_stack = 20
chunk_limit = 30

[lag_clear]
enabled = false
interval_minutes = 20
warning_seconds = 30
clear_items = true
clear_xp = true
clear_arrows = true
clear_hostiles = true
clear_passives = false
emergency = true
emergency_mobs = 500
emergency_drops = 300
emergency_cooldown_seconds = 120

[piston_guard]
enabled = true
moves_per_window = 40
window_seconds = 10
suspend_seconds = 30

[tnt_guard]
enabled = true
chain_limit = 16
hard_limit = 48
window_seconds = 5
cell_size = 16

[travel_cooldown]
enabled = false
rocket_seconds = 3
riptide_seconds = 2

[afk]
enabled = false
idle_minutes = 10
warn_seconds = 60
dimension = "overworld"
x = 0
y = 100
z = 0

[report]
boot_audit = true
chunk_sample_seconds = 60
public_tps = true
```

## What it cannot do

These are limits of what Endstone lets a plugin see and do, not things left for later.

- No redstone budget and no hopper guard. Endstone has no redstone event and no hopper event. Pistons,
  explosions and liquid flow are the only block activity a plugin can see, which is why the piston guard is
  the one answer to a runaway clock.
- No chunk unloading, no chunk limiter and no view distance changes while the server runs. A plugin can count
  loaded chunks and nothing more. `view-distance` and `tick-distance` in `server.properties` are yours to set,
  and `/lag` tells you when they look high.
- No mob AI switch. There is no way to turn a mob's AI or collision off.
- No way to tell a fresh spawn from a chunk load. That is why the mob cap and the projectile cap trim a chunk
  as it loads, and why the vehicle cap only refuses placing.
- No way to see a mob's age, colour, variant or whether it is tamed. That is why stacks mix colours and
  babies, and why protection goes by type and name tag.
- No loot API. That is why a stack dies one mob at a time, and why anything a module removes drops nothing.

## How it stays cheap

The plugin runs on the server's tick thread, so everything it does is time the whole server waits on. A lag
guard has to cost less than the lag it guards against. These are the rules the code keeps.

- One listener for each event. The whole plugin has eight handlers, in one file: entity spawn, entity removal,
  entity death, explosion, piston extend, piston retract, player interact and player quit. When two modules
  need the same event, the one handler calls both. A handler whose module is off returns on its first check.
  Nothing listens to player movement or to liquid flow.
- An entity index, so nothing scans the level on a timer. The index is fed by the spawn and removal events
  and holds mobs, dropped items, XP orbs, projectiles and vehicles, with a count for each chunk. It walks the
  loaded entities once, five seconds after it is switched on, to pick up what was already there. After that
  it only drops dead entries, a slice every 10 seconds. When no module that needs it is on, it is off.
- Every background pass has a time budget, `sweep_budget_ms`. A pass that runs out stops and picks up where it
  left off: on the next tick for the mob stacker, the vehicle recount and the lag clear sweep, and at the next
  pass for item merging and index pruning.
- Slow timers where slow is enough. Idle players are sampled every 10 seconds, loaded chunks are counted every
  60 seconds and vehicle positions are read every five minutes.
- Bounded memory. The index holds at most 20,000 entities of each kind. Past that, further dropped items and
  XP orbs go untracked, and the chunk counts for mobs, projectiles and vehicles are reset with a warning in
  the console. The piston guard watches at most 4,000 pistons.
- Settings are applied in place. A change in the menu restarts the modules, not the server.
- Menus are built when a player opens them and thrown away when they close.

## Status

The logic is covered by 208 automated tests that run against a stand in for Endstone, and every push to `main`
is built and tested on Windows and Linux for Python 3.11 to 3.14. A stand in proves the plugin's own logic. It
proves nothing about what Bedrock really does.

The following have not yet been confirmed on a live server:

- That the spawn event fires for saved mobs when a chunk loads, and that their name tags are already set then.
- Which click a boat on open water arrives as, and that a refused placement leaves the item in the hand.
- That a merged stack shows its new count to players at once.
- That stack labels and tags survive a restart, and how a mob in its death animation reads.
- That cancelling the item use really stops a rocket boost or a Riptide launch.
- That a TNT blast's source is the primed TNT, and that TNT taken out of the blast stays unlit.
- How the menu icons and button colours look in game.
- The real ceiling on piston moves a second.

Reports on any of these, either way, are welcome on the
[issue tracker](https://github.com/ozorical/Let-Me-Perform/issues).

## Developing

```
Let-Me-Perform/
  pyproject.toml
  LICENSE
  README.md
  CHANGELOG.md
  .github/workflows/build.yml   lint, test, build and release
  src/endstone_let_me_perform/
    __init__.py
    plugin.py                   plugin class, commands, permissions, settings load and save
    settings.py                 every option with its default, range and hint
    listeners.py                the only event handlers
    core/
      index.py                  entity index fed by spawn and removal events
      tables.py                 protected, hostile, farm animal, projectile and vehicle ids
      feature.py                what every module shares: start, stop, timers, budget
      budget.py                 the time budget for one pass
      messages.py               chat prefix and replies
    features/
      mob_cap.py  projectile_cap.py  vehicle_cap.py
      item_merge.py  mob_stacker.py  lag_clear.py
      piston_guard.py  tnt_guard.py
      travel_cooldown.py  afk.py
    report/
      report.py                 /lag and /tps
      metrics.py                tick timings, thread CPU, memory
      chunks.py                 loaded chunk counts
      census.py                 /lag entities
      audit.py                  the server.properties check
    menus/
      menus.py                  /config-lmp and every page
      editor.py                 the settings form
      guide.py                  the in game guide
      icons.py  theme.py        button icons and colours
  tests/
    fake_endstone.py            the stand in for Endstone
    conftest.py
    test_*.py
```

To run the tests and the linter:

```
pip install pytest ruff tomlkit
pytest -q
ruff check src tests
```

The tests need no server and no Endstone install.

Releases are built by the workflow in `.github/workflows/build.yml`. Every push to `main` and every pull
request is linted, tested, built and then installed beside the real Endstone package to prove it imports, on
Windows and Linux for Python 3.11, 3.12, 3.13 and 3.14. After a push to `main` passes, the "Development build"
pre-release is replaced with a wheel from that commit. Pushing a tag such as `v1.0.0` publishes a release
named after the tag, with the wheel attached. A pull request publishes nothing.

## Licence

MIT, copyright Ozz. See [LICENSE](LICENSE). You are free to copy, change and redistribute the plugin as long as
the copyright notice and the licence text stay with it.
