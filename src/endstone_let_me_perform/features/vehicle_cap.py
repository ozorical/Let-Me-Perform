from endstone.block import BlockFace
from endstone.event import PlayerInteractEvent

from endstone_let_me_perform.core.feature import Feature
from endstone_let_me_perform.core.index import VEHICLE, chunk_of
from endstone_let_me_perform.core.messages import show_tip
from endstone_let_me_perform.core.tables import is_vehicle_item

RECOUNT_TICKS = 5 * 60 * 20

FACE_OFFSETS = {
    BlockFace.DOWN: (0, 0),
    BlockFace.UP: (0, 0),
    BlockFace.NORTH: (0, -1),
    BlockFace.SOUTH: (0, 1),
    BlockFace.WEST: (-1, 0),
    BlockFace.EAST: (1, 0),
}


class VehicleCap(Feature):
    key = "vehicle_cap"
    uses_index = True

    def __init__(self, plugin):
        super().__init__(plugin)
        self.refused = 0
        self._recount_cursor = []

    def start(self) -> None:
        self.repeat(self.start_recount, RECOUNT_TICKS)

    def stop(self) -> None:
        super().stop()
        self.refused = 0
        self._recount_cursor.clear()

    def on_interact(self, event, item, item_id: str) -> None:
        if not is_vehicle_item(item_id):
            return

        action = event.action
        if action == PlayerInteractEvent.Action.RIGHT_CLICK_BLOCK:
            block = event.block
            dimension = block.dimension.name
            x, z = block.x, block.z
            side_x, side_z = FACE_OFFSETS[event.block_face]
            chunks = ((dimension, x >> 4, z >> 4), (dimension, (x + side_x) >> 4, (z + side_z) >> 4))
        elif action == PlayerInteractEvent.Action.RIGHT_CLICK_AIR:
            chunks = (chunk_of(event.player),)
        else:
            return

        fullest = max(self.index.count(VEHICLE, chunk) for chunk in chunks)
        if fullest < self.options.per_chunk:
            return

        event.is_cancelled = True
        self.refused += 1
        show_tip(event.player, f"§cThis chunk is full. Boats and minecarts here: §e{fullest}")

    def start_recount(self) -> None:
        self._recount_cursor = list(self.index.of(VEHICLE))
        self.recount()

    def recount(self) -> None:
        vehicles = self.index.of(VEHICLE)
        budget = self.budget()
        while self._recount_cursor:
            if budget.spent():
                self.later(self.recount, 1)
                return

            entry = vehicles.get(self._recount_cursor.pop())
            if entry is None:
                continue

            chunk = chunk_of(entry.actor)
            if chunk is not None:
                self.index.move(entry, chunk)

    def report(self) -> list:
        return [("Placements refused", self.refused)]
