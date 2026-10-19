"""
猫脸识别模块 - 使用深度学习模型
功能：检测猫脸、提取特征、识别猫咪身份
"""
import cv2
import numpy as np
import os
import json
from datetime import datetime
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input
from tensorflow.keras.preprocessing import image
from sklearn.metrics.pairwise import cosine_similarity
import pickle

class CatFaceRecognizer:
    """猫脸识别器"""
    
    def __init__(self, model_dir='models'):
        self.model_dir = model_dir
        self.cat_features = {}  # 存储每只猫咪的特征向量
        self.cat_database = {}  # 猫咪数据库
        self.detector_net = None
        self.feature_extractor = None
        
        # 创建模型目录
        os.makedirs(model_dir, exist_ok=True)
        
        # 加载或创建模型
        self._load_models()
        
    def _load_models(self):
        """加载检测模型和特征提取模型"""
        try:
            # 尝试加载预训练的特征提取模型 (MobileNetV2)
            self.feature_extractor = MobileNetV2(
                weights='imagenet',
                include_top=False,
                pooling='avg'
            )
            print("✓ 特征提取模型加载成功")
        except Exception as e:
            print(f"⚠ 特征提取模型加载失败：{e}")
            print("  将使用简化模式")
            
        # 加载猫咪特征数据库
        self._load_cat_database()
        
    def _load_cat_database(self):
        """加载猫咪特征数据库"""
        db_path = os.path.join(self.model_dir, 'cat_database.json')
        features_path = os.path.join(self.model_dir, 'cat_features.pkl')
        
        if os.path.exists(db_path):
            with open(db_path, 'r', encoding='utf-8') as f:
                self.cat_database = json.load(f)
            print(f"✓ 猫咪数据库加载成功，共 {len(self.cat_database)} 只猫咪")
            
        if os.path.exists(features_path):
            with open(features_path, 'rb') as f:
                self.cat_features = pickle.load(f)
                
    def _save_cat_database(self):
        """保存猫咪特征数据库"""
        db_path = os.path.join(self.model_dir, 'cat_database.json')
        features_path = os.path.join(self.model_dir, 'cat_features.pkl')
        
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(self.cat_database, f, ensure_ascii=False, indent=2)
            
        with open(features_path, 'wb') as f:
            pickle.dump(self.cat_features, f)
            
    def detect_cat(self, image_path):
        """
        检测图片中的猫
        
        Args:
            image_path: 图片路径
            
        Returns:
            list: 检测到的猫的位置列表 [{x, y, width, height, confidence}]
        """
        img = cv2.imread(image_path)
        if img is None:
            return []
            
        # 使用 OpenCV 的猫检测器 (Haar Cascade)
        cat_cascade_path = 'models/haarcascade_frontalcatface.xml'
        
        # 如果没有预下载的 cascade，使用简化检测
        if os.path.exists(cat_cascade_path):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            cascade = cv2.CascadeClassifier(cat_cascade_path)
            cats = cascade.detectMultiScale(gray, 1.3, 5)
            
            results = []
            for (x, y, w, h) in cats:
                results.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'confidence': 0.8
                })
            return results
        else:
            # 简化模式：返回整个图片作为猫的区域
            h, w = img.shape[:2]
            return [{
                'x': 0,
                'y': 0,
                'width': w,
                'height': h,
                'confidence': 0.6
            }]
            
    def extract_features(self, image_path, cat_box=None):
        """
        提取猫脸特征向量
        
        Args:
            image_path: 图片路径
            cat_box: 猫的位置 [x, y, width, height]
            
        Returns:
            np.array: 特征向量
        """
        try:
            img = image.load_img(image_path, target_size=(224, 224))
            img_array = image.img_to_array(img)
            img_array = np.expand_dims(img_array, axis=0)
            img_array = preprocess_input(img_array)
            
            if self.feature_extractor:
                features = self.feature_extractor.predict(img_array, verbose=0)
                return features[0]
            else:
                # 简化模式：使用图片的统计特征
                img_cv = cv2.imread(image_path)
                img_cv = cv2.resize(img_cv, (224, 224))
                return img_cv.flatten()
                
        except Exception as e:
            print(f"特征提取错误：{e}")
            return None
            
    def register_cat(self, cat_id, cat_name, image_paths):
        """
        注册一只新猫咪
        
        Args:
            cat_id: 猫咪 ID
            cat_name: 猫咪名称
            image_paths: 猫咪照片路径列表
            
        Returns:
            bool: 是否成功
        """
        features_list = []
        
        for img_path in image_paths:
            if os.path.exists(img_path):
                features = self.extract_features(img_path)
                if features is not None:
                    features_list.append(features)
        
        if not features_list:
            print(f"⚠ 无法从提供的图片中提取特征")
            return False
            
        # 计算平均特征向量
        avg_features = np.mean(features_list, axis=0)
        
        # 保存到数据库
        self.cat_features[cat_id] = avg_features.tolist()
        self.cat_database[cat_id] = {
            'id': cat_id,
            'name': cat_name,
            'image_count': len(image_paths),
            'registered_at': datetime.now().isoformat()
        }
        
        self._save_cat_database()
        print(f"✓ 猫咪 '{cat_name}' 注册成功")
        return True
        
    def recognize(self, image_path, threshold=0.6):
        """
        识别图片中的猫咪
        
        Args:
            image_path: 图片路径
            threshold: 识别阈值 (0-1)，越高越严格
            
        Returns:
            dict: 识别结果 {cat_id, cat_name, confidence, matched}
        """
        # 检测猫的位置
        cats = self.detect_cat(image_path)
        
        if not cats:
            return {
                'matched': False,
                'message': '未检测到猫',
                'cats_detected': 0
            }
            
        # 提取特征并匹配
        features = self.extract_features(image_path)
        if features is None:
            return {
                'matched': False,
                'message': '特征提取失败',
                'cats_detected': len(cats)
            }
            
        if not self.cat_features:
            return {
                'matched': False,
                'message': '猫咪数据库为空，请先注册猫咪',
                'cats_detected': len(cats)
            }
            
        # 计算与每只猫咪的相似度
        best_match = None
        best_score = 0
        
        for cat_id, cat_features in self.cat_features.items():
            cat_features_np = np.array(cat_features)
            
            # 计算余弦相似度
            similarity = cosine_similarity(
                features.reshape(1, -1),
                cat_features_np.reshape(1, -1)
            )[0][0]
            
            if similarity > best_score:
                best_score = similarity
                best_match = cat_id
                
        # 返回结果
        if best_score >= threshold and best_match:
            cat_info = self.cat_database.get(best_match, {})
            return {
                'matched': True,
                'cat_id': best_match,
                'cat_name': cat_info.get('name', '未知猫咪'),
                'confidence': float(best_score),
                'cats_detected': len(cats)
            }
        else:
            return {
                'matched': False,
                'cat_name': '未知猫咪',
                'confidence': float(best_score),
                'message': f'相似度 {best_score:.2f} 低于阈值 {threshold}',
                'cats_detected': len(cats)
            }
            
    def get_all_cats(self):
        """获取所有已注册的猫咪"""
        return self.cat_database


# 全局识别器实例
_recognizer = None

def get_recognizer():
    """获取全局识别器实例"""
    global _recognizer
    if _recognizer is None:
        _recognizer = CatFaceRecognizer()
    return _recognizer


if __name__ == '__main__':
    # 测试代码
    print("猫脸识别模块测试")
    recognizer = get_recognizer()
    print(f"已注册猫咪：{recognizer.get_all_cats()}")