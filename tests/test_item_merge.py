from endstone_let_me_perform.core.index import ITEM


class Allowance:
    def __init__(self, checks):
        self.left = checks

    def spent(self):
        self.left -= 1
        return self.left < 0


def run_pass(plugin, passes=1):
    plugin.server.scheduler.advance(plugin.settings.item_merge.interval_seconds * 20 * passes)


def amounts_on_the_ground(plugin):
    return sorted(entry.actor.item_stack.amount for entry in plugin.index.of(ITEM).values())


def test_two_stacks_merge_and_the_survivor_holds_the_sum(plugin, server):
    first = server.drop("minecraft:cobblestone", 20, 1, 64, 1)
    second = server.drop("minecraft:cobblestone", 12, 2, 65, 3)

    run_pass(plugin)

    survivors = [item for item in (first, second) if item.is_valid]
    assert len(survivors) == 1
    assert survivors[0].item_stack.amount == 32
    assert plugin.index.total(ITEM) == 1
    assert plugin.item_merge.report() == [("Items merged away", 1), ("Dropped items tracked", 1)]


def test_a_pile_folds_into_as_few_stacks_as_fit(plugin, server):
    for amount in (64, 10, 20, 30):
        server.drop("minecraft:iron_ingot", amount)

    run_pass(plugin)

    assert amounts_on_the_ground(plugin) == [60, 64]
    assert plugin.item_merge.merged == 2


def test_different_items_stay_apart(plugin, server):
    server.drop("minecraft:cobblestone", 5)
    server.drop("minecraft:dirt", 5)
    server.drop("minecraft:wool", 5)
    server.drop("minecraft:wool", 5).item_stack.data = 14
    server.drop("minecraft:paper", 5)
    server.drop("minecraft:paper", 5).item_stack.item_meta.display_name = "Deed"

    run_pass(plugin)

    assert amounts_on_the_ground(plugin) == [5, 5, 5, 5, 5, 5]
    assert plugin.item_merge.merged == 0


def test_a_mixed_pile_merges_kind_by_kind(plugin, server):
    for item_id in ("minecraft:cobblestone", "minecraft:dirt", "minecraft:cobblestone", "minecraft:dirt", "minecraft:cobblestone"):
        server.drop(item_id, 4)

    run_pass(plugin)

    assert amounts_on_the_ground(plugin) == [8, 12]
    assert plugin.item_merge.merged == 3


def test_items_in_different_cubes_stay_apart(plugin, server, switch_on):
    switch_on(item_merge__radius=4)
    server.drop("minecraft:dirt", 5, 1, 64, 1)
    server.drop("minecraft:dirt", 5, 9, 64, 1)
    server.drop("minecraft:dirt", 5, 1, 70, 1)
    server.drop("minecraft:dirt", 5, 1, 64, -1)
    server.drop("minecraft:dirt", 5, 1, 64, 1, server.level.get_dimension("Nether"))

    run_pass(plugin)
    assert amounts_on_the_ground(plugin) == [5, 5, 5, 5, 5]

    switch_on(item_merge__radius=16)
    run_pass(plugin)
    assert amounts_on_the_ground(plugin) == [5, 5, 15]


def test_stacks_merge_up_to_the_stack_size_and_no_further(plugin, server):
    server.drop("minecraft:dirt", 40)
    server.drop("minecraft:dirt", 25)
    server.drop("minecraft:ender_pearl", 10, max_stack_size=16)
    server.drop("minecraft:ender_pearl", 7, max_stack_size=16)
    server.drop("minecraft:gravel", 40)
    server.drop("minecraft:gravel", 24)
    server.drop("minecraft:snowball", 9, max_stack_size=16)
    server.drop("minecraft:snowball", 7, max_stack_size=16)

    run_pass(plugin)

    assert amounts_on_the_ground(plugin) == [7, 10, 16, 25, 40, 64]
    assert plugin.item_merge.merged == 2


def test_no_stack_grows_past_what_an_amount_can_hold(plugin, server):
    server.drop("myaddon:token", 200, max_stack_size=1000)
    server.drop("myaddon:token", 56, max_stack_size=1000)
    server.drop("myaddon:coin", 200, max_stack_size=1000)
    server.drop("myaddon:coin", 55, max_stack_size=1000)

    run_pass(plugin)

    assert amounts_on_the_ground(plugin) == [56, 200, 255]


def test_items_still_locked_to_their_owner_wait(plugin, server):
    early = server.drop("minecraft:diamond", 3)
    server.drop("minecraft:diamond", 2)
    server.drop("minecraft:emerald", 2, 20)
    late = server.drop("minecraft:emerald", 3, 20)
    early.pickup_delay = 40
    late.pickup_delay = 40

    run_pass(plugin)
    assert amounts_on_the_ground(plugin) == [2, 2, 3, 3]

    early.pickup_delay = 0
    late.pickup_delay = 0
    run_pass(plugin)
    assert amounts_on_the_ground(plugin) == [5, 5]


def test_tagged_items_are_never_merged(plugin, server):
    server.drop("minecraft:diamond", 1).add_scoreboard_tag("shop_display")
    server.drop("minecraft:diamond", 1)
    server.drop("minecraft:emerald", 1, 20)
    server.drop("minecraft:emerald", 1, 20).add_scoreboard_tag("shop_display")

    run_pass(plugin)

    assert amounts_on_the_ground(plugin) == [1, 1, 1, 1]
    assert plugin.item_merge.merged == 0


def test_an_item_that_is_gone_is_not_merged_into(plugin, server):
    kept = server.drop("minecraft:dirt", 5)
    gone = server.drop("minecraft:dirt", 5)
    gone.is_valid = False

    run_pass(plugin)

    assert kept.is_valid
    assert kept.item_stack.amount == 5
    assert plugin.item_merge.merged == 0


def test_passes_follow_the_interval_setting(plugin, server, switch_on):
    switch_on(item_merge__interval_seconds=2)
    server.drop("minecraft:dirt", 5)
    server.drop("minecraft:dirt", 5)

    server.scheduler.advance(39)
    assert plugin.index.total(ITEM) == 2

    server.scheduler.advance(1)
    assert plugin.index.total(ITEM) == 1


def test_a_big_pile_is_spread_over_several_passes(plugin, server, monkeypatch):
    for _ in range(6):
        server.drop("minecraft:dirt", 1)
    monkeypatch.setattr(plugin.item_merge, "budget", lambda: Allowance(2))

    run_pass(plugin)
    assert amounts_on_the_ground(plugin) == [1, 1, 1, 1, 2]

    run_pass(plugin, 2)
    assert amounts_on_the_ground(plugin) == [2, 2, 2]

    run_pass(plugin, 3)
    assert amounts_on_the_ground(plugin) == [6]
    assert plugin.item_merge.merged == 5


def test_a_settings_change_starts_the_count_and_the_pass_again(plugin, server, monkeypatch):
    for _ in range(4):
        server.drop("minecraft:dirt", 1)
    monkeypatch.setattr(plugin.item_merge, "budget", lambda: Allowance(2))
    run_pass(plugin)
    assert plugin.item_merge.merged == 1

    plugin.apply_settings()
    assert plugin.item_merge.report() == [("Items merged away", 0), ("Dropped items tracked", 3)]

    run_pass(plugin)
    assert amounts_on_the_ground(plugin) == [1, 3]
