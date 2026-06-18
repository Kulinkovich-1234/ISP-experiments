"""Titration data processing script

Processes raw photodetector voltage from EDTA titration CSV files.
Fits an RC step-response model to the full curve to locate endpoint.

Usage:
    python process_titration.py

Output:
    - Terminal table: endpoint, lambda, R², calculated concentration
    - PNG figures: titration curve + RC fit
"""

import numpy as np
import csv
import os
from glob import glob
from collections import OrderedDict

from scipy.signal import savgol_filter
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams.update({
    'font.size': 10,
    'axes.labelsize': 11,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,
    'legend.fontsize': 8,
    'figure.dpi': 150,
})

# ── Physical / chemical constants ─────────────────────────────
SYRINGE_INNER_DIAM_MM = 4.73
AREA_UL_PER_MM = np.pi * (SYRINGE_INNER_DIAM_MM / 2) ** 2   # uL/mm

C_EDTA_NOMINAL = 0.02        # mol/L, nominal EDTA concentration
V_PRE_EDTA_ML = 0.500        # mL, pre-added EDTA
V_MGSO4_ML = 1.000           # mL, MgSO4 sample volume
V_TAP_WATER_ML = 1.5         # mL, tap water sample volume
M_CACO3 = 100.09             # g/mol

SG_WINDOW = 30
SG_ORDER = 3


# ── Model ─────────────────────────────────────────────────────

def rc_step_response(ul, V1, delta_V, ul_ep, lam):
    """First-order RC step response in volume domain.

    V(uL) = V1 + delta_V * [1 - exp(-(uL - uL_ep)/lam)] * u(uL - uL_ep)
    """
    return V1 + delta_V * (1 - np.exp(-np.clip(ul - ul_ep, 0, None) / lam))


# ── Load & preprocess ─────────────────────────────────────────

def load_titration_csv(path):
    """Load CSV into an OrderedDict of numpy arrays."""
    cols = OrderedDict()
    cols['timestamp'] = []
    cols['time_s'] = []
    cols['disp_mm'] = []
    cols['disp_ul'] = []
    cols['raw_V'] = []
    cols['avg_V'] = []

    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cols['timestamp'].append(row['timestamp'])
            cols['time_s'].append(float(row['time_s']))
            cols['disp_mm'].append(float(row['disp_mm']))
            cols['disp_ul'].append(float(row['disp_ul']))
            cols['raw_V'].append(float(row['raw_V']))
            cols['avg_V'].append(float(row['avg_V']))

    return {k: np.array(v) for k, v in cols.items()}


def smooth_raw(data):
    """Savitzky-Golay smoothing on raw_V (not using avg_V from file)."""
    data['smooth_V'] = savgol_filter(data['raw_V'], SG_WINDOW, SG_ORDER)


# ── RC model fitting on FULL curve ────────────────────────────

def estimate_init(data):
    """Auto-estimate initial parameters from full curve."""
    ul = data['disp_ul']
    vs = data['smooth_V']

    V1_guess = np.median(vs[:min(100, len(vs)//4)])
    V_last   = np.median(vs[-min(100, len(vs)//4):])
    delta_V_guess = V_last - V1_guess

    # jump centre: index of steepest descent/ascent
    grad = np.abs(np.diff(vs))
    mid_idx = np.argmax(grad) + 1
    ul_ep_guess = ul[min(mid_idx, len(ul)-1)]

    # lambda guess: ~1/10 of curve span
    lam_guess = (ul[-1] - ul[0]) / 15.0

    return V1_guess, delta_V_guess, ul_ep_guess, lam_guess


def fit_rc_full(data):
    """Fit RC step-response model to the entire titration curve.

    Hint: V(uL) = V1 + dV * [1 - exp(-(uL - uL_ep) / lambda)]  for uL >= uL_ep
    You need to find the endpoint volume uL_ep by fitting this model.

    Use scipy.optimize.curve_fit with:
        p0 = [V1_guess, delta_V_guess, ul_ep_guess, lam_guess]
        bounds = ([-5, -5, ul_min, 0.01], [5, 5, ul_max, 200])

    The estimate_init() function can provide initial guesses.
    """
    raise NotImplementedError(
        "Students must implement the RC step-response curve_fit "
        "to locate the titration endpoint volume."
    )

    # Return a dict with:
    # 'V1', 'delta_V', 'ul_ep', 'lam', 'R2', 'residuals'
    # and corresponding '_err' entries from pcov


# ── Concentration / hardness ──────────────────────────────────

def calc_MgSO4_concentration(ul_ep):
    """Calculate MgSO4 concentration from EDTA endpoint volume."""
    ul_ep_ml = ul_ep / 1000.0
    total_edta_ml = V_PRE_EDTA_ML + ul_ep_ml
    return C_EDTA_NOMINAL * total_edta_ml / V_MGSO4_ML


def calc_water_hardness(ul_ep, c_edta=None):
    """Calculate water hardness in mg/L as CaCO3."""
    if c_edta is None:
        c_edta = C_EDTA_NOMINAL
    ul_ep_ml = ul_ep / 1000.0
    hardness = c_edta * ul_ep_ml * M_CACO3 / (V_TAP_WATER_ML / 1000.0)
    return hardness


# ── Noise analysis ────────────────────────────────────────────

def analyze_noise(data):
    """Estimate RMS noise from the first 200 points (pre-jump baseline)."""
    n = min(200, len(data['raw_V']))
    raw_rms   = np.std(data['raw_V'][:n])
    smooth_rms = np.std(data['smooth_V'][:n])
    return raw_rms, smooth_rms


# ── Plotting ──────────────────────────────────────────────────

def plot_titration(data, result, title, png_path):
    """Titration curve + RC fit + residuals."""
    ul = data['disp_ul']
    raw_V = data['raw_V']
    smooth_V = data['smooth_V']

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(7, 5),
        gridspec_kw={'height_ratios': [3, 1]},
        sharex=True,
    )

    # ── Main: raw + smooth + RC fit ──
    ax1.plot(ul, raw_V, '-', color='gray', alpha=0.25, lw=0.5, label='raw')
    ax1.plot(ul, smooth_V, '-', color='tab:blue', lw=1.0, label='smooth (SG)')

    if result is not None:
        v_fit = rc_step_response(ul, result['V1'], result['delta_V'],
                                 result['ul_ep'], result['lam'])
        ax1.plot(ul, v_fit, '--', color='tab:red', lw=1.5,
                 label=f'RC fit  (lambda={result["lam"]:.1f} uL, R²={result["R2"]:.4f})')
        # Endpoint marker
        y_ep = rc_step_response(result['ul_ep'],
                                result['V1'], result['delta_V'],
                                result['ul_ep'], result['lam'])
        ax1.axvline(result['ul_ep'], color='tab:red', lw=0.8, ls=':')
        ax1.annotate(
            f'V_ep = {result["ul_ep"]:.1f} +/- {result["ul_ep_err"]:.1f} uL',
            xy=(result['ul_ep'], y_ep),
            xytext=(result['ul_ep'] + 20, y_ep - 0.06),
            arrowprops=dict(arrowstyle='->', color='tab:red', lw=0.8),
            fontsize=9, color='tab:red',
        )

    # Baseline highlight
    n_base = min(200, len(ul))
    ax1.axvspan(0, ul[n_base-1], alpha=0.05, color='green', label='baseline')

    ax1.set_ylabel('Voltage (V)')
    ax1.set_title(title)
    ax1.legend(loc='upper left', framealpha=0.9)
    ax1.grid(True, alpha=0.3)

    # ── Residuals ──
    if result is not None:
        res = result['residuals']
        ax2.plot(ul, res, '.', color='tab:red', ms=1.5, alpha=0.4)
        ax2.axhline(0, color='gray', lw=0.5)
        ax2.set_ylabel('Residual (V)')
        ax2.set_xlabel('Volume (uL)')
        ax2.grid(True, alpha=0.3)
        rms_res = np.std(res)
        ax2.text(0.98, 0.85, f'RMS = {rms_res:.4f} V',
                 transform=ax2.transAxes, ha='right', fontsize=8,
                 bbox=dict(facecolor='white', alpha=0.7, pad=1))
    else:
        ax2.set_xlabel('Volume (uL)')

    plt.tight_layout()
    plt.savefig(png_path, dpi=200)
    print(f"  Figure saved: {png_path}")
    plt.close()


# ── Per-file processing ───────────────────────────────────────

def process_file(csv_path, label, output_dir='figures'):
    """Process a single titration CSV and return fit result."""
    print(f"\n{'='*60}")
    print(f"  File: {label}")
    print(f"  Path: {csv_path}")

    data = load_titration_csv(csv_path)
    smooth_raw(data)

    # Noise
    raw_rms, sm_rms = analyze_noise(data)
    print(f"  Baseline noise: raw RMS = {raw_rms:.4f} V,  smooth RMS = {sm_rms:.4f} V")

    # Speed estimate
    dt = np.diff(data['time_s'])
    dv = np.diff(data['disp_ul'])
    mask = dt > 1e-6
    speed_ul_per_s = np.mean(dv[mask] / dt[mask])
    print(f"  Dispense speed: {speed_ul_per_s:.2f} uL/s")

    # Fit RC model on full curve
    result = fit_rc_full(data)
    if result is None:
        print("  [SKIP] Fit failed.")
        return None

    print(f"  Results:")
    print(f"    V1     = {result['V1']:.4f} +/- {result['V1_err']:.4f} V")
    print(f"    dV     = {result['delta_V']:.4f} +/- {result['delta_V_err']:.4f} V")
    print(f"    V_ep   = {result['ul_ep']:.2f} +/- {result['ul_ep_err']:.2f} uL")
    print(f"    lambda = {result['lam']:.2f} +/- {result['lam_err']:.2f} uL")
    print(f"    R2     = {result['R2']:.6f}")

    # tau (time constant) = lambda / speed
    tau = result['lam'] / speed_ul_per_s if speed_ul_per_s > 0 else np.nan
    print(f"    tau    = {tau:.3f} s  (lambda / speed)")

    # Plot
    os.makedirs(output_dir, exist_ok=True)
    safe = label.replace(' ', '_').replace('/', '_').replace('.', '')
    png = os.path.join(output_dir, f'{safe}.png')
    plot_titration(data, result, label, png)

    return result


def summary_table(results):
    """Print summary table of all results."""
    print("\n\n" + "="*90)
    print("SUMMARY")
    print("="*90)
    hdr = f"{'Experiment':<35} {'V_ep (uL)':<22} {'lambda (uL)':<15} {'R²':<10} {'Concentration'}"
    print(hdr)
    print("-"*90)

    for label, (res, _) in results.items():
        if res is None:
            print(f"{label:<35} {'fit failed':<22}")
            continue
        ep = res['ul_ep']
        ep_err = res['ul_ep_err']
        lam = res['lam']
        r2 = res['R2']

        if 'tap' in label.lower():
            val = calc_water_hardness(ep)
            val_str = f"{val:.1f} mg/L CaCO3"
        else:
            c = calc_MgSO4_concentration(ep)
            val_str = f"{c:.5f} mol/L"

        print(f"{label:<35} {ep:<8.2f} +/- {ep_err:<5.2f}   {lam:<8.2f} +/- {res['lam_err']:<.2f}   {r2:<8.4f}   {val_str}")


# ── File list ─────────────────────────────────────────────────

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = [
    # ── Uncalibrated MgSO4 samples (no practical use without calibration) ──
    ('titration_20260612_185236_not_calibrated.csv',
     'MgSO4 uncalibrated #3 (185236)'),
    ('titration_20260612_181620_not_calibrated.csv',
     'MgSO4 uncalibrated #1 (181620)'),
    ('titration_20260612_181720_not_calibrated.csv',
     'MgSO4 uncalibrated #2 (181720)'),
]

# ── Main ──────────────────────────────────────────────────────

def plot_overlay(results):
    """Overlay all MgSO4 titration curves."""
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:purple']
    idx = 0
    for label, (res, fpath) in results.items():
        if 'tap' in label.lower():
            continue
        data = load_titration_csv(fpath)
        smooth_raw(data)
        ax.plot(data['disp_ul'], data['smooth_V'], '-',
                color=colors[idx % len(colors)], lw=1.0, label=label)
        if res is not None:
            ax.axvline(res['ul_ep'], color=colors[idx % len(colors)], lw=0.6, ls='--')
        idx += 1

    ax.set_xlabel('Volume (uL)')
    ax.set_ylabel('Voltage (V)')
    ax.set_title('MgSO4 calibration titration curves')
    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('figures/all_MgSO4_overlay.png', dpi=200)
    print("\n  Overlay saved: figures/all_MgSO4_overlay.png")
    plt.close()


def plot_noise_comparison(results):
    """Baseline noise comparison for the first file."""
    first_label = list(results.keys())[0]
    _, fpath = results[first_label]
    if not fpath:
        return
    data = load_titration_csv(fpath)
    smooth_raw(data)
    n = min(300, len(data['raw_V']))
    ul_base = data['disp_ul'][:n]

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.plot(ul_base, data['raw_V'][:n], '-', color='gray', alpha=0.4, lw=0.6, label='raw')
    ax.plot(ul_base, data['smooth_V'][:n], '-', color='tab:blue', lw=1.0,
            label=f'smooth (SG {SG_WINDOW})')
    ax.set_xlabel('Volume (uL)')
    ax.set_ylabel('Voltage (V)')
    ax.set_title(f'Baseline noise — {first_label}')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3)

    raw_rms = np.std(data['raw_V'][:n])
    sm_rms = np.std(data['smooth_V'][:n])
    ax.text(0.98, 0.15,
            f'raw RMS = {raw_rms:.4f} V\nsmooth RMS = {sm_rms:.4f} V',
            transform=ax.transAxes, ha='right', fontsize=9, va='bottom',
            bbox=dict(facecolor='white', alpha=0.7, pad=2))
    plt.tight_layout()
    plt.savefig('figures/noise_comparison.png', dpi=200)
    print("  Noise comparison saved: figures/noise_comparison.png")
    plt.close()


def main():
    os.makedirs('figures', exist_ok=True)

    results = OrderedDict()
    for fname, label in FILES:
        fpath = os.path.join(DATA_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  File not found, skip: {fpath}")
            continue
        res = process_file(fpath, label)
        results[label] = (res, fpath)

    summary_table(results)
    plot_overlay(results)
    plot_noise_comparison(results)


if __name__ == '__main__':
    main()
