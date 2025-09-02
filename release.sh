#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FOLDER="$SCRIPT_DIR/config"
CONFIG_FILE="$CONFIG_FOLDER/updater.ini"
SCRIPT_NAME=$(basename "$0")
RELEASE_FOLDER="/tmp/releases"
INSTALLATION_FILE="$SCRIPT_DIR/installation.json"

echo "$CONFIG_FILE"
# Helper to read ini values
get_config_value() {
    section=$1
    key=$2
    awk -F '=' -v section="$section" -v key="$key" '
        /^\[.*\]$/ {current_section=$0}
        $1 ~ key && current_section == "["section"]" {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}
    ' "$CONFIG_FILE"
}

# Helper to write ini values
set_config_value() {
    section="$1"
    key="$2"
    value="$3"
    # Use the global CONFIG_FILE variable
    
    # Check if config file exists, create if it doesn't
    if [ ! -f "$CONFIG_FILE" ]; then
        touch "$CONFIG_FILE"
    fi
    
    # Check if section exists
    if ! grep -q "^\[$section\]" "$CONFIG_FILE"; then
        # Section doesn't exist, append it along with the key-value pair
        echo "" >> "$CONFIG_FILE"  # Add a newline for formatting
        echo "[$section]" >> "$CONFIG_FILE"
        echo "$key=$value" >> "$CONFIG_FILE"
    else
        # Section exists, check if key exists in that section
        # This gets complicated because we need to find the key in the specific section

        # Use awk to handle the section-specific key modification
        awk -v section="$section" -v key="$key" -v value="$value" '
            BEGIN { in_section=0; key_found=0; }
            
            # Track when we enter or exit the target section
            /^\[/ { 
                if (in_section && !key_found) {
                    # We are leaving the section and the key was not found, add it
                    print key "=" value
                }
                in_section = ($0 == "["section"]")
                print
                next
            }
            
            # Process key=value lines in the target section
            in_section && $0 ~ "^"key"=" { 
                print key "=" value
                key_found = 1
                next
            }
            
            # Print other lines unchanged
            { print }
            
            # At end of file, if we never found the key in its section, add it
            END {
                if (in_section && !key_found) {
                    print key "=" value
                }
            }
        ' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    fi
}


# Ask for release type
echo "Select release type: "
echo "1. Major"
echo "2. Minor"
echo "3. Patch"
read -r release_type

# Read current version
current_version=$(get_config_value "FIRMWARE_MANAGEMENT" "current_version")
IFS='.' read -r major minor patch <<< "$current_version"

# Increment version
case $release_type in
    1) ((major++)); minor=0; patch=0 ;;
    2) ((minor++)); patch=0 ;;
    3) ((patch++)) ;;
    *) echo "Invalid choice"; exit 1 ;;
esac

new_version="${major}.${minor}.${patch}"
echo "New version: $new_version"



# Create releases folder if needed
mkdir -p "$RELEASE_FOLDER"

# Final zip name
zip_file="${RELEASE_FOLDER}/qbox_${new_version}.zip"

# Find script directory
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Prepare list of files to include (exclude this script and releases folder itself)
# echo "Preparing files for zip (excluding $SCRIPT_NAME and $RELEASE_FOLDER)..."
# cd "$script_dir"
# zip -rq "$zip_file" . -x "./$SCRIPT_NAME" -x "./$RELEASE_FOLDER/*" x "./$CONFIG_FOLDER/*" 

echo "Preparing files for zip into 'test' folder (excluding $SCRIPT_NAME, $RELEASE_FOLDER, and $CONFIG_FOLDER)..."

# 1. Set up clean folder
new_update_dir="/tmp/update_firmware"
rm -rf "$new_update_dir"
mkdir -p "$new_update_dir"
mkdir -p "$new_update_dir/src"
echo "target file $new_update_dir"
# 2. Copy everything into test, excluding unwanted items
shopt -s dotglob  # include hidden files like .env or .gitignore


rsync -a \
--exclude="__pycache__" \
--exclude=".pytest_cache" \
--exclude="$(basename "$0")" \
--exclude="installation.json" \
--exclude=".DS_Store" \
--exclude=".git" \
--exclude="screenshots" \
--exclude='__pycache__' \
--exclude='*.pyc' \
--exclude="$new_update_dir" \
"$SCRIPT_DIR/" "$new_update_dir/src/"
cp "$INSTALLATION_FILE" "$new_update_dir/"


shopt -u dotglob

# 3. Zip everything inside 'update'
cd "$new_update_dir/.."
zip -rq "$zip_file" "$(basename "$new_update_dir")"

# Optional (debugging): Confirm contents of zip
echo "Contents of $zip_file:"
unzip -l "$zip_file"



# 4. Cleanup update folder if needed
rm -rf "$new_update_dir"

echo "Prepared and zipped clean 'firmware source' folder into $zip_file"





# Read password (fwd) from config.ini
fwd=$(get_config_value "FIRMWARE_MANAGEMENT" "zip_password")

# Post to /device/firmware/upload
post_url="https://api.aflabox.ai/device/firmware/upload"
echo "Deploying new release $post_url..."

response=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST "$post_url" \
     -F "file=@$zip_file" \
     -F "fwd=$fwd")

BODY=$(echo "$response" | sed -n '1,/HTTP_STATUS:/p' | sed '$d')
STATUS=$(echo "$response" | sed -n 's/.*HTTP_STATUS://p')
echo "$response"
if [ "$STATUS" -ne 200 ]; then
    echo "❌ Error: Unable to upload release"
    echo "Server response: $BODY"
    exit 1
fi

set_config_value "FIRMWARE_MANAGEMENT" "current_version" "$new_version"
echo "✅ Qbox $new_version deployed"

echo "Server response: $response"

# Cleanup: (Optional - you can skip deleting if you want to keep history)
rm "$zip_file"

echo "Release process complete!"
