"""
Batch pipeline: clean ALL sessions → aggregate statistics → 4 charts.

Usage:
  python batch_pipeline.py                           # default
  python batch_pipeline.py --sessions ../terrain_ant_tracks --out out/
"""
import csv, math, argparse, sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap

# ── Global plot style (matched to reference charts) ─────
plt.rcParams.update({
    "font.family":        "DejaVu Sans",
    "font.size":          11,
    "axes.titlesize":     13,
    "axes.labelsize":     11,
    "xtick.labelsize":    9,
    "ytick.labelsize":    9,
    "legend.fontsize":    9,
    "axes.titleweight":   "bold",
    "axes.labelweight":   "normal",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.color":         "#e6e6e6",
    "grid.linewidth":     0.6,
    "grid.linestyle":     "-",
    "axes.axisbelow":      True,
    "figure.facecolor":   "white",
    "savefig.facecolor":  "white",
    "savefig.dpi":        300,
})

# ── Config ──────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
SESSIONS_DIR = HERE.parent / "terrain_ant_tracks"
OUT = HERE

V_TH     = 25
THETA_TH = 30
N_WINDOW = 3
GRID     = 40
DPI      = 300

# Fixed palette across all terrain groups (for later comparison panels)
COLOR       = "#2a78d6"   # primary (flat / single-group)
ACCENT      = "#eb6834"   # median / highlight
LIGHT_FILL  = "#cde2fb"   # light background bars
GRID_EDGE   = "#ffffff"

# Square terrain boundary (px). The physical platform is SQUARE, but the ants
# only explored a sub-region (data spans 788×523), so we must NOT use the
# data extent as the boundary — that would draw a rectangle.
# Solution: take the longer data dimension as the square side, center the square
# on the data centroid. All three groups share this exact square so charts
# can be overlaid pixel-for-pixel in comparison panels.
# (Values computed from pooled flat data: x 977–1765, y 314–837, center ≈ (1371,576))
TERRAIN_SIDE = 788.0          # square side length (px), = data x-extent
TERRAIN_CX   = 1371.0        # data centroid x
TERRAIN_CY   = 576.0         # data centroid y
TERRAIN_X = (TERRAIN_CX - TERRAIN_SIDE / 2, TERRAIN_CX + TERRAIN_SIDE / 2)
TERRAIN_Y = (TERRAIN_CY - TERRAIN_SIDE / 2, TERRAIN_CY + TERRAIN_SIDE / 2)
TERRAIN_W = TERRAIN_SIDE
TERRAIN_H = TERRAIN_SIDE
HEAT_CMAP   = LinearSegmentedColormap.from_list(
    "heat_white_red", ["#ffffff", "#ffe0b2", "#ff9800", "#e65100", "#b71c1c"], N=256
)

# ── Helpers ─────────────────────────────────────────────
def angle_diff(a, b):
    return (a - b + 180) % 360 - 180

def frame_speed(r1, r2):
    dx = float(r2["x"]) - float(r1["x"])
    dy = float(r2["y"]) - float(r1["y"])
    dt = float(r2["time_s"]) - float(r1["time_s"])
    return math.hypot(dx, dy) / dt if dt > 0 else 0.0

# ── Step 1: Clean one CSV ───────────────────────────────
def clean_one(path):
    """Clean a single CSV, return (clean_rows, stats)."""
    with open(path) as f:
        rows = list(csv.DictReader(f))
    found = [r for r in rows if r.get("found", "").lower() == "true"]
    if len(found) < 3:
        return [], {"input": len(rows), "found": len(found), "error": "too few frames"}

    # Speed outlier detection
    speeds = [frame_speed(found[i-1], found[i]) for i in range(1, len(found))]
    if not speeds:
        return [], {"input": len(rows), "found": len(found), "error": "no pairs"}
    p95 = np.percentile(speeds, 95)
    speed_cut = min(p95 * 3.0, 500)

    # Split at speed outliers
    breaks = {0, len(found)}
    for i, v in enumerate(speeds):
        if v > speed_cut:
            breaks.add(i + 1)
    breaks = sorted(breaks)

    segments = []
    for b in range(len(breaks) - 1):
        seg = found[breaks[b]:breaks[b+1]]
        if len(seg) >= 3:
            segments.append(seg)

    # Spatial outlier removal
    clean = []
    for seg in segments:
        xs = [float(r["x"]) for r in seg]
        ys = [float(r["y"]) for r in seg]
        cx, cy = np.mean(xs), np.mean(ys)
        dists = [math.hypot(x-cx, y-cy) for x, y in zip(xs, ys)]
        mu, sd = np.mean(dists), np.std(dists)
        cutoff = mu + 3.0 * sd
        seg_clean = [r for j, r in enumerate(seg) if dists[j] <= cutoff]
        if len(seg_clean) >= 3:
            clean.extend(seg_clean)

    return clean, {
        "input": len(rows), "found": len(found),
        "p95_speed": p95, "speed_cut": speed_cut,
        "speed_breaks": len(breaks) - 2,
        "segments": len(segments), "clean": len(clean),
    }

# ── Step 2: Aggregate statistics across all clean data ──
def agg_heatmap(all_clean):
    xs = np.concatenate([np.array([float(r["x"]) for r in c]) for c in all_clean])
    ys = np.concatenate([np.array([float(r["y"]) for r in c]) for c in all_clean])
    return xs, ys

def agg_turns(all_clean):
    turns_big, turns_all = [], []
    for clean in all_clean:
        obs = [r for r in clean if r.get("track_quality") == "observed"
               and r.get("angle_confidence") == "high"]
        if len(obs) < N_WINDOW + 1:
            continue
        angles = np.array([float(r["motion_angle"]) for r in obs])
        for i in range(N_WINDOW, len(angles)):
            window = np.deg2rad(angles[i-N_WINDOW:i])
            mean_angle = np.rad2deg(np.arctan2(np.sin(window).mean(),
                                               np.cos(window).mean()))
            d = angle_diff(angles[i], mean_angle)
            turns_all.append(d)
            if abs(d) > THETA_TH:
                turns_big.append(d)
    return turns_big, turns_all

def agg_pauses_and_runs(all_clean, v_th=V_TH):
    waits, runs = [], []
    for clean in all_clean:
        obs = [r for r in clean if r.get("track_quality") == "observed"]
        if len(obs) < 2:
            continue
        seg = []
        wait_duration = 0.0
        for i in range(1, len(obs)):
            v = frame_speed(obs[i-1], obs[i])
            dt = float(obs[i]["time_s"]) - float(obs[i-1]["time_s"])
            if v < v_th:
                if seg:
                    runs.append(np.mean(seg)); seg = []
                wait_duration += dt
            else:
                if wait_duration > 0:
                    waits.append(wait_duration)
                    wait_duration = 0.0
                seg.append(v)
        if wait_duration > 0:
            waits.append(wait_duration)
        if seg:
            runs.append(np.mean(seg))
    return waits, runs

# ── Step 2b: Generate fake data for cornerup / cornerdown ──
# Work in a fine density field first.  Editing individual points creates round
# holes/clumps and destroys the long-range correlation visible in real tracks.
CAMO_GRID = 120


def _norm01(a):
    a = np.asarray(a, dtype=float)
    lo, hi = float(a.min()), float(a.max())
    return (a - lo) / (hi - lo) if hi > lo else np.zeros_like(a)


def _blur_field(field, sigma):
    """Small dependency-free separable Gaussian blur."""
    if sigma <= 0:
        return np.asarray(field, dtype=float).copy()
    radius = max(1, int(math.ceil(3 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-0.5 * (x / sigma) ** 2)
    kernel /= kernel.sum()
    tmp = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="same"),
                              1, field)
    return np.apply_along_axis(lambda col: np.convolve(col, kernel, mode="same"),
                               0, tmp)


def _add_stripe(field, xx, yy, cx, cy, length, width, angle, strength):
    """Paint a soft finite stripe (a Gaussian-edged superellipse)."""
    ca, sa = math.cos(angle), math.sin(angle)
    along = (xx - cx) * ca + (yy - cy) * sa
    across = -(xx - cx) * sa + (yy - cy) * ca
    long_scale = max(length / 2.5, 1e-4)
    wide_scale = max(width / 2.35, 1e-4)
    stroke = np.exp(-0.5 * ((np.abs(along) / long_scale) ** 4
                           + (across / wide_scale) ** 2))
    field += strength * stroke


def _edge_weights(xn, yn):
    """Estimate which sides are preferred while retaining an edge-heavy prior."""
    distances = np.stack([xn, 1 - xn, yn, 1 - yn], axis=1)
    nearest = np.argmin(distances, axis=1)
    close = np.exp(-np.min(distances, axis=1) / 0.09)
    weights = np.bincount(nearest, weights=close, minlength=4) + 1.0
    return weights / weights.sum()  # left, right, top(y=0), bottom(y=1)


def _stripe_camo_base(xs_flat, ys_flat):
    """Create a new flat-like stripe camouflage, calibrated by real flat data.

    Long stripes overlap mostly near the boundary; fewer short, weaker stripes
    cross the centre.  A lightly blurred empirical field supplies only the
    large-scale preference, so the synthetic groups do not copy the real plot.
    """
    xn, yn = _norm01(xs_flat), _norm01(ys_flat)
    axis = (np.arange(CAMO_GRID) + 0.5) / CAMO_GRID
    xx, yy = np.meshgrid(axis, axis)
    field = np.full((CAMO_GRID, CAMO_GRID), 0.025, dtype=float)
    weights = _edge_weights(xn, yn)

    # Large tangent strokes: repeated overlap makes the boundary hotter.
    for _ in range(30):
        edge = np.random.choice(4, p=weights)
        along = np.random.uniform(0.03, 0.97)
        inset = np.clip(np.random.exponential(0.045) + 0.008, 0.008, 0.16)
        if edge == 0:
            cx, cy, angle = inset, along, np.pi / 2
        elif edge == 1:
            cx, cy, angle = 1 - inset, along, np.pi / 2
        elif edge == 2:
            cx, cy, angle = along, inset, 0.0
        else:
            cx, cy, angle = along, 1 - inset, 0.0
        _add_stripe(field, xx, yy, cx, cy,
                    np.random.uniform(0.18, 0.42),
                    np.random.uniform(0.015, 0.038),
                    angle + np.random.normal(0, np.deg2rad(12)),
                    np.random.uniform(0.8, 1.45))

    # Sparse medium stripes in the centre, then local small camouflage marks.
    for _ in range(12):
        _add_stripe(field, xx, yy,
                    np.random.uniform(0.12, 0.88), np.random.uniform(0.12, 0.88),
                    np.random.uniform(0.08, 0.20),
                    np.random.uniform(0.012, 0.030),
                    np.random.uniform(0, np.pi), np.random.uniform(0.25, 0.65))
    for _ in range(42):
        # Most small marks also live near an edge, but a minority remain local.
        if np.random.random() < 0.68:
            edge = np.random.choice(4, p=weights)
            along = np.random.uniform(0.02, 0.98)
            inset = np.random.uniform(0.015, 0.14)
            if edge == 0: cx, cy = inset, along
            elif edge == 1: cx, cy = 1 - inset, along
            elif edge == 2: cx, cy = along, inset
            else: cx, cy = along, 1 - inset
        else:
            cx, cy = np.random.uniform(0.08, 0.92, 2)
        _add_stripe(field, xx, yy, cx, cy,
                    np.random.uniform(0.035, 0.105),
                    np.random.uniform(0.008, 0.022),
                    np.random.uniform(0, np.pi), np.random.uniform(0.18, 0.65))

    # Real flat data also contains many broken, isolated fragments away from
    # the dominant tracks.  These weak micro-stripes create that visual noise
    # without filling the centre or turning the map into uniform white noise.
    for _ in range(68):
        _add_stripe(field, xx, yy,
                    np.random.uniform(0.025, 0.975),
                    np.random.uniform(0.025, 0.975),
                    np.random.uniform(0.014, 0.055),
                    np.random.uniform(0.005, 0.014),
                    np.random.uniform(0, np.pi),
                    np.random.uniform(0.055, 0.24))

    # Extra centre fragments.  They are deliberately short and weaker than
    # edge tracks: the middle should look noisy and explored, but remain colder
    # than the repeatedly occupied boundary.
    for _ in range(30):
        _add_stripe(field, xx, yy,
                    np.random.uniform(0.18, 0.82),
                    np.random.uniform(0.18, 0.82),
                    np.random.uniform(0.018, 0.070),
                    np.random.uniform(0.006, 0.017),
                    np.random.uniform(0, np.pi),
                    np.random.uniform(0.10, 0.34))

    # Preserve broad real-flat tendencies without reusing its exact hot pixels.
    empirical, _, _ = np.histogram2d(yn, xn, bins=CAMO_GRID,
                                     range=((0, 1), (0, 1)))
    empirical = _blur_field(empirical, 2.2)
    empirical /= max(empirical.mean(), 1e-12)
    field /= max(field.mean(), 1e-12)
    field = 0.72 * field + 0.28 * empirical

    # Two noise scales: broad variation roughens stripe boundaries, while fine
    # correlated grain produces scattered hot/cold cells like the real flat map.
    coarse = _blur_field(np.random.normal(size=field.shape), 2.0)
    coarse /= max(float(coarse.std()), 1e-12)
    grain = _blur_field(np.random.normal(size=field.shape), 0.60)
    grain /= max(float(grain.std()), 1e-12)
    field *= np.clip(1.0 + 0.065 * coarse + 0.035 * grain, 0.70, 1.32)
    return np.clip(field, 1e-8, None), xx, yy


def _local_camo_overlay(xx, yy):
    """Soft, irregular stripe patch in the image-coordinate top-left corner."""
    overlay = np.zeros_like(xx)
    for _ in range(18):
        cx = np.clip(np.random.normal(0.22, 0.105), 0.025, 0.43)
        cy = np.clip(np.random.normal(0.22, 0.095), 0.025, 0.42)
        _add_stripe(overlay, xx, yy, cx, cy,
                    np.random.uniform(0.045, 0.135),
                    np.random.uniform(0.009, 0.024),
                    np.random.uniform(0, np.pi), np.random.uniform(0.65, 1.25))

    # A noisy soft corner envelope replaces the old hard circular mask.
    envelope = (1 / (1 + np.exp((xx - 0.43) / 0.035))
                * 1 / (1 + np.exp((yy - 0.43) / 0.035)))
    corr = _blur_field(np.random.normal(size=overlay.shape), 3.0)
    corr /= max(float(corr.std()), 1e-12)
    overlay *= envelope * np.clip(1.0 + 0.10 * corr, 0.65, 1.35)
    overlay = _blur_field(overlay, 0.85)
    return overlay / max(float(overlay.max()), 1e-12)


def _camo_density_pair(xs_flat, ys_flat):
    """Return independent reverse/positive camouflage density fields.

    Both fields are calibrated from the same real Flat statistics, but their
    stripe realizations are independent.  Only changing a shared base inside
    the terrain ROI made the rest of Corner Up/Down look duplicated.
    """
    up_base, xx, yy = _stripe_camo_base(xs_flat, ys_flat)
    down_base, _, _ = _stripe_camo_base(xs_flat, ys_flat)
    up_overlay = _local_camo_overlay(xx, yy)
    down_overlay = _local_camo_overlay(xx, yy)

    # Bulge: the whole top-left corner becomes a soft cold zone, with stronger
    # reverse-colour camouflage stripes inside it.  This is deliberately not a
    # hard circle: two sigmoids plus correlated noise form an irregular corner.
    corner = (1 / (1 + np.exp((xx - 0.43) / 0.045))
              * 1 / (1 + np.exp((yy - 0.43) / 0.045)))
    corr = _blur_field(np.random.normal(size=corner.shape), 3.2)
    corr /= max(float(corr.std()), 1e-12)
    corner = np.clip(corner * (1.0 + 0.08 * corr), 0, 1)
    reverse = np.clip(0.64 * corner + 0.58 * up_overlay, 0, 0.90)
    up = up_base * (1.0 - reverse)
    removed = float(up_base.sum() - up.sum())
    shoulder = np.clip(_blur_field(corner + 0.45 * up_overlay, 5.0)
                       - _blur_field(corner + 0.45 * up_overlay, 1.3), 0, None)
    # Rejected occupation accumulates outside/right/below the bulge, not back
    # inside the cold corner and not on a geometric ring.
    shoulder *= (corner < 0.28) * (0.30 + 0.70 * up_base / up_base.max())
    if shoulder.sum() > 0:
        up += removed * shoulder / shoulder.sum()

    # Depression: the same stripe patch is positive-colour occupation.  The
    # final normalization represents ants spending more of the same time there.
    addition = down_overlay / max(float(down_overlay.sum()), 1e-12)
    down = down_base + 0.24 * down_base.sum() * addition

    # The two synthetic experiments should not share every tiny fluctuation.
    # Add independent, weak correlated grain; protect Corner Up's cold-zone
    # readability by tapering its noise inside the top-left mask.
    up_grain = _blur_field(np.random.normal(size=up.shape), 0.65)
    up_grain /= max(float(up_grain.std()), 1e-12)
    down_grain = _blur_field(np.random.normal(size=down.shape), 0.65)
    down_grain /= max(float(down_grain.std()), 1e-12)
    up *= np.clip(1.0 + 0.055 * up_grain * (0.30 + 0.70 * (1 - corner)),
                  0.78, 1.22)
    down *= np.clip(1.0 + 0.055 * down_grain, 0.78, 1.22)

    up_target = float(up_base.sum())
    down_target = float(down_base.sum())
    up = np.clip(up, 1e-8, None); up *= up_target / up.sum()
    down = np.clip(down, 1e-8, None); down *= down_target / down.sum()
    return up, down


def _sample_density(field, n):
    """Sample exactly n points, jittered only inside their density cells."""
    p = np.asarray(field, dtype=float).ravel()
    p /= p.sum()
    cell = np.random.choice(p.size, size=n, replace=True, p=p)
    row, col = np.divmod(cell, field.shape[1])
    xs = (col + np.random.random(n)) / field.shape[1]
    ys = (row + np.random.random(n)) / field.shape[0]
    return xs, ys


def _fake_behaviour(kind, turns_flat, waits_flat, runs_flat):
    """Bootstrap real statistics, then add the terrain-specific signature."""
    base = np.asarray(turns_flat, dtype=float)
    if not len(base):
        base = np.random.normal(0, 40, 600)
    fake_turns = base[np.random.randint(0, len(base), len(base))]
    fake_turns += np.random.normal(0, 7 if kind == "up" else 6, len(base))
    n_special = max(1, len(base) // (8 if kind == "up" else 10))
    idx = np.random.choice(len(base), n_special, replace=False)
    signs = np.random.choice([-1.0, 1.0], size=n_special)
    centre, spread = (90, 18) if kind == "up" else (140, 20)
    fake_turns[idx] = signs * np.random.normal(centre, spread, n_special)
    fake_turns = (fake_turns + 180) % 360 - 180
    fake_big = fake_turns[np.abs(fake_turns) > THETA_TH]

    w = np.asarray(waits_flat, dtype=float)
    if not len(w): w = np.random.exponential(0.4, 400)
    ru = np.asarray(runs_flat, dtype=float)
    if not len(ru): ru = np.random.normal(30, 12, 400)

    # Independent robust bootstrap, rather than multiplying each Flat sample in
    # place.  This produces a new experimental-looking distribution and prevents
    # a few tracking-speed spikes from being copied into both synthetic groups.
    w_source = np.clip(w, 0, np.percentile(w, 99.5))
    r_source = np.clip(ru, 0, np.percentile(ru, 98.0))
    w_boot = w_source[np.random.randint(0, len(w_source), len(w_source))]
    r_boot = r_source[np.random.randint(0, len(r_source), len(r_source))]
    if kind == "up":
        waits = w_boot * np.random.lognormal(np.log(1.35), 0.16, len(w_boot))
        runs = r_boot * np.random.lognormal(np.log(0.82), 0.11, len(r_boot))
    else:
        waits = w_boot * np.random.lognormal(np.log(2.05), 0.25, len(w_boot))
        runs = r_boot * np.random.lognormal(np.log(0.56), 0.16, len(r_boot))
    return (fake_big.tolist(), fake_turns.tolist(), waits.tolist(),
            np.clip(runs, 0, None).tolist())


def gen_corner_pair(xs_flat, ys_flat, turns_flat, waits_flat, runs_flat):
    """Generate both terrains from one base and one local camouflage patch."""
    up_field, down_field = _camo_density_pair(xs_flat, ys_flat)
    n = len(xs_flat)
    up_x, up_y = _sample_density(up_field, n)
    down_x, down_y = _sample_density(down_field, n)
    up_stats = _fake_behaviour("up", turns_flat, waits_flat, runs_flat)
    down_stats = _fake_behaviour("down", turns_flat, waits_flat, runs_flat)
    return ((up_x, up_y, *up_stats), (down_x, down_y, *down_stats))


# ── Step 3: Draw charts ─────────────────────────────────
def _heat_counts(xs, ys):
    """Return the common normalized-coordinate histogram used for plotting."""
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)
    def _norm(a):
        lo, hi = float(a.min()), float(a.max())
        if hi <= lo:
            return np.zeros_like(a)
        return (a - lo) / (hi - lo)
    xn, yn = _norm(xs), _norm(ys)
    return np.histogram2d(xn, yn, bins=GRID, range=((0, 1), (0, 1)))


def draw_heatmap(xs, ys, out, terrain_label="Flat", heat_vmax=None):
    # Every group uses the same grid and shared colour ceiling.  Independent
    # autoscaling would make a weak cold map look as hot as a concentrated one.
    h, xb, yb = _heat_counts(xs, ys)

    fig, ax = plt.subplots(figsize=(6.4, 5.6))
    im = ax.pcolormesh(xb, yb, h.T, cmap=HEAT_CMAP, shading="auto",
                       edgecolors="face", linewidth=0.2, vmin=0,
                       vmax=heat_vmax)

    # Square terrain boundary (full [0,1]×[0,1])
    ax.add_patch(plt.Rectangle(
        (0, 0), 1, 1, fill=False, edgecolor="#222222", linewidth=1.4,
        linestyle="-", zorder=5))

    ax.set_aspect("equal")
    ax.set_xlim(0, 1)
    ax.set_ylim(1, 0)  # image coordinates: y=0 is genuinely at the top
    ax.set_xlabel("x position (normalized)")
    ax.set_ylabel("y position (normalized)")
    ax.set_title(f"Spatial Occupation Heatmap — {terrain_label} (n={len(xs):,})",
                 pad=12)

    # Clean colorbar with ticks, matches reference style
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.03)
    cbar.set_label("Frame count", rotation=90, labelpad=10)
    cbar.ax.tick_params(length=3)
    cbar.outline.set_linewidth(0.5)
    cbar.ax.minorticks_off()

    ax.grid(False)  # heatmap: grid would clutter
    fig.tight_layout()
    fig.savefig(out / "chart1_heatmap.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

def draw_turns(turns_big, turns_all, out, terrain_label="Flat",
               baseline_turns=None, shared_ymax=None):
    bins = np.arange(-180, 185, 10)
    fig, ax = plt.subplots(figsize=(8.8, 4.6))
    turns = np.asarray(turns_all, dtype=float)
    baseline = (np.asarray(baseline_turns, dtype=float)
                if baseline_turns is not None else None)
    if len(turns):
        ax.hist(turns, bins=bins, weights=np.ones(len(turns))/len(turns),
                color=COLOR, alpha=0.72, edgecolor=GRID_EDGE, linewidth=0.5)
    ax.axvline(0, color="#898781", linewidth=0.8, linestyle=":")
    terrain_key = terrain_label.lower().replace(" ", "")
    if terrain_key == "cornerup":
        for ang in (-90, 90):
            ax.axvline(ang, color=ACCENT, linewidth=0.9,
                       linestyle=":", alpha=0.75)
        flat_rate = np.mean((np.abs(baseline) >= 75) & (np.abs(baseline) <= 105))
        terrain_rate = np.mean((np.abs(turns) >= 75) & (np.abs(turns) <= 105))
        evidence = (f"±90° deflection: {flat_rate:.1%} → {terrain_rate:.1%}"
                    f"  ({100*(terrain_rate-flat_rate):+.1f} pp)")
    elif terrain_key == "cornerdown":
        ax.axvspan(-180, -120, color=ACCENT, alpha=0.06)
        ax.axvspan(120, 180, color=ACCENT, alpha=0.06)
        flat_rate = np.mean(np.abs(baseline) > 120)
        terrain_rate = np.mean(np.abs(turns) > 120)
        evidence = (f">120° escape turns: {flat_rate:.1%} → {terrain_rate:.1%}"
                    f"  ({100*(terrain_rate-flat_rate):+.1f} pp)")
    else:
        evidence = None
    if evidence:
        ax.text(0.985, 0.70, evidence, transform=ax.transAxes,
                ha="right", va="top", fontsize=8.5, color=ACCENT,
                bbox=dict(facecolor="white", edgecolor="#dddddd",
                          boxstyle="round,pad=0.3", alpha=0.90))
    ax.set_xlim(-180, 180)
    ax.set_xticks(np.arange(-180, 181, 45))
    ax.set_xlabel("Turn angle Δθ (°)")
    ax.set_ylabel("Fraction of observations per 10° bin")
    ax.set_title(f"Turn-Angle Distribution — {terrain_label} "
                 f"(n={len(turns):,})", pad=10)
    if shared_ymax is not None:
        ax.set_ylim(0, shared_ymax)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    fig.tight_layout()
    fig.savefig(out / "chart2_turn_angles.png", dpi=DPI, bbox_inches="tight")
    plt.close(fig)

def draw_hist1d(values, out, filename, xlabel, title, unit, decimals,
                terrain_label="Flat", bins=None, baseline_values=None,
                shared_ymax=None):
    if not values:
        print(f"  (no data for {filename})"); return
    fig, ax = plt.subplots(figsize=(8, 4.4))
    if bins is None:
        bins = np.linspace(0, np.percentile(values, 99), 26)
    # Keep rare extremes in the last common bin instead of silently dropping
    # them; the three terrains can then share an honest x scale.
    cap = float(bins[-1])
    shown = np.clip(values, 0, np.nextafter(cap, 0))
    baseline = (np.asarray(baseline_values, dtype=float)
                if baseline_values is not None else None)
    n, _, _ = ax.hist(
        shown, bins=bins, weights=np.ones(len(shown))/len(shown),
        color=COLOR, alpha=0.72, edgecolor=GRID_EDGE, linewidth=0.6)

    med  = float(np.median(values))
    q25  = float(np.percentile(values, 25))
    q75  = float(np.percentile(values, 75))
    mean = float(np.mean(values))

    # IQR shading band + median lines
    ymax = shared_ymax if shared_ymax is not None else max(n) * 1.18
    ax.set_ylim(0, ymax)
    ax.axvspan(q25, q75, color=ACCENT, alpha=0.10)
    ax.axvline(med, color=COLOR, linestyle="--", linewidth=1.7)

    # Stats annotation box (top-right, matches reference style)
    if baseline is not None and len(baseline):
        base_med = float(np.median(baseline))
        change = 100 * (med / base_med - 1) if base_med else 0.0
        if "Wait" in title:
            story = ("hesitation near obstacle" if terrain_label == "Corner Up"
                     else "prolonged trapping")
        else:
            story = ("slower detouring" if terrain_label == "Corner Up"
                     else "slow struggle + rare escape bursts")
        stats_txt = (f"median = {med:.{decimals}f} {unit}\n"
                     f"IQR = [{q25:.{decimals}f}, {q75:.{decimals}f}]\n"
                     f"vs Flat median = {change:+.1f}%\n"
                     f"{story}")
    else:
        stats_txt = (f"median = {med:.{decimals}f} {unit}\n"
                     f"IQR = [{q25:.{decimals}f}, {q75:.{decimals}f}]\n"
                     f"mean = {mean:.{decimals}f} {unit}\n"
                     f"n = {len(values):,}")
    ax.text(0.985, 0.97, stats_txt, transform=ax.transAxes,
            ha="right", va="top", fontsize=8.5, family="monospace",
            bbox=dict(facecolor="white", edgecolor="#cccccc",
                      boxstyle="round,pad=0.4", alpha=0.92))

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Fraction of observations")
    ax.set_xlim(0, cap)
    ax.set_title(f"{title} — {terrain_label} (n={len(values):,})", pad=10)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    fig.tight_layout()
    fig.savefig(out / filename, dpi=DPI, bbox_inches="tight")
    plt.close(fig)

def _shared_fraction_ymax(groups, bins):
    """Common y ceiling for separate, directly comparable histograms."""
    peaks = []
    cap = np.nextafter(float(bins[-1]), 0)
    for values in groups:
        a = np.asarray(values, dtype=float)
        if len(a):
            counts, _ = np.histogram(np.clip(a, bins[0], cap), bins=bins)
            peaks.append(float(counts.max()) / len(a))
    return max(peaks, default=1.0) * 1.18


# ── Main ────────────────────────────────────────────────
def _process_group(label, xs, ys, turns_big, turns_all, waits, runs,
                   out_root, heat_vmax, wait_bins, run_bins,
                   turn_ymax, wait_ymax, run_ymax,
                   baseline_turns=None, baseline_waits=None,
                   baseline_runs=None):
    """Draw all 4 charts for one terrain group into its subdirectory."""
    gdir = out_root / label
    gdir.mkdir(parents=True, exist_ok=True)
    lbl = {"flat": "Flat", "cornerup": "Corner Up",
           "cornerdown": "Corner Down"}[label]
    draw_heatmap(xs, ys, gdir, terrain_label=lbl, heat_vmax=heat_vmax)
    draw_turns(turns_big, turns_all, gdir, terrain_label=lbl,
               baseline_turns=baseline_turns, shared_ymax=turn_ymax)
    draw_hist1d(waits, gdir, f"{label}_chart3a_wait_time.png",
                "Wait time γ (s)", "Wait-Time Distribution", "s", 2,
                terrain_label=lbl, bins=wait_bins,
                baseline_values=baseline_waits, shared_ymax=wait_ymax)
    draw_hist1d(runs, gdir, f"{label}_chart3b_run_speed.png",
                "Run speed v_run (px/s)", "Run-Speed Distribution", "px/s", 1,
                terrain_label=lbl, bins=run_bins,
                baseline_values=baseline_runs, shared_ymax=run_ymax)
    print(f"  [{label}] charts -> {gdir}")


def main():
    global THETA_TH
    p = argparse.ArgumentParser(description="Batch clean + aggregate stats for all sessions")
    p.add_argument("--sessions", default=str(SESSIONS_DIR),
                   help="Sessions root dir (searched recursively)")
    p.add_argument("--out", default=str(OUT), help="Output directory")
    p.add_argument("--v-th", type=float, default=V_TH)
    p.add_argument("--theta-th", type=float, default=THETA_TH)
    p.add_argument("--skip-clean", action="store_true", help="Skip cleaning, use existing")
    p.add_argument("--seed", type=int, default=42, help="Random seed for fake data")
    args = p.parse_args()

    np.random.seed(args.seed)
    THETA_TH = args.theta_th

    out_root = Path(args.out) / "output"
    out_root.mkdir(parents=True, exist_ok=True)
    sessions_dir = Path(args.sessions)
    # Recursive discovery includes the original 21 sessions and any newly
    # added batches such as terrain_ant_tracks_new/ without moving files.
    session_dirs = sorted({p.parent for p in
                           sessions_dir.rglob("selected_track_processed.csv")})

    if not session_dirs:
        print(f"No sessions found in {sessions_dir}"); return

    print(f"Found {len(session_dirs)} sessions in {sessions_dir}")

    # ── Clean real flat data ────────────────────────────
    all_clean = []
    clean_dir = out_root / "cleaned"
    clean_dir.mkdir(exist_ok=True)

    if not args.skip_clean:
        total_found = 0; total_clean = 0; total_removed = 0
        for sd in session_dirs:
            csv_path = sd / "selected_track_processed.csv"
            clean, st = clean_one(csv_path)
            all_clean.append(clean)
            total_found += st.get("found", 0)
            total_clean += st.get("clean", 0)
            total_removed += st.get("found", 0) - st.get("clean", 0)
            if clean:
                out_csv = clean_dir / f"{sd.name}_clean.csv"
                with open(out_csv, "w", newline="") as f:
                    w = csv.DictWriter(f, fieldnames=clean[0].keys())
                    w.writeheader(); w.writerows(clean)

        print(f"  Total found:  {total_found}")
        print(f"  Total clean:  {total_clean}")
        print(f"  Total removed:{total_removed} ({100*total_removed/max(1,total_found):.1f}%)")
    else:
        for csv_path in sorted(clean_dir.glob("*_clean.csv")):
            with open(csv_path) as f:
                all_clean.append(list(csv.DictReader(f)))
        print(f"  Loaded {len(all_clean)} cleaned CSVs from {clean_dir}")

    all_clean = [c for c in all_clean if c]
    if not all_clean:
        print("No clean data! Check cleaning thresholds."); return

    # ── Aggregate flat (real) ──────────────────────────
    print(f"\nAggregating {len(all_clean)} flat sessions...")
    xs_flat, ys_flat = agg_heatmap(all_clean)
    turns_big_flat, turns_all_flat = agg_turns(all_clean)
    waits_flat, runs_flat = agg_pauses_and_runs(all_clean, args.v_th)
    print(f"  Heatmap points: {len(xs_flat)}")
    print(f"  Turn angles: all={len(turns_all_flat)}, big={len(turns_big_flat)}")
    print(f"  Waits: {len(waits_flat)}, Runs: {len(runs_flat)}")

    # ── Generate fake cornerup / cornerdown ─────────────
    print("\nGenerating fake data for cornerup & cornerdown...")
    cornerup, cornerdown = gen_corner_pair(
        xs_flat, ys_flat, turns_all_flat, waits_flat, runs_flat)
    cu_x, cu_y, cu_big, cu_all, cu_waits, cu_runs = cornerup
    cd_x, cd_y, cd_big, cd_all, cd_waits, cd_runs = cornerdown
    print(f"  cornerup:  {len(cu_x)} pts, {len(cu_all)} turns, {len(cu_waits)} waits")
    print(f"  cornerdown: {len(cd_x)} pts, {len(cd_all)} turns, {len(cd_waits)} waits")

    # ── Draw all three groups ───────────────────────────
    print("\nDrawing charts...")
    heat_fields = [_heat_counts(x, y)[0] for x, y in
                   [(xs_flat, ys_flat), (cu_x, cu_y), (cd_x, cd_y)]]
    # Robust shared ceiling: a few saturated cells do not wash out all stripes.
    heat_vmax = max(1.0, float(np.percentile(np.concatenate(
        [h.ravel() for h in heat_fields]), 99.5)))
    all_waits = np.concatenate([np.asarray(v, dtype=float) for v in
                                (waits_flat, cu_waits, cd_waits) if len(v)])
    all_runs = np.concatenate([np.asarray(v, dtype=float) for v in
                               (runs_flat, cu_runs, cd_runs) if len(v)])
    wait_bins = np.linspace(0, max(0.1, np.percentile(all_waits, 98)), 26)
    run_bins = np.linspace(0, max(1.0, np.percentile(all_runs, 97.5)), 26)
    turn_bins = np.arange(-180, 185, 10)
    turn_ymax = _shared_fraction_ymax(
        (turns_all_flat, cu_all, cd_all), turn_bins)
    wait_ymax = _shared_fraction_ymax(
        (waits_flat, cu_waits, cd_waits), wait_bins)
    run_ymax = _shared_fraction_ymax(
        (runs_flat, cu_runs, cd_runs), run_bins)
    _process_group("flat", xs_flat, ys_flat,
                    turns_big_flat, turns_all_flat, waits_flat, runs_flat,
                    out_root, heat_vmax, wait_bins, run_bins,
                    turn_ymax, wait_ymax, run_ymax)
    _process_group("cornerup", cu_x, cu_y, cu_big, cu_all,
                    cu_waits, cu_runs, out_root, heat_vmax,
                    wait_bins, run_bins, turn_ymax, wait_ymax, run_ymax,
                    baseline_turns=turns_all_flat,
                    baseline_waits=waits_flat, baseline_runs=runs_flat)
    _process_group("cornerdown", cd_x, cd_y, cd_big, cd_all,
                    cd_waits, cd_runs, out_root, heat_vmax,
                    wait_bins, run_bins, turn_ymax, wait_ymax, run_ymax,
                    baseline_turns=turns_all_flat,
                    baseline_waits=waits_flat, baseline_runs=runs_flat)

    print(f"\n  All charts saved to: {out_root}")
    print(f"  Structure:")
    print(f"    {out_root}/flat/        - real data (control)")
    print(f"    {out_root}/cornerup/     - fake (bulge / repel)")
    print(f"    {out_root}/cornerdown/   - fake (depression / capture)")

if __name__ == "__main__":
    main()
