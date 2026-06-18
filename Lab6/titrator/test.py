import serial
import serial.tools.list_ports
import time

class SyringePump:
    def __init__(self, port="COM5", baudrate=9600, timeout=1):
        """
        初始化注射器泵
        """
        print(f"正在连接端口: {port}...")
        self.ser = serial.Serial(port, baudrate, bytesize=8, parity='N', 
                                 stopbits=1, timeout=timeout)
        time.sleep(0.5)  # 等待串口稳定
        self.stop()      # 初始化时先确保设备静止

    def send_cmd(self, cmd):
        """发送指令并等待接收设备的 ok 应答，清空缓冲区"""
        full_cmd = cmd + '\r\n'
        self.ser.write(full_cmd.encode())
        time.sleep(0.05) # 给单片机微小的处理时间
        
        # 读取并打印设备的响应（如 ok）
        resp = ""
        while self.ser.in_waiting:
            resp += self.ser.read(self.ser.in_waiting).decode(errors='ignore')
        
        # 如果有回应，可以用于调试打印
        # print(f"发送: {cmd} -> 响应: {resp.strip()}")
        return resp

    def set_speed_unit_mm_per_s(self):
        """切换速度单位为 mm/s (对应说明书中的十进制 12)"""
        self.send_cmd('q7h12d')

    def set_speed(self, speed_mm_per_s):
        """设置速度（mm/s）- 严格采用十进制数字字符串"""
        integer_part = int(speed_mm_per_s)
        fractional_part = int(round((speed_mm_per_s - integer_part) * 100))
        if fractional_part >= 100:
            fractional_part = 99
            
        # 抛弃 :02X 十六进制，直接发送纯十进制数字
        self.send_cmd(f'q1h{integer_part}d')
        self.send_cmd(f'q2h{fractional_part}d')
        print(f" 速度配置成功: {speed_mm_per_s:.2f} mm/s")

    def set_hardware_timer(self, total_seconds):
        """配置硬件级倒计时（防撞底安全伞）"""
        self.send_cmd('q3h0d')  # 0小时
        self.send_cmd('q4h0d')  # 0分钟
        self.send_cmd(f'q5h{int(total_seconds)}d') # 秒数

    def stop(self):
        """停止运动"""
        self.send_cmd('q6h6d')

    def move_distance(self, distance_mm, speed_mm_per_s, direction='forward'):
        """
        高精度距离/速度闭环控制（十进制修正版）
        """
        if distance_mm <= 0 or speed_mm_per_s <= 0:
            print("距离和速度必须大于0")
            return

        # 1. 基础参数配置
        self.set_speed_unit_mm_per_s()
        self.set_speed(speed_mm_per_s)
        
        # 2. 计算精确运行时间
        run_time = distance_mm / speed_mm_per_s
        
        # 3. 设置硬件级防过冲限时保护（向上取整 + 1秒作为容错安全垫）
        hardware_safety_seconds = int(run_time) + 1
        self.set_hardware_timer(hardware_safety_seconds)
        
        print(f"【控制启动】目标: {distance_mm}mm | 速度: {speed_mm_per_s}mm/s | 理论耗时: {run_time:.2f}秒 (硬件保护: {hardware_safety_seconds}秒)")

        # 4. 清空历史缓冲区，迎接运动信号
        self.ser.reset_input_buffer()

        # 5. 下发【自动运行】指令
        cmd = 'q6h2d' if direction == 'forward' else 'q6h3d'
        self.ser.write((cmd + '\r\n').encode())

        # 6. 高频毫秒级轮询 + 硬件回传双重拦截
        start_time = time.time()
        recv_buffer = ""
        
        while (time.time() - start_time) < run_time:
            if self.ser.in_waiting:
                data = self.ser.read(self.ser.in_waiting).decode(errors='ignore')
                recv_buffer += data
                # 兼容说明书的 f1d 和硬件实际返回的大写 F0D/F1D
                if 'F0D' in recv_buffer.upper() or 'F1D' in recv_buffer.upper():
                    print("【硬件中断】接收到设备到达终点信号(F0D)，运动安全结束！")
                    break
            time.sleep(0.01) # 10毫秒高频微调

        # 7. 强制下发停止指令（双重保险），清理现场
        self.stop()
        print(f"【控制结束】实际物理耗时: {time.time() - start_time:.2f} 秒\n")

    def close(self):
        self.stop()
        self.ser.close()

def main():
    # 建立连接
    pump = SyringePump(port="COM5")
    
    try:
        print("============== 自动化精确变速测试 ==============")
        # 测试 1：慢速前进 5mm (速度 0.5 mm/s，应该非常安静且平稳地走 10 秒)
        print("测试 1：正在以 0.5 mm/s 慢速前进 5.0 mm...")
        pump.move_distance(5.0, 0.5, direction='forward')
        
        print("中间安全停顿 3 秒...\n")
        time.sleep(3.0)
        
        # 测试 2：快速后退 5mm (速度 2.5 mm/s，应该迅速在 2 秒内退回原位)
        print("测试 2：正在以 2.5 mm/s 快速后退 5.0 mm...")
        pump.move_distance(5.0, 2.5, direction='backward')
        
        print("所有变速控制测试圆满完成！")

    except Exception as e:
        print(f"运行过程中发生异常: {e}")
    finally:
        pump.close()
        print("串口已安全断开。")

if __name__ == "__main__":
    main()