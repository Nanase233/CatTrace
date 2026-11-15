/* 猫迹 CatTrace 离线版：内置接口数据 + fetch 拦截
 * 由 scripts/build_offline_site.py 生成，请勿手工修改。
 * 作用：双击打开页面时没有后端，这里用打包好的快照数据回应 /api/* 请求。 */
(function () {
  var MOCK = {
  "/api/cats": [
    {
      "adoption_note": "",
      "adoption_ready": false,
      "age": "2 岁",
      "color": "橘白相间",
      "description": "性格活泼，喜欢晒太阳，经常在教学楼后的小花园出现。",
      "feed_count": 156,
      "gender": "female",
      "health": "健康",
      "id": 1,
      "image": "cat1.jpg",
      "location": "A 区 - 教学楼后",
      "name": "咪咪",
      "neutered": true,
      "nickname": "小区一霸",
      "status": "free",
      "views": 1234
    },
    {
      "adoption_note": "",
      "adoption_ready": true,
      "age": "1 岁半",
      "color": "纯黑",
      "description": "夜间活跃，白天喜欢躲在车底下，对人比较警惕。",
      "feed_count": 89,
      "gender": "male",
      "health": "健康",
      "id": 2,
      "image": "cat2.jpg",
      "location": "B 区 - 食堂门口",
      "name": "小黑",
      "neutered": false,
      "nickname": "夜行侠",
      "status": "free",
      "views": 876
    },
    {
      "adoption_note": "",
      "adoption_ready": true,
      "age": "3 岁",
      "color": "纯白",
      "description": "非常亲人，会主动蹭人，是图书馆的常驻猫咪。",
      "feed_count": 234,
      "gender": "female",
      "health": "健康",
      "id": 3,
      "image": "cat3.jpg",
      "location": "C 区 - 图书馆前",
      "name": "雪球",
      "neutered": true,
      "nickname": "棉花糖",
      "status": "free",
      "views": 2156
    },
    {
      "adoption_note": "",
      "adoption_ready": false,
      "age": "4 岁",
      "color": "橘色",
      "description": "体重超标，需要控制饮食，但依然很贪吃。",
      "feed_count": 312,
      "gender": "male",
      "health": "需关注",
      "id": 4,
      "image": "cat4.jpg",
      "location": "D 区 - 操场角落",
      "name": "大橘",
      "neutered": true,
      "nickname": "十斤橘",
      "status": "free",
      "views": 1890
    }
  ],
  "/api/cat/1": {
    "adoption_note": "",
    "adoption_ready": false,
    "age": "2 岁",
    "color": "橘白相间",
    "description": "性格活泼，喜欢晒太阳，经常在教学楼后的小花园出现。",
    "feed_count": 156,
    "gender": "female",
    "health": "健康",
    "id": 1,
    "image": "cat1.jpg",
    "location": "A 区 - 教学楼后",
    "name": "咪咪",
    "neutered": true,
    "nickname": "小区一霸",
    "status": "free",
    "views": 1235
  },
  "/api/cat/2": {
    "adoption_note": "",
    "adoption_ready": true,
    "age": "1 岁半",
    "color": "纯黑",
    "description": "夜间活跃，白天喜欢躲在车底下，对人比较警惕。",
    "feed_count": 89,
    "gender": "male",
    "health": "健康",
    "id": 2,
    "image": "cat2.jpg",
    "location": "B 区 - 食堂门口",
    "name": "小黑",
    "neutered": false,
    "nickname": "夜行侠",
    "status": "free",
    "views": 877
  },
  "/api/stats": {
    "active_users": 42,
    "total_cats": 4,
    "total_feeds": 791,
    "total_views": 6158
  },
  "/api/stats/feed-history": [],
  "/api/notifications": [],
  "/api/notifications/unread-count": {
    "count": 0
  },
  "/api/feed-logs?limit=10": [],
  "/api/feed-logs?limit=5": [],
  "/api/reports": [],
  "/api/volunteers": [],
  "/api/emergency/alerts": [],
  "/api/diaries?page=1&per_page=50": {
    "diaries": [
      {
        "cat_color": "橘白相间",
        "cat_id": 1,
        "cat_location": "A 区 - 教学楼后",
        "cat_name": "咪咪",
        "cat_nickname": "小区一霸",
        "comments": [
          {
            "text": "咪咪太可爱了！",
            "time": "2026-09-28T14:30:00",
            "user": "小花妈妈"
          }
        ],
        "content": "咪咪今天来了 3 次，最喜欢中午那顿。它吃得很安心，还对着摄像头打了个哈欠。阳光很好，它在猫屋旁边晒了一下午的太阳。",
        "date": "2026-09-28",
        "duration": 45,
        "id": 1,
        "likes": 12,
        "mood": "开心",
        "visits": 3
      },
      {
        "cat_color": "纯黑",
        "cat_id": 2,
        "cat_location": "B 区 - 食堂门口",
        "cat_name": "小黑",
        "cat_nickname": "夜行侠",
        "comments": [],
        "content": "小黑今天特别活跃，在猫屋周围跑了好几圈。来的时候夜幕降临，它警惕地蹭了蹭猫屋。深夜才开始放松下来，舔了舔爪子。",
        "date": "2026-09-28",
        "duration": 30,
        "id": 2,
        "likes": 8,
        "mood": "警惕",
        "visits": 2
      },
      {
        "cat_color": "纯白",
        "cat_id": 3,
        "cat_location": "C 区 - 图书馆前",
        "cat_name": "雪球",
        "cat_nickname": "棉花糖",
        "comments": [
          {
            "text": "雪球是图书馆的镇馆之宝！",
            "time": "2026-09-28T10:15:00",
            "user": "图书馆常客"
          },
          {
            "text": "每次复习累了看看雪球就很治愈",
            "time": "2026-09-28T16:42:00",
            "user": "考研人"
          }
        ],
        "content": "清晨六点，雪球第一个来到猫屋。它轻轻叫了一声，开启了元气满满的一天。今天来了图书馆看书的同学们都忍不住去摸它。",
        "date": "2026-09-28",
        "duration": 60,
        "id": 3,
        "likes": 23,
        "mood": "温柔",
        "visits": 5
      },
      {
        "cat_color": "橘色",
        "cat_id": 4,
        "cat_location": "D 区 - 操场角落",
        "cat_name": "大橘",
        "cat_nickname": "十斤橘",
        "comments": [
          {
            "text": "大橘又胖了一圈哈哈",
            "time": "2026-09-28T18:20:00",
            "user": "操场跑步者"
          }
        ],
        "content": "大橘今天来了 4 次，每次停留约 20 分钟。它最喜欢的中午那顿似乎胃口很好，吃得干干净净。不过体重管理提醒已触发，需要关注。",
        "date": "2026-09-28",
        "duration": 20,
        "id": 4,
        "likes": 15,
        "mood": "慵懒",
        "visits": 4
      },
      {
        "cat_color": "橘白相间",
        "cat_id": 1,
        "cat_location": "A 区 - 教学楼后",
        "cat_name": "咪咪",
        "cat_nickname": "小区一霸",
        "comments": [],
        "content": "咪咪今天似乎有些慵懒，在猫屋待了 35 分钟。它伸了个懒腰，可能是在等它的猫朋友小黑。傍晚时分终于等到了一起玩耍。",
        "date": "2026-09-27",
        "duration": 35,
        "id": 5,
        "likes": 9,
        "mood": "慵懒",
        "visits": 2
      },
      {
        "cat_color": "纯白",
        "cat_id": 3,
        "cat_location": "C 区 - 图书馆前",
        "cat_name": "雪球",
        "cat_nickname": "棉花糖",
        "comments": [
          {
            "text": "第一次见到这么亲人的猫！",
            "time": "2026-09-27T11:00:00",
            "user": "大一新生"
          }
        ],
        "content": "雪球今天来了 4 次，每次停留约 15 分钟。微风习习的天气里，它在图书馆门前的大树下乘凉，还眯了眯眼睛享受午后时光。",
        "date": "2026-09-27",
        "duration": 15,
        "id": 6,
        "likes": 18,
        "mood": "放松",
        "visits": 4
      },
      {
        "cat_color": "纯黑",
        "cat_id": 2,
        "cat_location": "B 区 - 食堂门口",
        "cat_name": "小黑",
        "cat_nickname": "夜行侠",
        "comments": [],
        "content": "小黑今天似乎有些好奇，在猫屋待了 25 分钟。它甩了甩尾巴，可能是在研究新装的摄像头。深夜食堂门口只有它一个守夜人。",
        "date": "2026-09-27",
        "duration": 25,
        "id": 7,
        "likes": 6,
        "mood": "好奇",
        "visits": 1
      },
      {
        "cat_color": "橘色",
        "cat_id": 4,
        "cat_location": "D 区 - 操场角落",
        "cat_name": "大橘",
        "cat_nickname": "十斤橘",
        "comments": [],
        "content": "大橘今天特别活跃，在操场角落的猫屋周围跑了好几圈。来的时候天气暖和，它开心地蹭了蹭猫屋。投喂了两次猫粮都吃光了。",
        "date": "2026-09-27",
        "duration": 30,
        "id": 8,
        "likes": 11,
        "mood": "开心",
        "visits": 3
      },
      {
        "cat_color": "橘白相间",
        "cat_id": 1,
        "cat_location": "A 区 - 教学楼后",
        "cat_name": "咪咪",
        "cat_nickname": "小区一霸",
        "comments": [
          {
            "text": "雨后的咪咪好治愈",
            "time": "2026-09-26T07:30:00",
            "user": "早起的同学"
          }
        ],
        "content": "刚下过雨的清晨，咪咪第一个来到教学楼后的猫屋。它舔了舔爪子，在湿润的草地上踩了几个小脚印。今天的它格外安静温柔。",
        "date": "2026-09-26",
        "duration": 40,
        "id": 9,
        "likes": 14,
        "mood": "温柔",
        "visits": 2
      },
      {
        "cat_color": "纯白",
        "cat_id": 3,
        "cat_location": "C 区 - 图书馆前",
        "cat_name": "雪球",
        "cat_nickname": "棉花糖",
        "comments": [
          {
            "text": "雪球今天把好几本书都当枕头了",
            "time": "2026-09-26T15:00:00",
            "user": "图书馆管理员"
          },
          {
            "text": "给雪球拍了今天的写真！",
            "time": "2026-09-26T17:30:00",
            "user": "志愿者小王"
          }
        ],
        "content": "雪球今天来了 6 次！创下了本周最高记录。它最喜欢的下午时段来了好几波同学，每个人都忍不住给它加了餐。图书馆的人气王非它莫属。",
        "date": "2026-09-26",
        "duration": 50,
        "id": 10,
        "likes": 31,
        "mood": "开心",
        "visits": 6
      }
    ],
    "page": 1,
    "per_page": 50,
    "success": true,
    "total": 10,
    "total_pages": 1
  },
  "/api/diaries/1": {
    "cat": {
      "color": "橘白相间",
      "feed_count": 156,
      "health": "健康",
      "id": 1,
      "location": "A 区 - 教学楼后",
      "name": "咪咪",
      "neutered": true,
      "nickname": "小区一霸",
      "views": 1235
    },
    "diaries": [
      {
        "cat_id": 1,
        "comments": [
          {
            "text": "咪咪太可爱了！",
            "time": "2026-09-28T14:30:00",
            "user": "小花妈妈"
          }
        ],
        "content": "咪咪今天来了 3 次，最喜欢中午那顿。它吃得很安心，还对着摄像头打了个哈欠。阳光很好，它在猫屋旁边晒了一下午的太阳。",
        "date": "2026-09-28",
        "duration": 45,
        "id": 1,
        "likes": 12,
        "mood": "开心",
        "visits": 3
      },
      {
        "cat_id": 1,
        "comments": [],
        "content": "咪咪今天似乎有些慵懒，在猫屋待了 35 分钟。它伸了个懒腰，可能是在等它的猫朋友小黑。傍晚时分终于等到了一起玩耍。",
        "date": "2026-09-27",
        "duration": 35,
        "id": 5,
        "likes": 9,
        "mood": "慵懒",
        "visits": 2
      },
      {
        "cat_id": 1,
        "comments": [
          {
            "text": "雨后的咪咪好治愈",
            "time": "2026-09-26T07:30:00",
            "user": "早起的同学"
          }
        ],
        "content": "刚下过雨的清晨，咪咪第一个来到教学楼后的猫屋。它舔了舔爪子，在湿润的草地上踩了几个小脚印。今天的它格外安静温柔。",
        "date": "2026-09-26",
        "duration": 40,
        "id": 9,
        "likes": 14,
        "mood": "温柔",
        "visits": 2
      }
    ],
    "success": true
  },
  "/api/finance/summary": {
    "categories": {},
    "expense_by_category": {},
    "income_by_category": {},
    "success": true,
    "summary": {
      "balance": 0,
      "month_expense": 0,
      "month_income": 0,
      "total_expense": 0,
      "total_income": 0,
      "transaction_count": 0
    }
  },
  "/api/finance/transactions": {
    "categories": {},
    "page": 1,
    "per_page": 20,
    "success": true,
    "total": 0,
    "total_pages": 1,
    "transactions": []
  },
  "/api/finance/monthly": {
    "monthly": [],
    "success": true
  },
  "/api/learning/insights": {
    "cats_tracked": 0,
    "generated_at": "2026-11-15T23:39:48",
    "insights": [
      "平台累计记录 0 次投喂行为",
      "有 0 位活跃用户（投喂 3 次以上）"
    ],
    "total_feeds_analyzed": 0,
    "users_tracked": 0
  },
  "/api/learning/anomalies": {
    "anomalies": [],
    "count": 0,
    "success": true
  },
  "/api/live/info": {
    "enabled": false,
    "ok": true,
    "snapshot_url": null,
    "stats_url": null,
    "stream_url": null
  },
  "/api/location/1": {
    "cat_id": 1,
    "cat_name": "咪咪",
    "is_precise": false,
    "location": "A 区"
  }
};

  /* 页面里写死的一两个取不到数据的接口，给一份兜底，避免界面空白 */
  var FALLBACK = {
    '/api/cats': { 'success': true, 'cats': [] },
    '/api/stats': { 'success': true, 'total_cats': 0, 'total_feeds': 0, 'total_views': 0, 'active_users': 0 }
  };

  /* 写操作（投喂、领养申请等）在离线版里只做本地成功回执，不改动快照数据 */
  var POST_RESULTS = {
  "/api/feed": {
    "success": true,
    "message": "投喂成功（离线演示模式，数据不会上传）",
    "feed_count": 1
  },
  "/api/feed-as-guest": {
    "success": true,
    "message": "投喂成功（离线演示模式）",
    "remaining": 0
  },
  "/api/adopt/apply": {
    "success": true,
    "message": "申请已提交（离线演示模式）"
  },
  "/api/volunteer/apply": {
    "success": true,
    "message": "报名已提交（离线演示模式）"
  },
  "/api/report": {
    "success": true,
    "message": "举报已提交（离线演示模式）"
  },
  "/api/report-abuse": {
    "success": true,
    "message": "举报已提交（离线演示模式）"
  },
  "/api/cleanup-logs": {
    "success": true,
    "message": "清理记录已提交（离线演示模式）"
  },
  "/api/auth/login": {
    "success": true,
    "token": "offline-demo-token",
    "user": {
      "id": 1,
      "username": "爱心用户",
      "role": "user"
    }
  },
  "/api/auth/logout": {
    "success": true
  },
  "/api/auth/me": {
    "success": true,
    "user": {
      "id": 1,
      "username": "爱心用户",
      "role": "user"
    }
  },
  "/api/diaries/1/like": {
    "success": true,
    "likes": 13
  },
  "/api/diaries/2/like": {
    "success": true,
    "likes": 9
  },
  "/api/diaries/1/comment": {
    "success": true,
    "message": "评论已提交（离线演示模式）"
  },
  "/api/recognize": {
    "success": true,
    "message": "离线演示模式未接入识别模型",
    "cat": {
      "id": 1,
      "name": "咪咪"
    }
  },
  "/api/cat/register": {
    "success": true,
    "message": "已登记（离线演示模式）"
  },
  "*": {
    "success": true,
    "message": "离线演示模式：操作不会上传到服务器"
  }
};

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function jsonResponse(data, status) {
    return new Response(JSON.stringify(data), {
      status: status || 200,
      headers: { 'Content-Type': 'application/json; charset=utf-8' }
    });
  }

  function lookup(pathname) {
    if (Object.prototype.hasOwnProperty.call(MOCK, pathname)) { return MOCK[pathname]; }
    if (Object.prototype.hasOwnProperty.call(FALLBACK, pathname)) { return FALLBACK[pathname]; }
    /* /api/cat/<id> 之类的路径：按前缀找最近的快照 */
    var best = null;
    Object.keys(MOCK).forEach(function (key) {
      var keyPath = key.split('?')[0];
      if (pathname.indexOf(keyPath) === 0 && (!best || keyPath.length > best.length)) { best = keyPath; }
    });
    if (best) { return MOCK[best]; }
    /* /api/diaries?cat_id=1：去掉查询串后再试一次 */
    return null;
  }

  window.fetch = function (input, init) {
    var url = (typeof input === 'string') ? input : (input && input.url) || '';
    var method = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    var pathname = url.split('?')[0];
    if (pathname.charAt(0) === '.') { pathname = pathname.replace(/^\./, ''); }
    if (pathname.charAt(0) !== '/') { pathname = '/' + pathname; }

    var payload = null;
    if (method === 'GET' || method === 'HEAD') {
      payload = lookup(pathname);
      if (payload === null) {
        payload = POST_RESULTS['*'] || { 'success': true };
      }
      return Promise.resolve(jsonResponse(clone(payload)));
    }
    var post = POST_RESULTS[pathname];
    if (!post) {
      Object.keys(POST_RESULTS).forEach(function (key) {
        if (!post && key !== '*' && pathname.indexOf(key.split('?')[0]) === 0) { post = POST_RESULTS[key]; }
      });
    }
    return Promise.resolve(jsonResponse(clone(post || POST_RESULTS['*'] || { 'success': true })));
  };

  /* 少数地方直接用 XMLHttpRequest（例如 PWA 检测），一并走快照数据 */
  var NativeXHR = window.XMLHttpRequest;
  if (NativeXHR) {
    window.XMLHttpRequest = function () {
      var xhr = new NativeXHR();
      var self = this;
      this.open = function (method, url) {
        self.__url = url; self.__method = (method || 'GET').toUpperCase();
        return xhr.open.apply(xhr, arguments);
      };
      this.send = function () {
        var payload = (self.__method === 'GET') ? (lookup(String(self.__url || '').split('?')[0]) || MOCK['/api/stats']) : (POST_RESULTS['*'] || { 'success': true });
        var text = JSON.stringify(payload || {});
        Object.defineProperty(xhr, 'readyState', { value: 4, configurable: true });
        Object.defineProperty(xhr, 'status', { value: 200, configurable: true });
        Object.defineProperty(xhr, 'responseText', { value: text, configurable: true });
        Object.defineProperty(xhr, 'response', { value: text, configurable: true });
        if (typeof self.onreadystatechange === 'function') { self.onreadystatechange(); }
        if (typeof self.onload === 'function') { self.onload(); }
      };
      this.setRequestHeader = function () { return xhr.setRequestHeader.apply(xhr, arguments); };
      this.getAllResponseHeaders = function () { return 'content-type: application/json\r\n'; };
    };
  }
}());
