from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from time import sleep
from lib.display import LCD,Imager 
from tinydb import  Query
from .power import Powerpi
from utils.thread_locks import get_db
import random
import time
from enum import Enum
import os,json
from unittest.mock import MagicMock
from utils.internet_monitor  import InternetMonitor



options = [
    "Start Aflatoxin Test",
    "View Test Logs",
    "File Queue",
    "System Status",
    "Update Firmware",
    "Shutdown",
    "Exit"
]

# Initialize TinyDB
# db = get_db("speedtest_cache.json")
Speed = Query()
internet_monitor = InternetMonitor()

class DisplayType(Enum):
    MINI = 'MINI_SCREEN'
    FULL = 'FULL_SCREEN'

def split_ip(ip_string):
    """Splits a string containing both IPv4 and IPv6 addresses."""
    parts = ip_string.split()
    ipv4 = parts[0] if "." in parts[0] else parts[1]
    ipv6 = parts[1] if ":" in parts[1] else parts[0]
    return ipv4, ipv6
class DashboardAnimation:
    def __init__(self,gpio=None,display_type=DisplayType.FULL):
        """Initialize dashboard animation settings."""
        # Image size
        self.width, self.height = 320, 240  
        self.num_frames = 11  # Number of frames
        self.selected_menu=None
        self.config = None
        self.display_type = display_type
        self.network_info={
            "signal_strength":0,
            "internet_available":False,
            "internet_quality":0
        }
        # Load fonts
        self.ups = Powerpi()

        # Always resolve relative to *this file's location*, not the working directory
        font_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..","..","fonts")

        self.is_home_screen=False
        self.font_large = self.load_font(f"{font_base}/OpenSans-Regular.ttf", 20)
        self.font_small = self.load_font(f"{font_base}/OpenSans-Regular.ttf", 12)
        self.font_medium = self.load_font(f"{font_base}/OpenSans-Regular.ttf", 16)
        self.font_xsmall = self.load_font(f"{font_base}/OpenSans-Regular.ttf", 10)
        self.font_xxsmall = self.load_font(f"{font_base}/OpenSans-Regular.ttf", 9)
        self.pixel = self.load_font(f"{font_base}/PixelOperator8.ttf",24)
        self.lcd = LCD(screen_bg="WHITE",gpio=gpio)
        self.selected_index = 0

        # Status bar (top)
        self.status_bar_height = 30  
        self.battery_x, self.battery_y, self.battery_w, self.battery_h = 270, 5, 30, 15  # Battery icon
        self.wifi_x, self.wifi_y = 240, 5  # WiFi icon position
        self.logo_x, self.logo_y = 10, 5  # Logo position

        # Footer (bottom)
        self.footer_y = self.height - 20  # Firmware version position
        self.firmware_version = ""

        # Create a base image
        self.redraw_base()
    def update_status(self,msg):
        self.center_line(message=msg)
    def show_splash_screen(self,msg):
        self.center_line(message=msg)
    def show_error(self,msg,key="Error"):
        self.show_table_screen([[key,msg]])
    def redraw_base(self):
        self.base_img = Image.new("RGB", (self.width, self.height), "white")
        self.draw_static_elements()
        
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
    def cleanup(self):
        self.lcd.cleanup_resources()
    def addConfig(self,config):
        self.config =config
        self.redraw_base()
    def isHomeScreen(self):
        return self.is_home_screen
    def is_firmware_oudated(self):
        self.firmware_version = self.config.get("FIRMWARE_MANAGEMENT","current_version") if self.config else ""
        next_version =self.config.get("FIRMWARE_MANAGEMENT","next_version") if self.config else ""
        firmware_color = "red" if self.firmware_version!=next_version else "black"
        return self.firmware_version!=next_version,firmware_color
        
    def draw_static_elements(self):
        """Draw static elements like logo, battery outline, and footer text."""
        
        outdated,firmware_color=self.is_firmware_oudated()
        draw = ImageDraw.Draw(self.base_img)
        outdated,firmware_color=self.is_firmware_oudated()
        draw.text((self.logo_x, self.logo_y), "Aflabox", fill=firmware_color,font=self.font_medium)  # Logo
        draw.rectangle([self.battery_x, self.battery_y, self.battery_x + self.battery_w, self.battery_y + self.battery_h], outline="black", width=1)  # Battery outline
        draw.text((210, self.footer_y), f"Firmware v{self.firmware_version}", fill=firmware_color)  # Firmware version
    def getImage(self):
        img = self.base_img.copy()
        draw = ImageDraw.Draw(img)
        # Draw status bar elements (battery & WiFi)
        self.draw_status_bar(draw)
        
    def generate_frames(self):
        """Generate animation frames for all screens."""
        frames = []
        screens = ["Home", "Battery", "WiFi", "Test Results", "Alerts"]
        
        self.lcd.clear()

        for i in range(self.num_frames):
            battery_level = 100 - i * 10  # Battery decreasing
            cached_speed = internet_monitor.get_last_known()
            if not cached_speed:
                wifi_strength = 0
            else:
                wifi_strength  = cached_speed["strength_score"]

            img = self.base_img.copy()
            draw = ImageDraw.Draw(img)

            # Draw status bar elements (battery & WiFi)
            self.draw_status_bar(draw, battery_level, wifi_strength)

            # Cycle through screens
            screen_name = screens[i % len(screens)]
            self.draw_screen(draw, screen_name, battery_level, wifi_strength)

            frames.append(img)
            self.lcd.ShowImage(img.convert('RGB'))  # Display the image on the LCD in RGB mode
            time.sleep(3)
    def show_homescreen(self):
        self.is_home_screen=True
       
        img = self.base_img.copy()
        
        draw = ImageDraw.Draw(img)
        
        battery_level,wifi_strength = self.draw_status_bar(draw)
       
        self.draw_screen(draw, "Home",battery_level,wifi_strength)
      
        self.lcd.clear()
        self.lcd.ShowImage(img.convert('RGB')) 
        
        
        
    def display_alert(self,data):
        img = self.base_img.copy()
        draw = ImageDraw.Draw(img)
        self.draw_status_bar(draw)
        self.draw_table(draw,data)
        self.lcd.clear()
        self.lcd.ShowImage(img.convert('RGB'))
        self.is_home_screen=False
        
    def draw_status_bar(self, draw, battery_level=0, wifi_strength=0):
        """Draw battery and WiFi icons in the status bar."""
        data =self.ups.get_last_n_records(n=1) if self.ups else {}
        if isinstance(data,list):
           if data:  # list is not empty
                data = data[0]
           else:
                data = None
        
        if data:
            #and data["PowerInputStatus"]=="Connected" 
            is_charging =data["ChargeStatus"]=="Charging" 
            battery_percentage = data["BatteryPercentage"]
            battery_color=data["BatteryColor"]
            
        else:
            is_charging=False
            battery_percentage=battery_level
            battery_color="#555555"
            
        
        
        
        fill_width = (battery_percentage / 100) * self.battery_w

        # Draw battery fill
        draw.rectangle([self.battery_x, self.battery_y, self.battery_x + fill_width, self.battery_y + self.battery_h], fill=battery_color)
        draw.rectangle([self.battery_x, self.battery_y, self.battery_x + self.battery_w, self.battery_y + self.battery_h], outline=battery_color, width=2)

        # Draw battery tip
        draw.rectangle([self.battery_x + self.battery_w, self.battery_y + 5, self.battery_x + self.battery_w + 4, self.battery_y + self.battery_h - 5],
                        fill=battery_color, outline=battery_color, width=1)

        # Draw battery percentage or charging icon
        if is_charging:
            draw.text((self.battery_x + 10, self.battery_y + 2), "⚡", fill="black" if battery_percentage<60 else "white", font=self.font_xxsmall)
        else:
            draw.text((self.battery_x + 10, self.battery_y + 2), f"{battery_percentage}%", fill="black", font=self.font_xxsmall)

        # Draw WiFi signal bars
        self._draw_wifi_icon(draw, wifi_strength)
        return battery_percentage,wifi_strength
    def on_network_change(self,signal_strength, internet_available, internet_quality):
        """Handle network changes."""
        self.network_info={
            "signal_strength":signal_strength,
            "internet_available":internet_available,
            "internet_quality":internet_quality
        }
    def _draw_wifi_icon(self, draw, wifi_strength):
        """Draw WiFi signal bars."""
        bar_width = 3
        bar_spacing = 3
        bar_max_height = 15
        
        wifi_strength = self.network_info.get("signal_strength",0)
        internet_available = self.network_info.get("internet_available",False)
        internet_quality=self.network_info.get("internet_quality",0)
        x=wifi_strength
        wifi_strength = (wifi_strength+internet_quality)/2
        print(f"wifi_strength: {x} internet_quality: {internet_quality}  avg: {wifi_strength}")
        
        
            
        if wifi_strength >= 90:
            # 3 bars all deep green
            colors = ['#006400', '#006400', '#006400']  # Deep green for all
        elif wifi_strength >= 60:
            # 2 bars green, 3rd light green
            colors = ['#006400', '#006400', '#90EE90']  # 2 deep green, 1 light green
        elif wifi_strength >= 30:
            # one bar dark red, the rest light red
            colors = ['#8B0000', '#FFC0CB', '#FFC0CB']  # 1 dark red, 2 light red
        else:
            # all light red
            colors = ['#FFC0CB', '#FFC0CB', '#FFC0CB']  # All light red
            
        if wifi_strength<5:
            
            return
        
        if not internet_available:
            colors=["#8B0000","#8B0000","#8B0000"]
            
        

        for i in range(3):
            bar_height = [6, 10, 15][i]
            # if wifi_strength >= (i + 1) * 25:
            #     draw.rectangle([self.wifi_x + i * (bar_width + bar_spacing), self.wifi_y + bar_max_height - bar_height,
            #                     self.wifi_x + (i + 1) * bar_width + i * bar_spacing, self.wifi_y + bar_max_height], 
            #                     fill="green" if wifi_strength > 50 else "red")
            if wifi_strength >= (i + 1) * 25:
                # Draw filled bar
                draw.rectangle([
                    self.wifi_x + i * (bar_width + bar_spacing), 
                    self.wifi_y + bar_max_height - bar_height,
                    self.wifi_x + (i + 1) * bar_width + i * bar_spacing, 
                    self.wifi_y + bar_max_height
                ], fill=colors[i])
            else:
                # Draw empty/outline bar for insufficient score
                draw.rectangle([
                    self.wifi_x + i * (bar_width + bar_spacing), 
                    self.wifi_y + bar_max_height - bar_height,
                    self.wifi_x + (i + 1) * bar_width + i * bar_spacing, 
                    self.wifi_y + bar_max_height
                ], outline="gray")
    def show_screen(self,screen_name, battery_level=0, wifi_strength=0):
        img = self.base_img.copy()
        draw = ImageDraw.Draw(img)
        self.draw_status_bar(draw)
        self.draw_screen(draw,screen_name=screen_name,battery_level=battery_level,wifi_strength=wifi_strength)
        self.lcd.clear()
        self.lcd.ShowImage(img.convert('RGB'))
        
    def show_table_screen(self,data):
        img = self.base_img.copy()
        draw = ImageDraw.Draw(img)
        self.draw_status_bar(draw)
        self.draw_table(draw,data)
        self.lcd.clear()
        self.lcd.ShowImage(img.convert('RGB'))
        
    def draw_screen(self, draw, screen_name, battery_level=0, wifi_strength=0):
        """Draw different screens dynamically based on `screen_name`."""
        
        self.is_home_screen=False
        if screen_name == "Home":
            self.draw_home_screen(draw)
            self.is_home_screen=True
        elif screen_name == "Battery":
            self.draw_battery_info(draw, battery_level)
        elif screen_name == "WiFi":
            self.draw_wifi_info(draw, wifi_strength)
        elif screen_name == "Test Results":
            self.draw_test_results(draw)
        elif screen_name == "Alerts":
            self.draw_alerts(draw, battery_level, wifi_strength)
        elif screen_name == "Shutdown":
             self.center_line("Shutting down in 5 sec")
        elif screen_name=="status":
            self.center_line(draw)
    def center_line(self,message):
        """Center a message in the terminal."""
        img = self.base_img.copy()
        draw = ImageDraw.Draw(img)
        # Get text bounding box
        bbox = draw.textbbox((0, 0), message, font=self.font_medium)

        # Calculate width and height from bbox
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Compute centered position
        x_pos = (320 - text_width) // 2
        y_pos = (200 - text_height) // 2

        # Draw centered text
        draw.text((x_pos, y_pos), message, fill="black", font=self.font_medium)
        self.lcd.clear()
        self.lcd.ShowImage(img.convert('RGB')) 
        
    def show_qrcode(self,link=None):
        """Center a message in the terminal."""
        import qrcode
        img = self.base_img.copy()
        draw = ImageDraw.Draw(img)
        
        qr_text = "https://example.com" if link is None else link
        qr = qrcode.QRCode(box_size=4, border=2)  # Adjust size for fitting
        qr.add_data(qr_text)
        qr.make(fit=True)
        qr_img = qr.make_image(fill="black", back_color="white")
        
        qr_size = 120  # Adjust size
        qr_img = qr_img.resize((qr_size, qr_size))
        
        
        # Define the text (code) to display below the QR code
        code_text = "ABC123"

       

        # Get text bounding box
        bbox = draw.textbbox((0, 0), code_text, font=self.font_medium)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Compute positions to center QR code and text
        qr_x = (320 - qr_size) // 2
        qr_y = (200 - qr_size - text_height - 10) // 2  # Slight padding

        text_x = (320 - text_width) // 2
        text_y = qr_y + qr_size + 5  # Below QR code with padding

        # Paste QR code on image
        img.paste(qr_img, (qr_x, qr_y))

        # Draw the code text below QR code
        draw.text((text_x, text_y), code_text, fill="black", font=self.font_medium)
        self.lcd.clear()
        self.lcd.ShowImage(img.convert('RGB')) 
        
    def show_menu(self,menu=[]):
        # Draw bounding rectangle
        TEXT_X_MARGIN = 15  # Left margin for text
        HIGHLIGHT_X_MARGIN = 15  # Left margin for highlight box
        TEXT_Y_MARGIN = 5   # Space between options
        HIGHLIGHT_Y_MARGIN = 5  # Extra padding around highlight
        self.is_home_screen=False

        img = self.base_img.copy()
        draw = ImageDraw.Draw(img)
        draw.rectangle([(10, 30), (self.base_img.width - 10, self.base_img.height - 68)], outline="blue", width=1)
        battery_level,wifi_strength = self.draw_status_bar(draw)
       
        y_start = 35  # Start within the bounded rectangle
        for i, option in enumerate(options):
            text_color = "blue"
            highlight_top = y_start - HIGHLIGHT_Y_MARGIN
            highlight_bottom = y_start + 12 + HIGHLIGHT_Y_MARGIN

            if i == self.selected_index:
                # Draw highlight box covering the text properly
                # draw.rectangle(
                #     [(HIGHLIGHT_X_MARGIN, highlight_top), (self.base_img.width - HIGHLIGHT_X_MARGIN, highlight_bottom)],
                #     fill=255
                # )
                text_color = "red"  # Invert text color (black)
                self.selected_menu=option

            # Draw option text with left margin
            draw.text((TEXT_X_MARGIN, y_start), option, font=self.font_medium, fill=text_color)
            y_start += 14 + TEXT_Y_MARGIN  # Spacing between options
        
        self.lcd.clear()
        self.lcd.ShowImage(img.convert('RGB')) 
    def getSelectedMenuOption(self):
        return self.selected_menu
    def clearSelectedMenuOption(self):
        self.selected_menu = None
        self.selected_index=0
        
    def move_up(self,channel=None):
        """Moves selection up, loops back if at the top."""
        
        self.selected_index = (self.selected_index - 1) % len(options)
        self.show_menu()

    def move_down(self,channel=None):
        """Moves selection down, loops to the first if at the bottom."""

        self.selected_index = (self.selected_index + 1) % len(options)
        self.show_menu()

    def draw_home_screen(self, draw):
        """Display Home Screen."""
        self.is_home_screen=True
        height=68
        if self.display_type==DisplayType.FULL:
            height=30
        draw.rectangle([(10, 30), (self.base_img.width - 10, self.base_img.height - height)], outline="blue", width=1)
        # draw.text((80, 50), "Welcome!", fill="blue", font=self.font_large)
        text="Welcome!"
        bbox = draw.textbbox((0, 0), text, font=self.font_large)
        text_width = bbox[2] - bbox[0]  # Calculate width from bounding box
        text_height = bbox[3] - bbox[1]  # Calculate height from bounding box
        x = (self.base_img.width - text_width) // 2
        y = 50
        draw.text((x, y), text, fill="blue", font=self.font_large)
        
        # Display dynamic date
        current_date = datetime.now().strftime("%Y-%m-%d")
        text = f"{current_date}"
        bbox = draw.textbbox((0, 0), text, font=self.font_medium)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.base_img.width - text_width) // 2
        y += text_height + 20
        draw.text((x, y), text, fill="black", font=self.font_medium)

        # Add button instruction
        text = "Press button to start."
        bbox = draw.textbbox((0, 0), text, font=self.font_medium)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (self.base_img.width - text_width) // 2
        y += text_height + 20
        draw.text((x, y), text, fill="green", font=self.font_medium)
    def setBatteryUps(self,ups):
        self.ups=ups
    def draw_battery_info(self, draw, battery_level):
        """Display battery details."""
        self.is_home_screen=False
        data =self.ups.get_latest_status() if self.ups else {}
        
        if data:
            bat_data=[
               ["Voltage", f"{data['BatteryVoltage']}V"],
               ["Status", data["ChargeStatus"]],
               ["Charge",f"{data['BatteryPercentage']}%"],
               ["TimeRemaining", data["TimeRemaining"]],
               ["Battery Plugged", "Yes" if data["hasBattery"] else "No"],
               
            ]
        else:
        
          bat_data=[
               ["Voltage", "N/A"],
               ["Status", "N/A"],
               ["Charge",0.0],
               ["TimeRemaining", "N/A"],
               ["Battery Plugged", "N/A"],
               
            ]
          
        self.draw_table(draw, bat_data)
   
        
    def draw_wifi_info(self, draw, wifi_strength):
        """Display WiFi details."""
        cached_speed = internet_monitor.get_last_known()
       
        print(cached_speed)
        if "wifi" in cached_speed:
          wifi_info=cached_speed["wifi"]
          download_speed = int(float(cached_speed.get('download_speed', 0)))
          upload_speed = int(float(cached_speed.get('upload_speed', 0)))

          up = ["D/U", f"{download_speed}/{upload_speed}MB/s"]
          signal_percentage = wifi_info["signal_strength_percentage"]
         
          ipv4, ipv6 = split_ip( wifi_info["ip_address"])
          status = "Weak ❌"
          if signal_percentage > 80:
                status="Excellent 🚀"
          elif signal_percentage > 60:
                status="Good 👍"
          elif signal_percentage > 40:
                status="Fair ⚠"
          ip = ["IP",ipv4]
                
            
          data = [["WiFi Name",wifi_info["ssid"]], ["Signal Strength", f"{signal_percentage}%"], ["Signal Quality",status],ip,up]
        else:
          data = [["WiFi Name", "N/A"], ["Signal Strength", f"N/A"], ["Signal Quality", "N/A"],["IP", "N/A"]]
        self.draw_table(draw, data)

    def draw_test_results(self, draw):
        """Display test results."""
        data = [["Test #", "1"], ["Result", "+"], ["Purity", "95%"], ["Type", "Grain"]]
        self.draw_table(draw, data)

    def draw_alerts(self, draw, battery_level, wifi_strength):
        """Display alerts."""
        alerts = []
        if battery_level < 20:
            alerts.append(["Battery Low", f"{battery_level}%"])
        if wifi_strength < 30:
            alerts.append(["Weak WiFi", f"{wifi_strength}%"])
        self.draw_table(draw, alerts if alerts else [["No Alerts", ""]]) 
    
    def draw_table(self, draw, data, x=10, y=30, row_height=30, col_width=140):
        """Draw tables for structured data."""
        # draw.rectangle([(10, 30), (self.base_img.width - 10, self.base_img.height - height)], outline="blue", width=1)
        self.is_home_screen=False
        for row_idx, row in enumerate(data):
            y_pos = y + row_idx * row_height
            for col_idx, text in enumerate(row):
                x_pos = x + col_idx * col_width
                draw.rectangle([x_pos, y_pos, x_pos + col_width, y_pos + row_height], outline="black", width=1)
                draw.text((x_pos + 10, y_pos + 8), str(text), fill="black", font=self.font_medium)

    def save_animation(self, filename="dashboard_animation_320x240.gif"):
        """Save the animation as a GIF."""
        frames = self.generate_frames()
        try:
           frames[0].save(filename, save_all=True, append_images=frames[1:], duration=500, loop=0)
           print(f"Animation saved as {filename}")
        except Exception:
            pass
        

        