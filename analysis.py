import csv
import json
import math
import statistics
import sys
from collections import defaultdict

import numpy as np
from scipy import stats

NS = [2, 3, 4]
KS = range(1, 10)
LEVELS = [0, 1, 2, 3]
K_OPT = {2: 1, 3: 2, 4: 3}
K_SECOND = {2: 4, 3: 6, 4: 9}


def to_number(text):
    try:
        return int(text)
    except ValueError:
        return float(text)


def load():
    with open("data/grid.csv") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for key in r:
            if key != "physical_qubits":
                r[key] = to_number(r[key])
    return rows


def group(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["n"], r["level"], r["k"])].append(r)
    return groups


def mean(rows, key):
    return statistics.mean(r[key] for r in rows)


def ci95(rows, key):
    values = [r[key] for r in rows]
    t = stats.t.ppf(0.975, len(values) - 1)
    return t * statistics.stdev(values) / math.sqrt(len(values))


def best_k(groups, n, level, key):
    return max(KS, key=lambda k: mean(groups[(n, level, k)], key))


def tied_with_best(groups, n, level):
    kb = best_k(groups, n, level, "p_noisy")
    best = groups[(n, level, kb)]
    tied = []
    for k in KS:
        other = groups[(n, level, k)]
        gap = mean(best, "p_noisy") - mean(other, "p_noisy")
        if k != kb and gap < ci95(best, "p_noisy") + ci95(other, "p_noisy"):
            tied.append(k)
    return tied


def line_fit_data(rows):
    xs, ys = [], []
    for r in rows:
        N = 2 ** r["n"]
        signal = r["p_theory"] - 1 / N
        if abs(signal) < 0.2:
            continue
        ratio = (r["p_noisy"] - 1 / N) / signal
        if ratio <= 0:
            continue
        xs.append(r["cx_after"])
        ys.append(math.log(ratio))
    return np.array(xs), np.array(ys)


if __name__ == "__main__":
    sys.stdout = open("data/analysis.txt", "w", encoding="utf-8")

    rows = load()
    groups = group(rows)
    with open("data/grid.json") as f:
        info = json.load(f)
    eps = info["mean_cx_error"]
    print(f"{len(rows)} rows, {info['shots']} shots, backend {info['backend']}, mean CX error {eps:.4f}\n")

    print("=== Mean noisy success probability over seeds (± 95 % interval) ===")
    for n in NS:
        print(f"\nn = {n}, random guess 1/N = {1 / 2 ** n:.3f}")
        print("k      theory  " + "  ".join(f"level {L:<8}" for L in LEVELS))
        for k in KS:
            cells = [f"{mean(groups[(n, L, k)], 'p_noisy'):.3f} ±{ci95(groups[(n, L, k)], 'p_noisy'):.3f}"
                     for L in LEVELS]
            print(f"{k:<6} {groups[(n, 0, k)][0]['p_theory']:.3f}   " + "  ".join(f"{c:<14}" for c in cells))

    print("\n=== Best k per n and level ===")
    print("n  level  k_opt  k*  tied with  predicted(mean eps)  predicted(actual eps)")
    hits_mean = hits_actual = 0
    for n in NS:
        for L in LEVELS:
            ks = best_k(groups, n, L, "p_noisy")
            km = best_k(groups, n, L, "p_pred_mean")
            ka = best_k(groups, n, L, "p_pred_actual")
            hits_mean += km == ks
            hits_actual += ka == ks
            tied = ",".join(map(str, tied_with_best(groups, n, L))) or "-"
            print(f"{n}  {L}      {K_OPT[n]}      {ks}   {tied:<10} {km:<20} {ka}")

    print("\n=== H1: is k* below the theoretical optimum? is the second peak lower? ===")
    for n in NS:
        for L in LEVELS:
            ks = best_k(groups, n, L, "p_noisy")
            p1 = mean(groups[(n, L, K_OPT[n])], "p_noisy")
            p2 = mean(groups[(n, L, K_SECOND[n])], "p_noisy")
            print(f"n={n} L{L}: k*={ks} vs k_opt={K_OPT[n]} -> {'shifted down' if ks < K_OPT[n] else 'not shifted'};"
                  f"  first peak {p1:.3f}, second peak (k={K_SECOND[n]}) {p2:.3f}"
                  f" -> second {'NOT higher' if p2 <= p1 else 'HIGHER'}")

    print("\n=== H2 (1): mean CX count after transpilation, per k and level ===")
    for n in NS:
        print(f"n = {n}:  cx_before by k = {[groups[(n, 0, k)][0]['cx_before'] for k in KS]}")
        for L in LEVELS:
            print(f"   level {L}: {[round(mean(groups[(n, L, k)], 'cx_after'), 1) for k in KS]}")

    print("\nLevels 2 and 3 with identical depth, CX, 1q-gate count and qubits:")
    keys = ("depth_after", "cx_after", "oneq_after", "physical_qubits")
    for n in NS:
        pairs = [(r2, r3) for k in KS for r2, r3 in zip(groups[(n, 2, k)], groups[(n, 3, k)])]
        same = sum(all(r2[x] == r3[x] for x in keys) for r2, r3 in pairs)
        print(f"   n={n}: {same}/{len(pairs)}")

    print("\n=== H2 (2) and (3): does a higher level help at k_opt, and move k* towards k_opt? ===")
    for n in NS:
        ps = [f"{mean(groups[(n, L, K_OPT[n])], 'p_noisy'):.3f}" for L in LEVELS]
        kss = [best_k(groups, n, L, "p_noisy") for L in LEVELS]
        print(f"n={n}: p at k_opt by level {ps};  k* by level {kss} (k_opt {K_OPT[n]})")

    print("\n=== H3 (1): does the simple estimate predict the best k? ===")
    print(f"mean-error estimate:   {hits_mean}/12 hits")
    print(f"actual-error estimate: {hits_actual}/12 hits")

    print("\n=== H3 (2): straight-line check, y = ln(surviving signal) against CX count ===")
    xs, ys = line_fit_data(rows)
    fit = stats.linregress(xs, ys)
    print(f"{len(xs)} of {len(rows)} rows used")
    print(f"fitted slope {fit.slope:.4f} ± {1.96 * fit.stderr:.4f} (95 %), expected ln(1 - eps) = {math.log(1 - eps):.4f}")
    print(f"intercept {fit.intercept:.3f}, R^2 = {fit.rvalue ** 2:.3f}, p = {fit.pvalue:.1e}")

    print("\n=== H3 (3): mean |measured - predicted| ===")
    print(f"mean-error estimate:   {statistics.mean(abs(r['p_noisy'] - r['p_pred_mean']) for r in rows):.4f}")
    print(f"actual-error estimate: {statistics.mean(abs(r['p_noisy'] - r['p_pred_actual']) for r in rows):.4f}")

    print("\n=== Circuit properties at k_opt, before and after transpilation (mean over seeds, min-max) ===")
    print("n  k  level  qubits  depth before  CX before  depth after          CX after")
    for n in NS:
        k = K_OPT[n]
        for L in LEVELS:
            g = groups[(n, L, k)]
            d = [r["depth_after"] for r in g]
            c = [r["cx_after"] for r in g]
            print(f"{n}  {k}  {L}      {n}       {g[0]['depth_before']:<13} {g[0]['cx_before']:<10}"
                  f" {statistics.mean(d):6.1f} ({min(d)}-{max(d)})    {statistics.mean(c):6.1f} ({min(c)}-{max(c)})")

    print("\n=== Classical comparison (best level and k per n) ===")
    for n in NS:
        N = 2 ** n
        L, k = max(((L, k) for L in LEVELS for k in KS), key=lambda lk: mean(groups[(n, *lk)], "p_noisy"))
        p = mean(groups[(n, L, k)], "p_noisy")
        print(f"n={n}: best p={p:.3f} (level {L}, k={k}), random guess {1 / N:.3f};"
              f" expected circuit runs 1/p = {1 / p:.1f}, classical lookups (N+1)/2 = {(N + 1) / 2:.1f}")

    sys.stdout.close()
    sys.stdout = sys.__stdout__
    print("written to data/analysis.txt")
