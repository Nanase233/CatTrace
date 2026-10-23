#!/usr/bin/env bash
# 树莓派一键部署（摄像头与联调负责）。幂等，可以反复跑。
#
#   scp 到 Pi 上执行，或在仓库目录里：bash scripts/setup_pi.sh
set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/catvision}"
VENV_DIR="${VENV_DIR:-$HOME/venvs/catvision}"
CAMERA_ID="${CAMERA_ID:-cam0}"

echo "==> 0. 关掉桌面环境，省 269MB 内存（1GB 的 Pi4 很需要）"
if systemctl get-default | grep -q graphical; then
  echo "    当前是图形界面，切到 multi-user.target（重启后生效，开机从 ~3min 降到 ~30s）"
  sudo systemctl set-default multi-user.target
else
  echo "    已经是 multi-user.target，跳过"
fi

echo "==> 1. 系统依赖"
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  python3-picamera2 python3-numpy python3-pil \
  ffmpeg sqlite3 git ca-certificates

echo "==> 2. 帧目录放内存盘 /dev/shm，绝不写 SD 卡（SD 卡写坏一次就得重装）"
sudo mkdir -p /dev/shm/catvision/frames
sudo chown -R "$USER":"$USER" /dev/shm/catvision

echo "==> 3. 虚拟环境（必须 --system-site-packages，否则看不到 apt 装的 picamera2）"
python3 -m venv --system-site-packages "$VENV_DIR" 2>/dev/null || true
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -e "$REPO_DIR"
pip install onnxruntime opencv-python-headless  # AI 推理用（猫脸、耳标模块会用到）

echo "==> 4. 自检"
python - <<'PY'
import sys
import picamera2
print("python      :", sys.version.split()[0])
print("picamera2   :", picamera2.__version__ if hasattr(picamera2, "__version__") else "ok")
from pathlib import Path
print("shm writable:", Path("/dev/shm").is_dir())
PY

echo "==> 5. 摄像头自检（CSI）"
python -m modules.camera --source "csi://0" --fps 3 --frames 3 || {
  echo "!! CSI 采集失败。排查顺序："
  echo "   1) rpicam-still -o /tmp/t.jpg --timeout 2000   看看硬件通不通"
  echo "   2) vcgencmd get_throttled                       非 0 就是供电不足（必须 5V/3A）"
  echo "   3) ls -l /dev/video* /dev/media*                libcamera 是否认到设备"
  exit 1
}

echo "==> 6. D0 验收"
python -m pipeline.runner --source synthetic:30 --mock-all

echo
echo "全部就绪。跑真实摄像头："
echo "  source $VENV_DIR/bin/activate && cd $REPO_DIR"
echo "  python -m modules.camera --source csi://0 --fps 3 --frames 10"
