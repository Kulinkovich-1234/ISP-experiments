# -*- coding: utf-8 -*-
"""
Spectral Detail Viewer
- Load one or more *_aligned_scaled_norm.csv files
- Load an optional reference spectrum (CSV: wavelength, intensity or R,G,B)
- Display RGB curves and reference curve
- Interactive zoom (mouse wheel / toolbar) + button to zoom to 540-550 nm
- Save zoomed view as PNG
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from tkinter import filedialog, Tk
import tkinter as tk


def select_files(title, filetypes):
    """Open file dialog to select multiple files."""
    root = Tk()
    root.withdraw()
    files = filedialog.askopenfilenames(title=title, filetypes=filetypes)
    root.destroy()
    return list(files)


def load_spectrum_csv(filepath):
    """
    Load CSV file with columns: wavelength, R, G, B (header expected).
    Returns dict: {'x': array, 'R': array, 'G': array, 'B': array}
    """
    data = np.loadtxt(filepath, delimiter=',', skiprows=1)
    if data.shape[1] == 2:
        # Single channel: treat as intensity for all RGB (display as black)
        x = data[:, 0]
        intensity = data[:, 1]
        return {'x': x, 'R': intensity, 'G': intensity, 'B': intensity, 'single': True}
    elif data.shape[1] >= 4:
        x = data[:, 0]
        R = data[:, 1]
        G = data[:, 2]
        B = data[:, 3]
        return {'x': x, 'R': R, 'G': G, 'B': B, 'single': False}
    else:
        raise ValueError(f"Unexpected column count in {filepath}: {data.shape[1]}")


def main():
    print("=== Spectral Detail Viewer (Zoom to 540-550 nm) ===")
    
    # Step 1: select main csv files
    main_files = select_files("Select one or more *_aligned_scaled_norm.csv files",
                              [("CSV files", "*.csv")])
    if not main_files:
        print("No main files selected. Exiting.")
        return
    
    # Step 2: optionally select reference file
    load_ref = input("Load reference spectrum? (y/n): ").strip().lower()
    ref_data = None
    if load_ref == 'y':
        ref_files = select_files("Select reference CSV (wavelength, intensity or R,G,B)",
                                 [("CSV files", "*.csv")])
        if ref_files:
            ref_data = load_spectrum_csv(ref_files[0])
            print(f"Reference loaded: {os.path.basename(ref_files[0])}")
    
    # Step 3: load main data
    main_data = []
    for f in main_files:
        try:
            data = load_spectrum_csv(f)
            main_data.append({'path': f, 'data': data})
            print(f"Loaded: {os.path.basename(f)}")
        except Exception as e:
            print(f"Error loading {f}: {e}")
    
    if not main_data:
        print("No valid main data.")
        return
    
    # Step 4: create plot
    fig, ax = plt.subplots(figsize=(12, 6))
    plt.subplots_adjust(bottom=0.15)
    
    # Colors for main curves (each file uses own R,G,B lines)
    # Use solid lines for R,G,B per file; different files get different alpha or linewidth?
    # For clarity, use different alpha values per file.
    alphas = np.linspace(0.5, 1.0, len(main_data)) if len(main_data) > 1 else [0.8]
    
    for idx, m in enumerate(main_data):
        d = m['data']
        name = os.path.splitext(os.path.basename(m['path']))[0]
        alpha = alphas[idx % len(alphas)]
        ax.plot(d['x'], d['R'], color='red', linestyle='-', linewidth=1.5,
                alpha=alpha, label=f"{name} R")
        ax.plot(d['x'], d['G'], color='green', linestyle='-', linewidth=1.5,
                alpha=alpha, label=f"{name} G")
        ax.plot(d['x'], d['B'], color='blue', linestyle='-', linewidth=1.5,
                alpha=alpha, label=f"{name} B")
    
    # Draw reference if provided
    if ref_data:
        if ref_data.get('single', False):
            ax.plot(ref_data['x'], ref_data['R'], color='black', linestyle='--',
                    linewidth=2, label='Reference (intensity)', alpha=0.9)
        else:
            ax.plot(ref_data['x'], ref_data['R'], color='red', linestyle='--',
                    linewidth=2, label='Reference R', alpha=0.9)
            ax.plot(ref_data['x'], ref_data['G'], color='green', linestyle='--',
                    linewidth=2, label='Reference G', alpha=0.9)
            ax.plot(ref_data['x'], ref_data['B'], color='blue', linestyle='--',
                    linewidth=2, label='Reference B', alpha=0.9)
    
    ax.set_xlabel("Wavelength (nm)")
    ax.set_ylabel("Normalized Intensity")
    ax.set_title("Spectral Curves (Aligned & Scaled)")
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend(fontsize=8, loc='best')
    
    # Add button to zoom to 540-550 nm
    ax_button = plt.axes([0.7, 0.02, 0.2, 0.06])
    btn_zoom = Button(ax_button, "Zoom 540-550 nm")
    
    def zoom_to_540_550(event):
        ax.set_xlim(540, 550)
        # optionally auto-scale y within this x range
        # collect y data in this range
        y_min, y_max = np.inf, -np.inf
        for m in main_data:
            d = m['data']
            mask = (d['x'] >= 540) & (d['x'] <= 550)
            if np.any(mask):
                y_min = min(y_min, np.min(d['R'][mask]), np.min(d['G'][mask]), np.min(d['B'][mask]))
                y_max = max(y_max, np.max(d['R'][mask]), np.max(d['G'][mask]), np.max(d['B'][mask]))
        if ref_data:
            mask_ref = (ref_data['x'] >= 540) & (ref_data['x'] <= 550)
            if np.any(mask_ref):
                y_min = min(y_min, np.min(ref_data['R'][mask_ref]), np.min(ref_data['G'][mask_ref]), np.min(ref_data['B'][mask_ref]))
                y_max = max(y_max, np.max(ref_data['R'][mask_ref]), np.max(ref_data['G'][mask_ref]), np.max(ref_data['B'][mask_ref]))
        if np.isfinite(y_min) and np.isfinite(y_max):
            y_margin = (y_max - y_min) * 0.05
            if y_margin == 0:
                y_margin = 0.1
            ax.set_ylim(y_min - y_margin, y_max + y_margin)
        fig.canvas.draw_idle()
    
    btn_zoom.on_clicked(zoom_to_540_550)
    
    # Add reset view button
    ax_reset = plt.axes([0.5, 0.02, 0.15, 0.06])
    btn_reset = Button(ax_reset, "Reset View")
    def reset_view(event):
        ax.autoscale_view()
        ax.set_xlim(None, None)
        ax.set_ylim(None, None)
        fig.canvas.draw_idle()
    btn_reset.on_clicked(reset_view)
    
    # Instructions
    print("\nInteractive controls:")
    print("- Use mouse wheel or toolbar zoom/pan to explore.")
    print("- Click 'Zoom 540-550 nm' to focus on the specified range.")
    print("- Click 'Reset View' to see full range.")
    print("- Close the figure window to exit.")
    
    plt.show()
    
    # Optional save zoomed view
    save_choice = input("\nSave current view as PNG? (y/n): ").strip().lower()
    if save_choice == 'y':
        save_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")],
            title="Save zoomed view as"
        )
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Saved: {save_path}")


if __name__ == "__main__":
    main()