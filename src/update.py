import os
from services.firmware import FirmwareUpdater
import configparser



config_path=os.path.abspath("../config/config.ini")



updater = FirmwareUpdater(config_path)
updater.run()