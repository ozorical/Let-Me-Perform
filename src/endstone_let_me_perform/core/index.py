from endstone.actor import Item, Mob

from endstone_let_me_perform.core.budget import Budget
from endstone_let_me_perform.core.tables import CAPPED_PROJECTILES, ITEM_TYPE, PLAYER_TYPE, VEHICLE_TYPES, XP_TYPE

MOB = "mob"
ITEM = "item"
XP = "xp"
PROJECTILE = "projectile"
VEHICLE = "vehicle"

KINDS = (MOB, ITEM, XP, PROJECTILE, VEHICLE)
COUNTED_KINDS = (MOB, PROJECTILE, VEHICLE)

PLAIN_KINDS = {XP_TYPE: XP}
PLAIN_KINDS.update({type_id: PROJECTILE for type_id in CAPPED_PROJECTILES})
PLAIN_KINDS.update({type_id: VEHICLE for type_id in VEHICLE_TYPES})

KIND_LIMIT = 20000
PRUNE_TICKS = 200
PRUNE_SLICE = 800
SEED_DELAY_TICKS = 100


def chunk_of(actor):
    try:
        location = actor.location
        return (location.dimension.name, location.block_x >> 4, location.block_z >> 4)
    except Exception:
        return None


class Entry:
    __slots__ = ("actor", "id", "kind", "type", "chunk")

    def __init__(self, actor, actor_id, kind, type_id, chunk):
        self.actor = actor
        self.id = actor_id
        self.kind = kind
        self.type = type_id
        self.chunk = chunk

    @property
    def alive(self) -> bool:
        try:
            return bool(self.actor.is_valid)
        except Exception:
            return False


class EntityIndex:
    def __init__(self, plugin):
        self.plugin = plugin
        self.active = False
        self.spawning = False
        self.resets = 0
        self.protected = frozenset()
        self.entries = {}
        self.by_kind = {kind: {} for kind in KINDS}
        self.counts = {kind: {} for kind in COUNTED_KINDS}
        self._prune_cursor = []
        self._prune_task = None

    def configure(self, wanted: bool) -> None:
        self.protected = frozenset(self.plugin.settings.general.protected_types)
        if wanted == self.active:
            return

        self.active = wanted
        if self._prune_task is not None:
            self._prune_task.cancel()
            self._prune_task = None

        if not wanted:
            self.clear()
            return

        scheduler = self.plugin.server.scheduler
        self._prune_task = scheduler.run_task(self.plugin, self.prune, delay=PRUNE_TICKS, period=PRUNE_TICKS)
        scheduler.run_task(self.plugin, self.seed, delay=SEED_DELAY_TICKS)

    def classify(self, actor):
        if isinstance(actor, Item):
            return Entry(actor, actor.id, ITEM, ITEM_TYPE, None)

        type_id = actor.type
        kind = PLAIN_KINDS.get(type_id)
        if kind is None:
            if type_id == PLAYER_TYPE or not isinstance(actor, Mob):
                return None
            if type_id in self.protected or not type_id.startswith("minecraft:"):
                return None
            kind = MOB

        chunk = chunk_of(actor) if kind in COUNTED_KINDS else None
        if chunk is None and kind in COUNTED_KINDS:
            return None
        return Entry(actor, actor.id, kind, type_id, chunk)

    def track(self, entry: Entry) -> None:
        bucket = self.by_kind[entry.kind]
        if len(bucket) >= KIND_LIMIT:
            if entry.kind not in COUNTED_KINDS:
                return
            self.reset_counted()

        self.entries[entry.id] = entry
        bucket[entry.id] = entry
        if entry.chunk is not None:
            counts = self.counts[entry.kind]
            counts[entry.chunk] = counts.get(entry.chunk, 0) + 1

    def forget(self, actor_id: int) -> None:
        entry = self.entries.pop(actor_id, None)
        if entry is None:
            return

        self.by_kind[entry.kind].pop(actor_id, None)
        if entry.chunk is not None:
            self._release(entry.kind, entry.chunk)

    def move(self, entry: Entry, chunk) -> None:
        if chunk == entry.chunk or entry.id not in self.entries:
            return

        self._release(entry.kind, entry.chunk)
        counts = self.counts[entry.kind]
        counts[chunk] = counts.get(chunk, 0) + 1
        entry.chunk = chunk

    def _release(self, kind: str, chunk) -> None:
        counts = self.counts[kind]
        left = counts.get(chunk, 0) - 1
        if left > 0:
            counts[chunk] = left
        else:
            counts.pop(chunk, None)

    def count(self, kind: str, chunk) -> int:
        return self.counts[kind].get(chunk, 0)

    def total(self, kind: str) -> int:
        return len(self.by_kind[kind])

    def of(self, kind: str) -> dict:
        return self.by_kind[kind]

    def busiest(self, kind: str, limit: int) -> list:
        return sorted(self.counts[kind].items(), key=lambda pair: pair[1], reverse=True)[:limit]

    def snapshot(self) -> list:
        if self.active:
            return list(self.entries.values())

        self.protected = frozenset(self.plugin.settings.general.protected_types)
        found = []
        for actor in self.plugin.server.level.actors:
            try:
                entry = self.classify(actor)
            except Exception:
                continue
            if entry is not None:
                found.append(entry)
        return found

    def spawn(self, location, type_id: str):
        self.spawning = True
        try:
            return location.dimension.spawn_actor(location, type_id)
        finally:
            self.spawning = False

    def seed(self) -> None:
        if not self.active:
            return

        for actor in self.plugin.server.level.actors:
            try:
                if actor.id in self.entries:
                    continue
                entry = self.classify(actor)
            except Exception:
                continue
            if entry is not None:
                self.track(entry)

    def prune(self) -> None:
        if not self._prune_cursor:
            if not self.entries:
                return
            self._prune_cursor = list(self.entries)

        budget = Budget(self.plugin.settings.general.sweep_budget_ms)
        for _ in range(PRUNE_SLICE):
            if not self._prune_cursor or budget.spent():
                return

            actor_id = self._prune_cursor.pop()
            entry = self.entries.get(actor_id)
            if entry is not None and not entry.alive:
                self.forget(actor_id)

    def reset_counted(self) -> None:
        for kind in COUNTED_KINDS:
            for actor_id in self.by_kind[kind]:
                self.entries.pop(actor_id, None)
            self.by_kind[kind].clear()
            self.counts[kind].clear()

        self._prune_cursor.clear()
        self.resets += 1
        self.plugin.logger.warning(f"Entity tracking passed {KIND_LIMIT} live entities of one kind, so the chunk counts were reset.")

    def clear(self) -> None:
        self.entries.clear()
        self._prune_cursor.clear()
        for bucket in self.by_kind.values():
            bucket.clear()
        for counts in self.counts.values():
            counts.clear()
