import sys
import types

import pytest
from fake_endstone import Chunk, Command

from endstone_let_me_perform import LetMePerform
from endstone_let_me_perform.report import audit, metrics
from endstone_let_me_perform.report.report import FIRST_SAMPLE_TICKS
from endstone_let_me_perform.settings import SECTIONS

PROPERTIES = "\n".join((
    "#Bedrock server settings",
    "",
    "server-name=Dedicated Server",
    "view-distance = 32",
    "#tick-distance=12",
    "tick-distance=4",
    "max-threads=8",
    "not a setting",
    "player-idle-timeout=30",
    "compression-algorithm=zlib",
    "compression-threshold=1",
    "client-side-chunk-generation-enabled=true",
    "level-seed=",
    "",
))


class FakeProcess:
    def memory_info(self):
        return types.SimpleNamespace(rss=512 * 1024 * 1024)


@pytest.fixture(autouse=True)
def away_from_any_server_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def quiet_modules(plugin, monkeypatch):
    for feature in plugin.features:
        monkeypatch.setattr(feature, "report", lambda: [])


def enabled_plugin(server, folder):
    created = LetMePerform()
    created.attach(server, folder)
    created.on_enable()
    return created


def headings(sections):
    return [heading for heading, _ in sections]


def rows_under(sections, heading):
    return dict(sections)[heading]


def labels_under(sections, heading):
    return [label for label, _ in rows_under(sections, heading)]


def audit_warnings(server):
    return [line for line in server.logger.said("warning") if line.startswith("server.properties")]


def stat_line(user_ticks, system_ticks):
    return f"4242 (bedrock (main)) S 1 1 1 0 0 0 0 0 0 0 {user_ticks} {system_ticks} 0 0 20 0 9 0 5000\n"


def test_summary_keeps_its_order_and_leaves_out_empty_sections(plugin, server, tmp_path, quiet_modules, monkeypatch):
    assert headings(plugin.report.summary()) == ["Timings", "Entities", "Server settings"]

    (tmp_path / "server.properties").write_text("view-distance=32\n", encoding="utf-8")
    monkeypatch.setattr(plugin.tnt_guard, "report", lambda: [("Blasts damped", 2)])
    monkeypatch.setattr(plugin.projectile_cap, "report", lambda: [("Projectiles denied", 4)])
    plugin.apply_settings()
    server.scheduler.advance(FIRST_SAMPLE_TICKS)

    summary = plugin.report.summary()
    assert headings(summary) == [
        "Timings",
        "Chunks",
        "Entities",
        "Projectile cap",
        "TNT chain guard",
        "Server settings",
        "Advice",
    ]
    assert labels_under(summary, "Advice") == ["View distance"]


def test_a_module_reports_under_its_title_only_while_it_is_on(plugin, switch_on, monkeypatch):
    monkeypatch.setattr(plugin.mob_cap, "report", lambda: [("Spawns denied", 12)])
    assert "Mob cap" not in headings(plugin.report.summary())

    switch_on("mob_cap")
    assert rows_under(plugin.report.summary(), "Mob cap") == [("Spawns denied", 12)]

    plugin.settings.change("mob_cap", "enabled", False)
    plugin.apply_settings()
    assert "Mob cap" not in headings(plugin.report.summary())


def test_entity_section_follows_the_index(plugin, server):
    for _ in range(3):
        server.spawn_mob("minecraft:zombie", 40, 64, 5)
    for _ in range(2):
        server.spawn_mob("minecraft:cow", 5, 64, 5)
    server.spawn_mob("minecraft:pig", 5, 64, 40)
    server.spawn_mob("minecraft:sheep", 70, 64, 70)
    server.spawn_mob("minecraft:villager_v2", 5, 64, 5)
    server.spawn_plain("minecraft:arrow", 5, 64, 5)
    server.drop("minecraft:dirt", 2, 5, 64, 5)

    assert rows_under(plugin.report.summary(), "Entities") == [
        ("Mobs", "7"),
        ("Dropped items", "1"),
        ("XP orbs", "0"),
        ("Projectiles", "1"),
        ("Vehicles", "0"),
        ("Mobs in Overworld chunk 2, 0 (around 40, 8)", "3"),
        ("Mobs in Overworld chunk 0, 0 (around 8, 8)", "2"),
        ("Mobs in Overworld chunk 0, 2 (around 8, 40)", "1"),
    ]


def test_entity_section_says_when_nothing_is_tracked(plugin, server):
    for section in SECTIONS:
        if section.has_switch:
            plugin.settings.change(section.key, "enabled", False)
    plugin.apply_settings()
    server.spawn_mob("minecraft:zombie")

    assert labels_under(plugin.report.summary(), "Entities") == ["Tracking"]


def test_chunks_are_counted_on_the_timer_and_keep_their_peak(plugin, server):
    overworld = server.overworld
    overworld.loaded_chunks = [Chunk(overworld, x, 0) for x in range(3)]
    assert "Chunks" not in headings(plugin.report.summary())

    server.scheduler.advance(FIRST_SAMPLE_TICKS)
    assert rows_under(plugin.report.summary(), "Chunks") == [
        ("Overworld", "3 loaded, peak 3"),
        ("Nether", "0 loaded, peak 0"),
        ("TheEnd", "0 loaded, peak 0"),
    ]

    overworld.loaded_chunks = overworld.loaded_chunks[:1]
    assert rows_under(plugin.report.summary(), "Chunks")[0] == ("Overworld", "3 loaded, peak 3")

    server.scheduler.advance(plugin.settings.report.chunk_sample_seconds * 20)
    assert rows_under(plugin.report.summary(), "Chunks")[0] == ("Overworld", "1 loaded, peak 3")


def test_a_settings_change_keeps_the_counts_and_follows_the_new_period(plugin, server, switch_on):
    overworld = server.overworld
    overworld.loaded_chunks = [Chunk(overworld, x, 0) for x in range(2)]
    server.scheduler.advance(FIRST_SAMPLE_TICKS)

    switch_on(report__chunk_sample_seconds=10)
    assert rows_under(plugin.report.summary(), "Chunks")[0] == ("Overworld", "2 loaded, peak 2")

    server.scheduler.advance(FIRST_SAMPLE_TICKS)
    overworld.loaded_chunks = [Chunk(overworld, x, 0) for x in range(5)]
    server.scheduler.advance(10 * 20)
    assert rows_under(plugin.report.summary(), "Chunks")[0] == ("Overworld", "5 loaded, peak 5")


def test_properties_are_read_past_comments_and_blank_lines(tmp_path):
    path = tmp_path / "server.properties"
    path.write_text(PROPERTIES, encoding="utf-8")

    assert audit.read_properties(path) == {
        "server-name": "Dedicated Server",
        "view-distance": "32",
        "tick-distance": "4",
        "max-threads": "8",
        "player-idle-timeout": "30",
        "compression-algorithm": "zlib",
        "compression-threshold": "1",
        "client-side-chunk-generation-enabled": "true",
        "level-seed": "",
    }


def test_audit_lists_the_settings_and_what_is_worth_changing(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "read_allowed_cores", lambda: 4.0)
    (tmp_path / "server.properties").write_text(PROPERTIES, encoding="utf-8")

    found = audit.read_audit(tmp_path)
    assert found.path.samefile(tmp_path / "server.properties")
    assert found.settings == [
        ("CPU cores", "4"),
        ("View distance", "32"),
        ("Tick distance", "4"),
        ("Threads", "8"),
        ("Compression", "zlib"),
        ("Compression threshold", "1"),
        ("Client side chunk generation", "true"),
        ("Idle timeout", "30"),
    ]

    advice = dict(found.findings)
    assert list(advice) == ["View distance", "Threads", "Compression threshold"]
    assert advice["View distance"].startswith("view-distance is 32,")
    assert advice["Threads"].startswith("max-threads is 8, above the core count of 4")


def test_audit_carries_on_without_the_file(tmp_path):
    found = audit.read_audit(tmp_path)

    assert found.path is None
    assert found.settings[-1] == ("server.properties", "Not found")
    assert found.findings == []


def test_audit_looks_above_the_plugin_folder(tmp_path, tmp_path_factory, monkeypatch):
    (tmp_path / "server.properties").write_text("view-distance=10\n", encoding="utf-8")
    data_folder = tmp_path / "plugins" / "let_me_perform"
    data_folder.mkdir(parents=True)
    monkeypatch.chdir(tmp_path_factory.mktemp("elsewhere"))

    found = audit.read_audit(data_folder)
    assert ("View distance", "10") in found.settings
    assert found.findings == []


def test_advice_follows_the_thresholds():
    calm = {
        "view-distance": "12",
        "tick-distance": "4",
        "max-threads": "4",
        "player-idle-timeout": "30",
        "compression-threshold": "256",
    }
    assert audit.find_advice(calm, 4.0) == []
    assert audit.find_advice({"view-distance": "far", "max-threads": ""}, 4.0) == []

    advice = dict(audit.find_advice({"tick-distance": "8", "max-threads": "0", "player-idle-timeout": "0"}, 1.5))
    assert list(advice) == ["Tick distance", "Threads", "Idle timeout"]
    assert "289 chunks" in advice["Tick distance"] and "it is 81" in advice["Tick distance"]
    assert "core count of 1.5, so 1 or lower" in advice["Threads"]


def test_allowed_cores_follow_the_container_limit(tmp_path, monkeypatch):
    for name in ("CGROUP_V2_QUOTA", "CGROUP_V1_QUOTA", "CGROUP_V1_PERIOD"):
        monkeypatch.setattr(audit, name, tmp_path / name)
    monkeypatch.setattr(audit.os, "cpu_count", lambda: 16)
    assert audit.read_allowed_cores() == 16.0

    audit.CGROUP_V1_QUOTA.write_text("-1\n", encoding="utf-8")
    audit.CGROUP_V1_PERIOD.write_text("100000\n", encoding="utf-8")
    assert audit.read_allowed_cores() == 16.0

    audit.CGROUP_V1_QUOTA.write_text("400000\n", encoding="utf-8")
    assert audit.read_allowed_cores() == 4.0

    audit.CGROUP_V2_QUOTA.write_text("max 100000\n", encoding="utf-8")
    assert audit.read_allowed_cores() == 4.0

    audit.CGROUP_V2_QUOTA.write_text("150000 100000\n", encoding="utf-8")
    assert audit.read_allowed_cores() == 1.5


def test_boot_audit_logs_each_finding_once(server, tmp_path):
    (tmp_path / "server.properties").write_text("view-distance=32\ncompression-threshold=1\n", encoding="utf-8")
    plugin = enabled_plugin(server, tmp_path)

    logged = audit_warnings(server)
    assert len(logged) == 2
    assert logged[0].startswith("server.properties: view-distance is 32,")

    plugin.apply_settings()
    assert audit_warnings(server) == logged


def test_boot_audit_stays_out_of_the_log_when_switched_off(server, tmp_path):
    (tmp_path / "server.properties").write_text("view-distance=32\n", encoding="utf-8")
    (tmp_path / "config.toml").write_text("[report]\nboot_audit = false\n", encoding="utf-8")
    plugin = enabled_plugin(server, tmp_path)

    assert audit_warnings(server) == []
    assert labels_under(plugin.report.summary(), "Advice") == ["View distance"]


def test_census_counts_by_dimension_type_and_chunk(plugin, server):
    nether = server.level.get_dimension("nether")
    for _ in range(3):
        server.spawn_mob("minecraft:zombie", 5, 64, 5)
    server.spawn_mob("myaddon:robot", 40, 64, 5)
    server.drop("minecraft:dirt", 1, 5, 64, 5, dimension=nether)
    server.drop("minecraft:stone", 1, 5, 64, 5, dimension=nether)
    server.join("Ozz", 5, 64, 5)

    assert plugin.report.census() == [
        ("Loaded entities", [("Nether", "2"), ("Overworld", "5"), ("Total", "7")]),
        ("Most common types", [("zombie", "3"), ("item", "2"), ("myaddon:robot", "1"), ("player", "1")]),
        (
            "Fullest chunks",
            [
                ("Overworld chunk 0, 0 (around 8, 8)", "4, mostly zombie (3)"),
                ("Nether chunk 0, 0 (around 8, 8)", "2, mostly item (2)"),
                ("Overworld chunk 2, 0 (around 40, 8)", "1, mostly myaddon:robot (1)"),
            ],
        ),
    ]


def test_census_stops_at_eight_types_and_five_chunks(plugin, server):
    types_spawned = ("zombie", "husk", "stray", "cow", "pig", "sheep", "bat", "spider", "witch")
    for place, name in enumerate(types_spawned):
        server.spawn_mob(f"minecraft:{name}", place * 16, 64, 0)

    census = dict(plugin.report.census())
    assert len(census["Most common types"]) == 8
    assert len(census["Fullest chunks"]) == 5
    assert census["Loaded entities"][-1] == ("Total", "9")


def test_census_of_an_empty_world_is_one_total(plugin):
    assert plugin.report.census() == [("Loaded entities", [("Total", "0")])]


def test_lag_prints_the_report_to_whoever_asked(plugin, server):
    console = server.command_sender
    plugin.on_command(console, Command("lag"), [])

    assert console.errors == []
    assert console.messages[0] == "§6Timings"
    assert "§7TPS: §f20.0 now, 20.0 on average" in console.messages
    assert "§7Tick budget used: §f20%§f" in console.messages
    assert "§6Entities" in console.messages
    assert "§6Loaded entities" not in console.messages


def test_lag_entities_prints_the_census(plugin, server):
    server.spawn_mob("minecraft:zombie", 5, 64, 5)
    player = server.join("Ozz", 40, 64, 5)
    plugin.on_command(player, Command("lag"), ["Entities"])

    assert player.errors == []
    assert player.messages[0] == "§6Loaded entities"
    assert "§7zombie: §f1" in player.messages
    assert "§7Overworld chunk 2, 0 (around 40, 8): §f1, mostly player (1)" in player.messages
    assert "§6Timings" not in player.messages


def test_tps_answers_everyone_while_it_is_public(plugin, server):
    server.current_tps, server.current_mspt = 18.26, 54.76
    server.average_tps, server.average_mspt = 19.5, 41.04
    player = server.join("Ozz")
    plugin.on_command(player, Command("tps"), [])

    assert player.errors == []
    assert len(player.messages) == 2
    assert player.messages[0].endswith("§7Now: §f18.3 §7TPS, §f54.8 §7ms a tick")
    assert player.messages[1].endswith("§7On average: §f19.5 §7TPS, §f41.0 §7ms a tick")


def test_tps_is_for_staff_once_it_stops_being_public(plugin, server, switch_on):
    switch_on(report__public_tps=False)
    player = server.join("Ozz")
    plugin.on_command(player, Command("tps"), [])
    assert player.messages == []
    assert len(player.errors) == 1

    player.granted.add("lmp.command.lag")
    plugin.on_command(player, Command("tps"), [])
    assert len(player.messages) == 2
    assert len(player.errors) == 1


def test_headline_is_one_line_of_averages(plugin, server):
    server.average_tps, server.average_mspt = 19.96, 12.44
    assert plugin.report.headline() == "§f20.0 §7TPS, §f12.4 §7ms a tick"


def test_cpu_share_is_what_the_thread_used_between_two_readings(tmp_path, monkeypatch):
    stat = tmp_path / "stat"
    clock = [50.0]
    monkeypatch.setattr(metrics, "STAT_PATH", str(stat))
    monkeypatch.setattr(metrics, "CLOCK_TICKS", 100)
    monkeypatch.setattr(metrics.time, "monotonic", lambda: clock[0])

    stat.write_text(stat_line(250, 50), encoding="utf-8")
    cpu = metrics.ThreadCpu()

    clock[0] += 2.0
    stat.write_text(stat_line(330, 70), encoding="utf-8")
    assert cpu.measure() == 50.0

    clock[0] += 1.0
    assert cpu.measure() == 0.0


def test_timings_carry_on_where_proc_does_not_exist(plugin, tmp_path, monkeypatch):
    monkeypatch.setattr(metrics, "STAT_PATH", str(tmp_path / "proc" / "{}" / "stat"))
    assert metrics.read_thread_ticks(4242) is None
    assert metrics.ThreadCpu().measure() is None

    labels = labels_under(plugin.report.summary(), "Timings")
    assert labels[:3] == ["Tick time", "TPS", "Tick budget used"]
    assert "Main thread CPU" not in labels


def test_cpu_share_joins_the_timings_once_it_can_be_read(plugin, tmp_path, monkeypatch):
    stat = tmp_path / "stat"
    clock = [50.0]
    monkeypatch.setattr(metrics, "STAT_PATH", str(stat))
    monkeypatch.setattr(metrics, "CLOCK_TICKS", 100)
    monkeypatch.setattr(metrics.time, "monotonic", lambda: clock[0])

    stat.write_text(stat_line(250, 50), encoding="utf-8")
    plugin.report.cpu = metrics.ThreadCpu()

    clock[0] += 4.0
    stat.write_text(stat_line(340, 60), encoding="utf-8")
    assert rows_under(plugin.report.summary(), "Timings")[3] == ("Main thread CPU", "25%§f since the last reading")


def test_memory_is_shown_only_when_psutil_is_there(plugin, monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", types.SimpleNamespace(Process=FakeProcess))
    assert ("Process memory", "512 MB") in rows_under(plugin.report.summary(), "Timings")

    monkeypatch.setitem(sys.modules, "psutil", None)
    assert "Process memory" not in labels_under(plugin.report.summary(), "Timings")
