PTA 自动代码写入工具 v4.2
作者: Z-baozi

一、源码方式使用
1. 电脑需已安装 Python 3.12 或更高版本。
2. 双击“启动GUI.bat”。
3. 首次运行会自动创建 .venv 虚拟环境并安装依赖。
4. 安装完成后会自动打开图形界面。

二、手动运行方式
1. 在当前目录打开终端。
2. 执行:
   py -m venv .venv
   .venv\Scripts\activate
   python -m pip install -r requirements.txt
   python gui_app.py

三、主要文件说明
- gui_app.py: 图形界面主程序
- pta_auto_type.py: 自动写入逻辑
- get_cookies.py: 登录态获取逻辑
- code.txt: 默认代码文件
- cookies.json: 首次登录成功后自动生成的本地登录态文件
- favicon.ico / logo.png: 图标与界面资源

四、注意事项
1. 当前分享包默认不包含任何账号登录态，首次使用请手动登录 PTA。
2. 首次运行 webdriver-manager 可能会联网下载驱动。
3. 建议在 Windows 环境下使用。
