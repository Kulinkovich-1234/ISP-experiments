import csv
import datetime
import msvcrt  # Windows 标准库，用于实现非阻塞键盘输入监听
import time
import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType

# ================= 最新配置参数 =================
DEVICE_NAME = "Dev1"
CH_AO = "ao1"          # 供电输出口
CH_AI_SOURCE = "ai1"   # 实时测量总电源电压的通道
CH_AI_NTC = "ai2"      # 实时测量热敏电阻分压的通道
V_TARGET = 3.3         # AO1 设定的目标输出电压 (V)

# 已同步为你最新提供的固定电阻值
R_REF = 75300.0         # 固定电阻值 (75.3 kΩ)

# 基于你之前的精密校准报告所得的 NTC 物理常数
B_CONSTANT = 3588.4    # B 常数
R0_25C = 8326.20       # 25℃ 时的标称阻值 (Ω)
T0_25C = 25.0 + 273.15 # 25℃ 对应的开尔文绝对温度

# 采集与运行配置
SAMPLE_RATE = 1000     # 采样率 (Hz)
NUM_SAMPLES = 500      # 每次读取的点数（与你配置同步，增强防抖效果）
LOG_INTERVAL = 1.0     # 屏幕刷新与数据记录的时间间隔 (秒)
CSV_FILENAME = "temperature_log.csv"
# ============================================

def calculate_temperature(v_source, v_ntc):
    """根据实时比例电压、固定电阻和 B 值公式计算当前的摄氏度"""
    if v_ntc >= v_source or v_ntc <= 0:
        return None

    # 1. 动态计算当前 NTC 电阻值
    r_ntc = R_REF * v_ntc / (v_source - v_ntc)

    # 2. 代入 B 值公式计算开尔文温度: 1/T = 1/T0 + (1/B) * ln(R/R0)
    inv_T = 1.0 / T0_25C + (1.0 / B_CONSTANT) * np.log(r_ntc / R0_25C)
    t_kelvin = 1.0 / inv_T

    # 3. 转换为摄氏度
    t_celsius = t_kelvin - 273.15
    return t_celsius, r_ntc

print("=" * 60)
print("             NI DAQ 实时温度监测与记录系统")
print("=" * 60)
print(f"数据实时记录中... 刷新间隔: {LOG_INTERVAL} 秒")
print(f"随时在控制台输入 【q】 并回车，可安全退出并保存至 CSV。")
print("-" * 60)
print(f"{'当前时间 (Time)':<25}{'源电压(V)':<10}{'分压(V)':<10}{'当前阻值(Ω)':<12}{'实际温度(℃)'}")
print("-" * 60)

data_log = []

try:
    with nidaqmx.Task() as task_ao, nidaqmx.Task() as task_ai:
        # 1. 开启 AO 稳定供电
        task_ao.ao_channels.add_ao_voltage_chan(f"{DEVICE_NAME}/{CH_AO}")
        task_ao.write(V_TARGET, auto_start=True)

        # 2. 配置双通道同步有限点采集
        task_ai.ai_channels.add_ai_voltage_chan(f"{DEVICE_NAME}/{CH_AI_SOURCE}", min_val=0.0, max_val=4.0)
        task_ai.ai_channels.add_ai_voltage_chan(f"{DEVICE_NAME}/{CH_AI_NTC}", min_val=0.0, max_val=4.0)
        task_ai.timing.cfg_samp_clk_timing(
            rate=SAMPLE_RATE,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=NUM_SAMPLES
        )

        input_buffer = ""

        while True:
            start_time = time.time()

            # 3. 硬件缓冲区采集数据
            task_ai.start()
            voltages = task_ai.read(number_of_samples_per_channel=NUM_SAMPLES, timeout=2.0)
            task_ai.stop()  # 停止本次采集，为下一次腾出缓存

            v_src = np.mean(voltages[0])
            v_ntc = np.mean(voltages[1])

            # 4. 转换并解析温度
            result = calculate_temperature(v_src, v_ntc)
            if result is not None:
                current_temp, current_res = result
                time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # 5. 控制台实时单行数据打印
                print(f"{time_str:<25}{v_src:<10.4f}{v_ntc:<10.4f}{current_res:<12.2f}{current_temp:.2f} ℃")

                # 6. 暂存到内存中
                data_log.append({
                    "Timestamp": time_str,
                    "Source_Voltage(V)": round(v_src, 4),
                    "NTC_Voltage(V)": round(v_ntc, 4),
                    "Resistance(Ohm)": round(current_res, 2),
                    "Temperature(C)": round(current_temp, 2)
                })

            # 7. 非阻塞键盘监听 (Windows 专属机制，不卡死单片机/采集循环)
            while msvcrt.kbhit():
                char = msvcrt.getche().decode("utf-8", errors="ignore")
                if char == "\r" or char == "\n":  # 当检测到用户敲击回车
                    if input_buffer.strip().lower() == "q":
                        raise KeyboardInterrupt  # 抛出异常优雅退出
                    input_buffer = ""  # 清空缓冲区
                else:
                    input_buffer += char

            # 8. 严格控制 1.0 秒的采样节拍
            elapsed = time.time() - start_time
            sleep_time = LOG_INTERVAL - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

except KeyboardInterrupt:
    print("\n\n正在安全停止采集，准备将数据写入文件...")
except nidaqmx.errors.DaqError as e:
    print(f"\nNI DAQ 驱动发生异常: {e}")
except Exception as e:
    print(f"\n发生未预期错误: {e}")

# ================= 9. 数据汇总保存为 CSV =================
if data_log:
    headers = list(data_log[0].keys())
    with open(CSV_FILENAME, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data_log)

    print("=" * 60)
    print(f"【保存成功】共成功录得 {len(data_log)} 组定时温度历史数据！")
    print(f"文件保存路径: {CSV_FILENAME}")
    print("=" * 60)
else:
    print("\n未检测到有效采集数据，未生成 CSV 文件。")