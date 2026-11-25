# Changelog

All notable changes to Let Me Perform are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0 beta 1]

The first public beta. It carries the performance modules of the CrabSMP server into one standalone Endstone
plugin, set up from in game menus. A fresh install turns on only the projectile cap, item merging, the piston
guard and the TNT chain guard. Everything that removes mobs or items, or restricts players, starts off. The
logic is tested against a stand in for Endstone, and the README lists under Status what is still to be
confirmed on a live server.

### Added

The numbers below are the defaults. Every one of them can be changed in the menu.

- Mob cap. A spawn in a chunk already holding 30 vanilla mobs is cancelled. It also trims a chunk that loads
  holding more, because Endstone cannot tell a fresh spawn from a chunk load. A named mob is let through.
  Starts off.
- Projectile cap. A projectile fired in a chunk already holding 200 is cancelled. It counts arrows, snowballs,
  eggs, splash and lingering potions, XP bottles, fire charges and wind charges, and never tridents, fishing
  hooks, ender pearls or firework rockets. Starts on.
- Vehicle cap. Placing a boat or minecart by hand in a chunk already holding 16 is refused. It never removes
  a vehicle. Starts off.
- Item merging. Every 5 seconds, matching dropped items inside the same cube of 4 blocks are joined into one
  stack, when the whole total fits in one stack. Items with a pick up delay or a scoreboard tag are left
  alone. Starts on.
- Mob stacker. Crowds of the same mob in a chunk are folded into one mob that carries a count, up to 20 in a
  stack. A stack dies one mob at a time, each kill dropping one mob's normal loot and XP. After stacking,
  mobs past 30 in a chunk are removed. Starts off.
- Lag clear. Every 20 minutes, after a 30 second warning in chat, dropped items, XP orbs, arrows and unnamed
  hostile mobs are swept away, with a switch for each kind and one more for unnamed farm animals. An
  emergency clear runs at once when more than 500 hostile mobs or 300 drops are loaded, at most once every
  120 seconds. Thrown tridents are never removed. Starts off.
- Piston guard. A piston that moves more than 40 times in 10 seconds is held still for 30 seconds, then works
  again. No block is ever broken. Starts on.
- TNT chain guard. Blasts from primed TNT and TNT minecarts are counted per cube of 16 blocks over 5 seconds.
  After 16 blasts, further blasts stop lighting more TNT, and after 48 they are cancelled outright. Starts on.
- Travel cooldowns. A firework boost while gliding waits 3 seconds after the last one, and a Riptide launch
  2 seconds. Players in creative and spectator mode are exempt. Starts off.
- AFK move. A player who has stood still for 10 minutes is moved to one shared spot, with a warning in chat
  60 seconds before. The spot is set from the menu with Use where I am standing. Starts off.
- Protection shared by every module. Only vanilla mobs are ever capped, stacked or cleared. Mobs from other
  add-ons, the 29 types on the protected list and mobs a player named are left alone.
- `/config-lmp`, with the alias `/lmp`: a menu with a page for every module, where each option is changed
  with a slider, switch, dropdown or text box, saved to `config.toml` and applied without a restart. It also
  holds the server report, the entity census and a fifteen page guide. From the console the command reloads
  `config.toml`.
- `/lag`: tick timings, loaded chunks, entity counts, what each module has done, and advice drawn from
  `server.properties`. `/lag entities` counts every loaded entity by dimension, type and chunk.
- `/lagclear`, `/lagclear now` and `/lagclear cancel`: start a countdown, clear at once, or stop a countdown.
  They work while the lag clear timer is off.
- `/tps`: TPS and milliseconds a tick, now and on average. Open to everyone unless `public_tps` is turned off.
- Four permissions: `lmp.command.config`, `lmp.command.lag` and `lmp.command.lagclear` for operators, and
  `lmp.command.tps` for everyone.
- An entity index fed by spawn and removal events, so no module scans the level on a timer, and a time budget
  for every background pass, 3 ms a tick.
- A build workflow. Every push to `main`, every `v*` tag and every pull request is linted, tested and built
  on Windows and Linux for Python 3.11 to 3.14. A push to `main` refreshes the Development build pre-release,
  and a `v*` tag publishes a release with the wheel.
