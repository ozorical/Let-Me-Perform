from endstone_let_me_perform.core.feature import Feature


class PistonGuard(Feature):
    key = "piston_guard"

    def on_piston(self, event) -> None:
        return
