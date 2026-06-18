import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType
import time

# ================= 配置参数 =================
DEVICE_NAME = "Dev1"
CH_AO = "ao1"

AMPLITUDE = 3.0
OFFSET = 0.2
SAMPLE_RATE = 5000
BPM = 100
NOTE_DURATION = 60.0 / BPM       # 0.6 秒
SCALE_NOTE_DURATION = 0.4

DECAY_PER_PERIOD = 0.998         # 每周期衰减

# ================= 频率计算（十二平均律） =================
def note_to_freq(note_name, octave=4):
    note_map = {
        'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
        'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8,
        'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11
    }
    semitone = note_map[note_name] - 9
    freq = 440.0 * (2 ** ((semitone + (octave - 4) * 12) / 12))
    return freq

# ================= 稳定的 Karplus-Strong (修正周期取整) =================
def generate_karplus_strong_stable(freq, amplitude, offset, duration, sample_rate,
                                   decay_per_period=DECAY_PER_PERIOD, iterations=12):
    """
    使用确定性激励（单位脉冲），周期长度四舍五入，保证音准。
    """
    # 关键修改：四舍五入取整，避免截断误差
    period_len = max(2, round(sample_rate / freq))
    
    total_samples = int(sample_rate * duration)
    
    # 1. 确定性激励：单个脉冲
    excitation = np.zeros(period_len)
    excitation[0] = 1.0
    
    # 2. 迭代循环平均滤波
    buffer = excitation.copy()
    for _ in range(iterations):
        new_buffer = np.zeros_like(buffer)
        for i in range(period_len):
            new_buffer[i] = (buffer[i] + buffer[(i+1) % period_len]) * 0.5
        buffer = new_buffer
    single_period = buffer.copy()
    
    # 3. 重复周期并应用每周期衰减
    num_periods = (total_samples + period_len - 1) // period_len
    waveform = np.tile(single_period, num_periods)[:total_samples]
    
    for i in range(num_periods):
        start = i * period_len
        end = min((i+1) * period_len, total_samples)
        waveform[start:end] *= (decay_per_period ** i)
    
    # 4. 归一化到目标幅度
    peak = np.max(np.abs(waveform))
    if peak > 1e-6:
        waveform = waveform / peak * amplitude
    
    waveform = waveform + offset
    return waveform

generate_karplus_strong = generate_karplus_strong_stable

# ================= 播放音符 =================
def play_tone(freq, duration, amplitude=AMPLITUDE, offset=OFFSET):
    waveform = generate_karplus_strong(freq, amplitude, offset, duration, SAMPLE_RATE)
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

# ================= 自检音阶（C4～B4，不上八度） =================
def run_self_test():
    print("\n🎵 自检音阶：C4 → B4 (半音阶上行) → 下行 (不升八度)")
    notes = []
    for note in ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']:
        notes.append((note, 4))
    # 上行
    for note, oct in notes:
        freq = note_to_freq(note, oct)
        print(f"播放 {note}{oct} → {freq:.1f} Hz")
        play_tone(freq, SCALE_NOTE_DURATION)
        time.sleep(0.05)
    # 下行
    for note, oct in notes[-2::-1]:
        freq = note_to_freq(note, oct)
        print(f"播放 {note}{oct} → {freq:.1f} Hz")
        play_tone(freq, SCALE_NOTE_DURATION)
        time.sleep(0.05)
    print("自检完成。")

# ================= 小星星旋律（C4～A4，不上八度） =================
melody_symbols = [
    "C", "C", "G", "G", "A", "A", "G",
    "F", "F", "E", "E", "D", "D", "C",
    "G", "G", "F", "F", "E", "E", "D",
    "G", "G", "F", "F", "E", "E", "D",
    "C", "C", "G", "G", "A", "A", "G",
    "F", "F", "E", "E", "D", "D", "C"
]
melody = [(name, note_to_freq(name, octave=4)) for name in melody_symbols]

# ================= 主程序 =================
def main():
    print("=" * 60)
    print("   NI DAQ 弦乐《小星星》- 修正音高版")
    print(f"    幅度: {AMPLITUDE} V, 偏置: {OFFSET} V, 衰减: {DECAY_PER_PERIOD}")
    print(f"    采样率: {SAMPLE_RATE} Hz, 音符时长: {NOTE_DURATION}s")
    print("    关键修改：不升八度 + 周期四舍五入，消除音高偏差")
    print("=" * 60)
    
    run_self_test()
    
    confirm = input("\n✅ 音高正确（E/F/A 无偏差）？输入 y 演奏小星星，其他退出: ")
    if confirm.lower() != 'y':
        print("已取消。")
        with nidaqmx.Task() as reset_task:
            reset_task.ao_channels.add_ao_voltage_chan(f"{DEVICE_NAME}/{CH_AO}")
            reset_task.write(0.0, auto_start=True)
        return
    
    print("\n🎵 演奏《小星星》...")
    try:
        for idx, (note_name, freq) in enumerate(melody, 1):
            # 关键修改：直接使用原始频率，不再乘以 2
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
        print("=" * 60)

if __name__ == "__main__":
    main()