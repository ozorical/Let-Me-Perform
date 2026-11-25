from endstone_let_me_perform.core.feature import Feature
from endstone_let_me_perform.core.index import ITEM

LARGEST_AMOUNT = 255


class ItemMerge(Feature):
    key = "item_merge"
    uses_index = True

    def __init__(self, plugin):
        super().__init__(plugin)
        self.merged = 0
        self._merge_cursor = []

    def start(self) -> None:
        self.repeat(self.merge_items, self.options.interval_seconds * 20)

    def stop(self) -> None:
        super().stop()
        self.merged = 0
        self._merge_cursor.clear()

    def merge_items(self) -> None:
        items = self.index.of(ITEM)
        if len(items) < 2:
            return
        if not self._merge_cursor:
            self._merge_cursor = list(items)

        size = self.options.radius
        budget = self.budget()
        piles = {}
        while self._merge_cursor and not budget.spent():
            entry = items.get(self._merge_cursor.pop())
            if entry is None or not entry.alive:
                continue

            actor = entry.actor
            stack = actor.item_stack
            location = actor.location
            spot = (
                location.dimension.name,
                location.block_x // size,
                location.block_y // size,
                location.block_z // size,
                stack.type.id,
            )

            pile = piles.get(spot)
            if pile is None or not self.merge_pair(*pile, actor, stack):
                piles[spot] = (actor, stack)

    def merge_pair(self, survivor, held, other, stack) -> bool:
        if not held.is_similar(stack):
            return False

        total = held.amount + stack.amount
        if total > min(held.max_stack_size, LARGEST_AMOUNT):
            return False
        if survivor.pickup_delay > 0 or other.pickup_delay > 0:
            return False
        if survivor.scoreboard_tags or other.scoreboard_tags:
            return False

        held.amount = total
        survivor.item_stack = held
        other.remove()
        self.merged += 1
        return True

    def report(self) -> list:
        return [("Items merged away", self.merged), ("Dropped items tracked", self.index.total(ITEM))]
