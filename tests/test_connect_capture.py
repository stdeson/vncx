import os
import unittest
from vncx import VNCClient
import cv2
import numpy as np

class TestConnectCapture(unittest.TestCase):
    def setUp(self):
        host = os.getenv('VNC_HOST', '127.0.0.1')
        port = int(os.getenv('VNC_PORT', '5900'))
        password = os.getenv('VNC_PASSWORD', '')
        self.client = VNCClient(host, port, password)
        
        
    def test_capture_region(self):
        """测试屏幕区域捕获功能，确保截图不是全黑的"""
        max_attempts = 5
        
        for attempt in range(max_attempts):
            try:
                # self.client.mouse_move(100, 100)
                # import time
                # time.sleep(1)

                # 尝试捕获区域截图
                result = self.client.capture_region(0, 0, 3840, 2160)
                self.assertIsNotNone(result)
                
                # 检查是否为NumPy数组格式
                if not isinstance(result, np.ndarray):
                    raise ValueError("返回值不是NumPy数组")
                
                # 检查数组维度和数据类型
                self.assertEqual(len(result.shape), 3, "数组应该是3维的(height, width, 3)")
                self.assertEqual(result.shape[2], 3, "第三个维度应该是3 (RGB)")
                self.assertEqual(result.dtype, np.uint8, "数组数据类型应该是uint8")
                
                # 检查是否为全黑图像
                is_all_black = np.all(result == 0)
                
                if not is_all_black:
                    # 有有效数据，测试通过
                    print(f"成功捕获非全黑截图，尝试次数: {attempt + 1}")
                    print(f"截图形状: {result.shape}, 非零像素数量: {np.sum(result != 0)}")
                    # 保存截图为PNG文件
                    debug_filename = f"debug_capture_attempt_{attempt + 1}.png"
                    cv2.imwrite(debug_filename, cv2.cvtColor(result, cv2.COLOR_RGB2BGR))
                    print(f"已保存截图: {debug_filename}")
                    return  # 测试通过
                
                # 如果是全黑，尝试触发屏幕更新
                print(f"尝试 {attempt + 1}/{max_attempts}: 截图全黑，尝试触发屏幕更新...")
                
                # 智能触发屏幕更新：移动鼠标和发送无害键盘事件
                if attempt % 2 == 0:
                    # 移动鼠标到不同位置
                    self.client.mouse_move(50 + attempt * 10, 50 + attempt * 10)
                    print("已移动鼠标尝试触发屏幕更新")
                else:
                    # 发送Shift键按下释放事件
                    self.client.key_press(0xFFE1)  # Shift键
                    print("已发送键盘事件尝试触发屏幕更新")
                
                # 等待一段时间让屏幕有机会更新
                import time
                wait_time = 0.1 * (attempt + 1)
                time.sleep(wait_time)
                
            except Exception as e:
                print(f"尝试 {attempt + 1} 失败: {e}")
                
                # 如果是最后一次尝试，重新抛出异常
                if attempt == max_attempts - 1:
                    raise
                
                # 等待一段时间后重试
                time.sleep(0.1)
        
        # 如果所有尝试都失败了
        self.fail(f"在 {max_attempts} 次尝试后仍无法捕获非全黑截图")



if __name__ == '__main__':
    unittest.main()