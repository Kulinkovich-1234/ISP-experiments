import time
import threading
import numpy as np
import nidaqmx
from nidaqmx.constants import AcquisitionType, LineGrouping

# ================= 硬件配置 =================
DEVICE_NAME = "Dev1"
CH_DO_ELECTROMAGNET = f"{DEVICE_NAME}/port0/line0"   # 数字输出通道（请确认实际线号）
CH_AO_BUZZER = "ao1"                                  # 模拟输出通道（蜂鸣器）

# 电磁铁参数（通过数字输出高/低电平）
PULSE_DURATION = 0.05          # 每次脉冲宽度（秒）

# ================= 音乐参数 =================
BPM = 81
BEAT_DURATION = 60.0 / BPM / 4         # 一拍时长 0.7407秒
TICKS_PER_BEAT = 1
TICK_DURATION = BEAT_DURATION / TICKS_PER_BEAT

# 鼓点网格（十六分音符精度）
kick_grid = [1,0,1,0, 0,0,0,0, 1,0,1,0, 0,0,0,0,
             1,0,1,0, 0,0,0,0, 1,0,1,0, 0,0,0,0]
snare_grid = [0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0,
              0,0,0,0, 1,0,0,0, 0,0,0,0, 1,0,0,0]
full_kick = (kick_grid * 4)[:128]
full_snare = (snare_grid * 4)[:128]

# 旋律（每拍一个音符，0=休止）
melody_notes = [
    "5","5","5","5",   # 小节1
    "4","4","4","4",   # 小节2
    "3","3","3","3",   # 小节3
    "2","2","2","2",   # 小节4
    "3","0","0","0",   # 小节5
    "3","0","0","0",   # 小节6
    "0","0","0","0",   # 小节7
    "0","0","0","0"    # 小节8
]

# 简谱（G调）转频率
note_to_freq = {
    "1": 196.00, "2": 220.00, "3": 246.94, "4": 261.63, "5": 293.66,
}

# ================= 蜂鸣器播放（使用AO） =================
def play_tone(freq, duration, amplitude=4.0, offset=0.0, sample_rate=5000):
    freq = freq * 2  # 根据实际测试，频率需要乘以2才能听到正确的音高
    total_samples = int(sample_rate * duration)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    waveform = amplitude * np.sin(2 * np.pi * freq * t)
    envelope = np.ones(total_samples)
    attack_samples = int(0.01 * sample_rate)
    release_samples = int(0.05 * sample_rate)
    if attack_samples > 0:
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    if release_samples > 0 and release_samples <= total_samples:
        envelope[-release_samples:] = np.linspace(1, 0, release_samples)
    waveform = waveform * envelope + offset
    with nidaqmx.Task() as task:
        task.ao_channels.add_ao_voltage_chan(
            f"{DEVICE_NAME}/{CH_AO_BUZZER}",
            min_val=-amplitude - offset - 0.5,
            max_val= amplitude + offset + 0.5
        )
        task.timing.cfg_samp_clk_timing(
            rate=sample_rate,
            sample_mode=AcquisitionType.FINITE,
            samps_per_chan=len(waveform)
        )
        task.write(waveform, auto_start=True)
        task.wait_until_done(timeout=duration + 0.1)

# ================= 电磁铁脉冲（使用DO） =================
def electromagnet_pulse():
    """通过数字输出产生一个短脉冲"""
    with nidaqmx.Task() as task:
        task.do_channels.add_do_chan(CH_DO_ELECTROMAGNET, line_grouping=LineGrouping.CHAN_PER_LINE)
        task.write(True, auto_start=True)   # 输出高电平（根据您的驱动电路可能需要反相）
        time.sleep(PULSE_DURATION)
        task.write(False, auto_start=True)  # 恢复低电平

# ================= 鼓点线程（独立于AO，不会冲突） =================
drum_stop_flag = False

def drum_loop(common_start):
    global drum_stop_flag
    tick = 0
    while not drum_stop_flag:
        expected_time = common_start + tick * TICK_DURATION
        now = time.perf_counter()
        if now < expected_time:
            time.sleep(expected_time - now)
        kick = full_kick[tick % len(full_kick)] if tick < len(full_kick) else 0
        snare = full_snare[tick % len(full_snare)] if tick < len(full_snare) else 0
        if kick or snare:
            electromagnet_pulse()
        tick += 1

# ================= 主程序 =================
def main():
    global drum_stop_flag
    print("=" * 60)
    print("   NI DAQ 演奏《We Will Rock You》（DO控制电磁铁）")
    print("   电磁铁 → 数字输出端口（无资源冲突）")
    print("   蜂鸣器 → 模拟输出 ao1")
    print(f"   BPM = {BPM}, 一拍 = {BEAT_DURATION:.3f} 秒")
    print("   按 Ctrl+C 安全停止")
    print("=" * 60)

    common_start = time.perf_counter() + 0.1
    drum_stop_flag = False
    drum_thread = threading.Thread(target=drum_loop, args=(common_start,), daemon=True)
    drum_thread.start()

    try:
        for idx, note in enumerate(melody_notes):
            note_start = common_start + idx * BEAT_DURATION
            now = time.perf_counter()
            if now < note_start:
                time.sleep(note_start - now)
            if note == "0":
                print(f"[休止] 第{idx+1:2d}拍")
            else:
                freq = note_to_freq[note]
                print(f"🎵 第{idx+1:2d}拍: 音符 {note} ({freq:.1f} Hz), 时长 {BEAT_DURATION:.3f}s")
                play_tone(freq, BEAT_DURATION)
        print("\n✨ 演奏完成！")
    except KeyboardInterrupt:
        print("\n⏸️ 用户中断")
    finally:
        drum_stop_flag = True
        time.sleep(0.1)
        print("正在复位所有通道至 0V ...")
        with nidaqmx.Task() as reset_bz:
            reset_bz.ao_channels.add_ao_voltage_chan(f"{DEVICE_NAME}/{CH_AO_BUZZER}")
            reset_bz.write(0.0, auto_start=True)
        with nidaqmx.Task() as reset_do:
            reset_do.do_channels.add_do_chan(CH_DO_ELECTROMAGNET, line_grouping=LineGrouping.CHAN_PER_LINE)
            reset_do.write(False, auto_start=True)
        print("安全复位完成")
        print("=" * 60)

if __name__ == "__main__":
    main()