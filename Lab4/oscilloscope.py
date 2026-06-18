import csv
import matplotlib.pyplot as plt
import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType
from scipy.optimize import curve_fit

# ================= 配置参数 =================
DEVICE_NAME = "Dev1"
CH_INPUT = "ai0"  # 输入信号 (总激励)
CH_OUTPUT = "ai5"  # 输出信号 (R两端电压)
SAMPLE_RATE = 20000  # 采样率 (Hz) - 建议设为预计最高测试频率的5-10倍
ACQ_TIME = 5.0  # 每次采集时长 (秒)
VOLTAGE_RANGE = 10.0

TOTAL_SAMPLES = int(SAMPLE_RATE * ACQ_TIME)
CSV_FILENAME = "rc_circuit_results.csv"
# ============================================


# 正弦波拟合函数 (强制频率一致，分别拟合幅度和相位)
def sine_func(t, A, phi, offset, f):
    return A * np.sin(2 * np.pi * f * t + phi) + offset


def fit_channel_data(t_data, y_data, est_freq):
    """辅助函数：利用已知粗略频率，精确拟合信号的振幅、相位和偏置"""
    est_amp = (np.max(y_data) - np.min(y_data)) / 2
    est_offset = np.mean(y_data)
    p0 = [est_amp, 0.0, est_offset]

    # 使用 lambda 固定频率 f，只拟合 A, phi, offset
    popt, _ = curve_fit(
        lambda t, A, phi, offset: sine_func(t, A, phi, offset, est_freq),
        t_data,
        y_data,
        p0=p0,
    )
    return popt  # 返回 [Amp, Phi, Offset]


# 用于存储所有频率测试结果的列表
results_summary = []

print("=" * 60)
print("  NI DAQ RC电路频率响应自动化测试系统")
print("=" * 60)
print(f"数据将保存至: {CSV_FILENAME}\n")

try:
    with nidaqmx.Task() as task:
        # 同时添加两个通道：AI0 和 AI5
        task.ai_channels.add_ai_voltage_chan(
            f"{DEVICE_NAME}/{CH_INPUT}",
            min_val=-VOLTAGE_RANGE,
            max_val=VOLTAGE_RANGE,
        )
        task.ai_channels.add_ai_voltage_chan(
            f"{DEVICE_NAME}/{CH_OUTPUT}",
            min_val=-VOLTAGE_RANGE,
            max_val=VOLTAGE_RANGE,
        )

        task.timing.cfg_samp_clk_timing(
            rate=SAMPLE_RATE,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=TOTAL_SAMPLES,
        )

        t_data = np.linspace(0, ACQ_TIME, TOTAL_SAMPLES, endpoint=False)

        freq_count = 1
        while True:
            print(f"\n--- [测试点 #{freq_count}] ---")
            user_input = input(
                "请调节信号发生器到目标频率，按【回车】开始测量（输入 'q' 保存并退出）: "
            )
            if user_input.strip().lower() == "q":
                break

            print("正在采集5秒数据...")
            task.start()
            # read 返回一个二维列表: [ [AI0数据], [AI5数据] ]
            raw_data = task.read(
                number_of_samples_per_channel=TOTAL_SAMPLES,
                timeout=ACQ_TIME + 1.0,
            )
            task.stop()  # 停止当前单次任务，准备下一次

            in_data = np.array(raw_data[0])
            out_data = np.array(raw_data[1])

            # 1. 通过 FFT 自动识别当前输入信号的实际频率
            fft_freqs = np.fft.fftfreq(TOTAL_SAMPLES, 1 / SAMPLE_RATE)
            fft_vals = np.abs(np.fft.fft(in_data))
            positive_idx = fft_freqs > 0
            actual_freq = fft_freqs[positive_idx][
                np.argmax(fft_vals[positive_idx])
            ]

            # 2. 分别精确拟合输入通道(AI0)和输出通道(AI5)
            in_amp, in_phi, _ = fit_channel_data(t_data, in_data, actual_freq)
            out_amp, out_phi, _ = fit_channel_data(
                t_data, out_data, actual_freq
            )

            # 3. 计算电路响应指标
            # 增益 (Gain)
            gain = out_amp / in_amp
            gain_db = 20 * np.log10(gain)

            # 相位差 (Phase Shift)，将其限制在 -pi 到 pi 之间
            phase_diff = out_phi - in_phi
            phase_diff = (phase_diff + np.pi) % (2 * np.pi) - np.pi
            phase_diff_deg = np.degrees(phase_diff)

            # 复传递函数 H(j*omega) = (A_out / A_in) * exp(j * phase_diff)
            # 展开为复数形式：实部 + 虚部j
            h_complex = gain * np.exp(1j * phase_diff)
            h_real = h_complex.real
            h_imag = h_complex.imag

            # 4. 实时打印当前频率的分析结果
            print(f"检测到输入主频: {actual_freq:.2f} Hz")
            print(f"输入幅值: {in_amp:.3f} V | 输出幅值: {out_amp:.3f} V")
            print(f"电压增益: {gain:.4f} ({gain_db:.2f} dB)")
            print(f"相位差:   {phase_diff_deg:.2f}°")
            print(f"复传递函数 H(f): {h_real:.4f} + ({h_imag:.4f})j")

            # 5. 保存单步数据
            results_summary.append(
                {
                    "Frequency(Hz)": round(actual_freq, 2),
                    "Input_Amp(V)": round(in_amp, 4),
                    "Output_Amp(V)": round(out_amp, 4),
                    "Gain_Linear": round(gain, 4),
                    "Gain_dB": round(gain_db, 2),
                    "Phase_Shift_Deg": round(phase_diff_deg, 2),
                    "H_Real": round(h_real, 4),
                    "H_Imag": round(h_imag, 4),
                }
            )
            freq_count += 1

except nidaqmx.errors.DaqError as e:
    print(f"\nNI DAQ 驱动错误: {e}")
except Exception as e:
    print(f"\n运行错误: {e}")

# ================= 汇总导出 CSV =================
if results_summary:
    # 按频率从小到大排序，方便后续作图（如伯德图）分析
    results_summary.sort(key=lambda x: x["Frequency(Hz)"])

    headers = list(results_summary[0].keys())
    with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results_summary)

    print("\n" + "=" * 60)
    print(f"【测试结束】成功汇总 {len(results_summary)} 组频率数据！")
    print(f"数据已妥善写入: {CSV_FILENAME}")
    print("=" * 60)
else:
    print("\n未保存任何有效测试数据。")