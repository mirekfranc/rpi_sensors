WEB = True
SENSOR_INTERVAL = 30
GRAPH_IT_INTERVAL = 2

BASE = '/var/www/html/'
DB = BASE + ('web.db' if WEB else 'terminal.db')
NGINX_WEB = BASE + 'index.html'
NGINX_LOG = BASE + 'log.txt'
WEB_HEADER = '''<!DOCTYPE html>
<html>
<head>
<meta charset="utf8">
<title>Bievenue chez Geneviève</title>
<style>
body {
    color: white;
    background-color: black;
	margin: auto 0.2em;
	font-size: 3.2em;
	font-family: Tahoma, Verdana, Arial, sans-serif;
}
</style>
</head>
<body>
<h3>Bievenue chez Geneviève</h3>
'''
WEB_FOOTER = '''
<img src="img_co2.png" alt="CO₂ Levels Over Time" width="1000" height="500">
<img src="img_temp.png" alt="Temperature Over Time" width="1000" height="500">
<img src="img_rh.png" alt="Relative Humidity Over Time" width="1000" height="500">
<img src="img_ah.png" alt="Absolute Humidity Over Time" width="1000" height="500"> 
<img src="img_pressure.png" alt="Air Pressure Over Time" width="1000" height="500">
<img src="img_dp.png" alt="Dew Point Over Time" width="1000" height="500">
</body></html>
'''

import time, board, busio, math, adafruit_bmp280, adafruit_scd4x, datetime, sqlite3, sys, os, multiprocessing

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
plt.style.use('dark_background')

def ts2td(ts):
    return datetime.datetime.fromtimestamp(float(ts))

def ts2str(ts):
    return ts2td(ts).strftime('%Y-%m-%d %H:%M:%S')

def get_absolute_humidity(temp_c, rh_percent):
    saturation_vapor_pressure = 6.112 * math.exp((17.67 * temp_c) / (temp_c + 243.5))
    actual_vapor_pressure = rh_percent / 100.0 * saturation_vapor_pressure
    absolute_humidity = 216.7 * actual_vapor_pressure / (temp_c + 273.15)
    return absolute_humidity

def get_dew_point(temp_c, rh_percent):
    a, b = 17.62, 243.12
    alpha = ((a * temp_c) / (b + temp_c)) + math.log(rh_percent / 100.0)
    dew_point = (b * alpha) / (a - alpha)
    return dew_point

class Log:
    def __init__(self, now):
        then = now - 24 * 3600 # 24 hours
        self.output_file_base = BASE + os.sep + 'img_'
        self.values = { 'time': [], 'temp1': [], 'pressure': [], 'temp2': [], 'relative_humidity': [], 'absolute_humidity': [], 'dew_point': [], 'co2': [] }
        query = f'SELECT time, temp1, pressure, temp2, relative_humidity, co2 FROM sensor_data WHERE time > {then}'
        with sqlite3.connect(DB) as conn:
            cur = conn.cursor()
            cur.execute(query)
            while True:
                r = cur.fetchone()
                if not r:
                    break
                try:
                    self.values['time'].append(ts2td(r[0]))
                    self.values['temp1'].append(r[1])
                    self.values['pressure'].append(r[2])
                    self.values['temp2'].append(r[3])
                    self.values['relative_humidity'].append(r[4])
                    ah2 = get_absolute_humidity(r[3], r[4])
                    self.values['absolute_humidity'].append(ah2)
                    dp2 = get_dew_point(r[3], r[4])
                    self.values['dew_point'].append(dp2)
                    self.values['co2'].append(r[5])
                except ValueError:
                    print(f'values are malformed: {l}', file=sys.stderr)
                    continue

    def __plot(self, what, ything, title, file):
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.set_title(title)
        for w, k, c in what:
            ax.plot(self.values['time'], self.values[k], label=w, color=c)
        ax.set_xlabel('Time')
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=30))
        ax.set_ylabel(ything)
        ax.legend()
        ax.grid(True, color='gray', linestyle='dotted', alpha=0.5)
        fig.tight_layout()
        fig.savefig(self.output_file_base + file)
        plt.close(fig)

    def plot_co2(self):
        self.__plot(what=[('CO₂ (ppm)', 'co2', 'lightgreen')], ything='CO₂ Concentration (CO₂, sdc41)', title='CO₂ Levels Over Time', file='co2.png')

    def plot_temp(self):
        self.__plot(what=[('Temperature (°C, bmp280)', 'temp1', 'lightgreen'), ('Temperature (°C, scd41)', 'temp2', 'lightblue')],
                    ything='Temperature (bmp280, sdc41)', title='Temperature Over Time', file='temp.png')

    def plot_dew_point(self):
        self.__plot(what=[('Dew Point (°C, scd41)', 'dew_point', 'red')], ything='Dew Point (sdc41)', title='Dew Point Over Time', file='dp.png')

    def plot_pressure(self):
        self.__plot(what=[('Pressure (hPa)', 'pressure', 'yellow')], ything='Pressure (hPa, bmp280)', title='Air Pressure Over Time', file='pressure.png')

    def plot_rh(self):
        self.__plot(what=[('Relative Humidity (%)', 'relative_humidity', 'lightblue')], ything='Relative Humidity (%, scd41)', title='Relative Humidity Over Time', file='rh.png')

    def plot_ah(self):
        self.__plot(what=[('Absolute Humidity (g/m³)', 'absolute_humidity', 'lightblue')], ything='Absolute Humidity (g/m³, calculated, scd41)', title='Absolute Humidity Over Time', file='ah.png')

def create_graphs(now):
    l = Log(now)
    l.plot_co2()
    l.plot_temp()
    l.plot_dew_point()
    l.plot_pressure()
    l.plot_rh()
    l.plot_ah()

i2c = busio.I2C(board.SCL, board.SDA)
bmp280 = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
scd41 = adafruit_scd4x.SCD4X(i2c)

scd41.stop_periodic_measurement()
time.sleep(1)
scd41.temperature_offset = 0.56
time.sleep(1)
print(scd41.temperature_offset)

scd41.start_low_periodic_measurement()
time.sleep(35)

def print_stuff(f, begin, end, time, t1, p1, t2, rh2, co22):
    print(f"{begin}BMP280: Temperature......... {t1:.2f} °C{end}", file=f)
    print(f"{begin}BMP280: Pressure............ {p1:.2f} hPa{end}", file=f)
    print(f"{begin}SCD41 : Temperature......... {t2:.2f} °C{end}", file=f)
    print(f"{begin}SCD41 : Relative Humidity... {rh2:.2f} %{end}", file=f)
    ah2 = get_absolute_humidity(t2, rh2)
    print(f"{begin}SCD41 : Absolute Humidity... {ah2:.2f} g/m³{end}", file=f)
    dp2 = get_dew_point(t2, rh2)
    print(f"{begin}SCD41 : Dew Point........... {dp2:.2f} °C{end}", file=f)
    print(f"{begin}SCD41 : CO2................. {co22} ppm{end}", file=f)
    print(begin, "---", ts2str(time), "-" * 16, end, file=f)

def print_terminal(time, t1, p1, t2, rh2, co22):
    print_stuff(sys.stdout, '', '', time, t1, p1, t2, rh2, co22)

def print_web(time, t1, p1, t2, rh2, co22):
    with open(NGINX_WEB, 'w') as f:
        print(WEB_HEADER, file=f)
        print_stuff(f, '<p><tt>', '</p></tt>', time, t1, p1, t2, rh2, co22)
        print(WEB_FOOTER, file=f)

def create_db():
    with sqlite3.connect(DB) as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY,
        time INTEGER UNIQUE,
        temp1 REAL,
        pressure REAL,
        temp2 REAL,
        relative_humidity REAL,
        co2 INTEGER
        );
        ''')

def log_db(time, t1, p1, t2, rh2, co22):
    query = 'INSERT INTO sensor_data (time, temp1, pressure, temp2, relative_humidity, co2) VALUES (?, ?, ?, ?, ?, ?)'
    with sqlite3.connect(DB) as conn:
        conn.execute(query, [time, t1, p1, t2, rh2, co22])

create_db()

it = 0;
while True:
    it += 1
    now = int(datetime.datetime.now().timestamp())
    if scd41.data_ready:
        data = [ now, bmp280.temperature, bmp280.pressure, scd41.temperature, scd41.relative_humidity, int(scd41.CO2) ]
        scd41.set_ambient_pressure(int(bmp280.pressure))
        log_db(*data)
        if WEB:
            print_web(*data)
        else:
            print_terminal(*data)
    p = None
    if WEB and (it % GRAPH_IT_INTERVAL == 0):
        p = multiprocessing.Process(target=create_graphs, args=(now,))
        p.start()
    time.sleep(SENSOR_INTERVAL)
    if p:
        p.join()
