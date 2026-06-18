import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType
import time

# ================= 配置参数 =================
DEVICE_NAME = "Dev1"
CH_AO = "ao1"                    # 压电蜂鸣器连接的模拟输出通道

# 固定波形参数
AMPLITUDE = 3                  # 信号幅度 (V)
OFFSET = 0.2                     # 直流偏置 (V)

# 采样参数（根据您的设备最大 5 kHz）
SAMPLE_RATE = 5000               # Hz

# 乐曲参数
BPM = 100                        # 拍速 (拍/分钟)
NOTE_DURATION = 60.0 / BPM       # 四分音符时长 (秒) = 0.6 秒

# 小星星旋律（音符序列，每个元素为 (音名, 频率Hz)）
melody = [
    ("C", 261.63), ("C", 261.63), ("G", 392.00), ("G", 392.00),
    ("A", 440.00), ("A", 440.00), ("G", 392.00),
    ("F", 349.23), ("F", 349.23), ("E", 329.63), ("E", 329.63),
    ("D", 293.66), ("D", 293.66), ("C", 261.63),
    ("G", 392.00), ("G", 392.00), ("F", 349.23), ("F", 349.23),
    ("E", 329.63), ("E", 329.63), ("D", 293.66),
    ("G", 392.00), ("G", 392.00), ("F", 349.23), ("F", 349.23),
    ("E", 329.63), ("E", 329.63), ("D", 293.66),
    ("C", 261.63), ("C", 261.63), ("G", 392.00), ("G", 392.00),
    ("A", 440.00), ("A", 440.00), ("G", 392.00),
    ("F", 349.23), ("F", 349.23), ("E", 329.63), ("E", 329.63),
    ("D", 293.66), ("D", 293.66), ("C", 261.63)
]

# ================= 辅助函数 =================
def generate_tone(freq, amplitude, offset, duration, sample_rate):
    """生成正弦波数据（numpy数组）"""
    num_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)
    waveform = offset + amplitude * np.sin(2 * np.pi * freq * t)
    return waveform

# ================= 主程序 =================
print("=" * 60)
print("        NI DAQ 演奏《小星星》")
print(f"        通道: {DEVICE_NAME}/{CH_AO}")
print(f"        幅度: {AMPLITUDE} Vpp, 偏置: {OFFSET} V")
print(f"        采样率: {SAMPLE_RATE} Hz, 拍速: {BPM} BPM, 音符时长: {NOTE_DURATION:.2f}s")
print(f"        总音符数: {len(melody)}")
print("=" * 60)
print("开始演奏... 按 Ctrl+C 提前停止。")

try:
    for idx, (note_name, freq) in enumerate(melody, 1):
        # 生成当前音符的波形
        waveform = generate_tone(freq*2, AMPLITUDE, OFFSET, NOTE_DURATION, SAMPLE_RATE)
        
        # 为每个音符创建一个独立的任务
        with nidaqmx.Task() as task:
            # 添加模拟输出通道
            task.ao_channels.add_ao_voltage_chan(
                f"{DEVICE_NAME}/{CH_AO}",
                min_val=-AMPLITUDE-OFFSET-0.5,
                max_val=AMPLITUDE+OFFSET+0.5
            )
            # 配置采样时钟（有限采样模式）
            task.timing.cfg_samp_clk_timing(
                rate=SAMPLE_RATE,
                sample_mode=AcquisitionType.FINITE,
                samps_per_chan=len(waveform)
            )
            # 写入数据并自动开始生成
            task.write(waveform, auto_start=True)
            # 等待生成完成
            task.wait_until_done(timeout=NOTE_DURATION + 0.1)
        
        # 打印进度
        print(f"[{idx:2d}] {note_name} ({freq:.1f} Hz)", end="  ")
        if idx % 7 == 0:
            print()   # 每行7个音符（一小节）
    
    print("\n\n演奏完成！")
        
except KeyboardInterrupt:
    print("\n\n检测到用户中断，正在停止演奏...")
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