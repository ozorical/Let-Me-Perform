from time import monotonic

from endstone_let_me_perform.core.feature import Feature

TRACK_LIMIT = 4000
PRUNE_TICKS = 200


class PistonGuard(Feature):
    key = "piston_guard"

    def __init__(self, plugin):
        super().__init__(plugin)
        self.windows = {}
        self.paused = {}
        self.pauses = 0

    def start(self) -> None:
        self.repeat(self.prune, PRUNE_TICKS)

    def stop(self) -> None:
        super().stop()
        self.windows.clear()
        self.paused.clear()

    def on_piston(self, event) -> None:
        block = event.block
        piston = (block.dimension.name, block.x, block.y, block.z)
        now = monotonic()

        until = self.paused.get(piston)
        if until is not None:
            if now < until:
                event.is_cancelled = True
                return
            del self.paused[piston]

        options = self.options
        window = self.windows.get(piston)
        if window is None:
            if len(self.windows) >= TRACK_LIMIT:
                return
            started, moves = now, 0
        else:
            started, moves = window
            if now - started > options.window_seconds:
                started, moves = now, 0

        moves += 1
        if moves <= options.moves_per_window:
            self.windows[piston] = (started, moves)
            return

        del self.windows[piston]
        self.paused[piston] = now + options.suspend_seconds
        self.pauses += 1
        event.is_cancelled = True

        dimension, x, y, z = piston
        self.logger.warning(
            f"Piston at {x} {y} {z} in {dimension} moved more than {options.moves_per_window} times "
            f"in {options.window_seconds} seconds, so it is paused for {options.suspend_seconds} seconds."
        )

    def prune(self) -> None:
        now = monotonic()
        cutoff = now - self.options.window_seconds
        self.windows = {piston: window for piston, window in self.windows.items() if window[0] >= cutoff}
        self.paused = {piston: until for piston, until in self.paused.items() if until > now}

    def report(self) -> list:
        if not self.pauses:
            return []

        now = monotonic()
        paused_now = sum(1 for until in self.paused.values() if until > now)
        return [("Pistons paused", self.pauses), ("Paused now", paused_now)]
