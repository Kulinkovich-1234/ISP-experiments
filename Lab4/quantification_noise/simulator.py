import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq

def main():
    # ========== 参数设置 ==========
    f_signal = 300.0      # 正弦波频率 (Hz)
    f_s = 5000.0          # 采样率 (Hz)
    duration = 1.0        # 信号时长 (s)
    bits = 8             # 量化位数
    full_scale = 1.0      # 信号幅度范围 [-full_scale, +full_scale]

    # 采样点数
    N = int(f_s * duration)
    t = np.linspace(0, duration, N, endpoint=False)

    # ========== 生成原始正弦波 ==========
    x_analog = np.sin(2 * np.pi * f_signal * t)  # 幅度 ±1

    # ========== 量化 ==========
    # 量化步长
    L = 2 ** bits                     # 量化级数
    delta = (2 * full_scale) / L      # 量化间隔

    # 将浮点值映射到整数码字 (0 ~ L-1)
    # 公式：code = round((x + full_scale) / delta)
    code = np.round((x_analog + full_scale) / delta).astype(int)
    code = np.clip(code, 0, L - 1)    # 防止边界溢出

    # 由码字重建量化后的信号 (浮点值)
    x_quant = code * delta - full_scale

    # ========== 计算量化误差 ==========
    e_quant = x_analog - x_quant      # 误差 = 原信号 - 量化信号

    # ========== 频谱分析（误差信号） ==========
    # 加汉宁窗减少频谱泄漏（可选）
    window = np.hanning(N)
    e_windowed = e_quant * window

    # 单边幅度谱 (取正频率部分)
    Y = fft(e_windowed) / N                # FFT 并归一化
    Y_mag = 2 * np.abs(Y[:N//2])           # 单边幅度谱（乘2恢复能量）
    freqs = fftfreq(N, 1/f_s)[:N//2]       # 频率轴

    # 转换到 dB (参考电平 1.0)
    Y_dB = 20 * np.log10(Y_mag + 1e-12)    # 加微小值避免 log(0)

    # ========== 绘图 ==========
    plt.figure(figsize=(12, 10))

    # 子图1：原始正弦波（前 5 个周期）
    t_zoom = t[:200]                      # 显示 0 ~ 0.04 秒
    x_analog_zoom = x_analog[:200]
    plt.subplot(3, 1, 1)
    plt.plot(t_zoom, x_analog_zoom, 'b-', label='Original Analog Signal')
    plt.title(f'Original Analog Signal (f={f_signal} Hz)')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()

    # 子图2：量化后的信号（阶梯效果）
    plt.subplot(3, 1, 2)
    plt.plot(t_zoom, x_quant[:200], 'r.-', markersize=2, linewidth=0.5,
             label=f'Quantized Signal ({bits}-bit)')
    plt.title('Quantized Signal (Displaying Quantization Steps)')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()

    # 子图3：量化误差的频谱（FT 谱）
    plt.subplot(3, 1, 3)
    plt.plot(freqs, Y_dB, 'g-', linewidth=1)
    plt.title(f'Quantization Noise Spectrum (FFT, Hann window, {bits}-bit Quantization)')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude Spectrum (dB)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xlim(0, f_s/2)                     # 显示到奈奎斯特频率
    plt.ylim(-140, 0)

    # 可选：标注理论量化噪声底 (SNR = 6.02*bits + 1.76 dB)
    snr_theory = 6.02 * bits + 1.76        # dB, 对于正弦波满幅输入
    # 满幅正弦波功率 = 0.5，量化噪声功率理论值 = delta^2/12
    # 此处仅作为参考线，实际观测到的噪声谱密度会低于信号峰值
    plt.axhline(y=-snr_theory, color='r', linestyle='--',
                label=f'Theoretical S/N ratio ≈ {snr_theory:.1f} dB')

    plt.legend()

    plt.tight_layout()
    plt.show()

    # 输出一些统计信息
    print(f"采样率: {f_s} Hz")
    print(f"量化位数: {bits} bits")
    print(f"量化步长: {delta:.6f}")
    print(f"量化误差均值: {np.mean(e_quant):.4e}")
    print(f"量化误差均方根: {np.std(e_quant):.4e}")
    print(f"理论量化噪声 RMS: {delta / np.sqrt(12):.4e}")
    print(f"实测信噪比 (SNR): {20*np.log10(np.std(x_analog)/np.std(e_quant)):.2f} dB")
    print(f"理论信噪比 (正弦波满幅): {6.02*bits + 1.76:.2f} dB")

if __name__ == "__main__":
    main()