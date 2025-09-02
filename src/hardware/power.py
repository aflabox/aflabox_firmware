import os
import threading
import asyncio
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from db.batter_db import BatteryDB
try:
    import smbus
except Exception:
    from .simulation import VirtualSMBus as smbus


DB_PATH = "battery_data.db"




class Powerpi:
    PORT = 1
    ADDRESS = 0x6A

    REG_STATUS = 0x0B
    REG_VBAT = 0x0E
    REG_IBAT = 0x12
    REG_VBUS = 0x11
    REG_CONV_ADC = 0x02
    REG_FAULT = 0x0C

    VBAT_LOW = 3.2
    VBAT_MAX = 4.208
    BAT_CAPACITY = 2900
    CURRENT_DRAW = 2000

    def __init__(self):
        self.bus = smbus.SMBus(self.PORT)
        self.battery_status = {}
        self.event_queue = asyncio.Queue()
        self.running = True
        self.db = BatteryDB()
        self.loop = None

        self.thread = None

    def is_battery_present(self):
        status = self.bus.read_byte_data(self.ADDRESS, self.REG_STATUS)
        return bool(status & 0b00000100)

    def get_fault(self):
        fault_status = self.bus.read_byte_data(self.ADDRESS, self.REG_FAULT)
        faults = {
            0b10000000: "Watchdog Timer Fault",
            0b01000000: "Safety Timer Expired",
            0b00100000: "Battery Overvoltage",
            0b00010000: "Thermal Shutdown",
            0b00001000: "Battery Not Detected",
            0b00000100: "Charge Timeout",
            0b00000010: "Input Overvoltage",
            0b00000001: "Input Undervoltage"
        }
        return [msg for bit, msg in faults.items() if fault_status & bit]

    def _int_to_bool_list(self, num):
        return [bool(num & (1 << n)) for n in range(8)]

    def _vbat_convert(self, vbat_byte):
        return 2.304 + sum(self._int_to_bool_list(vbat_byte)[i] * (0.02 * (2 ** i)) for i in range(7))

    def _ibat_convert(self, ibat_byte):
        return sum(self._int_to_bool_list(ibat_byte)[i] * (50 * (2 ** i)) for i in range(7))

    def _vbus_convert(self, vbus_byte):
        return 2.6 + sum(self._int_to_bool_list(vbus_byte)[i] * (0.1 * (2 ** i)) for i in range(7))

    def _calc_bat_charge_percent(self, vbat):
        percent = (vbat - self.VBAT_LOW) / (self.VBAT_MAX - self.VBAT_LOW)
        return max(0, min(100, int(percent * 100)))

    def _calc_time_left(self, vbat):
        return max(0, int(self._calc_bat_charge_percent(vbat) * 60 * self.BAT_CAPACITY / self.CURRENT_DRAW))

    def read_status(self,db=None):
        try:
            if not db:
                db = BatteryDB()
                
            self.bus.write_byte_data(self.ADDRESS, self.REG_CONV_ADC, 0b10011101)
            time.sleep(2)

            status = self._int_to_bool_list(self.bus.read_byte_data(self.ADDRESS, self.REG_STATUS))
            vbat = self._vbat_convert(self.bus.read_byte_data(self.ADDRESS, self.REG_VBAT))
            ibat = self._ibat_convert(self.bus.read_byte_data(self.ADDRESS, self.REG_IBAT))
            vbus = self._vbus_convert(self.bus.read_byte_data(self.ADDRESS, self.REG_VBUS))

            self.bus.write_byte_data(self.ADDRESS, self.REG_CONV_ADC, 0b00011101)

        except Exception as ex:
            logging.error(f"Error reading UPS data: {ex}")
            return None

        power_status = "Connected" if status[2] else "Not Connected"
        time_left = -1 if status[2] else self._calc_time_left(vbat)

        if status[3] and status[4]:
            charge_status = "Charging done"
        elif status[4]:
            charge_status = "Charging"
        elif status[3]:
            charge_status = "Pre-Charge"
        else:
            charge_status = "Not Charging"

        hasBattery = self.is_battery_present()
        battery_percentage = self._calc_bat_charge_percent(vbat)

        battery_color = (
            "#555555" if not hasBattery else
            "#8B0000" if battery_percentage <= 10 else
            "#FF8C00" if battery_percentage <= 30 else
            "#1E90FF" if battery_percentage <= 60 else
            "#32CD32" if battery_percentage <= 90 else
            "#006400"
        )

        new_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'PowerInputStatus': power_status,
            'InputVoltage': round(vbus, 3),
            'ChargeStatus': charge_status,
            'BatteryVoltage': round(vbat, 3),
            'BatteryPercentage': battery_percentage,
            'ChargeCurrent': ibat,
            'TimeRemaining': time_left,
            'hasBattery': hasBattery,
            'BatteryColor': battery_color,
            'faults': ", ".join(self.get_fault())
        }

        if new_status != self.battery_status:
            self.battery_status = new_status
            if self.loop:
                asyncio.run_coroutine_threadsafe(self.event_queue.put(new_status), self.loop)
            try:
                db.insert_record(new_status)
                db.delete_old_records()
            except Exception:
                pass
           


        return new_status
    def get_latest_status(self):
        """Return the latest battery status."""
        return self.battery_status

    def get_last_n_records(self, n=10):
        db = BatteryDB()
        results = db.get_last_n_records(n)
        db.cleanup()
        return results

    def battery_monitor_thread(self):
        thread_db = BatteryDB()
        while self.running:
            self.read_status(thread_db)
            time.sleep(5)

    def start_monitoring(self, loop,queue=None):
        self.loop = loop
        self.thread = threading.Thread(target=self.battery_monitor_thread, daemon=True)
        self.thread.start()

    def stop_monitoring(self):
        self.running = False
        if self.thread:
            self.thread.join()

    async def wait_for_update(self):
        return await self.event_queue.get()

    def cleanup(self):
        self.db.cleanup()
