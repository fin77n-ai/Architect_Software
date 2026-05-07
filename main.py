import sys
import json
import threading
import webbrowser
import http.server
import socketserver
import urllib.parse
import os
import time

SOFTWARE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SOFTWARE_DIR)

from tracer.error_catcher import run_and_catch
from tracer.multi_extractor import extract_multi_file_context
from ai.translator import translate_error_with_deepseek
from scanner.static_mapper import scan_project, save_cache

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

def start_web_server(port=8000):
    ui_dir = os.path.join(SOFTWARE_DIR, 'ui')
    os.chdir(ui_dir)
    try:
        with socketserver.TCPServer(("", port), ArchitectHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except OSError:
        print(f"⚠️ 端口 {port} 被占用。")

def generate_and_show_ui(ui_data):
    ui_dir = os.path.join(SOFTWARE_DIR, 'ui')
    json_path = os.path.join(ui_dir, 'data.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(ui_data, f, ensure_ascii=False, indent=2)

    print("🌐 正在启动可视化界面...")
    server_thread = threading.Thread(target=start_web_server, daemon=True)
    server_thread.start()
    time.sleep(1)
    webbrowser.open('http://localhost:8000')
    
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
        print("用法 1: architect <命令> (例如: architect python3 script.py)")
        print("用法 2: architect map - 静态扫描当前项目并生成全局架构图")
        return

    PROJECT_ROOT = os.getcwd()

    if sys.argv[1] == "map":
        print("🗺️ 启动全局架构扫描模式...")
        graph_data = scan_project(PROJECT_ROOT)
        save_cache(PROJECT_ROOT, graph_data)
        
        ui_data = {
            "nodes": graph_data["nodes"],
            "edges": graph_data["edges"],
            "diagnosis": "这是当前项目的全局静态架构图。\n\n👉 交互指南：\n1. 点击任意节点：高亮显示其上下游依赖链路。\n2. 点击任意节点：在下方代码面板中查看其真实源码。\n3. 点击空白处：恢复全景图。"
        }
        generate_and_show_ui(ui_data)
        return

    command_to_run = sys.argv[1:]
    error_text = run_and_catch(command_to_run, cwd=PROJECT_ROOT)
    
    if error_text:
        print("🔍 正在追踪跨文件调用链路...")
        code_context, call_chain = extract_multi_file_context(error_text, cwd=PROJECT_ROOT)
        
        print("🧠 正在呼叫 AI 架构师...")
        ai_diagnosis = translate_error_with_deepseek(error_text, code_context)

        nodes = []
        edges = []
        added_node_ids = set()
        
        if call_chain:
            for i, step in enumerate(call_chain):
                node_id = step['id']
                if node_id not in added_node_ids:
                    nodes.append({"id": node_id, "label": step['label']})
                    added_node_ids.add(node_id)
                if i > 0:
                    prev_id = call_chain[i-1]['id']
                    if prev_id != node_id:
                        edges.append({"from": prev_id, "to": node_id})

        ui_data = {
            "nodes": nodes,
            "edges": edges,
            "diagnosis": ai_diagnosis
        }
        generate_and_show_ui(ui_data)
    else:
        print("🎉 程序完美运行！")

if __name__ == "__main__":
    main()
