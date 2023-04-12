#
# Immediately turn off the Badger2040W LED
#
from machine import reset, ADC, lightsleep, Pin
Pin(22).off()

import badger2040w
from badger2040w import HEIGHT, WIDTH
from sys import exit
from time import sleep_ms
from mcp9808 import MCP9808

from math import fabs
import ntptime
import utime
from json_repo import JSON_REPO

from pcf_badger import pcf_chip

from network import WLAN, STA_IF
from watchdog import WATCHDOG
from umqttsimple import MQTTClient
#
# Create your own file secrets.py containing WIFI credentials,
# MQTT credentials, and your time zone offset from GMT in seconds.
#
from secrets import WIFI_SSID, WIFI_PASS, COUNTRY, CLIENT_ID, MQTT_SERVER, USER_T, PASSWORD_T, TZ_OFFSET

last_error = 0
rtc_chip = pcf_chip()

wdt = WATCHDOG(8388) # Note: My watchdog class disables watchdog in __init__

if wdt.caused_reboot() :
    try :
        last_feeder = rtc_chip.get_byte()
        
        my_fail("Watchdog restart", 0)
    except :
        # In this case I want to continue execution
        # But sleep for a bit.
        # 
        sleep_ms(60000)
        pass

class RestartNeededException(Exception) :
    # Raised when application code fails
    pass

def my_fail(reason, cause) :
    global last_error
    global repo
    global wdt
    wdt.disable()
    # last_error is formatted as follows:
    #
    # Bits 0 to 23 are a mask. Each bit position corresponds
    # to a number of flashes requested.
    #
    # Bits 24 to 30 are a count of the total number of fails
    # since the last power up.
    # Value will be 0 to 127 and will wrap-around.
    #
    # Bit 31 not used to avoid sign issues.
    #
    error_mask = last_error & 0x0ffffff
    error_count = (last_error >> 24) &0x0ff
    error_count += 1
    error_count &= 0x7f
    error_mask |= (1<<cause) & 0x0ffffff
    last_error = (error_count << 24) | error_mask

    repo.set_error(last_error)
    repo.write_cache()

    # Removed led flash. Rely on publishing errors
    raise RestartNeededException

display = badger2040w.Badger2040W()

wlan = None
def connectWifi() :
    global wlan
    wdt.feed(0xf0)
    rp2.country(COUNTRY)
    wdt.feed(0xf1)
    wlan = WLAN(STA_IF)
    wdt.feed(0xf2)

    # Aggressive power saving mode. Will reduce throughput.
    wlan.config(pm = 0xa11c81)
    wdt.feed(0xf3)
    wlan.active(True)
    wdt.feed(0xf4)
    
    wlan.connect(WIFI_SSID, WIFI_PASS)
    wdt.feed(0xf5)
    # Wait for connect or fail
    max_wait = 10
    while max_wait > 0 :
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        wdt.feed(0xf6)
        sleep_ms(1000)
    wdt.feed(0xf7)
    
    # Handle connection error
    if wlan.status() != 3 :
        my_fail('Connect failed', 1)

def disconnectWifi() :
    global wlan
    wlan.disconnect()
    wlan.active(False)
    wlan.deinit()
    wlan = None
   
#
# Display temperature in center of display using size 5
#

def display_temperature(temp_str) :
    text_width = display.measure_text(temp_str, 5)
    text_height = 8 * 5
    x = int((WIDTH - text_width) /2)
    y = int((HEIGHT - text_height)/2)
    display.text(temp_str, x, y, WIDTH-x, 5)

#
# Display vsys at top right of the screen left size 3.
#
def display_vsys(str) :
    text_width = display.measure_text(str, 2)
    x = WIDTH - text_width
    y = 0
    display.text(str, x, y, WIDTH, 2)

#
# Display last_error bottom on left
#
def display_lasterror(str) :
    x = 0
    y = HEIGHT - 8*2
    display.text(str, x, y, WIDTH, 2)

#
# Display feeder on the bottom right
#
def display_feeder(str) :
    text_width = display.measure_text(str, 2)
    x = WIDTH - text_width
    y = HEIGHT - 8*2
    display.text(str, x, y, WIDTH, 2)

#
# Display date in top left
#
def display_date(str) :
    x = 0
    y = 0
    display.text(str, x, y, WIDTH, 2)

#
# Display time immediately below date
#
def display_time(str) :
    x = 0
    y = 8*2
    display.text(str, x, y, WIDTH, 2)

# badger stemma QT is connected to pins 4 & 5
i2c = machine.I2C(0,sda=machine.Pin(4), scl=machine.Pin(5), freq=400000)
mcp9808 = MCP9808(i2c)

#
# Call only when wifi is inactive
#

def get_vsys():
   try:
      # Make sure pin 25 is high.
      Pin(25, mode=Pin.OUT, pull=Pin.PULL_DOWN).high()
      
      # Reconfigure pin 29 as an input.
      Pin(29, Pin.IN)
      
      return ADC(29).read_u16() * (3 * 3.3 / 65535)
   
   finally:
      # Restore the pin state
      Pin(29, Pin.ALT, pull=Pin.PULL_DOWN, alt=7)


def update_screen() :
    global display
    display.set_update_speed(badger2040w.UPDATE_MEDIUM)
    display.set_font("bitmap8")

    wdt.feed(0x21)
    display.set_pen(15)
    display.clear()
    display.set_pen(0)
    display_temperature("%.1f C" % temp)
    display_vsys("%.2f V" % vsys)
    if last_error != 0 :
        display_lasterror("E %08x" % last_error)
    if last_feeder != 0 :
        display_feeder("F %08x" % last_feeder)

    wdt.feed(0x22)
    # utime.gmtime() gives us time from machine.rtc.

    now = utime.gmtime(utime.time() + TZ_OFFSET)
    display_date("%04d/%02d/%02d"% (now[0], now[1], now[2]))
    display_time("%02d:%02d:%02d" % (now[3], now[4], now[5]))
    wdt.feed(0x23)
    display.update()

#
# Customize these for your MQTT server
#
topic_pub = 'sensors/home/BadgerW/P/C1/temperature_C'
topic_vsys_pub = 'sensors/home/BadgerW/P/C1/vsys'
topic_last_error_pub = 'sensors/home/BadgerW/P/C1/last_error'
topic_feeder_pub = 'sensors/home/BadgerW/P/C1/feeder'

def mqtt_connect() :
    try :
        client = MQTTClient(CLIENT_ID, MQTT_SERVER, user=USER_T, password=PASSWORD_T, keepalive=60)
        client.connect()
        return client
    except :
        my_fail('Mqtt connect failed', 3)
    return client

def publish(temp, vsys) :
    try :
        global last_error, last_feeder
        temp_data = "%.1f" % temp
        client.publish(topic_pub, msg=temp_data)
        
        vsys_data = "%.2f" % vsys
        client.publish(topic_vsys_pub, msg=vsys_data)

        if last_error != 0 :
            client.publish(topic_last_error_pub, msg=hex(last_error))

        if last_feeder != 0 :
            client.publish(topic_feeder_pub, msg=hex(last_feeder))
    except: 
        my_fail('Mqtt publish failed', 4)

try :
    repo = JSON_REPO()
            
    #
    # Loop for running on USB and thonny
    #
    while True:
        #
        # Set date/time
        #
        # If the pcf85063a RTC chip has a valid date/time use it.
        # Otherwise connect to the internet to get date time and
        # set the pcf85063a date time.
        #
        wdt.enable()
        wdt.feed(0x01)
        if not rtc_chip.is_pcf_datetime_valid() :
            connectWifi()
            wdt.feed(0x02)
            ntptime.settime()
            wdt.feed(0x03)
            disconnectWifi()
            wdt.feed(0x04)
            rtc_chip.set_pcf_from_rtc()
            wdt.feed(0x05)
        else :
            wdt.feed(0x06)
            rtc_chip.set_rtc_from_pcf()

        last_temp   = repo.get_temp()
        last_error  = repo.get_error()
        last_feeder = repo.get_feeder()
        count       = repo.get_count()
        
        wdt.feed(0x07)
        temp = mcp9808.temperature()
        delta_temp = fabs(temp - last_temp)
        if (count < 5  and delta_temp > 0.19) or (count >= 5 and delta_temp > 0.09) or (count >= 10) :
            vsys = get_vsys()
            wdt.feed(0x08)
            update_screen()
            repo.set_temp(temp)
            wdt.feed(0x09)
            connectWifi()
            wdt.feed(0x0a)
            client = mqtt_connect()
            wdt.feed(0x0b)
            publish(temp, vsys)
            wdt.feed(0x0c)
            sleep_ms(750)
            client.disconnect()
            sleep_ms(500)
            wdt.feed(0x0d)
            disconnectWifi()
            sleep_ms(750)
            count = 0
        else :
            # use feeder to count running with no update
            count += 1
            
        repo.set_count(count)
        repo.set_error(last_error)
        wdt.feed(0x0e)
        repo.write_cache()
        
        wdt.feed(0x0f)
        # Won't return when running from battery.
        rtc_chip.sleep_for(1, wdt) # wdt only used when running on USB power
        
except RestartNeededException :
    wdt.disable()
    # Try to write to cache.
    try :
        repo.set_error(last_error)
        repo.write_cache()
    except:
        pass
    lightsleep(60000)
    reset()
