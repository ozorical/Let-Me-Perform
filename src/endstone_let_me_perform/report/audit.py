import os
from pathlib import Path

FILE_NAME = "server.properties"
SEARCH_DEPTH = 5

CGROUP_V2_QUOTA = Path("/sys/fs/cgroup/cpu.max")
CGROUP_V1_QUOTA = Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
CGROUP_V1_PERIOD = Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us")

VIEW_DISTANCE_CEILING = 12
TICK_DISTANCE_CEILING = 4
COMPRESSION_THRESHOLD_FLOOR = 256

SHOWN_SETTINGS = {
    "view-distance": "View distance",
    "tick-distance": "Tick distance",
    "max-threads": "Threads",
    "compression-algorithm": "Compression",
    "compression-threshold": "Compression threshold",
    "client-side-chunk-generation-enabled": "Client side chunk generation",
    "player-idle-timeout": "Idle timeout",
}


class Audit:
    __slots__ = ("path", "settings", "findings")

    def __init__(self, path, settings: list, findings: list):
        self.path = path
        self.settings = settings
        self.findings = findings


def read_audit(data_folder) -> Audit:
    cores = read_allowed_cores()
    settings = [("CPU cores", f"{cores:g}")]

    path = find_properties(data_folder)
    if path is None:
        settings.append((FILE_NAME, "Not found"))
        return Audit(None, settings, [])

    values = read_properties(path)
    settings.extend((label, values[key]) for key, label in SHOWN_SETTINGS.items() if values.get(key))
    return Audit(path, settings, find_advice(values, cores))


def read_allowed_cores() -> float:
    return read_cgroup_v2_cores() or read_cgroup_v1_cores() or float(os.cpu_count() or 1)


def read_cgroup_v2_cores():
    try:
        quota, period = CGROUP_V2_QUOTA.read_text().split()
        return int(quota) / int(period)
    except (OSError, ValueError):
        return None


def read_cgroup_v1_cores():
    try:
        quota = int(CGROUP_V1_QUOTA.read_text())
        period = int(CGROUP_V1_PERIOD.read_text())
    except (OSError, ValueError):
        return None
    return quota / period if quota > 0 and period > 0 else None


def find_properties(data_folder):
    for root in (Path.cwd(), Path(data_folder).resolve()):
        for folder in (root, *root.parents[: SEARCH_DEPTH - 1]):
            candidate = folder / FILE_NAME
            if candidate.is_file():
                return candidate
    return None


def read_properties(path: Path) -> dict:
    values = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, separator, value = line.partition("=")
        if separator and not key.lstrip().startswith("#"):
            values[key.strip()] = value.strip()
    return values


def find_advice(values: dict, cores: float) -> list:
    advice = {}

    view = read_whole(values, "view-distance")
    if view is not None and view > VIEW_DISTANCE_CEILING:
        advice["view-distance"] = (
            f"view-distance is {view}, so every player can hold chunks loaded up to {view} chunks away. "
            f"{VIEW_DISTANCE_CEILING} or lower is the usual ceiling for a busy server."
        )

    tick = read_whole(values, "tick-distance")
    if tick is not None and tick > TICK_DISTANCE_CEILING:
        advice["tick-distance"] = (
            f"tick-distance is {tick}, which ticks {ticked_chunks(tick)} chunks around every player. "
            f"At {TICK_DISTANCE_CEILING} it is {ticked_chunks(TICK_DISTANCE_CEILING)}."
        )

    threads = read_whole(values, "max-threads")
    fitting = max(1, int(cores))
    if threads == 0:
        advice["max-threads"] = (
            "max-threads is 0, which lets the server start as many threads as it likes. "
            f"This process has a core count of {cores:g}, so {fitting} or lower stops the threads competing."
        )
    elif threads is not None and threads > cores:
        advice["max-threads"] = (
            f"max-threads is {threads}, above the core count of {cores:g} this process may use. "
            f"{fitting} or lower stops the threads competing."
        )

    if read_whole(values, "player-idle-timeout") == 0:
        advice["player-idle-timeout"] = (
            "player-idle-timeout is 0, so idle players are never kicked and the chunks around them stay loaded. "
            "A timeout in minutes, or the AFK move module, lets those chunks unload."
        )

    threshold = read_whole(values, "compression-threshold")
    if threshold is not None and threshold < COMPRESSION_THRESHOLD_FLOOR:
        advice["compression-threshold"] = (
            f"compression-threshold is {threshold}, so even the smallest packets are compressed. "
            f"{COMPRESSION_THRESHOLD_FLOOR} saves CPU time for almost no extra bandwidth."
        )

    return [(SHOWN_SETTINGS[key], sentence) for key, sentence in advice.items()]


def ticked_chunks(distance: int) -> int:
    return (2 * distance + 1) ** 2


def read_whole(values: dict, key: str):
    try:
        return int(values[key])
    except (KeyError, ValueError):
        return None
