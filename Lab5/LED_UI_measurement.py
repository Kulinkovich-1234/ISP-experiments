import nidaqmx
import numpy as np
import matplotlib.pyplot as plt
import time
import csv
import traceback
from nidaqmx.constants import TerminalConfiguration

# ========== 配置 ==========
DEVICE = "Dev2"                # 请确认设备名（在NI MAX中查看）
R_REF = 46.2                   # Ω
I_MAX = 0.020                  # A
V_START = 0.0
V_END = 4.5
V_STEP = 0.02
SETTLE_TIME = 0.01             # 10 ms
VIRTUAL_SHORT_TOLERANCE = 0.1  # V

voltages = np.arange(V_START, V_END + V_STEP/2, V_STEP)

# ========== 创建任务 ==========
ao_task = nidaqmx.Task()
ai_task = nidaqmx.Task()

try:
    # 配置 AO0
    ao_task.ao_channels.add_ao_voltage_chan(f"{DEVICE}/ao0")
    print("AO0 通道已添加")
    
    # 分别添加三个 AI 通道（单端模式）
    ai_task.ai_channels.add_ai_voltage_chan(f"{DEVICE}/ai0", terminal_config=TerminalConfiguration.RSE)
    ai_task.ai_channels.add_ai_voltage_chan(f"{DEVICE}/ai1", terminal_config=TerminalConfiguration.RSE)
    ai_task.ai_channels.add_ai_voltage_chan(f"{DEVICE}/ai2", terminal_config=TerminalConfiguration.RSE)
    print("AI0, AI1, AI2 通道已添加")
    
    print("开始扫描...")
    data = []
    
    for i, v_set in enumerate(voltages):
        print(f"\n步骤 {i+1}/{len(voltages)}: 设置 AO0 = {v_set:.3f} V")
        
        # 写入 AO0（自动开始输出）
        ao_task.write(v_set, auto_start=True)
        print("  AO0 写入完成")
        
        # 等待稳定
        time.sleep(SETTLE_TIME)
        print("  等待稳定结束")
        
        # 逐个读取 AI 通道（防止结构错误，同时设置超时）
        try:
            v_out = ai_task.read(1, timeout=1.0)[0]   # 读取 AI0 一个样本
            print(f"  AI0 读取: {v_out:.4f} V")
            v_inp = ai_task.read(1, timeout=1.0)[0]   # 读取 AI1
            print(f"  AI1 读取: {v_inp:.4f} V")
            v_inm = ai_task.read(1, timeout=1.0)[0]   # 读取 AI2
            print(f"  AI2 读取: {v_inm:.4f} V")
        except nidaqmx.errors.DaqError as e:
            print(f"  读取超时或错误: {e}")
            break
        
        # 计算电流和 LED 电压
        i_led = v_inm / R_REF
        u_led = v_out - v_inm
        
        # 诊断虚短
        diff = abs(v_inp - v_inm)
        if diff > VIRTUAL_SHORT_TOLERANCE:
            print(f"  ⚠️ 虚短差值过大: {diff:.3f} V")
            # 如果想差值过大就停止，取消下面注释
            # if diff > 0.5:
            #     print("  反馈严重异常，停止扫描")
            #     break
        
        # 过流保护
        if i_led > I_MAX:
            print(f"  ⚠️ 电流 {i_led*1000:.2f} mA 超过限制，停止扫描")
            break
        
        data.append((u_led, i_led))
        print(f"  => U_LED = {u_led:.3f} V, I_LED = {i_led*1000:.2f} mA")
    
    # 绘图与保存
    if data:
        u_vals, i_vals = zip(*data)
        plt.figure(figsize=(8,6))
        plt.plot(i_vals, u_vals, 'o-', linewidth=2)
        plt.xlabel("Current (A)")
        plt.ylabel("LED Voltage (V)")
        plt.title("U-I Characteristic of LED")
        plt.grid(True)
        with open("led_ui_data.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["U_LED (V)", "I_LED (A)"])
            writer.writerows(data)
        print("\n数据已保存为 led_ui_data.csv")
        plt.show()
    else:
        print("\n未采集到有效数据")
        
except Exception as e:
    print(f"发生未预期异常: {e}")
    traceback.print_exc()
finally:
    # 确保任务停止并释放
    ao_task.close()
    ai_task.close()
    print("任务已关闭")