""" C interface types for I2C access. """

import ctypes

__author__ = "Alexander Sowitzki"


class Message(ctypes.Structure):
    """ Represent the struct i2c_msg from linux/i2c-dev.h. """

    _fields_ = [('addr', ctypes.c_uint16),
                ('flags', ctypes.c_uint16),
                ('len', ctypes.c_int16),
                ('buf', ctypes.POINTER(ctypes.c_uint8))]

    __slots__ = [name for name, type in _fields_]


class IoctlData(ctypes.Structure):
    """ Represent the struct i2c_rdwr_ioctl_data from linux/i2c-dev.h. """

    _fields_ = [('msgs', ctypes.POINTER(Message)),
                ('nmsgs', ctypes.c_int32)]

    __slots__ = [name for name, type in _fields_]

I2C_M_TEN = 0x0010
I2C_M_RD = 0x0001
I2C_M_NOSTART = 0x4000
I2C_M_REV_DIR_ADDR = 0x2000
I2C_M_IGNORE_NAK = 0x1000
I2C_M_NO_RD_ACK = 0x0800
I2C_M_RECV_LEN = 0x0400
I2C_FUNC_I2C = 0x00000001
I2C_FUNC_10BIT_ADDR = 0x00000002
I2C_FUNC_PROTOCOL_MANGLING = 0x00000004
I2C_SLAVE = 0x0703
I2C_TENBIT = 0x0704
I2C_FUNCS = 0x0705
I2C_RDWR = 0x0707
