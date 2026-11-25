SERVER_REPORT = "textures/items/paper"
ENTITY_CENSUS = "textures/items/spyglass"
GUIDE = "textures/items/book_normal"
RELOAD = "textures/ui/refresh"

TURN_ON = "textures/blocks/redstone_torch_on"
TURN_OFF = "textures/blocks/redstone_torch_off"
CHANGE_SETTINGS = "textures/ui/settings_glyph_color_2x"
RESET = "textures/ui/wysiwyg_reset"
USE_MY_POSITION = "textures/items/compass_item"
CLEAR_NOW = "textures/items/brush"
CANCEL_COUNTDOWN = "textures/ui/cancel"

BACK = "textures/ui/arrow_left"
REFRESH = "textures/ui/refresh"

SECTIONS = {
    "general": "textures/ui/icon_setting",
    "mob_cap": "textures/items/spawn_eggs/spawn_egg_zombie",
    "projectile_cap": "textures/items/arrow",
    "vehicle_cap": "textures/items/minecart_normal",
    "item_merge": "textures/items/hopper",
    "mob_stacker": "textures/blocks/mob_spawner",
    "lag_clear": "textures/items/brush",
    "piston_guard": "textures/blocks/piston_top_normal",
    "tnt_guard": "textures/blocks/tnt_side",
    "travel_cooldown": "textures/items/elytra",
    "afk": "textures/items/bed_red",
    "report": "textures/items/clock_item",
}

TOPICS = {
    "start": "textures/ui/infobulb",
    "lag": SERVER_REPORT,
    "limits": "textures/blocks/barrier",
    **SECTIONS,
}
