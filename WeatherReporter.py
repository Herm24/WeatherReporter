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
LINE_SEPARATOR_LONG = "─" * 80

API_TIMEOUT = 10

FULL_DATETIME_FORMAT = "%A, %d %B %Y %H:%M"
TIME_ONLY_FORMAT = "%H:%M"
DAILY_DATE_FORMAT = "%a, %d %b"

WMO_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Drizzle: Light",
    53: "Drizzle: Moderate",
    55: "Drizzle: Dense",
    56: "Freezing Drizzle: Light",
    57: "Freezing Drizzle: Dense",
    61: "Rain: Slight",
    63: "Rain: Moderate",
    65: "Rain: Heavy",
    66: "Freezing Rain: Light",
    67: "Freezing Rain: Heavy",
    71: "Snow fall: Slight",
    73: "Snow fall: Moderate",
    75: "Snow fall: Heavy",
    77: "Snow grains",
    80: "Rain showers: Slight",
    81: "Rain showers: Moderate",
    82: "Rain showers: Violent",
    85: "Snow showers: Slight",
    86: "Snow showers: Heavy",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

def get_weather_description(code, default_val=DEFAULT_NA):
    if code is None:
        return default_val
    try:
        return WMO_WEATHER_CODES.get(int(code), f"Code {code}")
    except (ValueError, TypeError):
        return f"Code {code} (Unknown)"


def format_value_with_unit(value, unit, default_val=DEFAULT_NA, precision=None):
    if value is None or str(value) == default_val:
        return default_val
    
    if isinstance(default_val, str) and default_val.startswith("0.0") and \
       (isinstance(value, (int, float)) and value == 0.0):
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
        dt_obj = datetime.strptime(iso_date_str, "%Y-%m-%d")
        return dt_obj.strftime(fmt)
    except (ValueError, TypeError):
        return str(iso_date_str)

def degrees_to_cardinal(d, default_val=DEFAULT_NA):
    if d is None or str(d) == default_val:
        return default_val
    try:
        d_float = float(d)
        d_float = d_float % 360 
        ix = round(d_float / DEGREES_PER_CARDINAL_STEP) % len(CARDINAL_DIRECTIONS)
        return CARDINAL_DIRECTIONS[ix]
    except (ValueError, TypeError):
        return str(d)

def format_duration(total_seconds, default_val=DEFAULT_NA):
    if total_seconds is None or str(total_seconds) == default_val:
        return default_val
    try:
        val = float(total_seconds)
        if val < 0: val = 0 
        
        hours = int(val / 3600)
        minutes = int((val % 3600) / 60)
        
        if hours == 0 and minutes == 0 and val > 0:
            return f"{val:.0f} sec"
        
        return f"{hours}h {minutes:02d}m"
    except (ValueError, TypeError):
        return str(total_seconds)

def format_visibility_km(visibility_m, unit_str='m', default_val=DEFAULT_NA):
    if visibility_m is None or str(visibility_m) == default_val:
        return default_val
    try:
        val_float = float(visibility_m)
        if val_float < 0: return default_val 
        
        km = val_float / 1000.0
        if km >= 10.0: return f"{km:.0f} km"
        if km <= 0 and val_float > 0: return "<0.1 km"
        if km <= 0: return "0.0 km (Low)" 
        if 0 < km < 0.1: return "<0.1 km"
        return f"{km:.1f} km"
    except (ValueError, TypeError):
        return f"{visibility_m} {unit_str}"


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
        "daily": "precipitation_hours,precipitation_sum,precipitation_probability_max,weather_code,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant,sunrise,sunset,daylight_duration,sunshine_duration,uv_index_max,rain_sum,showers_sum,snowfall_sum,cape_min,cape_max,dew_point_2m_mean,wet_bulb_temperature_2m_mean,wet_bulb_temperature_2m_min,wet_bulb_temperature_2m_max,dew_point_2m_min,dew_point_2m_max,cloud_cover_min,cloud_cover_max,precipitation_probability_mean,snowfall_water_equivalent_sum,updraft_max,winddirection_10m_dominant,wind_gusts_10m_min,wind_speed_10m_min,visibility_min,visibility_max,surface_pressure_max,surface_pressure_min,pressure_msl_max,pressure_msl_min,relative_humidity_2m_max,relative_humidity_2m_min,precipitation_probability_min,pressure_msl_mean,surface_pressure_mean,visibility_mean,wind_gusts_10m_mean,wind_speed_10m_mean,relative_humidity_2m_mean,cape_mean,cloud_cover_mean",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,rain,showers,snowfall,cloud_cover,dew_point_2m,visibility,evapotranspiration,snow_depth,weather_code,pressure_msl,surface_pressure,wind_speed_10m,wind_direction_10m,wind_gusts_10m,uv_index,freezing_level_height,is_day,wet_bulb_temperature_2m",
        "models": "best_match",
        "current": "temperature_2m,relative_humidity_2m,is_day,wind_speed_10m,wind_direction_10m,wind_gusts_10m,precipitation,rain,showers,snowfall,weather_code,cloud_cover,pressure_msl,surface_pressure",
        "temperature_unit": "celsius",
        "windspeed_unit": "kmh",
        "precipitation_unit": "mm",
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
    """ Helper to display rain, showers, snowfall if their values are > 0 """
    precip_items = {
        'rain': ('Rain:', units.get('rain', 'mm')),
        'showers': ('Showers:', units.get('showers', 'mm')),
        'snowfall': ('Snowfall:', units.get('snowfall', 'cm'))
    }
    displayed_any = False
    for key, (label, unit) in precip_items.items():
        value = data_source.get(key)
        if value is not None and isinstance(value, (int, float)) and value > 0:
            effective_label_width = overall_label_width - len(indent_string)
            print(f"{indent_string}{label:<{effective_label_width}} {format_value_with_unit(value, unit, precision=DEFAULT_PRECISION)}")
            displayed_any = True
    return displayed_any

def display_current_weather(current_data, units, city_display_name):
    print("\n")
    title = f" Current Weather in {city_display_name} "
    print(title.center(len(LINE_SEPARATOR_MEDIUM), "━"))
    
    if not current_data:
        print("\nNo current weather data available.".center(len(LINE_SEPARATOR_MEDIUM)))
        print(LINE_SEPARATOR_MEDIUM)
        return
    print("\n")

    label_width = 23

    print(f"{'Time:':<{label_width}} {format_timestamp(current_data.get('time'))}")
    
    weather_code = current_data.get('weather_code')
    print(f"{'Condition:':<{label_width}} {get_weather_description(weather_code)}")

    temp_val = current_data.get('temperature_2m')
    temp_unit = units.get('temperature_2m', '°C')
    print(f"{'Temperature:':<{label_width}} {format_value_with_unit(temp_val, temp_unit, precision=DEFAULT_PRECISION)}")

    humidity_val = current_data.get('relative_humidity_2m')
    humidity_unit = units.get('relative_humidity_2m', '%')
    print(f"{'Rel. Humidity:':<{label_width}} {format_value_with_unit(humidity_val, humidity_unit)}")
    
    precip_val = current_data.get('precipitation')
    precip_unit = units.get('precipitation', 'mm')
    print(f"{'Total Precipitation:':<{label_width}} {format_value_with_unit(precip_val, precip_unit, precision=DEFAULT_PRECISION, default_val=f'0.0{precip_unit}')}")
    
    if isinstance(precip_val, (int, float)) and precip_val > 0:
        _display_precipitation_details(current_data, units, label_width, indent_string="  ↪ ")

    wind_speed_val = current_data.get('wind_speed_10m')
    wind_speed_unit = units.get('wind_speed_10m', 'km/h')
    wind_dir_deg = current_data.get('wind_direction_10m')
    wind_gusts_val = current_data.get('wind_gusts_10m')

    print(f"{'Wind Speed:':<{label_width}} {format_value_with_unit(wind_speed_val, wind_speed_unit, precision=DEFAULT_PRECISION)}")
    print(f"{'Wind Direction:':<{label_width}} {degrees_to_cardinal(wind_dir_deg)} ({format_value_with_unit(wind_dir_deg, units.get('wind_direction_10m', '°'), precision=0)})")
    if wind_gusts_val is not None and isinstance(wind_gusts_val, (int,float)) and wind_gusts_val > 0:
        print(f"{'Wind Gusts:':<{label_width}} {format_value_with_unit(wind_gusts_val, units.get('wind_gusts_10m', 'km/h'), precision=DEFAULT_PRECISION)}")

    cloud_val = current_data.get('cloud_cover')
    cloud_unit = units.get('cloud_cover', '%')
    print(f"{'Cloud Cover:':<{label_width}} {format_value_with_unit(cloud_val, cloud_unit)}")

    pressure_msl_val = current_data.get('pressure_msl')
    pressure_msl_unit = units.get('pressure_msl', 'hPa')
    print(f"{'Pressure (MSL):':<{label_width}} {format_value_with_unit(pressure_msl_val, pressure_msl_unit, precision=1)}")

    surface_pressure_val = current_data.get('surface_pressure')
    surface_pressure_unit = units.get('surface_pressure', 'hPa')
    print(f"{'Surface Pressure:':<{label_width}} {format_value_with_unit(surface_pressure_val, surface_pressure_unit, precision=1)}")
    
    is_day_val = current_data.get('is_day')
    is_day_str = 'Day ☀️' if is_day_val == 1 else 'Night 🌙' if is_day_val == 0 else DEFAULT_NA
    print(f"{'Day/Night:':<{label_width}} {is_day_str}")

def display_daily_weather(daily_data, units):
    print("\n")
    title = " Daily Forecast "
    print(title.center(len(LINE_SEPARATOR_LONG), "━"))
    
    if not daily_data or not daily_data.get('time'):
        print("\nNo daily forecast data available.".center(len(LINE_SEPARATOR_LONG)))
        print(LINE_SEPARATOR_LONG)
        return
    print("\n")

    label_width = 28
    indent = "  "
    sub_indent = indent + "  "
    effective_sub_label_width = label_width - len(sub_indent)

    times = daily_data.get('time', [])

    for i in range(len(times)):
        try:
            date_str = format_daily_date(times[i])
            print(f"📅 {date_str}:")

            def get_daily_val(key): 
                data_array = daily_data.get(key, [])
                return data_array[i] if data_array and i < len(data_array) else None

            weather_code = get_daily_val('weather_code')
            print(f"{indent}{'Condition:':<{label_width-len(indent)}} {get_weather_description(weather_code)}")

            temp_max = get_daily_val('temperature_2m_max')
            temp_min = get_daily_val('temperature_2m_min')
            temp_unit = units.get('temperature_2m_max', '°C')
            print(f"{indent}{'Temp (Max/Min):':<{label_width-len(indent)}} {format_value_with_unit(temp_max, temp_unit, precision=DEFAULT_PRECISION)} / {format_value_with_unit(temp_min, temp_unit, precision=DEFAULT_PRECISION)}")

            precip_sum_val = get_daily_val('precipitation_sum')
            precip_sum_unit = units.get('precipitation_sum', 'mm')
            precip_prob_max = get_daily_val('precipitation_probability_max')
            precip_prob_unit = units.get('precipitation_probability_max', '%')
            precip_hours = get_daily_val('precipitation_hours')
            precip_hours_unit = units.get('precipitation_hours', 'h')

            print(f"{indent}{'Precip Sum:':<{label_width-len(indent)}} {format_value_with_unit(precip_sum_val, precip_sum_unit, precision=DEFAULT_PRECISION, default_val=f'0.0{precip_sum_unit}')}")
            if isinstance(precip_sum_val, (int,float)) and precip_sum_val > 0:
                rain_s = get_daily_val('rain_sum')
                showers_s = get_daily_val('showers_sum')
                snowfall_s = get_daily_val('snowfall_sum')
                if rain_s is not None and float(rain_s) > 0: print(f"{sub_indent}{'Rain:':<{effective_sub_label_width}} {format_value_with_unit(rain_s, units.get('rain_sum', 'mm'), precision=DEFAULT_PRECISION)}")
                if showers_s is not None and float(showers_s) > 0: print(f"{sub_indent}{'Showers:':<{effective_sub_label_width}} {format_value_with_unit(showers_s, units.get('showers_sum', 'mm'), precision=DEFAULT_PRECISION)}")
                if snowfall_s is not None and float(snowfall_s) > 0: print(f"{sub_indent}{'Snowfall:':<{effective_sub_label_width}} {format_value_with_unit(snowfall_s, units.get('snowfall_sum', 'cm'), precision=DEFAULT_PRECISION)}")
            
            print(f"{indent}{'Precip Probability (Max):':<{label_width-len(indent)}} {format_value_with_unit(precip_prob_max, precip_prob_unit)}")
            print(f"{indent}{'Precip Hours:':<{label_width-len(indent)}} {format_value_with_unit(precip_hours, precip_hours_unit, precision=0)}")


            print(f"{indent}{'Sunrise / Sunset:':<{label_width-len(indent)}} {format_time_from_iso(get_daily_val('sunrise'))} 🌅 / {format_time_from_iso(get_daily_val('sunset'))} 🌇")
            print(f"{indent}{'Daylight / Sunshine:':<{label_width-len(indent)}} {format_duration(get_daily_val('daylight_duration'))} / {format_duration(get_daily_val('sunshine_duration'))}")
            
            print(f"{indent}{'Max UV Index:':<{label_width-len(indent)}} {format_value_with_unit(get_daily_val('uv_index_max'), units.get('uv_index_max', ''), precision=DEFAULT_PRECISION)}")

            wind_speed_max = get_daily_val('wind_speed_10m_max')
            wind_speed_unit = units.get('wind_speed_10m_max', 'km/h')
            wind_gusts_max = get_daily_val('wind_gusts_10m_max')
            wind_dir_deg = get_daily_val('wind_direction_10m_dominant')
            
            print(f"{indent}{'Wind Speed (Max):':<{label_width-len(indent)}} {format_value_with_unit(wind_speed_max, wind_speed_unit, precision=DEFAULT_PRECISION)}")
            if wind_gusts_max is not None and isinstance(wind_gusts_max, (int,float)) and wind_gusts_max > 0:
                 print(f"{indent}{'Wind Gusts (Max):':<{label_width-len(indent)}} {format_value_with_unit(wind_gusts_max, units.get('wind_gusts_10m_max', 'km/h'), precision=DEFAULT_PRECISION)}")
            print(f"{indent}{'Dominant Wind Dir:':<{label_width-len(indent)}} {degrees_to_cardinal(wind_dir_deg)} ({format_value_with_unit(wind_dir_deg, units.get('wind_direction_10m_dominant', '°'), precision=0)})")

            dew_point_mean = get_daily_val('dew_point_2m_mean')
            dew_point_unit = units.get('dew_point_2m_mean', '°C')
            print(f"{indent}{'Dew Point (Mean):':<{label_width-len(indent)}} {format_value_with_unit(dew_point_mean, dew_point_unit, precision=DEFAULT_PRECISION)}")

            vis_mean = get_daily_val('visibility_mean')
            vis_unit = units.get('visibility_mean', 'm')
            print(f"{indent}{'Visibility (Mean):':<{label_width-len(indent)}} {format_visibility_km(vis_mean, vis_unit)}")

        except (IndexError, KeyError) as e:
            print(f"{indent}[WARN] | Incomplete data for day index {i}: {e}")
        except Exception as e:
            print(f"{indent}[WARN] | Error processing data for day index {i}: {e}")
        
        if i < len(times) - 1:
            print(LINE_SEPARATOR_MEDIUM.center(len(LINE_SEPARATOR_LONG)))

def display_hourly_weather(hourly_data, units, current_time_iso_str):
    print("\n")
    title = " Hourly Forecast (Rest of the day) "
    print(title.center(len(LINE_SEPARATOR_LONG), "━"))
    
    if not hourly_data or not hourly_data.get('time'):
        print("\nNo hourly forecast data available.".center(len(LINE_SEPARATOR_LONG)))
        print(LINE_SEPARATOR_LONG)
        return
    print("\n")

    current_dt_obj, end_of_today_dt = None, None
    try:
        if not current_time_iso_str or current_time_iso_str == DEFAULT_NA:
            raise ValueError("Invalid current time provided for hourly forecast filtering.")
        
        processed_current_iso = _handle_iso_string_for_datetime(current_time_iso_str)
        current_dt_obj = datetime.fromisoformat(processed_current_iso)
        end_of_today_dt = datetime(current_dt_obj.year, current_dt_obj.month, current_dt_obj.day, tzinfo=current_dt_obj.tzinfo) + timedelta(days=1)

    except (ValueError, TypeError) as e:
        print(f"[WARNING] | Could not parse current time '{current_time_iso_str}' for hourly filtering: {e}. Showing limited forecast.")

    label_width = 26
    indent = "  "
    sub_item_indent = indent + "  ↪ "
    effective_sub_label_width = label_width - len(sub_item_indent)

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

            weather_code_hr = get_hourly_val('weather_code',i)
            print(f"{indent}{'Condition:':<{label_width-len(indent)}} {get_weather_description(weather_code_hr)}")

            print(f"{indent}{'Temperature:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('temperature_2m',i), units.get('temperature_2m', '°C'), precision=DEFAULT_PRECISION)}")
            print(f"{indent}{'Rel. Humidity:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('relative_humidity_2m',i), units.get('relative_humidity_2m', '%'))}")
            print(f"{indent}{'Dew Point:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('dew_point_2m',i), units.get('dew_point_2m', '°C'), precision=DEFAULT_PRECISION)}")
            
            precip_prob_hr = get_hourly_val('precipitation_probability',i)
            precip_prob_unit = units.get('precipitation_probability', '%')
            print(f"{indent}{'Precip. Probability:':<{label_width-len(indent)}} {format_value_with_unit(precip_prob_hr, precip_prob_unit)}")

            total_precip_hr = get_hourly_val('precipitation',i)
            precip_unit_hr = units.get('precipitation', 'mm')
            print(f"{indent}{'Total Precipitation:':<{label_width-len(indent)}} {format_value_with_unit(total_precip_hr, precip_unit_hr, precision=DEFAULT_PRECISION, default_val=f'0.0{precip_unit_hr}')}")
            
            if isinstance(total_precip_hr, (int, float)) and total_precip_hr > 0:
                current_hour_precip_data = {
                    'rain': get_hourly_val('rain', i),
                    'showers': get_hourly_val('showers', i),
                    'snowfall': get_hourly_val('snowfall', i)
                }
                _display_precipitation_details(current_hour_precip_data, units, label_width, indent_string=sub_item_indent)
            
            snow_depth_val = get_hourly_val('snow_depth', i)
            if snow_depth_val is not None and isinstance(snow_depth_val, (int, float)) and snow_depth_val > 0:
                snow_depth_unit = units.get('snow_depth', 'm')
                if snow_depth_unit == 'm' and snow_depth_val < 1 and snow_depth_val > 0:
                    print(f"{indent}{'Snow Depth:':<{label_width-len(indent)}} {format_value_with_unit(snow_depth_val * 100, 'cm', precision=1)}")
                else:
                    print(f"{indent}{'Snow Depth:':<{label_width-len(indent)}} {format_value_with_unit(snow_depth_val, snow_depth_unit, precision=2)}")

            visibility_m_hr = get_hourly_val('visibility',i)
            vis_unit_hr = units.get('visibility','m')
            print(f"{indent}{'Visibility:':<{label_width-len(indent)}} {format_visibility_km(visibility_m_hr, vis_unit_hr)}")

            print(f"{indent}{'Cloud Cover:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('cloud_cover',i), units.get('cloud_cover', '%'))}")
            
            print(f"{indent}{'Wind Speed:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('wind_speed_10m',i), units.get('wind_speed_10m', 'km/h'), precision=DEFAULT_PRECISION)}")
            wind_dir_deg_hr = get_hourly_val('wind_direction_10m',i)
            print(f"{indent}{'Wind Direction:':<{label_width-len(indent)}} {degrees_to_cardinal(wind_dir_deg_hr)} ({format_value_with_unit(wind_dir_deg_hr, units.get('wind_direction_10m', '°'), precision=0)})")
            
            wind_gusts_hr = get_hourly_val('wind_gusts_10m',i)
            if wind_gusts_hr is not None and isinstance(wind_gusts_hr, (int,float)) and wind_gusts_hr > 0:
                print(f"{indent}{'Wind Gusts:':<{label_width-len(indent)}} {format_value_with_unit(wind_gusts_hr, units.get('wind_gusts_10m', 'km/h'), precision=DEFAULT_PRECISION)}")

            print(f"{indent}{'UV Index:':<{label_width-len(indent)}} {format_value_with_unit(get_hourly_val('uv_index',i), units.get('uv_index', ''), precision=DEFAULT_PRECISION)}")
            
            pressure_msl_hr = get_hourly_val('pressure_msl',i)
            print(f"{indent}{'Pressure (MSL):':<{label_width-len(indent)}} {format_value_with_unit(pressure_msl_hr, units.get('pressure_msl', 'hPa'), precision=1)}")

            freezing_level_hr = get_hourly_val('freezing_level_height',i)
            print(f"{indent}{'Freezing Level:':<{label_width-len(indent)}} {format_value_with_unit(freezing_level_hr, units.get('freezing_level_height', 'm'), precision=0)}")
            
            wet_bulb_hr = get_hourly_val('wet_bulb_temperature_2m',i)
            print(f"{indent}{'Wet Bulb Temp:':<{label_width-len(indent)}} {format_value_with_unit(wet_bulb_hr, units.get('wet_bulb_temperature_2m', '°C'), precision=DEFAULT_PRECISION)}")

            evapo_hr = get_hourly_val('evapotranspiration',i)
            if evapo_hr is not None and isinstance(evapo_hr, (int,float)) and evapo_hr > 0:
                 print(f"{indent}{'Evapotranspiration:':<{label_width-len(indent)}} {format_value_with_unit(evapo_hr, units.get('evapotranspiration', 'mm'), precision=2)}")

            is_day_hr = get_hourly_val('is_day', i)
            print(f"{indent}{'Day/Night:':<{label_width-len(indent)}} {'Day ☀️' if is_day_hr == 1 else 'Night 🌙' if is_day_hr == 0 else DEFAULT_NA}")
            
            is_last_iteration = (i == len(hourly_times) - 1)
            should_break_fallback = (not (current_dt_obj and end_of_today_dt) and displayed_count >= max_display_fallback)
            
            if not is_last_iteration and not should_break_fallback:
                 print(LINE_SEPARATOR_SHORT.center(len(LINE_SEPARATOR_LONG)))

        except (IndexError, KeyError) as e:
            print(f"{indent}[WARN] | Incomplete data for hourly index {i}: {e}")
        except (ValueError, TypeError) as e:
            print(f"{indent}[WARN] | Error processing data for hourly index {i} ('{hourly_time_iso}'): {e}")
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
    if not OPENWEATHERMAP_API_KEY:
        print("[ERROR] | OPENWEATHERMAP_API_KEY not found in environment variables. Please set it in .env file.")
        exit()
        
    city_input = input("Enter city name: ").strip()
    if not city_input:
        print("[ERROR] | City name cannot be empty.")
    else:
        print(f"Searching for coordinates for '{city_input}'...")
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
            print(f"Failed to obtain coordinates for '{city_input}'. Cannot fetch weather data.")