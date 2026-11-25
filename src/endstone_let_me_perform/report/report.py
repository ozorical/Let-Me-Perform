from endstone_let_me_perform.core.feature import Feature
from endstone_let_me_perform.core.index import ITEM, MOB, PROJECTILE, VEHICLE, XP
from endstone_let_me_perform.core.messages import describe_chunk, tell, tell_failure, tell_heading, tell_line
from endstone_let_me_perform.report.audit import read_audit
from endstone_let_me_perform.report.census import take_census
from endstone_let_me_perform.report.chunks import ChunkCounts
from endstone_let_me_perform.report.metrics import ThreadCpu, describe_pace, timing_rows
from endstone_let_me_perform.settings import section_named

LAG_PERMISSION = "lmp.command.lag"
TICKS_PER_SECOND = 20
FIRST_SAMPLE_TICKS = 100
BUSIEST_CHUNKS = 3

KIND_LABELS = (
    (MOB, "Mobs"),
    (ITEM, "Dropped items"),
    (XP, "XP orbs"),
    (PROJECTILE, "Projectiles"),
    (VEHICLE, "Vehicles"),
)


class Report(Feature):
    key = "report"

    def __init__(self, plugin):
        super().__init__(plugin)
        self.cpu = ThreadCpu()
        self.chunks = ChunkCounts(self.server)
        self.audit = None
        self.audit_logged = False

    def start(self) -> None:
        self.audit = read_audit(self.plugin.data_folder)
        period = self.options.chunk_sample_seconds * TICKS_PER_SECOND
        self.repeat(self.chunks.sample, period, delay=FIRST_SAMPLE_TICKS)
        if self.audit_logged or not self.options.boot_audit:
            return

        self.audit_logged = True
        if self.audit.path is None:
            self.logger.info("server.properties was not found, so its settings were not checked.")
        for _, finding in self.audit.findings:
            self.logger.warning(f"server.properties: {finding}")

    def lag_command(self, sender, args: list) -> None:
        sections = self.census() if args and args[0].lower() == "entities" else self.summary()
        for heading, rows in sections:
            tell_heading(sender, heading)
            for label, value in rows:
                tell_line(sender, label, value)

    def tps_command(self, sender, args: list) -> None:
        if not self.options.public_tps and not sender.has_permission(LAG_PERMISSION):
            tell_failure(sender, "The tick rate is for staff only on this server.")
            return

        server = self.server
        tell(sender, f"Now: {describe_pace(server.current_tps, server.current_mspt)}")
        tell(sender, f"On average: {describe_pace(server.average_tps, server.average_mspt)}")

    def headline(self) -> str:
        return describe_pace(self.server.average_tps, self.server.average_mspt)

    def summary(self) -> list:
        sections = [
            ("Timings", timing_rows(self.server, self.cpu)),
            ("Chunks", self.chunks.rows()),
            ("Entities", self.entity_rows()),
        ]
        for feature in self.plugin.features:
            if feature is not self and feature.enabled:
                sections.append((section_named(feature.key).title, feature.report()))
        sections.append(("Server settings", self.audit.settings))
        sections.append(("Advice", self.audit.findings))
        return drop_empty(sections)

    def census(self) -> list:
        return drop_empty(take_census(self.server.level))

    def entity_rows(self) -> list:
        index = self.index
        if not index.active:
            return [("Tracking", "Off, because no module that needs it is on")]

        rows = [(label, f"{index.total(kind):,}") for kind, label in KIND_LABELS]
        for chunk, count in index.busiest(MOB, BUSIEST_CHUNKS):
            rows.append((f"Mobs in {describe_chunk(chunk)}", f"{count:,}"))
        return rows


def drop_empty(sections: list) -> list:
    return [(heading, rows) for heading, rows in sections if rows]
