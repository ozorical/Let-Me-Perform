from endstone_let_me_perform.core.feature import Feature


class Report(Feature):
    key = "report"

    def lag_command(self, sender, args: list) -> None:
        return

    def tps_command(self, sender, args: list) -> None:
        return

    def headline(self) -> str:
        return ""

    def summary(self) -> list:
        return []
