cmake_minimum_required(VERSION 3.16)

# 设置 ESP-IDF 路径（可选，如果设置了 IDF_PATH 环境变量则不需要）
# set(IDF_PATH "E:/Espressif/Espressif/frameworks/esp-idf-v5.4.3")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(esp32_catcam)