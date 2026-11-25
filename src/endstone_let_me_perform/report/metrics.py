import os
import threading
import time

CLOCK_TICKS = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
STAT_PATH = "/proc/self/task/{}/stat"
BYTES_IN_MB = 1024 * 1024


def timing_rows(server, cpu) -> list:
    rows = [
        ("Tick time", f"{server.current_mspt:.1f} ms now, {server.average_mspt:.1f} ms on average"),
        ("TPS", f"{server.current_tps:.1f} now, {server.average_tps:.1f} on average"),
        ("Tick budget used", f"{server.average_tick_usage * 100:.0f}%§f"),
    ]

    share = cpu.measure()
    if share is not None:
        rows.append(("Main thread CPU", f"{share:.0f}%§f since the last reading"))

    memory = read_memory_mb()
    if memory is not None:
        rows.append(("Process memory", f"{memory:,.0f} MB"))
    return rows


def describe_pace(tps: float, mspt: float) -> str:
    return f"§f{tps:.1f} §7TPS, §f{mspt:.1f} §7ms a tick"


class ThreadCpu:
    __slots__ = ("thread_id", "ticks", "read_at")

    def __init__(self):
        self.thread_id = threading.get_native_id()
        self.ticks = read_thread_ticks(self.thread_id)
        self.read_at = time.monotonic()

    def measure(self):
        ticks = read_thread_ticks(self.thread_id)
        if ticks is None:
            return None

        now = time.monotonic()
        before, since = self.ticks, self.read_at
        self.ticks, self.read_at = ticks, now
        if before is None or now <= since:
            return None
        return min(100.0, (ticks - before) / CLOCK_TICKS / (now - since) * 100.0)


def read_thread_ticks(thread_id: int):
    try:
        with open(STAT_PATH.format(thread_id)) as stat:
            fields = stat.read().rpartition(")")[2].split()
        return int(fields[11]) + int(fields[12])
    except (OSError, IndexError, ValueError):
        return None


def read_memory_mb():
    try:
        import psutil
    except ImportError:
        return None
    return psutil.Process().memory_info().rss / BYTES_IN_MB
