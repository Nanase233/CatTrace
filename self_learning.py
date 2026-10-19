"""
CatTrace 自学习引擎 (Self-Learning Engine)
============================================
通过分析用户行为和猫咪数据，自动学习模式、发现异常、生成推荐。

四大核心能力：
  1. 猫咪行为模式学习 - 学习每只猫的活跃时段、进食频率、情绪规律
  2. 用户偏好学习     - 学习每个用户的关注偏好、活跃时间、参与度
  3. 异常检测与健康预警 - 自动发现数据异常，计算健康评分
  4. 识别自优化       - 通过用户反馈持续改进识别准确率

作者：CatTrace 项目组
版本：v1.0
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json
import os


class SelfLearningEngine:
    """
    CatTrace 自学习引擎

    用法:
        engine = SelfLearningEngine('data.json')
        engine.on_feed(cat_id=1, user_id='u123', user_name='小明')
        profile = engine.get_cat_profile(1)
        recs = engine.get_recommendations('u123')
        anomalies = engine.detect_anomalies()
    """

    def __init__(self, data_file='data.json'):
        self.data_file = data_file
        self.model_version = 'v1.0'
        self._cat_profiles = {}
        self._user_prefs = {}
        self._feedback_log = []
        self._anomaly_records = []
        self._load()

    # ------------------------------------------------------------------ #
    #                        数据持久化                                    #
    # ------------------------------------------------------------------ #

    def _load(self):
        """从 data.json 加载学习数据"""
        if not os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return
        learning = data.get('learning', {})
        self._cat_profiles = learning.get('cat_profiles', {})
        self._user_prefs = learning.get('user_preferences', {})
        self._feedback_log = learning.get('feedback_log', [])
        self._anomaly_records = learning.get('anomaly_records', [])

    def _save_to_data(self, data):
        """将学习数据写回 data.json"""
        data['learning'] = {
            'cat_profiles': self._cat_profiles,
            'user_preferences': self._user_prefs,
            'feedback_log': self._feedback_log,
            'anomaly_records': self._anomaly_records,
            'model_version': self.model_version,
            'last_updated': datetime.now().isoformat(timespec='seconds')
        }

    # ------------------------------------------------------------------ #
    #                   能力一：猫咪行为模式学习                             #
    # ------------------------------------------------------------------ #

    def on_feed(self, cat_id, user_id=None, user_name=None):
        """记录一次投喂事件，更新猫咪画像和用户画像"""
        now = datetime.now()
        cat_key = str(cat_id)

        if cat_key not in self._cat_profiles:
            self._cat_profiles[cat_key] = {
                'cat_id': cat_id,
                'total_observations': 0,
                'feed_hours': [],
                'daily_feed_counts': {},
                'last_seen': None,
                'feeding_users': [],
                'anomaly_flags': []
            }

        profile = self._cat_profiles[cat_key]
        profile['total_observations'] += 1
        profile['feed_hours'].append(now.hour)
        profile['last_seen'] = now.isoformat(timespec='seconds')

        today = now.strftime('%Y-%m-%d')
        daily = profile.get('daily_feed_counts', {})
        daily[today] = daily.get(today, 0) + 1
        profile['daily_feed_counts'] = daily

        if user_id:
            users = profile.get('feeding_users', [])
            users.append(user_id)
            profile['feeding_users'] = users[-100:]
            self._update_user_preference(user_id, cat_id, now, user_name)

    def on_view(self, cat_id, user_id=None):
        """记录一次浏览事件"""
        if user_id:
            key = str(user_id)
            if key not in self._user_prefs:
                self._user_prefs[key] = self._new_user_pref(user_id)
            viewed = self._user_prefs[key].get('viewed_cats', [])
            viewed.append(cat_id)
            self._user_prefs[key]['viewed_cats'] = viewed[-200:]

    def _update_user_preference(self, user_id, cat_id, timestamp, user_name=None):
        """更新用户偏好"""
        key = str(user_id)
        if key not in self._user_prefs:
            self._user_prefs[key] = self._new_user_pref(user_id, user_name)

        pref = self._user_prefs[key]
        pref['total_feeds'] = pref.get('total_feeds', 0) + 1
        pref['feed_hours'].append(timestamp.hour)
        pref['last_active'] = timestamp.isoformat(timespec='seconds')

        cat_feeds = pref.get('cat_feed_counts', {})
        cat_key = str(cat_id)
        cat_feeds[cat_key] = cat_feeds.get(cat_key, 0) + 1
        pref['cat_feed_counts'] = cat_feeds

        last_date = pref.get('last_feed_date')
        today = timestamp.strftime('%Y-%m-%d')
        if last_date:
            try:
                d1 = datetime.strptime(last_date, '%Y-%m-%d')
                d2 = datetime.strptime(today, '%Y-%m-%d')
                if (d2 - d1).days == 1:
                    pref['consecutive_days'] = pref.get('consecutive_days', 1) + 1
                elif (d2 - d1).days > 1:
                    pref['consecutive_days'] = 1
            except Exception:
                pref['consecutive_days'] = 1
        else:
            pref['consecutive_days'] = 1
        pref['last_feed_date'] = today

    def _new_user_pref(self, user_id, user_name=None):
        """创建空白用户偏好"""
        return {
            'user_id': user_id,
            'user_name': user_name or '',
            'total_feeds': 0,
            'total_comments': 0,
            'feed_hours': [],
            'cat_feed_counts': {},
            'viewed_cats': [],
            'consecutive_days': 0,
            'last_active': None,
            'last_feed_date': None,
            'engagement_level': 'new'
        }

    def analyze_diary_moods(self, diaries):
        """从日记数据学习猫咪情绪规律"""
        mood_by_cat = defaultdict(list)
        for d in diaries:
            cat_key = str(d.get('cat_id'))
            mood_by_cat[cat_key].append({
                'mood': d.get('mood', '未知'),
                'date': d.get('date', ''),
                'visits': d.get('visits', 0),
                'duration': d.get('duration', 0)
            })

        for cat_key, moods in mood_by_cat.items():
            if cat_key not in self._cat_profiles:
                self._cat_profiles[cat_key] = {
                    'cat_id': int(cat_key),
                    'total_observations': 0,
                    'feed_hours': [],
                    'daily_feed_counts': {},
                    'last_seen': None,
                    'feeding_users': [],
                    'anomaly_flags': []
                }
            profile = self._cat_profiles[cat_key]
            mood_counts = Counter(m['mood'] for m in moods)
            profile['mood_distribution'] = dict(mood_counts)
            profile['dominant_mood'] = mood_counts.most_common(1)[0][0] if mood_counts else '未知'
            profile['avg_daily_visits'] = round(
                sum(m['visits'] for m in moods) / max(len(moods), 1), 1
            )

    # ------------------------------------------------------------------ #
    #                  能力二：用户偏好 → 个性化推荐                        #
    # ------------------------------------------------------------------ #

    def _get_favorite_cat(self, pref):
        """获取用户最喜欢的猫（投喂次数最多）"""
        cat_feeds = pref.get('cat_feed_counts', {})
        if not cat_feeds:
            return None
        return int(max(cat_feeds, key=cat_feeds.get))

    def _get_cat_name(self, cat_id):
        """从 data.json 获取猫咪名字"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for cat in data.get('cats', []):
                if cat.get('id') == cat_id:
                    return cat.get('name', f'猫咪#{cat_id}')
        except Exception:
            pass
        return f'猫咪#{cat_id}'

    def get_recommendations(self, user_id):
        """根据用户偏好生成个性化推荐"""
        key = str(user_id)
        pref = self._user_prefs.get(key)
        if not pref:
            return [{
                'type': 'welcome',
                'message': '欢迎来到 CatTrace！先去看看我们的猫咪吧 🐱',
                'cat_id': None
            }]

        recs = []
        fav_cat = self._get_favorite_cat(pref)

        if fav_cat:
            cat_key = str(fav_cat)
            profile = self._cat_profiles.get(cat_key, {})
            today = datetime.now().strftime('%Y-%m-%d')
            today_feeds = profile.get('daily_feed_counts', {}).get(today, 0)
            if today_feeds == 0:
                cat_name = self._get_cat_name(fav_cat)
                recs.append({
                    'type': 'feed_reminder',
                    'message': f'你关注的{cat_name}今天还没吃饭哦，要不要投喂一下？ 🍖',
                    'cat_id': fav_cat
                })

        days = pref.get('consecutive_days', 0)
        if days >= 7:
            recs.append({
                'type': 'achievement',
                'message': f'你已经连续 {days} 天投喂了！考虑成为猫咪的守护者吧 💛',
                'cat_id': fav_cat
            })
        elif days >= 3:
            recs.append({
                'type': 'streak',
                'message': f'连续投喂 {days} 天了，继续保持！ 🎉',
                'cat_id': fav_cat
            })

        hours = pref.get('feed_hours', [])
        if hours:
            now_hour = datetime.now().hour
            common_hour = Counter(hours).most_common(1)[0][0]
            if abs(now_hour - common_hour) <= 1:
                recs.append({
                    'type': 'time_match',
                    'message': '现在是你的常用投喂时间，来看看猫咪吧 ⏰',
                    'cat_id': fav_cat
                })

        if pref.get('total_feeds', 0) < 3:
            recs.append({
                'type': 'onboarding',
                'message': '试试投喂一只猫咪，让它记住你 🐾',
                'cat_id': None
            })

        return recs

    # ------------------------------------------------------------------ #
    #                 能力三：异常检测与健康预警                             #
    # ------------------------------------------------------------------ #

    def detect_anomalies(self):
        """扫描所有猫咪数据，检测异常模式"""
        anomalies = []
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')

        for cat_key, profile in self._cat_profiles.items():
            cat_id = profile.get('cat_id', int(cat_key))
            cat_name = self._get_cat_name(cat_id)
            daily = profile.get('daily_feed_counts', {})

            last_seen = profile.get('last_seen')
            if last_seen:
                try:
                    last_dt = datetime.fromisoformat(last_seen)
                    days_missing = (now - last_dt).days
                    if days_missing >= 3:
                        anomalies.append({
                            'type': 'cat_missing',
                            'severity': 'high' if days_missing >= 5 else 'medium',
                            'cat_id': cat_id,
                            'cat_name': cat_name,
                            'message': f'{cat_name}已经 {days_missing} 天没有出现了',
                            'detected_at': now.isoformat(timespec='seconds')
                        })
                except Exception:
                    pass

            if len(daily) >= 3:
                avg_feeds = sum(daily.values()) / len(daily)
                today_feeds = daily.get(today, 0)
                if avg_feeds > 0 and today_feeds > avg_feeds * 2:
                    anomalies.append({
                        'type': 'overfeeding',
                        'severity': 'medium',
                        'cat_id': cat_id,
                        'cat_name': cat_name,
                        'message': f'{cat_name}今天被投喂 {today_feeds} 次，远超日常 {avg_feeds:.1f} 次',
                        'detected_at': now.isoformat(timespec='seconds')
                    })

            mood_dist = profile.get('mood_distribution', {})
            dominant = profile.get('dominant_mood', '')
            if dominant in ['警惕', '低落', '不安']:
                anomalies.append({
                    'type': 'mood_concern',
                    'severity': 'low',
                    'cat_id': cat_id,
                    'cat_name': cat_name,
                    'message': f'{cat_name}近期情绪以"{dominant}"为主，建议关注',
                    'detected_at': now.isoformat(timespec='seconds')
                })

        self._anomaly_records = anomalies
        return anomalies

    def compute_health_score(self, cat_id):
        """计算某只猫的健康评分（0-100 分）"""
        cat_key = str(cat_id)
        profile = self._cat_profiles.get(cat_key, {})
        cat_name = self._get_cat_name(cat_id)

        score = 70
        breakdown = {'基础分': 70}

        daily = profile.get('daily_feed_counts', {})
        if len(daily) >= 3:
            values = list(daily.values())
            avg = sum(values) / len(values)
            if avg > 0:
                variance = sum((v - avg) ** 2 for v in values) / len(values)
                std = variance ** 0.5
                cv = std / avg
                regularity_score = max(0, 15 - int(cv * 15))
            else:
                regularity_score = 0
            score += regularity_score
            breakdown['进食规律分'] = regularity_score
        else:
            breakdown['进食规律分'] = 0

        mood_dist = profile.get('mood_distribution', {})
        if mood_dist:
            total = sum(mood_dist.values())
            positive_moods = ['开心', '放松', '温柔']
            positive_ratio = sum(mood_dist.get(m, 0) for m in positive_moods) / max(total, 1)
            mood_score = int(positive_ratio * 10)
            score += mood_score
            breakdown['情绪稳定分'] = mood_score
        else:
            breakdown['情绪稳定分'] = 0

        if len(daily) >= 2:
            sorted_days = sorted(daily.items())
            recent = [v for _, v in sorted_days[-3:]]
            older = [v for _, v in sorted_days[:-3]] if len(sorted_days) > 3 else []
            if older and recent:
                recent_avg = sum(recent) / len(recent)
                older_avg = sum(older) / len(older)
                if older_avg > 0:
                    trend = (recent_avg - older_avg) / older_avg
                    trend_score = min(5, max(0, int(trend * 10 + 2.5)))
                else:
                    trend_score = 3
            else:
                trend_score = 3
            score += trend_score
            breakdown['活跃趋势分'] = trend_score
        else:
            breakdown['活跃趋势分'] = 0

        anomaly_penalty = 0
        for a in self._anomaly_records:
            if a.get('cat_id') == cat_id:
                if a.get('severity') == 'high':
                    anomaly_penalty += 15
                elif a.get('severity') == 'medium':
                    anomaly_penalty += 10
                else:
                    anomaly_penalty += 5
        anomaly_penalty = min(30, anomaly_penalty)
        score -= anomaly_penalty
        breakdown['异常扣分'] = -anomaly_penalty

        score = max(0, min(100, score))

        if score >= 85:
            advice = f'{cat_name}状态很好，继续保持！ 🌟'
        elif score >= 70:
            advice = f'{cat_name}状态正常，可以多加关注。'
        elif score >= 50:
            advice = f'{cat_name}状态需要关注，建议志愿者实地查看。 ⚠️'
        else:
            advice = f'{cat_name}状态异常，请尽快安排志愿者检查！ 🚨'

        return {
            'cat_id': cat_id,
            'cat_name': cat_name,
            'score': score,
            'breakdown': breakdown,
            'advice': advice,
            'computed_at': datetime.now().isoformat(timespec='seconds')
        }

    # ------------------------------------------------------------------ #
    #                   能力四：识别自优化                                  #
    # ------------------------------------------------------------------ #

    def record_feedback(self, predicted_cat_id, actual_cat_id, confidence,
                        image_path=None):
        """记录识别反馈，用于自优化"""
        self._feedback_log.append({
            'predicted': predicted_cat_id,
            'actual': actual_cat_id,
            'confidence': confidence,
            'correct': predicted_cat_id == actual_cat_id,
            'image': image_path,
            'time': datetime.now().isoformat(timespec='seconds')
        })

    def get_accuracy_stats(self):
        """获取识别准确率统计"""
        if not self._feedback_log:
            return {'total': 0, 'correct': 0, 'accuracy': 0}
        correct = sum(1 for f in self._feedback_log if f.get('correct'))
        total = len(self._feedback_log)
        recent = self._feedback_log[-20:]
        recent_correct = sum(1 for f in recent if f.get('correct'))
        recent_acc = round(recent_correct / len(recent) * 100, 1) if recent else 0
        return {
            'total': total,
            'correct': correct,
            'accuracy': round(correct / total * 100, 1) if total > 0 else 0,
            'recent_accuracy': recent_acc
        }

    # ------------------------------------------------------------------ #
    #                    综合输出接口                                       #
    # ------------------------------------------------------------------ #

    def get_cat_profile(self, cat_id):
        """获取某只猫的完整学习画像"""
        cat_key = str(cat_id)
        profile = self._cat_profiles.get(cat_key)
        if not profile:
            return {
                'cat_id': cat_id,
                'cat_name': self._get_cat_name(cat_id),
                'status': 'new',
                'message': '还没有足够的数据来分析这只猫咪的行为模式'
            }

        hours = profile.get('feed_hours', [])
        peak_hours = []
        if hours:
            hour_counts = Counter(hours)
            peak_hours = [h for h, _ in hour_counts.most_common(4)]

        daily = profile.get('daily_feed_counts', {})
        avg_daily = round(sum(daily.values()) / max(len(daily), 1), 1)

        if len(daily) >= 3:
            sorted_days = sorted(daily.items())
            recent_avg = sum(v for _, v in sorted_days[-3:]) / 3
            older_vals = [v for _, v in sorted_days[:-3]]
            if older_vals:
                older_avg = sum(older_vals) / len(older_vals)
                if older_avg > 0:
                    change = (recent_avg - older_avg) / older_avg
                    if change > 0.2:
                        trend = '上升'
                    elif change < -0.2:
                        trend = '下降'
                    else:
                        trend = '稳定'
                else:
                    trend = '数据不足'
            else:
                trend = '数据不足'
        else:
            trend = '数据不足'

        cat_name = self._get_cat_name(cat_id)
        insights = []
        if peak_hours:
            hour_desc = '、'.join(f'{h} 点' for h in sorted(peak_hours[:2]))
            insights.append(f'{cat_name}在{hour_desc}最活跃')
        if avg_daily > 0:
            insights.append(f'日均被投喂 {avg_daily} 次')
        dominant = profile.get('dominant_mood')
        if dominant:
            insights.append(f'主要情绪：{dominant}')

        return {
            'cat_id': cat_id,
            'cat_name': cat_name,
            'total_observations': profile.get('total_observations', 0),
            'peak_hours': sorted(peak_hours),
            'avg_daily_feeds': avg_daily,
            'dominant_mood': profile.get('dominant_mood', '未知'),
            'mood_distribution': profile.get('mood_distribution', {}),
            'feeding_trend': trend,
            'last_seen': profile.get('last_seen'),
            'unique_feeders': len(set(profile.get('feeding_users', []))),
            'insights': insights,
            'health_score': self.compute_health_score(cat_id)
        }

    def get_user_profile(self, user_id):
        """获取用户偏好画像"""
        key = str(user_id)
        pref = self._user_prefs.get(key)
        if not pref:
            return {
                'user_id': user_id,
                'status': 'new',
                'message': '还没有足够的数据来分析用户偏好'
            }

        fav_cat = self._get_favorite_cat(pref)
        hours = pref.get('feed_hours', [])
        preferred_time = []
        if hours:
            preferred_time = [h for h, _ in Counter(hours).most_common(3)]

        total = pref.get('total_feeds', 0)
        if total >= 20:
            level = 'high'
        elif total >= 5:
            level = 'medium'
        elif total >= 1:
            level = 'low'
        else:
            level = 'new'
        pref['engagement_level'] = level

        return {
            'user_id': user_id,
            'user_name': pref.get('user_name', ''),
            'favorite_cat': fav_cat,
            'favorite_cat_name': self._get_cat_name(fav_cat) if fav_cat else None,
            'preferred_time': preferred_time,
            'engagement_level': level,
            'total_feeds': total,
            'consecutive_days': pref.get('consecutive_days', 0),
            'last_active': pref.get('last_active'),
            'suggested_actions': self.get_recommendations(user_id)
        }

    def get_global_insights(self):
        """生成全局模式洞察"""
        insights = []
        total_feeds = 0
        all_hours = []

        for cat_key, profile in self._cat_profiles.items():
            total_feeds += profile.get('total_observations', 0)
            all_hours.extend(profile.get('feed_hours', []))

        if all_hours:
            top_hours = Counter(all_hours).most_common(3)
            hour_desc = '、'.join(f'{h} 点' for h, _ in top_hours)
            insights.append(f'平台用户最喜欢在{hour_desc}投喂猫咪')

        if self._cat_profiles:
            most_popular = max(
                self._cat_profiles.items(),
                key=lambda x: x[1].get('total_observations', 0)
            )
            cat_name = self._get_cat_name(most_popular[1].get('cat_id'))
            insights.append(f'{cat_name}是最受欢迎的猫咪（{most_popular[1].get("total_observations", 0)} 次投喂）')

        insights.append(f'平台累计记录 {total_feeds} 次投喂行为')

        active_users = sum(
            1 for p in self._user_prefs.values()
            if p.get('total_feeds', 0) >= 3
        )
        insights.append(f'有 {active_users} 位活跃用户（投喂 3 次以上）')

        return {
            'total_feeds_analyzed': total_feeds,
            'cats_tracked': len(self._cat_profiles),
            'users_tracked': len(self._user_prefs),
            'insights': insights,
            'generated_at': datetime.now().isoformat(timespec='seconds')
        }

    def retrain(self):
        """触发模型重新训练（当前版本为规则引擎，重新扫描全量数据）"""
        self._load()
        self.detect_anomalies()
        return {
            'success': True,
            'message': '模型重新训练完成',
            'cats_analyzed': len(self._cat_profiles),
            'users_analyzed': len(self._user_prefs),
            'anomalies_found': len(self._anomaly_records),
            'model_version': self.model_version
        }