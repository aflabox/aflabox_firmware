#!/usr/bin/python
# -*- coding: UTF-8 -*-
import time
import numpy as np
from . import lcdconfig

class LCD_2inch4(lcdconfig.RaspberryPi):
    width = 320  # Landscape width
    height = 240 # Landscape height

    def __init__(self):
        super().__init__()  # Initialize the parent class
        self.np = np
        
    def digital_write(self, pin, value):
        self.GPIO.output(pin, value)

    def digital_read(self, pin):
        return self.GPIO.input(pin)

    def delay_ms(self, delaytime):
        time.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.SPI.writebytes(data)

    def module_init(self):
        self.GPIO.setmode(self.GPIO.BCM)
        self.GPIO.setwarnings(False)

        self.GPIO.setup(self.RST_PIN, self.GPIO.OUT)
        self.GPIO.setup(self.DC_PIN, self.GPIO.OUT)
        self.GPIO.setup(self.BL_PIN, self.GPIO.OUT)
        self.GPIO.setup(self.CS_PIN, self.GPIO.OUT)
        
        # Initialize SPI
        self.SPI.max_speed_hz = 40000000
        self.SPI.mode = 0b00
        return 0

    def module_exit(self):
        self.GPIO.cleanup()

    def command(self, cmd):
        self.digital_write(self.DC_PIN, self.GPIO.LOW)
        self.digital_write(self.CS_PIN, self.GPIO.LOW)
        self.spi_writebyte([cmd])
        self.digital_write(self.CS_PIN, self.GPIO.HIGH)

    def data(self, val):
        self.digital_write(self.DC_PIN, self.GPIO.HIGH)
        self.digital_write(self.CS_PIN, self.GPIO.LOW)
        self.spi_writebyte([val])
        self.digital_write(self.CS_PIN, self.GPIO.HIGH)

    def reset(self):
        """Reset the display"""
        self.GPIO.output(self.RST_PIN, self.GPIO.HIGH)
        time.sleep(0.01)
        self.GPIO.output(self.RST_PIN, self.GPIO.LOW)
        time.sleep(0.01)
        self.GPIO.output(self.RST_PIN, self.GPIO.HIGH)
        time.sleep(0.01)
        
        self.GPIO.output(self.CS_PIN, self.GPIO.HIGH)
        self.GPIO.output(self.BL_PIN, self.GPIO.HIGH)

    def Init(self):
        """Initialize display"""
        self.module_init()
        self.reset()

        self.command(0x11)  # Sleep out
        time.sleep(0.12)

        self.command(0xCF)  # Power Control B
        self.data(0x00)
        self.data(0xC1)
        self.data(0X30)

        self.command(0xED)  # Power on sequence control
        self.data(0x64)
        self.data(0x03)
        self.data(0X12)
        self.data(0X81)

        self.command(0xE8)  # Driver timing control A
        self.data(0x85)
        self.data(0x00)
        self.data(0x79)

        self.command(0xCB)  # Power Control A
        self.data(0x39)
        self.data(0x2C)
        self.data(0x00)
        self.data(0x34)
        self.data(0x02)

        self.command(0xF7)  # Pump ratio control
        self.data(0x20)

        self.command(0xEA)  # Driver timing control B
        self.data(0x00)
        self.data(0x00)

        self.command(0xC0)  # Power Control 1
        self.data(0x1D)  # VRH[5:0]

        self.command(0xC1)  # Power Control 2
        self.data(0x12)  # SAP[2:0];BT[3:0]

        self.command(0xC5)  # VCOM Control 1
        self.data(0x33)
        self.data(0x3F)

        self.command(0xC7)  # VCOM Control 2
        self.data(0x92)

        self.command(0x3A)  # Pixel Format Set
        self.data(0x55)  # 16 bits/pixel

        # Memory Access Control (orientation)
        self.command(0x36)
        self.data(0x48)  # MX, BGR = 0x48 for landscape

        self.command(0xB1)  # Frame Rate Control
        self.data(0x00)
        self.data(0x12)

        self.command(0xB6)  # Display Function Control
        self.data(0x0A)
        self.data(0xA2)

        self.command(0x44)  # Set Tear Scanline
        self.data(0x02)

        self.command(0xF2)  # Enable 3G
        self.data(0x00)  # 3Gamma Function Disable

        self.command(0x26)  # Gamma Set
        self.data(0x01)

        # Positive Gamma Correction
        self.command(0xE0)
        self.data(0x0F)
        self.data(0x22)
        self.data(0x1C)
        self.data(0x1B)
        self.data(0x08)
        self.data(0x0F)
        self.data(0x48)
        self.data(0xB8)
        self.data(0x34)
        self.data(0x05)
        self.data(0x0C)
        self.data(0x09)
        self.data(0x0F)
        self.data(0x07)
        self.data(0x00)

        # Negative Gamma Correction
        self.command(0XE1)
        self.data(0x00)
        self.data(0x23)
        self.data(0x24)
        self.data(0x07)
        self.data(0x10)
        self.data(0x07)
        self.data(0x38)
        self.data(0x47)
        self.data(0x4B)
        self.data(0x0A)
        self.data(0x13)
        self.data(0x06)
        self.data(0x30)
        self.data(0x38)
        self.data(0x0F)

        self.command(0x29)  # Display on

    def SetWindows(self, Xstart, Ystart, Xend, Yend):
        # Set X coordinates
        self.command(0x2A)
        self.data(Xstart >> 8)        # Set the horizontal starting point to the high octet
        self.data(Xstart & 0xff)      # Set the horizontal starting point to the low octet
        self.data(Xend >> 8)          # Set the horizontal end to the high octet
        self.data((Xend - 1) & 0xff)  # Set the horizontal end to the low octet

        # Set Y coordinates
        self.command(0x2B)
        self.data(Ystart >> 8)
        self.data(Ystart & 0xff)
        self.data(Yend >> 8)
        self.data((Yend - 1) & 0xff)

        self.command(0x2C)

    def ShowImage(self, Image):
        """Set buffer to value of Python Imaging Library image."""
        """Write display buffer to physical display"""
        imwidth, imheight = Image.size
        if imwidth != self.width or imheight != self.height:
            raise ValueError(
                f'Image must be same dimensions as display ({self.width}x{self.height})')

        img = self.np.asarray(Image)
        pix = self.np.zeros((imheight, imwidth, 2), dtype=self.np.uint8)
        
        # RGB888 to RGB565 conversion
        pix[...,[0]] = self.np.add(self.np.bitwise_and(img[...,[0]], 0xF8),
                                  self.np.right_shift(img[...,[1]], 5))
        pix[...,[1]] = self.np.add(self.np.bitwise_and(self.np.left_shift(img[...,[1]], 3), 0xE0),
                                  self.np.right_shift(img[...,[2]], 3))

        pix = pix.flatten().tolist()

        self.SetWindows(0, 0, self.width, self.height)
        self.digital_write(self.DC_PIN, self.GPIO.HIGH)
        self.digital_write(self.CS_PIN, self.GPIO.LOW)
        
        # Send data in chunks to avoid buffer limitations
        for i in range(0, len(pix), 4096):
            self.spi_writebyte(pix[i:i+4096])
            
        self.digital_write(self.CS_PIN, self.GPIO.HIGH)

    def clear(self):
        """Clear display"""
        _buffer = [0xff] * (self.width * self.height * 2)
        self.SetWindows(0, 0, self.width, self.height)
        self.digital_write(self.DC_PIN, self.GPIO.HIGH)
        self.digital_write(self.CS_PIN, self.GPIO.LOW)
        
        for i in range(0, len(_buffer), 4096):
            self.spi_writebyte(_buffer[i:i+4096])
            
        self.digital_write(self.CS_PIN, self.GPIO.HIGH)

    def clear_black(self):
        """Clear display with black"""
        _buffer = [0x00] * (self.width * self.height * 2)
        self.SetWindows(0, 0, self.width, self.height)
        self.digital_write(self.DC_PIN, self.GPIO.HIGH)
        self.digital_write(self.CS_PIN, self.GPIO.LOW)
        
        for i in range(0, len(_buffer), 4096):
            self.spi_writebyte(_buffer[i:i+4096])
            
        self.digital_write(self.CS_PIN, self.GPIO.HIGH)

    def clear_color(self, color):
        """Clear display with specific color"""
        _buffer = [color >> 8, color & 0xff] * (self.width * self.height)
        self.SetWindows(0, 0, self.width, self.height)
        self.digital_write(self.DC_PIN, self.GPIO.HIGH)
        self.digital_write(self.CS_PIN, self.GPIO.LOW)
        
        for i in range(0, len(_buffer), 4096):
            self.spi_writebyte(_buffer[i:i+4096])
            
        self.digital_write(self.CS_PIN, self.GPIO.HIGH)