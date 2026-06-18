# -*- coding: utf-8 -*-
"""
Spectral Image Extraction & Alignment Tool (Fixed Wavelength Range 200-900 nm)
- Extract RGB along manually drawn line, map pixel distance to 200-900 nm
- Load reference CSV (x in nm, intensity or R,G,B)
- Intensity normalized by max peak per channel
- Interactive alignment with optional scale/offset (small adjustments)
- Scaling anchor at 520 nm (adjust scale without moving 520 nm point)
- Display spectral curves, sampling-line RGB strip, and reference curve

NOTE: This tool performs MANUAL interactive alignment using slider controls.
The wavelength mapping is a simple linear assumption (pixel → nm).
No automatic fitting is performed — you adjust parameters by hand.
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, CheckButtons
from matplotlib.gridspec import GridSpec
from tkinter import filedialog, Tk
import cv2
from scipy.interpolate import interp1d

plt.ion()

# Default wavelength range (nm)
DEFAULT_WL_START = 200.0
DEFAULT_WL_END = 900.0
ANCHOR_WL = 520.0   # 缩放基准波长


def select_image_files():
    root = Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="Select Fluorescent Lamp Spectrum Images",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tif")]
    )
    root.destroy()
    return list(file_paths)


def load_reference_csv():
    """Load reference spectrum from CSV, normalize each channel by its max.
    Supports:
        - 2 columns: x (nm), intensity
        - 4 columns: x (nm), R, G, B
    Returns dict with 'x', 'R', 'G', 'B', and normalization info.
    """
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select reference spectrum CSV file",
        filetypes=[("CSV files", "*.csv")]
    )
    root.destroy()
    if not file_path:
        return None
    data = np.loadtxt(file_path, delimiter=',', skiprows=1)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    ncols = data.shape[1]
    if ncols == 2:
        x = data[:, 0]
        intensity = data[:, 1]
        max_val = float(np.max(intensity)) if np.max(intensity) > 0 else 1.0
        intensity = intensity / max_val
        return {
            'x': x,
            'R': intensity,
            'G': intensity,
            'B': intensity,
            'file': file_path,
            'single_channel': True,
            'norm_factor': max_val
        }
    elif ncols >= 4:
        x = data[:, 0]
        R = data[:, 1]
        G = data[:, 2]
        B = data[:, 3]
        max_R = float(np.max(R)) if np.max(R) > 0 else 1.0
        max_G = float(np.max(G)) if np.max(G) > 0 else 1.0
        max_B = float(np.max(B)) if np.max(B) > 0 else 1.0
        R = R / max_R
        G = G / max_G
        B = B / max_B
        return {
            'x': x,
            'R': R,
            'G': G,
            'B': B,
            'file': file_path,
            'single_channel': False,
            'norm_factor': {'R': max_R, 'G': max_G, 'B': max_B}
        }
    else:
        print("Error: CSV must have 2 columns (x, intensity) or 4 columns (x, R, G, B)")
        return None


def extract_line_rgb(image_path, num_points=1000, wl_range=(DEFAULT_WL_START, DEFAULT_WL_END)):
    """
    Draw a line on image, extract RGB along it.
    Map pixel distance to wavelength linearly: start of line -> wl_range[0], end -> wl_range[1].
    Returns:
        wavelengths: 1D array (nm)
        rgb_values: (num_points, 3) normalized (peak=1 per channel)
        rgb_strip: (num_points, 50, 3) image for display
        norm_factors: dict with max original intensities
    """
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)
    height, width = img_rgb.shape[:2]

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(img_rgb.astype(np.uint8))
    ax.set_title(f"Draw sampling line from left (short λ) to right (long λ)\n"
                 f"Start -> {wl_range[0]} nm, End -> {wl_range[1]} nm\n"
                 "Click start, then end, then press any key")
    points = []

    def on_press(event):
        if event.inaxes != ax:
            return
        points.append((event.xdata, event.ydata))
        if len(points) == 2:
            x0, y0 = points[0]
            x1, y1 = points[1]
            ax.plot([x0, x1], [y0, y1], 'r-', linewidth=2)
            fig.canvas.draw()
            fig.canvas.mpl_disconnect(cid_press)
            plt.waitforbuttonpress()
            plt.close(fig)

    cid_press = fig.canvas.mpl_connect('button_press_event', on_press)
    plt.show(block=True)

    if len(points) != 2:
        raise ValueError("Incomplete line")

    start = np.array(points[0])
    end = np.array(points[1])
    t = np.linspace(0, 1, num_points)   # normalized distance along line
    line_points = start + t[:, np.newaxis] * (end - start)
    xs = np.clip(line_points[:, 0], 0, width - 1).astype(int)
    ys = np.clip(line_points[:, 1], 0, height - 1).astype(int)
    rgb_values = img_rgb[ys, xs]   # shape (num_points, 3)

    # Normalize each channel by its maximum (peak normalization)
    max_R = np.max(rgb_values[:, 0])
    max_G = np.max(rgb_values[:, 1])
    max_B = np.max(rgb_values[:, 2])
    if max_R <= 0:
        max_R = 1.0
    if max_G <= 0:
        max_G = 1.0
    if max_B <= 0:
        max_B = 1.0
    rgb_values[:, 0] = rgb_values[:, 0] / max_R
    rgb_values[:, 1] = rgb_values[:, 1] / max_G
    rgb_values[:, 2] = rgb_values[:, 2] / max_B

    norm_factors = {'R': float(max_R), 'G': float(max_G), 'B': float(max_B)}

    # Map normalized distance to wavelength range
    wavelengths = wl_range[0] + t * (wl_range[1] - wl_range[0])

    # Create RGB strip image (scaled to 0-255 for display)
    strip_height = 50
    rgb_display = (rgb_values * 255).astype(np.uint8)
    rgb_strip = np.repeat(rgb_display[np.newaxis, :, :], strip_height, axis=0)

    return wavelengths, rgb_values, rgb_strip, norm_factors


def save_raw_data(data_dict, base_dir="output"):
    """Save normalized RGB data with wavelength (nm) to CSV."""
    os.makedirs(base_dir, exist_ok=True)
    for name, info in data_dict.items():
        csv_path = os.path.join(base_dir, f"{name}_normalized_rgb.csv")
        header = "wavelength_nm,R_norm,G_norm,B_norm"
        np.savetxt(csv_path, np.column_stack((info['wavelengths'], info['rgb'])),
                   delimiter=',', header=header, comments='')
        print(f"Normalized data saved: {csv_path}")
        # Save normalization factors
        norm_path = os.path.join(base_dir, f"{name}_norm_factors.json")
        with open(norm_path, 'w') as f:
            json.dump(info['norm_factors'], f, indent=2)
        print(f"Norm factors saved: {norm_path}")


def plot_raw_curves(data_dict):
    """Show normalized raw RGB curves vs wavelength (nm)."""
    channels = ['R', 'G', 'B']
    for idx, ch in enumerate(channels):
        plt.figure(figsize=(12, 6))
        plt.title(f"Normalized Spectral Intensity - {ch} Channel (peak = 1)")
        for name, info in data_dict.items():
            plt.plot(info['wavelengths'], info['rgb'][:, idx], label=name, alpha=0.7)
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Normalized Intensity")
        plt.legend()
        plt.grid(True)
        plt.show(block=True)


def align_interactive(data_dict, ref_data=None):
    if not data_dict:
        return

    all_names = list(data_dict.keys())
    print(f"Images loaded: {all_names}")
    print(f"缩放基准点: {ANCHOR_WL} nm (该波长在调整 Scale 时位置不变)")

    raw_wl = {name: data_dict[name]['wavelengths'] for name in all_names}
    raw_rgb = {name: data_dict[name]['rgb'] for name in all_names}
    raw_strip = {name: data_dict[name]['strip'] for name in all_names}

    # Parameters for each image (scale, offset for wavelength, intensity multiplier)
    # Transformation: x = ANCHOR_WL + scale * (x_raw - ANCHOR_WL) + offset
    params = {name: {'scale': 1.0, 'offset': 0.0, 'intensity': 1.0} for name in all_names}

    channel_visible = {'R': True, 'G': True, 'B': True}
    image_visible = {name: True for name in all_names}
    current_strip_name = all_names[0]

    ref_visible = True if ref_data is not None else False

    fig = plt.figure(figsize=(16, 10))
    gs_left = GridSpec(2, 1, figure=fig, left=0.05, right=0.55, top=0.95, bottom=0.05, hspace=0.3)
    ax_curves = fig.add_subplot(gs_left[0, 0])
    ax_curves.set_title(f"Spectral Curves (Peak Normalized, scaling anchor = {ANCHOR_WL} nm)")
    ax_curves.set_xlabel("Wavelength (nm)")
    ax_curves.set_ylabel("Normalized Intensity")
    ax_curves.grid(True)

    ax_strip = fig.add_subplot(gs_left[1, 0])
    ax_strip.set_title("RGB Strip of Selected Image")
    ax_strip.axis('off')

    n_images = len(all_names)
    total_control_rows = n_images * 4 + 3
    control_height_per_row = 0.035
    needed_height = control_height_per_row * total_control_rows
    if needed_height > 8:
        fig.set_size_inches(16, max(10, needed_height + 2))

    ax_right = fig.add_axes([0.58, 0.05, 0.4, 0.9])
    ax_right.axis('off')
    ax_right.set_title("Controls", fontsize=12)

    channel_check_ax = plt.axes([0.60, 0.88, 0.35, 0.08])
    channel_check = CheckButtons(channel_check_ax, ['R', 'G', 'B'], [True, True, True])

    image_check_ax = plt.axes([0.60, 0.78, 0.35, 0.10])
    image_check = CheckButtons(image_check_ax, all_names, [True]*n_images)

    ref_check_ax = None
    if ref_data is not None:
        ref_check_ax = plt.axes([0.60, 0.72, 0.35, 0.05])
        ref_check = CheckButtons(ref_check_ax, ['Show Reference'], [True])
        start_y = 0.66
    else:
        start_y = 0.72

    step_y = 0.04
    intensity_sliders = {}
    scale_sliders = {}
    offset_sliders = {}

    for i, name in enumerate(all_names):
        y = start_y - i * (step_y * 3.5)
        if y < 0.1:
            break
        fig.text(0.61, y + 0.025, name, fontsize=9, weight='bold')
        ax_int = plt.axes([0.62, y - 0.01, 0.32, 0.02])
        s_int = Slider(ax_int, "Intensity", 0.0, 2.0, valinit=params[name]['intensity'], valfmt='%.2f')
        ax_sca = plt.axes([0.62, y - 0.04, 0.32, 0.02])
        s_sca = Slider(ax_sca, "Wavelength Scale", 0.3, 2.0, valinit=params[name]['scale'], valfmt='%.3f')
        ax_off = plt.axes([0.62, y - 0.07, 0.32, 0.02])
        s_off = Slider(ax_off, "Wavelength Offset", -200, 200, valinit=params[name]['offset'], valfmt='%.1f')

        intensity_sliders[name] = s_int
        scale_sliders[name] = s_sca
        offset_sliders[name] = s_off

    reset_ax = plt.axes([0.62, 0.02, 0.25, 0.05])
    btn_reset = Button(reset_ax, "Reset All Parameters")

    # Add informational text on right panel
    fig.text(0.62, 0.95, "Click image checkbox to view its RGB strip", fontsize=8, style='italic')
    if ref_data is not None:
        fig.text(0.62, 0.71, f"Scaling anchor: {ANCHOR_WL} nm", fontsize=8, style='italic')
        fig.text(0.62, 0.68, "Reference spectrum (dashed, normalized)", fontsize=8, style='italic')
    else:
        fig.text(0.62, 0.71, f"Scaling anchor: {ANCHOR_WL} nm", fontsize=8, style='italic')

    def update_curves():
        ax_curves.clear()
        ax_curves.set_title(f"Spectral Curves (Peak Normalized, anchor={ANCHOR_WL} nm)")
        ax_curves.set_xlabel("Wavelength (nm)")
        ax_curves.set_ylabel("Normalized Intensity")
        ax_curves.grid(True)

        visible_channels = [ch for ch, vis in channel_visible.items() if vis]
        if not visible_channels:
            visible_channels = ['R']
        channel_color = {'R': 'red', 'G': 'green', 'B': 'blue'}

        # Draw reference spectrum (if visible and loaded)
        if ref_data is not None and ref_visible:
            if ref_data.get('single_channel', False):
                ax_curves.plot(ref_data['x'], ref_data['R'],
                               color='black', linestyle='--', linewidth=2,
                               alpha=0.9, label='Reference (norm)')
            else:
                for ch in visible_channels:
                    ax_curves.plot(ref_data['x'], ref_data[ch],
                                   color=channel_color[ch], linestyle='--', linewidth=2,
                                   alpha=0.9, label=f"Ref {ch}" if ch == visible_channels[0] else "")

        for name in all_names:
            if not image_visible[name]:
                continue
            scale = params[name]['scale']
            offset = params[name]['offset']
            # Transform with anchor at ANCHOR_WL
            x = ANCHOR_WL + scale * (raw_wl[name] - ANCHOR_WL) + offset
            intensity = params[name]['intensity']
            for ch in visible_channels:
                idx = {'R':0, 'G':1, 'B':2}[ch]
                y = raw_rgb[name][:, idx] * intensity
                ax_curves.plot(x, y, color=channel_color[ch], linestyle='-',
                               linewidth=1.5, alpha=0.7,
                               label=f"{name} {ch}" if ch == visible_channels[0] else "")

        handles, labels = ax_curves.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        ax_curves.legend(unique.values(), unique.keys(), fontsize=7, loc='upper right')
        fig.canvas.draw_idle()

    def update_strip():
        ax_strip.clear()
        ax_strip.set_title(f"RGB Strip: {current_strip_name}")
        strip_img = raw_strip[current_strip_name]
        ax_strip.imshow(strip_img, aspect='auto')
        ax_strip.axis('off')
        fig.canvas.draw_idle()

    def channel_clicked(label):
        channel_visible[label] = not channel_visible[label]
        update_curves()

    def image_clicked(label):
        image_visible[label] = not image_visible[label]
        if image_visible[label]:
            nonlocal current_strip_name
            current_strip_name = label
            update_strip()
        update_curves()

    def ref_clicked(label):
        nonlocal ref_visible
        ref_visible = not ref_visible
        update_curves()

    def intensity_changed(val, name):
        params[name]['intensity'] = val
        update_curves()

    def scale_changed(val, name):
        params[name]['scale'] = val
        update_curves()

    def offset_changed(val, name):
        params[name]['offset'] = val
        update_curves()

    def reset_all(event):
        for name in all_names:
            params[name]['scale'] = 1.0
            params[name]['offset'] = 0.0
            params[name]['intensity'] = 1.0
            scale_sliders[name].set_val(1.0)
            offset_sliders[name].set_val(0.0)
            intensity_sliders[name].set_val(1.0)
        for ch in ['R','G','B']:
            channel_visible[ch] = True
        for name in all_names:
            image_visible[name] = True
        nonlocal current_strip_name
        current_strip_name = all_names[0]
        update_curves()
        update_strip()

    channel_check.on_clicked(channel_clicked)
    image_check.on_clicked(image_clicked)
    if ref_check_ax is not None:
        ref_check.on_clicked(ref_clicked)
    for name in all_names:
        intensity_sliders[name].on_changed(lambda val, n=name: intensity_changed(val, n))
        scale_sliders[name].on_changed(lambda val, n=name: scale_changed(val, n))
        offset_sliders[name].on_changed(lambda val, n=name: offset_changed(val, n))
    btn_reset.on_clicked(reset_all)

    update_curves()
    update_strip()
    plt.show(block=True)

    # Save final parameters
    param_file = os.path.join("output", "alignment_params.json")
    with open(param_file, 'w') as f:
        json.dump(params, f, indent=2)
    print(f"Parameters saved: {param_file}")

    # Interpolate aligned data onto a common wavelength grid
    all_x = []
    for name in all_names:
        x = ANCHOR_WL + params[name]['scale'] * (raw_wl[name] - ANCHOR_WL) + params[name]['offset']
        all_x.extend(x)
    global_min = np.min(all_x)
    global_max = np.max(all_x)
    if ref_data is not None:
        ref_min = np.min(ref_data['x'])
        ref_max = np.max(ref_data['x'])
        global_min = min(global_min, ref_min)
        global_max = max(global_max, ref_max)
    common_x = np.linspace(global_min, global_max, 500)

    aligned_data = {}
    for name in all_names:
        x_orig = ANCHOR_WL + params[name]['scale'] * (raw_wl[name] - ANCHOR_WL) + params[name]['offset']
        mult = params[name]['intensity']
        rgb_orig = raw_rgb[name] * mult
        interp_r = interp1d(x_orig, rgb_orig[:,0], kind='linear', fill_value="extrapolate")
        interp_g = interp1d(x_orig, rgb_orig[:,1], kind='linear', fill_value="extrapolate")
        interp_b = interp1d(x_orig, rgb_orig[:,2], kind='linear', fill_value="extrapolate")
        aligned_data[name] = {
            'x': common_x,
            'R': interp_r(common_x),
            'G': interp_g(common_x),
            'B': interp_b(common_x)
        }
        csv_path = os.path.join("output", f"{name}_aligned_scaled_norm.csv")
        np.savetxt(csv_path, np.column_stack((common_x, aligned_data[name]['R'],
                                              aligned_data[name]['G'], aligned_data[name]['B'])),
                   delimiter=',', header="wavelength_nm,R_norm,G_norm,B_norm", comments='')
        print(f"Aligned+scaled normalized data saved: {csv_path}")

    # Final per-channel comparison plots (including reference)
    plt.figure(figsize=(12, 8))
    ch_names = ['R', 'G', 'B']
    ch_colors = ['red', 'green', 'blue']
    for idx, (ch, color) in enumerate(zip(ch_names, ch_colors)):
        plt.subplot(3, 1, idx+1)
        for name, ad in aligned_data.items():
            plt.plot(ad['x'], ad[ch], label=name, alpha=0.8)
        if ref_data is not None:
            if ref_data.get('single_channel', False):
                plt.plot(ref_data['x'], ref_data['R'], '--', color='black', linewidth=2,
                         label='Reference (norm)', alpha=0.9)
            else:
                plt.plot(ref_data['x'], ref_data[ch], '--', color=color, linewidth=2,
                         label=f'Reference {ch} (norm)', alpha=0.9)
        plt.title(f"{ch} channel (peak normalized, aligned to nm, anchor={ANCHOR_WL})")
        plt.xlabel("Wavelength (nm)")
        plt.ylabel("Normalized Intensity")
        plt.legend()
        plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join("output", "final_aligned_scaled_norm_curves.png"), dpi=150)
    plt.show(block=True)

    return aligned_data


def main():
    print("=== Spectral Image Extraction & Alignment Tool (Fixed Wavelength Range 200-900 nm) ===")
    file_paths = select_image_files()
    if not file_paths:
        print("No files selected.")
        return

    data_dict = {}
    for fpath in file_paths:
        name = os.path.splitext(os.path.basename(fpath))[0]
        print(f"\nProcessing: {name}")
        try:
            wavelengths, rgb_norm, strip, norm_factors = extract_line_rgb(fpath)
            data_dict[name] = {
                'path': fpath,
                'wavelengths': wavelengths,
                'rgb': rgb_norm,
                'strip': strip,
                'norm_factors': norm_factors
            }
            print(f"Done. Points: {len(wavelengths)}. Norm factors: R={norm_factors['R']:.1f}, G={norm_factors['G']:.1f}, B={norm_factors['B']:.1f}")
            print(f"Wavelength range: {wavelengths[0]:.1f} - {wavelengths[-1]:.1f} nm")
        except Exception as e:
            print(f"Error: {e}")

    if not data_dict:
        print("No valid data.")
        return

    save_raw_data(data_dict)
    plot_raw_curves(data_dict)

    ref_data = None
    load_ref = input("\nLoad a reference spectrum from CSV? (y/n): ").strip().lower()
    if load_ref == 'y':
        ref_data = load_reference_csv()
        if ref_data is None:
            print("No reference spectrum loaded.")
        else:
            print(f"Reference spectrum loaded: {ref_data['file']}")
            if ref_data.get('single_channel', False):
                print("Detected single-channel (intensity) reference. Normalized to peak=1.")
            else:
                print("Detected RGB reference. Each channel normalized to peak=1.")

    print("\nStarting interactive alignment...")
    align_interactive(data_dict, ref_data)
    print("\nAll results saved in 'output' folder.")


if __name__ == "__main__":
    main()