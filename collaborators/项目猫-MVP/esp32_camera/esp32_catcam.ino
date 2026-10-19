/*
 * 项目猫 - ESP32-S3-EYE 猫咪监控摄像头
 * 功能：定时拍摄并上传照片到服务器
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <esp_camera.h>
#include <ArduinoJson.h>

// ========== WiFi 配置 ==========
const char* ssid = "你的 WiFi 名称";
const char* password = "你的 WiFi 密码";

// ========== 服务器配置 ==========
const char* serverHost = "你的服务器 IP 或域名";
const int serverPort = 5000;
const char* serverPath = "/api/camera-upload";

// ========== 拍摄配置 ==========
const int photoInterval = 300;  // 拍摄间隔（秒），300 = 5 分钟
const int cameraResolution = OV2640;  // 摄像头分辨率

// ========== 全局变量 ==========
unsigned long lastPhotoTime = 0;
int photoCount = 0;

// ========== 摄像头引脚配置 (ESP32-S3-EYE) ==========
#define PWDN_GPIO_NUM     -1
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM     15
#define SIOD_GPIO_NUM     4
#define SIOC_GPIO_NUM     5

#define Y9_GPIO_NUM       39
#define Y8_GPIO_NUM       41
#define Y7_GPIO_NUM       42
#define Y6_GPIO_NUM       12
#define Y5_GPIO_NUM       3
#define Y4_GPIO_NUM       14
#define Y3_GPIO_NUM       38
#define Y2_GPIO_NUM       10
#define VSYNC_GPIO_NUM    21
#define HREF_GPIO_NUM     37
#define PCLK_GPIO_NUM     11

// ========== 摄像头初始化 ==========
void initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_SVGA;  // 800x600
  config.jpeg_quality = 12;
  config.fb_count = 2;

  // 初始化摄像头
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("摄像头初始化失败：0x%x\n", err);
    return;
  }

  Serial.println("摄像头初始化成功");
}

// ========== WiFi 连接 ==========
void connectWiFi() {
  Serial.print("正在连接 WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi 连接成功!");
    Serial.print("IP 地址：");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi 连接失败!");
  }
}

// ========== 拍摄照片并上传 ==========
bool uploadPhoto() {
  // 获取摄像头帧
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("获取摄像头帧失败");
    return false;
  }

  Serial.printf("照片大小：%d 字节\n", fb->len);

  // 构建服务器 URL
  String serverURL = String("http://") + serverHost + ":" + String(serverPort) + serverPath;
  
  // 创建 HTTP 客户端
  HTTPClient http;
  http.begin(serverURL);
  http.addHeader("Content-Type", "multipart/form-data");
  
  // 添加设备信息
  String boundary = "----WebKitFormBoundary" + String(random(0x10000000, 0x7FFFFFFF), HEX);
  
  // 构建 multipart 数据
  String body = "";
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n";
  body += "ESP32_CATCAM_001\r\n";
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"location\"\r\n\r\n";
  body += "猫咪喂食器\r\n";
  body += "--" + boundary + "\r\n";
  body += "Content-Disposition: form-data; name=\"photo\"; filename=\"cat.jpg\"\r\n";
  body += "Content-Type: image/jpeg\r\n\r\n";
  
  // 发送请求
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);
  
  // 发送头部
  int httpCode = http.POST(fb->buf, fb->len);
  
  if (httpCode > 0) {
    String payload = http.getString();
    Serial.printf("上传响应：%d - %s\n", httpCode, payload.c_str());
    
    if (httpCode == 200) {
      photoCount++;
      Serial.printf("第 %d 张照片上传成功\n", photoCount);
    }
  } else {
    Serial.printf("上传失败：%d - %s\n", httpCode, http.errorToString(httpCode).c_str());
  }
  
  http.end();
  
  // 释放帧缓冲区
  esp_camera_fb_return(fb);
  
  return httpCode == 200;
}

// ========== LED 控制 ==========
void blinkLED(int times, int interval = 100) {
  for (int i = 0; i < times; i++) {
    digitalWrite(2, HIGH);
    delay(interval);
    digitalWrite(2, LOW);
    delay(interval);
  }
}

// ========== 设置 ==========
void setup() {
  // 初始化串口
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n========== 项目猫 - ESP32 摄像头 ==========");
  
  // 初始化 LED
  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);
  
  // 连接 WiFi
  connectWiFi();
  
  // 初始化摄像头
  initCamera();
  
  // 启动指示灯闪烁
  blinkLED(3, 200);
  
  Serial.println("系统就绪，开始监控...");
  Serial.printf("拍摄间隔：%d 秒\n", photoInterval);
}

// ========== 主循环 ==========
void loop() {
  unsigned long currentTime = millis();
  unsigned long elapsedSeconds = currentTime / 1000;
  
  // 检查是否需要拍摄
  if (elapsedSeconds - lastPhotoTime >= photoInterval) {
    lastPhotoTime = elapsedSeconds;
    
    Serial.println("\n--- 开始拍摄 ---");
    
    // 拍摄并上传
    if (uploadPhoto()) {
      blinkLED(1, 100);  // 成功闪烁
    } else {
      blinkLED(3, 200);  // 失败闪烁
    }
    
    Serial.println("--- 拍摄完成 ---\n");
  }
  
  // 保持 WiFi 连接
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
  }
  
  delay(1000);
}