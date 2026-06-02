import json
import time
import os
import threading
import shutil
import sys
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.edge.options import Options as EdgeOptions

def _emit(status_callback, message: str):
    if status_callback:
        status_callback(message)
    else:
        print(message, flush=True)

def _create_with_timeout(create_func, timeout_seconds: int):
    result = {"driver": None, "error": None}

    def runner():
        try:
            result["driver"] = create_func()
        except Exception as exc:
            result["error"] = exc

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        return None, TimeoutError(f"启动超时（>{timeout_seconds}秒）")
    return result["driver"], result["error"]

def _browser_exists(browser_name: str) -> bool:
    if browser_name == "Edge":
        exe_name = "msedge.exe"
        candidate_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
    else:
        exe_name = "chrome.exe"
        candidate_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]

    if shutil.which(exe_name):
        return True
    return any(os.path.exists(path) for path in candidate_paths)

def _create_edge_driver(status_callback=None):
    options = EdgeOptions()
    options.add_argument("--disable-features=Translate,AutomationControlled")
    options.add_argument("--disable-notifications")

    edgedriver_path = os.environ.get("EDGEDRIVER_PATH")
    if edgedriver_path:
        _emit(status_callback, f"使用环境变量 EDGEDRIVER_PATH 指定的驱动：{edgedriver_path}")
        service = EdgeService(edgedriver_path)
        return webdriver.Edge(service=service, options=options)

    try:
        _emit(status_callback, "尝试直接启动 Edge（使用 Selenium Manager 自动匹配驱动，最长等待 15 秒）...")
        driver, error = _create_with_timeout(lambda: webdriver.Edge(options=options), 15)
        if driver:
            return driver
        raise error
    except Exception as e:
        _emit(status_callback, f"Selenium Manager 启动 Edge 失败：{e}")

    _emit(status_callback, "尝试使用 webdriver-manager 下载/匹配 EdgeDriver（最长等待 20 秒，首次需要联网）...")
    driver_path, error = _create_with_timeout(lambda: EdgeChromiumDriverManager().install(), 20)
    if error is not None:
        raise error
    if driver_path is None:
        raise TimeoutError("下载/匹配 EdgeDriver 超时（>20秒）")
    _emit(status_callback, f"EdgeDriver 路径：{driver_path}")
    service = EdgeService(driver_path)
    return webdriver.Edge(service=service, options=options)

def _create_chrome_driver(status_callback=None):
    options = Options()
    options.add_argument("--disable-features=Translate,AutomationControlled")
    options.add_argument("--disable-notifications")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    if chromedriver_path:
        _emit(status_callback, f"使用环境变量 CHROMEDRIVER_PATH 指定的驱动：{chromedriver_path}")
        service = Service(chromedriver_path)
        return webdriver.Chrome(service=service, options=options)

    try:
        _emit(status_callback, "尝试直接启动 Chrome（使用 Selenium Manager 自动匹配驱动，最长等待 15 秒）...")
        driver, error = _create_with_timeout(lambda: webdriver.Chrome(options=options), 15)
        if driver:
            return driver
        raise error
    except Exception as e:
        _emit(status_callback, f"Selenium Manager 启动失败：{e}")

    _emit(status_callback, "尝试使用 webdriver-manager 下载/匹配 ChromeDriver（最长等待 20 秒，首次需要联网）...")
    driver_path, error = _create_with_timeout(lambda: ChromeDriverManager().install(), 20)
    if error is not None:
        raise error
    if driver_path is None:
        raise TimeoutError("下载/匹配 ChromeDriver 超时（>20秒）")
    _emit(status_callback, f"ChromeDriver 路径：{driver_path}")
    service = Service(driver_path)
    return webdriver.Chrome(service=service, options=options)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
DEFAULT_COOKIES_FILE = os.path.join(APP_DIR, "cookies.json")

def _is_logged_in_url(current_url: str) -> bool:
    return any(
        part in current_url
        for part in ("pintia.cn/problem-sets", "pintia.cn/home", "pintia.cn/user")
    )

def _try_click_login_button(driver) -> bool:
    candidates = [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, ".login button"),
        (By.CSS_SELECTOR, ".signin button"),
        (By.XPATH, "//button[contains(., '登录')]"),
        (By.XPATH, "//button[contains(., 'Sign in')]"),
    ]
    for by, value in candidates:
        try:
            elements = driver.find_elements(by, value)
            for element in elements:
                if element.is_displayed() and element.is_enabled():
                    element.click()
                    return True
        except Exception:
            continue
    return False

def get_pta_cookies(
    status_callback=None,
    cookies_output_path: str = DEFAULT_COOKIES_FILE,
    username=None,
    password=None,
    keep_browser_open: bool = False,
):
    _emit(status_callback, "正在启动浏览器...")
    driver = None
    try:
        if _browser_exists("Edge"):
            _emit(status_callback, "检测到本机已安装 Edge，优先使用 Edge。")
            driver = _create_edge_driver(status_callback=status_callback)
        elif _browser_exists("Chrome"):
            _emit(status_callback, "检测到本机已安装 Chrome，使用 Chrome。")
            driver = _create_chrome_driver(status_callback=status_callback)
        else:
            _emit(status_callback, "未检测到 Edge 或 Chrome。请先安装任意一个浏览器后再使用。")
            return False
    except Exception:
        _emit(status_callback, "启动浏览器失败。常见原因：首次下载驱动较慢、网络拦截、浏览器未正确安装，或 Chrome 启动被安全软件拦截。")
        return False
    
    try:
        driver.get("https://pintia.cn/auth/login")
        
        wait = WebDriverWait(driver, 10)

        if username and password:
            try:
                _emit(status_callback, "正在尝试自动填充账号密码...")
                user_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text'], input[type='email']")))
                pass_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
                
                user_input.clear()
                user_input.send_keys(username)
                pass_input.clear()
                pass_input.send_keys(password)

                clicked = _try_click_login_button(driver)
                if clicked:
                    _emit(status_callback, "已自动填充并尝试点击登录按钮。")
                else:
                    _emit(status_callback, "已填充账号密码，但未找到登录按钮，请手动点击登录。")
                _emit(status_callback, "如页面出现验证码/二次验证，请在浏览器中手动完成。")
            except Exception as e:
                _emit(status_callback, f"自动填充失败: {e}，请手动输入。")
        else:
            _emit(status_callback, "请在浏览器中手动输入账号密码并登录...")

        timeout = 120
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if not driver.window_handles:
                    _emit(status_callback, "❌ 检测到浏览器已关闭，登录流程已取消。")
                    return None if keep_browser_open else False
                current_url = driver.current_url
                if _is_logged_in_url(current_url):
                    _emit(status_callback, "🎉 检测到登录成功！")
                    time.sleep(1)
                    break
            except Exception:
                _emit(status_callback, "❌ 检测到浏览器已关闭或会话已失效，登录流程已取消。")
                return None if keep_browser_open else False
            time.sleep(2)
        else:
            _emit(status_callback, "❌ 登录超时，请重新操作。")
            return None if keep_browser_open else False

        cookies = driver.get_cookies()
        with open(cookies_output_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=4)
        
        _emit(status_callback, f"✅ Cookies 已保存到 {cookies_output_path}")
        if keep_browser_open:
            _emit(status_callback, "浏览器将保持打开，后续会直接复用当前登录状态。")
            return driver
        return True
        
    finally:
        if driver is not None and not keep_browser_open:
            driver.quit()

if __name__ == "__main__":
    get_pta_cookies()
