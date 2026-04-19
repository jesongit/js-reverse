"""notion2api 服务管理脚本。

用法：
    python cli.py start     启动服务（后台运行）
    python cli.py stop      停止服务
    python cli.py restart   重启服务
    python cli.py status    查看服务状态
"""

import os
import sys
import signal
import subprocess
import requests
from dotenv import dotenv_values

if sys.platform == "win32":
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

PID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".notion2api.pid")
MAIN_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")


def get_env():
    """读取 .env 配置。"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return {}
    return dict(dotenv_values(env_path))


def get_port():
    """从 .env 读取端口配置。"""
    return str(get_env().get("PORT") or "3000")


def read_pid():
    """读取 PID 文件。"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            return int(f.read().strip())
    return None


def write_pid(pid):
    """写入 PID 文件。"""
    with open(PID_FILE, "w") as f:
        f.write(str(pid))


def remove_pid():
    """删除 PID 文件。"""
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def is_process_alive(pid):
    """检查进程是否存活。"""
    if not pid:
        return False
    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
        )
        return str(pid) in result.stdout and "No tasks are running" not in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def cmd_start():
    pid = read_pid()
    if pid and is_process_alive(pid):
        print(f"服务已在运行，PID: {pid}")
        return

    remove_pid()
    port = get_port()

    # 启动后台进程
    proc = subprocess.Popen(
        [sys.executable, MAIN_SCRIPT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    write_pid(proc.pid)

    # 健康检查
    import time
    api_key = get_env().get("API_KEY")
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    for i in range(10):
        time.sleep(0.5)
        if proc.poll() is not None:
            remove_pid()
            print("服务启动失败，请手动运行 python main.py 查看错误")
            return
        try:
            resp = requests.get(f"http://localhost:{port}/v1/models", headers=headers, timeout=2)
            if resp.status_code == 200:
                print(f"服务已启动，PID: {proc.pid}，地址: http://localhost:{port}")
                return
        except requests.ConnectionError:
            pass

    print(f"服务已启动，PID: {proc.pid}，但健康检查未通过，请手动确认")


def cmd_stop():
    pid = read_pid()
    if not pid:
        print("服务未运行")
        return
    if not is_process_alive(pid):
        remove_pid()
        print("服务未运行（残留 PID 文件已清理）")
        return

    if sys.platform == "win32":
        # Windows: 终止进程树
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.kill(pid, signal.SIGTERM)

    remove_pid()
    print(f"服务已停止，PID: {pid}")


def cmd_restart():
    cmd_stop()
    cmd_start()


def cmd_status():
    pid = read_pid()
    port = get_port()
    if not pid or not is_process_alive(pid):
        remove_pid()
        print("服务未运行")
        return

    try:
        api_key = get_env().get("API_KEY")
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        resp = requests.get(f"http://localhost:{port}/v1/models", headers=headers, timeout=2)
        if resp.status_code == 200:
            model_count = len(resp.json().get("data", []))
            print(f"服务运行中，PID: {pid}，端口: {port}，模型数: {model_count}")
            return
        print(f"服务运行中，PID: {pid}，但健康检查返回 {resp.status_code}")
    except Exception:
        print(f"服务运行中，PID: {pid}，但健康检查失败")


if __name__ == "__main__":
    commands = {"start": cmd_start, "stop": cmd_stop, "restart": cmd_restart, "status": cmd_status}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(__doc__)
        sys.exit(1)
    commands[sys.argv[1]]()
