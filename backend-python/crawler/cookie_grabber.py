"""
微博Cookie自动获取器（异步两阶段）
阶段1: start_qr_session  → 启动浏览器、截取二维码、立即返回 session_id + qr 图片
阶段2: poll_qr_session   → 前端轮询检测是否扫码成功
"""
import json
import logging
import os
import time
import threading
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

COOKIE_FILE = os.path.join(os.path.dirname(__file__), 'cookies.json')

# 全局会话存储 {session_id: {...}}
_qr_sessions: dict = {}
_sessions_lock = threading.Lock()


def get_selenium_driver():
    """创建 headless Chromium WebDriver"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    opts = Options()
    opts.binary_location = '/usr/bin/chromium'
    opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--window-size=800,600')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=opts)
    driver.implicitly_wait(0)
    return driver


def start_qr_session(timeout: int = 120) -> dict:
    """
    阶段1: 同步启动浏览器并截取二维码（约5秒），然后启动后台线程等待扫码。
    返回 session_id + QR 图片给前端立即显示。
    """
    session_id = str(uuid.uuid4())[:8]
    driver = None

    try:
        driver = get_selenium_driver()
        logger.info(f"QR session {session_id}: driver 创建成功")

        driver.get('https://passport.weibo.com/sso/signin?entry=miniblog&source=miniblog')
        # 等待页面关键元素出现，而非固定sleep
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'img[src*="qrcode"], img[src*="login"], .qrcode img, img.qrcode_img'))
            )
        except Exception:
            time.sleep(1)

        # 尝试切换到扫码tab
        try:
            qr_tabs = driver.find_elements(By.CSS_SELECTOR, '.qrcode_tab, [node-type="qrcode_tab"], .tab_item')
            for tab in qr_tabs:
                text = tab.text or ''
                cls = tab.get_attribute('class') or ''
                if '扫码' in text or 'qr' in cls.lower():
                    tab.click()
                    time.sleep(0.5)
                    break
        except Exception:
            pass

        # 截取二维码
        qrcode_base64 = None
        try:
            qr_selectors = [
                'img.qrcode_img', 'img[node-type="qrcode_img"]',
                '.qrcode img', '.qr_code img', '#qrcode img',
                'img[src*="qrcode"]', 'img[src*="login"]',
            ]
            for sel in qr_selectors:
                imgs = driver.find_elements(By.CSS_SELECTOR, sel)
                if imgs:
                    qrcode_base64 = imgs[0].screenshot_as_base64
                    break
            if not qrcode_base64:
                qrcode_base64 = driver.get_screenshot_as_base64()
        except Exception:
            qrcode_base64 = driver.get_screenshot_as_base64()

        logger.info(f"QR session {session_id}: 二维码已截取 (len={len(qrcode_base64) if qrcode_base64 else 0})")

        # 保存会话状态
        with _sessions_lock:
            _qr_sessions[session_id] = {
                'status': 'qr_ready',
                'qrcode_base64': qrcode_base64,
                'cookie_string': '',
                'cookies': {},
                'message': '请使用微博APP扫描二维码',
                'created_at': time.time(),
            }

        # 启动后台线程等待扫码
        def _wait_for_scan():
            try:
                start = time.time()
                while time.time() - start < timeout:
                    with _sessions_lock:
                        s = _qr_sessions.get(session_id)
                        if not s or s['status'] == 'cancelled':
                            return

                    try:
                        cookies = driver.get_cookies()
                        cookie_names = {c['name'] for c in cookies}
                        current_url = driver.current_url

                        if 'SUB' in cookie_names:
                            _finish_login(session_id, driver, cookies)
                            return

                        if 'weibo.com' in current_url and 'passport' not in current_url:
                            time.sleep(2)
                            cookies = driver.get_cookies()
                            if any(c['name'] == 'SUB' for c in cookies):
                                _finish_login(session_id, driver, cookies)
                                return
                    except Exception:
                        pass

                    time.sleep(2)

                # 超时
                try:
                    driver.get('https://weibo.com/')
                    time.sleep(3)
                    cookies = driver.get_cookies()
                    if any(c['name'] == 'SUB' for c in cookies):
                        _finish_login(session_id, driver, cookies)
                        return
                except Exception:
                    pass

                _update(session_id, status='timeout', message=f'扫码超时({timeout}秒)，请重试')
            except Exception as e:
                logger.error(f"QR scan wait error: {e}")
                _update(session_id, status='error', message=str(e))
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        threading.Thread(target=_wait_for_scan, daemon=True).start()

        return {
            'session_id': session_id,
            'status': 'qr_ready',
            'qrcode_base64': qrcode_base64,
            'message': '请使用微博APP扫描二维码',
        }

    except Exception as e:
        logger.error(f"QR session start failed: {e}", exc_info=True)
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        return {
            'session_id': session_id,
            'status': 'error',
            'qrcode_base64': None,
            'message': f'启动失败: {str(e)}',
        }


def poll_qr_session(session_id: str) -> dict:
    """阶段2: 前端轮询，检查扫码结果"""
    with _sessions_lock:
        s = _qr_sessions.get(session_id)

    if not s:
        return {'status': 'not_found', 'message': '会话不存在或已过期'}

    result = {
        'session_id': session_id,
        'status': s['status'],
        'message': s['message'],
    }

    if s['status'] == 'qr_ready':
        result['qrcode_base64'] = s.get('qrcode_base64')

    if s['status'] == 'success':
        result['cookie_string'] = s.get('cookie_string', '')
        result['cookies'] = s.get('cookies', {})
        # 成功后清理会话
        with _sessions_lock:
            _qr_sessions.pop(session_id, None)

    if s['status'] in ('timeout', 'error', 'cancelled'):
        with _sessions_lock:
            _qr_sessions.pop(session_id, None)

    return result


def cancel_qr_session(session_id: str):
    """取消扫码会话"""
    with _sessions_lock:
        if session_id in _qr_sessions:
            _qr_sessions[session_id]['status'] = 'cancelled'


def _update(session_id: str, **kwargs):
    with _sessions_lock:
        if session_id in _qr_sessions:
            _qr_sessions[session_id].update(kwargs)


def _finish_login(session_id: str, driver, cookies):
    cookie_dict = {}
    for c in cookies:
        cookie_dict[c['name']] = c['value']

    try:
        ua = driver.execute_script('return navigator.userAgent')
        cookie_dict['_user_agent'] = ua
    except Exception:
        pass

    cookie_string = '; '.join(
        f"{k}={v}" for k, v in cookie_dict.items() if not k.startswith('_')
    )
    save_cookies(cookie_dict)

    _update(session_id,
            status='success',
            cookies=cookie_dict,
            cookie_string=cookie_string,
            message=f'登录成功，获取到 {len(cookie_dict)} 个Cookie字段')
    logger.info(f"QR session {session_id} 登录成功")


def refresh_cookies() -> dict:
    """
    使用已有Cookie刷新/验证，并尝试续期

    Returns:
        dict: 同 grab_cookies_by_qrcode 返回格式
    """
    driver = None
    try:
        # 加载现有Cookie
        existing = load_cookies()
        if not existing or 'SUB' not in existing:
            return {
                'success': False,
                'cookies': {},
                'cookie_string': '',
                'message': '无已保存的Cookie或缺少SUB字段'
            }

        driver = get_selenium_driver()

        # 先访问微博域名（设置cookie需要先在对应域名）
        driver.get('https://weibo.com/')
        time.sleep(2)

        # 注入已有Cookie
        for name, value in existing.items():
            if name.startswith('_'):
                continue
            try:
                driver.add_cookie({
                    'name': name,
                    'value': value,
                    'domain': '.weibo.com',
                    'path': '/'
                })
            except Exception:
                pass

        # 刷新页面触发Cookie更新
        driver.get('https://weibo.com/')
        time.sleep(3)

        # 提取更新后的Cookie
        cookies = driver.get_cookies()
        cookie_dict = {}
        for c in cookies:
            cookie_dict[c['name']] = c['value']

        if 'SUB' not in cookie_dict:
            return {
                'success': False,
                'cookies': {},
                'cookie_string': '',
                'message': 'Cookie已失效，需要重新扫码登录'
            }

        ua = driver.execute_script('return navigator.userAgent')
        cookie_dict['_user_agent'] = ua

        cookie_string = '; '.join(
            f"{k}={v}" for k, v in cookie_dict.items()
            if not k.startswith('_')
        )

        save_cookies(cookie_dict)

        return {
            'success': True,
            'cookies': cookie_dict,
            'cookie_string': cookie_string,
            'message': f'Cookie刷新成功，{len(cookie_dict)} 个字段',
            'has_sub': True,
            'has_xsrf': 'XSRF-TOKEN' in cookie_dict,
        }

    except Exception as e:
        logger.error(f"Cookie刷新失败: {e}", exc_info=True)
        return {
            'success': False,
            'cookies': {},
            'cookie_string': '',
            'message': f'刷新失败: {str(e)}'
        }
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def save_cookies(cookie_dict: dict):
    """保存Cookie到文件"""
    cookie_dict['_updated_at'] = datetime.now().isoformat()
    data = [cookie_dict]
    with open(COOKIE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Cookie已保存到 {COOKIE_FILE}")


def load_cookies() -> dict:
    """从文件加载Cookie"""
    try:
        if not os.path.exists(COOKIE_FILE):
            return {}
        with open(COOKIE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list) and data:
            return data[0]
        elif isinstance(data, dict):
            return data
        return {}
    except Exception as e:
        logger.warning(f"加载Cookie失败: {e}")
        return {}


def get_cookie_status() -> dict:
    """获取当前Cookie状态"""
    cookies = load_cookies()
    if not cookies:
        return {'has_cookie': False, 'valid': False, 'message': '未保存任何Cookie', 'cookie_string': ''}

    has_sub = 'SUB' in cookies
    has_xsrf = 'XSRF-TOKEN' in cookies
    updated = cookies.get('_updated_at', '未知')
    # 拼接可用的cookie字符串（排除内部字段）
    cookie_string = '; '.join(f'{k}={v}' for k, v in cookies.items() if v and not k.startswith('_'))

    if not has_sub:
        return {
            'has_cookie': True,
            'valid': False,
            'message': f'Cookie缺少SUB字段（更新时间: {updated}）',
            'fields': list(k for k in cookies if not k.startswith('_')),
            'updated_at': updated,
            'cookie_string': cookie_string,
        }

    return {
        'has_cookie': True,
        'valid': True,  # 仅代表格式有效，实际是否过期需在线验证
        'message': f'Cookie格式有效（更新时间: {updated}）',
        'fields': list(k for k in cookies if not k.startswith('_')),
        'updated_at': updated,
        'sub_prefix': cookies.get('SUB', '')[:20] + '...',
        'cookie_string': cookie_string,
    }
