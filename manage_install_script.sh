#!/bin/bash

UPLOAD_URL="https://0x0.st"
TOKEN_FILE="$HOME/.qbox_data/upload_data.json"
file_path="$(cd "$(dirname "$0")" && pwd)/installer_global.sh"

upload_file() {
    if [ ! -f "$file_path" ]; then
        echo "Error: File $file_path not found."
        return 1
    fi
    echo "curl -s -D - -F'file=@$file_path' $UPLOAD_URL"
    response=$(curl -s -D - -F "file=@$file_path" "$UPLOAD_URL")
    file_url=$(echo "$response" | grep -oE 'https?://[^ ]+')
    token=$(echo "$response" | grep -Fi 'X-Token:' | awk '{print $2}' | tr -d '\r')
    
    if [[ -n "$file_url" && -n "$token" ]]; then
        timestamp=$(date +%s)
        echo "Upload successful: $file_url"
        save_details "$file_url" "$token" "$file_path" "$timestamp"
    else
        echo "Upload failed. Please check the file and try again."
    fi
}

save_details() {
    local file_url="$1"
    local token="$2"
    local file_path="$3"
    local timestamp="$4"
    
    mkdir -p "$(dirname "$TOKEN_FILE")"
    if [ ! -f "$TOKEN_FILE" ]; then
        echo "[]" > "$TOKEN_FILE"
    fi
    
    jq --arg file "$file_path" --arg url "$file_url" --arg token "$token" --arg time "$timestamp" \
       '. += [{"file": $file, "url": $url, "token": $token, "time": $time}]' "$TOKEN_FILE" > temp.json && mv temp.json "$TOKEN_FILE"
    echo "Details saved in $TOKEN_FILE"
}

reupload_file() {
    existing_url=$(jq -r --arg file "$file_path" '.[] | select(.file==$file) | .url' "$TOKEN_FILE")
    
    if [[ -n "$existing_url" ]]; then
        echo "File already uploaded: $existing_url"
        read -p "Do you want to reupload? (y/n): " choice
        if [[ "$choice" == "y" ]]; then
            upload_file "$file_path"
        fi
    else
        echo "File not found in records. Uploading..."
        upload_file "$file_path"
    fi
}

delete_file() {
    existing_url=$(jq -r --arg file "$file_path" '.[] | select(.file==$file) | .url' "$TOKEN_FILE")
    existing_token=$(jq -r --arg file "$file_path" '.[] | select(.file==$file) | .token' "$TOKEN_FILE")
    
    if [[ -n "$existing_url" && -n "$existing_token" ]]; then
        echo "Deleting $existing_url..."
        curl -s -X POST -F "token=$existing_token" -F "delete=" "$existing_url"
        jq --arg file "$file_path" 'del(.[] | select(.file==$file))' "$TOKEN_FILE" > temp.json && mv temp.json "$TOKEN_FILE"
        echo "File deleted and removed from records."
    else
        echo "File not found in records. Nothing to delete."
    fi
}

show_latest_url() {
    latest_entry=$(jq -r 'max_by(.time) | .url' "$TOKEN_FILE")
    if [[ -n "$latest_entry" ]]; then
        echo "Latest uploaded file URL: $latest_entry"
    else
        echo "No uploads found."
    fi
}

menu() {
    echo "1. Upload a file"
    echo "2. Reupload a file"
    echo "3. Delete a file"
    echo "4. Show latest uploaded URL"
    echo "5. Exit"
    read -p "Choose an option: " option
    
    case $option in
        1)
            upload_file "$file_path"
            ;;
        2)
            reupload_file "$file_path"
            ;;
        3)
            delete_file "$file_path"
            ;;
        4)
            show_latest_url
            ;;
        5)
            exit 0
            ;;
        *)
            echo "Invalid option. Try again."
            menu
            ;;
    esac
}

menu
