from endstone_let_me_perform.core.budget import Budget


class Feature:
    key = ""
    uses_index = False

    def __init__(self, plugin):
        self.plugin = plugin
        self.server = plugin.server
        self.logger = plugin.logger
        self.index = plugin.index
        self.options = plugin.settings.section(self.key)
        self._tasks = []

    @property
    def enabled(self) -> bool:
        return bool(getattr(self.options, "enabled", True))

    def start(self) -> None:
        return

    def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    def repeat(self, run, ticks: int, delay: int = 0):
        ticks = max(1, int(ticks))
        task = self.server.scheduler.run_task(self.plugin, run, delay=delay or ticks, period=ticks)
        if task is not None:
            self._tasks.append(task)
        return task

    def later(self, run, ticks: int):
        return self.server.scheduler.run_task(self.plugin, run, delay=max(1, int(ticks)))

    def budget(self) -> Budget:
        return Budget(self.plugin.settings.general.sweep_budget_ms)

    def report(self) -> list:
        return []
