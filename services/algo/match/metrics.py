"""Linear-gain, tie-averaged NDCG; all-zero queries stay in the aggregate."""

import math


def ndcg(relevance, scores, k=10):
    if (not relevance or len(relevance) != len(scores) or type(k) is not int or k < 1
            or any(not math.isfinite(v) or v < 0 for v in relevance)
            or any(not math.isfinite(v) for v in scores)):
        raise ValueError("Invalid ranking vectors or cutoff")
    n = len(scores)
    discounts = [1 / math.log2(i + 2) for i in range(min(k, n))]
    ideal = sum(v * d for v, d in zip(sorted(relevance, reverse=True), discounts, strict=False))
    if ideal == 0:
        return 0.0
    order = sorted(range(n), key=lambda i: -scores[i])
    start, gain = 0, 0.0
    while start < min(k, n):
        end = start + 1
        while end < n and scores[order[end]] == scores[order[start]]:
            end += 1
        mean_relevance = sum(relevance[order[i]] for i in range(start, end)) / (end - start)
        gain += mean_relevance * sum(discounts[start:min(end, k)])
        start = end
    return min(1.0, max(0.0, gain / ideal))
