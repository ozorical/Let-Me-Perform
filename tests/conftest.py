import fake_endstone

fake_endstone.install()

import pytest

from endstone_let_me_perform import LetMePerform


@pytest.fixture
def server():
    return fake_endstone.Server()


@pytest.fixture
def plugin(server, tmp_path):
    created = LetMePerform()
    created.attach(server, tmp_path)
    created.on_enable()
    return created


@pytest.fixture
def switch_on(plugin):
    def turn(*keys, **changes):
        for key in keys:
            plugin.settings.change(key, "enabled", True)
        for path, value in changes.items():
            section, option = path.split("__")
            plugin.settings.change(section, option, value)
        plugin.apply_settings()

    return turn
