from endstone_let_me_perform.core.feature import Feature


class TntGuard(Feature):
    key = "tnt_guard"

    def on_explode(self, event) -> None:
        return
