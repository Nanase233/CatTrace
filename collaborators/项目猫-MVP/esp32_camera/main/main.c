/*
 * 项目猫 - ESP32-S3-EYE 猫咪监控摄像头
 * 功能：定时拍摄并上传照片到服务器
 * 增强功能：NTP 时间同步、API 认证、看门狗、低功耗
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <time.h>
#include <sys/time.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"

#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_task_wdt.h"

#include "nvs_flash.h"
#include "esp_http_client.h"

#include "esp_camera.h"
#include "lwip/err.h"
#include "lwip/sys.h"

// ========== WiFi 配置 ==========
#define WIFI_SSID         "yexuan"
#define WIFI_PASS         "yexuan1231"

// ========== 服务器配置 ==========
#define SERVER_HOST       "192.168.137.1"
#define SERVER_PORT       5000
#define SERVER_PATH       "/api/camera-upload"
#define API_TOKEN         "your_api_token_here"

// ========== NTP 时间配置 ==========
#define NTP_SERVER        "pool.ntp.org"
#define GMT_OFFSET_SEC    (8 * 3600)  // 中国时区 GMT+8
#define DAYLIGHT_OFFSET_SEC 0

// ========== 拍摄配置 ==========
#define PHOTO_INTERVAL_SEC 300  // 5 分钟
#define CAMERA_RESOLUTION FRAMESIZE_SVGA

// ========== 设备配置 ==========
#define DEVICE_ID         "ESP32_CATCAM_001"
#define DEVICE_LOCATION   "猫咪喂食器"

// ========== 看门狗配置 ==========
#define WDT_TIMEOUT_SEC   60

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

// ========== 全局变量 ==========
static const char *TAG = "catcam";
static int photo_count = 0;
static bool time_synced = false;
static int reconnect_attempts = 0;
static const int max_reconnect_attempts = 5;
static unsigned long last_photo_time = 0;

// WiFi 事件组
static EventGroupHandle_t wifi_event_group;
static const int WIFI_CONNECTED_BIT = BIT0;

// ========== 摄像头初始化 ==========
static esp_err_t init_camera(void) {
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
    config.frame_size = CAMERA_RESOLUTION;
    config.jpeg_quality = 12;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;

    esp_err_t err = esp_camera_init(&config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "摄像头初始化失败：0x%x", err);
        return err;
    }

    // 优化图像质量
    sensor_t *s = esp_camera_sensor_get();
    if (s) {
        s->set_brightness(s, 0);
        s->set_contrast(s, 1);
        s->set_saturation(s, 1);
        s->set_whitebal(s, 1);
        s->set_gainceiling(s, (gainceiling_t)1);
    }

    ESP_LOGI(TAG, "摄像头初始化成功");
    return ESP_OK;
}

// ========== NTP 时间同步 ==========
static void obtain_time(void) {
    ESP_LOGI(TAG, "正在同步 NTP 时间...");
    
    struct timeval tv;
    gettimeofday(&tv, NULL);
    
    esp_netif_sntp_config_t sntp_config = ESP_NETIF_SNTP_DEFAULT_CONFIG(NTP_SERVER);
    esp_netif_sntp_init(&sntp_config);
    
    // 等待时间同步
    time_t now = 0;
    struct tm timeinfo = { 0 };
    int retry = 0;
    const int retry_count = 10;
    
    while (esp_netif_sntp_sync_wait(2000 / portTICK_PERIOD_MS) != ESP_OK && ++retry < retry_count) {
        ESP_LOGI(TAG, "等待 NTP 同步...");
    }
    
    time(&now);
    localtime_r(&now, &timeinfo);
    
    if (timeinfo.tm_year > (2020 - 1900)) {
        time_synced = true;
        ESP_LOGI(TAG, "NTP 时间同步成功!");
        ESP_LOGI(TAG, "当前时间：%04d-%02d-%02d %02d:%02d:%02d",
                 timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
                 timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
    } else {
        time_synced = false;
        ESP_LOGW(TAG, "NTP 时间同步失败");
    }
}

// ========== 获取时间戳 ==========
static void get_timestamp(char *buffer, size_t size) {
    time_t now;
    struct tm timeinfo;
    time(&now);
    localtime_r(&now, &timeinfo);
    
    if (timeinfo.tm_year > (2020 - 1900)) {
        snprintf(buffer, size, "%04d%02d%02d_%02d%02d%02d",
                 timeinfo.tm_year + 1900, timeinfo.tm_mon + 1, timeinfo.tm_mday,
                 timeinfo.tm_hour, timeinfo.tm_min, timeinfo.tm_sec);
    } else {
        snprintf(buffer, size, "%lu", (unsigned long)now);
    }
}

// ========== WiFi 事件处理 ==========
static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data) {
    if (event_base == WIFI_EVENT) {
        switch (event_id) {
            case WIFI_EVENT_STA_START:
                esp_wifi_connect();
                break;
            case WIFI_EVENT_STA_DISCONNECTED:
                if (reconnect_attempts < max_reconnect_attempts) {
                    esp_wifi_connect();
                    reconnect_attempts++;
                } else {
                    ESP_LOGE(TAG, "达到最大重连次数");
                }
                xEventGroupClearBits(wifi_event_group, WIFI_CONNECTED_BIT);
                break;
            default:
                break;
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *) event_data;
        ESP_LOGI(TAG, "WiFi 连接成功，IP: " IPSTR, IP2STR(&event->ip_info.ip));
        reconnect_attempts = 0;
        xEventGroupSetBits(wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

// ========== WiFi 初始化 ==========
static void wifi_init_sta(void) {
    wifi_event_group = xEventGroupCreate();
    
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        NULL));
    
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = "",
            .password = "",
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    strncpy((char *)wifi_config.sta.ssid, WIFI_SSID, sizeof(wifi_config.sta.ssid) - 1);
    strncpy((char *)wifi_config.sta.password, WIFI_PASS, sizeof(wifi_config.sta.password) - 1);
    
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    ESP_LOGI(TAG, "WiFi 初始化完成");
}

// ========== HTTP 上传回调 ==========
static esp_err_t http_event_handler(esp_http_client_event_t *evt) {
    static char *post_data = NULL;
    static int post_data_len = 0;
    
    switch (evt->event_id) {
        case HTTP_EVENT_ERROR:
            ESP_LOGD(TAG, "HTTP 错误");
            break;
        case HTTP_EVENT_ON_CONNECTED:
            ESP_LOGD(TAG, "HTTP 已连接");
            break;
        case HTTP_EVENT_HEADER_SENT:
            ESP_LOGD(TAG, "HTTP 头部已发送");
            break;
        case HTTP_EVENT_ON_HEADER:
            ESP_LOGD(TAG, "HTTP 头部接收：%s: %s", evt->header_key, evt->header_value);
            break;
        case HTTP_EVENT_ON_DATA:
            ESP_LOGD(TAG, "HTTP 数据接收：%.*s", evt->data_len, (char *)evt->data);
            break;
        case HTTP_EVENT_ON_FINISH:
            ESP_LOGD(TAG, "HTTP 完成");
            break;
        case HTTP_EVENT_DISCONNECTED:
            ESP_LOGD(TAG, "HTTP 断开连接");
            break;
        default:
            break;
    }
    return ESP_OK;
}

// ========== 拍摄照片并上传 ==========
static bool upload_photo(void) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
        ESP_LOGE(TAG, "获取摄像头帧失败");
        return false;
    }

    ESP_LOGI(TAG, "照片大小：%d 字节", fb->len);

    // 生成时间戳文件名
    char timestamp[32];
    get_timestamp(timestamp);
    char filename[64];
    snprintf(filename, sizeof(filename), "%s_%s.jpg", DEVICE_ID, timestamp);

    // 构建 URL
    char url[128];
    snprintf(url, sizeof(url), "http://%s:%d%s", SERVER_HOST, SERVER_PORT, SERVER_PATH);

    // 创建 HTTP 客户端
    esp_http_client_config_t config = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .event_handler = http_event_handler,
        .buffer_size = 1024,
        .timeout_ms = 10000,
    };
    
    esp_http_client_handle_t client = esp_http_client_init(&config);
    
    // 生成边界
    char boundary[64];
    snprintf(boundary, sizeof(boundary), "----ESP32Boundary%08X", (unsigned int)esp_random());
    
    // 构建 Content-Type
    char content_type[128];
    snprintf(content_type, sizeof(content_type), "multipart/form-data; boundary=%s", boundary);
    esp_http_client_set_header(client, "Content-Type", content_type);
    
    // 添加设备信息头部
    esp_http_client_set_header(client, "X-Device-ID", DEVICE_ID);
    
    // 添加 API Token 认证
    if (strlen(API_TOKEN) > 0 && strcmp(API_TOKEN, "your_api_token_here") != 0) {
        char auth_header[128];
        snprintf(auth_header, sizeof(auth_header), "Bearer %s", API_TOKEN);
        esp_http_client_set_header(client, "Authorization", auth_header);
    }
    
    // 构建 multipart 数据
    char header[512];
    int header_len = snprintf(header, sizeof(header),
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n"
        "%s\r\n"
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"location\"\r\n\r\n"
        "%s\r\n"
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"timestamp\"\r\n\r\n"
        "%s\r\n"
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"photo\"; filename=\"%s\"\r\n"
        "Content-Type: image/jpeg\r\n\r\n",
        boundary, DEVICE_ID,
        boundary, DEVICE_LOCATION,
        boundary, timestamp,
        boundary, filename);
    
    char footer[64];
    int footer_len = snprintf(footer, sizeof(footer), "\r\n--%s--\r\n", boundary);
    
    // 设置 post 字段
    esp_http_client_set_post_field(client, header, header_len);
    
    ESP_LOGI(TAG, "正在上传照片...");
    
    esp_err_t err = esp_http_client_perform(client);
    
    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(client);
        ESP_LOGI(TAG, "HTTP 状态码：%d", status);
        
        if (status == 200) {
            photo_count++;
            ESP_LOGI(TAG, "第 %d 张照片上传成功", photo_count);
            esp_camera_fb_return(fb);
            esp_http_client_cleanup(client);
            return true;
        }
    } else {
        ESP_LOGE(TAG, "HTTP 请求失败：0x%x", err);
    }
    
    esp_camera_fb_return(fb);
    esp_http_client_cleanup(client);
    return false;
}

// ========== 主任务 ==========
static void catcam_task(void *pvParameter) {
    // 等待 WiFi 连接
    xEventGroupWaitBits(wifi_event_group, WIFI_CONNECTED_BIT, pdFALSE, pdTRUE, portMAX_DELAY);
    
    // 同步时间
    obtain_time();
    
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t interval_ticks = pdMS_TO_TICKS(PHOTO_INTERVAL_SEC * 1000);
    
    while (1) {
        // 检查 WiFi 连接
        if (xEventGroupGetBits(wifi_event_group) & WIFI_CONNECTED_BIT) {
            ESP_LOGI(TAG, "--- 开始拍摄 ---");
            
            // 拍摄并上传
            if (upload_photo()) {
                ESP_LOGI(TAG, "--- 拍摄完成 ---");
            } else {
                ESP_LOGE(TAG, "--- 拍摄失败 ---");
            }
        } else {
            ESP_LOGW(TAG, "WiFi 未连接");
            // 尝试重新同步时间
            obtain_time();
        }
        
        // 等待下一个周期
        vTaskDelayUntil(&last_wake_time, interval_ticks);
    }
}

// ========== 应用程序入口 ==========
void app_main(void) {
    ESP_LOGI(TAG, "========== 项目猫 - ESP32 摄像头 ==========");
    ESP_LOGI(TAG, "设备 ID: %s", DEVICE_ID);
    ESP_LOGI(TAG, "位置：%s", DEVICE_LOCATION);
    
    // 初始化 NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS 分区已满，擦除并重新初始化");
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    // 初始化看门狗
    esp_task_wdt_init(WDT_TIMEOUT_SEC, true);
    esp_task_wdt_add(NULL);
    
    // 初始化摄像头
    ESP_ERROR_CHECK(init_camera());
    
    // 初始化 WiFi
    wifi_init_sta();
    
    // 创建主任务
    xTaskCreatePinnedToCore(&catcam_task, "catcam_task", 4096, NULL, 5, NULL, 1);
    
    ESP_LOGI(TAG, "系统就绪，开始监控...");
}
