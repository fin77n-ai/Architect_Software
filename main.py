import sys
import json
import threading
import webbrowser
import http.server
import socketserver
import urllib.parse
import os
import time
import socket

SOFTWARE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SOFTWARE_DIR)

from tracer.error_catcher import run_and_catch
from tracer.multi_extractor import extract_multi_file_context
from ai.translator import translate_error_with_deepseek
from scanner.static_mapper import scan_project, save_cache, detect_run_command
from scanner.brief_generator import generate_brief, generate_handoff_template, diff_architecture, format_diff

# 全局变量，记录用户当前扫描的项目根目录
PROJECT_ROOT = ""

class ArchitectHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # 拦截 /api/code 请求
        if self.path.startswith('/api/code'):
            parsed_path = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed_path.query)
            if 'file' in query:
                rel_file_path = query['file'][0]
                # 拼接出真实的文件绝对路径
                abs_file_path = os.path.join(PROJECT_ROOT, rel_file_path)
                
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f:
                        code_content = f.read()
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(code_content.encode('utf-8'))
                except Exception as e:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(f"无法读取文件: {e}".encode('utf-8'))
            return
            
        # 其他请求按默认静态文件处理
        super().do_GET()
        
    def log_message(self, format, *args):
        pass # 禁用日志输出

def find_free_port(start=8088):
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    return start

def start_web_server(port):
    ui_dir = os.path.join(SOFTWARE_DIR, 'ui')
    os.chdir(ui_dir)
    with socketserver.TCPServer(("", port), ArchitectHTTPRequestHandler) as httpd:
        httpd.serve_forever()

def generate_and_show_ui(ui_data):
    ui_dir = os.path.join(SOFTWARE_DIR, 'ui')
    json_path = os.path.join(ui_dir, 'data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(ui_data, f, ensure_ascii=False, indent=2)

    port = find_free_port()
    print("🌐 正在启动可视化界面...")
    server_thread = threading.Thread(target=start_web_server, args=(port,), daemon=True)
    server_thread.start()
    time.sleep(1)
    webbrowser.open(f'http://localhost:{port}')
    
    print("\n✨ 请在弹出的浏览器窗口中查看可视化报告。（按 Ctrl+C 退出）")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 退出 Architect.")
        sys.exit(0)

def main():
    global PROJECT_ROOT
    print("=== 🛠️ Architect 诊断助手 ===")
    if len(sys.argv) < 2:
        print("用法:")
        print("  architect map                    — 扫描项目，生成架构图")
        print("  architect doctor                 — 运行项目并自动诊断报错")
        print("  architect brief                  — 生成完整项目 Brief 给 AI 执行模型")
        print("  architect brief --module [层]    — 生成指定模块 Brief（Entry/UI/Logic/Data/Utils）")
        print("  architect handoff                — 生成 Handoff 模板（让 AI 执行模型填写）")
        print("  architect handoff --module [层]  — 指定模块的 Handoff 模板")
        print("  architect diff                   — 对比当前代码与上次 map 的架构变化")
        print("  architect <命令>                 — 运行命令并诊断报错（例如: architect python3 main.py）")
        return

    PROJECT_ROOT = os.getcwd()

    if sys.argv[1] == "map":
        print("🗺️ 启动全局架构扫描模式...")
        run_command = detect_run_command(PROJECT_ROOT)
        if run_command:
            print(f"✅ 自动检测到运行命令: {' '.join(run_command)}")
        else:
            print("💬 未能自动检测运行命令，请手动输入（例如: python3 main.py）：")
            try:
                cmd_input = input("> ").strip()
                run_command = cmd_input.split() if cmd_input else None
            except (EOFError, KeyboardInterrupt):
                run_command = None
        graph_data = scan_project(PROJECT_ROOT, run_command)
        save_cache(PROJECT_ROOT, graph_data, run_command)
        ui_data = {
            "nodes": graph_data["nodes"],
            "edges": graph_data["edges"],
            "diagnosis": "这是当前项目的全局静态架构图。\n\n👉 交互指南：\n1. 点击任意节点：高亮显示其上下游依赖链路。\n2. 点击任意节点：在下方代码面板中查看其真实源码。\n3. 点击空白处：恢复全景图。"
        }
        generate_and_show_ui(ui_data)
        return

    if sys.argv[1] == "doctor":
        cache_path = os.path.join(PROJECT_ROOT, '.architect', 'index.json')
        if not os.path.exists(cache_path):
            print("⚠️ 还没有架构缓存，请先运行: architect map")
            return
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        run_command = cache.get('run_command')
        if not run_command:
            print("💬 缓存中没有运行命令，请手动输入（例如: python3 main.py）：")
            try:
                cmd_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                cmd_input = ""
            if not cmd_input:
                return
            run_command = cmd_input.split()
            cache['run_command'] = run_command
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

        arch_lines = [f"  {e['from']} → {e['to']}" for e in cache.get('edges', [])]
        arch_context = "项目文件依赖关系：\n" + "\n".join(arch_lines) if arch_lines else None

        MAX_RETRIES = 3
        attempts = 0
        while attempts < MAX_RETRIES:
            attempts += 1
            print(f"\n🩺 Doctor 模式（第 {attempts}/{MAX_RETRIES} 次）— 运行: {' '.join(run_command)}")
            error_text = run_and_catch(run_command, cwd=PROJECT_ROOT)
            if not error_text:
                print("🎉 程序完美运行！")
                return
            print("🔍 正在追踪跨文件调用链路...")
            code_context, call_chain = extract_multi_file_context(error_text, cwd=PROJECT_ROOT)
            ai_diagnosis = translate_error_with_deepseek(error_text, code_context, arch_context)

            nodes = [dict(n) for n in cache.get('nodes', [])]
            edges = cache.get('edges', [])
            error_file_ids = {step['id'] for step in call_chain}
            for node in nodes:
                if node['id'] in error_file_ids or os.path.basename(node['id']) in error_file_ids:
                    node['color'] = {"background": "#FF1744", "border": "#D50000"}
                    node['font'] = {"color": "#fff"}
                    node['borderWidth'] = 3

            ui_data = {"nodes": nodes, "edges": edges, "diagnosis": ai_diagnosis}
            generate_and_show_ui(ui_data)

            if attempts < MAX_RETRIES:
                print(f"\n修复好了吗？按 Enter 重新运行，或 Ctrl+C 退出...")
                try:
                    input()
                except (KeyboardInterrupt, EOFError):
                    print("\n👋 退出 Doctor 模式。")
                    return
            else:
                print(f"\n💀 已连续失败 {MAX_RETRIES} 次，请检查上方的 AI 诊断报告后手动修复。")
        return

    if sys.argv[1] == "brief":
        cache_path = os.path.join(PROJECT_ROOT, '.architect', 'index.json')
        if not os.path.exists(cache_path):
            print("⚠️ 还没有架构缓存，请先运行: architect map")
            return
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        module = None
        if '--module' in sys.argv:
            idx = sys.argv.index('--module')
            if idx + 1 < len(sys.argv):
                module = sys.argv[idx + 1]
        print(generate_brief(cache, PROJECT_ROOT, module))
        return

    if sys.argv[1] == "handoff":
        cache_path = os.path.join(PROJECT_ROOT, '.architect', 'index.json')
        if not os.path.exists(cache_path):
            print("⚠️ 还没有架构缓存，请先运行: architect map")
            return
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        module = None
        if '--module' in sys.argv:
            idx = sys.argv.index('--module')
            if idx + 1 < len(sys.argv):
                module = sys.argv[idx + 1]
        print(generate_handoff_template(cache, module))
        return

    if sys.argv[1] == "diff":
        cache_path = os.path.join(PROJECT_ROOT, '.architect', 'index.json')
        if not os.path.exists(cache_path):
            print("⚠️ 还没有架构缓存，请先运行: architect map")
            return
        with open(cache_path, 'r', encoding='utf-8') as f:
            old_cache = json.load(f)
        print("🔍 正在重新扫描项目结构...")
        new_data = scan_project(PROJECT_ROOT)
        diff = diff_architecture(old_cache, new_data)
        print(format_diff(diff))
        return

    command_to_run = sys.argv[1:]
    cache_path = os.path.join(PROJECT_ROOT, '.architect', 'index.json')
    arch_context = None
    cached_nodes, cached_edges = [], []
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        arch_lines = [f"  {e['from']} → {e['to']}" for e in cache.get('edges', [])]
        arch_context = "项目文件依赖关系：\n" + "\n".join(arch_lines) if arch_lines else None
        cached_nodes = cache.get('nodes', [])
        cached_edges = cache.get('edges', [])

    error_text = run_and_catch(command_to_run, cwd=PROJECT_ROOT)
    if error_text:
        print("🔍 正在追踪跨文件调用链路...")
        code_context, call_chain = extract_multi_file_context(error_text, cwd=PROJECT_ROOT)
        ai_diagnosis = translate_error_with_deepseek(error_text, code_context, arch_context)

        if cached_nodes:
            nodes = [dict(n) for n in cached_nodes]
            error_file_ids = {step['id'] for step in call_chain}
            for node in nodes:
                if node['id'] in error_file_ids or os.path.basename(node['id']) in error_file_ids:
                    node['color'] = {"background": "#FF1744", "border": "#D50000"}
                    node['font'] = {"color": "#fff"}
            ui_data = {"nodes": nodes, "edges": cached_edges, "diagnosis": ai_diagnosis}
        else:
            nodes, edges, added = [], [], set()
            for i, step in enumerate(call_chain):
                if step['id'] not in added:
                    nodes.append({"id": step['id'], "label": step['label']})
                    added.add(step['id'])
                if i > 0 and call_chain[i-1]['id'] != step['id']:
                    edges.append({"from": call_chain[i-1]['id'], "to": step['id']})
            ui_data = {"nodes": nodes, "edges": edges, "diagnosis": ai_diagnosis}

        generate_and_show_ui(ui_data)
    else:
        print("🎉 程序完美运行！")

if __name__ == "__main__":
    main()
