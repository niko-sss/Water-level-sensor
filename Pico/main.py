import time, utime, ujson, network, urequests
from machine import Pin, SPI, ADC
from drivers.ili9341.ili9341 import ILI9341
import framebuf
from gui.core.writer import Writer, CWriter
import arial24b as FNT
import dht

# ---------------------------------------------------
# SETTINGS wifi, ts, calibration file
# ---------------------------------------------------

ADC_PIN = 26  # GP26 = ADC0
BTN_OK_PIN = 16
CALIB_FILE = "calib.json"

SSID = "YourSSID"
PASS = "YourPassword"

THINGSPEAK_API_KEY = "YourApiKey"
THINGSPEAK_URL = "YourUrl"
TS_MIN_INTERVAL_MS = 600000  # 10 minutes

LOW_WARN  = 10
HIGH_WARN = 90

# DHT11
DHT_PIN = 15
sensor = dht.DHT11(Pin(DHT_PIN))

# LED / pump control pin
PUMP_PIN = 14
pump = Pin(PUMP_PIN, Pin.OUT)
PUMP_LED = Pin("LED", Pin.OUT)


# Backend URL for control
PUMP_CONTROL_URL = "YourPumpControlUrl"

# ---------------------------------------------------
# ADC
# ---------------------------------------------------

adc = ADC(ADC_PIN)

def read_pot_raw(n=8):
    s = 0
    for _ in range(n):
        s += adc.read_u16()
    return s // n

def raw_to_volt(raw):
    return raw * 3.3 / 65535.0

# ---------------------------------------------------
# DISPLAY INITIALIZATION
# ---------------------------------------------------

spi = SPI(0, baudrate=40_000_000, polarity=0, phase=0,
          sck=Pin(18), mosi=Pin(19))

cs  = Pin(17, Pin.OUT)
dc  = Pin(20, Pin.OUT)
rst = Pin(21, Pin.OUT)

tft = ILI9341(spi, cs=cs, dc=dc, rst=rst,
              height=320, width=240, mod=2, usd=False)

tft.greyscale(False)
tft.fill(0)
tft.show()

# Color indexes
IDX_BLACK = CWriter.create_color(tft, 0, 0, 0, 0)
IDX_WHITE = CWriter.create_color(tft, 1, 255, 255, 255)
IDX_RED   = CWriter.create_color(tft, 2, 255, 0, 0)
IDX_GREEN = CWriter.create_color(tft, 3, 0, 255, 0)
IDX_BLUE  = CWriter.create_color(tft, 4, 0, 0, 255)
IDX_CYAN  = CWriter.create_color(tft, 5, 0, 200, 200)
IDX_GREY  = CWriter.create_color(tft, 6, 120, 120, 120)

uw = Writer(tft, FNT)
_color_writers = {}

def utext(x, y, s):
    Writer.set_textpos(tft, y, x)
    uw.printstring(s)

def utext_color(x, y, s, color_idx, bg_idx=IDX_BLACK):
    key = (color_idx, bg_idx)
    cw = _color_writers.get(key)
    if cw is None:
        cw = CWriter(tft, FNT, color_idx, bg_idx)
        _color_writers[key] = cw
    CWriter.set_textpos(tft, y, x)
    cw.printstring(s)

def fill_rect(x, y, w, h, color_idx):
    tft.fill_rect(x, y, w, h, color_idx)

def rect(x, y, w, h, color_idx):
    tft.rect(x, y, w, h, color_idx)

def text(s, x, y, color_idx=IDX_WHITE):
    tft.text(s, x, y, color_idx)

def text_scaled(s, x, y, color_idx=IDX_WHITE, scale=2):
    if scale <= 1:
        tft.text(s, x, y, color_idx)
        return
    w = 8 * len(s)
    h = 8
    buf = bytearray((w * h + 7) // 8)
    fb = framebuf.FrameBuffer(buf, w, h, framebuf.MONO_HLSB)
    fb.fill(0)
    fb.text(s, 0, 0, 1)
    for yy in range(h):
        for xx in range(w):
            if fb.pixel(xx, yy):
                tft.fill_rect(x + xx*scale, y + yy*scale,
                              scale, scale, color_idx)

def draw_progress(x, y, w, h, pct, fg=IDX_CYAN, bg=IDX_GREY, border=IDX_WHITE):
    pct = max(0, min(100, pct))
    fill_rect(x, y, w, h, bg)
    rect(x, y, w, h, border)
    inner_w = w - 2
    filled = int(inner_w * pct / 100)
    if filled > 0:
        fill_rect(x+1, y+1, filled, h-2, fg)

# ---------------------------------------------------
# BUTTON HANDLING
# ---------------------------------------------------

btn_ok = Pin(BTN_OK_PIN, Pin.IN, Pin.PULL_UP)

def wait_ok():
    while btn_ok.value() == 0:
        time.sleep_ms(10)
    while btn_ok.value() == 1:
        time.sleep_ms(10)
    time.sleep_ms(25)
    while btn_ok.value() == 0:
        time.sleep_ms(10)

def ok_long_pressed(ms=2000):
    if btn_ok.value() == 1:
        return False
    t0 = utime.ticks_ms()
    while btn_ok.value() == 0:
        if utime.ticks_diff(utime.ticks_ms(), t0) >= ms:
            while btn_ok.value() == 0:
                time.sleep_ms(10)
            return True
        time.sleep_ms(10)
    return False

# ---------------------------------------------------
# CALIBRATION FILE
# ---------------------------------------------------

def load_calib():
    try:
        with open(CALIB_FILE, "r") as f:
            data = ujson.load(f)
        mn = int(data.get("min_raw", 0))
        mx = int(data.get("max_raw", 65535))
        if 0 <= mn < mx <= 65535:
            return (mn, mx)
    except:
        pass
    return None

def save_calib(min_raw, max_raw):
    if min_raw > max_raw:
        min_raw, max_raw = max_raw, min_raw
    data = {"min_raw": int(min_raw), "max_raw": int(max_raw)}
    with open(CALIB_FILE, "w") as f:
        ujson.dump(data, f)

def map_to_percent(raw, mn, mx):
    if mn == mx:
        return 0
    if raw < mn:
        raw = mn
    if raw > mx:
        raw = mx
    return int((raw - mn) * 100 / (mx - mn))

# ---------------------------------------------------
# WIFI + THINGSPEAK
# ---------------------------------------------------

def wifi_connect(ssid, password, timeout_ms=20000):
    tft.fill(IDX_BLACK)
    utext_color(10, 10, "Connecting Wi-Fi...", IDX_WHITE)
    text(ssid, 10, 35, IDX_CYAN)
    draw_progress(10, 65, 220, 16, 0)
    tft.show()

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    t0 = utime.ticks_ms()
    step = 0
    while not wlan.isconnected():
        step = (step + 4) % 101
        draw_progress(10, 65, 220, 16, step)
        tft.show()
        time.sleep(0.1)
        if utime.ticks_diff(utime.ticks_ms(), t0) > timeout_ms:
            return wlan, False

    for p in range(step, 101, 6):
        draw_progress(10, 65, 220, 16, p)
        tft.show()
        time.sleep(0.02)

    # Turn LED on when Wi-Fi OK
    # try:
     #    led_sys = Pin("LED", Pin.OUT)
      #   led_sys.on()
    # except:
     #    pass

    return wlan, True


def send_to_thingspeak(level_pct, temp=None, hum=None):
    """Send data to ThingSpeak fields."""
    try:
        params = (
            f"?api_key={THINGSPEAK_API_KEY}"
            f"&field1={temp:.1f}"
            f"&field2={hum:.1f}"
            f"&field3={level_pct}"
        )
        url = THINGSPEAK_URL + params
        r = urequests.get(url)
        txt = r.text.strip()
        ok = txt.isdigit() and int(txt) > 0
        r.close()
        return ok, txt
    except Exception as e:
        return False, str(e)

# ---------------------------------------------------
# NEW: LED CONTROL FROM BACKEND
# ---------------------------------------------------

def update_pump_from_server():
    """Poll backend for LED/pump state and update GPIO output."""
    try:
        r = urequests.get(PUMP_CONTROL_URL)
        state = r.text.strip()
        r.close()
        if state == "on":
            pump.value(1)
            PUMP_LED.value(1)  # built-in LED on

        else:
            pump.value(0)
            PUMP_LED.value(0)  # built-in LED off
            
    except Exception as e:
        print("LED control error:", e)

# ---------------------------------------------------
# DHT READ
# ---------------------------------------------------

def read_dht():
    """Return (temp, humidity, ok)."""
    try:
        sensor.measure()
        t = sensor.temperature()
        h = sensor.humidity()
        if (t < -40 or t > 85) or (h < 0 or h > 100):
            return None, None, False
        return t, h, True
    except:
        return None, None, False

# ---------------------------------------------------
# SCREENS
# ---------------------------------------------------

def screen_menu(has_saved):
    tft.fill(IDX_BLACK)
    utext_color(10, 10, "Water Level", IDX_CYAN)
    y = 60
    if has_saved:
        utext(10, y, "Select:")
        y += 30
        utext_color(10, y, "1) Calibrate sensor", IDX_WHITE)
        y += 30
        utext_color(10, y, "2) Continue with saved", IDX_WHITE)
        y += 30
        text("Rotate knob to choose", 10, y, IDX_GREY)
        text("then press OK", 10, y + 15, IDX_GREY)
    else:
        utext_color(10, y, "No saved calibration", IDX_RED)
        y += 30
        utext_color(10, y, "1) Calibrate sensor", IDX_WHITE)
        y += 30
        text("Press OK to start calibration", 10, y, IDX_GREY)
    tft.show()

def draw_selector(sel):
    fill_rect(0, 80, 8, 80, IDX_BLACK)
    y = 90 if sel == 0 else 120
    text(">", 0, y, IDX_GREEN)
    tft.show()

def screen_prompt(line1, line2=""):
    tft.fill(IDX_BLACK)
    utext_color(10, 20, line1, IDX_WHITE)
    if line2:
        text(line2, 10, 100, IDX_GREY)
    utext_color(10, 260, "Press OK", IDX_CYAN)
    tft.show()

def screen_level(pct, wifi_ok, last_time_str, last_ok, next_secs,
                 last_info, temp, hum, dht_ok):
    tft.fill(IDX_BLACK)
    utext_color(10, 10, "Water Level:", IDX_CYAN)

    text_scaled("{:3d}%".format(pct), 145, 15, IDX_CYAN, scale=2)

    draw_progress(10, 120, 220, 18, pct, fg=IDX_BLUE,
                  bg=IDX_GREY, border=IDX_WHITE)

    if pct <= LOW_WARN:
        utext_color(10, 150, "Warning: Empty", IDX_RED)
    elif pct >= HIGH_WARN:
        utext_color(10, 150, "Warning: Full", IDX_RED)
    else:
        utext_color(10, 150, "OK", IDX_CYAN)

    text("Wi-Fi: {}".format("OK" if wifi_ok else "OFF"),
         10, 240, IDX_GREY)

    if last_time_str:
        text("Last TS: {} ({})".format(last_time_str,
              "OK" if last_ok else "Fail"),
              10, 200,
              IDX_GREEN if last_ok else IDX_RED)
    else:
        text("Last TS: --:--:--", 10, 200, IDX_GREY)

    text("Next in: {}s".format(next_secs),
         10, 220, IDX_GREY)

    if dht_ok:
        text("Temp: {:.0f}C".format(temp or 0), 10, 95, IDX_GREEN)
        text("Hum: {:.0f}%".format(hum or 0), 130, 95, IDX_CYAN)
    else:
        text("Temp/Hum: --", 10, 95, IDX_GREY)

    text("Hold OK 2s to re-calibrate", 10, 260, IDX_GREEN)
    tft.show()

# ---------------------------------------------------
# CALIBRATION
# ---------------------------------------------------

def do_calibration():
    screen_prompt("Set probe to TOP (100%)",
                  "Move arm to highest level")
    wait_ok()
    top = read_pot_raw()

    screen_prompt("Set probe to BOTTOM (0%)",
                  "Move arm to lowest level")
    wait_ok()
    bottom = read_pot_raw()

    min_raw = min(top, bottom)
    max_raw = max(top, bottom)

    if max_raw - min_raw < 256:
        screen_prompt("Calibration span too small!",
                      "Move further and press OK")
        wait_ok()
        return do_calibration()

    save_calib(min_raw, max_raw)
    screen_prompt("Calibration saved!",
                  f"min={min_raw} max={max_raw}")
    wait_ok()
    return (min_raw, max_raw)

# ---------------------------------------------------
# MAIN LOOP
# ---------------------------------------------------

def fmt_time_now():
    t = utime.localtime()
    return "{:02d}:{:02d}:{:02d}".format(t[3], t[4], t[5])

def main():
    wlan, wifi_ok = wifi_connect(SSID, PASS)

    tft.fill(IDX_BLACK)
    if wifi_ok:
        ip = wlan.ifconfig()[0]
        utext_color(10, 15, "Wi-Fi OK", IDX_GREEN)
        text("IP: " + ip, 10, 40, IDX_CYAN)
    else:
        utext_color(10, 15, "Wi-Fi FAILED", IDX_RED)
        text("ThingSpeak disabled", 10, 40, IDX_GREY)
    tft.show()
    time.sleep(1)

    # Menu
    calib = load_calib()
    screen_menu(has_saved=(calib is not None))

    if calib is None:
        calib = do_calibration()
    else:
        while True:
            raw = read_pot_raw()
            sel = 0 if (raw < 32768) else 1
            draw_selector(sel)
            if btn_ok.value() == 0:
                wait_ok()
                if sel == 0:
                    calib = do_calibration()
                break
            time.sleep_ms(80)

    min_raw, max_raw = calib

    last_send_ms = 0
    last_send_ok = False
    last_send_info = ""
    last_send_time_str = ""

    while True:
        raw = read_pot_raw()
        pct = map_to_percent(raw, min_raw, max_raw)

        temp, hum, dht_ok = read_dht()

        # --------------------------------------
        # NEW: Update LED/pump state from backend
        # --------------------------------------
        update_pump_from_server()

        now = utime.ticks_ms()
        elapsed = utime.ticks_diff(now, last_send_ms)
        remain_ms = TS_MIN_INTERVAL_MS - elapsed \
                    if last_send_ms != 0 else 0
        next_secs = remain_ms // 1000 if remain_ms > 0 else 0

        screen_level(pct, wifi_ok, last_send_time_str,
                     last_send_ok, next_secs,
                     last_send_info, temp, hum, dht_ok)

        if ok_long_pressed(2000):
            calib = do_calibration()
            min_raw, max_raw = calib

        if wifi_ok and (last_send_ms == 0 or
                        utime.ticks_diff(now, last_send_ms) >= TS_MIN_INTERVAL_MS):

            ok, info = send_to_thingspeak(pct, temp or 0, hum or 0)
            last_send_ok = ok
            last_send_info = info
            last_send_time_str = fmt_time_now()
            last_send_ms = now

            screen_level(pct, wifi_ok, last_send_time_str,
                         last_send_ok, 0, last_send_info,
                         temp, hum, dht_ok)

        time.sleep(0.2)


main()
