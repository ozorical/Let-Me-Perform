from endstone_let_me_perform.core.feature import Feature
from endstone_let_me_perform.core.index import MOB


class MobCap(Feature):
    key = "mob_cap"
    uses_index = True

    def __init__(self, plugin):
        super().__init__(plugin)
        self.refused = 0

    def stop(self) -> None:
        super().stop()
        self.refused = 0

    def admit(self, entry) -> bool:
        if entry.kind != MOB:
            return True
        if self.index.count(MOB, entry.chunk) < self.options.per_chunk:
            return True
        if entry.actor.name_tag:
            return True

        self.refused += 1
        return False

    def report(self) -> list:
        return [("Spawns refused", self.refused)]
