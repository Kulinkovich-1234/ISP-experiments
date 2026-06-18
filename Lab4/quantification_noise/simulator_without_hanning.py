import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft, fftfreq

def main():
    # ========== Parameters ==========
    f_signal = 300.0          # sine frequency (Hz)
    f_s = 5000.0              # sampling rate (Hz)
    duration = 1.0            # signal duration (s)
    bits = 16                 # quantization bits
    full_scale = 1.0          # amplitude range [-1, 1]
    M = 100                   # oversampling factor per sample (to approximate continuous-time)

    # ----- Discrete-time processing -----
    N_samples = int(f_s * duration)                 # number of samples
    Ts = 1.0 / f_s
    t_discrete = np.linspace(0, duration, N_samples, endpoint=False)

    # original sine
    x_analog = np.sin(2 * np.pi * f_signal * t_discrete)

    # uniform quantization
    L = 2 ** bits
    delta = (2 * full_scale) / L
    code = np.round((x_analog + full_scale) / delta).astype(int)
    code = np.clip(code, 0, L - 1)
    x_quant_discrete = code * delta - full_scale      # quantized values at sampling instants

    # ----- Build continuous-time staircase signal (zero-order hold) -----
    # Time axis for the continuous approximation: very fine resolution
    N_cont = N_samples * M
    t_cont = np.linspace(0, duration, N_cont, endpoint=False)
    # Repeat each quantized value M times
    x_staircase = np.repeat(x_quant_discrete, M)

    # ----- Approximate Continuous Fourier Transform via FFT on fine grid -----
    # No window (preserve staircase shape)
    Y_cont = fft(x_staircase) / N_cont            # normalized FFT (approximates CFT/fs_cont?)
    freqs_cont = fftfreq(N_cont, t_cont[1] - t_cont[0])   # frequency axis for continuous approx
    # Single-sided amplitude spectrum (magnitude of CFT approximation)
    Y_mag = 2 * np.abs(Y_cont[:N_cont // 2])
    freqs_pos = freqs_cont[:N_cont // 2]

    # Convert to dB
    Y_dB = 20 * np.log10(Y_mag + 1e-12)

    # ----- Theoretical CFT of a staircase signal (zero-order hold) -----
    # The continuous Fourier transform X_c(f) = Ts * sinc(f * Ts) * exp(-jπ f Ts) * X_d(f)
    # where X_d(f) is the DTFT of the quantized sequence.
    # For a sinusoidal input after quantization, the spectrum consists of the fundamental
    # and harmonics (k * f_signal) convolved with the sinc envelope.
    # We plot the theoretical envelope |Ts * sinc(f * Ts)|
    f_theory = np.linspace(0, f_s / 2, 2000)
    envelope = Ts * np.abs(np.sinc(f_theory * Ts))   # sinc(x) = sin(πx)/(πx)

    # ----- Plotting -----
    plt.figure(figsize=(12, 10))

    # Subplot 1: Staircase signal (time domain zoom)
    zoom_dur = 0.02            # show 20 ms
    zoom_idx = int(zoom_dur * f_s * M)   # indices in continuous axis
    t_zoom = t_cont[:zoom_idx]
    x_zoom = x_staircase[:zoom_idx]

    plt.subplot(3, 1, 1)
    plt.plot(t_zoom, x_zoom, 'b.-', markersize=2, linewidth=0.5)
    plt.title(f'Continuous-Time Staircase Signal (Zero-Order Hold) — fs = {f_s} Hz, {bits}-bit')
    plt.xlabel('Time (s)')
    plt.ylabel('Amplitude')
    plt.grid(True, linestyle='--', alpha=0.6)

    # Subplot 2: Approximated CFT magnitude spectrum (dB)
    plt.subplot(3, 1, 2)
    plt.plot(freqs_pos, Y_dB, 'g-', linewidth=1.2, label='Numerical CFT (oversampled FFT)')
    plt.plot(f_theory, 20 * np.log10(envelope + 1e-12), 'r--', linewidth=1.5,
            label='|Ts sinc(f Ts)| envelope')   # 修改为普通文本
    plt.title('Approximated Continuous Fourier Transform of Staircase Signal')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude Spectrum (dB)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.xlim(0, f_s)
    plt.ylim(-140, 0)
    # Mark harmonic frequencies of the input sine (fundamental and harmonics)
    max_harmonic = int(f_s / f_signal) // 2
    for k in range(1, max_harmonic + 1):
        freq_harm = k * f_signal
        if freq_harm <= f_s:
            plt.axvline(x=freq_harm, color='gray', linestyle=':', alpha=0.4, linewidth=0.8)
    plt.legend()

    # Subplot 3: Zoom around low frequencies (better view of harmonic comb)
    plt.subplot(3, 1, 3)
    zoom_fmax = 5 * f_signal   # up to 1500 Hz
    idx_zoom = np.where(freqs_pos <= zoom_fmax)[0]
    plt.plot(freqs_pos[idx_zoom], Y_dB[idx_zoom], 'g-', linewidth=1.2)
    plt.plot(f_theory[f_theory <= zoom_fmax], 20 * np.log10(envelope[f_theory <= zoom_fmax] + 1e-12),
             'r--', linewidth=1.5)
    plt.title('Zoomed Spectrum (DC to 5× Fundamental) — Harmonic Comb Structure')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude Spectrum (dB)')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.ylim(-140, 0)
    for k in range(1, 6):
        plt.axvline(x=k * f_signal, color='k', linestyle=':', alpha=0.6, linewidth=0.8,
                    label=f'{k}f₀' if k == 1 else "")
    plt.legend()

    plt.tight_layout()
    plt.show()

    # Console output
    print(f"Sampling rate: {f_s} Hz")
    print(f"Quantization bits: {bits}")
    print(f"Quantization step size: {delta:.3e}")
    # Estimate SNR from the discrete-time quantized sequence (not from continuous approx)
    noise = x_analog - x_quant_discrete
    snr_measured = 20 * np.log10(np.std(x_analog) / np.std(noise))
    snr_theory = 6.02 * bits + 1.76
    print(f"Measured SNR (discrete-time): {snr_measured:.2f} dB")
    print(f"Theoretical SNR (full-scale sine): {snr_theory:.2f} dB")
    print("\nNotes on the Continuous Fourier Transform of a staircase signal:")
    print("- The spectrum is the product of the DTFT of the quantized sequence and a sinc envelope.")
    print("- Because the input is a single sine, the DTFT consists of discrete harmonics at k * f_signal.")
    print("- Therefore the CFT also shows a harmonic comb, but each harmonic is shaped by the sinc envelope.")
    print("- The envelope nulls occur at multiples of f_s (e.g., 5000, 10000 Hz).")
    print("- The numerical approximation uses a very fine time grid (M = {} points per sample).".format(M))

if __name__ == "__main__":
    main()