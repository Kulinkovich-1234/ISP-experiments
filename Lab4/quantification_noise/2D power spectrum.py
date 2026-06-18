import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq
from tqdm import tqdm

def compute_staircase_cft(f_in, fs, bits, duration, M, full_scale=1.0):
    N_samples = int(fs * duration)
    Ts = 1.0 / fs
    t_discrete = np.linspace(0, duration, N_samples, endpoint=False)
    x_analog = np.sin(2 * np.pi * f_in * t_discrete)
    
    L = 2 ** bits
    delta = (2 * full_scale) / L
    code = np.round((x_analog + full_scale) / delta).astype(int)
    code = np.clip(code, 0, L - 1)
    x_quant_discrete = code * delta - full_scale
    
    N_cont = N_samples * M
    t_cont = np.linspace(0, duration, N_cont, endpoint=False)
    x_staircase = np.repeat(x_quant_discrete, M)
    
    Y_cont = fft(x_staircase) / N_cont
    freqs_cont = fftfreq(N_cont, t_cont[1] - t_cont[0])
    Y_mag = 2 * np.abs(Y_cont[:N_cont // 2])
    freqs_pos = freqs_cont[:N_cont // 2]
    Y_dB = 20 * np.log10(Y_mag + 1e-12)
    return freqs_pos, Y_dB

def main_2d_spectrum_no_interp():
    fs = 5000.0
    bits = 16
    duration = 1.0
    full_scale = 1.0
    M = 20
    
    f_min = 10.0
    f_max = fs
    num_f_in = 150
    f_in_list = np.linspace(f_min, f_max, num_f_in)
    
    # 先计算一个输入频率，获取公共频率轴（所有输入频率共用）
    freqs_ref, _ = compute_staircase_cft(f_in_list[0], fs, bits, duration, M, full_scale)
    n_freq_out = len(freqs_ref)
    
    # 初始化矩阵：行 = 输入频率，列 = 输出频率
    spectrogram = np.zeros((len(f_in_list), n_freq_out))
    
    print("Computing 2D quantization noise spectrum (no interpolation)...")
    for i, f_in in enumerate(tqdm(f_in_list)):
        freqs, Y_dB = compute_staircase_cft(f_in, fs, bits, duration, M, full_scale)
        # 确保频率轴一致（理论上完全相同，若因浮点误差微小差异，可强制对齐）
        assert np.allclose(freqs, freqs_ref), "Frequency axis mismatch"
        spectrogram[i, :] = Y_dB
    
    # 绘图
    plt.figure(figsize=(12, 8))
    extent = [freqs_ref[0], freqs_ref[-1], f_in_list[0], f_in_list[-1]]
    plt.imshow(spectrogram, aspect='auto', origin='lower', cmap='viridis',
               extent=extent, vmin=-120, vmax=0)
    plt.colorbar(label='Magnitude Spectrum (dB)')
    plt.xlabel('Output Frequency (Hz)')
    plt.ylabel('Input Signal Frequency (Hz)')
    plt.title(f'2D Quantization Noise Spectrum (16-bit, fs={fs} Hz)\nDirect FFT, no interpolation')
    plt.grid(False)
    # 辅助线
    plt.plot([0, fs/2], [0, fs/2], 'w--', linewidth=0.8, alpha=0.6, label='Fundamental')
    plt.plot([0, fs/2], [fs, fs/2], 'w--', linewidth=0.8, alpha=0.6, label='Aliasing (fs - f_in)')
    plt.legend()
    plt.savefig('quantization_noise_2d_no_interp.png', dpi=500, bbox_inches='tight')
    plt.show()
    print("Image saved as quantization_noise_2d_no_interp.png (500 dpi)")

if __name__ == "__main__":
    main_2d_spectrum_no_interp()