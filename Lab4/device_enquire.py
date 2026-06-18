import nidaqmx
from nidaqmx.system import System

try:
    # 获取当前系统对象
    local_system = System.local()

    # 获取所有连接的硬件设备列表
    device_list = local_system.devices

    if not device_list:
        print("未检测到任何 NI DAQ 设备。请检查 USB/PCI 连接或驱动是否安装。")
    else:
        print("=" * 40)
        print("成功检测到以下 NI 设备：")
        print("=" * 40)
        # 遍历并打印每个设备的信息
        for dev in device_list:
            print(f"设备名称 (Device Name): {dev.name}")
            print(f"设备产品型号 (Product Type): {dev.product_type}")
            print(f"设备序列号 (Serial Number): {dev.serial_num}")
            print("-" * 40)

except nidaqmx.errors.DaqError as e:
    print(f"查询设备时发生底层驱动错误: {e}")
except Exception as e:
    print(f"发生未知错误: {e}")