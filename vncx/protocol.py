"""RFB 协议相关常量和工具函数"""

import struct
from typing import Dict, Any

# RFB 协议版本
RFB_VERSION_3_3 = b"RFB 003.003\n"
RFB_VERSION_3_8 = b"RFB 003.008\n"

# 安全类型
SECURITY_INVALID = 0
SECURITY_NONE = 1
SECURITY_VNC_AUTH = 2

# 客户端到服务器消息类型
CLIENT_SET_PIXEL_FORMAT = 0
CLIENT_SET_ENCODINGS = 2
CLIENT_FRAMEBUFFER_UPDATE_REQUEST = 3
CLIENT_KEY_EVENT = 4
CLIENT_POINTER_EVENT = 5

# 服务器到客户端消息类型
SERVER_FRAMEBUFFER_UPDATE = 0
SERVER_SET_COLOUR_MAP_ENTRIES = 1
SERVER_BELL = 2
SERVER_SERVER_CUT_TEXT = 3

# 编码类型
ENCODING_RAW = 0
ENCODING_COPY_RECT = 1
ENCODING_RRE = 2
ENCODING_HEXTILE = 5
ENCODING_ZLIB = 6

# 像素格式
class PixelFormat:
    def __init__(self):
        self.bits_per_pixel = 32
        self.depth = 24
        self.big_endian = 0
        self.true_colour = 1
        self.red_max = 255
        self.green_max = 255
        self.blue_max = 255
        self.red_shift = 16
        self.green_shift = 8
        self.blue_shift = 0
        
    def pack(self) -> bytes:
        """打包像素格式为字节"""
        return struct.pack(
            "!BBBB HHH BBB xxx",
            self.bits_per_pixel,
            self.depth,
            self.big_endian,
            self.true_colour,
            self.red_max,
            self.green_max,
            self.blue_max,
            self.red_shift,
            self.green_shift,
            self.blue_shift
        )
        
    @classmethod
    def unpack(cls, data: bytes):
        """从字节解包像素格式"""
        pf = cls()
        unpacked = struct.unpack("!BBBB HHH BBB xxx", data)
        pf.bits_per_pixel = unpacked[0]
        pf.depth = unpacked[1]
        pf.big_endian = unpacked[2]
        pf.true_colour = unpacked[3]
        pf.red_max = unpacked[4]
        pf.green_max = unpacked[5]
        pf.blue_max = unpacked[6]
        pf.red_shift = unpacked[7]
        pf.green_shift = unpacked[8]
        pf.blue_shift = unpacked[9]
        return pf


def pack_client_init(shared: bool = True) -> bytes:
    """打包客户端初始化消息"""
    return struct.pack("!B", 1 if shared else 0)


def pack_set_pixel_format(pixel_format: PixelFormat) -> bytes:
    """打包设置像素格式消息"""
    return struct.pack("!B xxx", CLIENT_SET_PIXEL_FORMAT) + pixel_format.pack()


def pack_set_encodings(encodings: list) -> bytes:
    """打包设置编码消息"""
    data = struct.pack("!B x H", CLIENT_SET_ENCODINGS, len(encodings))
    for encoding in encodings:
        data += struct.pack("!i", encoding)
    return data


def pack_framebuffer_update_request(incremental: bool, x: int, y: int, width: int, height: int) -> bytes:
    """打包帧缓冲区更新请求"""
    return struct.pack(
        "!B B HH HH",
        CLIENT_FRAMEBUFFER_UPDATE_REQUEST,
        1 if incremental else 0,
        x, y,
        width, height
    )


def pack_key_event(down: bool, key: int) -> bytes:
    """打包按键事件"""
    return struct.pack("!B B xx I", CLIENT_KEY_EVENT, 1 if down else 0, key)


def pack_pointer_event(buttons: int, x: int, y: int) -> bytes:
    """打包鼠标事件"""
    return struct.pack("!B B HH", CLIENT_POINTER_EVENT, buttons, x, y)