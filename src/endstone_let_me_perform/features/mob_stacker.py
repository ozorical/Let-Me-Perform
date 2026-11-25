import re

from endstone.level import Location

from endstone_let_me_perform.core.feature import Feature
from endstone_let_me_perform.core.index import MOB, chunk_of
from endstone_let_me_perform.core.tables import STACK_TAG

TICKS_PER_SECOND = 20
NAMED_BY_PLAYER = 0
STACK_LABEL = re.compile(r"§e.+ §7x(\d+)")


def make_label(type_id: str, count: int) -> str:
    name = type_id.rpartition(":")[2].replace("_", " ").title()
    return f"§e{name} §7x{count}"


def read_label(label: str) -> int:
    match = STACK_LABEL.fullmatch(label)
    return int(match.group(1)) if match else NAMED_BY_PLAYER


class Stack:
    __slots__ = ("entry", "before", "count")

    def __init__(self, entry, count: int):
        self.entry = entry
        self.before = count
        self.count = count


class MobStacker(Feature):
    key = "mob_stacker"
    uses_index = True

    def __init__(self, plugin):
        super().__init__(plugin)
        self.counts = {}
        self._cursor = []
        self._chunks = {}

    def start(self) -> None:
        self.repeat(self.start_pass, self.options.interval_seconds * TICKS_PER_SECOND)

    def stop(self) -> None:
        super().stop()
        self.counts.clear()
        self._cursor.clear()
        self._chunks.clear()

    def start_pass(self) -> None:
        if self._cursor or self._chunks:
            return

        mobs = self.index.of(MOB)
        self.counts = {actor_id: count for actor_id, count in self.counts.items() if actor_id in mobs}
        self._cursor = list(mobs.values())
        self.continue_pass()

    def continue_pass(self) -> None:
        budget = self.budget()
        while self._cursor:
            if budget.spent():
                self.later(self.continue_pass, 1)
                return
            self.visit(self._cursor.pop())

        while self._chunks:
            if budget.spent():
                self.later(self.continue_pass, 1)
                return
            self.settle_chunk(self._chunks.popitem()[1])

    def visit(self, entry) -> None:
        chunk = chunk_of(entry.actor)
        if chunk is None:
            return

        self.index.move(entry, chunk)
        if self.read_count(entry.actor, entry.id) == NAMED_BY_PLAYER:
            return

        self._chunks.setdefault(chunk, {}).setdefault(entry.type, []).append(entry)

    def settle_chunk(self, by_type: dict) -> None:
        survivors = []
        for group in by_type.values():
            survivors.extend(self.fold(group) if len(group) > 1 else group)

        limit = self.options.chunk_limit
        if limit < 1:
            return

        for entry in survivors[limit:]:
            if entry.alive:
                self.remove(entry)

    def fold(self, group: list) -> list:
        counts = self.counts
        stacks = [Stack(entry, counts.get(entry.id, 1)) for entry in group if entry.alive]
        stacks.sort(key=lambda stack: stack.count, reverse=True)

        largest = self.options.max_stack
        leader = 0
        follower = len(stacks) - 1
        while leader < follower:
            space = largest - stacks[leader].count
            if space <= 0:
                leader += 1
                continue

            moved = min(space, stacks[follower].count)
            stacks[leader].count += moved
            stacks[follower].count -= moved
            if stacks[follower].count == 0:
                follower -= 1

        survivors = []
        for stack in stacks:
            entry = stack.entry
            if stack.count == 0:
                self.remove(entry)
                continue

            survivors.append(entry)
            if stack.count != stack.before:
                self.write_count(entry.actor, entry.id, entry.type, stack.count)
        return survivors

    def on_death(self, event) -> None:
        actor = event.actor
        count = self.read_count(actor, actor.id)
        if count < 2:
            return

        location = actor.location
        dimension_name = location.dimension.name
        x, y, z = location.x, location.y, location.z
        type_id = actor.type
        self.later(lambda: self.spawn_rest(dimension_name, x, y, z, type_id, count - 1), 1)

    def spawn_rest(self, dimension_name: str, x: float, y: float, z: float, type_id: str, count: int) -> None:
        dimension = self.server.level.get_dimension(dimension_name)
        actor = self.index.spawn(Location(dimension, x, y, z), type_id)
        if actor is None or count < 2:
            return

        self.write_count(actor, actor.id, type_id, count)

    def report(self) -> list:
        stacks = [count for count in self.counts.values() if count > 1]
        if not stacks:
            return []
        return [("Stacks", len(stacks)), ("Mobs in stacks", sum(stacks))]

    def read_count(self, actor, actor_id: int) -> int:
        count = self.counts.get(actor_id)
        if count is not None:
            return count

        label = actor.name_tag
        if not label:
            return 1

        count = read_label(label) if STACK_TAG in actor.scoreboard_tags else NAMED_BY_PLAYER
        self.counts[actor_id] = count
        return count

    def write_count(self, actor, actor_id: int, type_id: str, count: int) -> None:
        if count < 2:
            self.counts.pop(actor_id, None)
            actor.remove_scoreboard_tag(STACK_TAG)
            actor.name_tag = ""
            return

        self.counts[actor_id] = count
        actor.add_scoreboard_tag(STACK_TAG)
        actor.name_tag = make_label(type_id, count)

    def remove(self, entry) -> None:
        self.counts.pop(entry.id, None)
        entry.actor.remove()
