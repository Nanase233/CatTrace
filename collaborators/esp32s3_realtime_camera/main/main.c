/*
 * ESP32-S3-EYE 实时摄像头 + QMA7981 IMU
 * MJPEG Stream + 加速度计
 * /stream=MJPEG  /snapshot=JPEG  /api/sensors=JSON
 * ⚠️ SD卡引脚与摄像头冲突不能同时使用
 */
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "freertos/semphr.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_http_server.h"
#include "nvs_flash.h"
#include "driver/i2c.h"
#include "esp_camera.h"

static const char *TAG = "cam";
// ==== 配置 ====
#define WIFI_SSID "yexuan"
#define WIFI_PASS "yexuan1231"
#define MAX_RETRY 10
#define HTTP_PORT 8080
#define CAM_SIOD  4
#define CAM_SIOC  5
#define I2C_NUM0  I2C_NUM_0
#define QMA_ADDR  0x12
// ==== 全局 ====
static EventGroupHandle_t s_weg;
static const int WIFI_BIT = BIT0;
static int s_retry = 0;
static char s_ip[16] = "0.0.0.0";
typedef struct { int16_t rx,ry,rz; float gx,gy,gz; bool ok; } imu_t;
static imu_t s_imu = {0};
static SemaphoreHandle_t s_mtx;
static uint32_t s_fcnt = 0;
static int64_t s_t0 = 0;
// ==== I2C ====
static esp_err_t i2c_init(void) {
    i2c_config_t c = {.mode=I2C_MODE_MASTER,.sda_io_num=CAM_SIOD,
        .scl_io_num=CAM_SIOC,.sda_pullup_en=1,.scl_pullup_en=1,
        .master.clk_speed=400000};
    ESP_ERROR_CHECK(i2c_param_config(I2C_NUM0,&c));
    return i2c_driver_install(I2C_NUM0,c.mode,0,0,0);
}
static esp_err_t qw(uint8_t r,uint8_t v) {
    i2c_cmd_handle_t c=i2c_cmd_link_create();
    i2c_master_start(c);
    i2c_master_write_byte(c,(QMA_ADDR<<1)|0,true);
    i2c_master_write_byte(c,r,true);
    i2c_master_write_byte(c,v,true);
    i2c_master_stop(c);
    esp_err_t e=i2c_master_cmd_begin(I2C_NUM0,c,pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(c); return e;
}
static esp_err_t qr(uint8_t r,uint8_t *d,size_t n) {
    i2c_cmd_handle_t c=i2c_cmd_link_create();
    i2c_master_start(c);
    i2c_master_write_byte(c,(QMA_ADDR<<1)|0,true);
    i2c_master_write_byte(c,r,true);
    i2c_master_start(c);
    i2c_master_write_byte(c,(QMA_ADDR<<1)|1,true);
    if(n>1) i2c_master_read(c,d,n-1,I2C_MASTER_ACK);
    i2c_master_read_byte(c,d+n-1,I2C_MASTER_NACK);
    i2c_master_stop(c);
    esp_err_t e=i2c_master_cmd_begin(I2C_NUM0,c,pdMS_TO_TICKS(100));
    i2c_cmd_link_delete(c); return e;
}
static esp_err_t qma_init(void) {
    qw(0x11,0x80); vTaskDelay(pdMS_TO_TICKS(50));
    qw(0x11,0x01); vTaskDelay(pdMS_TO_TICKS(20));
    qw(0x0F,0x01); qw(0x10,0x02); vTaskDelay(pdMS_TO_TICKS(20));
    uint8_t id=0; qr(0x00,&id,1);
    ESP_LOGI(TAG,"QMA7981 ID=0x%02X",id);
    return (id==0x80)?ESP_OK:ESP_ERR_NOT_FOUND;
}
static esp_err_t qma_rd(imu_t *d) {
    uint8_t b[6]; esp_err_t e=qr(0x01,b,6);
    if(e) return e;
    d->rx=((int16_t)b[1]<<8)|(b[0]&0xF0);
    d->ry=((int16_t)b[3]<<8)|(b[2]&0xF0);
    d->rz=((int16_t)b[5]<<8)|(b[4]&0xF0);
    d->gx=d->rx/256.0f; d->gy=d->ry/256.0f; d->gz=d->rz/256.0f;
    d->ok=true; return ESP_OK;
}
static void imu_task(void *a) {
    TickType_t t=xTaskGetTickCount();
    while(1) { imu_t tmp={0};
        if(qma_rd(&tmp)==ESP_OK) {
            xSemaphoreTake(s_mtx,portMAX_DELAY);
            s_imu=tmp; xSemaphoreGive(s_mtx);
        } vTaskDelayUntil(&t,pdMS_TO_TICKS(100));
    }
}
// ==== Camera ====
static esp_err_t cam_init(void) {
    camera_config_t c={.pin_pwdn=-1,.pin_reset=-1,.pin_xclk=15,
        .pin_sccb_sda=CAM_SIOD,.pin_sccb_scl=CAM_SIOC,
        .pin_d7=39,.pin_d6=41,.pin_d5=42,.pin_d4=12,
        .pin_d3=3,.pin_d2=14,.pin_d1=38,.pin_d0=10,
        .pin_vsync=21,.pin_href=37,.pin_pclk=11,
        .xclk_freq_hz=20000000,.ledc_timer=LEDC_TIMER_0,
        .ledc_channel=LEDC_CHANNEL_0,.pixel_format=PIXFORMAT_JPEG,
        .frame_size=FRAMESIZE_SVGA,.jpeg_quality=12,.fb_count=2,
        .grab_mode=CAMERA_GRAB_LATEST,.fb_location=CAMERA_FB_IN_PSRAM};
    esp_err_t e=esp_camera_init(&c);
    if(e) { ESP_LOGE(TAG,"Cam fail 0x%x",e); return e; }
    sensor_t *s=esp_camera_sensor_get();
    if(s) { s->set_brightness(s,1);s->set_contrast(s,0);
        s->set_whitebal(s,1);s->set_aec2(s,1);
        s->set_gain_ctrl(s,1);s->set_gainceiling(s,(gainceiling_t)4); }
    ESP_LOGI(TAG,"Camera OK"); return ESP_OK;
}
// ==== WiFi ====
static void wev(void *a,esp_event_base_t b,int32_t id,void *d) {
    if(b==WIFI_EVENT&&id==WIFI_EVENT_STA_START) esp_wifi_connect();
    else if(b==WIFI_EVENT&&id==WIFI_EVENT_STA_DISCONNECTED) {
        if(s_retry<MAX_RETRY){esp_wifi_connect();s_retry++;}
    } else if(b==IP_EVENT&&id==IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *e=(ip_event_got_ip_t*)d;
        snprintf(s_ip,sizeof(s_ip),IPSTR,IP2STR(&e->ip_info.ip));
        ESP_LOGI(TAG,"IP=%s",s_ip); s_retry=0;
        xEventGroupSetBits(s_weg,WIFI_BIT);
    }
}
static void wifi_start(void) {
    s_weg=xEventGroupCreate();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    wifi_init_config_t c=WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&c));
    esp_event_handler_instance_t h1,h2;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,ESP_EVENT_ANY_ID,&wev,NULL,&h1));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,IP_EVENT_STA_GOT_IP,&wev,NULL,&h2));
    wifi_config_t wc={.sta={.ssid=WIFI_SSID,.password=WIFI_PASS,.threshold.authmode=WIFI_AUTH_WPA2_PSK}};
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA,&wc));
    ESP_ERROR_CHECK(esp_wifi_start());
    xEventGroupWaitBits(s_weg,WIFI_BIT,pdFALSE,pdTRUE,portMAX_DELAY);
}
// ==== HTTP Handlers ====
static const char INDEX_HTML[] =
"<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"UTF-8\">"
"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
"<title>ESP32-S3-EYE Camera</title>"
"<style>*{margin:0;padding:0;box-sizing:border-box}"
"body{font-family:sans-serif;background:#1a1a2e;color:#eee}"
".hd{background:linear-gradient(135deg,#667eea,#764ba2);padding:20px;text-align:center}"
".ct{max-width:900px;margin:20px auto;padding:0 16px}"
".vb{background:#16213e;border-radius:12px;overflow:hidden;margin-bottom:20px}"
".vb img{width:100%;display:block;min-height:200px;background:#000}"
".bar{display:flex;justify-content:space-between;padding:12px 16px;background:#0f3460}"
".bg{background:#e94560;color:#fff;padding:4px 12px;border-radius:20px;font-size:.85rem}"
".sg{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:20px}"
".sc{background:#16213e;border-radius:10px;padding:16px;text-align:center}"
".sc .v{font-size:1.6rem;font-weight:700;color:#667eea}"
".sc .l{font-size:.8rem;color:#aaa;margin-top:4px}"
".ib{background:#16213e;border-radius:10px;padding:16px;margin-bottom:20px}"
".ib h3{margin-bottom:12px;color:#667eea}"
".ig{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}"
".ii{background:#0f3460;border-radius:8px;padding:12px;text-align:center}"
".ii .ax{font-size:.75rem;color:#aaa}"
".ii .gv{font-size:1.2rem;font-weight:700}"
".br{display:flex;gap:10px;justify-content:center;margin-top:16px}"
"button{padding:10px 20px;border:none;border-radius:8px;color:#fff;font-weight:600;cursor:pointer}"
".bp{background:linear-gradient(135deg,#667eea,#764ba2)}"
".bs{background:#0f3460;border:1px solid #667eea}"
"</style></head><body>"
"<div class=\"hd\"><h1>ESP32-S3-EYE Camera</h1><p>MJPEG + QMA7981</p></div>"
"<div class=\"ct\">"
"<div class=\"vb\"><img id=\"s\" src=\"/stream\" onerror=\"setTimeout(()=>{this.src='/stream'},3000)\">"
"<div class=\"bar\"><span class=\"bg\" id=\"st\">LIVE</span><span id=\"fps\">--</span><span>800x600</span></div></div>"
"<div class=\"sg\">"
"<div class=\"sc\"><div class=\"v\" id=\"fc\">0</div><div class=\"l\">Frames</div></div>"
"<div class=\"sc\"><div class=\"v\" id=\"up\">0s</div><div class=\"l\">Uptime</div></div>"
"<div class=\"sc\"><div class=\"v\" id=\"hp\">--</div><div class=\"l\">Heap</div></div></div>"
"<div class=\"ib\"><h3>QMA7981 Accel</h3><div class=\"ig\">"
"<div class=\"ii\"><div class=\"ax\">X</div><div class=\"gv\" id=\"ix\">--</div></div>"
"<div class=\"ii\"><div class=\"ax\">Y</div><div class=\"gv\" id=\"iy\">--</div></div>"
"<div class=\"ii\"><div class=\"ax\">Z</div><div class=\"gv\" id=\"iz\">--</div></div>"
"</div></div>"
"<div class=\"br\">"
"<button class=\"bp\" onclick=\"location.reload()\">Refresh</button>"
"<button class=\"bs\" onclick=\"open('/snapshot')\">Snapshot</button></div></div>"
"<script>let fc=0,st=Date.now();"
"function poll(){fetch('/api/sensors').then(r=>r.json()).then(d=>{"
"if(d.imu&&d.imu.available){$('ix').textContent=d.imu.x_g.toFixed(3)+'g';"
"$('iy').textContent=d.imu.y_g.toFixed(3)+'g';"
"$('iz').textContent=d.imu.z_g.toFixed(3)+'g';}"
"if(d.status){$('hp').textContent=(d.status.free_heap/1024|0)+'KB';"
"$('fc').textContent=d.status.frame_count;fc=d.status.frame_count;}"
"}).catch(()=>{})}"
"function $(i){return document.getElementById(i)}"
"setInterval(poll,2000);"
"setInterval(()=>{let e=(Date.now()-st)/1000|0,m=e/60|0,s=e%60;"
"$('up').textContent=m>0?m+'m'+s+'s':s+'s';},1000);"
"poll();</script></body></html>";

static esp_err_t root_h(httpd_req_t *req) {
    httpd_resp_set_type(req,"text/html");
    httpd_resp_set_hdr(req,"Access-Control-Allow-Origin","*");
    httpd_resp_send(req,INDEX_HTML,sizeof(INDEX_HTML)-1);
    return ESP_OK;
}

static esp_err_t sensor_h(httpd_req_t *req) {
    imu_t im; xSemaphoreTake(s_mtx,portMAX_DELAY); im=s_imu; xSemaphoreGive(s_mtx);
    char r[400];
    int n=snprintf(r,sizeof(r),
        "{\"imu\":{\"available\":%s,\"x_raw\":%d,\"y_raw\":%d,\"z_raw\":%d,"
        "\"x_g\":%.4f,\"y_g\":%.4f,\"z_g\":%.4f},"
        "\"status\":{\"ip\":\"%s\",\"free_heap\":%u,\"frame_count\":%u,\"uptime\":%lld}}",
        im.ok?"true":"false",im.rx,im.ry,im.rz,im.gx,im.gy,im.gz,
        s_ip,(unsigned)esp_get_free_heap_size(),s_fcnt,
        (long long)((esp_timer_get_time()-s_t0)/1000000));
    httpd_resp_set_type(req,"application/json");
    httpd_resp_set_hdr(req,"Access-Control-Allow-Origin","*");
    httpd_resp_send(req,r,n); return ESP_OK;
}

static esp_err_t status_h(httpd_req_t *req) {
    char r[300];
    int n=snprintf(r,sizeof(r),
        "{\"device\":\"ESP32-S3-EYE\",\"ip\":\"%s\",\"free_heap\":%u,"
        "\"frames\":%u,\"uptime\":%lld,\"ssid\":\"%s\","
        "\"stream\":\"http://%s:%d/stream\",\"snapshot\":\"http://%s:%d/snapshot\"}",
        s_ip,(unsigned)esp_get_free_heap_size(),s_fcnt,
        (long long)((esp_timer_get_time()-s_t0)/1000000),
        WIFI_SSID,s_ip,HTTP_PORT,s_ip,HTTP_PORT);
    httpd_resp_set_type(req,"application/json");
    httpd_resp_set_hdr(req,"Access-Control-Allow-Origin","*");
    httpd_resp_send(req,r,n); return ESP_OK;
}

static esp_err_t stream_h(httpd_req_t *req) {
    httpd_resp_set_type(req,"multipart/x-mixed-replace;boundary=frame");
    httpd_resp_set_hdr(req,"Access-Control-Allow-Origin","*");
    httpd_resp_set_hdr(req,"Cache-Control","no-cache,no-store");
    int64_t t0=esp_timer_get_time();
    while(1) {
        camera_fb_t *fb=esp_camera_fb_get();
        if(!fb) { ESP_LOGE(TAG,"fb fail"); vTaskDelay(pdMS_TO_TICKS(100)); break; }
        char h[80];
        int hl=snprintf(h,sizeof(h),
            "\r\n--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
            (unsigned)fb->len);
        if(httpd_resp_send_chunk(req,h,hl)!=ESP_OK) { esp_camera_fb_return(fb); break; }
        if(httpd_resp_send_chunk(req,(const char*)fb->buf,fb->len)!=ESP_OK) {
            esp_camera_fb_return(fb); break; }
        if(httpd_resp_send_chunk(req,"\r\n--frame\r\n",12)!=ESP_OK) {
            esp_camera_fb_return(fb); break; }
        esp_camera_fb_return(fb);
        s_fcnt++;
        if(s_fcnt%100==0) {
            int64_t now=esp_timer_get_time();
            float el=(now-t0)/1e6f; float fps=el>0?100.0f/el:0;
            ESP_LOGI(TAG,"#%u FPS=%.1f heap=%u",s_fcnt,fps,(unsigned)esp_get_free_heap_size());
            t0=now;
        }
    }
    httpd_resp_send_chunk(req,NULL,0);
    return ESP_OK;
}

static esp_err_t snap_h(httpd_req_t *req) {
    camera_fb_t *fb=esp_camera_fb_get();
    if(!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
    httpd_resp_set_type(req,"image/jpeg");
    httpd_resp_set_hdr(req,"Access-Control-Allow-Origin","*");
    httpd_resp_set_hdr(req,"Content-Disposition","inline;filename=snap.jpg");
    httpd_resp_send(req,(const char*)fb->buf,fb->len);
    esp_camera_fb_return(fb);
    ESP_LOGI(TAG,"Snap %ub",(unsigned)fb->len);
    return ESP_OK;
}

static httpd_handle_t start_webserver(void) {
    httpd_config_t c=HTTPD_DEFAULT_CONFIG();
    c.server_port=HTTP_PORT; c.stack_size=8192;
    c.max_uri_handlers=8; c.lru_purge_enable=true;
    c.recv_wait_timeout=10; c.send_wait_timeout=30;
    httpd_handle_t s=NULL;
    if(httpd_start(&s,&c)!=ESP_OK) { ESP_LOGE(TAG,"Server fail"); return NULL; }
    httpd_uri_t u1={.uri="/",.method=HTTP_GET,.handler=root_h};
    httpd_uri_t u2={.uri="/stream",.method=HTTP_GET,.handler=stream_h};
    httpd_uri_t u3={.uri="/snapshot",.method=HTTP_GET,.handler=snap_h};
    httpd_uri_t u4={.uri="/api/sensors",.method=HTTP_GET,.handler=sensor_h};
    httpd_uri_t u5={.uri="/api/status",.method=HTTP_GET,.handler=status_h};
    httpd_register_uri_handler(s,&u1);
    httpd_register_uri_handler(s,&u2);
    httpd_register_uri_handler(s,&u3);
    httpd_register_uri_handler(s,&u4);
    httpd_register_uri_handler(s,&u5);
    ESP_LOGI(TAG,"Server on port %d",HTTP_PORT);
    return s;
}

// ==== Main ====
void app_main(void) {
    ESP_LOGI(TAG,"=== ESP32-S3-EYE Realtime Camera v2.0 ===");
    s_t0=esp_timer_get_time();
    esp_err_t r=nvs_flash_init();
    if(r==ESP_ERR_NVS_NO_FREE_PAGES||r==ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase()); r=nvs_flash_init();
    } ESP_ERROR_CHECK(r);
    s_mtx=xSemaphoreCreateMutex();
    ESP_ERROR_CHECK(i2c_init());
    if(qma_init()==ESP_OK)
        xTaskCreatePinnedToCore(imu_task,"imu",4096,NULL,5,NULL,0);
    ESP_ERROR_CHECK(cam_init());
    wifi_start();
    httpd_handle_t srv=start_webserver();
    if(!srv) { ESP_LOGE(TAG,"Server fail!"); esp_restart(); }
    ESP_LOGI(TAG,"========================================");
    ESP_LOGI(TAG," READY! http://%s:%d/",s_ip,HTTP_PORT);
    ESP_LOGI(TAG," Stream: http://%s:%d/stream",s_ip,HTTP_PORT);
    ESP_LOGI(TAG,"========================================");
    while(1) vTaskDelay(pdMS_TO_TICKS(10000));
}

