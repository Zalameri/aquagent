"""Draw the report figures (ACL column width) from the CSV files made by generate_analysis.py.

Run from the repository root:  python analysis/make_report_figures.py
Reads analysis/data/*.csv and writes PDF + PNG figures to report/source/figures/ (used by main.tex and the README).
The posterior curve uses the Bayes formula from src/uncertainty.py (prior 0.35, specificity 0.90)."""
import csv, sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

HERE = Path(__file__).resolve().parent
D = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "data"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parent / "report" / "source" / "figures"
OUT.mkdir(exist_ok=True, parents=True)
for f in Path("/usr/share/texmf/fonts/opentype/public/tex-gyre").glob("texgyretermes-*.otf"):
    fm.fontManager.addfont(str(f))
def _pick_font():
    names = {f.name for f in fm.fontManager.ttflist}
    return next((n for n in ("TeX Gyre Termes", "Times New Roman", "Liberation Serif") if n in names), "DejaVu Serif")

plt.rcParams.update({
    "font.family": _pick_font(), "mathtext.fontset": "stix", "font.size": 8.5,
    "axes.titlesize": 9, "axes.labelsize": 8.5, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.6,
    "xtick.major.width": 0.6, "ytick.major.width": 0.6, "lines.linewidth": 1.4,
    "axes.grid": True, "axes.axisbelow": True, "grid.color": "#e3e3e3", "grid.linewidth": 0.5,
})
TEAL, ORANGE, GREY, RED = "#0F7C78", "#D9822B", "#9AA0A6", "#B5443B"
def save(fig, name):
    fig.savefig(OUT / name, bbox_inches="tight", pad_inches=0.02)
    fig.savefig(OUT / name.replace(".pdf", ".png"), dpi=220, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)

def read(name):
    with open(D / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

# ---- Figure: scenario outcomes (horizontal bars) ----
rows = read("scenario_results.csv")
fig, ax = plt.subplots(figsize=(3.05, 2.55))
names = [r["Scenario"] for r in rows][::-1]
for i, r in enumerate(rows[::-1]):
    w = r["Water (L), demo"]
    if r["Status"] == "SUCCESS":
        fog = r["Recommendation"].startswith("Fog")
        v = float(w)
        ax.barh(i, v, color=TEAL if fog else ORANGE, height=0.62)
        lab = f'{"Fog" if fog else "MOF"} {r["Hours"]} h · {v:.3f} L'
        ax.text(v + 0.05, i, lab, va="center", fontsize=7)
    else:
        lab = "no feasible plan" if r["Status"] == "NO_FEASIBLE_METHOD" else "input warning"
        ax.text(0.05, i, lab, va="center", fontsize=7, style="italic", color=RED)
ax.set_yticks(range(len(names)), names)
ax.set_xlim(0, 4.0); ax.set_xlabel("Selected-plan water (L, simulated)")
ax.grid(axis="y", visible=False); ax.tick_params(axis="y", length=0)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=TEAL, label="Fog mesh"), Patch(color=ORANGE, label="MOF-303 bed")],
          loc="center right", frameon=False, fontsize=7)
save(fig, "scenarios.pdf")

# ---- Figure: four one-at-a-time sweeps ----
sens = read("sensitivity_values.csv")
def series(var):
    s = [(float(r["input"]), float(r["yield_liters_demo"])) for r in sens if r["variable"] == var]
    return [a for a, _ in s], [b for _, b in s]
panels = [("wind_m_s", "Wind speed (m/s)", "(a) Fog: wind", TEAL, 2.0),
          ("fog_lwc_g_m3", r"Fog LWC (g/m$^3$)", "(b) Fog: LWC", TEAL, 0.20),
          ("mof_mass_kg", "MOF-303 mass (kg)", "(c) MOF: sorbent mass", ORANGE, 1.0),
          ("humidity_pct", "Relative humidity (%)", "(d) MOF: RH (limitation)", ORANGE, 85)]
fig, axs = plt.subplots(1, 4, figsize=(6.3, 1.65))
for ax, (var, xl, title, c, base) in zip(axs, panels):
    x, y = series(var)
    ax.plot(x, y, color=c, marker="o" if var == "humidity_pct" else None, markersize=2)
    by = y[min(range(len(x)), key=lambda i: abs(x[i] - base))]
    ax.plot([base], [by], "o", color="black", markersize=3.2, zorder=5)
    ax.set_xlabel(xl); ax.set_title(title, loc="left")
    if var == "humidity_pct":
        ax.set_ylim(0, 0.05)
axs[0].set_ylabel("Yield in 4 h (L, sim.)")
fig.tight_layout(w_pad=0.9)
save(fig, "sensitivity.pdf")

# ---- Figure: energy budget step + Bayesian posterior vs sensitivity ----
er = read("energy_budget_sensitivity.csv")
b = [float(r["Available energy (kWh)"]) for r in er]
w = [float(r["Water (L), demo"]) if r["Water (L), demo"] else 0.0 for r in er]
fig, axs = plt.subplots(1, 2, figsize=(3.1, 1.6))
ax = axs[0]
ax.step(b, w, where="post", color=TEAL); ax.plot(b, w, "o", color=TEAL, markersize=2.5)
ax.set_xscale("symlog", linthresh=0.5); ax.set_xticks([0, 0.2, 0.4, 1, 2, 8], ["0", ".2", ".4", "1", "2", "8"])
ax.set_xlabel("Energy budget (kWh)"); ax.set_ylabel("Selected water (L)")
ax.set_title("(a) Energy budget", loc="left")
for x0, lab in [(0.1, "1 h"), (0.2, "2 h"), (0.4, "4 h")]:
    yy = w[b.index(x0)]
    ax.annotate(lab, (x0, yy), xytext=(3, -8 if x0 != 0.4 else -9), textcoords="offset points", fontsize=6.5)
ax = axs[1]
prior, spec = 0.35, 0.90
se = [0.5 + i * 0.005 for i in range(101)]
post = [s * prior / (s * prior + (1 - spec) * (1 - prior)) for s in se]
ax.plot(se, post, color=TEAL)
ax.axhline(0.75, color=RED, lw=0.8, ls="--"); ax.text(0.72, 0.727, "threshold 0.75", fontsize=6.5, color=RED)
for s_, p_ in [(0.55, 0.7476), (0.90, 0.8289)]:
    ax.plot([s_], [p_], "o", color="black", markersize=3)
ax.set_xlabel("Sensor sensitivity"); ax.set_ylabel(r"$P(F\mid E^+)$")
ax.set_title("(b) Fog posterior", loc="left"); ax.set_ylim(0.7, 0.9)
fig.tight_layout(w_pad=0.6)
save(fig, "energy_posterior.pdf")
print("ok")
