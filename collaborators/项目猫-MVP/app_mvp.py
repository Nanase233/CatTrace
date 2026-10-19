"""
项目猫-MVP 最小原型版
核心功能：猫咪展示、投喂、数据统计、猫脸识别
"""
from flask import Flask, render_template, jsonify, request
import json
import os
import threading
from datetime import datetime
import base64
from werkzeug.utils import secure_filename

# 导入猫脸识别模块
try:
    from cat_face_recognition import get_recognizer
    CAT_RECOGNITION_ENABLED = True
except ImportError:
    CAT_RECOGNITION_ENABLED = False

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data_mvp.json')
DATA_LOCK = threading.RLock()
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# 默认猫咪数据
DEFAULT_DATA = {
    "cats": [
        {
            "id": 1,
            "name": "咪咪",
            "nickname": "小区一霸",
            "gender": "female",
            "age": "2 岁",
            "color": "橘白相间",
            "location": "A 区 - 教学楼后",
            "description": "性格活泼，喜欢晒太阳，经常在教学楼后的小花园出现。",
            "feed_count": 156,
            "views": 1234
        },
        {
            "id": 2,
            "name": "小黑",
            "nickname": "夜行侠",
            "gender": "male",
            "age": "1 岁半",
            "color": "纯黑",
            "location": "B 区 - 食堂门口",
            "description": "夜间活跃，白天喜欢躲在车底下，对人比较警惕。",
            "feed_count": 89,
            "views": 876
        },
        {
            "id": 3,
            "name": "雪球",
            "nickname": "棉花糖",
            "gender": "female",
            "age": "3 岁",
            "color": "纯白",
            "location": "C 区 - 图书馆前",
            "description": "非常亲人，会主动蹭人，是图书馆的常驻猫咪。",
            "feed_count": 234,
            "views": 2156
        },
        {
            "id": 4,
            "name": "大橘",
            "nickname": "十斤橘",
            "gender": "male",
            "age": "4 岁",
            "color": "橘色",
            "location": "D 区 - 操场角落",
            "description": "体重超标，需要控制饮食，但依然很贪吃。",
            "feed_count": 312,
            "views": 1890
        }
    ],
    "feed_logs": [],
    "stats": {
        "total_cats": 4,
        "total_feeds": 791,
        "total_views": 6156
    }
}

def load_data():
    """加载数据"""
    with DATA_LOCK:
        if not os.path.exists(DATA_FILE):
            save_data(DEFAULT_DATA)
            return DEFAULT_DATA.copy()
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except:
            save_data(DEFAULT_DATA)
            return DEFAULT_DATA.copy()

def save_data(data):
    """保存数据"""
    with DATA_LOCK:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

def _next_id(items):
    """生成下一个 ID"""
    if not items:
        return 1
    return max(item.get('id', 0) for item in items) + 1

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ========== 页面路由 ==========

@app.route('/')
def index():
    """首页 - 直播间"""
    return render_template('mvp_index.html')

@app.route('/cats')
def cats():
    """猫咪档案页"""
    return render_template('mvp_cats.html')

@app.route('/mobile')
def mobile_recognize():
    """移动端猫脸识别页面"""
    return render_template('mobile_recognize.html')

# ========== API 接口 ==========

@app.route('/api/cats')
def get_cats():
    """获取所有猫咪列表"""
    data = load_data()
    return jsonify(data['cats'])

@app.route('/api/cat/<int:cat_id>')
def get_cat(cat_id):
    """获取单个猫咪详情"""
    data = load_data()
    for cat in data['cats']:
        if cat['id'] == cat_id:
            cat['views'] = cat.get('views', 0) + 1
            save_data(data)
            return jsonify(cat)
    return jsonify({'error': 'Cat not found'}), 404

@app.route('/api/stats')
def get_stats():
    """获取统计数据"""
    data = load_data()
    return jsonify(data['stats'])

@app.route('/api/feed', methods=['POST'])
def feed_cat():
    """投喂猫咪"""
    if not request.is_json:
        return jsonify({'success': False, 'message': '请求格式错误'}), 400

    req_data = request.get_json(silent=True) or {}
    cat_id = req_data.get('cat_id')
    user_name = req_data.get('user_name', '匿名用户')

    if not cat_id:
        return jsonify({'success': False, 'message': 'cat_id 不合法'}), 400

    data = load_data()
    
    target_cat = None
    for cat in data['cats']:
        if cat.get('id') == cat_id:
            target_cat = cat
            break
    
    if not target_cat:
        return jsonify({'success': False, 'message': '猫咪不存在'}), 404

    target_cat['feed_count'] = target_cat.get('feed_count', 0) + 1
    
    # 记录投喂日志
    log = {
        'id': _next_id(data['feed_logs']),
        'cat_id': cat_id,
        'cat_name': target_cat.get('name'),
        'user_name': user_name,
        'time': datetime.now().isoformat(timespec='seconds')
    }
    data['feed_logs'].append(log)
    
    # 更新统计
    data['stats']['total_feeds'] = sum(c.get('feed_count', 0) for c in data['cats'])
    
    save_data(data)
    
    return jsonify({
        'success': True,
        'message': f'投喂成功！{user_name} 投喂了 {target_cat.get("name", "猫咪")}',
        'feed_count': target_cat['feed_count']
    })

@app.route('/api/feed-logs')
def get_feed_logs():
    """获取投喂记录"""
    data = load_data()
    limit = min(int(request.args.get('limit', 10)), 50)
    logs = data.get('feed_logs', [])[-limit:][::-1]
    return jsonify(logs)

@app.route('/api/reset', methods=['POST'])
def reset_data():
    """重置数据（仅用于演示）"""
    save_data(DEFAULT_DATA)
    return jsonify({'success': True, 'message': '数据已重置'})

@app.route('/api/camera-upload', methods=['POST'])
def camera_upload():
    """ESP32 摄像头照片上传接口"""
    try:
        # 确保上传目录存在
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # 获取设备信息
        device_id = request.form.get('device_id', 'ESP32_001')
        location = request.form.get('location', '未知位置')
        
        # 处理上传的照片
        if 'photo' in request.files:
            file = request.files['photo']
            if file.filename == '':
                return jsonify({'success': False, 'message': '没有选择文件'}), 400
            
            if file and allowed_file(file.filename):
                # 生成文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{device_id}_{timestamp}.jpg"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                
                # 获取照片大小
                file_size = os.path.getsize(filepath)
                
                # 更新猫咪数据（增加投喂计数）
                data = load_data()
                for cat in data['cats']:
                    cat['feed_count'] = cat.get('feed_count', 0) + 1
                
                # 更新统计
                data['stats']['total_feeds'] = sum(c.get('feed_count', 0) for c in data['cats'])
                save_data(data)
                
                # 记录日志
                log = {
                    'id': _next_id(data['feed_logs']),
                    'cat_id': 1,
                    'cat_name': '摄像头',
                    'user_name': device_id,
                    'time': datetime.now().isoformat(timespec='seconds'),
                    'location': location,
                    'photo': filename
                }
                data['feed_logs'].append(log)
                save_data(data)
                
                return jsonify({
                    'success': True,
                    'message': '照片上传成功',
                    'filename': filename,
                    'file_size': file_size,
                    'location': location
                })
            else:
                return jsonify({'success': False, 'message': '不支持的文件格式'}), 400
        else:
            # 如果没有文件，但收到了原始数据
            content_length = request.content_length
            if content_length and content_length > 0:
                # 保存原始二进制数据
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{device_id}_{timestamp}.jpg"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(request.data)
                
                file_size = os.path.getsize(filepath)
                
                # 更新数据
                data = load_data()
                for cat in data['cats']:
                    cat['feed_count'] = cat.get('feed_count', 0) + 1
                data['stats']['total_feeds'] = sum(c.get('feed_count', 0) for c in data['cats'])
                save_data(data)
                
                return jsonify({
                    'success': True,
                    'message': '照片上传成功',
                    'filename': filename,
                    'file_size': file_size
                })
            
            return jsonify({'success': False, 'message': '没有收到照片数据'}), 400
            
    except Exception as e:
        print(f"上传错误：{e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/photos')
def get_photos():
    """获取所有上传的照片"""
    try:
        if not os.path.exists(UPLOAD_FOLDER):
            return jsonify([])
        
        photos = []
        for filename in sorted(os.listdir(UPLOAD_FOLDER), reverse=True):
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                stat = os.stat(filepath)
                photos.append({
                    'filename': filename,
                    'url': f'/static/uploads/{filename}',
                    'size': stat.st_size,
                    'time': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        return jsonify(photos[:50])  # 返回最近 50 张
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recognize', methods=['POST'])
def recognize_cat():
    """识别照片中的猫咪"""
    if not CAT_RECOGNITION_ENABLED:
        return jsonify({
            'success': False,
            'message': '猫脸识别模块未启用，请检查依赖是否安装'
        }), 500
        
    if 'photo' not in request.files:
        return jsonify({'success': False, 'message': '没有上传照片'}), 400
        
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
    try:
        # 保存临时文件
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_filename = f"temp_{timestamp}.jpg"
        temp_path = os.path.join(UPLOAD_FOLDER, temp_filename)
        file.save(temp_path)
        
        # 执行识别
        recognizer = get_recognizer()
        result = recognizer.recognize(temp_path)
        
        # 清理临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        return jsonify({
            'success': True,
            'recognition': result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recognize-photo/<path:filename>')
def recognize_uploaded_photo(filename):
    """识别已上传的照片"""
    if not CAT_RECOGNITION_ENABLED:
        return jsonify({
            'success': False,
            'message': '猫脸识别模块未启用'
        }), 500
        
    try:
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'message': '文件不存在'}), 404
            
        recognizer = get_recognizer()
        result = recognizer.recognize(filepath)
        
        return jsonify({
            'success': True,
            'recognition': result,
            'filename': filename
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/register-cat', methods=['POST'])
def register_cat():
    """注册新猫咪（用于猫脸识别）"""
    if not CAT_RECOGNITION_ENABLED:
        return jsonify({
            'success': False,
            'message': '猫脸识别模块未启用'
        }), 500
        
    cat_id = request.form.get('cat_id')
    cat_name = request.form.get('cat_name')
    
    if not cat_id or not cat_name:
        return jsonify({'success': False, 'message': '缺少 cat_id 或 cat_name'}), 400
        
    try:
        recognizer = get_recognizer()
        
        # 收集上传的照片
        image_paths = []
        for file in request.files.getlist('photos'):
            if file.filename:
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"register_{cat_id}_{timestamp}.jpg"
                filepath = os.path.join(UPLOAD_FOLDER, filename)
                file.save(filepath)
                image_paths.append(filepath)
                
        if not image_paths:
            return jsonify({'success': False, 'message': '没有上传照片'}), 400
            
        # 注册猫咪
        success = recognizer.register_cat(cat_id, cat_name, image_paths)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'猫咪 {cat_name} 注册成功',
                'image_count': len(image_paths)
            })
        else:
            return jsonify({'success': False, 'message': '注册失败'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/registered-cats')
def get_registered_cats():
    """获取已注册的猫咪列表"""
    if not CAT_RECOGNITION_ENABLED:
        return jsonify([])
        
    try:
        recognizer = get_recognizer()
        cats = recognizer.get_all_cats()
        return jsonify(list(cats.values()))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/auto-recognize-upload', methods=['POST'])
def auto_recognize_upload():
    """自动识别上传的照片（在 camera-upload 后自动识别）"""
    if not CAT_RECOGNITION_ENABLED:
        # 如果没有启用识别，直接调用原来的上传逻辑
        return camera_upload()
        
    # 先执行上传
    upload_result = camera_upload()
    
    if upload_result.status_code != 200:
        return upload_result
        
    # 获取刚上传的文件名
    upload_data = upload_result.get_json()
    filename = upload_data.get('filename')
    
    if not filename:
        return upload_result
        
    # 执行识别
    try:
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        recognizer = get_recognizer()
        result = recognizer.recognize(filepath)
        
        # 将识别结果保存到日志
        data = load_data()
        log = data['feed_logs'][-1] if data['feed_logs'] else {}
        log['recognition'] = result
        save_data(data)
        
        # 合并结果
        upload_data['recognition'] = result
        return jsonify(upload_data)
        
    except Exception as e:
        # 识别失败不影响上传
        return upload_result

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)