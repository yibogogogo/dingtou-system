"""
量化定投择时系统 - EXE入口
双击启动 Streamlit 应用
"""
import sys
import os
import socket
import threading
import webbrowser
import time


def find_app():
    """查找app.py（兼容PyInstaller打包和源码运行）"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'app.py')


def find_free_port(start=8501):
    """查找可用端口"""
    for port in range(start, start + 10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return 8501


def main():
    app_path = find_app()
    
    if not os.path.exists(app_path):
        print(f"[ERROR] app.py not found: {app_path}")
        print(f"Current dir: {os.getcwd()}")
        input("Press Enter to exit...")
        sys.exit(1)

    os.chdir(os.path.dirname(app_path))
    port = find_free_port()

    print("=" * 60)
    print("  量化定投择时系统 v2.1")
    print("=" * 60)
    print(f"  Starting on http://localhost:{port}")
    print(f"  Press Ctrl+C to stop")
    print()

    # Open browser after a short delay
    def open_browser():
        time.sleep(2)
        webbrowser.open(f'http://localhost:{port}')

    threading.Thread(target=open_browser, daemon=True).start()

    # Use streamlit CLI directly
    sys.argv = [
        'streamlit', 'run', app_path,
        '--server.port', str(port),
        '--server.headless', 'true',
        '--browser.gatherUsageStats', 'false',
    ]
    
    from streamlit.web import cli as stcli
    stcli.main()


if __name__ == '__main__':
    main()
