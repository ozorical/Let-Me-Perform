class ChunkCounts:
    def __init__(self, server):
        self.server = server
        self.latest = {}
        self.peak = {}

    def sample(self) -> None:
        for dimension in self.server.level.dimensions:
            name = dimension.name
            loaded = len(dimension.loaded_chunks)
            self.latest[name] = loaded
            self.peak[name] = max(loaded, self.peak.get(name, 0))

    def rows(self) -> list:
        return [(name, f"{loaded:,} loaded, peak {self.peak[name]:,}") for name, loaded in self.latest.items()]
