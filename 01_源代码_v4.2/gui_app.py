import tkinter as tk
from tkinter import messagebox
import threading
import os
import sys
import datetime
import customtkinter as ctk
from pta_auto_type import auto_type_pta
from get_cookies import get_pta_cookies

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

APP_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
RESOURCE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
CODE_FILE = os.path.join(APP_DIR, "code.txt")
COOKIES_FILE = os.path.join(APP_DIR, "cookies.json")
ICON_FILE = os.path.join(RESOURCE_DIR, "favicon.ico")
LOGO_FILE = os.path.join(RESOURCE_DIR, "logo.png")


class PTATypeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PTA 自动代码写入工具 | Z-baozi")
        self.driver = None
        self.about_window = None
        self.splash_window = None
        self._setup_window()
        self._setup_icon()
        self._setup_fonts()
        self._build_ui()
        self.root.after(0, self._sync_header_status_width)
        self.root.after(0, self._fit_root_to_screen)
        self._load_default_code()
        self._sync_code_stats()
        self._refresh_status_ui()
        self.root.bind("<Configure>", self._on_window_resize)
        self.root.after(1500, self._poll_runtime_state)
        self.root.after(120, self._show_welcome_splash)

    def _setup_window(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self._apply_adaptive_scaling(screen_w, screen_h)

        self.window_margin_x = 40
        self.window_margin_y = 56
        self.min_window_width = min(980, max(820, screen_w - 120))
        self.min_window_height = min(640, max(560, screen_h - 120))

        width = min(max(self.min_window_width, int(screen_w * 0.74)), screen_w - self.window_margin_x * 2)
        height = min(max(self.min_window_height, int(screen_h * 0.78)), screen_h - self.window_margin_y * 2)
        x = max((screen_w - width) // 2, 16)
        y = max((screen_h - height) // 2, 16)

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.minsize(self.min_window_width, self.min_window_height)
        self.root.resizable(True, True)
        self.root.configure(fg_color="#07101c")

    def _apply_adaptive_scaling(self, screen_w, screen_h):
        scale = min(screen_w / 1600, screen_h / 960, 1.0)
        scale = max(scale, 0.88)
        ctk.set_widget_scaling(scale)
        ctk.set_window_scaling(scale)

    def _fit_root_to_screen(self):
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        max_w = max(screen_w - self.window_margin_x * 2, 720)
        max_h = max(screen_h - self.window_margin_y * 2, 520)

        req_w = self.root.winfo_reqwidth() + 24
        req_h = self.root.winfo_reqheight() + 24
        width = min(max(req_w, self.min_window_width), max_w)
        height = min(max(req_h, self.min_window_height), max_h)
        x = max((screen_w - width) // 2, 16)
        y = max((screen_h - height) // 2, 16)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _center_toplevel(self, window, width, height):
        self.root.update_idletasks()
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        width = min(width, screen_w - 80)
        height = min(height, screen_h - 80)
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_w = self.root.winfo_width()
        root_h = self.root.winfo_height()

        if root_w > 1 and root_h > 1:
            x = root_x + max((root_w - width) // 2, 0)
            y = root_y + max((root_h - height) // 2, 0)
        else:
            x = max((screen_w - width) // 2, 20)
            y = max((screen_h - height) // 2, 20)

        window.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_icon(self):
        self.icon_path = ICON_FILE if os.path.exists(ICON_FILE) else None
        self.logo_path = LOGO_FILE if os.path.exists(LOGO_FILE) else None
        self.logo_source = None
        self.logo_cache = {}
        if self.logo_path:
            try:
                self.logo_source = tk.PhotoImage(file=self.logo_path)
            except Exception:
                self.logo_source = None
        self.app_icon = tk.PhotoImage(width=64, height=64)
        self.app_icon.put("#07101c", to=(0, 0, 64, 64))
        self.app_icon.put("#0f2743", to=(6, 6, 58, 58))
        self.app_icon.put("#00b8ff", to=(10, 10, 54, 18))
        self.app_icon.put("#08111f", to=(10, 18, 54, 54))
        self.app_icon.put("#1ad1ff", to=(14, 22, 50, 26))
        self.app_icon.put("#7dd3fc", to=(14, 30, 42, 34))
        self.app_icon.put("#7dd3fc", to=(14, 38, 46, 42))
        self.app_icon.put("#fbbf24", to=(46, 30, 50, 42))
        self._apply_window_icon(self.root)

    def _apply_window_icon(self, window):
        if self.icon_path:
            try:
                window.iconbitmap(self.icon_path)
                return
            except Exception:
                pass
        window.iconphoto(True, self.app_icon)

    def _get_logo_image(self, max_size):
        if self.logo_source is None:
            return None
        if max_size not in self.logo_cache:
            width = max(self.logo_source.width(), 1)
            height = max(self.logo_source.height(), 1)
            scale = max((width + max_size - 1) // max_size, (height + max_size - 1) // max_size, 1)
            self.logo_cache[max_size] = self.logo_source.subsample(scale, scale)
        return self.logo_cache[max_size]

    def _setup_fonts(self):
        self.brand_font = ctk.CTkFont(family="Microsoft YaHei UI", size=27, weight="bold")
        self.header_brand_font = ctk.CTkFont(family="Microsoft YaHei UI", size=22, weight="bold")
        self.subtitle_font = ctk.CTkFont(family="Microsoft YaHei UI", size=11)
        self.status_label_font = ctk.CTkFont(family="Microsoft YaHei UI", size=9)
        self.status_value_font = ctk.CTkFont(family="Microsoft YaHei UI", size=12, weight="bold")
        self.section_title_font = ctk.CTkFont(family="Microsoft YaHei UI", size=15, weight="bold")
        self.section_hint_font = ctk.CTkFont(family="Microsoft YaHei UI", size=10)
        self.toolbar_font = ctk.CTkFont(family="Microsoft YaHei UI", size=10, weight="bold")
        self.button_font = ctk.CTkFont(family="Microsoft YaHei UI", size=12, weight="bold")
        self.code_font = ctk.CTkFont(family="Consolas", size=14)
        self.log_font = ctk.CTkFont(family="Microsoft YaHei UI", size=10)
        self.footer_font = ctk.CTkFont(family="Microsoft YaHei UI", size=9)

    def _build_ui(self):
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_workspace()
        self._build_actions()

    def _show_welcome_splash(self):
        if self.splash_window is not None and self.splash_window.winfo_exists():
            return

        splash_width = 500
        splash_height = 300
        splash = ctk.CTkToplevel(self.root)
        self.splash_window = splash
        splash.title("欢迎")
        splash.geometry(f"{splash_width}x{splash_height}")
        splash.resizable(False, False)
        splash.transient(self.root)
        splash.lift()
        splash.attributes("-topmost", True)
        splash.configure(fg_color="#08111f")
        self._apply_window_icon(splash)
        self._center_toplevel(splash, splash_width, splash_height)
        splash.protocol("WM_DELETE_WINDOW", self._close_welcome_splash)

        frame = ctk.CTkFrame(
            splash,
            corner_radius=22,
            fg_color="#0d1b31",
            border_width=1,
            border_color="#1a4b78",
        )
        frame.pack(fill="both", expand=True, padx=16, pady=16)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)

        content = ctk.CTkFrame(frame, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew")

        splash_logo = self._get_logo_image(58)
        if splash_logo is not None:
            splash_logo_label = tk.Label(
                content,
                image=splash_logo,
                bg="#0d1b31",
                bd=0,
                highlightthickness=0,
            )
            splash_logo_label.image = splash_logo
            splash_logo_label.pack(pady=(0, 8))

        ctk.CTkLabel(
            content,
            text="WELCOME",
            font=self.footer_font,
            text_color="#7dd3fc",
            fg_color="#0a2238",
            corner_radius=999,
            padx=10,
            pady=3,
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            content,
            text="欢迎使用",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=15, weight="bold"),
            text_color="#8be9fd",
        ).pack(pady=(0, 4))

        ctk.CTkLabel(
            content,
            text="PTA 自动代码写入工具",
            font=self.brand_font,
            text_color="#dbeafe",
        ).pack()

        ctk.CTkLabel(
            content,
            text="一站式完成登录、写入、切换账号与状态查看。",
            font=self.subtitle_font,
            text_color="#9fb3c8",
            justify="center",
        ).pack(pady=(10, 0))

        ctk.CTkLabel(
            content,
            text="本软件仅供学习与技术交流使用",
            font=self.footer_font,
            text_color="#fbbf24",
        ).pack(pady=(10, 0))

        info = ctk.CTkFrame(
            content,
            fg_color="#0a1220",
            corner_radius=14,
            border_width=1,
            border_color="#163554",
        )
        info.pack(pady=(18, 0))
        ctk.CTkLabel(
            info,
            text="作者：Z-baozi\n联系方式：scholartime@qq.com",
            font=self.section_hint_font,
            text_color="#bcd1e7",
            justify="center",
        ).pack(padx=16, pady=12)

        splash_button_bar = ctk.CTkFrame(content, fg_color="transparent")
        splash_button_bar.pack(fill="x", padx=44, pady=(20, 0))

        ctk.CTkButton(
            splash_button_bar,
            text="进入软件",
            font=self.button_font,
            height=44,
            corner_radius=12,
            fg_color="#00b8ff",
            hover_color="#67d5ff",
            text_color="#07111f",
            command=self._close_welcome_splash,
        ).pack(fill="x")

        ctk.CTkLabel(
            content,
            text="按下按钮即可进入主界面",
            font=self.footer_font,
            text_color="#6f86a3",
        ).pack(pady=(8, 0))

        self.root.after(2800, self._close_welcome_splash)

    def _close_welcome_splash(self):
        if self.splash_window is not None:
            try:
                if self.splash_window.winfo_exists():
                    self.splash_window.destroy()
            except Exception:
                pass
            self.splash_window = None

    def _build_header(self):
        header_frame = ctk.CTkFrame(
            self.main_frame,
            corner_radius=16,
            fg_color="#0c1a2c",
            border_width=1,
            border_color="#143151",
        )
        self.header_frame = header_frame
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        header_frame.grid_columnconfigure(0, weight=8, uniform="main_split")
        header_frame.grid_columnconfigure(1, weight=4, uniform="main_split")

        brand_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        brand_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=6)
        brand_frame.grid_columnconfigure(2, weight=1)
        brand_frame.grid_rowconfigure(0, weight=0)
        brand_frame.grid_rowconfigure(1, weight=0)

        title_row = ctk.CTkFrame(brand_frame, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=(14, 0))
        title_col = 0
        notice_col = 1
        about_col = 3
        header_logo = self._get_logo_image(32)
        if header_logo is not None:
            header_logo_label = tk.Label(
                title_row,
                image=header_logo,
                bg="#0c1a2c",
                bd=0,
                highlightthickness=0,
            )
            header_logo_label.image = header_logo
            header_logo_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
            title_col = 1
            notice_col = 2
            about_col = 4
        title_row.grid_columnconfigure(about_col - 1, weight=1)

        self.title_label = ctk.CTkLabel(
            title_row,
            text="PTA 自动代码写入工具",
            font=self.header_brand_font,
            text_color="#8be9fd",
        )
        self.title_label.grid(row=0, column=title_col, sticky="w")

        self.notice_label = ctk.CTkLabel(
            title_row,
            text="仅供学习使用",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=10),
            text_color="#fbbf24",
            fg_color="#2a2008",
            corner_radius=999,
            padx=8,
            pady=1,
        )
        self.notice_label.grid(row=0, column=notice_col, sticky="nw", padx=(8, 0), pady=(1, 0))

        self.about_btn = ctk.CTkButton(
            title_row,
            text="关于",
            width=46,
            height=20,
            corner_radius=999,
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=10),
            text_color="#fbbf24",
            fg_color="#2a2008",
            hover_color="#3a2b0a",
            border_width=0,
            border_spacing=0,
            command=self.show_about_dialog,
        )
        self.about_btn.grid(row=0, column=about_col, sticky="e", padx=(8, 0), pady=(1, 0))

        self.desc_label = ctk.CTkLabel(
            brand_frame,
            text="登录、写入、切换账号集中完成，状态栏实时提示当前状态。",
            font=self.subtitle_font,
            text_color="#9fb3c8",
            justify="left",
            anchor="w",
        )
        self.desc_label.grid(row=1, column=0, sticky="ew", padx=(14, 0), pady=(3, 0))

        status_strip = ctk.CTkFrame(
            header_frame,
            fg_color="transparent",
            corner_radius=0,
            border_width=0,
            height=74,
        )
        self.status_strip = status_strip
        status_strip.grid(row=0, column=1, sticky="ew", padx=(6, 10), pady=6)
        status_strip.grid_propagate(False)
        for column in range(3):
            status_strip.grid_columnconfigure(column, weight=1)

        self.status_login_value = self._create_status_tile(status_strip, 0, "登录状态")
        self.status_browser_value = self._create_status_tile(status_strip, 1, "浏览器状态")
        self.status_cookie_value = self._create_status_tile(status_strip, 2, "本地登录态")

    def _create_status_tile(self, parent, column, title):
        tile_padx = (0, 3) if column == 0 else (3, 6) if column == 2 else 3
        tile = ctk.CTkFrame(
            parent,
            fg_color="#0b1a2c",
            corner_radius=10,
            border_width=1,
            border_color="#17314e",
            height=62,
        )
        tile.grid(row=0, column=column, sticky="ew", padx=tile_padx, pady=6)
        tile.grid_propagate(False)

        content = ctk.CTkFrame(tile, fg_color="transparent")
        content.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            content,
            text=title,
            font=self.status_label_font,
            text_color="#7f92aa",
            justify="center",
            anchor="center",
        ).pack(anchor="center", pady=(0, 1))

        value_label = ctk.CTkLabel(
            content,
            text="检测中",
            font=self.status_value_font,
            text_color="#dbeafe",
            justify="center",
            anchor="center",
        )
        value_label.pack(anchor="center", pady=(1, 0))
        return value_label

    def _build_workspace(self):
        workspace = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.workspace = workspace
        workspace.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        workspace.grid_columnconfigure(0, weight=8, uniform="main_split")
        workspace.grid_columnconfigure(1, weight=4, uniform="main_split")
        workspace.grid_rowconfigure(0, weight=1, minsize=360)

        self._build_code_panel(workspace)
        self._build_right_panel(workspace)

    def _build_code_panel(self, parent):
        code_panel = ctk.CTkFrame(
            parent,
            corner_radius=18,
            fg_color="#0d1627",
            border_width=1,
            border_color="#1a3558",
        )
        self.code_panel = code_panel
        code_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        code_panel.grid_columnconfigure(0, weight=1)
        code_panel.grid_rowconfigure(1, weight=1, minsize=260)

        title_row = ctk.CTkFrame(code_panel, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 3))
        title_row.grid_columnconfigure(0, weight=3)
        title_row.grid_columnconfigure(1, weight=2)

        title_text = ctk.CTkFrame(title_row, fg_color="transparent")
        title_text.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        title_text.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_text,
            text="代码编辑工作区",
            font=self.section_title_font,
            text_color="#dbeafe",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            title_text,
            text="在这里粘贴或编辑需要写入 PTA 的代码",
            font=self.section_hint_font,
            text_color="#7f92aa",
        ).grid(row=1, column=0, sticky="w", pady=(1, 0))

        toolbar = ctk.CTkFrame(title_row, fg_color="#0a1220", corner_radius=12)
        toolbar.grid(row=0, column=1, sticky="e")
        toolbar.grid_columnconfigure(0, weight=1)
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.grid_columnconfigure(2, weight=1)

        self.load_btn = ctk.CTkButton(
            toolbar,
            text="加载 code.txt",
            font=self.toolbar_font,
            height=34,
            corner_radius=10,
            fg_color="#13243f",
            hover_color="#1a3359",
            command=self.load_code_from_file,
        )
        self.load_btn.grid(row=0, column=0, sticky="ew", padx=(10, 6), pady=8)

        self.save_btn = ctk.CTkButton(
            toolbar,
            text="保存到 code.txt",
            font=self.toolbar_font,
            height=34,
            corner_radius=10,
            fg_color="#13243f",
            hover_color="#1a3359",
            command=self.save_code_to_file,
        )
        self.save_btn.grid(row=0, column=1, sticky="ew", padx=6, pady=8)

        self.clear_btn = ctk.CTkButton(
            toolbar,
            text="清空输入区",
            font=self.toolbar_font,
            height=34,
            corner_radius=10,
            fg_color="#13243f",
            hover_color="#1a3359",
            command=self.clear_code_area,
        )
        self.clear_btn.grid(row=0, column=2, sticky="ew", padx=(6, 10), pady=8)

        code_text_frame = ctk.CTkFrame(
            code_panel,
            fg_color="#07101c",
            corner_radius=14,
            border_width=1,
            border_color="#17314e",
        )
        code_text_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 1))
        code_text_frame.grid_columnconfigure(0, weight=1)
        code_text_frame.grid_rowconfigure(0, weight=1)

        self.text_area = ctk.CTkTextbox(
            code_text_frame,
            wrap="none",
            font=self.code_font,
            corner_radius=12,
            fg_color="#07101c",
            text_color="#dbeafe",
            border_width=0,
            scrollbar_button_color="#17314e",
            scrollbar_button_hover_color="#20456d",
        )
        self.text_area.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.text_area.bind("<KeyRelease>", self._on_code_change)

        x_scroll = ctk.CTkScrollbar(code_text_frame, orientation="horizontal", command=self.text_area.xview)
        x_scroll.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.text_area.configure(xscrollcommand=x_scroll.set)

        editor_footer = ctk.CTkFrame(code_panel, fg_color="transparent")
        editor_footer.grid(row=2, column=0, sticky="ew", padx=14, pady=(6, 8))
        editor_footer.grid_columnconfigure(0, weight=1)
        editor_footer.grid_columnconfigure(1, weight=1)

        self.code_stats_label = ctk.CTkLabel(
            editor_footer,
            text="行数：0  字符数：0",
            font=self.footer_font,
            text_color="#8ca4c0",
        )
        self.code_stats_label.grid(row=0, column=0, sticky="w")

        self.editor_hint_label = ctk.CTkLabel(
            editor_footer,
            text="建议保持 Python 原始缩进，避免手动改成 Tab/空格混用。",
            font=self.footer_font,
            text_color="#6f86a3",
        )
        self.editor_hint_label.grid(row=0, column=1, sticky="e")

    def _build_right_panel(self, parent):
        right_panel = ctk.CTkFrame(parent, fg_color="transparent")
        self.right_panel = right_panel
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(1, weight=1)

        status_card = ctk.CTkFrame(
            right_panel,
            corner_radius=18,
            fg_color="#0d1627",
            border_width=1,
            border_color="#1a3558",
        )
        status_card.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        status_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            status_card,
            text="当前状态面板",
            font=self.section_title_font,
            text_color="#dbeafe",
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 1))

        self.status_summary_label = ctk.CTkLabel(
            status_card,
            text="正在检测当前环境...",
            font=self.section_hint_font,
            text_color="#8fa3bb",
            wraplength=320,
            justify="left",
            anchor="w",
        )
        self.status_summary_label.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 4))

        self.status_action_label = ctk.CTkLabel(
            status_card,
            text="建议操作：先登录或直接写入",
            font=self.section_hint_font,
            text_color="#8be9fd",
            wraplength=320,
            justify="left",
            anchor="w",
        )
        self.status_action_label.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))

        log_panel = ctk.CTkFrame(
            right_panel,
            corner_radius=18,
            fg_color="#0d1627",
            border_width=1,
            border_color="#1a3558",
        )
        log_panel.grid(row=1, column=0, sticky="nsew")
        log_panel.grid_columnconfigure(0, weight=1)
        log_panel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            log_panel,
            text="运行日志",
            font=self.section_title_font,
            text_color="#dbeafe",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self.log_area = ctk.CTkTextbox(
            log_panel,
            font=self.log_font,
            corner_radius=12,
            fg_color="#0a1220",
            text_color="#bcd1e7",
            border_width=0,
            scrollbar_button_color="#17314e",
            scrollbar_button_hover_color="#20456d",
        )
        self.log_area.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 10))
        self.log_area.configure(state="disabled")

    def _build_actions(self):
        bottom_frame = ctk.CTkFrame(
            self.main_frame,
            corner_radius=16,
            fg_color="#0d1628",
            border_width=1,
            border_color="#15345f",
        )
        bottom_frame.grid(row=2, column=0, sticky="ew")
        bottom_frame.grid_columnconfigure(0, weight=1)

        self.footer_label = ctk.CTkLabel(
            bottom_frame,
            text="推荐：已登录后直接点击“一键开始”，切换账号请使用红色按钮。",
            font=self.footer_font,
            text_color="#7f92aa",
            justify="center",
        )
        self.footer_label.grid(row=0, column=0, sticky="ew", padx=16, pady=(8, 4))

        button_row = ctk.CTkFrame(
            bottom_frame,
            fg_color="#0a1424",
            corner_radius=14,
            border_width=1,
            border_color="#17314e",
        )
        button_row.grid(row=1, column=0, sticky="ew", padx=12, pady=2)
        for column in range(4):
            button_row.grid_columnconfigure(column, weight=1)

        self.login_btn = ctk.CTkButton(
            button_row,
            text="打开浏览器并手动登录",
            font=self.button_font,
            height=40,
            corner_radius=12,
            fg_color="#1f5f95",
            hover_color="#2f79b5",
            border_width=1,
            border_color="#58a6dd",
            command=self.start_login_thread,
        )
        self.login_btn.grid(row=0, column=0, sticky="ew", padx=(10, 4), pady=10)

        self.start_btn = ctk.CTkButton(
            button_row,
            text="仅写入（需已登录）",
            font=self.button_font,
            height=40,
            corner_radius=12,
            fg_color="#1985a1",
            hover_color="#24a1c2",
            border_width=1,
            border_color="#63d2ea",
            command=self.start_typing_thread,
        )
        self.start_btn.grid(row=0, column=1, sticky="ew", padx=4, pady=10)

        self.switch_btn = ctk.CTkButton(
            button_row,
            text="切换账号",
            font=self.button_font,
            height=40,
            corner_radius=12,
            fg_color="#5a1d2d",
            hover_color="#7a273b",
            border_width=1,
            border_color="#a74660",
            text_color="#ffd6de",
            command=self.start_switch_account_thread,
        )
        self.switch_btn.grid(row=0, column=2, sticky="ew", padx=4, pady=10)

        self.auto_btn = ctk.CTkButton(
            button_row,
            text="一键开始",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold"),
            height=40,
            corner_radius=12,
            fg_color="#00b8ff",
            hover_color="#6cd8ff",
            border_width=1,
            border_color="#8be9fd",
            text_color="#07111f",
            command=self.start_full_auto_thread,
        )
        self.auto_btn.grid(row=0, column=3, sticky="ew", padx=(4, 10), pady=10)

        self.signature_label = ctk.CTkLabel(
            bottom_frame,
            text="Designed by Z-baozi",
            font=self.footer_font,
            text_color="#5f738f",
            justify="center",
        )
        self.signature_label.grid(row=2, column=0, sticky="ew", padx=16, pady=(4, 8))

    def _on_window_resize(self, event):
        if event.widget is not self.root:
            return
        self.root.after_idle(self._sync_header_status_width)
        self.footer_label.configure(wraplength=max(int(event.width * 0.21), 260))
        self.status_summary_label.configure(wraplength=max(int(event.width * 0.18), 220))
        self.status_action_label.configure(wraplength=max(int(event.width * 0.18), 220))

    def _sync_header_status_width(self):
        if not hasattr(self, "status_strip") or not hasattr(self, "right_panel") or not hasattr(self, "header_frame"):
            return
        try:
            self.root.update_idletasks()
            header_width = self.header_frame.winfo_width()
            header_left = self.header_frame.winfo_rootx()
            header_right = header_left + header_width
            right_left = self.right_panel.winfo_rootx()
            right_width = self.right_panel.winfo_width()
            right_right = right_left + right_width
            if header_width > 80 and right_left >= header_left and right_width > 40:
                left_inset = max(right_left - header_left, 0)
                right_margin = max(header_right - right_right, 0)
                self.header_frame.grid_columnconfigure(0, weight=0, minsize=left_inset)
                self.header_frame.grid_columnconfigure(1, weight=1, minsize=max(header_width - left_inset, 0))
                self.status_strip.grid_configure(padx=(0, right_margin))
        except Exception:
            pass

    def _refresh_status_ui(self):
        has_cookie = os.path.exists(COOKIES_FILE)
        browser_alive = self._has_live_driver()

        if browser_alive:
            browser_text = "浏览器已连接"
            browser_color = "#8be9fd"
        else:
            browser_text = "浏览器未连接"
            browser_color = "#fbbf24"

        if has_cookie:
            cookie_text = "已检测到"
            cookie_color = "#34d399"
        else:
            cookie_text = "未检测到"
            cookie_color = "#f87171"

        if browser_alive and has_cookie:
            login_text = "可直接写入"
            login_color = "#34d399"
            summary = "已检测到浏览器会话和本地登录态，当前更适合直接进入题目页面进行写入。"
            action = "建议操作：点击“仅写入”或“一键开始”。"
        elif has_cookie:
            login_text = "已保存登录态"
            login_color = "#60a5fa"
            summary = "本地已有 PTA 登录态，但当前没有连接到浏览器窗口。"
            action = "建议操作：点击“一键开始”或重新打开浏览器。"
        else:
            login_text = "未登录"
            login_color = "#f87171"
            summary = "当前未检测到可复用的登录状态，需要先在浏览器中手动登录 PTA。"
            action = "建议操作：点击“打开浏览器并手动登录”。"

        self.status_login_value.configure(text=login_text, text_color=login_color)
        self.status_browser_value.configure(text=browser_text, text_color=browser_color)
        self.status_cookie_value.configure(text=cookie_text, text_color=cookie_color)
        self.status_summary_label.configure(text=summary)
        self.status_action_label.configure(text=action)

    def _poll_runtime_state(self):
        self._refresh_status_ui()
        self._sync_code_stats()
        self.root.after(1500, self._poll_runtime_state)

    def _sync_code_stats(self):
        content = self.text_area.get("1.0", "end-1c")
        if not content:
            lines = 0
            chars = 0
        else:
            lines = content.count("\n") + 1
            chars = len(content)
        self.code_stats_label.configure(text=f"行数：{lines}  字符数：{chars}")

    def _on_code_change(self, _event=None):
        self._sync_code_stats()

    def _load_default_code(self):
        if os.path.exists(CODE_FILE):
            try:
                with open(CODE_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                self.text_area.insert("1.0", content)
            except Exception as e:
                self.log(f"[错误] 读取 {CODE_FILE} 失败: {e}")

    def load_code_from_file(self):
        self.text_area.delete("1.0", "end")
        self._load_default_code()
        self._sync_code_stats()
        self.log(f"[信息] 已从 {CODE_FILE} 重新加载内容。")

    def save_code_to_file(self):
        try:
            with open(CODE_FILE, "w", encoding="utf-8") as f:
                f.write(self.text_area.get("1.0", "end-1c"))
            self.log(f"[成功] 当前代码已保存到 {CODE_FILE}。")
        except Exception as e:
            self.log(f"[错误] 保存 {CODE_FILE} 失败: {e}")

    def clear_code_area(self):
        self.text_area.delete("1.0", "end")
        self._sync_code_stats()
        self.log("[信息] 已清空代码输入区。")

    def log(self, message):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", f"[{self._get_time()}] {message}\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")
        self.root.update_idletasks()
        self._refresh_status_ui()

    def _get_time(self):
        return datetime.datetime.now().strftime("%H:%M:%S")

    def _has_live_driver(self):
        if not self.driver:
            return False
        try:
            _ = self.driver.current_url
            return True
        except Exception:
            self.driver = None
            return False

    def _close_current_driver(self):
        if not self.driver:
            return
        try:
            self.driver.quit()
        except Exception:
            pass
        finally:
            self.driver = None

    def _clear_login_state(self):
        self._close_current_driver()
        if os.path.exists(COOKIES_FILE):
            try:
                os.remove(COOKIES_FILE)
                self.log(f"[成功] 已删除旧的 {COOKIES_FILE}。")
            except Exception as e:
                self.log(f"[错误] 删除 {COOKIES_FILE} 失败：{e}")

    def _set_buttons_state(self, state):
        self.login_btn.configure(state=state)
        self.start_btn.configure(state=state)
        self.auto_btn.configure(state=state)
        self.switch_btn.configure(state=state)
        self.load_btn.configure(state=state)
        self.save_btn.configure(state=state)
        self.clear_btn.configure(state=state)
        self.about_btn.configure(state=state)

    def show_about_dialog(self):
        if self.about_window is not None:
            try:
                if self.about_window.winfo_exists():
                    self.about_window.focus()
                    self.about_window.lift()
                    return
            except Exception:
                self.about_window = None

        about_width = 500
        about_height = 370
        about = ctk.CTkToplevel(self.root)
        self.about_window = about
        about.title("关于")
        about.geometry(f"{about_width}x{about_height}")
        about.resizable(False, False)
        about.transient(self.root)
        about.lift()
        about.attributes("-topmost", True)
        about.configure(fg_color="#08111f")
        self._apply_window_icon(about)
        self._center_toplevel(about, about_width, about_height)

        def _close_about():
            try:
                about.destroy()
            finally:
                self.about_window = None

        about.protocol("WM_DELETE_WINDOW", _close_about)

        panel = ctk.CTkFrame(
            about,
            corner_radius=20,
            fg_color="#0d1b31",
            border_width=1,
            border_color="#1a4b78",
        )
        panel.pack(fill="both", expand=True, padx=16, pady=16)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)

        content = ctk.CTkFrame(panel, fg_color="transparent")
        content.grid(row=0, column=0, sticky="nsew")

        about_logo = self._get_logo_image(64)
        if about_logo is not None:
            about_logo_label = tk.Label(
                content,
                image=about_logo,
                bg="#0d1b31",
                bd=0,
                highlightthickness=0,
            )
            about_logo_label.image = about_logo
            about_logo_label.pack(pady=(0, 8))

        ctk.CTkLabel(
            content,
            text="ABOUT",
            font=self.footer_font,
            text_color="#7dd3fc",
            fg_color="#0a2238",
            corner_radius=999,
            padx=10,
            pady=3,
        ).pack(pady=(0, 8))

        ctk.CTkLabel(
            content,
            text="关于本软件",
            font=self.section_title_font,
            text_color="#8be9fd",
        ).pack(pady=(0, 6))

        ctk.CTkLabel(
            content,
            text="PTA 自动代码写入工具",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=22, weight="bold"),
            text_color="#dbeafe",
        ).pack()

        info_card = ctk.CTkFrame(
            content,
            fg_color="#0a1220",
            corner_radius=14,
            border_width=1,
            border_color="#163554",
        )
        info_card.pack(pady=(18, 12))
        ctk.CTkLabel(
            info_card,
            text=(
                "作者：Z-baozi\n"
                "联系方式：scholartime@qq.com\n"
                "版本：v4.2\n"
                "更新时间：2026-05-28\n"
                "项目：PTA 自动代码写入工具"
            ),
            font=self.section_hint_font,
            text_color="#c9d8ea",
            justify="center",
        ).pack(padx=16, pady=14)

        ctk.CTkLabel(
            content,
            text=(
                "说明：用于辅助演示浏览器自动化、界面交互与代码写入流程。\n"
                "本软件仅供学习与技术交流使用，请勿将其用于违反平台规则或不当用途。"
            ),
            font=self.section_hint_font,
            text_color="#9fb3c8",
            justify="center",
            wraplength=430,
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            content,
            text="Designed by Z-baozi",
            font=self.footer_font,
            text_color="#fbbf24",
        ).pack()

        about_button_bar = ctk.CTkFrame(content, fg_color="transparent")
        about_button_bar.pack(fill="x", pady=(18, 0))

        ctk.CTkButton(
            about_button_bar,
            text="关闭",
            font=self.button_font,
            width=124,
            height=36,
            corner_radius=18,
            fg_color="#17466e",
            hover_color="#24679f",
            border_width=1,
            border_color="#58a6dd",
            command=_close_about,
        ).pack(anchor="center")

    def start_switch_account_thread(self):
        confirmed = messagebox.askyesno(
            "切换账号",
            "这会关闭当前 PTA 浏览器并清空本地登录态，然后重新打开浏览器供您登录新账号。是否继续？",
        )
        if not confirmed:
            return

        self._set_buttons_state("disabled")
        self.log("[信息] 正在切换账号...")
        thread = threading.Thread(target=self._run_switch_account, daemon=True)
        thread.start()

    def start_login_thread(self):
        self._set_buttons_state("disabled")
        self.log("[信息] 正在启动登录流程...")
        thread = threading.Thread(target=self._run_login, daemon=True)
        thread.start()

    def start_full_auto_thread(self):
        code_content = self.text_area.get("1.0", "end").strip()
        if not code_content:
            messagebox.showwarning("警告", "请输入要写入的代码内容！")
            return

        self._set_buttons_state("disabled")
        self.log("[信息] 启动全自动流程：登录 -> 写入")
        thread = threading.Thread(target=self._run_full_auto, args=(code_content,), daemon=True)
        thread.start()

    def _run_full_auto(self, code_content):
        try:
            if not self._has_live_driver():
                if os.path.exists(COOKIES_FILE):
                    self.log("[信息] 检测到已有 Cookie，准备启动浏览器...")
                else:
                    self.log("[警告] 未检测到登录态，正在打开浏览器，请您手动登录...")
                    self.driver = get_pta_cookies(
                        status_callback=self.log,
                        keep_browser_open=True,
                    )
                    if not self.driver:
                        self.log("[错误] 登录流程未完成，自动写入已中止。")
                        return

            self.driver = auto_type_pta(
                code_content=code_content,
                status_callback=self.log,
                existing_driver=self.driver,
            )
        except Exception as e:
            self.log(f"[错误] 全自动流程发生错误: {e}")
        finally:
            self.root.after(0, lambda: self._set_buttons_state("normal"))

    def _run_login(self):
        try:
            self.log("[信息] 浏览器已打开后，请在页面中手动完成登录。")
            self.driver = get_pta_cookies(
                status_callback=self.log,
                keep_browser_open=True,
            )
            if self.driver:
                self.log("[成功] 登录成功！Cookies 已保存。")
                messagebox.showinfo("成功", "登录成功，浏览器会保持打开，接下来可以直接写入代码。")
            else:
                self.log("[错误] 登录失败或超时。")
        except Exception as e:
            self.log(f"[错误] 登录过程发生错误: {e}")
        finally:
            self.root.after(0, lambda: self._set_buttons_state("normal"))

    def _run_switch_account(self):
        try:
            self._clear_login_state()
            self.log("[信息] 旧账号会话已清理，正在打开浏览器，请登录新账号...")
            self.driver = get_pta_cookies(
                status_callback=self.log,
                keep_browser_open=True,
            )
            if self.driver:
                self.log("[成功] 新账号登录成功！当前已切换到新的 PTA 账号。")
                messagebox.showinfo("切换成功", "已切换到新账号，接下来可以直接写入代码。")
            else:
                self.log("[错误] 新账号登录未完成。")
        except Exception as e:
            self.log(f"[错误] 切换账号过程中发生错误: {e}")
        finally:
            self.root.after(0, lambda: self._set_buttons_state("normal"))

    def start_typing_thread(self):
        code_content = self.text_area.get("1.0", "end").strip()
        if not code_content:
            messagebox.showwarning("警告", "请输入要写入的代码内容！")
            return

        try:
            with open(CODE_FILE, "w", encoding="utf-8") as f:
                f.write(code_content)
        except Exception:
            pass

        self._set_buttons_state("disabled")
        self.log("[信息] 正在启动自动写入流程...")
        thread = threading.Thread(target=self._run_typing, args=(code_content,), daemon=True)
        thread.start()

    def _run_typing(self, code_content):
        try:
            self.driver = auto_type_pta(
                code_content=code_content,
                status_callback=self.log,
                existing_driver=self.driver,
            )
        except Exception as e:
            self.log(f"[错误] 写入过程发生错误: {e}")
        finally:
            self.root.after(0, lambda: self._set_buttons_state("normal"))


if __name__ == "__main__":
    root = ctk.CTk()
    app = PTATypeApp(root)
    root.mainloop()
