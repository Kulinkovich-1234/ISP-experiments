import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType
import time

# ================= 配置参数 =================
DEVICE_NAME = "Dev1"
CH_AO = "ao1"                  # 压电蜂鸣器连接的模拟输出通道

# 正弦波参数
FREQ = 300.0                  # 信号频率 (Hz)，1kHz 为人耳敏感频率
AMPLITUDE = 1                # 信号幅度 (V)，请根据蜂鸣器规格调整（通常 1~5V）
OFFSET = 0                   # 直流偏置 (V)

# 采样参数
SAMPLE_RATE = 5000             # 采样率 (Hz)，应远大于信号频率（至少 2倍，通常 5~10倍）
DURATION = 5.0                 # 输出持续时间 (秒)，若需无限循环可设为 None
# ============================================

# 计算总的采样点数
num_samples = int(SAMPLE_RATE * DURATION) if DURATION else SAMPLE_RATE * 2  # 若持续输出则至少两秒数据

# 生成时间轴
t = np.linspace(0, num_samples / SAMPLE_RATE, num_samples, endpoint=False)
# 生成正弦波数据
sine_wave = OFFSET + AMPLITUDE * np.sin(2 * np.pi * FREQ * t)

print("=" * 60)
print("        NI DAQ 压电蜂鸣器正弦波测试")
print(f"        通道: {DEVICE_NAME}/{CH_AO}")
print(f"        频率: {FREQ} Hz, 幅度: {AMPLITUDE} Vpp, 偏置: {OFFSET} V")
print(f"        采样率: {SAMPLE_RATE} Hz, 持续时间: {DURATION} 秒")
print("=" * 60)
print("程序开始输出正弦波... 按 Ctrl+C 提前停止。")

try:
    with nidaqmx.Task() as task:
        # 添加模拟输出通道（根据实际 DAQ 量程设置 min_val/max_val）
        task.ao_channels.add_ao_voltage_chan(
            f"{DEVICE_NAME}/{CH_AO}",
            min_val=-AMPLITUDE-OFFSET-0.5,   # 略小于最小可能电压
            max_val=AMPLITUDE+OFFSET+0.5     # 略大于最大可能电压
        )
        
        # 配置采样时钟（连续输出模式，便于长时间测试）
        task.timing.cfg_samp_clk_timing(
            rate=SAMPLE_RATE,
            sample_mode=AcquisitionType.CONTINUOUS,  # 连续输出
            samps_per_chan=num_samples               # 缓冲区大小（至少为单次写入大小）
        )
        
        # 预先将正弦波数据写入输出缓冲区（连续循环写入）
        # 使用 write 的 auto_start=False 以便手动启动任务
        task.write(sine_wave, auto_start=False)
        
        # 启动任务
        task.start()
        
        if DURATION:
            # 固定时长输出
            time.sleep(DURATION)
        else:
            # 无限循环，直到用户中断
            print("正弦波持续输出中... 按 Ctrl+C 停止。")
            while True:
                time.sleep(0.1)
        
        # 停止任务
        task.stop()
        print("\n正常完成输出。")
        
except KeyboardInterrupt:
    print("\n检测到用户中断，正在停止输出...")
except nidaqmx.errors.DaqError as e:
    print(f"\nNI DAQ 驱动错误: {e}")
except Exception as e:
    print(f"\n发生未知错误: {e}")
finally:
    # 安全复位：确保 AO 通道电压归零
    print("正在复位 AO 通道电压至 0V...")
    try:
        with nidaqmx.Task() as reset_task:
            reset_task.ao_channels.add_ao_voltage_chan(f"{DEVICE_NAME}/{CH_AO}")
            reset_task.write(0.0, auto_start=True)
        print("电压已归零。")
    except Exception:
        print("复位失败，请手动断开或复位输出。")
    print("=" * 60)