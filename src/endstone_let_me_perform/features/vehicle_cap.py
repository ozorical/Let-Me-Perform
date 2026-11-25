from endstone_let_me_perform.core.feature import Feature


class VehicleCap(Feature):
    key = "vehicle_cap"
    uses_index = True

    def on_interact(self, event, item, item_id: str) -> None:
        return
