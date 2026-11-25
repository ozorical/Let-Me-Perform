from time import monotonic

from endstone_let_me_perform.core.feature import Feature
from endstone_let_me_perform.core.messages import show_tip
from endstone_let_me_perform.core.tables import TNT_TYPES

TNT_BLOCK = "minecraft:tnt"
ANNOUNCE_RADIUS = 24
CELL_LIMIT = 256


def copy_of(block):
    return block.get_relative(0, 0, 0)


class Chain:
    __slots__ = ("started", "blasts", "announced")

    def __init__(self, started: float):
        self.started = started
        self.blasts = 0
        self.announced = False


class TntGuard(Feature):
    key = "tnt_guard"

    def __init__(self, plugin):
        super().__init__(plugin)
        self.chains = {}
        self.damped = 0
        self.cancelled = 0

    def stop(self) -> None:
        super().stop()
        self.chains.clear()

    def on_explode(self, event) -> None:
        if event.actor.type not in TNT_TYPES:
            return

        options = self.options
        location = event.location
        dimension = location.dimension.name
        size = options.cell_size
        cell = (dimension, location.block_x // size, location.block_y // size, location.block_z // size)

        now = monotonic()
        chain = self.chains.get(cell)
        if chain is None or now - chain.started >= options.window_seconds:
            if len(self.chains) >= CELL_LIMIT:
                self.drop_finished_chains(now)
            chain = self.chains[cell] = Chain(now)

        chain.blasts += 1
        if chain.blasts <= options.chain_limit:
            return

        if chain.blasts > options.hard_limit:
            event.is_cancelled = True
            self.cancelled += 1
        else:
            self.keep_tnt_unlit(event)

        if chain.announced:
            return

        chain.announced = True
        self.tell_nearby_players(location, dimension)

    def drop_finished_chains(self, now: float) -> None:
        cutoff = now - self.options.window_seconds
        self.chains = {cell: chain for cell, chain in self.chains.items() if chain.started > cutoff}

    def keep_tnt_unlit(self, event) -> None:
        blocks = event.block_list
        kept = [block for block in blocks if block.type != TNT_BLOCK]
        if len(kept) == len(blocks):
            return

        event.block_list = [copy_of(block) for block in kept]
        self.damped += 1

    def tell_nearby_players(self, location, dimension: str) -> None:
        for player in self.server.online_players:
            spot = player.location
            if spot.dimension.name == dimension and spot.distance_squared(location) <= ANNOUNCE_RADIUS**2:
                show_tip(player, "§cToo much TNT went off at once, so the chain was stopped.")

    def report(self) -> list:
        if not self.damped and not self.cancelled:
            return []
        return [("Blasts damped", self.damped), ("Blasts cancelled", self.cancelled)]
