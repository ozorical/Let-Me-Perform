import re
import traceback
from pathlib import Path
from typing import ClassVar

import endstone
from endstone.command import Command, CommandSender
from endstone.plugin import Plugin

from endstone_let_me_perform.core.index import EntityIndex
from endstone_let_me_perform.core.messages import tell_failure
from endstone_let_me_perform.features import (
    AfkMove,
    ItemMerge,
    LagClear,
    MobCap,
    MobStacker,
    PistonGuard,
    ProjectileCap,
    TntGuard,
    TravelCooldown,
    VehicleCap,
)
from endstone_let_me_perform.listeners import Listeners
from endstone_let_me_perform.menus import Menus
from endstone_let_me_perform.report import Report
from endstone_let_me_perform.settings import Settings

OLDEST_ENDSTONE = (0, 11, 14)


def endstone_version() -> tuple:
    numbers = re.findall(r"\d+", str(getattr(endstone, "__version__", "")))[:3]
    return tuple(int(number) for number in numbers)


class LetMePerform(Plugin):
    api_version = "0.11"
    load = "POSTWORLD"
    prefix = "LetMePerform"
    authors: ClassVar[list] = ["Ozz"]
    description = "Entity caps, mob stacking, item merging, lag clears and guards, set up from in game menus."
    website = "https://github.com/ozorical/Let-Me-Perform"

    commands: ClassVar[dict] = {
        "config-lmp": {
            "description": "Open the Let Me Perform settings menu.",
            "usages": ["/config-lmp"],
            "aliases": ["lmp"],
            "permissions": ["lmp.command.config"],
        },
        "lag": {
            "description": "Show tick timings, loaded chunks, entity counts and what each guard has done.",
            "usages": ["/lag (entities)[report: LagReport]"],
            "permissions": ["lmp.command.lag"],
        },
        "lagclear": {
            "description": "Clear dropped items and stray mobs after a countdown, at once, or cancel a countdown.",
            "usages": ["/lagclear (now|cancel)[action: LagClearAction]"],
            "permissions": ["lmp.command.lagclear"],
        },
        "tps": {
            "description": "Show how well the server is keeping up.",
            "usages": ["/tps"],
            "permissions": ["lmp.command.tps"],
        },
    }

    permissions: ClassVar[dict] = {
        "lmp.command.config": {"description": "Open the settings menu and change settings.", "default": "op"},
        "lmp.command.lag": {"description": "Read the /lag report.", "default": "op"},
        "lmp.command.lagclear": {"description": "Start or cancel a lag clear.", "default": "op"},
        "lmp.command.tps": {"description": "Read the server tick rate.", "default": True},
    }

    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.features = ()
        self.routes = {}

    def on_enable(self) -> None:
        if endstone_version() < OLDEST_ENDSTONE:
            self.logger.warning("Let Me Perform is written for Endstone 0.11.14 or newer. Parts of it may not work on this build.")

        self.load_settings()

        self.index = EntityIndex(self)
        self.mob_cap = MobCap(self)
        self.projectile_cap = ProjectileCap(self)
        self.vehicle_cap = VehicleCap(self)
        self.item_merge = ItemMerge(self)
        self.mob_stacker = MobStacker(self)
        self.lag_clear = LagClear(self)
        self.piston_guard = PistonGuard(self)
        self.tnt_guard = TntGuard(self)
        self.travel_cooldown = TravelCooldown(self)
        self.afk = AfkMove(self)
        self.report = Report(self)
        self.features = (
            self.mob_cap,
            self.projectile_cap,
            self.vehicle_cap,
            self.item_merge,
            self.mob_stacker,
            self.lag_clear,
            self.piston_guard,
            self.tnt_guard,
            self.travel_cooldown,
            self.afk,
            self.report,
        )
        self.menus = Menus(self)

        self.routes = {
            "config-lmp": self.menus.command,
            "lag": self.report.lag_command,
            "lagclear": self.lag_clear.command,
            "tps": self.report.tps_command,
        }

        self.listeners = Listeners(self)
        self.register_events(self.listeners)
        self.apply_settings()

        running = [feature.key for feature in self.features if feature.enabled and feature is not self.report]
        self.logger.info(f"Ready with {len(running)} of {len(self.features) - 1} modules on: {', '.join(running) or 'none'}.")

    def on_disable(self) -> None:
        for feature in self.features:
            feature.stop()
        self.server.scheduler.cancel_tasks(self)

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        handler = self.routes.get(command.name)
        if handler is None:
            return False

        try:
            handler(sender, args)
        except Exception:
            self.logger.error(f"The command '{command.name}' failed:\n{traceback.format_exc()}")
            tell_failure(sender, "That command ran into a problem. The console has the details.")
        return True

    def load_settings(self) -> None:
        path = Path(self.data_folder) / "config.toml"
        try:
            created = not path.exists()
            if created:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("", encoding="utf-8")

            missing = self.settings.apply_from(self.reload_config())
            if created or missing:
                self.save_settings()
        except Exception as error:
            self.logger.error(f"Could not read config.toml, so the defaults are in use: {error}")
            self.settings.apply_from({})

    def save_settings(self) -> bool:
        try:
            self.settings.write_into(self.config)
            self.save_config()
        except Exception as error:
            self.logger.error(f"Could not write config.toml: {error}")
            return False
        return True

    def reload_settings(self) -> bool:
        try:
            self.settings.apply_from(self.reload_config())
        except Exception as error:
            self.logger.error(f"Could not reload config.toml, so the settings in memory were kept: {error}")
            return False

        self.apply_settings()
        return True

    def apply_settings(self) -> None:
        for feature in self.features:
            feature.stop()

        self.index.configure(any(feature.enabled and feature.uses_index for feature in self.features))
        for feature in self.features:
            if feature.enabled:
                feature.start()

        self.listeners.rebind()
