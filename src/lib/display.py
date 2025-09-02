import time
import os
from . import lcdconfig
import numpy as np
from PIL import Image,ImageDraw,ImageFont
try:
    import spidev
except ModuleNotFoundError:
    from hardware.simulation import MockSpiDev as spidev
    
    
class Imager:
    def __init__(self, width,height,color):
        self.width = width
        self.height = height
        self.color = color
        self.is_rotated=False
        self.is_init=False
        
        self.image = Image.new("RGB", (self.width, self.height ), self.color)
        self.draw = ImageDraw.Draw(self.image)
   
    
class LCD(lcdconfig.RaspberryPi):
    width = 240
    height = 320
    
    def __init__(self,spi=spidev.SpiDev(0,0),spi_freq=40000000,rst = 27,dc = 25,bl = 18,bl_freq=1000,i2c=None,i2c_freq=100000,screen_bg="WHITE",imager=None,gpio=None):
        super().__init__(spi=spi, spi_freq=spi_freq, rst=rst, dc=dc, bl=bl, bl_freq=bl_freq, i2c=i2c, i2c_freq=i2c_freq,gpio_manger=gpio)
        
        self.screen_bg = screen_bg
        self.imager = imager
         # Initialize the display when entering the context
        font_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..","..", "fonts")
    
        self.font_big = self.load_font(f"{font_base}/OpenSans-Regular.ttf", 14)
        self.font_medium = self.load_font(f"{font_base}/OpenSans-Regular.ttf", 12)
        self.font_small = self.load_font(f"{font_base}/OpenSans-Regular.ttf", 10)
        
        
        self.add_image()
        # if 
        self.Init()
    def add_image(self):
        if self.imager:
            # print("using imager")
            self.main_image = self.imager.image
            self.draw =  self.imager.draw
        else:
            self.main_image = Image.new("RGB", (self.height, self.width ), self.screen_bg)
            self.draw = ImageDraw.Draw(self.main_image)
            
        
    def load_font(self, path, size):
        """
        Attempt to load a TrueType font file. If the file cannot be opened, a default font is used instead.
        """
        try:
            font = ImageFont.truetype(path, size)
            # print(f"Loaded font {path} successfully.")
            return font
        except IOError:
            print(f"Failed to load font from {path}, using default font.")
            return ImageFont.load_default()
         
    def __enter__(self):
       
        self.clear()

        return self
    def cleanup_resources(self):
        self.clear()  # Optionally clear the display when exiting the context
        self.module_exit()  # Clean up resources, if any specific cleanup is necessary
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_resources() 

    def command(self, cmd):
        self.digital_write(self.DC_PIN, self.GPIO.LOW)
        self.spi_writebyte([cmd])

    def data(self, val):
        self.digital_write(self.DC_PIN, self.GPIO.HIGH)
        self.spi_writebyte([val])

    def reset(self):
        """Reset the display"""
        self.GPIO.output(self.RST_PIN,self.GPIO.HIGH)
        time.sleep(0.01)
        self.GPIO.output(self.RST_PIN,self.GPIO.LOW)
        time.sleep(0.01)
        self.GPIO.output(self.RST_PIN,self.GPIO.HIGH)
        time.sleep(0.01)

    def Init(self):
        """Initialize display"""
        self.module_init()
        self.reset()

        self.command(0x11)#'''Sleep out'''
	
        self.command(0xCF)#
        self.data(0x00)#
        self.data(0xC1)#
        self.data(0X30)#
        self.command(0xED)#
        self.data(0x64)#
        self.data(0x03)#
        self.data(0X12)#
        self.data(0X81)#
        self.command(0xE8)#
        self.data(0x85)#
        self.data(0x00)#
        self.data(0x79)#
        self.command(0xCB)#
        self.data(0x39)#
        self.data(0x2C)#
        self.data(0x00)#
        self.data(0x34)#
        self.data(0x02)#
        self.command(0xF7)#
        self.data(0x20)#
        self.command(0xEA)#
        self.data(0x00)#
        self.data(0x00)#
        self.command(0xC0)#'''Power control'''
        self.data(0x1D)#'''VRH[5:0]'''
        self.command(0xC1)#'''Power control'''
        self.data(0x12)#'''SAP[2:0]#BT[3:0]'''
        self.command(0xC5)#'''VCM control'''
        self.data(0x33)#
        self.data(0x3F)#
        self.command(0xC7)#'''VCM control'''
        self.data(0x92)#
        self.command(0x3A)#'''Memory Access Control'''
        self.data(0x55)#
        self.command(0x36)#'''Memory Access Control'''
        self.data(0x08)#
        self.command(0xB1)#
        self.data(0x00)#
        self.data(0x12)#
        self.command(0xB6)#'''Display Function Control'''
        self.data(0x0A)#
        self.data(0xA2)#

        self.command(0x44)#
        self.data(0x02)#

        self.command(0xF2)#'''3Gamma Function Disable'''
        self.data(0x00)#
        self.command(0x26)#'''Gamma curve selected'''
        self.data(0x01)#
        self.command(0xE0)#'''Set Gamma'''
        self.data(0x0F)#
        self.data(0x22)#
        self.data(0x1C)#
        self.data(0x1B)#
        self.data(0x08)#
        self.data(0x0F)#
        self.data(0x48)#
        self.data(0xB8)#
        self.data(0x34)#
        self.data(0x05)#
        self.data(0x0C)#
        self.data(0x09)#
        self.data(0x0F)#
        self.data(0x07)#
        self.data(0x00)#
        self.command(0XE1)#'''Set Gamma'''
        self.data(0x00)#
        self.data(0x23)#
        self.data(0x24)#
        self.data(0x07)#
        self.data(0x10)#
        self.data(0x07)#
        self.data(0x38)#
        self.data(0x47)#
        self.data(0x4B)#
        self.data(0x0A)#
        self.data(0x13)#
        self.data(0x06)#
        self.data(0x30)#
        self.data(0x38)#
        self.data(0x0F)#
        self.command(0x29)#'''Display on'''

    # Include other methods like SetWindows, ShowImage, clear, etc.

    def SetWindows(self, Xstart, Ystart, Xend, Yend):
        #set the X coordinates
        self.command(0x2A)
        self.data(Xstart >> 8)
        self.data(Xstart & 0xff)
        self.data(Xend >> 8)
        self.data((Xend - 1) & 0xff)
        #set the Y coordinates
        self.command(0x2B)
        self.data(Ystart >> 8)
        self.data(Ystart & 0xff)
        self.data(Yend >> 8)
        self.data((Yend - 1) & 0xff)
        self.command(0x2C)
    def rotate_img(self,angle=0):
        #rotate the image
        if self.imager and not self.imager.is_rotated:
           
            self.imager.is_rotated = True
        self.main_image = self.main_image.rotate(angle)
        
        
    def show(self):
        self.ShowImage(self.main_image.convert('RGB'))  # Display the image on the LCD in RGB mode
    def ShowImage(self, image, Xstart=0, Ystart=0):
        """Show image from PIL Image"""
        
        import sys
        if "linux" not in sys.platform:
            save_dir="screenshots"
            os.makedirs(save_dir, exist_ok=True)
            i = 1  # Start from 1
            while os.path.exists(os.path.join(save_dir, f"current_screen_{i}.png")):
                i += 1  # Increment if file exists
            filename = os.path.join(save_dir, f"current_screen_{i}.png")
            image.save(filename)
            return
        image = image.rotate(180)
            
        imwidth, imheight = image.size
        if imwidth == self.height and imheight ==  self.width:
            # print("ShowImage onLonger Side")
            img = self.np.asarray(image)
            pix = self.np.zeros((imheight,imwidth , 2), dtype = self.np.uint8)
            
            pix[...,[0]] = self.np.add(self.np.bitwise_and(img[...,[0]],0xF8),self.np.right_shift(img[...,[1]],5))
            pix[...,[1]] = self.np.add(self.np.bitwise_and(self.np.left_shift(img[...,[1]],3),0xE0), self.np.right_shift(img[...,[2]],3))

            pix = pix.flatten().tolist()
            
            self.command(0x36)
            self.data(0x78) 
            self.SetWindows ( 0, 0, self.height, self.width)
            self.digital_write(self.DC_PIN,self.GPIO.HIGH)
            for i in range(0,len(pix),4096):
                self.spi_writebyte(pix[i:i+4096])
            
        else :
            img = self.np.asarray(image)
            pix = self.np.zeros((imheight,imwidth , 2), dtype = self.np.uint8)
            
            pix[...,[0]] = self.np.add(self.np.bitwise_and(img[...,[0]],0xF8),self.np.right_shift(img[...,[1]],5))
            pix[...,[1]] = self.np.add(self.np.bitwise_and(self.np.left_shift(img[...,[1]],3),0xE0), self.np.right_shift(img[...,[2]],3))

            pix = pix.flatten().tolist()
            
            self.command(0x36)
            self.data(0x08) 
            self.SetWindows ( 0, 0, self.width, self.height)
            self.digital_write(self.DC_PIN,self.GPIO.HIGH)
            for i in range(0,len(pix),4096):
                self.spi_writebyte(pix[i:i+4096])

    def clear(self):
        """Clear display"""
        _buffer = [0xff]*(self.height * self.width * 2)
        time.sleep(0.02)
        self.SetWindows ( 0, 0, self.height, self.width)
        self.digital_write(self.DC_PIN,self.GPIO.HIGH)
        for i in range(0,len(_buffer),4096):
            self.spi_writebyte(_buffer[i:i+4096])
            	
        self.add_image()
        
    def clear_color(self,color):
        """Clear contents of image buffer"""
        _buffer = [color>>8, color & 0xff]*(self.height * self.width)
        time.sleep(0.02)
        self.SetWindows ( 0, 0, self.height, self.width)
        self.digital_write(self.DC_PIN,self.GPIO.HIGH)
        for i in range(0,len(_buffer),4096):
            self.spi_writebyte(_buffer[i:i+4096])

   