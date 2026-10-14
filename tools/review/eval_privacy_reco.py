#!/usr/bin/env python3
"""Privacy-compatible recommender experiments on Douban Movie (public data).

    python3 -I exp_privacy_reco.py --data DIR --extra DIR --seed 1 [--users 500] [--train-users 1000]

Constraint mirrored from たぐり: at prediction time a method uses ONLY the
evaluated user's own first k ratings. Shared parameters (meta-learned weights,
public priors, embeddings) are fit ONLY on a disjoint set of public users
(train users), never on the evaluated users.

Protocol = eval_person_reco.learning_curve: per user and shuffle, the last 40
ratings are a fixed test set, k = 5,10,20,40,80 earlier ratings are usable,
AUC of the user's top grade among the test (evaluate_one, unscored = 0).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, sys.argv[sys.argv.index("--repo") + 1] if "--repo" in sys.argv else ".")
import eval_person_reco as E  # noqa: E402

KS = (5, 10, 20, 40, 80)
TEST = 40
SHRINK = 3.0
ROLE_W = {"actor": 1.0, "director": 0.4}


# ----------------------------------------------------------------- data
def load_types(extra: Path):
    types = defaultdict(list)
    for line in (extra / "movie_type.dat").read_text().split("\n"):
        if line.strip():
            m, t, _ = line.split()
            types[m].append(t)
    return types


# ----------------------------------------------------------------- per-user stats (own data only)
class Stats:
    """Everything a method may know about the user: their own k ratings."""

    def __init__(self, history, people, types):
        self.k = len(history)
        rs = [r for _, r in history]
        self.mean = statistics.fmean(rs)
        sd = statistics.pstdev(rs) if len(rs) > 1 else 0.0
        self.sd = sd if sd > 0 else 1.0
        self.z = {m: (r - self.mean) / self.sd for m, r in history}
        self.top = max(rs)
        self.per = defaultdict(lambda: [0, 0.0])
        self.gen = defaultdict(lambda: [0, 0.0])
        for m, r in history:
            z = self.z[m]
            for rp in set(people.get(m, ())):
                self.per[rp][0] += 1
                self.per[rp][1] += z
            for g in set(types.get(m, ())):
                self.gen[g][0] += 1
                self.gen[g][1] += z


def role_parts(st, m, people, role, excl_z=None):
    parts = []
    for ro, p in set(people.get(m, ())):
        if ro != role or (ro, p) not in st.per:
            continue
        n, s = st.per[(ro, p)]
        if excl_z is not None:
            n, s = n - 1, s - excl_z
        if n <= 0:
            continue
        parts.append(s / (n + SHRINK))
    pos = sorted((x for x in parts if x > 0), reverse=True)[:3]
    neg = sorted(x for x in parts if x < 0)[:3]
    return sum(pos) + sum(neg), len(parts)


def genre_part(st, m, types, excl_z=None):
    gs = set(types.get(m, ()))
    if not gs:
        return 0.0, 0.0, 0
    vals, fam, known = [], [], 0
    for g in gs:
        n, s = st.gen.get(g, (0, 0.0))
        if excl_z is not None and n:
            n, s = n - 1, s - excl_z
        vals.append(s / (n + SHRINK) if n > 0 else 0.0)
        fam.append(n / max(st.k - (excl_z is not None), 1))
        known += n > 0
    return statistics.fmean(vals), statistics.fmean(fam), known


FEATS = ["act", "dir", "has_person", "log_pairs", "genre", "genre_fam",
         "act_x_k", "dir_x_k", "genre_x_k", "fam_x_k",
         "genre_prior", "n_credits", "creator_prior"]
GROUPS = {
    "P": ["act", "dir", "has_person", "log_pairs", "act_x_k", "dir_x_k"],
    "G": ["genre", "genre_fam", "genre_x_k", "fam_x_k"],
    "GP": ["genre_prior"],          # public population prior per genre (fixed parameter)
    "META": ["n_credits"],          # number of listed credits (catalogue size proxy)
    "CR": ["creator_prior"],        # public track record of the creators, target excluded
}


def features(st, m, people, types, pub, excl_z=None):
    a, na = role_parts(st, m, people, "actor", excl_z)
    d, nd = role_parts(st, m, people, "director", excl_z)
    g, fam, _ = genre_part(st, m, types, excl_z)
    lk = math.log(max(st.k, 2)) / math.log(80)
    gp = [pub["genre"].get(t, 0.0) for t in set(types.get(m, ()))]
    return [a, d, float(na + nd > 0), math.log1p(na + nd), g, fam,
            a * lk, d * lk, g * lk, fam * lk,
            statistics.fmean(gp) if gp else 0.0,
            math.log1p(len(people.get(m, ()))),
            pub["creator"](m)]


# ----------------------------------------------------------------- public (train-user) priors
def public_priors(ratings, people, types, train_users):
    """Fixed parameters learned on public train users only."""
    zr = {}
    for u in train_users:
        rs = list(ratings[u].values())
        mu, sd = statistics.fmean(rs), statistics.pstdev(rs) or 1.0
        zr[u] = {m: (r - mu) / sd for m, r in ratings[u].items()}
    gsum = defaultdict(lambda: [0.0, 0])
    msum = defaultdict(lambda: [0.0, 0])
    for u, d in zr.items():
        for m, z in d.items():
            msum[m][0] += z
            msum[m][1] += 1
            for g in set(types.get(m, ())):
                gsum[g][0] += z
                gsum[g][1] += 1
    genre = {g: s / (n + 20) for g, (s, n) in gsum.items()}
    # movie means (shrunk) -> per-person sums, so the target movie can be left out
    mmean = {m: s / (n + 5) for m, (s, n) in msum.items()}
    psum = defaultdict(lambda: [0.0, 0])
    for m, plist in people.items():
        if m in mmean:
            for rp in set(plist):
                psum[rp][0] += mmean[m]
                psum[rp][1] += 1

    def creator(m):
        own = mmean.get(m)
        vals = []
        for rp in set(people.get(m, ())):
            s, n = psum.get(rp, (0.0, 0))
            if own is not None:
                s, n = s - own, n - 1     # leave the target movie itself out
            if n > 0:
                vals.append(s / (n + 2))
        return statistics.fmean(vals) if vals else 0.0
    return {"genre": genre, "creator": creator, "zr": zr, "mmean": mmean}


def content_embeddings(ratings, people, types, train_users, zr, dim=24, seed=0):
    """Two-tower style item tower: CF item factors learned on public train users
    (truncated SVD of the user-z matrix), then a CONTENT embedding per movie =
    mean factor of its persons' OTHER movies + its genres' movies. A new
    (never-rated) show gets an embedding from its credits alone."""
    movies = sorted({m for u in train_users for m in ratings[u]})
    idx = {m: i for i, m in enumerate(movies)}
    M = np.zeros((len(train_users), len(movies)), dtype=np.float32)
    for i, u in enumerate(train_users):
        for m, z in zr[u].items():
            M[i, idx[m]] = z
    # randomized truncated SVD
    rng = np.random.default_rng(seed)
    Q = rng.standard_normal((len(movies), dim + 10)).astype(np.float32)
    Y = M @ Q
    for _ in range(3):
        Y, _ = np.linalg.qr(Y)
        Y = M @ (M.T @ Y)
    Qy, _ = np.linalg.qr(Y)
    B = Qy.T @ M
    _, S, Vt = np.linalg.svd(B, full_matrices=False)
    V = (Vt[:dim].T * np.sqrt(S[:dim])).astype(np.float64)    # movie factors
    V /= (np.linalg.norm(V, axis=1, keepdims=True).mean() + 1e-9)
    psum = defaultdict(lambda: [np.zeros(dim), 0])
    gsum = defaultdict(lambda: [np.zeros(dim), 0])
    for m, i in idx.items():
        for rp in set(people.get(m, ())):
            psum[rp][0] = psum[rp][0] + V[i]
            psum[rp][1] += 1
        for g in set(types.get(m, ())):
            gsum[g][0] = gsum[g][0] + V[i]
            gsum[g][1] += 1
    cache = {}

    def emb(m):
        if m in cache:
            return cache[m]
        own = V[idx[m]] if m in idx else None
        vs = []
        for rp in set(people.get(m, ())):
            s, n = psum.get(rp, (None, 0))
            if s is None:
                continue
            if own is not None:
                s, n = s - own, n - 1
            if n > 0:
                vs.append(s / n)
        gv = []
        for g in set(types.get(m, ())):
            s, n = gsum.get(g, (None, 0))
            if s is None:
                continue
            if own is not None:
                s, n = s - own, n - 1
            if n > 0:
                gv.append(s / n)
        e = np.zeros(dim)
        if vs:
            e += np.mean(vs, axis=0)
        if gv:
            e += 0.5 * np.mean(gv, axis=0)
        cache[m] = e
        return e
    return emb


# ----------------------------------------------------------------- learners (numpy)
def ridge(X, y, lam, w0=None):
    d = X.shape[1]
    w0 = np.zeros(d) if w0 is None else w0
    A = X.T @ X + lam * np.eye(d)
    return np.linalg.solve(A, X.T @ (y - X @ w0)) + w0


class Std:
    def __init__(self, X):
        self.mu = X.mean(0)
        self.sd = X.std(0) + 1e-9

    def __call__(self, X):
        return (X - self.mu) / self.sd


def mlp_train(X, y, hidden=32, epochs=8, lr=3e-3, seed=0, wd=1e-4):
    rng = np.random.default_rng(seed)
    d = X.shape[1]
    W1 = rng.standard_normal((d, hidden)) * (1 / math.sqrt(d))
    b1 = np.zeros(hidden)
    W2 = rng.standard_normal(hidden) * (1 / math.sqrt(hidden))
    b2 = 0.0
    params = [W1, b1, W2, np.array([b2])]
    m_ = [np.zeros_like(p) for p in params]
    v_ = [np.zeros_like(p) for p in params]
    t = 0
    n = len(y)
    for _ in range(epochs):
        perm = rng.permutation(n)
        for s in range(0, n, 512):
            b = perm[s:s + 512]
            xb, yb = X[b], y[b]
            h = np.tanh(xb @ params[0] + params[1])
            out = h @ params[2] + params[3][0]
            g = 2 * (out - yb) / len(b)
            gW2 = h.T @ g
            gb2 = np.array([g.sum()])
            gh = np.outer(g, params[2]) * (1 - h ** 2)
            gW1 = xb.T @ gh
            gb1 = gh.sum(0)
            grads = [gW1 + wd * params[0], gb1, gW2 + wd * params[2], gb2]
            t += 1
            for i, (p, gr) in enumerate(zip(params, grads)):
                m_[i] = 0.9 * m_[i] + 0.1 * gr
                v_[i] = 0.999 * v_[i] + 0.001 * gr ** 2
                p -= lr * (m_[i] / (1 - 0.9 ** t)) / (np.sqrt(v_[i] / (1 - 0.999 ** t)) + 1e-8)

    def f(Xq):
        return np.tanh(Xq @ params[0] + params[1]) @ params[2] + params[3][0]
    return f


# ----------------------------------------------------------------- experiment
def splits(items, seed, u, s):
    rng = random.Random(f"lc:{seed}:{u}:{s}")
    order = items[:]
    rng.shuffle(order)
    return order[-TEST:], order[:-TEST]


def build_train(ratings, people, types, pub, train_users, seed):
    """Rows: (features of a test movie given k history ratings, z target)."""
    X, Y, K = [], [], []
    for u in train_users:
        items = sorted(ratings[u].items())
        test, train = splits(items, f"tr{seed}", u, 0)
        for k in KS:
            st = Stats(train[:k], people, types)
            for m, r in test:
                X.append(features(st, m, people, types, pub))
                Y.append((r - st.mean) / st.sd)
                K.append(k)
    return np.array(X), np.array(Y), np.array(K)


def cols(names):
    return [FEATS.index(c) for c in names]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--extra", type=Path, required=True)
    ap.add_argument("--repo")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--users", type=int, default=500)
    ap.add_argument("--train-users", type=int, default=1000)
    ap.add_argument("--emb-users", type=int, default=3000)
    ap.add_argument("--shuffles", type=int, default=3)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    t0 = time.time()
    ratings, people = E.load(a.data)
    types = load_types(a.extra)
    eligible = sorted(u for u, rs in ratings.items() if len(rs) >= 100)
    # same evaluation users as eval_person_reco (seed sample of 500, >=120 used)
    eval_users = random.Random(a.seed).sample(eligible, min(a.users, len(eligible)))
    eval_users = [u for u in eval_users if len(ratings[u]) >= max(KS) + TEST]
    rest = sorted(set(ratings) - set(eval_users))
    rest_elig = [u for u in rest if len(ratings[u]) >= max(KS) + TEST]
    rng = random.Random(f"train:{a.seed}")
    train_users = rng.sample(rest_elig, min(a.train_users, len(rest_elig)))
    # public priors use many public (non-eval) users
    pub_users = rng.sample(rest, min(a.emb_users, len(rest)))
    pub = public_priors(ratings, people, types, pub_users)
    emb = content_embeddings(ratings, people, types, pub_users, pub["zr"], seed=a.seed)
    print(f"[{time.time()-t0:.0f}s] eval={len(eval_users)} train={len(train_users)} pub={len(pub_users)}", file=sys.stderr)

    X, Y, K = build_train(ratings, people, types, pub, train_users, a.seed)
    print(f"[{time.time()-t0:.0f}s] train rows {len(Y)}", file=sys.stderr)
    models = {}
    variants = {
        "meta_P": GROUPS["P"],
        "meta_PG": GROUPS["P"] + GROUPS["G"],
        "meta_PG_GP": GROUPS["P"] + GROUPS["G"] + GROUPS["GP"],
        "meta_PG_GP_META": GROUPS["P"] + GROUPS["G"] + GROUPS["GP"] + GROUPS["META"],
        "meta_PG_CR": GROUPS["P"] + GROUPS["G"] + GROUPS["GP"] + GROUPS["CR"],
    }
    for name, cs in variants.items():
        c = cols(cs)
        Xc = X[:, c]
        Xa = np.hstack([Xc, np.ones((len(Xc), 1))])
        w = ridge(Xa, Y, 1.0)
        models[name] = (c, w)
    # (d) small MLP on personal features (P+G+GP)
    cm = cols(variants["meta_PG_GP"])
    stdz = Std(X[:, cm])
    mlp = mlp_train(stdz(X[:, cm]), Y, seed=a.seed)
    # (c) shrinkage strength: tune on train users (a second shuffle) over a grid
    c_sh = cols(GROUPS["P"][:4] + GROUPS["G"][:2] + ["genre_prior"])  # no k-interactions per user
    Xs = np.hstack([X[:, c_sh], np.ones((len(Y), 1))])
    w0_sh = ridge(Xs, Y, 1.0)

    def per_user_fit(st, hist, lam):
        if lam == float("inf"):
            return w0_sh
        F = np.array([[features(st, m, people, types, pub, excl_z=st.z[m])[i] for i in c_sh] + [1.0] for m, _ in hist])
        z = np.array([st.z[m] for m, _ in hist])
        return ridge(F, z, lam, w0_sh)

    def tune_lambda():
        res = {}
        for lam in (3.0, 10.0, 30.0, 100.0, float("inf")):
            aucs = []
            for u in train_users[:300]:
                items = sorted(ratings[u].items())
                test, train = splits(items, f"tune{a.seed}", u, 1)
                for k in (10, 40, 80):
                    hist = train[:k]
                    st = Stats(hist, people, types)
                    w = per_user_fit(st, hist, lam)
                    sc = {m: float(np.dot([features(st, m, people, types, pub)[i] for i in c_sh] + [1.0], w)) for m, _ in test}
                    r = E.evaluate_one(lambda m: sc[m], test, random.Random(0))["auc_top"]
                    if r is not None:
                        aucs.append(r)
            res[lam] = statistics.fmean(aucs)
        return res
    lam_res = tune_lambda()
    best_lam = max(lam_res, key=lam_res.get)
    print(f"[{time.time()-t0:.0f}s] lambda {lam_res} -> {best_lam}", file=sys.stderr)

    # ---------------------------------------------------------------- methods at eval time
    def m_linear(name):
        c, w = models[name]

        def make(hist):
            st = Stats(hist, people, types)
            return lambda m: float(np.dot([features(st, m, people, types, pub)[i] for i in c] + [1.0], w))
        return make

    def m_graded_genre(wg):
        def make(hist):
            st = Stats(hist, people, types)
            g = E.graded(hist, people)
            return lambda m: (g(m) or 0.0) + wg * genre_part(st, m, types)[0]
        return make

    def m_genre_only(hist):
        st = Stats(hist, people, types)
        return lambda m: genre_part(st, m, types)[0]

    def m_mlp(hist):
        st = Stats(hist, people, types)

        def f(m):
            x = np.array([[features(st, m, people, types, pub)[i] for i in cm]])
            return float(mlp(stdz(x))[0])
        return f

    def m_shrink(lam):
        def make(hist):
            st = Stats(hist, people, types)
            w = per_user_fit(st, hist, lam)
            return lambda m: float(np.dot([features(st, m, people, types, pub)[i] for i in c_sh] + [1.0], w))
        return make

    def m_emb(lam):
        def make(hist):
            st = Stats(hist, people, types)
            Eh = np.array([emb(m) for m, _ in hist])
            z = np.array([st.z[m] for m, _ in hist])
            u = ridge(Eh, z, lam)
            return lambda m: float(emb(m) @ u)
        return make

    def m_creator_only(hist):
        return lambda m: pub["creator"](m)

    def m_genre_prior_only(hist):
        return lambda m: features(None or Stats(hist, people, types), m, people, types, pub)[FEATS.index("genre_prior")]

    methods = {
        "B0_current": lambda h: E.b0_current(h, people),
        "graded": lambda h: E.graded(h, people),
        "a_genre_only": m_genre_only,
        "a_graded+genre(w=1)": m_graded_genre(1.0),
        "b_meta_P": m_linear("meta_P"),
        "b_meta_PG": m_linear("meta_PG"),
        "b_meta_PG+genrePrior": m_linear("meta_PG_GP"),
        "b_meta_PG+GP+nCredits": m_linear("meta_PG_GP_META"),
        "c_shrink_tuned": m_shrink(best_lam),
        "c_shrink_none(lam=1)": m_shrink(1.0),
        "d_mlp_PG+GP": m_mlp,
        "e_emb_twotower(lam=10)": m_emb(10.0),
        "f_genrePrior_only": m_genre_prior_only,
        "f_creatorPrior_only": m_creator_only,
        "f_meta_PG+creatorPrior": m_linear("meta_PG_CR"),
    }
    per = {n: defaultdict(dict) for n in methods}    # method -> k -> user -> mean auc
    for ui, u in enumerate(eval_users):
        items = sorted(ratings[u].items())
        acc = {n: defaultdict(list) for n in methods}
        for s in range(a.shuffles):
            test, train = splits(items, a.seed, u, s)
            for k in KS:
                hist = train[:k]
                for n, mk in methods.items():
                    r = E.evaluate_one(mk(hist), test, random.Random(f"lc:{a.seed}:{u}:{s}:t"))
                    if r["auc_top"] is not None:
                        acc[n][k].append(r["auc_top"])
        for n in methods:
            if all(acc[n][k] for k in KS):
                for k in KS:
                    per[n][k][u] = statistics.fmean(acc[n][k])
        if ui % 50 == 0:
            print(f"[{time.time()-t0:.0f}s] user {ui}", file=sys.stderr)

    def ci(v):
        return 1.96 * statistics.pstdev(v) / math.sqrt(len(v))
    out = {"seed": a.seed, "eval_users": len(eval_users), "train_users": len(train_users),
           "pub_users": len(pub_users), "lambda_grid": {str(k): round(v, 4) for k, v in lam_res.items()},
           "best_lambda": str(best_lam), "meta_weights": {n: dict(zip([FEATS[i] for i in c] + ["bias"], np.round(w, 3).tolist())) for n, (c, w) in models.items()},
           "shrink_w0": dict(zip([FEATS[i] for i in c_sh] + ["bias"], np.round(w0_sh, 3).tolist())), "methods": {}}
    for n in methods:
        row = {}
        for k in KS:
            us = sorted(set(per[n][k]) & set(per["B0_current"][k]) & set(per["graded"][k]))
            v = [per[n][k][u] for u in us]
            d0 = [per[n][k][u] - per["B0_current"][k][u] for u in us]
            dg = [per[n][k][u] - per["graded"][k][u] for u in us]
            row[k] = {"auc": round(statistics.fmean(v), 4), "ci": round(ci(v), 4), "n": len(v),
                      "vsB0_better": round(sum(x > 0 for x in d0) / len(d0), 3),
                      "vsB0_worse": round(sum(x < 0 for x in d0) / len(d0), 3),
                      "vsGraded_diff": round(statistics.fmean(dg), 4), "vsGraded_ci": round(ci(dg), 4),
                      "vsGraded_better": round(sum(x > 0 for x in dg) / len(dg), 3),
                      "vsGraded_worse": round(sum(x < 0 for x in dg) / len(dg), 3)}
        us = [u for u in per[n][5] if u in per[n][80]]
        rise = [per[n][80][u] - per[n][5][u] for u in us]
        row["rise_5_to_80"] = {"mean": round(statistics.fmean(rise), 4), "ci": round(ci(rise), 4),
                               "rose": round(sum(x > 0 for x in rise) / len(rise), 3),
                               "fell": round(sum(x < 0 for x in rise) / len(rise), 3)}
        out["methods"][n] = row
    out["elapsed_s"] = round(time.time() - t0)
    txt = json.dumps(out, ensure_ascii=False, indent=1)
    if a.out:
        a.out.write_text(txt)
    print(txt)


if __name__ == "__main__":
    main()
