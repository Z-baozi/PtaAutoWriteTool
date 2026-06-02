import json
import time
import os
import sys
import threading
import shutil
import random
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions

APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
CODE_FILE = os.path.join(APP_DIR, "code.txt")
COOKIES_FILE = os.path.join(APP_DIR, "cookies.json")

def _sanitize_cookie(cookie: dict) -> dict:
    allowed_keys = {
        "name",
        "value",
        "path",
        "domain",
        "expiry",
        "secure",
        "httpOnly",
        "sameSite",
    }
    cleaned = {k: v for k, v in cookie.items() if k in allowed_keys}
    if "expiry" in cleaned:
        try:
            cleaned["expiry"] = int(cleaned["expiry"])
        except Exception:
            cleaned.pop("expiry", None)
    return cleaned

def _cookie_variants(cookie: dict):
    variants = []
    base = dict(cookie)
    variants.append(base)

    if "domain" in base:
        no_dot = dict(base)
        no_dot["domain"] = no_dot["domain"].lstrip(".")
        variants.append(no_dot)

        no_domain = dict(base)
        no_domain.pop("domain", None)
        variants.append(no_domain)

    if "sameSite" in base:
        without_samesite = dict(base)
        without_samesite.pop("sameSite", None)
        variants.append(without_samesite)

    deduped = []
    seen = set()
    for item in variants:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped

def _add_cookies_with_fallbacks(driver, cookies):
    added = 0
    skipped = 0
    failures = []

    for cookie in cookies:
        cleaned = _sanitize_cookie(cookie)
        added_this_cookie = False
        last_error = None

        for variant in _cookie_variants(cleaned):
            try:
                driver.add_cookie(variant)
                added += 1
                added_this_cookie = True
                break
            except Exception as exc:
                last_error = str(exc)

        if not added_this_cookie:
            skipped += 1
            failures.append(f"{cleaned.get('name')}: {last_error}")

    return added, skipped, failures

def _find_editor_input(driver):
    candidates = [
        (By.CSS_SELECTOR, "div.monaco-editor textarea.inputarea"),
        (By.CSS_SELECTOR, "textarea"),
        (By.CSS_SELECTOR, "div[contenteditable='true']"),
    ]
    for by, sel in candidates:
        elements = driver.find_elements(by, sel)
        for el in elements:
            try:
                if el.is_displayed() and el.is_enabled():
                    return el
            except Exception:
                continue
    return None

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
        raise TimeoutError(f"启动超时（>{timeout_seconds}秒）")
    if result["error"] is not None:
        raise result["error"]
    return result["driver"]

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

def _create_browser_driver():
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--disable-features=Translate,AutomationControlled")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    edge_options = EdgeOptions()
    edge_options.add_argument("--disable-features=Translate,AutomationControlled")
    edge_options.add_argument("--disable-notifications")

    chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
    if chromedriver_path:
        service = Service(chromedriver_path)
        return webdriver.Chrome(service=service, options=chrome_options), "Chrome"

    edgedriver_path = os.environ.get("EDGEDRIVER_PATH")
    if edgedriver_path:
        service = EdgeService(edgedriver_path)
        return webdriver.Edge(service=service, options=edge_options), "Edge"

    if _browser_exists("Edge"):
        try:
            return _create_with_timeout(lambda: webdriver.Edge(options=edge_options), 15), "Edge"
        except Exception:
            driver_path = _create_with_timeout(lambda: EdgeChromiumDriverManager().install(), 20)
            service = EdgeService(driver_path)
            return webdriver.Edge(service=service, options=edge_options), "Edge"

    if _browser_exists("Chrome"):
        try:
            return _create_with_timeout(lambda: webdriver.Chrome(options=chrome_options), 15), "Chrome"
        except Exception:
            driver_path = _create_with_timeout(lambda: ChromeDriverManager().install(), 20)
            service = Service(driver_path)
            return webdriver.Chrome(service=service, options=chrome_options), "Chrome"

    raise RuntimeError("未检测到 Edge 或 Chrome。请先安装浏览器后再使用。")

def _set_code_via_editor_api(driver, code_content: str):
    script = r"""
const code = arguments[0];
try {
  if (window.monaco && window.monaco.editor) {
    if (typeof window.monaco.editor.getEditors === 'function') {
      const editors = window.monaco.editor.getEditors();
      if (editors && editors.length) {
        const editor = editors[0];
        editor.focus();
        const model = editor.getModel && editor.getModel();
        if (model && typeof model.pushEditOperations === 'function') {
          const fullRange = model.getFullModelRange();
          model.pushEditOperations([], [
            {
              range: fullRange,
              text: code,
              forceMoveMarkers: false
            }
          ]);
        } else {
          editor.setValue(code);
        }
        if (model && typeof model.getValue === 'function' && model.getValue() !== code) {
          return "error:monaco-editor-verify-failed";
        }
        if (model && typeof model.getLineCount === 'function') {
          const lastLine = model.getLineCount();
          const lastColumn = model.getLineMaxColumn(lastLine);
          if (typeof editor.setPosition === 'function') {
            editor.setPosition({ lineNumber: lastLine, column: lastColumn });
          }
        }
        return "monaco-editor";
      }
    }

    if (typeof window.monaco.editor.getModels === 'function') {
      const models = window.monaco.editor.getModels();
      if (models && models.length) {
        models[0].setValue(code);
        if (typeof models[0].getValue === 'function' && models[0].getValue() !== code) {
          return "error:monaco-model-verify-failed";
        }
        return "monaco-model";
      }
    }
  }

  const textarea = document.querySelector('div.monaco-editor textarea.inputarea')
    || document.querySelector('textarea');
  if (textarea) {
    textarea.focus();
    textarea.value = code;
    textarea.dispatchEvent(new Event('input', { bubbles: true }));
    textarea.dispatchEvent(new Event('change', { bubbles: true }));
    if (textarea.value !== code) {
      return "error:textarea-verify-failed";
    }
    return "textarea";
  }
} catch (error) {
  return "error:" + error.message;
}
return null;
"""
    try:
        result = driver.execute_script(script, code_content)
        return result or "error:editor-api-unavailable"
    except Exception as exc:
        return f"error:execute-script-failed:{exc}"

def _emit(status_callback, message: str):
    if status_callback:
        status_callback(message)
    else:
        print(message, flush=True)

def _sleep_like_human(base: float = 0.02, jitter: float = 0.04):
    time.sleep(base + random.random() * jitter)

def _press_shift_tab(driver):
    actions = ActionChains(driver)
    actions.key_down(Keys.SHIFT).send_keys(Keys.TAB).key_up(Keys.SHIFT)
    actions.perform()
    _sleep_like_human(0.01, 0.02)

def _type_code_like_human(driver, code_content: str):
    normalized = code_content.replace("\r\n", "\n").replace("\r", "\n").expandtabs(4)
    lines = normalized.split("\n")
    target = driver.switch_to.active_element

    clear_actions = ActionChains(driver)
    clear_actions.key_down(Keys.CONTROL).send_keys("a").key_up(Keys.CONTROL)
    clear_actions.send_keys(Keys.DELETE)
    clear_actions.perform()
    time.sleep(0.2)

    previous_indent_level = 0
    previous_line = ""

    for index, line in enumerate(lines):
        target = driver.switch_to.active_element
        if index > 0:
            target.send_keys(Keys.ENTER)
            _sleep_like_human(0.03, 0.05)

        stripped = line.lstrip(" ")
        desired_indent = len(line) - len(stripped)
        desired_indent_level = desired_indent // 4
        desired_extra_spaces = desired_indent % 4

        if index == 0:
            predicted_indent_level = 0
        else:
            previous_stripped = previous_line.rstrip()
            predicted_indent_level = previous_indent_level + (1 if previous_stripped.endswith(":") else 0)

        if desired_indent_level > predicted_indent_level:
            target.send_keys(Keys.TAB * (desired_indent_level - predicted_indent_level))
        elif predicted_indent_level > desired_indent_level:
            for _ in range(predicted_indent_level - desired_indent_level):
                _press_shift_tab(driver)

        if desired_extra_spaces:
            target.send_keys(" " * desired_extra_spaces)

        for ch in stripped:
            target.send_keys(ch)
            _sleep_like_human(0.005, 0.015)

        previous_indent_level = desired_indent_level
        previous_line = line
        _sleep_like_human(0.02, 0.03)

def auto_type_pta(code_content: str = None, status_callback=None, existing_driver=None):
    if not os.path.exists(COOKIES_FILE):
        _emit(status_callback, f"错误：未找到 {COOKIES_FILE} 文件！请先点击【打开浏览器并手动登录】。")
        return None

    if code_content is None:
        if not os.path.exists(CODE_FILE):
            _emit(status_callback, f"错误：未找到 {CODE_FILE} 文件，且未通过界面输入代码。")
            return None
        with open(CODE_FILE, "r", encoding="utf-8") as f:
            code_content = f.read()

    if not code_content.strip():
        _emit(status_callback, "错误：代码内容为空！")
        return None

    driver = existing_driver
    if driver is None:
        _emit(status_callback, "正在启动新浏览器...")
        try:
            driver, browser_name = _create_browser_driver()
            _emit(status_callback, f"已启动 {browser_name}")
        except Exception as e:
            _emit(status_callback, f"启动浏览器失败: {e}")
            return None
    else:
        _emit(status_callback, "正在复用已有浏览器窗口...")

    try:
        try:
            current_url = driver.current_url
        except Exception:
            _emit(status_callback, "原浏览器窗口已关闭，正在重新启动...")
            driver, browser_name = _create_browser_driver()
            current_url = ""

        if "pintia.cn" not in current_url:
            _emit(status_callback, "正在进入 PTA 并注入登录信息...")
            driver.get("https://pintia.cn/")
            
            with open(COOKIES_FILE, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            
            added, skipped, failures = _add_cookies_with_fallbacks(driver, cookies)
            _emit(status_callback, f"Cookies 注入完成。")
            driver.get("https://pintia.cn/problem-sets")
        
        _emit(status_callback, "请确保浏览器处于目标题目页面，正在检测编辑器...")

        max_retries = 30
        retry_count = 0
        login_hint_shown = False
        while retry_count < max_retries:
            try:
                current_url = driver.current_url
                if "/auth/login" in current_url:
                    if not login_hint_shown:
                        _emit(status_callback, "当前仍在登录页，请先在浏览器中手动登录，登录成功后再进入题目页面。")
                        login_hint_shown = True
                    time.sleep(1)
                    retry_count += 1
                    continue

                editable_element = _find_editor_input(driver)
                if editable_element is None:
                    time.sleep(1)
                    retry_count += 1
                    continue
                
                _emit(status_callback, "🚀 检测到编辑器！正在写入新内容...")
                editable_element.click()
                time.sleep(0.5)

                result = _set_code_via_editor_api(driver, code_content)
                if result and not str(result).startswith("error:"):
                    _emit(status_callback, f"✨ 代码写入完成！（{result}）")
                    return driver

                _emit(status_callback, f"API 写入失败：{result}")
                _emit(status_callback, "正在改用模拟键盘输入...")
                _type_code_like_human(driver, code_content)
                _emit(status_callback, "✅ 代码已通过模拟键盘输入完成。")
                return driver
                
            except Exception as e:
                time.sleep(1)
                retry_count += 1

        _emit(status_callback, "❌ 等待编辑器超时，请确认是否已打开题目页面。")
        return driver

    except Exception as e:
        _emit(status_callback, f"❌ 运行出错: {e}")
        return driver

if __name__ == "__main__":
    auto_type_pta()
