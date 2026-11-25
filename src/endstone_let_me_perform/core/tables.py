PROTECTED_TYPES = (
    "minecraft:villager",
    "minecraft:villager_v2",
    "minecraft:wandering_trader",
    "minecraft:iron_golem",
    "minecraft:snow_golem",
    "minecraft:npc",
    "minecraft:wither",
    "minecraft:ender_dragon",
    "minecraft:elder_guardian",
    "minecraft:warden",
    "minecraft:wolf",
    "minecraft:cat",
    "minecraft:ocelot",
    "minecraft:parrot",
    "minecraft:horse",
    "minecraft:donkey",
    "minecraft:mule",
    "minecraft:llama",
    "minecraft:trader_llama",
    "minecraft:skeleton_horse",
    "minecraft:zombie_horse",
    "minecraft:camel",
    "minecraft:allay",
    "minecraft:armor_stand",
)

HOSTILE_TYPES = frozenset({
    "minecraft:zombie",
    "minecraft:zombie_villager",
    "minecraft:zombie_villager_v2",
    "minecraft:zombie_pigman",
    "minecraft:husk",
    "minecraft:stray",
    "minecraft:drowned",
    "minecraft:skeleton",
    "minecraft:wither_skeleton",
    "minecraft:bogged",
    "minecraft:spider",
    "minecraft:cave_spider",
    "minecraft:creeper",
    "minecraft:enderman",
    "minecraft:endermite",
    "minecraft:silverfish",
    "minecraft:slime",
    "minecraft:magma_cube",
    "minecraft:blaze",
    "minecraft:ghast",
    "minecraft:witch",
    "minecraft:phantom",
    "minecraft:shulker",
    "minecraft:guardian",
    "minecraft:pillager",
    "minecraft:vindicator",
    "minecraft:evocation_illager",
    "minecraft:ravager",
    "minecraft:vex",
    "minecraft:piglin",
    "minecraft:piglin_brute",
    "minecraft:hoglin",
    "minecraft:zoglin",
    "minecraft:breeze",
})

PASSIVE_TYPES = frozenset({
    "minecraft:bat",
    "minecraft:chicken",
    "minecraft:cow",
    "minecraft:mooshroom",
    "minecraft:pig",
    "minecraft:polar_bear",
    "minecraft:sheep",
})

CAPPED_PROJECTILES = frozenset({
    "minecraft:arrow",
    "minecraft:snowball",
    "minecraft:egg",
    "minecraft:splash_potion",
    "minecraft:lingering_potion",
    "minecraft:xp_bottle",
    "minecraft:small_fireball",
    "minecraft:wind_charge_projectile",
})

VEHICLE_TYPES = frozenset({
    "minecraft:boat",
    "minecraft:chest_boat",
    "minecraft:minecart",
    "minecraft:chest_minecart",
    "minecraft:hopper_minecart",
    "minecraft:tnt_minecart",
    "minecraft:command_block_minecart",
})

TNT_TYPES = frozenset({"minecraft:tnt", "minecraft:tnt_minecart"})

ITEM_TYPE = "minecraft:item"
XP_TYPE = "minecraft:xp_orb"
ARROW_TYPE = "minecraft:arrow"

DIMENSION_NAMES = ("Overworld", "Nether", "TheEnd")


def is_vehicle_item(item_id: str) -> bool:
    return item_id.endswith(("_boat", "_raft", "minecart"))
