# ESP32-S3-EYE 快速开始指南

## 📦 开箱即用配置

> **注意**：当前配置已针对您的热点进行设置：
> - WiFi 名称：`yexuan`
> - WiFi 密码：`yexuan1231`
> - 服务器 IP：`192.168.137.1`（Windows 移动热点默认网关）
>
> 如需修改，请编辑 `esp32_catcam.ino` 文件中的配置部分。

### 步骤 1：确认 WiFi 配置
打开 `esp32_catcam.ino`，确认以下配置：

```cpp
// ========== WiFi 配置 ==========
const char* ssid = "yexuan";              // 热点名称
const char* password = "yexuan1231";      // 热点密码

// ========== 服务器配置 ==========
const char* serverHost = "192.168.137.1";  // Windows 移动热点默认网关 IP
```

**如需修改为自己的 WiFi：**
- 修改 `ssid` 为你的 WiFi 名称
- 修改 `password` 为你的 WiFi 密码
- 修改 `serverHost` 为你运行 `app.py` 的电脑 IP

**如何获取电脑 IP？**
- Windows: 打开命令提示符，输入 `ipconfig`
- Mac/Linux: 打开终端，输入 `ifconfig` 或 `ip addr`
- 查找 "IPv4 地址" 或 "inet"

### 步骤 2：启动服务器
在项目猫-MVP 目录下运行：
```bash
cd d:\项目\项目猫-MVP
python app.py
```

确保看到类似输出：
```
 * Running on http://0.0.0.0:5000
 * Press CTRL+C to quit
```

### 步骤 3：上传代码到 ESP32
1. 用 USB 线连接 ESP32-S3-EYE 到电脑
2. 在 Arduino IDE 中打开 `esp32_catcam.ino`
3. 选择开发板：`ESP32S3 Dev Module`
4. 选择正确的 COM 端口
5. 点击上传按钮

### 步骤 4：观察运行
1. 打开串口监视器（波特率 115200）
2. 等待 WiFi 连接成功
3. 等待 NTP 时间同步成功
4. 等待首次拍摄和上传

## 🎯 预期输出

串口监视器应显示：
```
========== 项目猫 - ESP32 摄像头 ==========
设备 ID: ESP32_CATCAM_001
位置：猫咪喂食器
正在连接 WiFi: 你的 WiFi 名称
................................WiFi 连接成功!
IP 地址：192.168.1.xxx
正在同步 NTP 时间...
NTP 时间同步成功!
当前时间：2026-06-24 14:30:00
摄像头初始化成功
系统就绪，开始监控...
拍摄间隔：300 秒

--- 开始拍摄 ---
时间戳：20260624_143005
照片大小：123456 字节
正在上传照片...
上传响应：200 - {"success": true, ...}
第 1 张照片上传成功
--- 拍摄完成 ---
```

## ⚡ 常见问题

### Q: 找不到 COM 端口？
A: 确保安装了 CH340/CP210x 驱动，尝试更换 USB 线

### Q: 上传失败？
A: 按住 ESP32 的 BOOT 键，点击 RESET 键，然后重试上传

### Q: WiFi 连接失败？
A: 
- 确认 WiFi 名称和密码正确
- ESP32 只支持 2.4GHz WiFi，不支持 5GHz
- 确保 WiFi 信号强度足够

### Q: 服务器收不到照片？
A:
- 确认服务器正在运行（看到 "Running on..." 输出）
- 确认防火墙允许 5000 端口
- 检查服务器 IP 是否正确

## 🔗 相关文档

- [README.md](README.md) - 完整文档
- [esp32_catcam.ino](esp32_catcam.ino) - 源代码