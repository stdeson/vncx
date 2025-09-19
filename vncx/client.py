import socket
import struct
import numpy as np
import cv2
import time
from typing import Optional, Tuple, Union
from .protocol import (
    RFB_VERSION_3_8, SECURITY_NONE, SECURITY_VNC_AUTH,
    PixelFormat, pack_client_init, pack_set_pixel_format, 
    pack_set_encodings, pack_framebuffer_update_request,
    pack_key_event, pack_pointer_event,
    ENCODING_RAW, SERVER_FRAMEBUFFER_UPDATE
)


class VNCClient:
    """轻量级 VNC 客户端，支持基础的 RFB 协议操作"""
    
    def __init__(self, host="127.0.0.1", port=5900, password='', timeout: float = 10.0):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.width = 0
        self.height = 0
        self._mouse_pos = (0, 0)  # 跟踪当前鼠标位置
        self.pixel_format = None
        self.framebuffer = None
        self._last_frame = None
        self._frame_updated = False
        self._connect()
        
    def _connect(self):
        """连接到 VNC 服务器并进行 RFB 协议握手"""
        # 建立 TCP 连接（带超时）
        self.socket.settimeout(self.timeout)
        self.socket.connect((self.host, self.port))
        # RFB 协议版本握手
        server_version = self._recv_with_timeout(12, "RFB version handshake")
        if not server_version.startswith(b"RFB"):
            raise Exception("Invalid RFB protocol version")
        # 发送客户端版本
        self.socket.send(RFB_VERSION_3_8)
        # 安全类型协商
        security_types_length = struct.unpack("!B", self._recv_with_timeout(1, "security types length"))[0]
        if security_types_length == 0:
            # 连接失败
            reason_length = struct.unpack("!I", self.socket.recv(4))[0]
            reason = self.socket.recv(reason_length).decode('utf-8')
            raise Exception(f"Connection failed: {reason}")
        security_types = self._recv_with_timeout(security_types_length, "security types")
        # 选择安全类型（优先选择无认证）
        if SECURITY_NONE in security_types:
            self.socket.send(struct.pack("!B", SECURITY_NONE))
        elif SECURITY_VNC_AUTH in security_types:
            if not self.password:
                raise Exception("VNC authentication required but no password provided")
            self.socket.send(struct.pack("!B", SECURITY_VNC_AUTH))
            self._vnc_auth()
        else:
            raise Exception("No supported security type")
        # 检查安全结果（仅对 VNC 认证）
        if SECURITY_VNC_AUTH in security_types and self.password:
            security_result = struct.unpack("!I", self._recv_with_timeout(4, "security result"))[0]
            if security_result != 0:
                raise Exception("VNC authentication failed")
        # 客户端初始化
        self.socket.send(pack_client_init(shared=True))
        # 服务器初始化
        server_init = self._recv_with_timeout(24, "server initialization")
        self.width, self.height = struct.unpack("!HH", server_init[:4])
        # 解析像素格式
        pixel_format_data = server_init[4:20]
        self.pixel_format = PixelFormat.unpack(pixel_format_data)
        # 服务器名称
        name_length = struct.unpack("!I", server_init[20:24])[0]
        server_name = self._recv_with_timeout(name_length, "server name").decode('utf-8')
        print(f"Connected to VNC server: {server_name} ({self.width}x{self.height})")
        # 设置编码
        self.socket.send(pack_set_encodings([ENCODING_RAW]))
        # 初始化 framebuffer
        self.framebuffer = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self._last_frame = self.framebuffer.copy()
        # 立即请求一次屏幕更新以获取初始帧
        self._request_initial_frame()

    def _vnc_auth(self):
        """处理 VNC 认证 - 按照 RFC 6143 协议使用 DES 加密"""
        # 接收挑战
        challenge = self._recv_with_timeout(16, "VNC authentication challenge")
        # VNC 密码需要反转每个字节的位顺序
        password_bytes = self.password.encode('utf-8')[:8].ljust(8, b'\x00')
        reversed_password = bytes([self._reverse_bits(b) for b in password_bytes])
        # DES 加密挑战
        response = self._des_encrypt(challenge, reversed_password)
        self.socket.send(response)
    
    def _reverse_bits(self, byte_val):
        """反转字节的位顺序"""
        result = 0
        for i in range(8):
            result = (result << 1) | (byte_val & 1)
            byte_val >>= 1
        return result
    
    def _des_encrypt(self, data, key):
        """VNC 协议标准的 DES 加密实现"""
        # VNC 协议 (RFC 6143) 规定使用 DES ECB 模式进行密码验证
        # 这是标准实现，使用 pycryptodome 库
        from Crypto.Cipher import DES
        # 确保数据是 8 字节的倍数
        if len(data) % 8 != 0:
            data = data.ljust((len(data) + 7) // 8 * 8, b'\x00')
        # 创建 DES 加密器
        cipher = DES.new(key, DES.MODE_ECB)
        # 加密数据
        return cipher.encrypt(data)
        
    def disconnect(self):
        """断开与 VNC 服务器的连接"""
        if self.socket:
            self.socket.close()
            
    def capture_screen(self) -> np.ndarray:
        """截取全屏并返回 numpy 数组 (height, width, 3) RGB"""
        # 添加重试机制，处理服务器初始全黑状态
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                result = self.capture_region(0, 0, self.width, self.height)
                
                # 检查是否全黑
                if np.any(result != 0):
                    # 有有效数据，更新最后帧并返回
                    self._last_frame = result.copy()
                    self._frame_updated = True
                    return result
                
                # 如果是最后一次尝试，使用帧缓冲
                if attempt == max_retries - 1:
                    if self._frame_updated and self._last_frame is not None:
                        # 返回缓存的上一帧
                        return self._last_frame.copy()
                    return result
                
                # 智能等待：第一次快速重试，后续逐渐增加等待时间
                wait_time = 0.05 * (attempt + 1)
                import time
                time.sleep(wait_time)
                
                # 智能触发更新：交替移动鼠标和发送键盘事件
                if attempt % 2 == 0:
                    self.mouse_move(10 + attempt * 5, 10 + attempt * 5)
                else:
                    # 发送无害的键盘事件（如Shift键）
                    self.key_press(0xFFE1)  # Shift键
                    
            except Exception as e:
                # 如果发生异常，在最后一次尝试时重新抛出
                if attempt == max_retries - 1:
                    raise e
                # 否则等待并重试
                import time
                time.sleep(0.1)
        
        return np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
    def capture_region(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        """截取指定区域并返回 numpy 数组 (height, width, 3) RGB"""
        if not self.socket:
            raise Exception("Not connected to VNC server")
        
        # 请求帧缓冲区更新（使用 incremental=True 让服务器知道我们支持增量更新）
        request = pack_framebuffer_update_request(True, x, y, width, height)
        self.socket.send(request)
        
        # 接收服务器响应（带超时）
        response = self._recv_with_timeout(4, "framebuffer update response")
        msg_type, num_rectangles = struct.unpack("!B x H", response)
        
        if msg_type != SERVER_FRAMEBUFFER_UPDATE:
            raise Exception(f"Unexpected message type: {msg_type}")
        
        region_data = np.zeros((height, width, 3), dtype=np.uint8)
        
        for _ in range(num_rectangles):
            # 读取矩形头部（带超时）
            rect_header = self._recv_with_timeout(12, "rectangle header")
            rect_x, rect_y, rect_width, rect_height, encoding = struct.unpack("!HH HH i", rect_header)
            
            if encoding == ENCODING_RAW:
                # RAW 编码：直接读取像素数据
                if self.pixel_format is None:
                    raise Exception("Pixel format not initialized - connection may have failed")
                bytes_per_pixel = self.pixel_format.bits_per_pixel // 8
                pixel_data_size = rect_width * rect_height * bytes_per_pixel
                pixel_data = self._recv_with_timeout(pixel_data_size, "pixel data")
                
                # 解析像素数据为 RGB
                pixels = self._parse_raw_pixels(pixel_data, rect_width, rect_height)
                
                # 更新区域数据
                end_y = min(rect_y + rect_height - y, height)
                end_x = min(rect_x + rect_width - x, width)
                start_y = max(rect_y - y, 0)
                start_x = max(rect_x - x, 0)
                
                if start_y < end_y and start_x < end_x:
                    src_start_y = max(y - rect_y, 0)
                    src_start_x = max(x - rect_x, 0)
                    src_end_y = src_start_y + (end_y - start_y)
                    src_end_x = src_start_x + (end_x - start_x)
                    
                    region_data[start_y:end_y, start_x:end_x] = pixels[src_start_y:src_end_y, src_start_x:src_end_x]
            else:
                raise Exception(f"Unsupported encoding: {encoding}")
        
        # 更新主 framebuffer 并维护帧缓冲
        if x == 0 and y == 0 and width == self.width and height == self.height:
            # '全屏更新，直接替换
            self.framebuffer = region_data.copy()
            self._last_frame = self.framebuffer.copy()
            self._frame_updated = True
        else:
            # 区域更新，合并到现有帧
            if self.framebuffer is None:
                # 初始化framebuffer
                self.framebuffer = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                if self._last_frame is None:
                    self._last_frame = self.framebuffer.copy()
            
            end_y = min(y + height, self.height)
            end_x = min(x + width, self.width)
            if y < end_y and x < end_x:
                # 只更新非黑色区域（避免用黑色覆盖有效内容）
                region_slice = region_data[0:end_y-y, 0:end_x-x]
                non_black_mask = (region_slice != 0).any(axis=2)
                
                if np.any(non_black_mask):
                    # 只更新非黑色像素
                    self.framebuffer[y:end_y, x:end_x][non_black_mask] = region_slice[non_black_mask]
                    # 更新_last_frame以反映此更新
                    if self._last_frame is not None:
                        self._last_frame[y:end_y, x:end_x][non_black_mask] = region_slice[non_black_mask]
                    self._frame_updated = True
        
        return region_data
    
    def _recv_all(self, size: int) -> bytes:
        """确保接收指定大小的数据（带超时）"""
        data = b""
        start_time = time.time()
        
        while len(data) < size:
            # 检查超时
            if time.time() - start_time > self.timeout:
                raise TimeoutError(f"Receive timeout after {self.timeout} seconds")
            
            try:
                chunk = self.socket.recv(size - len(data))
                if not chunk:
                    raise Exception("Connection closed unexpectedly")
                data += chunk
            except socket.timeout:
                # 如果recv超时，但总时间还没超时，继续尝试
                if time.time() - start_time > self.timeout:
                    raise TimeoutError(f"Receive timeout after {self.timeout} seconds")
                continue
            except BlockingIOError:
                # 非阻塞模式下会抛出这个异常，但我们使用的是阻塞模式
                continue
        
        return data
    
    def _recv_with_timeout(self, size: int, operation: str = "receive") -> bytes:
        """接收指定大小的数据，带超时处理和详细错误信息"""
        try:
            return self._recv_all(size)
        except TimeoutError:
            raise TimeoutError(f"{operation} timed out after {self.timeout} seconds")
        except Exception as e:
            raise Exception(f"{operation} failed: {e}")
    
    def _parse_raw_pixels(self, data: bytes, width: int, height: int) -> np.ndarray:
        """解析 RAW 像素数据为 RGB 数组"""
        if self.pixel_format is None:
            raise Exception("Pixel format not initialized - connection may have failed")
        bytes_per_pixel = self.pixel_format.bits_per_pixel // 8
        
        if bytes_per_pixel == 4:  # 32-bit
            # 直接解析为BGRA格式（很多VNC服务器使用这种格式）
            pixels_bgra = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 4)
            
            # 转换为RGB（丢弃alpha通道）
            # BGRA -> RGB: 取BGR通道，忽略A通道
            pixels_rgb = pixels_bgra[:, :, [2, 1, 0]]  # BGR -> RGB
            
            return pixels_rgb
            
        elif bytes_per_pixel == 3:  # 24-bit RGB
            pixels = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 3)
            return pixels
            
        elif bytes_per_pixel == 2:  # 16-bit
            # 处理 16-bit 格式
            pixels_16 = np.frombuffer(data, dtype=np.uint16).reshape(height, width)
            # 假设是 RGB565 格式
            r = ((pixels_16 & 0xF800) >> 8).astype(np.uint8)
            g = ((pixels_16 & 0x07E0) >> 3).astype(np.uint8)  
            b = ((pixels_16 & 0x001F) << 3).astype(np.uint8)
            return np.stack([r, g, b], axis=2)
            
        else:
            raise Exception(f"Unsupported pixel format: {bytes_per_pixel} bytes per pixel")
        
    def save_img(self, filename: str):
        """保存当前 framebuffer 为图片文件"""
        if self.framebuffer is not None:
            cv2.imwrite(filename, cv2.cvtColor(self.framebuffer, cv2.COLOR_RGB2BGR))
    
    def has_valid_frame(self) -> bool:
        """检查是否有有效的帧数据（非全黑）"""
        return self._frame_updated and self._last_frame is not None and bool(np.any(self._last_frame != 0))
            
    def mouse_move(self, x: int, y: int):
        """移动鼠标到指定坐标"""
        # 更新并发送鼠标位置
        self._mouse_pos = (x, y)
        pointer_event = pack_pointer_event(0, x, y)
        self.socket.send(pointer_event)
        
    def mouse_click(self, button: int, sleep_time=50):
        """点击鼠标按键 (1=左键, 2=中键, 4=右键)"""
        self.mouse_down(button)
        time.sleep(sleep_time / 1000)
        self.mouse_up(button)
        
    def mouse_down(self, button: int):
        """按下鼠标按键"""
        # 使用当前鼠标位置
        x, y = self._mouse_pos
        pointer_event = pack_pointer_event(button, x, y)
        self.socket.send(pointer_event)
        
    def mouse_up(self, button: int):
        """释放鼠标按键"""
        # 使用当前鼠标位置
        x, y = self._mouse_pos
        pointer_event = pack_pointer_event(0, x, y)  # 按键状态为 0 表示释放
        self.socket.send(pointer_event)
        
    def mouse_roll_up(self):
        """鼠标滚轮向上"""
        # 鼠标滚轮向上通常是按钮 8
        x, y = self._mouse_pos
        self.socket.send(pack_pointer_event(8, x, y))  # 按下
        self.socket.send(pack_pointer_event(0, x, y))  # 释放
        
    def mouse_roll_down(self):
        """鼠标滚轮向下"""
        # 鼠标滚轮向下通常是按钮 16
        x, y = self._mouse_pos
        self.socket.send(pack_pointer_event(16, x, y))  # 按下
        self.socket.send(pack_pointer_event(0, x, y))   # 释放
        
    def key_down(self, key_code: int):
        """按下键盘按键"""
        key_event = pack_key_event(True, key_code)
        self.socket.send(key_event)
        
    def key_up(self, key_code: int):
        """释放键盘按键"""
        key_event = pack_key_event(False, key_code)
        self.socket.send(key_event)
        
    def key_press(self, key_code: int):
        """按下并释放键盘按键"""
        self.key_down(key_code)
        self.key_up(key_code)
        
    def _request_initial_frame(self):
        """在连接建立后立即请求初始帧，确保第一次截图不是全黑"""
        # 发送全屏更新请求
        request = pack_framebuffer_update_request(False, 0, 0, self.width, self.height)
        self.socket.send(request)
        # 接收并处理服务器响应
        try:
            response = self._recv_with_timeout(4, "initial framebuffer update response")
            msg_type, num_rectangles = struct.unpack("!B x H", response)
            if msg_type != SERVER_FRAMEBUFFER_UPDATE:
                return
            # 处理所有矩形区域
            for _ in range(num_rectangles):
                rect_header = self._recv_with_timeout(12, "initial rectangle header")
                rect_x, rect_y, rect_width, rect_height, encoding = struct.unpack("!HH HH i", rect_header)
                
                if encoding == ENCODING_RAW:
                    if self.pixel_format is None:
                        # 跳过像素数据（不解析，只为了清空缓冲区）
                        pixel_data_size = rect_width * rect_height * 4  # 假设32位像素格式
                    else:
                        bytes_per_pixel = self.pixel_format.bits_per_pixel // 8
                        pixel_data_size = rect_width * rect_height * bytes_per_pixel
                    self._recv_with_timeout(pixel_data_size, "initial pixel data")
        except Exception as e:
            print(f"初始帧请求失败（不影响后续操作）: {e}")