#!/usr/bin/env python3
"""Yahoo! Movies multi-criteria ratings (story, acting, direction, visuals and
overall, 1-13 grades): how much the aspects say beyond the overall grade, and
whether people differ in which aspect drives their overall grade. Own-user
analysis only.

    python3 -I tools/review/eval_yahoo_aspects.py PATH/data_movies.txt

The data is NOT in this repository: the public copies found (GitHub:
KunalShm/Multi-Criteria-Recommendation-System data_movies.txt,
sydney-machine-learning/multicriteria-recommendersys Movies_Yahoo.xlsx) state no
licence, and movie ids are opaque (cannot be joined to cast or directors), so
only private, aggregate checks are run. Columns of data_movies.txt: user,
story, acting, direction, visuals, overall, movie, row.
"""
import random, statistics, sys
from collections import defaultdict
import numpy as np

path = sys.argv[1]
rows = []
for line in open(path):
    if not line.strip():
        continue
    p = line.split("\t")
    u, c, o, m = p[0], list(map(int, p[1:5])), int(p[5]), p[6]
    rows.append((u, m, c, o))
NAMES = ["story", "acting", "direction", "visuals"]
print("ratings", len(rows), "users", len({r[0] for r in rows}), "movies", len({r[1] for r in rows}))

# 1. Aspects vs overall, per rating.
dev = [max(abs(x - o) for x in c) for _, _, c, o in rows]
spread = [max(c) - min(c) for _, _, c, o in rows]
print("share with an aspect >= 3 grades (one letter) away from overall:", round(sum(d >= 3 for d in dev) / len(dev), 3))
print("share with aspects spread >= 3 grades:", round(sum(s >= 3 for s in spread) / len(spread), 3))
print("share overall == round(mean aspects):", round(sum(o == round(sum(c) / 4) for _, _, c, o in rows) / len(rows), 3))
# 3-state marks as the 詳細 would record them: aspect >= overall+3 good, <= overall-3 trouble
marked = [sum(abs(x - o) >= 3 for x in c) for _, _, c, o in rows]
print("ratings with at least one mark (good or trouble):", round(sum(m > 0 for m in marked) / len(marked), 3))
both = sum(any(x - o >= 3 for x in c) and any(o - x >= 3 for x in c) for _, _, c, o in rows)
print("ratings with both a good and a trouble mark:", round(both / len(rows), 3))

# 2. Which aspect drives each user's overall grade (users with >= 30 ratings).
by_user = defaultdict(list)
for u, m, c, o in rows:
    by_user[u].append((c, o))
lead = defaultdict(int); r2s = []; n_users = 0; heldout = {"mean": [], "own": []}
rng = random.Random(1)
for u, rs in by_user.items():
    if len(rs) < 30:
        continue
    X = np.array([[1] + c for c, _ in rs], float); y = np.array([o for _, o in rs], float)
    if np.linalg.matrix_rank(X) < 5:
        continue
    n_users += 1
    w, *_ = np.linalg.lstsq(X, y, rcond=None)
    lead[NAMES[int(np.argmax(w[1:]))]] += 1
    pred = X @ w; r2s.append(1 - ((y - pred) ** 2).sum() / max(((y - y.mean()) ** 2).sum(), 1e-9))
    # held-out: does the user's own aspect weighting predict their overall better than the plain mean?
    idx = list(range(len(rs))); rng.shuffle(idx); tr, te = idx[: len(idx) * 2 // 3], idx[len(idx) * 2 // 3:]
    w2, *_ = np.linalg.lstsq(X[tr], y[tr], rcond=None)
    heldout["own"].append(np.abs(X[te] @ w2 - y[te]).mean())
    heldout["mean"].append(np.abs(X[te][:, 1:].mean(1) - y[te]).mean())
print("users with >= 30 ratings:", n_users)
print("aspect with the largest weight per user:", {k: round(v / n_users, 3) for k, v in sorted(lead.items())})
print("median R2 of overall from aspects (own weights):", round(statistics.median(r2s), 3))
d = [a - b for a, b in zip(heldout["mean"], heldout["own"])]
print("held-out mean abs error: plain mean of aspects", round(statistics.fmean(heldout["mean"]), 3),
      "own weights", round(statistics.fmean(heldout["own"]), 3),
      "users better with own weights", round(sum(x > 0 for x in d) / len(d), 3))
