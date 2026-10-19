# ESP32-S3-EYE 实时摄像头 + QMA7981 IMU

基于 ESP-IDF 的实时 MJPEG 视频流 + 加速度计数据采集。

## 🎯 功能

- 📹 **MJPEG 实时视频流** — 浏览器直接观看
- 📸 **单帧快照** — 一键截图下载
- 🎯 **QMA7981 加速度计** — I2C 读取 X/Y/Z 轴数据
- 🌐 **内置 Web UI** — 无需额外前端
- 📡 **JSON API** — 传感器数据接口
- 🔄 **WiFi 自动重连** — 断线自动恢复

## ⚠️ 硬件说明

| 外设 | 引脚 | 备注 |
|------|------|------|
| 摄像头 SCCB SDA | GPIO4 | 与 QMA7981 I2C SDA 共享 |
| 摄像头 SCCB SCL | GPIO5 | 与 QMA7981 I2C SCL 共享 |
| QMA7981 地址 | 0x12 | |
| SD 卡 CMD | GPIO38 | ⚠️ 与摄像头 D1 冲突 |
| SD 卡 CLK | GPIO39 | ⚠️ 与摄像头 D7 冲突 |
| SD 卡 D0 | GPIO40 | ⚠️ 摄像头与 SD 卡不能同时使用 |

## 📡 HTTP 接口

| 路径 | 说明 |
|------|------|
| `http://<IP>:8080/` | Web 控制界面 |
| `http://<IP>:8080/stream` | MJPEG 视频流 |
| `http://<IP>:8080/snapshot` | 单帧 JPEG |
| `http://<IP>:8080/api/sensors` | IMU JSON 数据 |
| `http://<IP>:8080/api/status` | 设备状态 |

## 🚀 快速开始

### 1. 配置 WiFi

编辑 `main/main.c`，修改：
```c
#define WIFI_SSID "你的WiFi"
#define WIFI_PASS "你的密码"
```

### 2. 设置 ESP-IDF 环境
```powershell
# Windows
. E:\Espressif\Espressif\frameworks\esp-idf-v5.4.3\export.bat
```

### 3. 编译烧录
```bash
cd esp32s3_realtime_camera
idf.py set-target esp32s3
idf.py build
idf.py -p COM3 flash monitor
```

### 4. 查看视频流

打开浏览器访问串口输出的 IP 地址（端口 8080）：
```
http://192.168.x.x:8080/stream
```

或在 Flask 前端的直播区嵌入：
```html
<img src="http://<ESP32-IP>:8080/stream" style="width:100%">
```

## 📂 项目结构

```
esp32s3_realtime_camera/
├── CMakeLists.txt
├── sdkconfig.defaults
├── main/
│   ├── CMakeLists.txt
│   ├── idf_component.yml   # esp32-camera 依赖
│   └── main.c              # 全部代码
└── README.md
```

## 🔧 环境要求

- ESP-IDF v5.0+
- Python 3.8+
- CMake 3.16+
- 4MB+ PSRAM（摄像头帧缓冲需要）

## 🔍 故障排除

| 问题 | 解决 |
|------|------|
| Camera init failed | 检查摄像头排线，确认 PSRAM 已启用 |
| WiFi 连不上 | 确认 SSID/密码，检查 2.4GHz 频段 |
| 视频卡顿 | 降低分辨率(QVGA)，提高 jpeg_quality 数值 |
| IMU 读不到 | 确认 QMA7981 焊接，检查 I2C 地址 |
| 内存不足 | 检查 sdkconfig.defaults 中 PSRAM 配置 |
