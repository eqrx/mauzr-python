""" Types for SPI communication. """
__author__ = "Alexander Sowitzki"

import ctypes

SPI_IOC_MESSAGE = 0x40206b00

class IoctlData(ctypes.Structure):
    """ ioctl message for spi transfer. See linux spi doc. """
    _fields_ = [('tx_buf', ctypes.POINTER(ctypes.c_uint8)),
                ('rx_buf', ctypes.POINTER(ctypes.c_uint8)),
                ('len', ctypes.c_uint32),
                ('speed_hz', ctypes.c_uint32),
                ('delay_usecs', ctypes.c_uint16),
                ('bits_per_word', ctypes.c_uint8),
                ('cs_change', ctypes.c_uint8),
                ('tx_nbits', ctypes.c_uint8),
                ('rx_nbits', ctypes.c_uint8),
                ('pad', ctypes.c_uint16)]
