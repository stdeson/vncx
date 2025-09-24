#!/usr/bin/env python3
"""
vncx 基本使用示例
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from vncx import VNCClient
import time

def main():
    # 创建 VNC 客户端
    client = VNCClient("127.0.0.1", 5900)
    
    try:
        # 连接到 VNC 服务器
        print("Connecting to VNC server...")
        
        # 截取全屏
        print("Capturing full screen...")
        img = client.capture_screen()
        print(f"Screen captured: {img.shape}")
        
        # 保存截图
        client.save_img("screen.png")
        print("Screenshot saved as screen.png")
        
        # 截取区域
        print("Capturing region...")
        region_img = client.capture_region(100, 100, 300, 200)
        print(f"Region captured: {region_img.shape}")
        
        # 鼠标操作
        print("Mouse operations...")
        client.mouse_move(200, 200)
        time.sleep(0.1)
        client.mouse_click(1)  # 左键点击
        time.sleep(0.1)
        
        # 键盘操作
        print("Keyboard operations...")
        client.key_press(ord('H'))  # 按 H 键
        client.key_press(ord('i'))  # 按 i 键
        
        print("Demo completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # 断开连接
        client.disconnect()
        print("Disconnected from VNC server")

if __name__ == "__main__":
    main()