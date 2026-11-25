from endstone_let_me_perform.core.feature import Feature


class LagClear(Feature):
    key = "lag_clear"
    uses_index = True

    def command(self, sender, args: list) -> None:
        return

    def start_countdown(self) -> bool:
        return False

    def cancel_countdown(self) -> bool:
        return False

    def clear_now(self) -> int:
        return 0
