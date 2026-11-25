from endstone_let_me_perform.core.feature import Feature


class MobStacker(Feature):
    key = "mob_stacker"
    uses_index = True

    def on_death(self, event) -> None:
        return
