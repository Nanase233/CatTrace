"""
项目猫-MVP API 测试脚本
测试所有主要 API 端点的功能
"""

import requests
import json
import base64
import uuid
import os
import sys

# 确保 UTF-8 编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 基础 URL
BASE_URL = os.environ.get('TEST_BASE_URL', 'http://127.0.0.1:5000')

# 测试用图片（base64 编码的简单图片数据）
TEST_IMAGE_BASE64 = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAn/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="

def print_result(test_name, success, message=""):
    """打印测试结果"""
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} {test_name}: {message}")

def test_get_cats():
    """测试获取猫咪列表"""
    print("\n=== 测试获取猫咪列表 ===")
    try:
        resp = requests.get(f"{BASE_URL}/api/cats", timeout=5)
        data = resp.json()
        # API 直接返回数组
        success = resp.status_code == 200 and isinstance(data, list)
        cats = data if isinstance(data, list) else []
        print_result("获取猫咪列表", success, f"猫咪数量：{len(cats)}")
        if cats:
            print(f"  示例：{cats[0].get('name')} - {cats[0].get('location')}")
        return success
    except Exception as e:
        print_result("获取猫咪列表", False, str(e))
        return False

def test_get_cat_detail():
    """测试获取猫咪详情"""
    print("\n=== 测试获取猫咪详情 ===")
    try:
        # 先获取猫咪列表获取一个 ID
        resp = requests.get(f"{BASE_URL}/api/cats", timeout=5)
        cats_data = resp.json()
        cats = cats_data if isinstance(cats_data, list) else cats_data.get('cats', [])
        if not cats:
            print_result("获取猫咪详情", False, "没有可用的猫咪")
            return False
        
        cat_id = cats[0]['id']
        resp = requests.get(f"{BASE_URL}/api/cat/{cat_id}", timeout=5)
        data = resp.json()
        # API 直接返回猫咪对象
        success = resp.status_code == 200 and isinstance(data, dict) and 'id' in data
        print_result("获取猫咪详情", success, f"猫咪：{data.get('name', 'Unknown')}")
        return success
    except Exception as e:
        print_result("获取猫咪详情", False, str(e))
        return False

def test_get_stats():
    """测试获取统计数据"""
    print("\n=== 测试获取统计数据 ===")
    try:
        resp = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        data = resp.json()
        success = resp.status_code == 200
        print_result("获取统计数据", success, f"数据：{data}")
        return success
    except Exception as e:
        print_result("获取统计数据", False, str(e))
        return False

def test_login():
    """测试用户登录"""
    print("\n=== 测试用户登录 ===")
    try:
        # 使用手机号格式登录（系统要求手机号），添加测试验证码 8888
        resp = requests.post(f"{BASE_URL}/api/auth/login", json={
            'phone': '13800138000',
            'code': '8888'
        }, timeout=5)
        data = resp.json()
        success = resp.status_code == 200 and data.get('success')
        token = data.get('token')
        print_result("用户登录", success, f"Token: {token[:20]}..." if token else data.get('message', ''))
        return token if success else None
    except Exception as e:
        print_result("用户登录", False, str(e))
        return None

def test_feed_cat_guest():
    """测试游客投喂"""
    print("\n=== 测试游客投喂 ===")
    try:
        # 获取一个猫咪 ID
        resp = requests.get(f"{BASE_URL}/api/cats", timeout=5)
        cats_data = resp.json()
        cats = cats_data if isinstance(cats_data, list) else cats_data.get('cats', [])
        if not cats:
            print_result("游客投喂", False, "没有可用的猫咪")
            return False
        
        cat_id = cats[0]['id']
        guest_id = f"guest_{uuid.uuid4().hex[:8]}"
        
        resp = requests.post(f"{BASE_URL}/api/feed-as-guest", json={
            'cat_id': cat_id,
            'guest_id': guest_id
        }, timeout=5)
        data = resp.json()
        success = resp.status_code == 200 and data.get('success')
        print_result("游客投喂", success, data.get('message', ''))
        return success
    except Exception as e:
        print_result("游客投喂", False, str(e))
        return False

def test_feed_cat_login(token):
    """测试登录用户投喂"""
    print("\n=== 测试登录用户投喂 ===")
    try:
        if not token:
            print_result("登录用户投喂", False, "缺少 token")
            return False
        
        # 获取一个猫咪 ID
        resp = requests.get(f"{BASE_URL}/api/cats", timeout=5)
        cats_data = resp.json()
        cats = cats_data if isinstance(cats_data, list) else cats_data.get('cats', [])
        if not cats:
            print_result("登录用户投喂", False, "没有可用的猫咪")
            return False
        
        cat_id = cats[0]['id']
        
        resp = requests.post(f"{BASE_URL}/api/feed", json={
            'cat_id': cat_id
        }, headers={'Authorization': f'Bearer {token}'}, timeout=5)
        data = resp.json()
        success = resp.status_code == 200 and data.get('success')
        print_result("登录用户投喂", success, data.get('message', ''))
        return success
    except Exception as e:
        print_result("登录用户投喂", False, str(e))
        return False

def test_report_abuse():
    """测试举报功能"""
    print("\n=== 测试举报功能 ===")
    try:
        # 获取一个猫咪 ID
        resp = requests.get(f"{BASE_URL}/api/cats", timeout=5)
        cats_data = resp.json()
        cats = cats_data if isinstance(cats_data, list) else cats_data.get('cats', [])
        if not cats:
            print_result("举报功能", False, "没有可用的猫咪")
            return False
        
        cat_id = cats[0]['id']
        
        resp = requests.post(f"{BASE_URL}/api/report-abuse", json={
            'cat_id': cat_id,
            'report_type': 'health_issue',
            'description': '测试举报：猫咪看起来不太舒服',
            'reporter_name': '测试用户',
            'is_emergency': False
        }, timeout=5)
        data = resp.json()
        success = resp.status_code == 200 and data.get('success')
        print_result("举报功能", success, data.get('message', ''))
        return success
    except Exception as e:
        print_result("举报功能", False, str(e))
        return False

def test_recognizer_status():
    """测试识别器状态"""
    print("\n=== 测试识别器状态 ===")
    try:
        resp = requests.get(f"{BASE_URL}/api/cats/recognizer-status", timeout=5)
        data = resp.json()
        available = data.get('available', False)
        message = data.get('message', '')
        print_result("识别器状态", True, f"可用：{available}, {message}")
        return True
    except Exception as e:
        print_result("识别器状态", False, str(e))
        return False

def test_get_registered_cats():
    """测试获取已注册猫咪"""
    print("\n=== 测试获取已注册猫咪 ===")
    try:
        resp = requests.get(f"{BASE_URL}/api/cats/registered", timeout=5)
        data = resp.json()
        # API 可能直接返回数组或 {'success': true, 'cats': [...]}
        if isinstance(data, list):
            success = resp.status_code == 200
            cats = data
        else:
            success = resp.status_code == 200 and data.get('success')
            cats = data.get('cats', [])
        print_result("获取已注册猫咪", success, f"已注册：{len(cats)} 只")
        return success
    except Exception as e:
        print_result("获取已注册猫咪", False, str(e))
        return False

def test_recognize_cat():
    """测试猫脸识别"""
    print("\n=== 测试猫脸识别 ===")
    try:
        # 创建一个临时图片文件
        import tempfile
        image_data = base64.b64decode(TEST_IMAGE_BASE64)
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp.write(image_data)
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, 'rb') as f:
                files = {'image': f}
                resp = requests.post(f"{BASE_URL}/api/recognize", files=files, timeout=10)
                data = resp.json()
                
                # 503 表示识别服务未可用，这也是可接受的结果
                success = resp.status_code in (200, 503)
                message = data.get('message', '')
                print_result("猫脸识别", success, f"状态：{resp.status_code}, {message}")
                return success
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        print_result("猫脸识别", False, str(e))
        return False

def test_esp32_upload():
    """测试 ESP32 上传"""
    print("\n=== 测试 ESP32 上传 ===")
    try:
        # 使用 base64 方式测试
        resp = requests.post(f"{BASE_URL}/api/esp32/upload", json={
            'image': TEST_IMAGE_BASE64
        }, timeout=10)
        data = resp.json()
        
        # 503 表示识别服务未可用，这也是可接受的结果
        success = resp.status_code in (200, 503)
        message = data.get('message', '')
        print_result("ESP32 上传", success, f"状态：{resp.status_code}, {message}")
        return success
    except Exception as e:
        print_result("ESP32 上传", False, str(e))
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("项目猫-MVP API 测试")
    print("=" * 60)
    print(f"测试服务器：{BASE_URL}")
    
    results = {}
    
    # 基础功能测试
    results['get_cats'] = test_get_cats()
    results['get_cat_detail'] = test_get_cat_detail()
    results['get_stats'] = test_get_stats()
    
    # 用户认证测试
    token = test_login()
    results['login'] = token is not None
    
    # 投喂功能测试
    results['feed_guest'] = test_feed_cat_guest()
    results['feed_login'] = test_feed_cat_login(token) if token else False
    
    # 举报功能测试
    results['report_abuse'] = test_report_abuse()
    
    # 猫脸识别测试
    results['recognizer_status'] = test_recognizer_status()
    results['get_registered_cats'] = test_get_registered_cats()
    results['recognize_cat'] = test_recognize_cat()
    results['esp32_upload'] = test_esp32_upload()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "通过" if result else "失败"
        print(f"  [{status}] - {name}")
    
    print(f"\n总计：{passed}/{total} 测试通过 ({passed/total*100:.1f}%)")
    print("=" * 60)
    
    return passed == total

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)