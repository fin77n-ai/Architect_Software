import subprocess
import threading

_STARTUP_TIMEOUT = 5  # seconds to wait before assuming server started OK

def run_and_catch(command_list, cwd=None):
    print(f"🚀 正在运行: {' '.join(command_list)}...")
    proc = subprocess.Popen(
        command_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd,
    )
    try:
        stdout, stderr = proc.communicate(timeout=_STARTUP_TIMEOUT)
        # Process exited within timeout — it crashed
        if proc.returncode != 0:
            print("\n❌ 捕获到程序崩溃！")
            return (stderr or stdout).strip() or f"进程以退出码 {proc.returncode} 退出"
        # Exited cleanly (e.g. a one-shot script)
        return None
    except subprocess.TimeoutExpired:
        # Still running after timeout — server started OK
        proc.kill()
        proc.communicate()
        return None
