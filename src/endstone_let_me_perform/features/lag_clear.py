from time import monotonic

from endstone_let_me_perform.core.feature import Feature
from endstone_let_me_perform.core.index import ITEM, MOB, XP
from endstone_let_me_perform.core.messages import broadcast, tell_failure, tell_success
from endstone_let_me_perform.core.tables import ARROW_TYPE, HOSTILE_TYPES, ITEM_TYPE, PASSIVE_TYPES, STACK_TAG, XP_TYPE

TICKS_PER_SECOND = 20
HALFWAY_FROM_SECONDS = 20
LAST_WARNING_SECONDS = 5


class LagClear(Feature):
    key = "lag_clear"
    uses_index = True

    def __init__(self, plugin):
        super().__init__(plugin)
        self._countdown_task = None
        self._seconds_left = 0
        self._halfway = 0
        self._sweep_task = None
        self._queue = []
        self._removed = 0
        self._seconds_to_timed = 0
        self._cleared_at = None
        self._cleared_count = 0
        self._emergency_at = None
        self._emergencies = 0

    @property
    def counting_down(self) -> bool:
        return self._countdown_task is not None

    @property
    def seconds_left(self) -> int:
        return self._seconds_left

    @property
    def clearing(self) -> bool:
        return self._sweep_task is not None

    def start(self) -> None:
        self._seconds_to_timed = self.options.interval_minutes * 60
        self.repeat(self.advance_timer, TICKS_PER_SECOND)
        if self.options.emergency:
            self.repeat(self.check_overload, TICKS_PER_SECOND)

    def stop(self) -> None:
        super().stop()
        self._countdown_task = None
        self._seconds_left = 0
        self._sweep_task = None
        self._queue = []
        self._seconds_to_timed = 0

    def advance_timer(self) -> None:
        self._seconds_to_timed -= 1
        if self._seconds_to_timed > 0:
            return

        self._seconds_to_timed = self.options.interval_minutes * 60
        self.start_countdown()

    def check_overload(self) -> None:
        if self.counting_down or self.clearing:
            return

        options = self.options
        index = self.index
        hostiles = 0
        if options.clear_hostiles and index.total(MOB) > options.emergency_mobs:
            hostiles = sum(entry.type in HOSTILE_TYPES for entry in index.of(MOB).values())

        drops = 0
        if options.clear_items:
            drops += index.total(ITEM)
        if options.clear_xp:
            drops += index.total(XP)

        if hostiles > options.emergency_mobs:
            cause = f"§e{hostiles} §7hostile mobs"
        elif drops > options.emergency_drops:
            cause = f"§e{drops} §7dropped items and XP orbs"
        else:
            return

        now = monotonic()
        if self._emergency_at is not None and now - self._emergency_at < options.emergency_cooldown_seconds:
            return

        self._emergency_at = now
        self._emergencies += 1
        broadcast(self.server, f"§7Emergency lag clear: {cause} are loaded.")
        self.clear_now()

    def command(self, sender, args: list) -> None:
        action = args[0].lower() if args else ""
        if action == "cancel":
            if self.cancel_countdown():
                tell_success(sender, "Lag clear countdown cancelled.")
            else:
                tell_failure(sender, "No lag clear is counting down.")
            return

        if self.clearing:
            tell_failure(sender, "A lag clear is already running.")
            return

        if action == "now":
            tell_success(sender, f"Lag clear started. Entities queued: §e{self.clear_now()}")
            return

        if self.counting_down:
            tell_failure(sender, f"A lag clear is already counting down. Seconds left: §e{self._seconds_left}")
            return

        self.start_countdown()
        tell_success(sender, "Lag clear countdown started.")

    def start_countdown(self) -> bool:
        if self.counting_down or self.clearing:
            return False

        seconds = self.options.warning_seconds
        self._seconds_left = seconds
        self._halfway = seconds // 2 if seconds >= HALFWAY_FROM_SECONDS else 0
        self._countdown_task = self.repeat(self.count_second, TICKS_PER_SECOND)
        self.warn_players()
        return True

    def count_second(self) -> None:
        self._seconds_left -= 1
        if self._seconds_left <= 0:
            self.clear_now()
            return

        if self._seconds_left in (self._halfway, LAST_WARNING_SECONDS):
            self.warn_players()

    def warn_players(self) -> None:
        broadcast(self.server, f"§7Lag clear in §e{self._seconds_left} §7seconds.")

    def cancel_countdown(self) -> bool:
        if not self.counting_down:
            return False

        self.release(self._countdown_task)
        self._countdown_task = None
        self._seconds_left = 0
        return True

    def clear_now(self) -> int:
        if self.clearing:
            return 0

        self.cancel_countdown()

        options = self.options
        types = set()
        if options.clear_items:
            types.add(ITEM_TYPE)
        if options.clear_xp:
            types.add(XP_TYPE)
        if options.clear_arrows:
            types.add(ARROW_TYPE)
        if options.clear_hostiles:
            types |= HOSTILE_TYPES
        if options.clear_passives:
            types |= PASSIVE_TYPES

        self._queue = [entry for entry in self.index.snapshot() if entry.type in types]
        self._removed = 0
        self._sweep_task = self.repeat(self.sweep, 1)
        return len(self._queue)

    def sweep(self) -> None:
        budget = self.budget()
        queue = self._queue
        while queue and not budget.spent():
            entry = queue.pop()
            if not entry.alive:
                continue

            actor = entry.actor
            if entry.kind == ITEM and actor.scoreboard_tags:
                continue
            if entry.kind == MOB and actor.name_tag and STACK_TAG not in actor.scoreboard_tags:
                continue

            actor.remove()
            self._removed += 1

        if queue:
            return

        self.release(self._sweep_task)
        self._sweep_task = None
        self._cleared_at = monotonic()
        self._cleared_count = self._removed
        broadcast(self.server, f"§aLag clear finished. Entities removed: §e{self._removed}")

    def release(self, task) -> None:
        task.cancel()
        self._tasks.remove(task)

    def report(self) -> list:
        lines = []
        if self._cleared_at is not None:
            ago = describe_seconds(monotonic() - self._cleared_at)
            lines.append(("Last clear", f"{ago} ago, {self._cleared_count} removed"))
        if self._seconds_to_timed:
            lines.append(("Next timed clear", f"in {describe_seconds(self._seconds_to_timed)}"))
        if self._emergencies:
            lines.append(("Emergency clears", self._emergencies))
        return lines


def describe_seconds(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} s"
    if seconds < 60 * 60:
        return f"{seconds // 60} min"
    return f"{seconds // (60 * 60)} h {seconds // 60 % 60} min"
