from endstone_let_me_perform.core.feature import Feature
from endstone_let_me_perform.core.index import PROJECTILE


class ProjectileCap(Feature):
    key = "projectile_cap"
    uses_index = True

    def __init__(self, plugin):
        super().__init__(plugin)
        self.refused = 0

    def stop(self) -> None:
        super().stop()
        self.refused = 0

    def admit(self, entry) -> bool:
        if entry.kind != PROJECTILE:
            return True
        if self.index.count(PROJECTILE, entry.chunk) < self.options.per_chunk:
            return True

        self.refused += 1
        return False

    def report(self) -> list:
        return [("Projectiles refused", self.refused)]
