from collections import Counter, defaultdict

from endstone_let_me_perform.core.index import chunk_of
from endstone_let_me_perform.core.messages import describe_chunk

COMMON_TYPES = 8
FULLEST_CHUNKS = 5


def take_census(level) -> list:
    by_dimension = Counter()
    by_type = Counter()
    by_chunk = defaultdict(Counter)
    for actor in level.actors:
        try:
            type_id = actor.type.removeprefix("minecraft:")
        except Exception:
            continue

        chunk = chunk_of(actor)
        if chunk is None:
            continue

        by_dimension[chunk[0]] += 1
        by_type[type_id] += 1
        by_chunk[chunk][type_id] += 1

    loaded = [(dimension, f"{count:,}") for dimension, count in sorted(by_dimension.items())]
    loaded.append(("Total", f"{by_type.total():,}"))

    common = [(type_id, f"{count:,}") for type_id, count in by_type.most_common(COMMON_TYPES)]

    fullest = []
    for chunk, types in sorted(by_chunk.items(), key=lambda pair: pair[1].total(), reverse=True)[:FULLEST_CHUNKS]:
        type_id, count = types.most_common(1)[0]
        fullest.append((describe_chunk(chunk), f"{types.total():,}, mostly {type_id} ({count:,})"))

    return [("Loaded entities", loaded), ("Most common types", common), ("Fullest chunks", fullest)]
