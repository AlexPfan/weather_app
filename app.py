from flask import Flask, render_template, request
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
API_KEY = '97586efa76fd3e2199dc434ff2aafdd1'  # Replace with your OpenWeatherMap API key

def get_coordinates(city):
    geo_url = "http://api.openweathermap.org/geo/1.0/direct"
    params = {'q': city, 'limit': 1, 'appid': API_KEY}
    resp = requests.get(geo_url, params=params)
    data = resp.json()
    if data:
        return data[0]['lat'], data[0]['lon'], data[0]['name'], data[0].get('country', '')
    return None, None, None, None

def deg_to_compass(deg):
    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
    ix = int((deg + 22.5) / 45.0) % 8
    return directions[ix]

def get_current_weather(lat, lon):
    url = "https://api.openweathermap.org/data/3.0/onecall"
    params = {
        'lat': lat,
        'lon': lon,
        'appid': API_KEY,
        'units': 'metric',
        'exclude': 'minutely,alerts'
    }
    resp = requests.get(url, params=params)
    return resp.json()

# convert to local date-time
def convert_to_local_time(utc_timestamp, timezone_offset):
    utc_time = datetime.utcfromtimestamp(utc_timestamp)
    offset = timedelta(seconds=timezone_offset)
    local_time = utc_time + offset
    return local_time.strftime('%Y-%m-%d %H:%M:%S')

# convert to local time 
def convert_to_local_time_hms(utc_timestamp, timezone_offset):
    utc_time = datetime.utcfromtimestamp(utc_timestamp)
    offset = timedelta(seconds=timezone_offset)
    local_time = utc_time + offset
    return local_time.strftime('%H:%M:%S')

# calculate moon phases
def moon_phase_name(phase):
    if phase == 0 or phase == 1:
        return "New Moon"
    elif 0 < phase < 0.25:
        return "Waxing Crescent"
    elif phase == 0.25:
        return "First Quarter"
    elif 0.25 < phase < 0.5:
        return "Waxing Gibbous"
    elif phase == 0.5:
        return "Full Moon"
    elif 0.5 < phase < 0.75:
        return "Waning Gibbous"
    elif phase == 0.75:
        return "Last Quarter"
    else:
        return "Waning Crescent"
    
def filter_hourly_for_today(hourly, timezone_offset):
    now_utc = datetime.utcnow()
    now_local = now_utc + timedelta(seconds=timezone_offset)
    today_date = now_local.date()

    filtered_hours = []
    for hour in hourly:
        dt_local = datetime.utcfromtimestamp(hour['dt']) + timedelta(seconds=timezone_offset)
        if dt_local.date() == today_date:
            hour['time_str'] = dt_local.strftime('%H:%M')
            filtered_hours.append(hour)
    return filtered_hours


@app.route('/', methods=['GET', 'POST'])
def index():
    weather = None
    location = None
    country = None
    wind_compass = None
    error = None
    sunrise_local = None
    sunset_local = None
    moon_phase_str = None
    hourly_today = []
    forecast = []
    lat = None 
    lon = None  

    if request.method == 'POST':
        city = request.form.get('city')
        lat = request.form.get('lat')
        lon = request.form.get('lon')
        map_layer = request.form.get('map_layer', 'osm')

        # If lat/lon are provided, use them; otherwise, geocode city
        if lat and lon:
            try:
                lat = float(lat)
                lon = float(lon)
                location = None
                country = None
            except ValueError:
                error = "Invalid coordinates."
        elif city:
            lat, lon, location, country = get_coordinates(city)
            if lat is None or lon is None:
                error = "City not found."
        else:
            error = "Please enter a city or click on the map"
        
        if not error and lat is not None and lon is not None:
            data = get_current_weather(lat, lon)
            print('API response:', data)
            if 'current' in data:
                weather = data['current']
                # Convert wind speed to knots if present
                if 'wind_speed' in weather:
                    weather['wind_speed_knots'] = round(weather['wind_speed'] * 1.94384, 1)
                wind_deg = weather.get('wind_deg')
                wind_compass = deg_to_compass(wind_deg) if wind_deg is not None else None
                sunrise_local = convert_to_local_time_hms(weather.get('sunrise'), data.get('timezone_offset', 0))
                sunset_local = convert_to_local_time_hms(weather.get('sunset'), data.get('timezone_offset', 0))
                # Get moon phase for current day from the first daily forecast
                moon_phase_value = None
                moon_phase_str = None
                if data.get('daily'):
                    moon_phase_value = data['daily'][0].get('moon_phase')
                    moon_phase_str = moon_phase_name(moon_phase_value) if moon_phase_value is not None else None

                # Get daily forecast for the next 3 days (excluding today)
                forecast = data.get('daily', [])[1:5]  # days 1, 2, 3

                for day in forecast:
                    # Convert wind speed to knots if present
                    if 'wind_speed' in day:
                        day['wind_speed_knots'] = round(day['wind_speed'] * 1.94384, 1)
                    day['date_str'] = convert_to_local_time(day['dt'], data.get('timezone_offset', 0)).split(' ')[0]
                    day['wind_compass'] = deg_to_compass(day.get('wind_deg')) if day.get('wind_deg') is not None else None
                    if 'moon_phase' in day:
                        day['moon_phase_str'] = moon_phase_name(day['moon_phase'])

                hourly_today = filter_hourly_for_today(data.get('hourly', []), data.get('timezone_offset', 0))

            else:
                error = "Weather data not found for the provided location."

    return render_template(
        'index.html',
        # current weather data
        weather=weather,
        location=location,
        country=country,
        wind_compass=wind_compass,
        error=error,
        sunrise_local=sunrise_local,
        sunset_local=sunset_local,
        # forecast
        forecast=forecast,

        lat=lat,
        lon=lon,
        moon_phase_str=moon_phase_str,

        hourly_today=hourly_today,
        map_layer=map_layer
    )

if __name__ == '__main__':
    app.run(debug=True)
