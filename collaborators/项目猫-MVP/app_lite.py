"""
项目猫-MVP 轻量版
核心功能：猫咪展示、投喂、数据统计
无需安装 tensorflow 等重型依赖
"""
from flask import Flask, render_template, jsonify, request
import json
import os
import threading
from datetime import datetime

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, 'data_mvp.json')
DATA_LOCK = threading.RLock()

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
def mobile():
    """移动端猫咪列表页"""
    return render_template('mobile.html')

@app.route('/mobile/cat/<int:cat_id>')
def mobile_cat_detail(cat_id):
    """移动端猫咪详情页"""
    return render_template('mobile_detail.html')

@app.route('/mobile/recognize')
def mobile_recognize():
    """移动端猫脸识别页面（简化版）"""
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

if __name__ == '__main__':
    import sys
    # 设置控制台编码为 utf-8
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 50)
    print("项目猫-MVP 轻量版")
    print("=" * 50)
    print("访问地址：http://localhost:5000")
    print("手机访问：http://10.1.41.147:5000")
    print("=" * 50)
    print("功能说明:")
    print("  - 首页：http://localhost:5000/")
    print("  - 猫咪档案：http://localhost:5000/cats")
    print("  - 移动端识别：http://localhost:5000/mobile")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)
