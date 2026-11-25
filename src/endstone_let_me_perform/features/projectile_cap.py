from endstone_let_me_perform.core.feature import Feature


class ProjectileCap(Feature):
    key = "projectile_cap"
    uses_index = True

    def admit(self, entry) -> bool:
        return True
