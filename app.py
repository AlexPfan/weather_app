from flask import Flask, render_template, request
import requests

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
        'exclude': 'minutely,hourly,daily,alerts'
    }
    resp = requests.get(url, params=params)
    return resp.json()

@app.route('/', methods=['GET', 'POST'])
def index():
    weather = None
    location = None
    country = None
    wind_compass = None
    error = None

    if request.method == 'POST':
        city = request.form.get('city')
        lat, lon, location, country = get_coordinates(city)
        if lat is None or lon is None:
            error = "City not found."
        else:
            data = get_current_weather(lat, lon)
            if 'current' in data:
                weather = data['current']
                wind_deg = weather.get('wind_deg')
                wind_compass = deg_to_compass(wind_deg) if wind_deg is not None else None
            else:
                error = "Weather data not found for the provided location."

    return render_template(
        'index.html',
        weather=weather,
        location=location,
        country=country,
        wind_compass=wind_compass,
        error=error
    )

if __name__ == '__main__':
    app.run(debug=True)
