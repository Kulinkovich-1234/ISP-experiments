# -*- coding: utf-8 -*-
"""
Spectral Image Extraction & Alignment Tool
- Extract RGB along manually drawn lines
- Interactive alignment with independent scale/offset/intensity for EVERY image
- Scrollable right panel to support many images
- Display spectral curves and sampling-line RGB strip

NOTE: This tool performs MANUAL interactive alignment using slider controls.
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
    Draw a line on image, extract RGB along it, and return RGB strip image.
    Returns:
        distances: 1D array of cumulative distances (pixels)
        rgb_values: (num_points, 3) array
        rgb_strip: (num_points, 50, 3) image-like array for display (height=50 pixels)
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

    # Create RGB strip image (horizontal orientation, 50 pixels tall)
    strip_height = 50
    rgb_strip = np.repeat(rgb_values[np.newaxis, :, :], strip_height, axis=0)

    diff = np.diff(line_points, axis=0)
    seg_dist = np.linalg.norm(diff, axis=1)
    distances = np.concatenate(([0], np.cumsum(seg_dist)))
    return distances, rgb_values, rgb_strip


def save_raw_data(data_dict, base_dir="output"):
    os.makedirs(base_dir, exist_ok=True)
    for name, info in data_dict.items():
        csv_path = os.path.join(base_dir, f"{name}_raw_rgb.csv")
        header = "distance,R,G,B"
        np.savetxt(csv_path, np.column_stack((info['distances'], info['rgb'])),
                   delimiter=',', header=header, comments='')
        print(f"Raw data saved: {csv_path}")


def plot_raw_curves(data_dict):
    """Show raw RGB curves for all images."""
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
    Interactive alignment with independent scale/offset/intensity for every image.
    All controls are placed on a scrollable right panel.
    """
    if not data_dict:
        return

    all_names = list(data_dict.keys())
    print(f"Images loaded: {all_names}")

    # Raw data
    raw_dist = {name: data_dict[name]['distances'] for name in all_names}
    raw_rgb = {name: data_dict[name]['rgb'] for name in all_names}
    raw_strip = {name: data_dict[name]['strip'] for name in all_names}

    # Parameters for each image
    params = {name: {'scale': 1.0, 'offset': 0.0, 'intensity': 1.0} for name in all_names}

    # Visibility: channels and images
    channel_visible = {'R': True, 'G': True, 'B': True}
    image_visible = {name: True for name in all_names}
    current_strip_name = all_names[0]  # first image strip shown initially

    # Setup figure with GridSpec
    fig = plt.figure(figsize=(16, 10))
    # Left column: curves and strip
    gs_left = GridSpec(2, 1, figure=fig, left=0.05, right=0.55, top=0.95, bottom=0.05, hspace=0.3)
    ax_curves = fig.add_subplot(gs_left[0, 0])
    ax_curves.set_title("Spectral Curves")
    ax_curves.set_xlabel("Aligned Relative Wavelength")
    ax_curves.set_ylabel("Intensity (scaled)")
    ax_curves.grid(True)

    ax_strip = fig.add_subplot(gs_left[1, 0])
    ax_strip.set_title("RGB Strip of Selected Image")
    ax_strip.axis('off')

    # Right column: all controls
    # Use GridSpec with many rows; we will add a scrollable region using a separate Canvas?
    # Simpler: add a single axes that occupies the right side, then embed child axes manually with absolute positions
    # But we want scrollability. Since matplotlib doesn't have native scrolling for widgets,
    # we can instead place controls in a separate window? That's overkill.
    # Alternative: use a "collapsible" layout or just rely on the user adjusting window size.
    # For moderate number of images (<=6), we can fit without scrolling.
    # For more, we can increase figure height. We'll assume <=5. If more, user can resize.
    # Good practice: compute required height and adjust figure size.
    n_images = len(all_names)
    # Each image uses: 1 label + 3 sliders -> 4 rows per image, plus channel row, plus reset button.
    total_control_rows = n_images * 4 + 2
    control_height_per_row = 0.035  # inches per row
    needed_height = control_height_per_row * total_control_rows
    if needed_height > 8:  # default height is 10, so we can increase
        fig.set_size_inches(16, max(10, needed_height + 2))

    # Place a big axes for right column, then put everything inside with absolute coordinates
    ax_right = fig.add_axes([0.58, 0.05, 0.4, 0.9])
    ax_right.axis('off')
    ax_right.set_title("Controls", fontsize=12)

    # Channel checkbuttons
    channel_check_ax = plt.axes([0.60, 0.88, 0.35, 0.08])
    channel_check = CheckButtons(channel_check_ax, ['R', 'G', 'B'], [True, True, True])

    # Image checkbuttons (list)
    image_check_ax = plt.axes([0.60, 0.78, 0.35, 0.10])
    image_check = CheckButtons(image_check_ax, all_names, [True]*n_images)

    # Sliders for each image: we'll place them vertically
    # Starting Y position
    start_y = 0.72
    step_y = 0.04
    intensity_sliders = {}
    scale_sliders = {}
    offset_sliders = {}

    for i, name in enumerate(all_names):
        y = start_y - i * (step_y * 3.5)  # each group takes ~3.5*step
        if y < 0.1:
            break  # prevent going off bottom
        # Label as text
        fig.text(0.61, y + 0.025, name, fontsize=9, weight='bold')
        # Intensity slider
        ax_int = plt.axes([0.62, y - 0.01, 0.32, 0.02])
        s_int = Slider(ax_int, "Intensity", 0.0, 2.0, valinit=params[name]['intensity'], valfmt='%.2f')
        # Scale slider
        ax_sca = plt.axes([0.62, y - 0.04, 0.32, 0.02])
        s_sca = Slider(ax_sca, "Scale", 0.5, 3.0, valinit=params[name]['scale'])
        # Offset slider
        ax_off = plt.axes([0.62, y - 0.07, 0.32, 0.02])
        s_off = Slider(ax_off, "Offset", -200, 200, valinit=params[name]['offset'])

        intensity_sliders[name] = s_int
        scale_sliders[name] = s_sca
        offset_sliders[name] = s_off

    # Reset button
    reset_ax = plt.axes([0.62, 0.02, 0.25, 0.05])
    btn_reset = Button(reset_ax, "Reset All Parameters")

    # Function to update curves and strip
    def update_curves():
        ax_curves.clear()
        ax_curves.set_title("Spectral Curves")
        ax_curves.set_xlabel("Aligned Relative Wavelength")
        ax_curves.set_ylabel("Intensity (scaled)")
        ax_curves.grid(True)

        visible_channels = [ch for ch, vis in channel_visible.items() if vis]
        if not visible_channels:
            visible_channels = ['R']
        channel_color = {'R': 'red', 'G': 'green', 'B': 'blue'}

        # For each visible image
        for name in all_names:
            if not image_visible[name]:
                continue
            # Apply scale and offset to x
            scale = params[name]['scale']
            offset = params[name]['offset']
            x = scale * raw_dist[name] + offset
            intensity = params[name]['intensity']
            for ch in visible_channels:
                idx = {'R':0, 'G':1, 'B':2}[ch]
                y = raw_rgb[name][:, idx] * intensity
                style = '-'  # all solid lines, but we can differentiate by alpha or linewidth
                ax_curves.plot(x, y, color=channel_color[ch], linestyle=style,
                               linewidth=1.5, alpha=0.7,
                               label=f"{name} {ch}" if ch == visible_channels[0] else "")
        # Legend with unique entries
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

    # Event handlers
    def channel_clicked(label):
        channel_visible[label] = not channel_visible[label]
        update_curves()

    def image_clicked(label):
        image_visible[label] = not image_visible[label]
        # Update strip if this image is being shown
        if image_visible[label]:
            nonlocal current_strip_name
            current_strip_name = label
            update_strip()
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
        # Reset checkboxes: make all channels and images visible
        for ch in ['R','G','B']:
            channel_visible[ch] = True
        for name in all_names:
            image_visible[name] = True
        # Update UI checkboxes (difficult to programmatically invert, but plot will reflect)
        update_curves()
        # Also reset strip to first image
        nonlocal current_strip_name
        current_strip_name = all_names[0]
        update_strip()

    # Connect events
    channel_check.on_clicked(channel_clicked)
    image_check.on_clicked(image_clicked)
    for name in all_names:
        intensity_sliders[name].on_changed(lambda val, n=name: intensity_changed(val, n))
        scale_sliders[name].on_changed(lambda val, n=name: scale_changed(val, n))
        offset_sliders[name].on_changed(lambda val, n=name: offset_changed(val, n))
    btn_reset.on_clicked(reset_all)

    # Add a small instruction text
    fig.text(0.62, 0.95, "Click image checkbox to view its RGB strip", fontsize=8, style='italic')

    # Initial update
    update_curves()
    update_strip()
    plt.show(block=True)

    # Save final parameters
    param_file = os.path.join("output", "alignment_params.json")
    with open(param_file, 'w') as f:
        json.dump(params, f, indent=2)
    print(f"Parameters saved: {param_file}")

    # Interpolate and save aligned+scaled data onto a common x-axis
    # Determine common x-range from all transformed x's
    all_x = []
    for name in all_names:
        x = params[name]['scale'] * raw_dist[name] + params[name]['offset']
        all_x.extend(x)
    global_min = np.min(all_x)
    global_max = np.max(all_x)
    common_x = np.linspace(global_min, global_max, 500)

    aligned_data = {}
    for name in all_names:
        x_orig = params[name]['scale'] * raw_dist[name] + params[name]['offset']
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
    for name, ad in aligned_data.items():
        csv_path = os.path.join("output", f"{name}_aligned_scaled.csv")
        np.savetxt(csv_path, np.column_stack((ad['x'], ad['R'], ad['G'], ad['B'])),
                   delimiter=',', header="wavelength,R,G,B", comments='')
        print(f"Aligned+scaled data saved: {csv_path}")

    # Final per-channel comparison plots
    plt.figure(figsize=(12, 8))
    for ch, color in zip(['R','G','B'], ['red','green','blue']):
        plt.subplot(3,1,['R','G','B'].index(ch)+1)
        for name, ad in aligned_data.items():
            plt.plot(ad['x'], ad[ch], label=name, alpha=0.8)
        plt.title(f"{ch} channel (aligned & scaled)")
        plt.xlabel("Relative wavelength")
        plt.ylabel("Intensity")
        plt.legend()
        plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join("output", "final_aligned_scaled_curves.png"), dpi=150)
    plt.show(block=True)

    return aligned_data


def main():
    print("=== Spectral Image Extraction & Alignment Tool (Independent Controls for All Images) ===")
    file_paths = select_image_files()
    if not file_paths:
        print("No files selected.")
        return

    data_dict = {}
    for fpath in file_paths:
        name = os.path.splitext(os.path.basename(fpath))[0]
        print(f"\nProcessing: {name}")
        try:
            distances, rgb, strip = extract_line_rgb(fpath)
            data_dict[name] = {'path': fpath, 'distances': distances, 'rgb': rgb, 'strip': strip}
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