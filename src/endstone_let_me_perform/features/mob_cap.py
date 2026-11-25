from endstone_let_me_perform.core.feature import Feature


class MobCap(Feature):
    key = "mob_cap"
    uses_index = True

    def admit(self, entry) -> bool:
        return True
