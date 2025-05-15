import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
GEOCODING_API_URL = "http://api.openweathermap.org/geo/1.0/direct"
WEATHER_API_URL_BASE = "https://api.open-meteo.com/v1/forecast"

DEFAULT_NA = 'N/A'
DEFAULT_PRECISION = 1

CARDINAL_DIRECTIONS = ("N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                       "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW")
DEGREES_PER_CARDINAL_STEP = 360.0 / len(CARDINAL_DIRECTIONS)

LINE_SEPARATOR_SHORT = "─" * 40
LINE_SEPARATOR_MEDIUM = "─" * 60
LINE_SEPARATOR_LONG = "─" * 70

API_TIMEOUT = 10

FULL_DATETIME_FORMAT = "%A, %d %B %Y %H:%M"
TIME_ONLY_FORMAT = "%H:%M"
DAILY_DATE_FORMAT = "%a, %d %b"

def format_value_with_unit(value, unit, default_val=DEFAULT_NA, precision=None):
    if value is None or str(value) == default_val:
        return default_val
    
    if precision is not None:
        try:
            if not isinstance(value, (int, float)):
                value_num = float(value)
            else:
                value_num = value
            return f"{value_num:.{precision}f}{unit}"
        except (ValueError, TypeError):
            return f"{value}{unit}"
    return f"{value}{unit}"

def _handle_iso_string_for_datetime(iso_str):
    if isinstance(iso_str, str) and iso_str.endswith('Z'):
        return iso_str[:-1] + '+00:00'
    return iso_str

def format_timestamp(iso_timestamp, fmt=FULL_DATETIME_FORMAT, default_val=DEFAULT_NA):
    if not iso_timestamp or iso_timestamp == default_val:
        return default_val
    try:
        processed_iso_str = _handle_iso_string_for_datetime(iso_timestamp)
        dt_obj = datetime.fromisoformat(processed_iso_str)
        return dt_obj.strftime(fmt)
    except (ValueError, TypeError):
        return str(iso_timestamp)

def format_time_from_iso(iso_datetime_str, fmt=TIME_ONLY_FORMAT, default_val=DEFAULT_NA):
    return format_timestamp(iso_datetime_str, fmt, default_val)

def format_daily_date(iso_date_str, fmt=DAILY_DATE_FORMAT, default_val=DEFAULT_NA):
    if not iso_date_str or iso_date_str == default_val:
        return default_val
    try:
        dt_obj = datetime.fromisoformat(iso_date_str) 
        return dt_obj.strftime(fmt)
    except (ValueError, TypeError):
        return str(iso_date_str)

def degrees_to_cardinal(d, default_val=DEFAULT_NA):
    if d is None or str(d) == default_val:
        return default_val
    try:
        d_float = float(d)
        d_float = d_float % 360 #
        ix = round(d_float / DEGREES_PER_CARDINAL_STEP) % len(CARDINAL_DIRECTIONS)
        return CARDINAL_DIRECTIONS[ix]
    except (ValueError, TypeError):
        return str(d)

def get_coordinates(city_name, api_key):
    params = {"q": city_name, "limit": 1, "appid": api_key}
    try:
        response = requests.get(GEOCODING_API_URL, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        data = response.json()

        if not data:
            print(f"[ERROR] | City '{city_name}' not found or no data returned by geocoding API.")
            return None, city_name
        
        location_data = data[0]
        latitude = location_data.get('lat')
        longitude = location_data.get('lon')

        if latitude is None or longitude is None:
            print(f"[ERROR] | Invalid response from geocoding API for '{city_name}' (missing lat/lon).")
            return None, city_name

        api_city_name = location_data.get('name', city_name)
        country = location_data.get('country')
        state = location_data.get('state')
        
        name_parts = [part for part in [api_city_name, state, country] if part]
        resolved_display_name = ", ".join(name_parts)

        return (float(latitude), float(longitude)), resolved_display_name

    except requests.exceptions.Timeout:
        print(f"[ERROR] | Geocoding request for '{city_name}' timed out after {API_TIMEOUT} seconds.")
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] | HTTP Error in geocoding for '{city_name}': {e.response.status_code} - {e.response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] | Request Exception in geocoding for '{city_name}': {e}")
    except (IndexError, KeyError) as e:
        print(f"[ERROR] | Unexpected API response format from geocoding for '{city_name}': {e}")
    except ValueError as e:
        print(f"[ERROR] | Error processing geocoding data for '{city_name}': {e}")
    except Exception as e:
        print(f"[ERROR] | An unexpected error occurred during geocoding for '{city_name}': {e}")
    return None, city_name

def get_weather_data(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset,uv_index_max,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant",
        "hourly": "temperature_2m,precipitation_probability,rain,showers,snowfall,precipitation,visibility,evapotranspiration,wind_speed_10m,wind_direction_10m,wind_gusts_10m,relative_humidity_2m,cloud_cover,uv_index,is_day,sunshine_duration",
        "models": "best_match",
        "current": "temperature_2m,precipitation,rain,showers,snowfall,wind_speed_10m,wind_direction_10m,wind_gusts_10m,cloud_cover,relative_humidity_2m,is_day",
        "temperature_unit": "celsius",
        "windspeed_unit": "kmh",
        "timezone": "auto"
    }
    try:
        response = requests.get(WEATHER_API_URL_BASE, params=params, timeout=API_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print(f"[ERROR] | Weather data request timed out after {API_TIMEOUT} seconds.")
    except requests.exceptions.HTTPError as e:
        print(f"[ERROR] | HTTP Error fetching weather data: {e.response.status_code} - {e.response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] | Request Exception fetching weather data: {e}")
    except ValueError as e:
        print(f"[ERROR] | Error decoding JSON response from weather API: {e}")
    except Exception as e:
        print(f"[ERROR] | An unexpected error occurred fetching weather data: {e}")
    return None

def _display_precipitation_details(data_source, units, overall_label_width, indent_string):
    precip_items = {
        'rain': ('Rain:', units.get('rain', 'mm')),
        'showers': ('Showers:', units.get('showers', 'mm')),
        'snowfall': ('Snowfall:', units.get('snowfall', 'cm'))
    }

    for key, (label, unit) in precip_items.items():
        value = data_source.get(key)
        if value is not None and isinstance(value, (int, float)) and value > 0:
            effective_label_width = overall_label_width - len(indent_string)
            print(f"{indent_string}{label:<{effective_label_width}} {format_value_with_unit(value, unit, precision=DEFAULT_PRECISION)}")

def display_current_weather(current_data, units, city_display_name):
    print("\n")
    title = f" Current Weather in {city_display_name} "
    print(title.center(len(LINE_SEPARATOR_MEDIUM), "━"))
    print("\n")
    if not current_data:
        print("No current weather data available.".center(len(LINE_SEPARATOR_MEDIUM)))
        print(LINE_SEPARATOR_MEDIUM)
        return

    label_width = 23

    print(f"{'Time:':<{label_width}} {format_timestamp(current_data.get('time'))}")
    
    temp_val = current_data.get('temperature_2m')
    temp_unit = units.get('temperature_2m', '°C')
    print(f"{'Temperature:':<{label_width}} {format_value_with_unit(temp_val, temp_unit, precision=DEFAULT_PRECISION)}")

    humidity_val = current_data.get('relative_humidity_2m')
    humidity_unit = units.get('relative_humidity_2m', '%')
    print(f"{'Relative Humidity:':<{label_width}} {format_value_with_unit(humidity_val, humidity_unit)}")
    
    precip_val = current_data.get('precipitation')
    precip_unit = units.get('precipitation', 'mm')
    print(f"{'Total Precipitation:':<{label_width}} {format_value_with_unit(precip_val, precip_unit, precision=DEFAULT_PRECISION, default_val=f'0.0{precip_unit}')}")
    
    if isinstance(precip_val, (int, float)) and precip_val > 0:
        _display_precipitation_details(current_data, units, label_width, indent_string="  ")

    wind_speed_val = current_data.get('wind_speed_10m')
    wind_speed_unit = units.get('wind_speed_10m', 'km/h')
    wind_dir_deg = current_data.get('wind_direction_10m')
    wind_dir_unit = units.get('wind_direction_10m', '°')
    wind_gusts_val = current_data.get('wind_gusts_10m')
    wind_gusts_unit = units.get('wind_gusts_10m', 'km/h')

    print(f"{'Wind Speed:':<{label_width}} {format_value_with_unit(wind_speed_val, wind_speed_unit, precision=DEFAULT_PRECISION)}")
    print(f"{'Wind Direction:':<{label_width}} {degrees_to_cardinal(wind_dir_deg)} ({format_value_with_unit(wind_dir_deg, wind_dir_unit, precision=0)})")
    if wind_gusts_val is not None and isinstance(wind_gusts_val, (int,float)) and wind_gusts_val > 0:
        print(f"{'Wind Gusts:':<{label_width}} {format_value_with_unit(wind_gusts_val, wind_gusts_unit, precision=DEFAULT_PRECISION)}")

    cloud_val = current_data.get('cloud_cover')
    cloud_unit = units.get('cloud_cover', '%')
    print(f"{'Cloud Cover:':<{label_width}} {format_value_with_unit(cloud_val, cloud_unit)}")
    
    is_day_val = current_data.get('is_day')
    is_day_str = 'Day ☀️' if is_day_val == 1 else 'Night 🌙' if is_day_val == 0 else DEFAULT_NA
    print(f"{'Day/Night:':<{label_width}} {is_day_str}")

def display_daily_weather(daily_data, units):
    print("\n")
    print(" Daily Forecast ".center(len(LINE_SEPARATOR_MEDIUM), "━"))
    print("\n")
    if not daily_data or not daily_data.get('time'):
        print("No daily forecast data available.".center(len(LINE_SEPARATOR_MEDIUM)))
        print(LINE_SEPARATOR_MEDIUM)
        return

    label_width = 25
    indent = "  "
    times = daily_data.get('time', [])

    for i in range(len(times)):
        try:
            date_str = format_daily_date(times[i])
            print(f"📅 {date_str}:")

            def get_daily_val(key): return daily_data.get(key, [])[i] if daily_data.get(key) and i < len(daily_data.get(key, [])) else None

            print(f"{indent}{'Max Temp:':<{label_width-len(indent)}} {format_value_with_unit(get_daily_val('temperature_2m_max'), units.get('temperature_2m_max', '°C'), precision=DEFAULT_PRECISION)}")
            print(f"{indent}{'Min Temp:':<{label_width-len(indent)}} {format_value_with_unit(get_daily_val('temperature_2m_min'), units.get('temperature_2m_min', '°C'), precision=DEFAULT_PRECISION)}")
            print(f"{indent}{'Sunrise:':<{label_width-len(indent)}} {format_time_from_iso(get_daily_val('sunrise'))} 🌅")
            print(f"{indent}{'Sunset:':<{label_width-len(indent)}} {format_time_from_iso(get_daily_val('sunset'))} 🌇")
            print(f"{indent}{'Max UV Index:':<{label_width-len(indent)}} {format_value_with_unit(get_daily_val('uv_index_max'), units.get('uv_index_max', ''), precision=DEFAULT_PRECISION)}")
            print(f"{indent}{'Max Wind Speed:':<{label_width-len(indent)}} {format_value_with_unit(get_daily_val('wind_speed_10m_max'), units.get('wind_speed_10m_max', 'km/h'), precision=DEFAULT_PRECISION)}")
            
            wind_gusts = get_daily_val('wind_gusts_10m_max')
            if wind_gusts is not None and isinstance(wind_gusts, (int,float)) and wind_gusts > 0:
                 print(f"{indent}{'Max Wind Gusts:':<{label_width-len(indent)}} {format_value_with_unit(wind_gusts, units.get('wind_gusts_10m_max', 'km/h'), precision=DEFAULT_PRECISION)}")

            wind_dir_deg = get_daily_val('wind_direction_10m_dominant')
            print(f"{indent}{'Dominant Wind Dir:':<{label_width-len(indent)}} {degrees_to_cardinal(wind_dir_deg)} ({format_value_with_unit(wind_dir_deg, units.get('wind_direction_10m_dominant', '°'), precision=0)})")
        
        except (IndexError, KeyError) as e:
            print(f"{indent}[WARN] | Incomplete data for day index {i}: {e}")
        except Exception as e:
            print(f"{indent}[WARN] | Error processing data for day index {i}: {e}")
        
        if i < len(times) - 1:
            print(LINE_SEPARATOR_SHORT.center(len(LINE_SEPARATOR_MEDIUM)))

def display_hourly_weather(hourly_data, units, current_time_iso_str):
    print("\n")
    print(" Hourly Forecast (Rest of the day) ".center(len(LINE_SEPARATOR_LONG), "━"))
    print("\n")
    if not hourly_data or not hourly_data.get('time'):
        print("No hourly forecast data available.".center(len(LINE_SEPARATOR_LONG)))
        print(LINE_SEPARATOR_LONG)
        return

    current_dt_obj, end_of_today_dt = None, None
    try:
        if not current_time_iso_str or current_time_iso_str == DEFAULT_NA:
            raise ValueError("Invalid current time provided for hourly forecast filtering.")
        
        processed_current_iso = _handle_iso_string_for_datetime(current_time_iso_str)
        current_dt_obj = datetime.fromisoformat(processed_current_iso)
        
        end_of_today_dt = datetime(current_dt_obj.year, current_dt_obj.month, current_dt_obj.day, tzinfo=current_dt_obj.tzinfo) + timedelta(days=1)
    except (ValueError, TypeError) as e:
        print(f"[WARNING] | Could not parse current time '{current_time_iso_str}' for hourly filtering: {e}. Showing limited forecast.")

    label_width = 28
    indent = "  "
    sub_item_indent = indent + "  "

    hourly_times = hourly_data.get('time', [])
    displayed_count = 0
    max_display_fallback = 8

    for i in range(len(hourly_times)):
        try:
            hourly_time_iso = hourly_times[i]
            processed_hourly_iso = _handle_iso_string_for_datetime(hourly_time_iso)
            hourly_dt = datetime.fromisoformat(processed_hourly_iso)

            if current_dt_obj and end_of_today_dt:
                if not (current_dt_obj <= hourly_dt < end_of_today_dt):
                    if hourly_dt >= end_of_today_dt and displayed_count > 0: break
                    if hourly_dt < current_dt_obj : continue
            elif displayed_count >= max_display_fallback:
                break
            
            print(f"🕒 {format_time_from_iso(hourly_time_iso)}:")
            displayed_count += 1

            def get_hourly_val(key, idx):
                series = hourly_data.get(key)
                return series[idx] if series and idx < len(series) else None

            print(f"{indent}{'Temperature:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('temperature_2m',i), units.get('temperature_2m', '°C'), precision=DEFAULT_PRECISION)}")
            print(f"{indent}{'Precip. Probability:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('precipitation_probability',i), units.get('precipitation_probability', '%'))}")

            total_precip = get_hourly_val('precipitation',i)
            precip_unit_hr = units.get('precipitation', 'mm')
            print(f"{indent}{'Total Precipitation:':<{label_width-len(indent)}} {format_value_with_unit(total_precip, precip_unit_hr, precision=DEFAULT_PRECISION, default_val=f'0.0{precip_unit_hr}')}")
            if isinstance(total_precip, (int, float)) and total_precip > 0:
                current_hour_precip_data = {
                    'rain': get_hourly_val('rain', i),
                    'showers': get_hourly_val('showers', i),
                    'snowfall': get_hourly_val('snowfall', i)
                }
                _display_precipitation_details(current_hour_precip_data, units, label_width, indent_string=sub_item_indent)

            visibility_m = get_hourly_val('visibility',i)
            visibility_str = DEFAULT_NA
            if visibility_m is not None and visibility_m != DEFAULT_NA:
                try:
                    val_float = float(visibility_m)
                    km = val_float / 1000.0
                    if km >= 10.0: visibility_str = f"{km:.0f} km"
                    elif 0 < km < 0.1: visibility_str = "<0.1 km"
                    elif km <= 0.0: visibility_str = "0.0 km (Low)"
                    else: visibility_str = f"{km:.1f} km"
                except (ValueError, TypeError):
                    visibility_str = f"{visibility_m} {units.get('visibility', 'm')}"
            print(f"{indent}{'Visibility:':<{label_width-len(indent)}} {visibility_str}")

            print(f"{indent}{'Wind Speed:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('wind_speed_10m',i), units.get('wind_speed_10m', 'km/h'), precision=DEFAULT_PRECISION)}")
            wind_dir_deg_hr = get_hourly_val('wind_direction_10m',i)
            print(f"{indent}{'Wind Direction:':<{label_width-len(indent)}} {degrees_to_cardinal(wind_dir_deg_hr)} ({format_value_with_unit(wind_dir_deg_hr, units.get('wind_direction_10m', '°'), precision=0)})")
            
            wind_gusts_hr = get_hourly_val('wind_gusts_10m',i)
            if wind_gusts_hr is not None and isinstance(wind_gusts_hr, (int,float)) and wind_gusts_hr > 0:
                print(f"{indent}{'Wind Gusts:':<{label_width-len(indent)}} {format_value_with_unit(wind_gusts_hr, units.get('wind_gusts_10m', 'km/h'), precision=DEFAULT_PRECISION)}")

            print(f"{indent}{'Relative Humidity:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('relative_humidity_2m',i), units.get('relative_humidity_2m', '%'))}")
            print(f"{indent}{'Cloud Cover:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('cloud_cover',i), units.get('cloud_cover', '%'))}")
            print(f"{indent}{'UV Index:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('uv_index',i), units.get('uv_index', ''), precision=DEFAULT_PRECISION)}")

            is_day_hr = get_hourly_val('is_day', i)
            print(f"{indent}{'Day/Night:':<{label_width-len(indent)}} {'Day ☀️' if is_day_hr == 1 else 'Night 🌙' if is_day_hr == 0 else DEFAULT_NA}")

            sunshine_sec = get_hourly_val('sunshine_duration',i)
            if sunshine_sec is not None and isinstance(sunshine_sec, (int,float)) and sunshine_sec > 0 :
                print(f"{indent}{'Sunshine (last hr):':<{label_width-len(indent)}} {float(sunshine_sec) / 3600.0:.2f} hours")
            
            is_last_iteration = (i == len(hourly_times) - 1)
            will_break_next_fallback = (not (current_dt_obj and end_of_today_dt) and displayed_count >= max_display_fallback -1)
            if not is_last_iteration and not will_break_next_fallback :
                 print(LINE_SEPARATOR_SHORT.center(len(LINE_SEPARATOR_LONG)))

        except (IndexError, KeyError) as e:
            print(f"{indent}[WARN] | Incomplete data for hourly index {i}: {e}")
        except (ValueError, TypeError) as e:
            print(f"{indent}[WARN] | Error processing data for hourly index {i}: {e}")
        except Exception as e:
            print(f"{indent}[WARN] | Unexpected error processing hourly index {i}: {e}")

    if displayed_count == 0:
        print("No further hourly data available for today.".center(len(LINE_SEPARATOR_LONG)))

def display_weather(weather_data, city_display_name):
    if not weather_data:
        print("Weather data couldn't be retrieved or is incomplete.")
        return

    current = weather_data.get('current', {})
    current_units = weather_data.get('current_units', {})
    display_current_weather(current, current_units, city_display_name)

    daily = weather_data.get('daily', {})
    daily_units = weather_data.get('daily_units', {})
    display_daily_weather(daily, daily_units)

    hourly = weather_data.get('hourly', {})
    hourly_units = weather_data.get('hourly_units', {})
    current_time_iso = current.get('time')
    display_hourly_weather(hourly, hourly_units, current_time_iso)

if __name__ == "__main__":
    OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')
    city_input = input("Enter city name: ").strip()
    if not city_input:
        print("[ERROR] | City name cannot be empty.")
    else:
        coordinates_tuple, resolved_city_name = get_coordinates(city_input, OPENWEATHERMAP_API_KEY)
        
        if coordinates_tuple:
            latitude, longitude = coordinates_tuple
            print(f"\nFetching weather data for {resolved_city_name} (Lat: {latitude:.2f}, Lon: {longitude:.2f})...")
            
            weather_data = get_weather_data(latitude, longitude)
            if weather_data:
                display_weather(weather_data, resolved_city_name)
            else:
                print("Failed to retrieve detailed weather data.")
        else:
            print("Failed to obtain coordinates. Cannot fetch weather data.")