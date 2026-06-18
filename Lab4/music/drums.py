import time
import nidaqmx
from nidaqmx.constants import LineGrouping

# ================= 配置参数 =================
DEVICE_NAME = "Dev1"
RELAY_LINES = [f"{DEVICE_NAME}/port0/line{i}" for i in range(4)]   # 四个继电器

PULSE_WIDTH = 0.05          # 每个继电器吸合脉冲宽度（秒）
INITIAL_INTERVAL = 0.05      # 初始流水间隔（秒）
MIN_INTERVAL = 0.001         # 最小流水间隔（秒）
DECREMENT_STEP = 0.002      # 每轮完整流水后间隔减少的步长（秒）
# ============================================

def trigger_relay(task, index, duration=PULSE_WIDTH):
    """触发指定继电器（index 0~3）产生一个短脉冲"""
    states = [False] * 4
    states[index] = True
    task.write(states, auto_start=True)
    time.sleep(duration)
    states[index] = False
    task.write(states, auto_start=True)

def main():
    print("=" * 60)
    print("       四继电器逐渐加快流水脉冲脚本")
    print(f"        初始间隔: {INITIAL_INTERVAL}s")
    print(f"        最小间隔: {MIN_INTERVAL}s")
    print(f"        步长: {DECREMENT_STEP}s")
    print(f"        脉冲宽度: {PULSE_WIDTH}s")
    print("        按 Ctrl+C 安全停止")
    print("=" * 60)

    with nidaqmx.Task() as task:
        # 添加四个数字输出通道
        for line in RELAY_LINES:
            task.do_channels.add_do_chan(line, line_grouping=LineGrouping.CHAN_PER_LINE)
        # 初始全部断开
        task.write([False] * 4, auto_start=True)

        current_interval = INITIAL_INTERVAL
        round_count = 0

        try:
            while True:
                # 一轮流水：依次触发继电器 0,1,2,3
                for idx in range(4):
                    trigger_relay(task, idx)
                    # 除了最后一个继电器后不需要额外间隔（下一轮流水开始时会等待），但为了节奏均匀，在两次继电器之间也等待当前间隔
                    # 注意：最后一个继电器脉冲后的等待将在下一轮循环开始时再次触发前完成
                    # 更合理的做法：每个继电器触发后都等待当前间隔（除了最后一个？不，每个脉冲之间都需要相同的间隔）
                    # 但为了让流水连续，每个脉冲之间都应该有相同的间隔时间。
                    # 当前设计：触发脉冲后，等待 interval，然后触发下一个。
                    if idx < 3:   # 前三个继电器后等待间隔
                        time.sleep(current_interval)
                # 最后一组脉冲后等待间隔（否则下一轮的第一个脉冲会马上开始，破坏连续性）
                time.sleep(current_interval)

                round_count += 1
                # 更新间隔（逐渐减小）
                old_interval = current_interval
                current_interval = max(MIN_INTERVAL, current_interval - DECREMENT_STEP)
                if current_interval != old_interval:
                    print(f"第 {round_count} 轮完成，间隔调整为 {current_interval:.3f}s")
                else:
                    print(f"第 {round_count} 轮完成，间隔已达最小值 {current_interval:.3f}s")
        except KeyboardInterrupt:
            print("\n用户中断，正在复位所有继电器...")
        finally:
            task.write([False] * 4, auto_start=True)
            print("所有继电器已断开，程序结束。")
            print("=" * 60)

if __name__ == "__main__":
    main()