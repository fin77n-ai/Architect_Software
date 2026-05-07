import subprocess

def run_and_catch(command_list, cwd=None):
    print(f"🚀 正在运行: {' '.join(command_list)}...")
    try:
        result = subprocess.run(
            command_list,
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd # 在指定目录下运行
        )
        print("输出:\n", result.stdout)
        return None
    except subprocess.CalledProcessError as e:
        print("\n❌ 捕获到程序崩溃！")
        error_output = e.stderr
        error_lines = error_output.strip().split('\n')
        last_20_lines = '\n'.join(error_lines[-20:])
        return last_20_lines
