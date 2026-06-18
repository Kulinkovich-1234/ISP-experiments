import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

# ==================== 实验数据 ====================
# 数据格式: (物距 s_o / mm, 像素数 N)
data_raw = [
    (770, 793.023), (770, 793.023), (770, 791.031),
    (442.5, 1372.118), (442.5, 1373.593), (442.5, 1372.808),
    (328, 1895.178), (328, 1895.528), (328, 1895.932),
    (153, 4138.124), (153, 4139.116), (153, 4139.116),
    (1500, 403.754), (1500, 404.006), (1500, 404.006),
    (797, 769.25), (797, 769.25), (797, 769.25),
    (939, 649.028), (939, 649.028), (939, 649.028),
    (1124, 543.338), (1124, 543.338), (1124, 542.666)
]

# Known parameters
# TODO: Replace these with your measured values.
# H: the actual physical height of the object (mm)
# pixel_size: your camera sensor's pixel pitch (mm/pixel), from datasheet
H = None                  # Measure the actual object height (mm)
pixel_size = None         # Determine from your camera sensor specifications (mm/pixel)

# ==================== Compute image height h and 1/h ====================
s_o_list = []
inv_h_list = []

for s, N in data_raw:
    h = N * pixel_size          # image height (mm)
    inv_h = 1.0 / h             # 1/h (mm^{-1})
    s_o_list.append(s)
    inv_h_list.append(inv_h)

s_o_arr = np.array(s_o_list)
inv_h_arr = np.array(inv_h_list)

# ==================== Linear regression: inv_h = k * s_o + b ====================
# Theoretical relationship: inv_h = (1/(f*H)) * s_o - 1/H
slope, intercept, r_value, p_value, std_err = stats.linregress(s_o_arr, inv_h_arr)

# Focal length f (mm) from slope
f_fit = 1.0 / (slope * H)
# Uncertainty propagation from slope error
f_err = 1.0 / (slope**2 * H) * std_err   # df/dk = -1/(k^2 H), absolute error

print("========== Linear Regression Results ==========")
print(f"Fitted equation: 1/h = {slope:.6f} * s_o + {intercept:.6f}")
print(f"Standard error of slope: {std_err:.6f}")
print(f"Correlation coefficient R^2: {r_value**2:.6f}")
print(f"Theoretical intercept: -1/H = {-1/H:.6f} mm^{-1}")
print(f"Measured intercept: {intercept:.6f} mm^{-1}")
print(f"\nFocal length from fitting: f = {f_fit:.3f} mm")
print(f"Uncertainty in f: ±{f_err:.3f} mm")

# ==================== Point‑by‑point calculation of f ====================
def compute_f(s, h):
    return s * h / (H + h)

f_values = []
for idx, (s, N) in enumerate(data_raw):
    h = N * pixel_size
    f_val = compute_f(s, h)
    f_values.append(f_val)

f_mean = np.mean(f_values)
f_std = np.std(f_values, ddof=1)   # sample standard deviation

print("\n========== Direct Point‑by‑Point Focal Lengths ==========")
print(f"Average focal length (direct) = {f_mean:.3f} ± {f_std:.3f} mm")

# Group by object distance
unique_s = sorted(set(s for s,_ in data_raw))
print("\nAverage focal length at each object distance:")
for s in unique_s:
    idxs = [i for i, (s0,_) in enumerate(data_raw) if s0 == s]
    fs_group = [f_values[i] for i in idxs]
    print(f"s_o = {s:5.1f} mm : f = {np.mean(fs_group):.3f} ± {np.std(fs_group, ddof=1):.3f} mm")

# ==================== Plotting ====================
plt.figure(figsize=(8,5))

# Subplot 1: 1/h vs. s_o with linear fit
plt.subplot(1,2,1)
plt.scatter(s_o_arr, inv_h_arr, alpha=0.6, label='Experimental data')
s_fit = np.linspace(min(s_o_arr), max(s_o_arr), 100)
inv_h_fit = slope * s_fit + intercept
plt.plot(s_fit, inv_h_fit, 'r-', label=f'Fit: 1/h = {slope:.4f} s_o + {intercept:.2f}')
plt.xlabel('Object distance s_o (mm)')
plt.ylabel('1/h (mm⁻¹)')
plt.title('Linearised fitting for focal length')
plt.legend()
plt.grid(True)

# Subplot 2: Object distance vs. directly computed f
plt.subplot(1,2,2)
plt.scatter(s_o_arr, f_values, alpha=0.6)
plt.axhline(y=f_mean, color='r', linestyle='--', label=f'Mean f = {f_mean:.3f} mm')
plt.xlabel('Object distance s_o (mm)')
plt.ylabel('Computed focal length f (mm)')
plt.title('Point‑by‑point focal length values')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig('focal_length_fitting.png', dpi=150)
print("\nFitting image saved as 'focal_length_fitting.png'")
plt.show()