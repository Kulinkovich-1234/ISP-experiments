"""NIDAQmx AI 实时监测脚本

持续读取指定 AI 通道的电压值，实时打印并可选绘制趋势图。
无需 AO 输出，纯监测用途。

示例:
    python monitor_ai.py --ai ai0 --interval 0.1 --csv log.csv
"""

import argparse
import csv
import sys
import time
from datetime import datetime

try:
    import numpy as np
    import nidaqmx
except ImportError as exc:
    print("缺少依赖，请先安装: numpy nidaqmx")
    print(exc)
    sys.exit(1)

# matplotlib 按需导入（仅绘图模式需要）
plt = None


def import_plt():
    global plt
    if plt is None:
        import matplotlib.pyplot as p
        plt = p


def monitor_ai(
    device_name: str = "Dev3",
    ao_channel: str = "ao0",
    ao_voltage: float = 0.6,
    ai_channel: str = "ai0",
    duration: float = 10.0,
    sample_rate: float = 100.0,
    plot_after: bool = True,
    csv_path: str | None = None,
):
    """在 `ao_channel` 输出 `ao_voltage`，对 `ai_channel` 以 `sample_rate` 采样 `duration` 秒，
    完成后绘制波形并可选保存 CSV。此函数不进行实时绘图或逐点打印。
    """
    ao_name = f"{device_name}/{ao_channel}"
    ai_name = f"{device_name}/{ai_channel}"

    # 驱动初始化并清理残留任务
    import nidaqmx.system
    system = nidaqmx.system.System.local()
    _ = system.driver_version
    for task in system.tasks:
        try:
            task.control(nidaqmx.constants.TaskMode.KILL)
        except Exception:
            pass

    # 计算采样参数
    if sample_rate <= 0:
        raise ValueError("sample_rate 必须为正数")
    if duration <= 0:
        raise ValueError("duration 必须为正数")

    interval = 1.0 / sample_rate
    total_samples = int(round(duration * sample_rate))

    print(f"将 {ao_name} 设为 {ao_voltage} V，然后对 {ai_name} 采样 {duration}s @ {sample_rate}Hz，共 {total_samples} 点")

    timestamps: list[float] = []
    voltages: list[float] = []

    csv_file = None
    csv_writer = None
    if csv_path:
        csv_file = open(csv_path, "w", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["time_s", "voltage_V"])

    # 使用独立的 AO/AI 任务，先写 AO，再采样 AI
    with nidaqmx.Task() as ao_task, nidaqmx.Task() as ai_task:
        ao_task.ao_channels.add_ao_voltage_chan(ao_name)
        ai_task.ai_channels.add_ai_voltage_chan(ai_name)

        # 输出 AO 电压
        ao_task.write(ao_voltage)
        time.sleep(0.02)  # 确保输出稳定

        start = time.perf_counter()
        next_time = start
        samples_taken = 0

        try:
            while samples_taken < total_samples:
                now = time.perf_counter()
                # 采样
                measured = ai_task.read()
                if isinstance(measured, list):
                    measured = measured[0]

                elapsed = now - start
                timestamps.append(elapsed)
                voltages.append(measured)

                if csv_writer:
                    csv_writer.writerow([f"{elapsed:.6f}", f"{measured:.6f}"])

                samples_taken += 1

                # 计算下次采样时间并睡眠
                next_time += interval
                sleep_for = next_time - time.perf_counter()
                if sleep_for > 0:
                    time.sleep(sleep_for)

        finally:
            # 将 AO 拉回 0V
            try:
                ao_task.write(0.0)
            except Exception:
                pass
            if csv_file:
                csv_file.close()

    print(f"采样完成，共 {len(voltages)} 个点，持续 {timestamps[-1] if timestamps else 0:.3f}s")

    # 绘图
    if plot_after:
        import_plt()
        plt.figure(figsize=(10, 4))
        plt.plot(timestamps, voltages, marker=".", linestyle="-", ms=3)
        plt.title(f"{ai_name} Sampling Waveform ({duration}s @ {sample_rate}Hz)")
        plt.xlabel("Time (s)")
        plt.ylabel("Voltage (V)")
        plt.grid(True)
        plt.tight_layout()
        plt.show()


def parse_args():
    parser = argparse.ArgumentParser(description="在 AO 输出时监测 AI 并绘制波形")
    parser.add_argument("--device", default="Dev3", help="NI 设备名称，例如 Dev3")
    parser.add_argument("--ao", default="ao0", help="AO 通道，例如 ao0")
    parser.add_argument("--ao-voltage", type=float, default=0.5, help="写入 AO 的电压 (V)")
    parser.add_argument("--ai", default="ai0", help="AI 通道，例如 ai0")
    parser.add_argument("--duration", type=float, default=5.0, help="采样总时长 (秒)")
    parser.add_argument("--rate", type=float, default=100.0, help="采样率 (Hz)，例如 100")
    parser.add_argument(
        "--no-plot", action="store_true",
        help="采样后不自动弹出绘图窗口",
    )
    parser.add_argument("--csv", default=None, help="保存数据到 CSV 文件")
    return parser.parse_args()


def main():
    args = parse_args()
    print("准备开始：请确认电源已连接，设备已准备好。")
    input("按 Enter 键开始监测 (将对 AO 输出并采样 AI)...")
    monitor_ai(
        device_name=args.device,
        ao_channel=args.ao,
        ao_voltage=args.ao_voltage,
        ai_channel=args.ai,
        duration=args.duration,
        sample_rate=args.rate,
        plot_after=not args.no_plot,
        csv_path=args.csv,
    )


if __name__ == "__main__":
    main()
