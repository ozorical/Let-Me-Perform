from endstone_let_me_perform.core.feature import Feature


class AfkMove(Feature):
    key = "afk"

    def forget(self, name: str) -> None:
        return
