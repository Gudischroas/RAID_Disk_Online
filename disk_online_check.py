import subprocess
import re
import serial
import time
from win10toast import ToastNotifier

toaster = ToastNotifier()

# 定义磁盘状态与对应的颜色
STATUS_COLOR_MAP = {
    'Online': (0, 255, 0, 1),  # Green, 在线状态
    'Failed': (255, 0, 0, 2),  # Red, 掉线状态
    'Predictive Failure': (255, 255, 0, 3),  # Yellow, 可能存在故障状态
    'Rebuild': (0, 0, 255, 4)   # Blue, 重建状态
}

def get_disk_status():
    # 执行 megacli 命令获取物理磁盘状态
    cmd = ["megacli", "-PDList", "-aALL"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    if result.returncode != 0:
        print("Error running megacli:", result.stderr)
        return {}

    # 解析结果，提取每个物理磁盘的 slot 和状态
    status_info = {}
    disk_entries = result.stdout.split('Enclosure Device ID')

    for entry in disk_entries:
        slot_match = re.search(r'Slot Number:\s+(\d+)', entry)
        status_match = re.search(r'Firmware state:\s+(\w+)', entry)

        if slot_match and status_match:
            slot = int(slot_match.group(1))
            status = status_match.group(1)
            status_info[slot] = status

    return status_info

def status_to_color(status):
    # 根据状态返回颜色
    return STATUS_COLOR_MAP.get(status, (0, 0, 0))  # 默认黑色 (无效状态)

def send_status_to_esp8266(status_info):
    # 打开串口
    ser = serial.Serial('COM3', 9600, timeout = 5)  # 请将 COM3 改为实际串口号
    
    # 发送状态信息到 ESP8266
    for slot, status in status_info.items():
        r, g, b = status_to_color(status)
        data = f'{slot}:{r},{g},{b}\n'
        ser.write(data.encode())
        time.sleep(0.1)
    ser.close()

def main():
    # 获取磁盘状态
    disk_status = get_disk_status()
    
    # 若无法获取磁盘状态：
    if not disk_status:
        toaster.show_toast(f"火火科技提醒您：",
                   f"无法获取阵列磁盘状态，请检查 Megacli 软件运行状态或磁盘连接情况。",
                   icon_path=None,
                   duration=10)
        while toaster.notification_active(): time.sleep(0.1)
        return

    # 将状态发送到 ESP8266
    send_status_to_esp8266(disk_status)

    time.sleep(5)  # 每5秒检测一次硬盘状态

    

if __name__ == "__main__":
    main()
