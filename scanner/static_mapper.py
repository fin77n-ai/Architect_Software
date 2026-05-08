import os
import json
import ast
import re
import urllib.request
import urllib.error
import ssl

def get_python_info(filepath):
    imports = set()
    functions = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read(), filename=filepath)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names: imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module: imports.add(node.module)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                if not node.name.startswith('__'): functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                functions.append(f"Class:{node.name}")
    except Exception:
        pass
    return imports, functions

def get_js_ts_info(filepath):
    imports = set()
    functions = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        for pattern in [
            re.compile(r'import\s+.*?[\'"]([^\'"]+)[\'"]'),
            re.compile(r'export\s+.*?[\'"]([^\'"]+)[\'"]'),
            re.compile(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)'),
            re.compile(r'import\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)')
        ]:
            for match in pattern.findall(content):
                if match.endswith(('.css', '.scss', '.less', '.png', '.jpg', '.svg', '.json')):
                    continue
                if match.startswith('.') or match.startswith('/') or match.startswith('@/') or match.startswith('~/'):
                    imports.add(match)
        func_matches = re.findall(r'(?:function|class)\s+([a-zA-Z0-9_]+)', content)
        const_matches = re.findall(r'(?:const|let|var)\s+([A-Z][a-zA-Z0-9_]+)\s*=', content)
        all_funcs = list(set(func_matches + const_matches))
        all_funcs.sort(key=lambda x: (not x[0].isupper(), x))
        functions = all_funcs[:5]
    except Exception:
        pass
    return imports, functions

def classify_files_with_ai(file_info_dict):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key: return {}
    print("🧠 正在呼叫 AI 架构师进行模块归类...")
    compact_info = {k: v['functions'] for k, v in file_info_dict.items() if v['functions']}
    if not compact_info: return {}
    
    prompt = f"""
你是一个资深的软件架构师。请根据以下文件列表及其包含的函数/类/组件名，将它们划分到以下 5 个架构类别中：
1. "Entry": 入口与路由 (main, app, router, index 等)
2. "UI": 视图与界面 (components, render, html, jsx, vue 等)
3. "Logic": 核心业务逻辑 (services, controllers, process, hooks 等)
4. "Data": 数据与存储 (db, models, api_client, store, query 等)
5. "Utils": 工具与配置 (utils, config, format, constants 等)

文件信息：
{json.dumps(compact_info, ensure_ascii=False)}

请直接返回一个 JSON 对象，键为文件路径，值为类别名称（必须是上述 5 个英文单词之一）。不要输出任何其他文字。
"""
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", 
                                 data=json.dumps(data).encode('utf-8'), 
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, 
                                 method='POST')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            return json.loads(result['choices'][0]['message']['content'])
    except Exception as e:
        print(f"⚠️ AI 分类失败: {e}")
        return {}

# ==========================================
# 核心新增：提取项目依赖清单
# ==========================================
def extract_project_dependencies(directory):
    deps_info = ""
    
    # 1. 尝试读取 Node.js 的 package.json
    pkg_path = os.path.join(directory, 'package.json')
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg_data = json.load(f)
                deps = pkg_data.get('dependencies', {})
                dev_deps = pkg_data.get('devDependencies', {})
                if deps or dev_deps:
                    deps_info += "### 📦 Node.js 依赖 (package.json)\n"
                    if deps:
                        deps_info += "**生产环境依赖 (Dependencies):**\n"
                        for k, v in list(deps.items())[:15]: # 最多列出15个核心库
                            deps_info += f"- `{k}`: {v}\n"
                    if dev_deps:
                        deps_info += "**开发环境依赖 (DevDependencies):**\n"
                        for k, v in list(dev_deps.items())[:10]:
                            deps_info += f"- `{k}`: {v}\n"
                    deps_info += "\n"
        except Exception:
            pass

    # 2. 尝试读取 Python 的 requirements.txt
    req_path = os.path.join(directory, 'requirements.txt')
    if os.path.exists(req_path):
        try:
            with open(req_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                core_reqs = [l.strip() for l in lines if l.strip() and not l.startswith('#')][:15]
                if core_reqs:
                    deps_info += "### 🐍 Python 依赖 (requirements.txt)\n"
                    for req in core_reqs:
                        deps_info += f"- `{req}`\n"
                    deps_info += "\n"
        except Exception:
            pass
            
    return deps_info

def generate_architecture_md(directory, nodes, edges, category_map, file_info_dict):
    md_path = os.path.join(directory, 'ARCHITECTURE.md')
    categories = {
        "Entry": {"icon": "🚪", "desc": "程序的起点与路由分发", "files": []},
        "UI": {"icon": "🎨", "desc": "视图渲染与前端组件", "files": []},
        "Logic": {"icon": "🧠", "desc": "核心业务处理与状态管理", "files": []},
        "Data": {"icon": "💾", "desc": "数据库与外部 API 交互", "files": []},
        "Utils": {"icon": "⚙️", "desc": "通用工具函数与静态配置", "files": []},
        "Unknown": {"icon": "📁", "desc": "未分类文件", "files": []}
    }
    for node in nodes:
        cat = category_map.get(node['id'], "Unknown")
        if cat not in categories: cat = "Unknown"
        categories[cat]['files'].append(node['id'])
    deps_map = {}
    for edge in edges:
        if edge['from'] not in deps_map: deps_map[edge['from']] = []
        deps_map[edge['from']].append(edge['to'])
        
    md_content = "# 项目架构全景图 (Auto-Generated by Architect)\n\n"
    md_content += "> 这是一个由 AI 辅助生成的项目架构文档。供新加入的开发者或 AI 编程助手快速理解项目结构和生态。\n\n"
    
    # 插入项目依赖清单
    deps_info = extract_project_dependencies(directory)
    if deps_info:
        md_content += "## 🛠️ 项目生态与第三方依赖\n"
        md_content += deps_info
        md_content += "---\n\n"

    for cat_name, cat_data in categories.items():
        if not cat_data['files']: continue
        md_content += f"## {cat_data['icon']} {cat_name} ({cat_data['desc']})\n"
        for file_path in cat_data['files']:
            funcs = file_info_dict.get(file_path, {}).get('functions', [])
            func_str = f"包含: `{', '.join(funcs)}`" if funcs else ""
            md_content += f"- **`{file_path}`** {func_str}\n"
            if file_path in deps_map:
                md_content += f"  - 依赖 -> `{', '.join(deps_map[file_path])}`\n"
        md_content += "\n"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"📄 已生成架构文档: {md_path}")

def scan_project(directory):
    print(f"🔍 启动强化版多语言扫描引擎...")
    nodes = []
    edges = []
    file_map = {} 
    file_info_dict = {} 
    supported_exts = ('.py', '.js', '.jsx', '.ts', '.tsx', '.vue')
    
    ignore_dirs = {'venv', 'env', 'node_modules', '__pycache__', '.git', '.idea', '.vscode', 'dist', 'build', '.architect'}
    
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        for file in files:
            if file.endswith(supported_exts):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, directory).replace('\\', '/')
                if rel_path == '.' or rel_path == '': continue
                file_map[rel_path] = full_path
                nodes.append({"id": rel_path, "label": os.path.basename(file), "title": rel_path})

    print(f"✅ 共发现 {len(nodes)} 个源代码文件。正在提取骨架...")
    all_rel_paths = list(file_map.keys())

    for node in nodes:
        file_path = file_map[node['id']]
        if node['id'].endswith('.py'):
            imports, funcs = get_python_info(file_path)
            file_info_dict[node['id']] = {'functions': funcs}
            for mod in imports:
                mod_path_suffix = mod.replace('.', '/') + '.py'
                mod_init_suffix = mod.replace('.', '/') + '/__init__.py'
                target_id = next((p for p in all_rel_paths if p.endswith(mod_path_suffix) or p.endswith(mod_init_suffix)), None)
                if target_id and target_id != node['id']:
                    edges.append({"from": node['id'], "to": target_id})
        else:
            imports, funcs = get_js_ts_info(file_path)
            file_info_dict[node['id']] = {'functions': funcs}
            current_dir = os.path.dirname(node['id'])
            for mod in imports:
                base_mod = mod.replace('@/', 'src/', 1) if mod.startswith('@/') else os.path.normpath(os.path.join(current_dir, mod))
                base_mod = base_mod.replace('\\', '/')
                possible_suffixes = [base_mod, base_mod+'.js', base_mod+'.jsx', base_mod+'.ts', base_mod+'.tsx', base_mod+'.vue', base_mod+'/index.js', base_mod+'/index.ts']
                target_id = None
                for suffix in possible_suffixes:
                    target_id = next((p for p in all_rel_paths if p.endswith(suffix)), None)
                    if target_id: break
                if target_id and target_id != node['id']:
                    edges.append({"from": node['id'], "to": target_id})

    unique_edges = []
    seen = set()
    for e in edges:
        if (e['from'], e['to']) not in seen:
            seen.add((e['from'], e['to']))
            unique_edges.append(e)

    category_map = classify_files_with_ai(file_info_dict)
    color_palette = {
        "Entry": {"background": "#F44336", "border": "#D32F2F", "font": "#fff"}, 
        "UI": {"background": "#E91E63", "border": "#C2185B", "font": "#fff"},    
        "Logic": {"background": "#9C27B0", "border": "#7B1FA2", "font": "#fff"}, 
        "Data": {"background": "#4CAF50", "border": "#388E3C", "font": "#fff"},  
        "Utils": {"background": "#9E9E9E", "border": "#616161", "font": "#fff"}, 
        "Unknown": {"background": "#607D8B", "border": "#455A64", "font": "#fff"}
    }
    for node in nodes:
        cat = category_map.get(node['id'], "Unknown")
        node['color'] = {"background": color_palette[cat]["background"], "border": color_palette[cat]["border"]}
        node['font'] = {"color": color_palette[cat]["font"]}
        node['group'] = cat 
        node['title'] = f"[{cat}] {node['title']}"

    generate_architecture_md(directory, nodes, unique_edges, category_map, file_info_dict)
    return {"nodes": nodes, "edges": unique_edges}

def detect_run_command(directory):
    pkg_path = os.path.join(directory, 'package.json')
    if os.path.exists(pkg_path):
        try:
            with open(pkg_path, 'r', encoding='utf-8') as f:
                pkg = json.load(f)
            scripts = pkg.get('scripts', {})
            for script in ['dev', 'start']:
                if script in scripts:
                    return ['npm', 'run', script]
        except Exception:
            pass
    for entry in ['main.py', 'app.py', 'run.py', 'server.py', 'index.py']:
        if os.path.exists(os.path.join(directory, entry)):
            return ['python3', entry]
    for entry in ['index.js', 'server.js', 'app.js']:
        if os.path.exists(os.path.join(directory, entry)):
            return ['node', entry]
    return None

def save_cache(directory, data, run_command=None):
    cache_dir = os.path.join(directory, '.architect')
    if not os.path.exists(cache_dir): os.makedirs(cache_dir)
    cache_data = {"nodes": data["nodes"], "edges": data["edges"]}
    if run_command:
        cache_data["run_command"] = run_command
    with open(os.path.join(cache_dir, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scan_project(test_dir)
