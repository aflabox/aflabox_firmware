#!/bin/bash

sudo mkdir -p /var/log/device
sudo chmod 775 /var/log/device
sudo chown $USER:$(whoami) /var/log/device
old_path="/etc/supervisor/conf.d/qbox_main.conf"
backup_path="${old_path}.backup"
    
if [ -f "$old_path" ]; then
    sudo mv "$old_path" "$backup_path"
    echo "Backup created at $backup_path"
else
    echo "Error: File $old_path not found."
fi
# Ensure we're running with proper permissions
if [ "$(id -u)" != "0" ]; then
    echo "Setting up sudo access without password..."
    # Check if the user already has passwordless sudo
    if ! sudo -n true 2>/dev/null; then
        # Get current username
        CURRENT_USER=$(whoami)
        
        # Create a temporary sudoers file
        echo "$CURRENT_USER ALL=(ALL) NOPASSWD: ALL" > /tmp/sudoers_temp
        
        # Check if the syntax is valid
        visudo -c -f /tmp/sudoers_temp
        if [ $? -eq 0 ]; then
            # Append to sudoers file
            echo "$CURRENT_USER ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/$CURRENT_USER
            sudo chmod 0440 /etc/sudoers.d/$CURRENT_USER
            echo "Sudo access configured successfully."
        else
            echo "Error in sudoers syntax. Passwordless sudo not configured."
        fi
        
        # Remove temporary file
        rm /tmp/sudoers_temp
    else
        echo "Passwordless sudo already configured."
    fi
fi

if ! command -v pip &> /dev/null; then
    echo "pip is not installed. Installing pip..."
    
    # Check if Python is installed
    if command -v python3 &> /dev/null; then
        # Using Python 3
        python3 -m ensurepip --upgrade
    elif command -v python &> /dev/null; then
        # Using Python (might be Python 2 or 3)
        python -m ensurepip --upgrade
    else
        echo "Python is not installed. Please install Python first."
        exit 1
    fi
    
    echo "pip has been installed successfully."
else
    echo "pip is already installed."
fi

PIP_PATH=$(which pip)
# Define temporary directory
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

# Download the zip file
echo "Downloading package..."
curl -L "https://api.aflabox.ai/device/firmware/update" -o package.zip

# Request password from user
# echo -n "Enter password for firmware file: "
# read -s PASSWORD
# echo

# Install pyzipper if not already installed
$PIP_PATH install --break-system-packages pyzipper >/dev/null 2>&1

# Extract the zip file with password using pyzipper
echo "Extracting package..."
python3 -c "
import pyzipper
import os

with pyzipper.AESZipFile('package.zip') as zf:
    zf.pwd = 'MySecurePassword123'.encode()
    zf.extractall('.')
"

# Read and parse the JSON configuration
CONFIG_FILE="update_firmware/installation.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found!"
    exit 1
fi

# Parse JSON (using simple grep/sed approach for bash compatibility)
BASE_DIR=$(grep -o '"base_dir": *"[^"]*"' "$CONFIG_FILE" | sed 's/"base_dir": *"\(.*\)"/\1/')
SRC_CMD=$(grep -o '"cmd": *"[^"]*"' "$CONFIG_FILE" | sed 's/"cmd": *"\(.*\)"/\1/')
DESTINATION=$(grep -o '"destination": *"[^"]*"' "$CONFIG_FILE" | sed 's/"destination": *"\(.*\)"/\1/')

# Expand tilde to home directory
BASE_DIR="${BASE_DIR/#\~/$HOME}"
DESTINATION="${DESTINATION/#\~/$HOME}"

# Create base directory if it doesn't exist
echo "Setting up application directory at $BASE_DIR..."
if [ -d "$BASE_DIR" ]; then
  rm -rf "$BASE_DIR"
fi
mkdir -p "$BASE_DIR"

# Move all files to the base directory as specified in the json
echo "Moving files to destination..."
mv ./update_firmware/src/* "$BASE_DIR"/ 2>/dev/null

# Add cron jobs
echo "Setting up cron jobs..."
(crontab -l 2>/dev/null || echo "") | grep -v "$BASE_DIR" > temp_cron
echo "* * * * * /usr/bin/python $BASE_DIR/src/net.py --mode minute" >> temp_cron
echo "0 * * * * /usr/bin/python $BASE_DIR/src/net.py --mode hour" >> temp_cron
echo "0 * * * * /usr/bin/python $BASE_DIR/src/gps_query.py" >> temp_cron
echo "@reboot /usr/bin/python $BASE_DIR/src/gps_query.py" >> temp_cron
echo "@reboot /usr/bin/python $BASE_DIR/src/net.py --mode hour" >> temp_cron
crontab temp_cron
rm temp_cron


# Install GPS services
echo "Installing GPS services and dependencies..."
if command -v apt-get &>/dev/null; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y gpsd gpsd-clients python3-gps supervisor python3-spidev python3-smbus i2c-tools
elif command -v dnf &>/dev/null; then
    # Fedora/RHEL/CentOS
    sudo dnf install -y gpsd gpsd-clients gpsd-devel
elif command -v pacman &>/dev/null; then
    # Arch Linux
    sudo pacman -Sy --noconfirm gpsd
elif command -v zypper &>/dev/null; then
    # openSUSE
    sudo zypper install -y gpsd gpsd-clients
else
    echo "Could not identify package manager. Please install GPS services manually."
fi

# Enable and start gpsd service
if command -v systemctl &>/dev/null; then
    sudo systemctl enable gpsd
    sudo systemctl start gpsd
fi

# Install requirements
echo "Installing Python dependencies..."
if [ -f "$BASE_DIR/requirements.txt" ]; then
    $PIP_PATH install --break-system-packages -r "$BASE_DIR/requirements.txt"
    # Also install GPS Python module if not in requirements
    $PIP_PATH install --break-system-packages gps
else
    echo "No requirements.txt found, installing minimal dependencies."
    $PIP_PATH install --break-system-packages gps
fi

# Setup supervisor configuration
echo "Configuring supervisor service..."
SUPERVISOR_CONF="/etc/supervisor/conf.d/qbox.conf"


# Check if we can write to supervisor directory, if not use sudo
if [ -w "/etc/supervisor/conf.d/" ]; then
    cat > "$SUPERVISOR_CONF" << EOF
[program:qbox]
command=/usr/bin/python $BASE_DIR/src/main.py
directory=$BASE_DIR/src
autostart=true
autorestart=true
stderr_logfile=/var/log/qbox.err.log
stdout_logfile=/var/log/qbox.out.log
user=$(whoami)
priority=1
startretries=5
startsecs=0
process_name=%(program_name)s_%(process_num)02d
umask=022
EOF
else
    sudo bash -c "cat > $SUPERVISOR_CONF << EOF
[program:qbox]
command=/usr/bin/python $BASE_DIR/src/main.py
directory=$BASE_DIR
autostart=true
autorestart=true
stderr_logfile=/var/log/qbox.err.log
stdout_logfile=/var/log/qbox.out.log
user=$(whoami)
priority=1
startretries=5
startsecs=0
process_name=%(program_name)s_%(process_num)02d
umask=022
EOF"
fi

sudo apt install -y \
    python3-dbus \
    python3-gi \
    gir1.2-glib-2.0 \
    libgirepository1.0-dev \
    pkg-config \
    python3-dev \
    build-essential \
    libffi-dev \
    libcairo2-dev

# Reload supervisor
echo "Reloading supervisor..."
if command -v supervisorctl &>/dev/null; then
    if [ -w "/var/run/supervisor.sock" ]; then
        supervisorctl reread
        supervisorctl update
        supervisorctl start qbox:
    else
        sudo supervisorctl reread
        sudo supervisorctl update
        sudo supervisorctl start qbox:
    fi
else
    echo "Supervisor not found, please install it or start the service manually."
fi

# Setup the CLI command
echo "Setting up CLI command..."
CLI_DEST="/usr/local/bin/qbox"

if [ -w "/usr/local/bin/" ]; then
    cat > "$CLI_DEST" << EOF
#!/bin/bash
python $BASE_DIR/src/register_device.py "\$@"
EOF
    chmod +x "$CLI_DEST"
else
    sudo bash -c "cat > $CLI_DEST << EOF
#!/bin/bash
python $BASE_DIR/src/register_device.py \"\$@\"
EOF"
    sudo chmod +x "$CLI_DEST"
fi

# Clean up
echo "Cleaning up..."
cd
rm -rf "$TMP_DIR"

# Self-destruct
echo "Setup complete! This script will now self-destruct."
# rm -- "$0"

exit 0