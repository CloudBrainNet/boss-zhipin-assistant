#!/usr/bin/env python3
"""环境检测模块 —— 启动时自动检查运行前置条件。

检测项：
  ① 浏览器是否可用（Chrome / Edge 等 Chromium 内核均可）
  ② Kimi WebBridge 插件是否可用（端口 10086）
  ③ Boss 直聘页面是否已登录（复用用户登录态）

用法：
    from scripts.env_check import check_env, EnvResult
    result = check_env()
    if not result.ok:
        print(result.message)   # 含修复指引
        sys.exit(1)
    print("✅ 环境检测全部通过")
"""

import sys
import os
import subprocess
import socket
import json

# 路径引导：确保 scripts 包可导入（无论以脚本直接运行还是被其它模块导入）
_HERE = os.path.dirname(os.path.abspath(__file__))
# 兼容 Git Bash 的 /c/... UNIX 风格路径：Windows Python 会把 /c 误算成 C:\c
if len(_HERE) >= 3 and _HERE[0] == "/" and _HERE[1].isalpha() and _HERE[2] == "/":
    _HERE = _HERE[1].upper() + ":" + _HERE[2:]
SKILL_DIR = os.path.dirname(_HERE)
if SKILL_DIR not in sys.path:
    sys.path.insert(0, SKILL_DIR)

# ── 检测结果 ──────────────────────────────────────
class EnvResult:
    """单次环境检测结果。"""
    def __init__(self):
        self.ok = True
        self.items = []   # [(name, passed, detail), ...]
        self.message = ""

    def add(self, name, passed, detail=""):
        self.items.append((name, passed, detail))
        if not passed:
            self.ok = False

    def build_message(self):
        lines = []
        for name, passed, detail in self.items:
            icon = "✅" if passed else "❌"
            lines.append(f"  {icon} {name}: {detail or ('通过' if passed else '未通过')}")
        if not self.ok:
            lines.append("")
            lines.append("⚠️  环境未就绪，请按上方指引完成准备后重试。")
        self.message = "\n".join(lines)
        return self.message


# ── 浏览器检测（Chrome / Edge 等 Chromium 内核均可）────
# 本技能全部通过 Kimi WebBridge 的 HTTP 接口（127.0.0.1:10086）操作浏览器，
# 代码里不碰浏览器进程、不用 CDP 直连，因此与「具体哪个浏览器」无关：
# 只要是 Chromium 内核且装了 WebBridge 插件的浏览器都能用（Chrome / Edge / Brave / Chromium）。
# Edge 与 Chrome 同内核，实测可完全替代（UA 形如 ... Chrome/156.0.0.0 Safari/537.36 Edg/156.0.0.0）。
_BROWSER_PATHS = [
    ("Chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    ("Chrome", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ("Chrome", os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")),
    ("Edge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ("Edge", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    ("Edge", os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")),
    ("Brave", r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ("Chromium", r"C:\Program Files\Chromium\Application\chrome.exe"),
]


def _detect_installed_browsers():
    """扫描常见安装路径，返回已安装的 Chromium 系浏览器 [(名称, 路径), ...]。"""
    found = []
    for name, p in _BROWSER_PATHS:
        if os.path.exists(p) and not any(n == name for n, _ in found):
            found.append((name, p))
    return found


def _bridge_browser_name():
    """从 WebBridge 当前标签页读 UA，判断真正在用的浏览器。

    这是最权威的判断——WebBridge 能读到页面，就说明该浏览器已装插件并连接成功。
    失败（服务未启动 / 会话里还没有标签页）返回 None。
    """
    try:
        from scripts.webbridge_client import api
        r = api("evaluate", {"code": "navigator.userAgent"}, timeout=8)
        ua = (((r or {}).get("data") or {}).get("value") or "")
        if not ua:
            return None
        if "Edg/" in ua:
            return "Edge"
        if "OPR/" in ua:
            return "Opera"
        if "Brave" in ua:
            return "Brave"
        if "Chrome/" in ua:
            return "Chrome"
        return None
    except Exception:
        return None


def _check_browser():
    """检测可用浏览器：先用 WebBridge 实际连接确认，再回退到本地安装扫描。"""
    name = _bridge_browser_name()
    if name:
        return True, f"{name}（WebBridge 已连接，可正常操作）"

    installed = _detect_installed_browsers()
    if installed:
        names = "、".join(n for n, _ in installed)
        return True, (
            f"已安装 {names}，但 WebBridge 尚未连上该浏览器。\n"
            "   请在浏览器中启用 Kimi WebBridge 插件，并登录 Boss 直聘后重试。"
        )

    return False, (
        "未检测到 Chrome / Edge 等 Chromium 内核浏览器。\n"
        "   装 Chrome（https://www.google.com/chrome/）或 Edge 任一皆可，\n"
        "   并在浏览器里安装 Kimi WebBridge 插件。"
    )


# ── WebBridge 检测 ─────────────────────────────────
_WEBBRIDGE_HOST = "127.0.0.1"
_WEBBRIDGE_PORT = 10086


def _check_webbridge():
    """检测 Kimi WebBridge 是否在本地端口 10086 可达。"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex((_WEBBRIDGE_HOST, _WEBBRIDGE_PORT))
        s.close()
        if result == 0:
            return True, f"WebBridge 已启动 (端口 {_WEBBRIDGE_PORT})"
        return False, (
            f"WebBridge 未在端口 {_WEBBRIDGE_PORT} 响应。\n"
            "   请确认：\n"
            "   ① 已安装 Kimi WebBridge 插件 → https://www.kimi.com/zh-cn/features/webbridge\n"
            "   ② 浏览器（Chrome / Edge 均可）中已启用该插件\n"
            "   ③ 终端执行 kimi-webbridge start 启动服务"
        )
    except Exception as e:
        return False, f"WebBridge 连接异常: {e}"


# ── Boss 登录检测 ──────────────────────────────────
def _check_boss_login():
    """
    通过 WebBridge evaluate 检测 Boss 直聘登录态。
    不绑定任何特定用户名——通用检测：
      - 页面非登录墙（不含"请登录"/"立即登录"等）
      - 页面含已登录标志（导航栏有用户信息 / body 含正常推荐内容）
    """
    try:
        # 延迟导入，避免无 WebBridge 时 import 失败
        from scripts.webbridge_client import api, evaluate as _ev
        import time as _t

        # 先导航到 Boss 推荐页，确保读到的是目标页面（而非其它空白标签页）
        RECOMMEND_URL = "https://www.zhipin.com/web/geek/jobs?ka=header-jobs"
        try:
            _ev  # noqa
            api("navigate", {"url": RECOMMEND_URL})
            _t.sleep(6)
        except Exception:
            pass

        body_text = _ev("document.body.innerText || ''") or ""
        login_wall_kws = ["请登录", "立即登录", "扫码登录", "账号密码登录", "手机号登录"]
        for kw in login_wall_kws:
            # 短文本命中且是主导航区特征（避免误判岗位描述中的"登录"）
            if kw in body_text and body_text.index(kw) < 200:
                return False, (
                    "Boss 直聘未登录或登录态已过期。\n"
                    "   请在已连接 WebBridge 的浏览器中打开 https://www.zhipin.com 并完成登录，\n"
                    "   本流程需复用您的登录数据才能投递。"
                )

        # 已登录标志：body 足够长（说明已加载推荐内容）且无登录墙
        if len(body_text.strip()) > 100:
            return True, "Boss 直聘已登录"

        return False, (
            "无法确认 Boss 直聘登录状态（页面内容过短）。\n"
            "   请在已连接 WebBridge 的浏览器中打开 https://www.zhipin.com 确认已登录。"
        )
    except Exception as e:
        return False, f"无法连接 WebBridge 检测登录态: {e}（请先确保 WebBridge 已启动）"


# ── 主入口 ─────────────────────────────────────────
def check_env(verbose=True):
    """执行全部环境检测，返回 EnvResult。

    Args:
        verbose: 是否打印每项结果到 stdout
    """
    result = EnvResult()

    # ① 浏览器（Chrome / Edge 等 Chromium 内核均可）
    passed, detail = _check_browser()
    result.add("浏览器", passed, detail)

    # ② WebBridge
    passed, detail = _check_webbridge()
    result.add("Kimi WebBridge", passed, detail)

    # 仅当前两项都通过时才检测登录（需要 WebBridge 才能读页面）
    if result.ok or any(n == "Kimi WebBridge" and p for n, p, _ in result.items):
        passed, detail = _check_boss_login()
        result.add("Boss 直聘登录", passed, detail)

    result.build_message()
    if verbose:
        print("\n🔍 BOSS 直聘投递技能 — 环境检测")
        print(result.message)
        print()
    return result


# ── CLI 入口 ───────────────────────────────────────
if __name__ == "__main__":
    r = check_env()
    sys.exit(0 if r.ok else 1)
