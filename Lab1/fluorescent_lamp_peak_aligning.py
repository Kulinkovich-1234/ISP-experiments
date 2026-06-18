# -*- coding: utf-8 -*-
"""
Simplified Spectral Image Alignment Tool
- Each image has its own subplot (RGB curves)
- Click on any curve to pick a peak (auto channel detection)
- Align by common peak names using first image as reference
- No channel selection / visibility toggles
- No RGB strip display
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
from matplotlib.gridspec import GridSpec
from tkinter import filedialog, Tk
import cv2
from scipy.interpolate import interp1d

plt.ion()


def select_image_files():
    """Open file dialog to select multiple spectrum images."""
    root = Tk()
    root.withdraw()
    file_paths = filedialog.askopenfilenames(
        title="Select Fluorescent Lamp Spectrum Images",
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tif")]
    )
    root.destroy()
    return list(file_paths)


def extract_line_rgb(image_path, num_points=1000):
    """
    Draw a line on image, extract RGB along it, and return RGB data.
    Returns:
        distances: 1D array of cumulative distances (pixels)
        rgb_values: (num_points, 3) array
    """
    img = cv2.imread(image_path)
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    height, width = img_rgb.shape[:2]

    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(img_rgb)
    ax.set_title("Draw sampling line (click start -> end), then press any key")
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
    t = np.linspace(0, 1, num_points)
    line_points = start + t[:, np.newaxis] * (end - start)
    xs = np.clip(line_points[:, 0], 0, width - 1).astype(int)
    ys = np.clip(line_points[:, 1], 0, height - 1).astype(int)
    rgb_values = img_rgb[ys, xs]

    diff = np.diff(line_points, axis=0)
    seg_dist = np.linalg.norm(diff, axis=1)
    distances = np.concatenate(([0], np.cumsum(seg_dist)))
    return distances, rgb_values


def save_raw_data(data_dict, base_dir="output"):
    os.makedirs(base_dir, exist_ok=True)
    for name, info in data_dict.items():
        csv_path = os.path.join(base_dir, f"{name}_raw_rgb.csv")
        header = "distance,R,G,B"
        np.savetxt(csv_path, np.column_stack((info['distances'], info['rgb'])),
                   delimiter=',', header=header, comments='')
        print(f"Raw data saved: {csv_path}")


def plot_raw_curves(data_dict):
    """Show raw RGB curves for all images (legacy preview)."""
    channels = ['R', 'G', 'B']
    for idx, ch in enumerate(channels):
        plt.figure(figsize=(12, 6))
        plt.title(f"Raw Spectral Intensity - {ch} Channel")
        for name, info in data_dict.items():
            plt.plot(info['distances'], info['rgb'][:, idx], label=name, alpha=0.7)
        plt.xlabel("Pixel Distance")
        plt.ylabel("Intensity")
        plt.legend()
        plt.grid(True)
        plt.show(block=True)


def align_interactive(data_dict):
    """
    Simplified alignment: one subplot per image with RGB curves.
    Click on any curve to define a peak (auto channel detection).
    Align using first image as reference.
    """
    if not data_dict:
        return

    all_names = list(data_dict.keys())
    n_images = len(all_names)
    print(f"Images loaded: {all_names}")

    # Raw data
    raw_dist = {name: data_dict[name]['distances'] for name in all_names}
    raw_rgb = {name: data_dict[name]['rgb'] for name in all_names}

    # Alignment parameters (scale, offset) for each image
    params = {name: {'scale': 1.0, 'offset': 0.0} for name in all_names}

    # Peak storage: peaks[name][peak_name] = (raw_x, channel)
    peaks = {name: {} for name in all_names}

    # Reference image (use first as default)
    ref_name = all_names[0]

    # Build figure: subplots for each image, plus bottom buttons
    subplot_height = 2.5  # inches per subplot
    fig_height = max(6, n_images * subplot_height + 1.5)
    fig = plt.figure(figsize=(12, fig_height))

    # Grid for subplots (left 90% width) and a tiny bottom area for buttons
    gs = GridSpec(n_images + 1, 1, height_ratios=[1]*n_images + [0.1],
                  figure=fig, left=0.05, right=0.98, top=0.98, bottom=0.05)
    subplot_axes = []
    for i in range(n_images):
        ax = fig.add_subplot(gs[i, 0])
        ax.set_title(all_names[i])
        ax.set_xlabel("Relative Wavelength (aligned)")
        ax.set_ylabel("Intensity")
        ax.grid(True)
        subplot_axes.append(ax)

    # Button area
    ax_buttons = fig.add_subplot(gs[n_images, 0])
    ax_buttons.axis('off')
    ax_align = plt.axes([0.3, 0.02, 0.2, 0.04])
    ax_reset = plt.axes([0.5, 0.02, 0.2, 0.04])
    btn_align = Button(ax_align, "Align by Peaks (ref: first image)")
    btn_reset = Button(ax_reset, "Reset Alignment")

    # Text area for showing current peaks (simplified)
    ax_peak_text = plt.axes([0.02, 0.02, 0.25, 0.08])
    ax_peak_text.axis('off')
    peak_text = ax_peak_text.text(0.05, 0.95, "Peaks:", fontsize=8, verticalalignment='top')

    # Helper to update all plots with current params and peaks
    def update_all_plots():
        channel_color = {'R': 'red', 'G': 'green', 'B': 'blue'}
        for idx, name in enumerate(all_names):
            ax = subplot_axes[idx]
            ax.clear()
            ax.set_title(name)
            ax.set_xlabel("Relative Wavelength (aligned)")
            ax.set_ylabel("Intensity")
            ax.grid(True)

            scale = params[name]['scale']
            offset = params[name]['offset']
            x_trans = scale * raw_dist[name] + offset
            for ch, col in channel_color.items():
                ch_idx = {'R': 0, 'G': 1, 'B': 2}[ch]
                y = raw_rgb[name][:, ch_idx]
                ax.plot(x_trans, y, color=col, linewidth=1.5, label=ch)

            ax.legend(loc='upper right', fontsize=7)

            # Mark defined peaks
            for peak_name, (raw_x, ch) in peaks[name].items():
                # find transformed x and intensity
                scale_p = params[name]['scale']
                offset_p = params[name]['offset']
                trans_x = scale_p * raw_x + offset_p
                ch_idx = {'R': 0, 'G': 1, 'B': 2}[ch]
                # Find nearest index to raw_x for y value
                idx_close = np.argmin(np.abs(raw_dist[name] - raw_x))
                y_val = raw_rgb[name][idx_close, ch_idx]
                ax.plot(trans_x, y_val, 'ro', markersize=8, markeredgecolor='black')
                ax.annotate(peak_name, (trans_x, y_val), xytext=(5, 5),
                            textcoords='offset points', fontsize=8, fontweight='bold')

        # Update peak text display
        txt = "Peaks (raw x, channel):\n"
        for name in all_names:
            if peaks[name]:
                items = [f"{p}({peaks[name][p][1]})={peaks[name][p][0]:.1f}" for p in peaks[name]]
                txt += f"{name}: " + ", ".join(items) + "\n"
            else:
                txt += f"{name}: none\n"
        peak_text.set_text(txt)
        fig.canvas.draw_idle()

    def on_peak_click(event):
        """Automatically detect which subplot and which channel was clicked."""
        # Find which subplot the click occurred in
        for idx, ax in enumerate(subplot_axes):
            if event.inaxes == ax:
                name = all_names[idx]
                break
        else:
            return  # not in any subplot

        x_click = event.xdata
        if x_click is None:
            return

        # Get current transformed x for this image
        scale = params[name]['scale']
        offset = params[name]['offset']
        trans_x = scale * raw_dist[name] + offset

        # Find closest point index in transformed coordinates
        idx_closest = np.argmin(np.abs(trans_x - x_click))
        closest_raw_x = raw_dist[name][idx_closest]
        x_trans_closest = trans_x[idx_closest]

        # Determine which channel was clicked by comparing vertical distance
        ch_color = {'R': 'red', 'G': 'green', 'B': 'blue'}
        ch_idx = {'R': 0, 'G': 1, 'B': 2}
        best_ch = None
        best_dist = float('inf')
        for ch, col in ch_color.items():
            y_val = raw_rgb[name][idx_closest, ch_idx[ch]]
            dist_y = abs(event.ydata - y_val)
            if dist_y < best_dist:
                best_dist = dist_y
                best_ch = ch
        # Threshold: if vertical distance too large, maybe user missed the curve
        if best_dist > 0.2 * np.max(raw_rgb[name][:, ch_idx[best_ch]]):
            # Not close to any curve, abort
            print("Click too far from any curve, peak not added.")
            return

        # Now ask for peak name
        from matplotlib.widgets import TextBox
        ax_name = plt.axes([0.4, 0.5, 0.2, 0.05])
        text_box = TextBox(ax_name, "Peak name:", initial="")

        def submit(text):
            if text.strip():
                peaks[name][text.strip()] = (closest_raw_x, best_ch)
                print(f"Peak '{text.strip()}' added for {name} ({best_ch}) at raw x={closest_raw_x:.2f}")
                update_all_plots()
            ax_name.remove()
            fig.canvas.draw_idle()
        text_box.on_submit(submit)
        fig.canvas.draw_idle()

    # Connect click event to all subplots
    for ax in subplot_axes:
        ax.figure.canvas.mpl_connect('button_press_event', on_peak_click)

    # Align function (use first image as reference)
    def align_by_peaks(event):
        """
        Align images by matching user-defined peaks to a reference image.

        Hint: For each non-reference image, find the linear mapping from
        its raw pixel coordinates to the reference coordinates:
            x_ref = scale * x_img + offset

        Use np.linalg.lstsq with at least 2 matching peaks to solve for
        scale and offset. If only 1 peak is available, use offset-only alignment.
        """
        raise NotImplementedError(
            "Students must implement the least-squares peak alignment algorithm. "
            "See docstring for the linear mapping formula."
        )

    def reset_alignment(event):
        for name in all_names:
            params[name]['scale'] = 1.0
            params[name]['offset'] = 0.0
        update_all_plots()
        print("Alignment reset to identity.")

    btn_align.on_clicked(align_by_peaks)
    btn_reset.on_clicked(reset_alignment)

    update_all_plots()
    plt.show(block=True)

    # Save parameters
    os.makedirs("output", exist_ok=True)
    param_file = os.path.join("output", "alignment_params.json")
    with open(param_file, 'w') as f:
        json.dump(params, f, indent=2)
    print(f"Parameters saved: {param_file}")

    # Interpolate all spectra to a common x-range
    all_trans_x = []
    for name in all_names:
        x = params[name]['scale'] * raw_dist[name] + params[name]['offset']
        all_trans_x.extend(x)
    global_min = np.min(all_trans_x)
    global_max = np.max(all_trans_x)
    common_x = np.linspace(global_min, global_max, 500)

    aligned_data = {}
    for name in all_names:
        x_orig = params[name]['scale'] * raw_dist[name] + params[name]['offset']
        rgb_orig = raw_rgb[name]
        interp_r = interp1d(x_orig, rgb_orig[:, 0], kind='linear', fill_value="extrapolate")
        interp_g = interp1d(x_orig, rgb_orig[:, 1], kind='linear', fill_value="extrapolate")
        interp_b = interp1d(x_orig, rgb_orig[:, 2], kind='linear', fill_value="extrapolate")
        aligned_data[name] = {
            'x': common_x,
            'R': interp_r(common_x),
            'G': interp_g(common_x),
            'B': interp_b(common_x)
        }
    for name, ad in aligned_data.items():
        csv_path = os.path.join("output", f"{name}_aligned.csv")
        np.savetxt(csv_path, np.column_stack((ad['x'], ad['R'], ad['G'], ad['B'])),
                   delimiter=',', header="wavelength,R,G,B", comments='')
        print(f"Aligned data saved: {csv_path}")

    # Final comparison plots
    plt.figure(figsize=(12, 8))
    for ch, color in zip(['R', 'G', 'B'], ['red', 'green', 'blue']):
        plt.subplot(3, 1, ['R', 'G', 'B'].index(ch)+1)
        for name, ad in aligned_data.items():
            plt.plot(ad['x'], ad[ch], label=name, alpha=0.8)
        plt.title(f"{ch} channel (aligned)")
        plt.xlabel("Relative wavelength")
        plt.ylabel("Intensity")
        plt.legend()
        plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join("output", "final_aligned_curves.png"), dpi=150)
    plt.show(block=True)

    return aligned_data


def main():
    print("=== Simplified Spectral Alignment Tool ===")
    print("Click on any curve to add a peak. First image is reference for alignment.")
    file_paths = select_image_files()
    if not file_paths:
        print("No files selected.")
        return

    data_dict = {}
    for fpath in file_paths:
        name = os.path.splitext(os.path.basename(fpath))[0]
        print(f"\nProcessing: {name}")
        try:
            distances, rgb = extract_line_rgb(fpath)
            data_dict[name] = {'path': fpath, 'distances': distances, 'rgb': rgb}
            print(f"Done. Points: {len(distances)}")
        except Exception as e:
            print(f"Error: {e}")

    if not data_dict:
        print("No valid data.")
        return

    save_raw_data(data_dict)
    plot_raw_curves(data_dict)
    print("\nStarting interactive alignment...")
    align_interactive(data_dict)
    print("\nAll results saved in 'output' folder.")


if __name__ == "__main__":
    main()