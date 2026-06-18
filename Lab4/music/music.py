import time
import nidaqmx
from nidaqmx.constants import LineGrouping

# ================= 配置参数 =================
DEVICE_NAME = "Dev1"
# 四个继电器对应的数字线
RELAY_LINES = [f"{DEVICE_NAME}/port0/line{i}" for i in range(4)]

PULSE_DURATION = 0.2      # 每个继电器吸合时间（秒）
INTERVAL = 0.02            # 继电器切换间隔（秒），即上一个断开后等多久再触发下一个
# ============================================

def main():
    print("=" * 60)
    print("        NI DAQ 流水脉冲门锁控制脚本")
    print(f"        继电器线路: {', '.join(RELAY_LINES)}")
    print(f"        脉冲宽度: {PULSE_DURATION}s, 切换间隔: {INTERVAL}s")
    print("        按 Ctrl+C 安全停止所有继电器")
    print("=" * 60)

    # 创建数字输出任务
    with nidaqmx.Task() as task:
        # 添加四个数字输出通道（每个线单独配置）
        for line in RELAY_LINES:
            task.do_channels.add_do_chan(line, line_grouping=LineGrouping.CHAN_PER_LINE)
        
        # 初始将所有继电器置于断开状态（低电平）
        # 假设继电器高电平吸合（可根据实际电路修改 True/False）
        initial_state = [False] * len(RELAY_LINES)
        task.write(initial_state, auto_start=True)
        print("初始状态: 所有继电器断开。")

        count = 0
        try:
            while True:
                # 依次触发每个继电器
                for idx, line in enumerate(RELAY_LINES):
                    # 吸合当前继电器
                    states = [False] * len(RELAY_LINES)
                    states[idx] = True
                    task.write(states, auto_start=True)
                    print(f"[{count}] 继电器 {idx} 吸合 (门锁开启)")
                    time.sleep(PULSE_DURATION)
                    
                    # 断开当前继电器
                    states[idx] = False
                    task.write(states, auto_start=True)
                    print(f"[{count}] 继电器 {idx} 断开 (门锁关闭)")
                    
                    # 间隔等待，然后轮到下一个继电器
                    time.sleep(INTERVAL)
                
                count += 1
                print(f"完成第 {count} 轮流水脉冲。")
        except KeyboardInterrupt:
            print("\n用户中断，正在复位所有继电器...")
        finally:
            # 确保所有继电器断开
            task.write([False] * len(RELAY_LINES), auto_start=True)
            print("所有继电器已安全断开。")
            print("=" * 60)

if __name__ == "__main__":
    main()