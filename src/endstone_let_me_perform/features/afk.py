from time import monotonic

from endstone import GameMode
from endstone.level import Location

from endstone_let_me_perform.core.feature import Feature
from endstone_let_me_perform.core.messages import tell, tell_success

SAMPLE_TICKS = 200
SPOT_RADIUS = 16
MOVABLE_MODES = (GameMode.SURVIVAL, GameMode.ADVENTURE)


class Watch:
    __slots__ = ("sample", "since", "warned_at", "moved")

    def __init__(self, since: float):
        self.sample = None
        self.since = since
        self.warned_at = None
        self.moved = False


class AfkMove(Feature):
    key = "afk"

    def __init__(self, plugin):
        super().__init__(plugin)
        self.watched = {}
        self.moves = 0

    def start(self) -> None:
        self.repeat(self.sample_players, SAMPLE_TICKS)

    def stop(self) -> None:
        super().stop()
        self.watched.clear()

    def forget(self, name: str) -> None:
        self.watched.pop(name, None)

    def sample_players(self) -> None:
        now = monotonic()
        for player in self.server.online_players:
            location = player.location
            sample = (location.x, location.y, location.z, location.pitch, location.yaw)
            name = player.name

            watch = self.watched.get(name)
            if watch is None:
                watch = self.watched[name] = Watch(now)

            if watch.sample is None:
                watch.sample = sample
            elif sample != watch.sample:
                watch.sample = sample
                watch.since = now
                watch.warned_at = None
                watch.moved = False
            elif not watch.moved:
                self.warn_or_move(player, location, watch, now)

    def warn_or_move(self, player, location, watch: Watch, now: float) -> None:
        options = self.options
        move_after = options.idle_minutes * 60
        idle = now - watch.since
        if idle < move_after - options.warn_seconds:
            return
        if player.game_mode not in MOVABLE_MODES:
            return

        dimension = self.server.level.get_dimension(options.dimension)
        spot = Location(dimension, options.x + 0.5, options.y, options.z + 0.5, location.pitch, location.yaw)
        if location.dimension.name == dimension.name and location.distance_squared(spot) <= SPOT_RADIUS**2:
            return

        if watch.warned_at is None:
            watch.warned_at = now
            tell(
                player,
                f"You have been idle for a while. Move in the next §f{options.warn_seconds} seconds "
                "§7or you will be taken to the AFK spot.",
            )
            return

        if idle < move_after or now - watch.warned_at < options.warn_seconds:
            return
        if not player.teleport(spot):
            return

        watch.sample = None
        watch.moved = True
        self.moves += 1
        tell_success(player, "You were idle for too long, so you were taken to the AFK spot.")

    def report(self) -> list:
        cutoff = monotonic() - self.options.idle_minutes * 60
        idle_now = sum(1 for watch in self.watched.values() if watch.since <= cutoff)
        if not self.moves and not idle_now:
            return []
        return [("Players moved", self.moves), ("Idle now", idle_now)]
