#!/bin/bash

set -e

sudo apt-get update
sudo apt-get install -y python3-pip i2c-tools python3-smbus

sudo raspi-config nonint do_i2c 0

pip3 install smbus2

sudo mkdir -p /usr/local/bin
sudo tee /usr/local/bin/bq25895_configurator.py > /dev/null << 'EOF'
import smbus2
import time

I2C_BUS = 1
BQ25895_I2C_ADDRESS = 0x6A

BQ25895_CONFIGURATION = [
    (0x00, 0x3F),
    (0x0A, 0x35),
]

def configure_bq25895():
    bus = smbus2.SMBus(I2C_BUS)
    for register, value in BQ25895_CONFIGURATION:
        try:
            bus.write_byte_data(BQ25895_I2C_ADDRESS, register, value)
            time.sleep(0.05)
        except Exception as e:
            print(f"Failed to write to register 0x{register:02X}: {e}")
    bus.close()

if __name__ == "__main__":
    configure_bq25895()
EOF

sudo chmod +x /usr/local/bin/bq25895_configurator.py

sudo tee /etc/systemd/system/bq25895-config.service > /dev/null <<EOL
[Unit]
Description=Configure BQ25895 at boot before WiFi
Before=network.target
After=multi-user.target
DefaultDependencies=no

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/bq25895_configurator.py
Type=oneshot
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable bq25895-config.service
sudo systemctl start bq25895-config.service
