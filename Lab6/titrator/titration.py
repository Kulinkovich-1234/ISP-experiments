"""滴定控制脚本

流程:
 1. 连接注射器泵 (默认 COM5)，等待用户手动将活塞推到最小体积并按回车确认。
 2. 自动后退吸取指定体积（默认 800 µL）。
 3. 将 DAQ 的 AO 保持在指定电压（默认 0.5 V）。
 4. 恒速前进滴定，同时以指定采样率采集 AI（默认 100 Hz），对读数做滑动平均。
 5. 在达到吸取体积时停止，保存 CSV 并绘图。

依赖: numpy, matplotlib, nidaqmx, pyserial

注意: 校准参数（EDTA 浓度、注射器内径）必须通过实验测量获得。
      MM_TO_UL_AREA 由注射器内径通过公式 π*(d/2)^2 计算得到。
"""

import argparse
import csv
import time
from collections import deque
from datetime import datetime
import math

try:
    import numpy as np
    import matplotlib.pyplot as plt
    import nidaqmx
    from nidaqmx.constants import AcquisitionType
except ImportError as exc:
    print("缺少依赖，请先安装: numpy matplotlib nidaqmx")
    print(exc)
    raise

from syringe_control import SyringePump


MM_TO_UL_AREA = math.pi * (4.73 / 2) ** 2  # mm^2 -> µL/mm (since 1 mm^3 = 1 µL)


def mm_for_ul(ul: float) -> float:
    return ul / MM_TO_UL_AREA


def ul_for_mm(mm: float) -> float:
    return mm * MM_TO_UL_AREA


def run_titration(
    port: str,
    daq_device: str,
    ao_channel: str,
    ao_voltage: float,
    aspirate_ul: float,
    aspirate_speed_mm_s: float,
    dispense_speed_mm_s: float,
    sample_rate: float,
    avg_window: int,
    csv_path: str | None,
    png_path: str | None,
):
    """执行滴定流程（按上方说明）。"""
    # 计算距离
    aspirate_mm = mm_for_ul(aspirate_ul)

    print(f"注射器内径 4.73 mm，面积 ≈ {MM_TO_UL_AREA:.3f} µL/mm")
    print(f"计划吸取 {aspirate_ul:.1f} µL ≈ {aspirate_mm:.2f} mm")

    pump = SyringePump(port=port)

    try:
        print("Please prepare the titration reagents in sequence and confirm each step.")
        input("1) Add 1 mL 0.02 mol/L (approx.) MgSO4, then press Enter to confirm... ")
        input("2) Add 50 μL pH = 10 ammonia buffer, then press Enter to confirm... ")
        input("3) Add 10~20 μL Eriochrome Black T indicator, then press Enter to confirm... ")
        input("4) Add 500 μL 0.02 mol/L EDTA (pre-add), then press Enter to confirm... ")
        input("Please hand-push the plunger to the minimum aspirating volume position and press Enter to confirm... ")
        input("Please immerse the needle in the EDTA solution and press Enter to confirm... ")
        

        # 吸取动作（后退）
        print(f"开始后退吸取 {aspirate_ul:.1f} µL ({aspirate_mm:.2f} mm) @ {aspirate_speed_mm_s:.3f} mm/s")
        pump.set_speed_unit_mm_per_s()
        pump.set_speed(aspirate_speed_mm_s)
        aspirate_run_time = pump.set_time_from_distance(aspirate_mm, aspirate_speed_mm_s)
        pump.save_params()

        pump.auto_backward()
        # 等待硬件完成信号 f1d（超时保护 = 预计时间 + 5s）
        aspirate_timeout = aspirate_run_time + 5.0
        aspirate_start = time.time()
        aspirate_buffer = ""
        while (time.time() - aspirate_start) < aspirate_timeout:
            if pump.ser.in_waiting:
                data = pump.ser.read(pump.ser.in_waiting).decode(errors='ignore')
                aspirate_buffer += data
                if 'f1d' in aspirate_buffer:
                    print("【硬件完成】吸取动作完成(f1d)")
                    break
            time.sleep(0.01)
        print(f"Aspirate complete. Elapsed: {time.time() - aspirate_start:.2f} s")
        input("Please place the needle into the cuvette and press Enter to continue...")

        # 准备 CSV
        if csv_path is None:
            csv_path = datetime.now().strftime("titration_%Y%m%d_%H%M%S.csv")
        csv_file = open(csv_path, "w", newline="", encoding="utf-8")
        print(f"Saving results to {csv_path}")
        writer = csv.writer(csv_file)
        writer.writerow(["timestamp", "time_s", "disp_mm", "disp_ul", "raw_V", "avg_V"])

        # AO 设置并保持
        ao_name = f"{daq_device}/{ao_channel}"
        ai_name = f"{daq_device}/ai0"
        print(f"设置 AO {ao_name} = {ao_voltage} V 并开始滴定采样 ({sample_rate} Hz)")

        # DAQ 初始化并清理残留任务
        import nidaqmx.system
        system = nidaqmx.system.System.local()
        _ = system.driver_version
        for task in system.tasks:
            try:
                task.control(nidaqmx.constants.TaskMode.KILL)
            except Exception:
                pass

        interval = 1.0 / sample_rate
        total_dispense_mm = aspirate_mm  # 不允许超过吸取量
        dispense_run_time = total_dispense_mm / dispense_speed_mm_s
        print(f"Starting dispense for {total_dispense_mm:.2f} mm, estimated {dispense_run_time:.2f} s at {dispense_speed_mm_s:.3f} mm/s")

        timestamps = []
        disp_mm_list = []
        disp_ul_list = []
        raw_vs = []
        avg_vs = []

        window = deque(maxlen=avg_window)

        with nidaqmx.Task() as ao_task, nidaqmx.Task() as ai_task:
            ao_task.ao_channels.add_ao_voltage_chan(ao_name)
            ai_task.ai_channels.add_ai_voltage_chan(ai_name)

            # 写入 AO 并保持
            ao_task.write(ao_voltage)
            print("AO set, waiting 3 seconds for LED stabilization...")
            time.sleep(3.0)

            # 启动恒速前进（设置时间 → 保存参数 → 硬件自动运行）
            pump.set_speed_unit_mm_per_s()
            pump.set_speed(dispense_speed_mm_s)
            dispense_run_time = pump.set_time_from_distance(total_dispense_mm, dispense_speed_mm_s)
            pump.save_params()
            pump.auto_forward()

            start = time.perf_counter()
            end_time = start + dispense_run_time
            samples = 0
            hw_completed = False

            try:
                while True:
                    t0 = time.perf_counter()
                    if t0 >= end_time:
                        break
                    if hw_completed:
                        break

                    # 检查硬件完成信号 f1d（泵可能提前结束）
                    if pump.ser.in_waiting:
                        data = pump.ser.read(pump.ser.in_waiting).decode(errors='ignore')
                        if 'f1d' in data:
                            print("【硬件完成】滴定注射完成(f1d)")
                            hw_completed = True
                            # 收到 f1d 后仍需采完当前点再退出

                    measured = ai_task.read()
                    if isinstance(measured, list):
                        measured = measured[0]

                    elapsed = t0 - start
                    dispensed_mm = min(elapsed * dispense_speed_mm_s, total_dispense_mm)
                    dispensed_ul = ul_for_mm(dispensed_mm)

                    window.append(measured)
                    avg_v = float(sum(window) / len(window))

                    timestamps.append(elapsed)
                    disp_mm_list.append(dispensed_mm)
                    disp_ul_list.append(dispensed_ul)
                    raw_vs.append(measured)
                    avg_vs.append(avg_v)

                    writer.writerow([datetime.now().isoformat(), f"{elapsed:.6f}", f"{dispensed_mm:.6f}", f"{dispensed_ul:.6f}", f"{measured:.6f}", f"{avg_v:.6f}"])

                    samples += 1
                    t1 = time.perf_counter()
                    to_sleep = interval - (t1 - t0)
                    if to_sleep > 0:
                        # 如果距离结束时间更近，睡眠到结束时间
                        remaining = end_time - t1
                        if remaining <= 0:
                            break
                        time.sleep(min(to_sleep, remaining))

                # Final sample at exact target volume if needed
                if not hw_completed:
                    final_elapsed = dispense_run_time
                    final_mm = total_dispense_mm
                    final_ul = ul_for_mm(final_mm)
                    if not timestamps or timestamps[-1] < final_elapsed:
                        final_measured = ai_task.read()
                        if isinstance(final_measured, list):
                            final_measured = final_measured[0]
                        window.append(final_measured)
                        final_avg_v = float(sum(window) / len(window))
                        timestamps.append(final_elapsed)
                        disp_mm_list.append(final_mm)
                        disp_ul_list.append(final_ul)
                        raw_vs.append(final_measured)
                        avg_vs.append(final_avg_v)
                        writer.writerow([datetime.now().isoformat(), f"{final_elapsed:.6f}", f"{final_mm:.6f}", f"{final_ul:.6f}", f"{final_measured:.6f}", f"{final_avg_v:.6f}"])

            except KeyboardInterrupt:
                print("检测到中断，停止滴定...")

            finally:
                pump.stop()
                # 还原 AO 到 0V
                try:
                    ao_task.write(0.0)
                except Exception:
                    pass

        csv_file.close()

        print(f"滴定结束，共采集 {len(raw_vs)} 点，累计体积 {disp_ul_list[-1] if disp_ul_list else 0:.3f} µL")

        # 绘图：电压（原始/平均）和累积体积
        fig, ax1 = plt.subplots(figsize=(10, 4))
        ax1.plot(timestamps, raw_vs, label="raw V", alpha=0.4)
        ax1.plot(timestamps, avg_vs, label=f"avg V (window={avg_window})", color="tab:blue")
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Voltage (V)")
        ax1.grid(True)

        ax2 = ax1.twinx()
        ax2.plot(timestamps, disp_ul_list, label="cumulative µL", color="tab:orange")
        ax2.set_ylabel("Cumulative Volume (µL)")

        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

        plt.title(f"Titration - {aspirate_ul:.0f} µL aspirated, {sample_rate} Hz, dispense speed {dispense_speed_mm_s} mm/s")
        plt.tight_layout()
        if png_path:
            plt.savefig(png_path)
            print(f"图像已保存到 {png_path}")
        plt.show()

    finally:
        pump.close()


def parse_args():
    parser = argparse.ArgumentParser(description="注射器泵滴定控制脚本")
    parser.add_argument("--port", default="COM5")
    parser.add_argument("--daq", default="Dev3")
    parser.add_argument("--ao", default="ao0")
    parser.add_argument("--ao-voltage", type=float, default=2.0)
    parser.add_argument("--aspirate-ul", type=float, default=700.0)
    parser.add_argument("--aspirate-speed-mm-s", type=float, default=2.0)
    parser.add_argument("--dispense-speed-mm-s", type=float, default=1.0)
    parser.add_argument("--rate", type=float, default=100.0)
    parser.add_argument("--avg-window", type=int, default=11)
    parser.add_argument("--csv", default=None, nargs='?')
    parser.add_argument("--png", default=None)
    return parser.parse_args()


def main():
    args = parse_args()
    run_titration(
        port=args.port,
        daq_device=args.daq,
        ao_channel=args.ao,
        ao_voltage=args.ao_voltage,
        aspirate_ul=args.aspirate_ul,
        aspirate_speed_mm_s=args.aspirate_speed_mm_s,
        dispense_speed_mm_s=args.dispense_speed_mm_s,
        sample_rate=args.rate,
        avg_window=args.avg_window,
        csv_path=args.csv,
        png_path=args.png,
    )


if __name__ == "__main__":
    main()
