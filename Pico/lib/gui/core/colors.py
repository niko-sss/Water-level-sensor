# /lib/gui/core/colors.py
# Минимальные RGB565-цвета без зависимостей от color_setup/SSD.

def rgb565(r, g, b):
    # Конвертация 8-бит RGB в 16-бит RGB565 (int)
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | ((b & 0xF8) >> 3)

# Базовые цвета
BLACK = 0
WHITE = rgb565(255, 255, 255)
RED   = rgb565(255, 0, 0)
GREEN = rgb565(0, 255, 0)
BLUE  = rgb565(0, 0, 255)
CYAN  = rgb565(0, 200, 200)
GREY  = rgb565(120, 120, 120)

# Ничего больше не экспортируем. create_color и LUT тут не нужны.
