import serial
import serial.tools.list_ports
import time
import sys

class SyringePump:
    def __init__(self, port=None, auto_detect=True, baudrate=9600, timeout=1):
        """
        初始化注射器泵
        :param port: 串口号，如果为None且auto_detect为True则自动检测
        :param auto_detect: 是否自动检测设备端口
        :param baudrate: 波特率
        :param timeout: 超时时间
        """
        if port is None and auto_detect:
            port = self.auto_detect_port()
            if port is None:
                raise Exception("未找到注射器泵设备，请检查连接")
            print(f"自动检测到设备端口: {port}")
        elif port is not None:
            print(f"使用指定端口: {port}")
        else:
            raise Exception("未指定端口且自动检测失败")
        
        self.ser = serial.Serial(port, baudrate, bytesize=8, parity='N', 
                                 stopbits=1, timeout=timeout)
        time.sleep(0.5)  # 等待设备稳定

    def auto_detect_port(self):
        """自动检测注射器泵端口（通过主动探测）"""
        print("正在扫描可用串口...")
        available_ports = list(serial.tools.list_ports.comports())
        
        if not available_ports:
            print("未检测到任何串口设备")
            return None
        
        print(f"发现 {len(available_ports)} 个串口:")
        for i, p in enumerate(available_ports):
            print(f"  {i+1}. {p.device} - {p.description}")
        
        # 主动探测每个端口
        for port_info in available_ports:
            port = port_info.device
            print(f"正在探测 {port}...")
            try:
                test_ser = serial.Serial(port, 9600, timeout=1)
                time.sleep(0.1)
                
                # 发送停止指令进行探测
                test_ser.write(b'q6h6d\r\n')  
                time.sleep(0.2)
                
                response = test_ser.read(100).decode('utf-8', errors='ignore').strip()
                test_ser.close()
                
                if response:
                    print(f"  {port} 返回了数据: {response[:50]}")
                    if 'f' in response or 'q' in response or response.isalnum():
                        print(f"✓ 找到疑似注射器泵: {port}")
                        return port
                else:
                    print(f"  {port} 无返回数据")
                    
            except Exception as e:
                print(f"  {port} 探测失败: {str(e)}")
                continue
        
        print("主动探测未找到，将使用第一个可用端口")
        return available_ports[0].device

    def send_cmd(self, cmd):
        """发送指令，自动添加回车换行"""
        full_cmd = cmd + '\r\n'
        self.ser.write(full_cmd.encode())
        print(f"发送: {cmd}")
        time.sleep(0.05)
        while self.ser.in_waiting:
            resp = self.ser.read(self.ser.in_waiting).decode().strip()
            if resp:
                print(f"接收: {resp}")

    def set_speed_unit_mm_per_s(self):
        """切换速度单位为 mm/s (发送十进制值 12 对应 mm/s 单位)"""
        self.send_cmd('q7h12d')

    def set_speed(self, speed_mm_per_s):
        """设置速度（mm/s）"""
        integer_part = int(speed_mm_per_s)
        fractional_part = int(round((speed_mm_per_s - integer_part) * 100))
        if fractional_part >= 100:
            fractional_part = 99
        self.send_cmd(f'q1h{integer_part:02d}d')
        self.send_cmd(f'q2h{fractional_part:02d}d')
        print(f"速度已设为 {speed_mm_per_s:.2f} mm/s")

    def set_time(self, hours=0, minutes=0, seconds=0):
        """设置自动运行的工作时间（时/分/秒）"""
        self.send_cmd(f'q3h{int(hours):02d}d')
        self.send_cmd(f'q4h{int(minutes):02d}d')
        self.send_cmd(f'q5h{int(seconds):02d}d')
        print(f"工作时间已设: {int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}")

    def set_time_from_distance(self, distance_mm, speed_mm_per_s):
        """根据距离和速度计算并设置工作时间"""
        run_time = distance_mm / speed_mm_per_s
        hours = int(run_time // 3600)
        minutes = int((run_time % 3600) // 60)
        seconds = int(round(run_time % 60))
        # 处理进位：round 可能让 seconds = 60
        if seconds >= 60:
            seconds = 0
            minutes += 1
        if minutes >= 60:
            minutes = 0
            hours += 1
        self.set_time(hours, minutes, seconds)
        return run_time

    def save_params(self):
        """保存参数到设备（速度、工作时间等配置写入硬件，必须在 auto_forward/auto_backward 前调用）"""
        self.send_cmd('q6h1d')

    def auto_forward(self):
        """核心修正：修改为自动前进指令，使其严格执行设定的分级速度"""
        self.send_cmd('q6h2d')

    def auto_backward(self):
        """核心修正：修改为自动后退指令，使其严格执行设定的分级速度"""
        self.send_cmd('q6h3d')

    def manual_forward(self):
        """手动快进（点动模式，通常无视工作速度）"""
        self.send_cmd('q6h4d')

    def manual_backward(self):
        """手动快退（点动模式，通常无视工作速度）"""
        self.send_cmd('q6h5d')

    def stop(self):
        """停止运动"""
        self.send_cmd('q6h6d')

    def move_distance(self, distance_mm, speed_mm_per_s, direction='forward'):
        """
        高精度距离控制（设置速度+工作时间 → 保存参数 → 自动运行 → 等待硬件 f1d 完成信号）
        """
        if distance_mm <= 0 or speed_mm_per_s <= 0:
            print("距离和速度必须大于0")
            return

        # 1. 设置速度单位及速度值
        self.set_speed_unit_mm_per_s()
        self.set_speed(speed_mm_per_s)

        # 2. 根据距离/速度计算并设置工作时间（q3h/q4h/q5h）
        run_time = self.set_time_from_distance(distance_mm, speed_mm_per_s)
        print(f"【目标】{distance_mm} mm @ {speed_mm_per_s} mm/s = {run_time:.2f} s")

        # 3. 清空串口缓冲区后保存参数（使速度+时间配置生效）
        self.ser.reset_input_buffer()
        self.save_params()

        # 4. 启动【自动模式】运行（硬件按已配置的时间和速度执行）
        if direction == 'forward':
            self.auto_forward()
        else:
            self.auto_backward()

        # 5. 等待硬件完成信号 f1d（超时保护 = 预计时间 + 5s）
        start_time = time.time()
        recv_buffer = ""
        timeout = run_time + 5.0

        while (time.time() - start_time) < timeout:
            if self.ser.in_waiting:
                data = self.ser.read(self.ser.in_waiting).decode(errors='ignore')
                recv_buffer += data
                if 'f1d' in recv_buffer:
                    print("【硬件完成】接收到设备自动完成信号(f1d)，运动结束！")
                    break
            time.sleep(0.01)

        # 6. 保险停止
        self.stop()
        print(f"【结束】实际耗时: {time.time() - start_time:.2f} 秒")

    def close(self):
        self.ser.close()

def main():
    distance = float(input("请输入要移动的距离（毫米）: "))
    speed = float(input("请输入运动速度（毫米/秒）: "))

    pump = None
    try:
        # 指定你的COM端口
        pump = SyringePump(port="COM5")
        print("连接成功，开始前进...")
        pump.move_distance(distance, speed, direction='forward')
        
        input("按 Enter 键开始后退...")
        print("开始后退...")
        pump.move_distance(distance, speed, direction='backward')
        print("全部控制任务完成！")
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        if pump:
            pump.close()
            print("串口已关闭")

if __name__ == "__main__":
    main()