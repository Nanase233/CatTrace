# ESP32-S3-EYE 猫咪监控摄像头

## 📋 硬件要求

- ESP32-S3-EYE 开发板
- OV2640 摄像头模块（通常已集成）
- USB-C 数据线
- 5V 电源（可通过 USB 供电）

## 🔧 软件准备

### 1. 安装 Arduino IDE
- 下载地址：https://www.arduino.cc/en/software
- 推荐版本：Arduino IDE 2.x

### 2. 添加 ESP32 开发板支持
在 Arduino IDE 中：
1. 打开 `文件` -> `偏好设置`
2. 在 "附加开发板管理器网址" 中添加：
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. 打开 `工具` -> `开发板` -> `开发板管理器`
4. 搜索 "ESP32" 并安装 "esp32 by Espressif Systems"

### 3. 安装所需库
在 Arduino IDE 中：
1. 打开 `工具` -> `管理库`
2. 安装以下库：
   - `esp32-camera` by Espressif
   - `ArduinoJson` by Benoit Blanchon (版本 6.x 或 7.x)

## ⚙️ 代码配置

打开 `esp32_catcam.ino`，修改以下配置：

```cpp
// ========== WiFi 配置 ==========
const char* ssid = "你的 WiFi 名称";      // 修改为你的 WiFi
const char* password = "你的 WiFi 密码";  // 修改为你的密码

// ========== 服务器配置 ==========
const char* serverHost = "192.168.1.100";  // 修改为你的服务器 IP
const int serverPort = 5000;
const char* serverPath = "/api/camera-upload";

// ========== 拍摄配置 ==========
const int photoInterval = 300;  // 拍摄间隔（秒），300 = 5 分钟
```

## 📤 上传代码

1. 连接 ESP32-S3-EYE 到电脑
2. 在 Arduino IDE 中选择开发板：
   - `工具` -> `开发板` -> `ESP32 Arduino` -> `ESP32S3 Dev Module`
3. 选择正确的端口：
   - `工具` -> `端口` -> 选择对应的 COM 端口
4. 上传设置：
   - `工具` -> `Flash Size` -> `16MB` (或根据实际)
   - `工具` -> `PSRAM` -> `OPI PSRAM`
5. 点击上传按钮

## 🚀 运行

1. 上传完成后，打开串口监视器（波特率 115200）
2. 观察输出日志
3. 确认 WiFi 连接成功
4. 确认摄像头初始化成功
5. 等待首次拍摄（根据 photoInterval 设置）

## 📡 网络配置

### 局域网部署
如果 ESP32 和服务器在同一局域网：
- serverHost 使用服务器的局域网 IP（如 192.168.1.100）

### 远程部署
如果需要从外网访问：
- 使用域名或公网 IP
- 确保端口 5000 已开放
- 考虑使用 HTTPS

## 🐛 故障排查

### WiFi 连接失败
- 检查 WiFi 名称和密码是否正确
- 确认 ESP32 在 WiFi 信号范围内
- 尝试重启 ESP32

### 摄像头初始化失败
- 检查摄像头模块是否正确连接
- 确认引脚配置与硬件匹配
- 尝试重新插拔摄像头

### 照片上传失败
- 检查服务器是否正常运行
- 确认服务器 IP 和端口正确
- 查看串口输出错误信息

## 📸 照片存储

上传的照片保存在：
```
项目猫-MVP/static/uploads/
```

文件名格式：`设备 ID_时间戳.jpg`

## 🔐 安全建议

1. 生产环境使用 HTTPS
2. 添加 API 认证机制
3. 限制上传频率防止滥用
4. 定期清理旧照片

## 📞 技术支持

遇到问题可以查看：
- ESP32 官方文档：https://docs.espressif.com/
- Arduino ESP32: https://github.com/espressif/arduino-esp32