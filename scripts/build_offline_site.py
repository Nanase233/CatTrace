#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 Flask 站点（templates/ + static/）导出为可双击打开的离线站点。

背景：仓库根目录的 index.html / demo.html 是 9 月的旧版原型页，而
templates/ 下的首页、云直播、猫咪档案、领养中心、AI 日记才是最新网页。
这些页面依赖后端 /api/* 接口，直接双击打开只会有空数据，所以本脚本：

1. 用 Flask 测试客户端渲染每个页面的最终 HTML；
2. 把 /static/ 资源路径改成相对路径（static/...），去掉 cache-bust 查询串，
   让 file:// 下也能加载 CSS/JS；
3. 把页内跳转改成同名 .html 文件；
4. 采集所有前端用到的 /api/* 返回数据，写入 static/js/offline-mock.js，
   该脚本在页面脚本之前劫持 window.fetch，用内置数据回应接口请求。

用法：
    python scripts/build_offline_site.py
产物：
    index.html / live.html / cats.html / adopt.html / diary.html
    static/js/offline-mock.js
"""

import json
import os
import re
import sys
import tempfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# 必须在 import app 之前指定数据文件，避免污染仓库里的 data.json。
OFFLINE_TMP = tempfile.mkdtemp(prefix='cattrace-offline-')
os.environ.setdefault('PROJECTCAT_DATA_FILE', os.path.join(OFFLINE_TMP, 'data.json'))
os.environ.setdefault('PROJECTCAT_LIVE_URL', '')  # 离线版不代理树莓派视频流

import app as app_module  # noqa: E402


PAGES = [
    ('/', 'index.html'),
    ('/cats', 'cats.html'),
    ('/adopt', 'adopt.html'),
    ('/live', 'live.html'),
]

# 前端各页面实际会请求的接口（GET）。POST 接口由 mock 脚本按路径返回固定结果。
API_ENDPOINTS = [
    '/api/cats',
    '/api/cat/1',
    '/api/cat/2',
    '/api/stats',
    '/api/stats/feed-history',
    '/api/notifications',
    '/api/notifications/unread-count',
    '/api/feed-logs?limit=10',
    '/api/feed-logs?limit=5',
    '/api/reports',
    '/api/volunteers',
    '/api/emergency/alerts',
    '/api/diaries?page=1&per_page=50',
    '/api/diaries/1',
    '/api/finance/summary',
    '/api/finance/transactions',
    '/api/finance/monthly',
    '/api/learning/insights',
    '/api/learning/anomalies',
    '/api/live/info',
    '/api/location/1',
]

PAGE_LINK_MAP = {
    '/live': 'live.html',
    '/cats': 'cats.html',
    '/adopt': 'adopt.html',
    '/diary': 'diary.html',
    '/dashboard': 'index.html',
}


def rewrite_html(html):
    """把服务端渲染结果改造成 file:// 可直接打开的静态页。"""
    # /static/xxx?v=123456 -> static/xxx
    html = re.sub(r'(["\'(])/static/([^"\'?)]+)\?v=[^"\'&)]*', r'\1static/\2', html)
    html = re.sub(r'(["\'(])/static/', r'\1static/', html)
    # 站内路由 -> 静态文件（含 JS 里拼接的 '/cats?id=' 这类字符串和 '/#锚点'）
    html = re.sub(
        r'(["\'])/(cats|live|adopt|diary|dashboard)(?=["\'?#])',
        lambda m: '%s%s' % (m.group(1), PAGE_LINK_MAP['/' + m.group(2)]),
        html,
    )
    html = html.replace('"/#"', '"index.html#"').replace("'/#", "'index.html#")
    html = html.replace('"/#', '"index.html#')
    html = html.replace('href="/"', 'href="index.html"')
    # 在 <head> 之后立刻注入 mock，保证它的 fetch 劫持早于页面脚本
    mock_tag = '<script src="static/js/offline-mock.js"></script>'
    if '</head>' in html:
        html = html.replace('</head>', '  ' + mock_tag + '\n</head>', 1)
    else:  # 极端情况下没有 head，就塞到最前面
        html = mock_tag + html
    return html


def collect_api(client):
    fixtures = {}
    for path in API_ENDPOINTS:
        try:
            resp = client.get(path)
            if resp.status_code == 200 and resp.is_json:
                fixtures[path] = resp.get_json()
            else:
                print('  ! %s -> HTTP %s（跳过）' % (path, resp.status_code))
        except Exception as exc:  # 单个接口失败不影响整体导出
            print('  ! %s -> %s（跳过）' % (path, exc))
    return fixtures


MOCK_TEMPLATE = '''/* 猫迹 CatTrace 离线版：内置接口数据 + fetch 拦截
 * 由 scripts/build_offline_site.py 生成，请勿手工修改。
 * 作用：双击打开页面时没有后端，这里用打包好的快照数据回应 /api/* 请求。 */
(function () {
  var MOCK = %(fixtures)s;

  /* 页面里写死的一两个取不到数据的接口，给一份兜底，避免界面空白 */
  var FALLBACK = {
    '/api/cats': { 'success': true, 'cats': [] },
    '/api/stats': { 'success': true, 'total_cats': 0, 'total_feeds': 0, 'total_views': 0, 'active_users': 0 }
  };

  /* 写操作（投喂、领养申请等）在离线版里只做本地成功回执，不改动快照数据 */
  var POST_RESULTS = %(post_results)s;

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
    if (pathname.charAt(0) === '.') { pathname = pathname.replace(/^\\./, ''); }
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
      this.getAllResponseHeaders = function () { return 'content-type: application/json\\r\\n'; };
    };
  }
}());
'''


POST_RESULTS_TEMPLATE = {
    '/api/feed': {'success': True, 'message': '投喂成功（离线演示模式，数据不会上传）', 'feed_count': 1},
    '/api/feed-as-guest': {'success': True, 'message': '投喂成功（离线演示模式）', 'remaining': 0},
    '/api/adopt/apply': {'success': True, 'message': '申请已提交（离线演示模式）'},
    '/api/volunteer/apply': {'success': True, 'message': '报名已提交（离线演示模式）'},
    '/api/report': {'success': True, 'message': '举报已提交（离线演示模式）'},
    '/api/report-abuse': {'success': True, 'message': '举报已提交（离线演示模式）'},
    '/api/cleanup-logs': {'success': True, 'message': '清理记录已提交（离线演示模式）'},
    '/api/auth/login': {'success': True, 'token': 'offline-demo-token', 'user': {'id': 1, 'username': '爱心用户', 'role': 'user'}},
    '/api/auth/logout': {'success': True},
    '/api/auth/me': {'success': True, 'user': {'id': 1, 'username': '爱心用户', 'role': 'user'}},
    '/api/diaries/1/like': {'success': True, 'likes': 13},
    '/api/diaries/2/like': {'success': True, 'likes': 9},
    '/api/diaries/1/comment': {'success': True, 'message': '评论已提交（离线演示模式）'},
    '/api/recognize': {'success': True, 'message': '离线演示模式未接入识别模型', 'cat': {'id': 1, 'name': '咪咪'}},
    '/api/cat/register': {'success': True, 'message': '已登记（离线演示模式）'},
    '*': {'success': True, 'message': '离线演示模式：操作不会上传到服务器'}
}


def main():
    client = app_module.app.test_client()
    if hasattr(app_module, 'init_data'):
        app_module.init_data()

    print('采集接口数据…')
    fixtures = collect_api(client)

    mock_js = MOCK_TEMPLATE % {
        'fixtures': json.dumps(fixtures, ensure_ascii=False, indent=2),
        'post_results': json.dumps(POST_RESULTS_TEMPLATE, ensure_ascii=False, indent=2),
    }
    mock_path = os.path.join(BASE_DIR, 'static', 'js', 'offline-mock.js')
    with open(mock_path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(mock_js)
    print('写入 %s（%d 个接口）' % (os.path.relpath(mock_path, BASE_DIR), len(fixtures)))

    for route, filename in PAGES:
        resp = client.get(route)
        if resp.status_code != 200:
            print('  ! %s -> HTTP %s' % (route, resp.status_code))
            continue
        html = rewrite_html(resp.data.decode('utf-8'))
        target = os.path.join(BASE_DIR, filename)
        with open(target, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(html)
        print('导出 %s（%d KB）' % (filename, len(html.encode('utf-8')) // 1024))

    print('完成。直接双击 index.html 即可离线浏览。')


if __name__ == '__main__':
    main()
