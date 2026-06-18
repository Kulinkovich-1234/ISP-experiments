import time
import nidaqmx

# ================= 配置参数 =================
DEVICE_NAME = "Dev1"
CH_AO = "ao0"          # 控制三极管基极的模拟输出通道

# 严格根据 47Ω 电阻计算出的安全电压极限
V_ON = 1.0             # 吸合电压 (绝对不能超过 1.0V，否则有烧毁风险)
V_OFF = 0.0            # 释放电压 (0V 彻底断开)

PULSE_INTERVAL = 1   # 状态维持时间 (1秒吸合，1秒释放)
# ============================================

print("=" * 60)
print("        NI DAQ 电磁铁周期性吸合/释放控制程序")
print(f"        [警告]: 当前配置基极电阻为 47Ω，控制电压已严格限幅为 {V_ON}V")
print("=" * 60)
print("程序正在运行中... 电磁铁每秒切换一次状态。")
print("按下 【Ctrl + C】 可安全终止程序并关闭电磁铁。")
print("-" * 60)

try:
    with nidaqmx.Task() as task_ao:
        # 添加模拟输出通道
        task_ao.ao_channels.add_ao_voltage_chan(f"{DEVICE_NAME}/{CH_AO}")
        
        count = 1
        while True:
            # 1. 吸合阶段
            print(f"[{count}] 状态: 吸合 (ON)  -> 输出电压: {V_ON} V")
            task_ao.write(V_ON, auto_start=True)
            time.sleep(PULSE_INTERVAL)
            
            # 2. 释放阶段
            print(f"[{count}] 状态: 释放 (OFF) -> 输出电压: {V_OFF} V")
            task_ao.write(V_OFF, auto_start=True)
            time.sleep(PULSE_INTERVAL)
            
            count += 1

except KeyboardInterrupt:
    print("\n\n检测到用户终止信号 (Ctrl+C)。")
except nidaqmx.errors.DaqError as e:
    print(f"\nNI DAQ 驱动错误: {e}")
except Exception as e:
    print(f"\n发生未知错误: {e}")
finally:
    # 无论程序是正常退出、被用户强行终止还是发生报错，
    # finally 块都会强制执行，确保将 AO 口电压清零，防止电磁铁长通过热。
    print("正在安全复位 AO 通道电压至 0V...")
    try:
        with nidaqmx.Task() as task_safety:
            task_safety.ao_channels.add_ao_voltage_chan(f"{DEVICE_NAME}/{CH_AO}")
            task_safety.write(0.0, auto_start=True)
        print("电路已安全切断。")
    except Exception:
        print("复位失败，请手动关闭外部 12V 动力电源！")
    print("=" * 60)