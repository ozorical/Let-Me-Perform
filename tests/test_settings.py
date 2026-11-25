import tomlkit

from endstone_let_me_perform.settings import SECTIONS, Settings, read_value, section_named


def test_defaults_follow_the_safe_start():
    settings = Settings()
    on = [section.key for section in SECTIONS if section.has_switch and settings.section(section.key).enabled]
    assert on == ["projectile_cap", "item_merge", "piston_guard", "tnt_guard"]


def test_every_default_passes_its_own_check():
    for section in SECTIONS:
        for option in section.options:
            default = list(option.default) if isinstance(option.default, tuple) else option.default
            assert read_value(option, option.default, None) == default


def test_numbers_are_clamped_and_junk_falls_back():
    option = section_named("mob_cap").option("per_chunk")
    assert read_value(option, 99999, 30) == 200
    assert read_value(option, -4, 30) == 5
    assert read_value(option, "45", 30) == 45
    assert read_value(option, "plenty", 30) == 30
    assert read_value(option, True, 30) == 30


def test_choice_and_listing_are_cleaned():
    dimension = section_named("afk").option("dimension")
    assert read_value(dimension, "The_End", "overworld") == "the_end"
    assert read_value(dimension, "moon", "overworld") == "overworld"

    protected = section_named("general").option("protected_types")
    assert read_value(protected, " Minecraft:Cow, minecraft:pig ,, minecraft:cow", []) == ["minecraft:cow", "minecraft:pig"]


def test_apply_from_counts_what_the_file_left_out():
    settings = Settings()
    missing = settings.apply_from({"mob_cap": {"enabled": True, "per_chunk": 40}})
    total = sum(len(section.options) for section in SECTIONS)
    assert missing == total - 2
    assert settings.mob_cap.enabled is True
    assert settings.mob_cap.per_chunk == 40


def test_settings_survive_a_round_trip_through_toml():
    settings = Settings()
    settings.change("lag_clear", "interval_minutes", 45)
    settings.change("afk", "dimension", "nether")
    settings.change("general", "protected_types", ["minecraft:cow"])

    document = tomlkit.document()
    settings.write_into(document)
    loaded = Settings()
    assert loaded.apply_from(tomlkit.parse(tomlkit.dumps(document))) == 0
    assert loaded.lag_clear.interval_minutes == 45
    assert loaded.afk.dimension == "nether"
    assert loaded.general.protected_types == ["minecraft:cow"]


def test_a_bad_change_keeps_the_value_it_had():
    settings = Settings()
    settings.change("afk", "x", 500)
    settings.change("afk", "x", "over there")
    assert settings.afk.x == 500


def test_reset_puts_a_section_back():
    settings = Settings()
    settings.change("tnt_guard", "chain_limit", 3)
    assert not settings.is_default("tnt_guard")
    settings.reset("tnt_guard")
    assert settings.is_default("tnt_guard")


def test_plugin_writes_a_full_config_on_first_start(plugin, tmp_path):
    written = tomlkit.parse((tmp_path / "config.toml").read_text(encoding="utf-8")).unwrap()
    assert set(written) == {section.key for section in SECTIONS}
    assert written["mob_cap"] == {"enabled": False, "per_chunk": 30}


def test_reload_picks_up_an_edited_file(plugin, tmp_path):
    path = tmp_path / "config.toml"
    document = tomlkit.parse(path.read_text(encoding="utf-8"))
    document["piston_guard"]["suspend_seconds"] = 90
    path.write_text(tomlkit.dumps(document), encoding="utf-8")

    assert plugin.reload_settings()
    assert plugin.settings.piston_guard.suspend_seconds == 90
