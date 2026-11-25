from endstone_let_me_perform.core.feature import Feature


class TravelCooldown(Feature):
    key = "travel_cooldown"

    def on_interact(self, event, item, item_id: str) -> None:
        return

    def forget(self, name: str) -> None:
        return
