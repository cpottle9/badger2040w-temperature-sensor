A relatively simple application to monitor temperature using an Adafruit mcp9808 temperature sensor and report temperature data to an MQTT server.

The application is intended to run on battery.
Temperature, date, time, and battery voltage are output to the badger E-ink display screen.
Temperature and battery voltage are published to an MQTT server.

This app makes use of the badger RTC chip to deepsleep and wake up once a minute.
Previous temperature is stored on flash in a json file.
If the temperature change is too small the screen and the MQTT server are not updated.
After 10 minutes with no temperature change the screen and MQTT will be updated anyway.
The Raspberry PI Pico W WIFI chip is only powered up when needed.

While testing my code I noted instances where the app would hang.
I am pretty sure this occured when my wifi router was down or the MQTT server was down.
I am using the RP2040 watchdog timer to detect these hangs and restart the RP2040.
The RTC chip on the Badger has a single byte of RAM that will persist over a restart.
I use that byte to track the last place in my code where the watchdog timer was fed.

The app will display a hex value on the bottom right of the E-ink screen when a
watchdog timeout occurs.
There are other error conditions my code detects using try/except blocks.
Data about these error conditions is displayed in the bottom left.
The error data is also stored in the json file on flash and published to the MQTT server.

You will need to create a file secrets.py with your wifi credentials, your 2 letter country code,
your MQTT credentials, and yourlocal time offet from GMT in seconds.
I am in Canada in the Pacific timezone.
My secrets.py is:
```
# wifi credentials

WIFI_SSID = "MY-SSID"
WIFI_PASS = "MY-PASSWORD"
COUNTRY="CA"

# MQTT credentials

MQTT_SERVER = '192.168.0.18'
CLIENT_ID = 'BadgerW'
USER_T = 'MQTT-USERID'
PASSWORD_T = 'MQTT-PASSWORD'

# Timezone offset from GMT in seconds
TZ_OFFSET=-(7 * 60 * 60)
```
You will have to set all these variable with your details.
If you run more than one instance of this app talking to a single MQTT server each will need a unique CLIENT_ID.

I am making this code available under MIT license.
Not because it is terribly useful.
But, it might be helpful as starting point for other people building there own project.

I will do minor updates over time.
In general, I will not be accepting pull requests.







