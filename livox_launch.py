import requests
import os
import time
import yaml
from datetime import datetime, timedelta
import subprocess

# Constants
NEAREST_COOPS = "9410230"  # Station ID for the nearest tide gauge
DEFAULT_SAMP_TIME = 300  # Default sampling time in seconds (5 minutes)

def parse_datetime(datetime_str):
    """Convert a datetime string to a datetime object."""
    return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")

def find_closest_high_tides(predictions):
    """Find the closest past and future high tide dates from a list of predictions."""
    now = datetime.now()
    closest_past_high_tide = None
    closest_future_high_tide = None

    for prediction in predictions:
        pred_datetime = parse_datetime(prediction['t'])
        if prediction['type'] == 'H':
            if pred_datetime <= now:
                if closest_past_high_tide is None or pred_datetime > closest_past_high_tide:
                    closest_past_high_tide = pred_datetime
            else:
                if closest_future_high_tide is None or pred_datetime < closest_future_high_tide:
                    closest_future_high_tide = pred_datetime

    return closest_past_high_tide, closest_future_high_tide

def round_to_nearest_hour(dt):
    """Round a datetime object to the nearest hour."""
    if dt.minute >= 30:
        dt += timedelta(hours=1)
    return dt.replace(minute=0, second=0, microsecond=0)

def get_epoch_mstime():
    """Get and return the current epoch time in ms"""
    return int(time.time() * 1000)

def get_tide_predictions(coops, now_str):
    """Fetch tide predictions from NOAA API for the given station and date string.
    Returns None if the API call fails."""
    try:
        response = requests.get(
            f'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?'
            f'&product=predictions&datum=stnd&interval=hilo&format=json'
            f'&units=metric&time_zone=lst_ldt&station={coops}&begin_date={now_str}&range=48'
        )
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json().get('predictions', [])
    except (requests.RequestException, ValueError) as e:
        print(f"Error fetching tide data: {e}")
        print("Falling back to default sampling time")
        return None

def load_config(file_path):
    """
    Loads configuration from a YAML file.

    Parameters:
    - file_path (str): The path to the YAML configuration file.

    Returns:
    - dict: The loaded configuration as a dictionary.
    """
    try:
        with open(file_path, "r") as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print(f"File {file_path} not found.")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        return None


def main():
    config = load_config("config.yaml")
    now_str = (datetime.now()-timedelta(days=1)).strftime('%Y%m%d')

    if config is not None: 
        print("Config loaded")
        fqdn_ip = config['fqdn_ip']
        default_samp_time = config.get('sampling', {}).get('time', DEFAULT_SAMP_TIME)
    else:
        print("Failed to load config; using defaults")
        default_samp_time = DEFAULT_SAMP_TIME
        coops = NEAREST_COOPS
    
    predictions = get_tide_predictions(coops, now_str)
    
    if predictions is None:
        # If we couldn't get tide data, use default sampling time
        samp_time = default_samp_time
    else:
        closest_past_high_tide, closest_future_high_tide = find_closest_high_tides(predictions)
        
        print(f"Closest past high tide: {closest_past_high_tide}")
        print(f"Closest future high tide: {closest_future_high_tide}")

        now = datetime.now()
        closest_high_tide = None

        if closest_past_high_tide and closest_future_high_tide:
            if (now - closest_past_high_tide) <= (closest_future_high_tide - now):
                closest_high_tide = closest_past_high_tide
            else:
                closest_high_tide = closest_future_high_tide
        elif closest_past_high_tide:
            closest_high_tide = closest_past_high_tide
        elif closest_future_high_tide:
            closest_high_tide = closest_future_high_tide

        if closest_high_tide:
            rounded_high_tide = round_to_nearest_hour(closest_high_tide)
            if rounded_high_tide - timedelta(hours=2) <= now <= rounded_high_tide + timedelta(hours=3):
                samp_time = 25 * 60  # 25 minutes in seconds
            else:
                samp_time = default_samp_time
        else:
            samp_time = default_samp_time

    print(f"Sampling time set to: {samp_time} seconds")
    
    # Check current minute
    current_minute = datetime.now().minute
    
    # If we're on :30 and not in high tide situation, skip
    if current_minute == 30 and samp_time != 25 * 60:
        print("Running on :30 but not in high tide situation, skipping launch")
        return
    
    # Run livox_logger with appropriate config file
    config_file = f"conf/config-{samp_time}.yaml"
    try:
        subprocess.run(["/home/cpg/Dev/livox_logger/bin/livox_logger", config_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running livox_logger: {e}")
    except FileNotFoundError:
        print("livox_logger program not found")

if __name__ == "__main__":
    main()
