from math import ceil
from time import monotonic

from endstone import GameMode
from endstone.event import PlayerInteractEvent

from endstone_let_me_perform.core.feature import Feature
from endstone_let_me_perform.core.messages import show_tip

ROCKET = "minecraft:firework_rocket"
TRIDENT = "minecraft:trident"
RIPTIDE = "minecraft:riptide"
ITEM_USE = PlayerInteractEvent.Action.RIGHT_CLICK_AIR
LIMITED_MODES = (GameMode.SURVIVAL, GameMode.ADVENTURE)


class TravelCooldown(Feature):
    key = "travel_cooldown"

    def __init__(self, plugin):
        super().__init__(plugin)
        self.rocket_ready = {}
        self.riptide_ready = {}

    def stop(self) -> None:
        super().stop()
        self.rocket_ready.clear()
        self.riptide_ready.clear()

    def forget(self, name: str) -> None:
        self.rocket_ready.pop(name, None)
        self.riptide_ready.pop(name, None)

    def on_interact(self, event, item, item_id: str) -> None:
        if item_id == ROCKET:
            self.limit_rocket(event)
        elif item_id == TRIDENT:
            self.limit_riptide(event, item)

    def limit_rocket(self, event) -> None:
        wait = self.options.rocket_seconds
        if wait and event.action == ITEM_USE and event.player.is_gliding:
            self.hold_to_wait(event, self.rocket_ready, wait, "Rocket boost")

    def limit_riptide(self, event, item) -> None:
        wait = self.options.riptide_seconds
        if wait and event.action == ITEM_USE and item.item_meta.has_enchant(RIPTIDE):
            self.hold_to_wait(event, self.riptide_ready, wait, "Riptide")

    def hold_to_wait(self, event, ready_at: dict, wait: int, label: str) -> None:
        player = event.player
        if player.game_mode not in LIMITED_MODES:
            return

        name = player.name
        now = monotonic()
        ready = ready_at.get(name, 0.0)
        if now >= ready:
            ready_at[name] = now + wait
            return

        event.is_cancelled = True
        seconds_left = ceil(ready - now)
        show_tip(player, f"§c{label} is ready in §f{seconds_left}s§c.")
