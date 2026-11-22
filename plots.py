import json
import math
import statistics

import matplotlib.pyplot as plt
import numpy as np

from analysis import KS, LEVELS, NS, group, line_fit_data, load, mean
from circuit import theory

rows = load()
groups = group(rows)
with open("data/grid.json") as f:
    eps = json.load(f)["mean_cx_error"]


def spread(rows, key):
    return statistics.stdev(r[key] for r in rows)


fig, axes = plt.subplots(1, 3, figsize=(12, 3.6), sharey=True)
for ax, n in zip(axes, NS):
    k_smooth = np.linspace(1, 9, 200)
    ax.plot(k_smooth, [theory(n, k) for k in k_smooth], color="lightgray", label="teorija")
    ideal = [statistics.mean(r["p_ideal"] for L in LEVELS for r in groups[(n, L, k)]) for k in KS]
    ax.plot(KS, ideal, "kx", label="idealni simulator")
    for L in LEVELS:
        ax.errorbar([k + (L - 1.5) * 0.08 for k in KS],
                    [mean(groups[(n, L, k)], "p_noisy") for k in KS],
                    yerr=[spread(groups[(n, L, k)], "p_noisy") for k in KS],
                    marker="o", markersize=3, capsize=2, label=f"šum, stopnja {L}")
    ax.axhline(1 / 2 ** n, color="gray", linestyle="--", linewidth=0.8, label="naključno ugibanje 1/N")
    ax.set_title(f"n = {n} (N = {2 ** n})")
    ax.set_xlabel("število iteracij k")
    ax.set_xticks(list(KS))
axes[0].set_ylabel("verjetnost uspeha")
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=7, fontsize=8)
fig.tight_layout(rect=(0, 0.08, 1, 1))
fig.savefig("figures/success_vs_k.pdf")

fig, axes = plt.subplots(1, 3, figsize=(12, 3.6))
for ax, n in zip(axes, NS):
    ax.plot(KS, [groups[(n, 0, k)][0]["cx_before"] for k in KS], "k--", label="pred prevajanjem")
    for L in LEVELS:
        ax.errorbar(KS, [mean(groups[(n, L, k)], "cx_after") for k in KS],
                    yerr=[spread(groups[(n, L, k)], "cx_after") for k in KS],
                    marker="o", markersize=3, capsize=2, label=f"po prevajanju, stopnja {L}")
    ax.set_title(f"n = {n}")
    ax.set_xlabel("število iteracij k")
    ax.set_xticks(list(KS))
axes[0].set_ylabel("število vrat CX")
axes[0].legend(fontsize=7)
fig.tight_layout()
fig.savefig("figures/cx_vs_k.pdf")

fig, axes = plt.subplots(1, 2, figsize=(8, 4), sharey=True)
for ax, key, title in [(axes[0], "p_pred_mean", "ocena s povprečno napako"),
                       (axes[1], "p_pred_actual", "ocena z napakami uporabljenih parov")]:
    for n in NS:
        part = [r for r in rows if r["n"] == n]
        ax.scatter([r[key] for r in part], [r["p_noisy"] for r in part], s=6, alpha=0.5, label=f"n = {n}")
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8)
    ax.set_title(title)
    ax.set_xlabel("napovedana verjetnost uspeha")
axes[0].set_ylabel("izmerjena verjetnost uspeha (šum)")
axes[0].legend()
fig.tight_layout()
fig.savefig("figures/measured_vs_predicted.pdf")

xs, ys = line_fit_data(rows)
slope, intercept = np.polyfit(xs, ys, 1)
g = np.linspace(0, xs.max(), 100)
fig, ax = plt.subplots(figsize=(6, 4))
ax.scatter(xs, ys, s=6, alpha=0.5)
ax.plot(g, slope * g + intercept, "r", label=f"prilagojena premica, naklon {slope:.4f}")
ax.plot(g, math.log(1 - eps) * g + intercept, "k--", label=f"pričakovano ln(1-ε) = {math.log(1 - eps):.4f}")
ax.set_xlabel("število vrat CX po prevajanju")
ax.set_ylabel("ln(preživeli signal)")
ax.legend()
fig.tight_layout()
fig.savefig("figures/line_check.pdf")
