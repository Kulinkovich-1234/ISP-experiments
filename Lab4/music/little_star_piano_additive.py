import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType
import time

# ================= 配置参数 =================
DEVICE_NAME = "Dev1"
CH_AO = "ao1"
AMPLITUDE = 4                    # 信号幅度 (V)
OFFSET = 0.0                       # 直流偏置 (V)
SAMPLE_RATE = 5000                 # Hz
BPM = 100
NOTE_DURATION = 60.0 / BPM         # 0.6 秒
SCALE_NOTE_DURATION = 0.4

# 半音阶频率表 (C4, C#4, D4, D#4, E4, F4, F#4, G4, G#4, A4, A#4, B4)
scale_freqs = [261.63, 277.18, 293.66, 311.13, 329.63, 349.23, 369.99, 392.00, 415.30, 440.00, 466.16, 493.88]
note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# ================= 生成包络函数 =================
def generate_envelope(duration, sample_rate, attack=0.02, decay=0.05, sustain=0.6, release=0.1):
    """生成标准的钢琴风格包络"""
    total_samples = int(sample_rate * duration)
    envelope = np.zeros(total_samples)

    # 起音阶段 (线性上升)
    attack_samples = int(attack * sample_rate)
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

    # 衰减阶段 (线性下降)
    decay_samples = int(decay * sample_rate)
    if decay_samples > 0:
        start_val = 1.0
        end_val = sustain
        envelope[attack_samples:attack_samples+decay_samples] = \
            np.linspace(start_val, end_val, decay_samples, endpoint=False)

    # 持续阶段 (保持)
    hold_samples = total_samples - attack_samples - decay_samples - int(release * sample_rate)
    hold_samples = max(hold_samples, 0)
    if hold_samples > 0:
        envelope[attack_samples+decay_samples : attack_samples+decay_samples+hold_samples] = sustain

    # 释放阶段 (线性下降到0)
    release_samples = int(release * sample_rate)
    if release_samples > 0:
        release_start = total_samples - release_samples
        envelope[release_start:] = np.linspace(sustain, 0, release_samples)

    return envelope

def generate_piano_tone(freq, amplitude, offset, duration, sample_rate):
    """使用加法合成 + 钢琴包络生成音色"""
    freq = freq * 2
    total_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, total_samples, endpoint=False)

    # 1. 生成基本正弦波
    tone = amplitude * np.sin(2 * np.pi * freq * t)

    # 2. 添加一些谐波来增加钢琴的“质感”和“亮度”
    # 钢琴音色通常包含少量的二次、三次谐波，这里我们添加一些轻微的谐波
    if freq <= 400:  # 低音区可以少些谐波，保持清晰
        harmonics = [
            (freq * 2, 0.15),   # 第二谐波
            (freq * 3, 0.05),   # 第三谐波
            (freq * 4, 0.02)    # 第四谐波
        ]
    else:  # 高音区可以多一些谐波，增加明亮度
        harmonics = [
            (freq * 2, 0.12),   # 第二谐波
            (freq * 3, 0.03),   # 第三谐波
            (freq * 4, 0.01)    # 第四谐波
        ]

    for harmonic_freq, harmonic_amp in harmonics:
        tone += amplitude * harmonic_amp * np.sin(2 * np.pi * harmonic_freq * t)

    # 3. 生成包络并应用到音符
    envelope = generate_envelope(duration, sample_rate)
    tone = tone * envelope

    # 4. 添加直流偏置
    tone = tone + offset
    return tone

def play_tone(freq, duration, amplitude=AMPLITUDE, offset=OFFSET):
    """播放一个音符"""
    waveform = generate_piano_tone(freq, amplitude, offset, duration, SAMPLE_RATE)
    with nidaqmx.Task() as task:
        task.ao_channels.add_ao_voltage_chan(
            f"{DEVICE_NAME}/{CH_AO}",
            min_val=-amplitude-offset-0.5,
            max_val=amplitude+offset+0.5
        )
        task.timing.cfg_samp_clk_timing(
            rate=SAMPLE_RATE,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=len(waveform)
        )
        task.write(waveform, auto_start=True)
        task.wait_until_done(timeout=duration + 0.1)

def run_self_test():
    """自检音阶：C4 -> B4 -> C4"""
    print("\n🎵 开始自检音阶（加法合成+钢琴包络）：C4 → B4 → C4")
    # 上行
    for freq in scale_freqs:
        print(f"播放 {freq:.1f} Hz")
        play_tone(freq, SCALE_NOTE_DURATION)
        time.sleep(0.05)
    # 下行
    for freq in reversed(scale_freqs):
        print(f"播放 {freq:.1f} Hz")
        play_tone(freq, SCALE_NOTE_DURATION)
        time.sleep(0.05)

def main():
    print("="*60)
    print("   NI DAQ 演奏《小星星》- 加法合成 + 钢琴包络 (钢琴音色)")
    print(f"    幅度: {AMPLITUDE} V, 偏置: {OFFSET} V")
    print(f"    采样率: {SAMPLE_RATE} Hz, 音符时长: {NOTE_DURATION}s")
    print("="*60)

    # 自检音阶
    if input("Run self-test scale (C4-B4-C4) with piano envelope? (y/n): ").lower() == 'y':
        run_self_test()

    confirm = input("\n✅ 音高稳定且正确？输入 y 继续演奏小星星，其他退出: ")
    if confirm.lower() != 'y':
        print("已取消。")
        with nidaqmx.Task() as reset_task:
            reset_task.ao_channels.add_ao_voltage_chan(f"{DEVICE_NAME}/{CH_AO}")
            reset_task.write(0.0, auto_start=True)
        return

    # 小星星旋律对应的频率 (C4, C4, G4, G4, A4, A4, G4, ...)
    melody_freqs = [
        261.63, 261.63, 392.00, 392.00, 440.00, 440.00, 392.00,   # 一闪一闪亮晶晶
        349.23, 349.23, 329.63, 329.63, 293.66, 293.66, 261.63,   # 满地都是小星星
        392.00, 392.00, 349.23, 349.23, 329.63, 329.63, 293.66,   # 挂在天空放光明
        392.00, 392.00, 349.23, 349.23, 329.63, 329.63, 293.66,   # 好像千万小眼睛
        261.63, 261.63, 392.00, 392.00, 440.00, 440.00, 392.00,   # 一闪一闪亮晶晶
        349.23, 349.23, 329.63, 329.63, 293.66, 293.66, 261.63    # 满面都是小星星
    ]

    note_names_melody = [
        "C", "C", "G", "G", "A", "A", "G",
        "F", "F", "E", "E", "D", "D", "C",
        "G", "G", "F", "F", "E", "E", "D",
        "G", "G", "F", "F", "E", "E", "D",
        "C", "C", "G", "G", "A", "A", "G",
        "F", "F", "E", "E", "D", "D", "C"
    ]

    print("\n🎵 开始演奏《小星星》...")
    try:
        for idx, (note_name, freq) in enumerate(zip(note_names_melody, melody_freqs), 1):
            play_tone(freq, NOTE_DURATION)
            print(f"[{idx:2d}] {note_name}4 ({freq:.1f} Hz)", end="  ")
            if idx % 7 == 0:
                print()
        print("\n演奏完成！")
    except KeyboardInterrupt:
        print("\n用户中断。")
    finally:
        print("复位电压至 0V...")
        with nidaqmx.Task() as reset_task:
            reset_task.ao_channels.add_ao_voltage_chan(f"{DEVICE_NAME}/{CH_AO}")
            reset_task.write(0.0, auto_start=True)
        print("完成。")
        print("="*60)

if __name__ == "__main__":
    main()