# 实时直播接入（树莓派摄像头 → 网页直播间）

首页「实时直播间」原来是一个占位表情（🐱）。接入真实摄像头后，浏览器看到的是树莓派
摄像头的实时画面，断流时自动回退到占位动画，不会白屏。

## 1. 数据怎么走

```
树莓派摄像头 (CSI)
   │  picamera2
   ▼
树莓派 MJPEG 服务 :8000/stream        ← scripts/pi_phone_demo.py
   │  HTTP multipart/x-mixed-replace
   ▼
Flask /api/live/stream（同源代理，app.py + live_proxy.py）
   │
   ▼
浏览器 <img id="liveStream">
```

**为什么不让浏览器直连树莓派？**

| 直连 Pi | 走 Flask 代理（当前做法） |
|---|---|
| 手机换了网络就打不开 | 只要能打开网页，就能看到画面 |
| 页面以后上 HTTPS 会被判混合内容，直接拦掉 | 同源，没有混合内容问题 |
| 需要给 Pi 开 CORS | 不需要 |
| 少一跳，延迟低一丢丢 | 多一次转发（局域网内 < 30ms） |

## 2. 怎么跑

### 第零步（推荐）：没有树莓派也先把链路验证通

`scripts/mock_live_source.py` 会在本机起一个假摄像头（Pillow 现画画面 + 模拟 `/stats`），
接口和树莓派那一侧完全一致。用它先确认「Flask 代理 → 网页直播间」这段是好的，再去折腾硬件：

```powershell
# 终端 1：假摄像头，8100 端口
python scripts/mock_live_source.py --port 8100 --verdict cat

# 终端 2：带地址起网页
$env:CATTRACE_LIVE_URL      = "http://127.0.0.1:8100/stream"
$env:CATTRACE_LIVE_STATS    = "http://127.0.0.1:8100/stats"
$env:CATTRACE_LIVE_SNAPSHOT = "http://127.0.0.1:8100/snapshot.jpg"
python app.py
```

打开 `http://127.0.0.1:5000/live`，应该看到：画面切到实时（不再是被占位表情挡住），
右上角徽标从「AI 模拟识别」变成「AI 实时识别 · 猫 97% · 已绝育」。

`--verdict` 可以换成 `notcat`（徽标显示「未发现猫」）或 `starting`（「启动中」）；
想验证断流回退，直接把假摄像头的进程停掉。

### 第一步：树莓派上启动摄像头服务

```bash
cd ~/catvision
python scripts/pi_phone_demo.py --rotate 180 --port 8000 \
  --stream-fps 8 --fps 2 --threads 1
```

确认能出画面：手机或电脑浏览器打开 `http://<树莓派IP>:8000/`。

树莓派这一侧提供两路画面，别混用：

| 端点 | 内容 | 谁在用 |
|---|---|---|
| `/stream` | 原始画面 MJPEG，连续推流 | 网页直播间（Flask 代理转发这一路） |
| `/stream?annotated=1` | 带 HUD 判定（含绝育结论）的 MJPEG | 排障时看模型到底判了什么 |
| `/frame.jpg`、`/snapshot.jpg` | 单帧 JPEG，带 HUD | 树莓派本机页面（含 kiosk）轮询这一路 |
| `/stats` | 识别状态 JSON（含 `stream_fps` / `stream_frames`） | 网页右上角徽标、冻结检测 |

网页直播间要的是干净画面，所以调试标注不会烧进直播流；`stream_frames` 连续 5 秒
不增长时前端判定「画面已冻结」并自动重连。

> Pi 4（1GB）实测：`--threads 4` 会占满约 312% CPU，首帧可能等十几秒；
> 改成 `--threads 1` 后占用约 100%，首屏稳定在 1 秒左右。`--stream-fps 8`
> 是持续视频流目标帧率，`--fps 2` 是 AI 分类目标帧率。采集和推理由两个线程
> 解耦，推理变慢不会卡住直播。首页分别显示“视频 fps”和“识别 fps”。
>
> 电源必须是稳定的 5V/3A。若 `vcgencmd get_throttled` 不是 `0x0`，先处理欠压，
> 否则会出现花屏、掉线、USB/CSI 设备重启等难排查的问题。

### 推荐：用 systemd 用户服务保持树莓派直播常驻

SSH 断开后不能依赖 `nohup`，否则 logind 可能随会话结束清理摄像头进程。把仓库里的
`deploy/catvision-camera.service` 安装到用户级 systemd：

```bash
mkdir -p ~/.config/systemd/user
cp deploy/catvision-camera.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now catvision-camera.service
systemctl --user status catvision-camera.service
journalctl --user -u catvision-camera.service -f
```

服务单元用 `%h` 展开用户目录：`WorkingDirectory=%h/catvision`、`ExecStart=%h/venvs/catvision/bin/python`。
仓库默认假设代码在 `~/catvision`、虚拟环境在 `~/venvs/catvision`；路径不同就改这两行。
`systemctl --user enable` 需要用户 linger 已开启（`loginctl show-user <用户> -p Linger` 应为 `Linger=yes`）。

### 第二步：启动网页（带摄像头地址）

**推荐：一条命令**，它会先探一次树莓派再启动 Flask，省掉手抄环境变量：

```bash
# 电脑上跑（树莓派只当摄像头节点）
python scripts/serve_live.py --pi 192.168.1.50

# 或者直接在树莓派本机跑（手机热点 / 陌生网络下最省事）
python scripts/serve_live.py --pi 127.0.0.1
```

预检通过会打印 `/stats` 的判定和 `/snapshot` 的字节数，然后给出本机和手机的访问地址；
预检失败也会照样启动网页（页面显示「设备离线」），并提示最可能的四个原因。

> 树莓派上跑网页只需要 `pip install flask`（`app.py` 不依赖 Pillow / pydantic）。

也可以手工设环境变量（等价做法）：

Linux / macOS：

```bash
export CATTRACE_LIVE_URL=http://192.168.1.50:8000/stream
export CATTRACE_LIVE_STATS=http://192.168.1.50:8000/stats   # 可选，显示识别状态
export CATTRACE_LIVE_SNAPSHOT=http://192.168.1.50:8000/snapshot.jpg  # 可选，首屏单帧
python app.py
```

Windows PowerShell：

```powershell
$env:CATTRACE_LIVE_URL   = "http://192.168.1.50:8000/stream"
$env:CATTRACE_LIVE_STATS = "http://192.168.1.50:8000/stats"
$env:CATTRACE_LIVE_SNAPSHOT = "http://192.168.1.50:8000/snapshot.jpg"
python app.py
```

`CATTRACE_LIVE_STATS` 不填也能看画面，只是右上角徽标不会再更新「识别到猫 xx%」。

> 不配 `CATTRACE_LIVE_URL` 时，直播功能整体关闭，页面行为和之前完全一样（显示表情占位）。

### 第三步：让手机也能看

```powershell
$env:PROJECTCAT_HOST = "0.0.0.0"
python app.py
```

手机访问 `http://<电脑IP>:5000/`，画面会跟着一起出来——因为 Pi 的流是 Flask 去拉的，
手机不需要能连到树莓派。

## 3. 后端接口

| 接口 | 作用 | 说明 |
|---|---|---|
| `GET /api/live/info` | 是否可用 + 各端点地址 | 前端启动时调一次 |
| `GET /api/live/stream` | MJPEG 视频流 | 原样转发，`Cache-Control: no-store` |
| `GET /api/live/snapshot` | 截当前一帧 JPEG | 配了单帧接口时直接取图；否则从 MJPEG 流里抠帧 |
| `GET /api/live/stats` | 识别状态 JSON | 需要配 `CATTRACE_LIVE_STATS` |

环境变量：

| 变量 | 必填 | 例子 |
|---|---|---|
| `CATTRACE_LIVE_URL` | 是（否则关闭） | `http://192.168.1.50:8000/stream` |
| `CATTRACE_LIVE_STATS` | 否 | `http://192.168.1.50:8000/stats` |
| `CATTRACE_LIVE_SNAPSHOT` | 否；建议配置 | `http://192.168.1.50:8000/snapshot.jpg` |
| `CATTRACE_LIVE_TIMEOUT` | 否，默认 8 秒 | `5` |

## 4. 前端行为

- 连上：显示真实画面，隐藏表情；配了 `CATTRACE_LIVE_STATS` 时右上角徽标显示树莓派的**真实判定**
  ——「AI 实时识别 · 猫 97% · 已绝育」/「未发现猫」/「启动中」，没配则只显示「AI 实时识别 · 猫名」。
- 断流：显示「📡 摄像头断流」+ 重试按钮，表情回来，按 2s → 4s → 8s → 16s → 30s 退避重连。
- 画面冻结：每 2 秒轮询 `/stats`，若 `stream_frames` 连续 5 秒不增长，判定「画面已冻结」并主动重连，
  避免一直停在最后一帧。
- 6 秒还没出第一帧：判定「摄像头无响应」。
- 没配地址：完全不打扰，保持原来的占位动画。

## 5. 已知限制

| 限制 | 原因 | 后续方案 |
|---|---|---|
| 延迟约 0.2~0.5s | MJPEG 逐帧推流 | 要 <200ms 且多人观看 → WebRTC（go2rtc / MediaMTX） |
| 每个观众占一个 Flask 线程 | 同步转发 | 观众变多 → Nginx `proxy_pass` 直接转发，绕开 Flask |
| AI 识别约 2 FPS | 1GB 机器上 ONNX 分类算力有限 | 采集/推流与推理双线程解耦；画面按 `--stream-fps` 连续推送，识别按 `--fps` 消费最新帧 |
| Pi 4 只有 1GB 内存 | 硬件 | 关掉不用的分类线程（`--threads 1`），并换 5V/3A 电源 |

## 6. 与 AI 链路的关系

直播画面和识别链路**可以共用一路摄像头**，但要注意 picamera2 一个进程独占摄像头：

- 现在：`pi_phone_demo.py` 自己开摄像头，做分类 + 推流。
- 接正式识别时：让 `pipeline.runner` 成为唯一的摄像头持有者，把抽出来的帧同时
  (a) 写 `/dev/shm` 给识别用，(b) 推给 MJPEG 服务。这样画面就是「模型看到的那一帧」，
  演示时可信度最高，也不会两个进程抢摄像头。

## 7. 常见问题

### Q1. 我打开的是 GitHub Pages 的静态站，为什么看不到摄像头？

静态站只有 HTML/CSS/JS，没有后端 `/api/live/*` 代理，`<img src="/api/live/stream">` 会 404。
要看摄像头，页面必须跑在 **Flask** 上：

| 场景 | 做法 | Pi 需要公网吗 |
|---|---|---|
| 电脑和 Pi 在同一个 Wi-Fi（最常见） | 电脑上 `python app.py` + 三个 `CATTRACE_*` 环境变量，浏览器开 `http://<电脑IP>:5000/live` | 不需要 |
| 只想在 Pi 自己身上看 | Pi 上也跑一份 Flask，`CATTRACE_LIVE_URL=http://127.0.0.1:8000/stream` | 不需要 |
| 想给外网 / 手机 4G 看 | Pi 上开内网穿透（cloudflared / ngrok），隧道地址填进 `CATTRACE_LIVE_URL`，Flask 部署到 Render | 需要隧道 |

> Render 免费实例**连不到你家里的局域网**，所以「Render + 家里的 Pi」中间必须有隧道这一跳。

### Q2. 浏览器能打开 `http://<Pi>:8000/`，但网页直播间一直停在占位动画

按顺序查：

1. 在跑 Flask 的那台机器（不是 Pi）上执行 `curl http://<Pi>:8000/stats` —— 不通就是网络或端口问题；
2. Pi 的防火墙：`sudo ufw status` 里要有 `8000` 的 allow，否则 `sudo ufw allow 8000/tcp`；
3. 环境变量是不是没生效：Windows 必须在**同一个** PowerShell 窗口里先 `$env:` 再 `python app.py`；
4. `curl http://127.0.0.1:5000/api/live/info` 应返回 `"enabled": true`；若是 `false`，说明变量没读到；
5. 都正常但画面不动 → 看第 1 步 `stream_frames` 有没有在涨，不涨就是摄像头卡住（见 Q3）。

### Q3. 树莓派直播几秒就卡住 / 服务反复重启

先怀疑硬件：`vcgencmd get_throttled` 不是 `0x0` 就是欠压，换 5V/3A 电源并重插 CSI 排线。
实测这台 Pi 就是这个症状（`0x50005`）：`rpicam-still` 正常，但持续出流几秒后 Unicam 超时。
详见 [pi-kiosk-实测记录.md](./pi-kiosk-实测记录.md) 第 4 节。

### Q4. 徽标一直显示「启动中」

`/stats` 里 `verdict` 还是 `starting`，说明模型或摄像头还在初始化，等 5~10 秒；一直不变就看
`journalctl --user -u catvision-camera -n 50`，常见原因是模型文件缺失（onnx/json 被覆盖）。

