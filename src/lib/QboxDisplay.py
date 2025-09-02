#!/usr/bin/python
# -*- coding: UTF-8 -*-
import os
import sys
import time
import logging
import threading
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import cairosvg
import io
from ..utils.menu import MenuContext
from display import LCD_2inch4

class StatusIcons:
    @staticmethod
    def get_battery_svg(percentage, is_charging=False):
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
        <svg width="24" height="12" viewBox="0 0 24 12" xmlns="http://www.w3.org/2000/svg">
            <rect x="1" y="1" width="20" height="10" stroke="white" stroke-width="1" fill="none"/>
            <rect x="21" y="3.5" width="2" height="5" fill="white"/>
            <rect x="2" y="2" width="{18 * percentage / 100}" height="8" fill="white"/>
            {
            '<path d="M11 2 L13 6 L9 6 L11 10" stroke="white" stroke-width="1" fill="none"/>'
            if is_charging else ''
            }
        </svg>'''
        return svg

    @staticmethod
    def get_wifi_svg(signal_strength):
        arcs = [
            '<path d="M3 9 A 8 8 0 0 1 17 9" stroke="white" stroke-width="1.5" fill="none" opacity="0.3"/>',
            '<path d="M6 12 A 5 5 0 0 1 14 12" stroke="white" stroke-width="1.5" fill="none" opacity="0.3"/>',
            '<path d="M9 15 A 2 2 0 0 1 11 15" stroke="white" stroke-width="1.5" fill="none" opacity="0.3"/>'
        ]
        
        active_arcs = [
            arc.replace('opacity="0.3"', 'opacity="1"')
            for i, arc in enumerate(reversed(arcs))
            if i < signal_strength
        ]
        
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
        <svg width="20" height="20" viewBox="0 0 20 20" xmlns="http://www.w3.org/2000/svg">
            {''.join(arcs)}
            {''.join(active_arcs)}
            <circle cx="10" cy="17" r="1" fill="white"/>
        </svg>'''
        return svg

    @staticmethod
    def svg_to_pil(svg_content, size=None):
        png_bytes = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'))
        img = Image.open(io.BytesIO(png_bytes))
        if size:
            img = img.resize(size, Image.LANCZOS)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        return img

class QBoxDisplay:
    # Screen dimensions for landscape
    WIDTH = 320
    HEIGHT = 240

    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        
        try:
            # Initialize display
            self.lcd = LCD_2inch4.LCD_2inch4()
            self.menu = MenuContext()
            self.lcd.Init()
            self.lcd.clear()
            
            # Load fonts
            self.setup_fonts()
            
            # Initialize status icons
            self.status_icons = StatusIcons()
            
            # State variables
            self.current_section = 'home'
            self.battery_level = 85
            self.is_charging = False
            self.wifi_connected = True
            self.wifi_signal_strength = 3  # 0-3
            self.firmware_version = "v1.0.0"
            
            # Create initial image buffer
            self.create_canvas()
            
            # Start time update thread
            self.running = True
            self.update_thread = threading.Thread(target=self._time_update_loop)
            self.update_thread.daemon = True
            self.update_thread.start()
            
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise
    def handle_long_press(self):
        if not self.menu.is_active:
            # Start menu on long press when menu is inactive
            self.menu.start_menu()
            self.update_display()
        else:
            # Select current item and end menu on long press when menu is active
            selected_item = self.menu.get_current_item()
            self.handle_menu_selection(selected_item)
            self.menu.end_menu()
            self.update_display()
    def handle_double_press(self):
        pass
    def handle_short_press(self):
        if self.menu.is_active:
            # Navigate to next item on short press when menu is active
            self.menu.next_item()
            self.update_display()

    def handle_menu_selection(self, selected_item):
        if selected_item == "Take Photo":
            self.show_message("Taking photo...")
            time.sleep(2)
        elif selected_item == "Account Balance":
            self.show_message("Balance: $1,234.56")
            time.sleep(2)
        elif selected_item == "Night Mode":
            self.show_message("Switching to Night Mode...")
            time.sleep(1)
        elif selected_item == "Day Mode":
            self.show_message("Switching to Day Mode...")
            time.sleep(1)
    def draw_menu(self, draw):
        if not self.menu.is_active:
            return
            
        for i, item in enumerate(self.menu.items):
            y = self.MENU_START_Y + (i * self.MENU_ITEM_HEIGHT)
            
            # Draw selection highlight
            if i == self.menu.current_index:
                draw.rectangle([0, y, self.WIDTH, y + self.MENU_ITEM_HEIGHT], fill='blue')
                text_color = 'white'
            else:
                text_color = 'black'
            
            # Draw menu item text
            text_width = self.font.getsize(item)[0]
            x = (self.WIDTH - text_width) // 2
            text_y = y + (self.MENU_ITEM_HEIGHT - 16) // 2
            draw.text((x, text_y), item, font=self.font, fill=text_color)


    def show_message(self, message):
        image = Image.new('RGB', (self.WIDTH, self.HEIGHT), 'white')
        draw = ImageDraw.Draw(image)
        
        # Draw status bar
        self.draw_status_bar(draw)
        
        # Draw message
        text_width = self.font.getsize(message)[0]
        x = (self.WIDTH - text_width) // 2
        y = (self.HEIGHT - self.STATUS_BAR_HEIGHT) // 2
        draw.text((x, y), message, font=self.font, fill='black')
        
        self.lcd.ShowImage(image)
        
    def setup_fonts(self):
        try:
            font_paths = [
                "../Font/Font01.ttf",
                "../Font/Font02.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            ]
            
            font_path = next((path for path in font_paths if os.path.exists(path)), None)
            if not font_path:
                raise FileNotFoundError("No suitable fonts found")
                
            self.font_small = ImageFont.truetype(font_path, 14)
            self.font_medium = ImageFont.truetype(font_path, 18)
            self.font_large = ImageFont.truetype(font_path, 24)
            
        except Exception as e:
            self.logger.error(f"Font setup error: {e}")
            raise

    def create_canvas(self):
        self.image = Image.new('RGB', (self.WIDTH, self.HEIGHT), 'BLACK')
        self.draw = ImageDraw.Draw(self.image)

    def draw_status_bar(self):
        try:
            # Status bar background with margin from top
            margin_top = 3
            bar_height = 30
            right_margin = 10
            self.draw.rectangle([0, margin_top, self.WIDTH, margin_top + bar_height], fill='BLUE')
            
            # Time on left side
            self.draw.text(
                (10, margin_top + 5),
                datetime.now().strftime("%H:%M"),
                font=self.font_small,
                fill='WHITE'
            )
            
            # Right-aligned elements (working from right edge)
            current_x = self.WIDTH - right_margin
            
            # Battery icon with status
            battery_svg = self.status_icons.get_battery_svg(
                self.battery_level,
                self.is_charging
            )
            battery_img = self.status_icons.svg_to_pil(battery_svg, size=(24, 12))
            battery_y = margin_top + 8
            battery_x = current_x - 24
            
            # Paste battery icon
            self.image.paste(battery_img, (battery_x, battery_y))
            
            # Battery percentage
            current_x = battery_x - 5
            percentage_text = f"{self.battery_level}%"
            percentage_width = self.font_small.getlength(percentage_text)
            self.draw.text(
                (current_x - percentage_width, margin_top + 5),
                percentage_text,
                font=self.font_small,
                fill='WHITE'
            )
            
            # WiFi icon
            if self.wifi_connected:
                current_x = current_x - percentage_width - 8
                wifi_svg = self.status_icons.get_wifi_svg(self.wifi_signal_strength)
                wifi_img = self.status_icons.svg_to_pil(wifi_svg, size=(20, 20))
                wifi_y = margin_top + 4
                wifi_x = current_x - 20
                self.image.paste(wifi_img, (wifi_x, wifi_y))
                
        except Exception as e:
            self.logger.error(f"Status bar drawing error: {e}")

    def draw_details_header(self):
        try:
            y_pos = 40
            self.draw.text((10, y_pos), "QBox", font=self.font_medium, fill='WHITE')
            current_date = datetime.now().strftime("%Y-%m-%d")
            date_w = self.font_medium.getlength(current_date)
            self.draw.text((self.WIDTH//2 - date_w//2, y_pos), current_date, 
                          font=self.font_medium, fill='WHITE')
            
        except Exception as e:
            self.logger.error(f"Header drawing error: {e}")

    def draw_firmware_version(self):
        try:
            text = f"Firmware: {self.firmware_version}"
            text_w = self.font_small.getlength(text)
            self.draw.text((self.WIDTH - text_w - 5, self.HEIGHT - 20), 
                          text, font=self.font_small, fill='WHITE')
            
        except Exception as e:
            self.logger.error(f"Firmware version drawing error: {e}")

    def draw_home_page(self):
        try:
            welcome_text = "Welcome to QBox"
            touch_text = "Touch to begin"
            
            w_width = self.font_large.getlength(welcome_text)
            t_width = self.font_medium.getlength(touch_text)
            
            y_pos = self.HEIGHT // 3
            self.draw.text((self.WIDTH//2 - w_width//2, y_pos), 
                          welcome_text, font=self.font_large, fill='WHITE')
            
            self.draw.text((self.WIDTH//2 - t_width//2, y_pos + 40), 
                          touch_text, font=self.font_medium, fill='WHITE')
            
        except Exception as e:
            self.logger.error(f"Home page drawing error: {e}")
    def draw_results(self, test_number, aflatoxin, grain_count, grain_type, purity):
        y_pos = 80
        self.draw.text((10, y_pos), f"Test #{test_number}", 
                      font=self.font_medium, fill='white')
        self.draw.text((10, y_pos + 25), f"Aflatoxin: {aflatoxin} ppb", 
                      font=self.font_medium, fill='white')
        self.draw.text((10, y_pos + 50), f"Grain Count: {grain_count}", 
                      font=self.font_medium, fill='white')
        self.draw.text((10, y_pos + 75), f"Type: {grain_type}", 
                      font=self.font_medium, fill='white')
        self.draw.text((10, y_pos + 100), f"Purity: {purity}%", 
                      font=self.font_medium, fill='white')
    def draw_capture_progress(self, stage):
        y_pos = 80
        stages = {
            'capture': 33,
            'processing': 66,
            'uploading': 100
        }
        
        progress = stages.get(stage, 0)
        
        # Progress bar
        self.draw.rectangle([10, y_pos, 310, y_pos + 20], outline='white')
        self.draw.rectangle(
            [12, y_pos + 2, 12 + (296 * progress // 100), y_pos + 18],
            fill='green'
        )
        
        # Stage text
        self.draw.text((10, y_pos + 30), f"Status: {stage.capitalize()}", 
                      font=self.font_medium, fill='white')
    def draw_account_details(self, name, amount, account_number):
        y_pos = 80
        self.draw.text((10, y_pos), f"Name: {name}", font=self.font_medium, fill='white')
        self.draw.text((10, y_pos + 25), f"Amount: ${amount:.2f}", 
                      font=self.font_medium, fill='white')
        self.draw.text((10, y_pos + 50), f"Account: {account_number}", 
                      font=self.font_medium, fill='white')
        
    def update_display(self):
        try:
            self.create_canvas()
            
            self.draw_status_bar()
            self.draw_details_header()
            self.draw_firmware_version()
            
            if self.current_section == 'home':
                self.draw_home_page()
            elif self.current_section == 'account':
                self.draw_account_details("John Doe", 1000.00, "1234567890")
            elif self.current_section == 'capture':
                self.draw_capture_progress('processing')
            elif self.current_section == 'results':
                self.draw_results(1, 15.5, 1000, "Maize", 98.5)
            
            self.lcd.ShowImage(self.image)
            
        except Exception as e:
            self.logger.error(f"Display update error: {e}")
    def set_section(self, section):
        """Change current section and update display"""
        self.current_section = section
        self.update_display()
        
    def set_battery_level(self, level, is_charging=False):
        """Update battery level and charging status"""
        self.battery_level = max(0, min(100, level))
        self.is_charging = is_charging
        self.update_display()
        
    def set_wifi_status(self, connected):
        """Update WiFi connection status"""
        self.wifi_connected = connected
        self.update_display()

    def _time_update_loop(self):
        while self.running:
            try:
                self.update_display()
                time.sleep(60 - datetime.now().second)
            except Exception as e:
                self.logger.error(f"Time update error: {e}")
                time.sleep(60)

    def cleanup(self):
        try:
            self.running = False
            if hasattr(self, 'update_thread') and self.update_thread.is_alive():
                self.update_thread.join()
            if hasattr(self, 'lcd'):
                self.lcd.clear()
                self.lcd.module_exit()
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

# if __name__ == "__main__":
#     display = None
#     try:
#         display = QBoxDisplay()
        
#         # Main loop
#         while True:
#             time.sleep(1)
            
#     except KeyboardInterrupt:
#         logging.info("Program terminated by user")
#     except Exception as e:
#         logging.error(f"Unexpected error: {e}")
#     finally:
#         if display:
#             display.cleanup()