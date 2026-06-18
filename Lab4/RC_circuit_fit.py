import io
import matplotlib.pyplot as plt
import numpy as np

# ================= 1. 加载用户数据 =================
data_str = """Frequency(Hz),Input_Amp(V),Output_Amp(V),Gain_Linear,Gain_dB,Phase_Shift_Deg,H_Real,H_Imag
100.0,-0.9668,0.0465,-0.0481,nan,-93.76,0.0032,0.048
100.0,0.9672,0.0464,0.048,-26.38,86.39,0.003,0.0479
200.0,0.9616,-0.0902,-0.0938,nan,-93.75,0.0061,0.0936
200.0,0.9614,-0.0903,-0.0939,nan,-93.48,0.0057,0.0938
300.0,0.9534,0.1337,0.1402,-17.07,86.24,0.0092,0.1399
300.0,0.9537,0.1339,0.1404,-17.05,86.13,0.0095,0.14
400.0,-0.9418,0.1752,-0.186,nan,-94.23,0.0137,0.1855
400.0,0.9431,0.1752,0.1857,-14.62,85.77,0.0137,0.1852
500.0,0.9309,0.2159,0.2319,-12.69,85.54,0.018,0.2312
500.0,0.9307,0.2151,0.2311,-12.72,85.61,0.0177,0.2304
600.0,0.9148,-0.2547,-0.2784,nan,-95.14,0.0249,0.2773
600.0,0.9148,0.255,0.2787,-11.1,84.88,0.0249,0.2776
700.0,-0.8992,-0.2922,0.325,-9.76,84.29,0.0323,0.3234
700.0,0.8991,-0.2922,-0.3249,nan,-95.76,0.0326,0.3233
800.0,0.8816,0.3276,0.3716,-8.6,83.62,0.0413,0.3693
800.0,-0.8814,0.3272,-0.3712,nan,-96.3,0.0407,0.3689
900.0,0.8639,0.3616,0.4186,-7.56,82.9,0.0517,0.4154
900.0,0.8638,0.3616,0.4186,-7.56,82.96,0.0513,0.4154
1000.0,-0.8466,0.394,-0.4653,nan,-97.85,0.0636,0.461
1100.0,0.8271,0.4241,0.5127,-5.8,81.26,0.0779,0.5068
1500.0,0.7556,0.5249,0.6947,-3.16,77.19,0.154,0.6774
2000.0,0.6972,0.6226,0.893,-0.98,71.28,0.2865,0.8457
2500.0,0.6687,-0.6916,-1.0343,nan,-114.28,0.4252,0.9429
3000.0,0.6633,-0.7414,-1.1177,nan,-118.61,0.5352,0.9813
3500.0,0.6721,0.7764,1.1551,1.25,58.81,0.5983,0.9881
4000.0,0.6864,0.8016,1.1677,1.35,57.79,0.6225,0.988"""

# 解析数据（过滤掉可能从 CSV 读取进来的表头）
freq, gain_linear, phase_deg = [], [], []
for line in data_str.strip().split("\n")[1:]:
    parts = line.split(",")
    freq.append(float(parts[0]))
    # 对线性增益取绝对值（消除部分数据因负号导致的非物理现象）
    gain_linear.append(abs(float(parts[3])))
    # 将相位限制在 0 到 180 度之间（消除正弦波拟合时正负倒置带来的180度相位跳变）
    p = float(parts[5])
    if p < 0:
        p += 180
    phase_deg.append(p)

freq = np.array(freq)
gain_linear = np.array(gain_linear)
phase_deg = np.array(phase_deg)


# ================= 2. 定义拟合物理模型 =================
# 考虑高频放大系数 K 的高通幅频特性公式
def hpf_gain_model(f, RC, K):
    w = 2 * np.pi * f
    return K * (w * RC) / np.sqrt(1 + (w * RC) ** 2)


# ================= 3. 执行曲线拟合 =================
# TODO: Students must derive and implement the RC high-pass transfer function
#       H(s) = Vout/Vin = (sRC) / (1 + sRC)
#
# Hint: Use scipy.optimize.curve_fit to fit hpf_gain_model(f, RC, K) to your data.
#       The model is: |H(f)| = K * (2*pi*f*RC) / sqrt(1 + (2*pi*f*RC)^2)
#       Initial guess: RC ~ 1e-4, K ~ 1.1
raise NotImplementedError(
    "Students must implement the curve_fit for the RC high-pass filter model. "
    "See docstring above for the transfer function formula."
)

# Once fitted, compute:
#   f_cutoff = 1 / (2 * pi * RC)
# Then print the derived component values and plot the Bode diagram.
#
# Below is the plotting code that will run once you replace the NotImplementedError
# above with a working curve_fit. The variables fit_RC and fit_K come from popt.

# f_smooth = np.logspace(np.log10(min(freq)), np.log10(max(freq)), 500)
# gain_fit = hpf_gain_model(f_smooth, fit_RC, fit_K)
# phase_fit = 90 - np.degrees(np.arctan(2 * np.pi * f_smooth * fit_RC))
#
# fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
# ax1.semilogx(freq, 20 * np.log10(gain_linear), "bo", label="Measured Data")
# ax1.semilogx(f_smooth, 20 * np.log10(gain_fit), "r-", label="Fitted HPF Curve")
# ax1.axvline(f_cutoff, color="g", linestyle="--", label=f"Cutoff Freq ({f_cutoff:.1f} Hz)")
# ax1.set_ylabel("Gain (dB)")
# ax1.set_title("RC High-Pass Filter Bode Plot - Parameter Fitting")
# ax1.grid(True, which="both", ls="-")
# ax1.legend()
#
# ax2.semilogx(freq, phase_deg, "bo", label="Measured Phase")
# ax2.semilogx(f_smooth, phase_fit, "r-", label="Fitted Phase Curve")
# ax2.axvline(f_cutoff, color="g", linestyle="--")
# ax2.set_xlabel("Frequency (Hz)")
# ax2.set_ylabel("Phase Shift (Degrees)")
# ax2.grid(True, which="both", ls="-")
# ax2.legend()
# plt.tight_layout()
# plt.show()