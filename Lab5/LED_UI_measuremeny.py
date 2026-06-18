import nidaqmx
import numpy as np
import matplotlib.pyplot as plt
import time
import csv
from nidaqmx.constants import TerminalConfiguration

# ========== 配置 ==========
DEVICE = "Dev2"
R_REF = 46.2          # Ω
I_MAX = 0.020         # A
V_START = 0.0
V_END = 4.5           # 最大 AO0 电压（对应 97 mA 空载，但电流会被 I_MAX 截断）
V_STEP = 0.02
SETTLE_TIME = 0.01    # 10 ms

voltages = np.arange(V_START, V_END + V_STEP/2, V_STEP)

# 诊断阈值：IN+ 与 IN- 允许的最大误差（超过则警告）
VIRTUAL_SHORT_TOLERANCE = 0.1   # V

with nidaqmx.Task() as ao_task, nidaqmx.Task() as ai_task:
    # AO0
    ao_task.ao_channels.add_ao_voltage_chan(f"{DEVICE}/ao0")
    
    # 三个 AI 通道: AI0, AI1, AI2
    # 注意：这里假设 AI2 也使用 RSE 单端接法
    ai_task.ai_channels.add_ai_voltage_chan(
        f"{DEVICE}/ai0:2",   # 连续通道 ai0, ai1, ai2
        terminal_config=TerminalConfiguration.RSE
    )
    
    print("开始扫描，同时监测 IN+ 和 IN- 电压...")
    data = []   # 存储 (U_LED, I_LED)
    
    try:
        for v_set in voltages:
            ao_task.write(v_set, auto_start=True)
            time.sleep(SETTLE_TIME)
            
            # 读取三个电压：返回 [[AI0_1], [AI1_1], [AI2_1]]  (每个通道单个采样)
            ai_vals = ai_task.read(number_of_samples_per_channel=1)
            v_out   = ai_vals[0][0]   # 运放输出电压 (AI0)
            v_inp   = ai_vals[1][0]   # IN+ 电压 (AI1)
            v_inm   = ai_vals[2][0]   # IN- 电压 (AI2)
            
            # 计算 LED 电流和正向电压
            i_led = v_inm / R_REF      # 流过参考电阻的电流 = LED 电流
            u_led = v_out - v_inm      # 运放输出减去 IN- = LED 两端电压
            
            # 诊断虚短
            diff = abs(v_inp - v_inm)
            if diff > VIRTUAL_SHORT_TOLERANCE:
                print(f"⚠️ 警告: 虚短条件不满足 |IN+ - IN-| = {diff:.3f} V (AO0={v_set:.3f}V)")
                # 可选择停止：若差值太大且持续，说明反馈失效
                # 这里只警告，不停止，让您看到现象
                # 若想停止，取消下面注释:
                # if diff > 0.5:
                #     print("反馈严重异常，停止扫描。")
                #     break
            
            # 过流保护
            if i_led > I_MAX:
                print(f"电流达到 {i_led*1000:.2f} mA (> {I_MAX*1000} mA)，停止扫描。")
                break
            
            data.append((u_led, i_led))
            print(f"AO0={v_set:.3f}V | OUT={v_out:.3f}V IN+={v_inp:.3f}V IN-={v_inm:.3f}V | "
                  f"U_LED={u_led:.3f}V I_LED={i_led*1000:.2f}mA")
    
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"错误: {e}")
    
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
        print("数据已保存为 led_ui_data.csv")
        plt.show()
    else:
        print("无有效数据。")