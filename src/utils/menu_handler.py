import asyncio
from .logger import get_logger
from services.camera_scanner_service import CameraScannerService,QueueFileService
from services import gps_service,firmware
from collections import Counter
import json
from utils.helpers import run_sudo_shutdown_no_password

logger=get_logger()

class MenuHandler:
    def __init__(self, click_tracker, dashboard):
        """
        Initialize the MenuHandler class.
        """
        self.updater = None
        self.click_tracker = click_tracker
        self.dashboard = dashboard
        self.menu_context = False  # Track whether we are in menu mode
        self.is_gps_tracking=False
        
    def addScanner(self,camera_scanner:CameraScannerService,counter:Counter):
        self.camera_scanner = camera_scanner
        self.counter=counter
    def addUpdater(self,updater:firmware.FirmwareUpdater):
        self.updater = updater
    async def handle_short_press(self, duration):
        """
        Handles a short press event.
        - Saves the threshold for "click".
        - If in menu context, moves down the menu.
        - Otherwise, displays the menu.
        """
        self.click_tracker.save_threshold("click", duration)

        if self.menu_context:
            self.dashboard.move_down()
        else:
            self.dashboard.show_menu()
            self.menu_context = True

    async def handle_double_press(self, duration):
        """
        Handles a double press event.
        - Saves the threshold for "double_click".
        - If in menu context, moves down.
        - Otherwise, waits for 5 seconds and returns to the home screen.
        """
        self.click_tracker.save_threshold("double_click", duration)

        if self.menu_context:
            self.dashboard.move_down()
        else:
            await asyncio.sleep(5)
            self.dashboard.show_homescreen()
    def show_update_progress(self,data,last=False):
        self.dashboard.show_table_screen(data)
        if last:
            self.dashboard.redraw_base()
        
    async def handle_long_press(self, duration):
        """
        Handles a long press event.
        - Saves the threshold for "long_press".
        - If in menu context, executes selected menu option.
        - Otherwise, does nothing.
        """
        self.click_tracker.save_threshold("long_press", duration)

        if self.menu_context:
            selected = self.dashboard.getSelectedMenuOption()
            self.dashboard.clearSelectedMenuOption()

            if selected:
                if selected == "Start Aflatoxin Test":
                     self.counter['aflatoxin']+1
                     await self.camera_scanner.start()
                elif selected == "View Test Logs":
                    logs = self.camera_scanner.getResultsLogs()
                    if logs.is_empty():
                        self.dashboard.center_line("No Recent Test ")
                        await asyncio.sleep(5)
                    else:
                        for log in logs.peek_all():
                            self.dashboard.show_table_screen(log)
                            await asyncio.sleep(10)
                            
                            
                    
                elif selected == "File Queue":
                   
                    files = QueueFileService(None,None)
                    queue = files.get_queue_status()
                    self.dashboard.show_table_screen([
                                ["Queued", queue["queued"]],
                                ["uploading", queue["uploading"]],
                                ["Completed", queue["completed"]],
                                ["Failed", queue["failed"]],
                            ])
                    await asyncio.sleep(5)
                elif selected == "System Status":
                    self.dashboard.show_screen(screen_name="WiFi")
                    await asyncio.sleep(8)
                    self.dashboard.show_screen(screen_name="Battery")
                    await asyncio.sleep(8)
                    self.dashboard.show_table_screen([
                                ["GPS", "Searching.."]
                    ])
                    self.is_gps_tracking=True
                    manager = gps_service.GPSPowerManager(gps_acquire_time=1,gps_check_timeout=60)
                   
                    try:
                        data=manager.query_and_print()
                        if data["success"]:
                            self.dashboard.show_table_screen([
                                ["GPS", "Connected" if data["is_recent"] else "Prev"],
                                ["Latitude", data["latitude"]],
                                ["Longitude", data["longitude"]],
                            ])
                        elif "error" in data:
                            self.dashboard.show_table_screen(data['error'])
                    except Exception as e:
                        print(f"GPS {e}")
                        self.dashboard.show_table_screen([
                            ["GPS", "Error"],
                        ])
                    await asyncio.sleep(10)
                    
                elif selected=="Shutdown":
                    self.dashboard.show_screen(screen_name="Shutdown")
                    await asyncio.sleep(5)
                    run_sudo_shutdown_no_password()
                elif selected == "Update Firmware":
                
                    self.updater.run(self.show_update_progress)
                    await asyncio.sleep(5)
                
                elif selected == "Exit":
                    pass 
               
                self.menu_context = False
                self.dashboard.show_homescreen()

    async def reset_menu_context(self):
        """
        Resets the menu context after inactivity.
        """
        await asyncio.sleep(10)
        self.menu_context = False
        self.dashboard.show_homescreen()

