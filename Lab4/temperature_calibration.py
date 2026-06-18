import time
import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType

# ================= 配置参数 =================
DEVICE_NAME = "Dev1"
CH_AO = "ao1"          # 供电输出口
CH_AI_SOURCE = "ai1"   # 实时测量总电源电压的通道
CH_AI_NTC = "ai2"      # 实时测量热敏电阻分压的通道
V_TARGET = 3.3         # AO1 设定的目标输出电压 (V)

# 【重要提示】请确保你已经把固定电阻换成了 47kΩ 或 51kΩ 左右！
R_REF = None            # TODO: Measure and replace with your reference resistor value (ohms).
                        # A typical value for NTC thermistor circuits is ~47k-75k ohms.

SAMPLE_RATE = 1000     # 采样率
NUM_SAMPLES = 500      # 每次测量的读取点数（取平均值防抖）
# ============================================

def measure_ntc_resistance(task_ai):
    """同时读取 AI1 和 AI2，利用实时比例计算当前 NTC 的电阻值"""
    # read() 会返回一个二维列表：[ [AI1的数据], [AI2的数据] ]
    voltages = task_ai.read(number_of_samples_per_channel=NUM_SAMPLES, timeout=2.0)
    
    v_source_actual = np.mean(voltages[0])  # AI1 的实时真实总电压
    v_ntc_actual = np.mean(voltages[1])    # AI2 的实时热敏电阻分压
    
    # 基于实时电压比例反推 NTC 电阻
    if v_ntc_actual >= v_source_actual or v_ntc_actual <= 0:
        raise ValueError(
            f"检测到异常电压！总源电压(AI1): {v_source_actual:.4f}V, NTC分压(AI2): {v_ntc_actual:.4f}V。\n"
            f"请检查电路是否接反，或固定电阻是否依然过小。"
        )
        
    r_ntc = R_REF * v_ntc_actual / (v_source_actual - v_ntc_actual)
    return v_source_actual, v_ntc_actual, r_ntc

print("=" * 60)
print("     NTC 热敏电阻动态比例测量与参数拟合程序 (已启用AI1实时参考)")
print("=" * 60)

try:
    # 建立 AO 供电任务和 AI 双通道采集任务
    with nidaqmx.Task() as task_ao, nidaqmx.Task() as task_ai:
        # 1. 配置 AO1 输出
        task_ao.ao_channels.add_ao_voltage_chan(f"{DEVICE_NAME}/{CH_AO}")
        task_ao.write(V_TARGET, auto_start=True)
        
        # 2. 同时添加两个 AI 通道：AI1 和 AI2
        # 注意添加的顺序：先添加的在 task.read() 返回列表的第 0 项，后添加的在第 1 项
        task_ai.ai_channels.add_ai_voltage_chan(f"{DEVICE_NAME}/{CH_AI_SOURCE}", min_val=0.0, max_val=4.0)
        task_ai.ai_channels.add_ai_voltage_chan(f"{DEVICE_NAME}/{CH_AI_NTC}", min_val=0.0, max_val=4.0)
        
        # 配置时钟
        task_ai.timing.cfg_samp_clk_timing(
            rate=SAMPLE_RATE, 
            sample_mode=AcquisitionType.FINITE, 
            samps_per_chan=NUM_SAMPLES
        )

        # ------------------ 测量点 1 ------------------
        print("\n--- [测量点 1] ---")
        t1_celsius = float(input("请输入当前环境的实际温度 1 (℃): "))
        input("请将热敏电阻放入该环境，完全稳定后按【回车】开始采样...")
        v_src1, v_ntc1, r1 = measure_ntc_resistance(task_ai)
        print(f"采样成功 -> 实际源压(AI1): {v_src1:.4f} V | NTC分压(AI2): {v_ntc1:.4f} V")
        print(f"           计算所得电阻 R1: {r1:.2f} Ω")
        
        # ------------------ 测量点 2 ------------------
        print("\n--- [测量点 2] ---")
        t2_celsius = float(input("请输入当前环境的实际温度 2 (℃): "))
        input("请将热敏电阻放入第二个环境，完全稳定后按【回车】开始采样...")
        v_src2, v_ntc2, r2 = measure_ntc_resistance(task_ai)
        print(f"采样成功 -> 实际源压(AI1): {v_src2:.4f} V | NTC分压(AI2): {v_ntc2:.4f} V")
        print(f"           计算所得电阻 R2: {r2:.2f} Ω")

        # ------------------ 数学拟合计算 ------------------
        T1 = t1_celsius + 273.15
        T2 = t2_celsius + 273.15
        
        # 计算 B 常数
        fit_B = np.log(r1 / r2) / (1.0 / T1 - 1.0 / T2)
        
        # 反推标准 25℃ 下的标称阻值 R0
        T0 = 25.0 + 273.15
        fit_R0 = r1 / np.exp(fit_B * (1.0 / T1 - 1.0 / T0))
        
        # ------------------ 输出结果 ------------------
        print("\n" + "=" * 50)
        print("             热敏电阻参数拟合报告 (精密比例法)")
        print("=" * 50)
        print(f" 拟合出来的 B 常数 (B-Constant) : {fit_B:.1f} K")
        print(f" 25℃ 标称阻值 (R0 @ 25℃)       : {fit_R0:.2f} Ω (约 {fit_R0/1000:.2f} kΩ)")
        print("-" * 50)
        print("【您的精密温度转换公式】:")
        print(f" 1/T = 1/298.15 + (1/{fit_B:.1f}) * ln(R_ntc/{fit_R0:.2f})")
        print("=" * 50)

except nidaqmx.errors.DaqError as e:
    print(f"\nNI DAQ 驱动错误: {e}")
except ValueError as e:
    print(f"\n数据错误: {e}")
except Exception as e:
    print(f"\n发生其他意外错误: {e}")