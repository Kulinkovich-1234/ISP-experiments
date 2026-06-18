"""NIDAQmx AO-AI 扫描脚本

使用 Dev3/ao0 输出扫描电压，并在 Dev3/ai0 读取对应的输入电压。
扫描结束后绘制输出电压与输入电压曲线。

改动说明:
  - 已移除实时图像显示，改用文字打印输出
  - AO 电压从低到高再到低扫描 3 轮

示例:
    python scan_ao_ai.py --start 0 --stop 5 --points 100
"""

import argparse
import csv
import sys
import time

try:
    import numpy as np
    import matplotlib.pyplot as plt
    import nidaqmx
    from nidaqmx.constants import AcquisitionType
except ImportError as exc:
    print("缺少依赖，请先安装: numpy matplotlib nidaqmx")
    print(exc)
    sys.exit(1)


def scan_ao_ai(
    device_name: str = "Dev3",
    ao_channel: str = "ao0",
    ai_channel: str = "ai0",
    start_voltage: float = 0.0,
    stop_voltage: float = 0.6,
    points: int = 100,
    settle_time: float = 0.05,
    num_rounds: int = 3,
):
    """执行 AO 输出扫描并在 AI 测量，低→高→低往复 num_rounds 轮。"""
    ao_channel_name = f"{device_name}/{ao_channel}"
    ai_channel_name = f"{device_name}/{ai_channel}"

    import nidaqmx.system

    system = nidaqmx.system.System.local()
    # 触发驱动加载，有时这一步就能解决访问冲突
    _ = system.driver_version
    # 杀死所有未正确释放的任务（如果有）
    for task in system.tasks:
        try:
            task.control(nidaqmx.constants.TaskMode.KILL)
        except Exception:
            pass

    # 生成从低到高、再从高到低的扫描序列（每轮 2*points 点）
    forward = np.linspace(start_voltage, stop_voltage, points)       # 低→高
    backward = np.linspace(stop_voltage, start_voltage, points)      # 高→低

    total_per_round = len(forward) + len(backward)
    total_points = total_per_round * num_rounds

    print(f"设备: {device_name}, AO: {ao_channel}, AI: {ai_channel}")
    print(f"扫描范围: {start_voltage} V → {stop_voltage} V (每方向 {points} 点)")
    print(f"扫描轮数: {num_rounds} (每轮 低→高 + 高→低)")
    print(f"总点数: {total_points}, 每点稳定时间: {settle_time} 秒\n")

    output_voltages: list[float] = []
    measured_voltages: list[float] = []

    with nidaqmx.Task() as ao_task, nidaqmx.Task() as ai_task:
        ao_task.ao_channels.add_ao_voltage_chan(ao_channel_name)
        ai_task.ai_channels.add_ai_voltage_chan(ai_channel_name)

        point_no = 0
        for rnd in range(1, num_rounds + 1):
            print(f"========== 第 {rnd} 轮 ==========")

            for direction_label, voltages in [
                ("正向 (低→高)", forward),
                ("反向 (高→低)", backward),
            ]:
                print(f"  --- {direction_label} ---")
                for voltage in voltages:
                    point_no += 1
                    ao_task.write(voltage)
                    time.sleep(settle_time)

                    # 读取单点输入电压
                    measured = ai_task.read()
                    if isinstance(measured, list):
                        measured = measured[0]

                    output_voltages.append(voltage)
                    measured_voltages.append(measured)

                    print(
                        f"  [{point_no:4d}/{total_points}] "
                        f"AO = {voltage:6.4f} V,  "
                        f"AI = {measured:6.4f} V"
                    )

        # 扫描结束后将输出拉回 0V，确保安全
        print("\n扫描完成，AO 拉回 0V")
        ao_task.write(0.0)

    return np.array(output_voltages), np.array(measured_voltages)


def plot_result(output_voltages, measured_voltages, title: str = None):
    plt.figure(figsize=(8, 5))
    plt.plot(
        output_voltages, measured_voltages,
        marker="o", linestyle="-", color="tab:blue", markersize=2,
    )
    plt.title(title or "AO Output Scanning and AI Measurement Curve")
    plt.xlabel("AO Output Voltage (V)")
    plt.ylabel("AI Measurement Voltage (V)")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def save_csv(filename: str, output_voltages, measured_voltages):
    header = ["ao_输出电压_V", "ai_输入电压_V"]
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for ao_v, ai_v in zip(output_voltages, measured_voltages):
            writer.writerow([ao_v, ai_v])


def parse_args():
    parser = argparse.ArgumentParser(
        description="扫描 AO 输出并读取 AI 输入（低→高→低，3 轮）"
    )
    parser.add_argument("--device", default="Dev3", help="NI 设备名称，例如 Dev3")
    parser.add_argument("--ao", default="ao0", help="AO 通道，例如 ao0")
    parser.add_argument("--ai", default="ai0", help="AI 通道，例如 ai0")
    parser.add_argument("--start", type=float, default=0.0, help="扫描起始电压 (V)")
    parser.add_argument("--stop", type=float, default=0.6, help="扫描结束电压 (V)")
    parser.add_argument("--points", type=int, default=100, help="每个方向的扫描点数")
    parser.add_argument(
        "--rounds", type=int, default=3,
        help="往复扫描轮数（每轮 = 低→高 + 高→低）",
    )
    parser.add_argument(
        "--settle", type=float, default=0.05,
        help="每次输出后等待稳定时间 (秒)",
    )
    parser.add_argument(
        "--csv", default=None,
        help="可选 CSV 文件名，保存扫描数据",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    print("正在执行 AO-AI 扫描...请确认电源已连接，设备已准备好。")
    input("按 Enter 键开始扫描...")  # 等待用户确认
    print(f"使用设备: {args.device}, AO: {args.ao}, AI: {args.ai}")
    print(f"扫描范围: {args.start} V 到 {args.stop} V，共 {args.rounds} 轮，每方向 {args.points} 点")
    print(f"每点稳定时间: {args.settle} 秒")

    output_voltages, measured_voltages = scan_ao_ai(
        device_name=args.device,
        ao_channel=args.ao,
        ai_channel=args.ai,
        start_voltage=args.start,
        stop_voltage=args.stop,
        points=args.points,
        settle_time=args.settle,
        num_rounds=args.rounds,
    )

    if args.csv:
        save_csv(args.csv, output_voltages, measured_voltages)
        print(f"已保存数据到 {args.csv}")

    # 扫描结束后绘制最终曲线
    plot_result(
        output_voltages,
        measured_voltages,
        title=(
            f"{args.device}/{args.ao} -> {args.device}/{args.ai} "
            f"Scanning Curve ({args.rounds} Rounds)"
        ),
    )


if __name__ == "__main__":
    main()
