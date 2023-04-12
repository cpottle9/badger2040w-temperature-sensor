#
# Badger specific code for the pcf85063a used on badger2040w
#
# Loosely based on code in inky_frame.py and badger2040w.py provided by pimoroni.
#
# Ideally this would work for both badger2040W and inky_frame
# but, some pins are different.
# 

from pcf85063a import PCF85063A
from micropython import const
from machine import Pin, I2C, RTC
from pimoroni import ShiftRegister
from time import sleep_ms
import wakeup

class pcf_chip :
    
    RTC_ALARM        = const(8)
    HOLD_VSYS_EN     = const(10)

    #
    # Buttons don't really belong here.
    #
    
    BUTTON_DOWN      = const(11)
    BUTTON_A         = const(12)
    BUTTON_B         = const(13)
    BUTTON_C         = const(14)
    BUTTON_UP        = const(15)
    BUTTON_MASK      = const(0b0000_0000_0000_0000_1111_1000_0000_0000)
    ALARM_MASK       = const(0b0000_0000_0000_0000_0000_0001_0000_0000)
    
    def __init__(self) :
        self._i2c = I2C(0, sda=Pin(4), scl=Pin(5), freq=400000)
        # _pcf is the external RTC device
        self._pcf = PCF85063A(self._i2c)
        self._pcf.enable_timer_interrupt(False)
        self._i2c.writeto_mem(0x51, 0x00, b'\x00')  # ensure rtc is running (this should be default?)
        self._pcf.enable_timer_interrupt(False)
        self._vsys = Pin(HOLD_VSYS_EN)
        self._vsys.on()
        self._alarm = Pin(RTC_ALARM)

    #
    # Set external rtc date/time from pico RTC
    #
    
    def set_pcf_from_rtc(self) :
        year, month, day, dow, hour, minute, second, _ = RTC().datetime()
        self._pcf.datetime((year, month, day, hour, minute, second, dow))

    #
    # Set pico RTC date/time from external rtc
    #
    def set_rtc_from_pcf(self) :
        if self.is_pcf_datetime_valid() :
            t = self._pcf.datetime()
            # BUG ERRNO 22, EINVAL, when date read from RTC is invalid for the Pico's RTC.
            try:
                RTC().datetime((t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0))
                return True
            except OSError:
                pass
        return False
       
    #
    # Return True if the pcf datetime is reasonable (year >= 2022
    #
    def is_pcf_datetime_valid(self) :
        now = self._pcf.datetime()
        return now[0] >= 2022

    #
    # Return pcf datetime
    #
    def datetime(self) :
        return self._pcf.datetime()
    #
    # return true if woke by pcf alarm
    #
    def woken_by_rtc(self) :
        return wakeup.get_gpio_state() & ALARM_MASK > 0

    #
    # Turn off all of badger except the pcf chip.
    #
    def turn_off(self) :
        sleep_ms(100)
        self._vsys.off()

    #
    # Do deep deep sleep with pcf waking us up
    #
    # Sleep at least a minute and less than a day.

    def sleep_for (self, minutes, wdt) :

        _, _, _, hour, minute, second, _ = self._pcf.datetime()
        if second >= 55 :
            minute += 1

        minute += minutes

        while minute >= 60 :
            minute -= 60
            hour += 1
            
        while hour >= 24 :
            hour -= 24

        
        self._pcf.clear_alarm_flag()
        self._pcf.set_alarm(0, minute, hour)
        self._pcf.enable_alarm_interrupt(True)

        # Will not return when on battery
        self.turn_off()

        # Running from USB power. Simulate.
        #
        # Sleep one second at a time so user does not need to hold down the
        # button too long.
        seconds = minutes * 60
        while seconds > 0 :
            wdt.feed(0x10)
            sleep_ms(1000)
            if Pin(BUTTON_DOWN).value() != 0 :
                break
            if Pin(BUTTON_A).value() != 0 :
                break
            if Pin(BUTTON_B).value() != 0 :
                break
            if Pin(BUTTON_C).value() != 0 :
                break
            if Pin(BUTTON_UP).value() != 0 :
                break
            seconds -= 1

    #
    # Set the scratch byte in the pcf.
    #
    def set_byte(self, byte) :
        self._pcf.set_byte( byte)
    #
    # get the scratch byte in the pcf.
    #
    def get_byte(self) :
        return self._pcf.get_byte()
