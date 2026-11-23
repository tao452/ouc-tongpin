import math
import unicodedata
from datetime import UTC

from match.models import Profile

EARTH_RADIUS_M = 6_371_008.8


def tags(values):
    return {value for raw in values
            if (value := unicodedata.normalize("NFKC", raw).strip().lower())}


def interest_jaccard(left, right):
    a, b = tags(left), tags(right)
    return len(a & b) / len(a | b) if a | b else 0.0


def intervals(slots):
    merged = []
    for start, end in sorted((slot.start.astimezone(UTC).timestamp(),
                              slot.end.astimezone(UTC).timestamp()) for slot in slots):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def time_jaccard(left, right):
    a, b = intervals(left), intervals(right)
    total = sum(end - start for start, end in [*a, *b])
    i, j, overlap = 0, 0, 0.0
    while i < len(a) and j < len(b):
        overlap += max(0, min(a[i][1], b[j][1]) - max(a[i][0], b[j][0]))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return overlap / (total - overlap) if total > overlap else 0.0


def distance_m(left, right):
    lat1, lat2 = math.radians(left.lat), math.radians(right.lat)
    dlat, dlng = lat2 - lat1, math.radians(right.lng - left.lng)
    square = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(min(1, max(0, square))))


def features(left: Profile, right: Profile, scale_m=5000.0):
    a, b = left.emotion_vector, right.emotion_vector
    norm_a = math.sqrt(sum(v * v for v in a)) if a else 0.0
    norm_b = math.sqrt(sum(v * v for v in b)) if b else 0.0
    has_emotion = norm_a > 0 and norm_b > 0
    similarity = min(1, max(0, sum(x * y for x, y in zip(a, b, strict=True))
                            / (norm_a * norm_b))) if has_emotion else 0.0
    has_distance = left.location is not None and right.location is not None
    meters = distance_m(left.location, right.location) if has_distance else None
    return {
        "emotion_similarity": similarity,
        # Mathematical dissimilarity only; business "comfort/complement" semantics await M1.
        "emotion_complement": 1 - similarity if has_emotion else 0.0,
        "interest_jaccard": interest_jaccard(left.interests, right.interests),
        "time_jaccard": time_jaccard(left.availability, right.availability),
        "distance_decay": math.exp(-meters / scale_m) if meters is not None else 0.0,
        "distance_m": meters,
        "available": {"emotion": has_emotion, "interests": bool(tags(left.interests)
                                                                  and tags(right.interests)),
                      "time": bool(left.availability and right.availability),
                      "distance": has_distance},
    }
