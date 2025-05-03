#!/bin/bash

# Function to convert date to epoch time
convert_to_epoch() {
    local date_str=$1
    local time_str=$2
    
    # Extract year, month, day, hour, minute, second
    local year=${date_str:0:4}
    local month=${date_str:4:2}
    local day=${date_str:6:2}
    local hour=${time_str:0:2}
    local minute=${time_str:2:2}
    local second=${time_str:4:2}
    
    # Check if we're on macOS or Linux
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS version
        date -j -f "%Y-%m-%d %H:%M:%S" "${year}-${month}-${day} ${hour}:${minute}:${second}" "+%s"
    else
        # Linux version
        date -d "${year}-${month}-${day} ${hour}:${minute}:${second}" "+%s"
    fi
}

# Process all .laz files in the current directory
for file in do-lidar_*_UTC.laz; do
    if [[ -f "$file" ]]; then
        # Extract the date and time parts
        if [[ $file =~ do-lidar_([0-9]{8})_([0-9]{6})_UTC\.laz ]]; then
            date_part="${BASH_REMATCH[1]}"
            time_part="${BASH_REMATCH[2]}"
            
            # Convert to epoch time
            epoch_time=$(convert_to_epoch "$date_part" "$time_part")
            
            # Create new filename
            new_name="do-lidar_${epoch_time}.laz"
            
            # Rename the file
            mv "$file" "$new_name"
            echo "Renamed: $file -> $new_name"
        fi
    fi
done
