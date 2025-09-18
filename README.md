# vncx

轻量级 Python VNC 客户端库，支持标准 RFB 协议、键盘鼠标操作、区域截图功能。

## 特性

- ✅ 支持标准 RFB 3.8 协议
- ✅ 同步 TCP 连接，逻辑简单可靠
- ✅ 全屏截图和区域截图
- ✅ 返回 OpenCV 可用的 numpy 数组
- ✅ 鼠标移动、点击、滚轮操作
- ✅ 键盘按键输入
- ✅ 依赖最少（仅 numpy 和 opencv-python）
- ✅ 跨平台支持（Windows、macOS、Linux）

## 安装

```bash
pip install vncx
```

或者从源码安装：

```bash
pip install -e .
```

## 快速开始

```python
from vncx import VNCClient

# 创建客户端
client = VNCClient("127.0.0.1", 5900)

# 连接到 VNC 服务器
client.connect()

# 截取全屏
img = client.capture_screen()
print(f"Screen shape: {img.shape}")

# 保存截图
client.save_img("screen.png")

# 截取指定区域
region_img = client.capture_region(100, 100, 300, 200)

# 鼠标操作
client.mouse_move(200, 200)  # 移动到坐标 (200, 200)
client.mouse_click(1)        # 左键点击

# 键盘操作
client.key_press(ord('H'))   # 按 H 键
client.key_press(ord('i'))   # 按 i 键

# 断开连接
client.disconnect()
```

## API 参考

### VNCClient

#### `__init__(host: str = "127.0.0.1", port: int = 5900, password: Optional[str] = None)`
创建 VNC 客户端实例。

#### `connect()`
连接到 VNC 服务器并进行 RFB 协议握手。

#### `disconnect()`
断开与 VNC 服务器的连接。

#### `capture_screen() -> np.ndarray`
截取全屏并返回 numpy 数组 (height, width, 3) RGB。

#### `capture_region(x: int, y: int, width: int, height: int) -> np.ndarray`
截取指定区域并返回 numpy 数组。

#### `save_img(filename: str)`
保存当前 framebuffer 为图片文件。

#### `mouse_move(x: int, y: int)`
移动鼠标到指定坐标。

#### `mouse_click(button: int)`
点击鼠标按键 (1=左键, 2=中键, 4=右键)。

#### `mouse_down(button: int)`
按下鼠标按键。

#### `mouse_up(button: int)`
释放鼠标按键。

#### `mouse_roll_up()`
鼠标滚轮向上。

#### `mouse_roll_down()`
鼠标滚轮向下。

#### `key_down(key_code: int)`
按下键盘按键。

#### `key_up(key_code: int)`
释放键盘按键。

#### `key_press(key_code: int)`
按下并释放键盘按键。

## 开发

### 项目结构

```
vncx/
├── vncx/           # 核心库
│   ├── __init__.py
│   ├── client.py   # VNCClient 主类
│   └── protocol.py # RFB 协议相关
├── tests/          # 单元测试
├── examples/       # 使用示例
├── setup.py        # 安装配置
├── requirements.txt # 依赖列表
└── README.md       # 项目文档
```

### 运行测试

```bash
python -m pytest tests/
```

### 运行示例

```bash
python examples/basic_usage.py
```

## 依赖

- Python 3.7+
- numpy
- opencv-python

## 协议支持

- RFB 3.8 协议
- 安全类型：无认证、VNC 认证
- 编码：RAW 编码

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！