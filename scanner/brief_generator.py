import os
import re
import json


def generate_claude_md(directory, cache):
    nodes = cache['nodes']
    run_cmd = ' '.join(cache.get('run_command') or [])

    groups = {}
    for node in nodes:
        g = node.get('group', 'Unknown')
        groups.setdefault(g, []).append(node['id'])

    routes = []
    for node in nodes:
        if node.get('group') == 'Entry':
            full_path = os.path.join(directory, node['id'])
            if node['id'].endswith('.py'):
                routes.extend(extract_flask_routes(full_path))
            elif node['id'].endswith(('.js', '.ts')):
                routes.extend(extract_express_routes(full_path))

    lines = [
        "# Architect 项目协议 (Auto-Generated)",
        "",
        "> 这个文件由 `architect map` 自动生成。",
        "> 把它分享给 Claude (Sonnet) 即可让它了解项目背景和协作规则。",
        "",
        "## 项目运行",
        f"```",
        run_cmd or "（未检测到运行命令）",
        "```",
        "",
        "## 架构分层",
    ]

    layer_desc = {
        "Entry": "入口与路由",
        "UI": "视图与界面",
        "Logic": "核心业务逻辑",
        "Data": "数据与存储",
        "Utils": "工具与配置",
        "Unknown": "未分类",
    }

    for g, files in groups.items():
        desc = layer_desc.get(g, g)
        lines.append(f"\n### [{g}] — {desc}")
        for f in files:
            lines.append(f"- `{f}`")

    if routes:
        lines += [
            "",
            "## API 接口契约",
            "（执行模型不得修改这些接口签名）",
        ]
        for r in routes:
            lines.append(f"- `{r}`")

    lines += [
        "",
        "## Architect 协作规则",
        "",
        "### 角色分工",
        "- **Claude (Sonnet)**: 规划任务、生成 brief、验收结果",
        "- **执行模型 (Gemini / Haiku)**: 按 brief 写代码，完成后填 handoff",
        "",
        "### 标准工作流",
        "```",
        "1. 用 architect brief --module [层] 生成任务 brief",
        "2. 将 brief 完整粘贴给执行模型",
        "3. 执行模型完成后输出 handoff 模板",
        "4. 用 architect diff 验证没有越界改动",
        "5. 用 architect doctor 验证程序可运行",
        "```",
        "",
        "### Brief 规则（执行模型必须遵守）",
        "1. 改动前说明要改哪个文件和原因",
        "2. 不执行任何 git 命令",
        "3. 不修改 🚫 列表中的文件",
        "4. 完成后填写 handoff 模板",
        "",
        "### 常用命令速查",
        "```bash",
        "architect map                    # 重新扫描，更新架构图",
        "architect brief                  # 生成完整 brief",
        "architect brief --module Logic   # 只开放 Logic 层给执行模型",
        "architect handoff                # 生成 handoff 模板",
        "architect diff                   # 验证架构是否被越界修改",
        "architect doctor                 # 运行项目并 AI 诊断报错",
        "```",
    ]

    claude_md_path = os.path.join(directory, 'CLAUDE.md')
    with open(claude_md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"📋 已生成协作协议: {claude_md_path}")


def extract_flask_routes(filepath):
    routes = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        pattern = re.compile(
            r"@(?:app|bp|\w+)\.route\(['\"]([^'\"]+)['\"](?:[^)]*?methods=\[([^\]]+)\])?\)",
            re.DOTALL
        )
        for m in pattern.finditer(content):
            path = m.group(1)
            methods = m.group(2).replace("'", "").replace('"', "").strip() if m.group(2) else "GET"
            routes.append(f"{methods} {path}")
    except Exception:
        pass
    return routes


def extract_express_routes(filepath):
    routes = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        pattern = re.compile(r"(?:app|router)\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]")
        for m in pattern.finditer(content):
            routes.append(f"{m.group(1).upper()} {m.group(2)}")
    except Exception:
        pass
    return routes


def generate_brief(cache, project_root, module=None):
    nodes = cache['nodes']
    run_cmd = ' '.join(cache.get('run_command') or [])

    groups = {}
    for node in nodes:
        g = node.get('group', 'Unknown')
        groups.setdefault(g, []).append(node['id'])

    # Extract API routes from Entry files
    routes = []
    for node in nodes:
        if node.get('group') == 'Entry':
            full_path = os.path.join(project_root, node['id'])
            if node['id'].endswith('.py'):
                routes.extend(extract_flask_routes(full_path))
            elif node['id'].endswith(('.js', '.ts')):
                routes.extend(extract_express_routes(full_path))

    lines = ["【Architect Brief — 请在本次任务中严格遵守】", f"项目运行: {run_cmd}", ""]

    if module:
        in_scope = groups.get(module, [])
        out_scope = [n['id'] for n in nodes if n['id'] not in in_scope]

        if not in_scope:
            available = list(groups.keys())
            return f"⚠️ 没有找到 {module} 模块。可用模块: {', '.join(available)}"

        lines.append(f"📋 本次任务范围: [{module}] 层")
        lines.append("✅ 你可以修改:")
        for f in in_scope:
            lines.append(f"   - {f}")
        lines.append("")

        if routes:
            lines.append("🔌 接口契约 (只读，不要修改):")
            for r in routes:
                lines.append(f"   {r}")
            lines.append("")

        lines.append("🚫 禁止修改以下文件:")
        for f in out_scope[:25]:
            lines.append(f"   - {f}")
        if len(out_scope) > 25:
            lines.append(f"   ... 及其他 {len(out_scope) - 25} 个文件")
    else:
        lines.append("📋 完整项目架构:")
        for g, files in groups.items():
            lines.append(f"  [{g}]")
            for f in files:
                lines.append(f"    - {f}")
        if routes:
            lines.append("")
            lines.append("🔌 API 接口:")
            for r in routes:
                lines.append(f"   {r}")

    lines += [
        "",
        "⚠️ 规则:",
        "   1. 改动前先说要改哪个文件和原因",
        "   2. 不要执行任何 git 命令",
        "   3. 完成后输出 architect handoff 模板内容",
    ]
    return "\n".join(lines)


def generate_handoff_template(cache, module=None):
    run_cmd = ' '.join(cache.get('run_command') or [])
    scope = f"[{module}] 层" if module else "全项目"
    return f"""【Architect Handoff — 任务结束前请填写】
项目运行: {run_cmd}
本次范围: {scope}

## 修改的文件
（实际改动的文件，一行一个）
-

## 每个文件的变更摘要
- 文件名: 改了什么

## 是否有超出范围的改动？
- [ ] 无越界改动
- [ ] 有，文件: ___  原因: ___

## 遗留问题 / 下一步建议
-

## 验证方式
（跑了什么测试，或者怎么确认改动有效）
-
"""


def diff_architecture(old_cache, new_data):
    old_nodes = {n['id'] for n in old_cache['nodes']}
    new_nodes = {n['id'] for n in new_data['nodes']}
    old_edges = {(e['from'], e['to']) for e in old_cache['edges']}
    new_edges = {(e['from'], e['to']) for e in new_data['edges']}

    result = {
        'added_files': sorted(new_nodes - old_nodes),
        'removed_files': sorted(old_nodes - new_nodes),
        'added_deps': sorted(new_edges - old_edges),
        'removed_deps': sorted(old_edges - new_edges),
    }
    return result


def format_diff(diff):
    lines = ["📊 架构变更报告"]
    clean = True

    if diff['added_files']:
        clean = False
        lines.append("\n➕ 新增文件:")
        for f in diff['added_files']:
            lines.append(f"   + {f}")

    if diff['removed_files']:
        clean = False
        lines.append("\n➖ 删除文件:")
        for f in diff['removed_files']:
            lines.append(f"   - {f}")

    if diff['added_deps']:
        clean = False
        lines.append("\n🔗 新增依赖:")
        for a, b in diff['added_deps']:
            lines.append(f"   + {a} → {b}")

    if diff['removed_deps']:
        clean = False
        lines.append("\n✂️ 移除依赖:")
        for a, b in diff['removed_deps']:
            lines.append(f"   - {a} → {b}")

    if clean:
        lines.append("\n✅ 架构结构无变化，Gemini 没有越界改动文件依赖。")

    return "\n".join(lines)
