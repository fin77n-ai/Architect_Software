import os
import re
import ast

def get_python_function_context(filepath, target_line):
    """使用 AST 提取包含目标行的完整 Python 函数代码"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()
            lines = source_code.split('\n')
            tree = ast.parse(source_code, filename=filepath)
            
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # 如果目标行在这个函数/类的范围内
                if node.lineno <= target_line <= node.end_lineno:
                    # 提取完整的函数代码
                    extracted = []
                    for i in range(node.lineno - 1, node.end_lineno):
                        current_line_num = i + 1
                        marker = "👉 " if current_line_num == target_line else "   "
                        extracted.append(f"{marker}{current_line_num:4d} | {lines[i]}")
                    return "\n".join(extracted)
    except Exception:
        pass
    return None

def get_fallback_context(filepath, target_line, context_lines=5):
    """传统的上下 5 行提取法 (用于 JS/TS 或解析失败时)"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        start_idx = max(0, target_line - 1 - context_lines)
        end_idx = min(len(lines), target_line + context_lines)
        
        extracted = []
        for i in range(start_idx, end_idx):
            current_line_num = i + 1
            marker = "👉 " if current_line_num == target_line else "   "
            # 移除行尾换行符，防止拼接时出现空行
            extracted.append(f"{marker}{current_line_num:4d} | {lines[i].rstrip()}")
        return "\n".join(extracted)
    except Exception:
        return None

def extract_multi_file_context(error_text, context_lines=5, cwd=None):
    python_pattern = r'File "([^"]+)", line (\d+)(?:, in (\w+|<module>))?'
    js_pattern = r'at (?:.*? \()?([^:]+):(\d+):\d+\)?'

    py_matches = re.findall(python_pattern, error_text)
    js_matches = re.findall(js_pattern, error_text)

    call_chain = []
    if py_matches:
        for match in py_matches:
            call_chain.append({"file": match[0], "line": int(match[1]), "func": match[2] if len(match) > 2 else "unknown"})
    elif js_matches:
        for match in js_matches:
            call_chain.append({"file": match[0], "line": int(match[1]), "func": "unknown"})

    if not call_chain:
        return None, []

    call_chain = call_chain[-3:]
    extracted_contexts = []
    valid_chain = []
    
    for step in call_chain:
        file_path = step['file']
        line_number = step['line']
        
        if cwd and not os.path.isabs(file_path):
            file_path = os.path.join(cwd, file_path)
            
        if not os.path.exists(file_path) or "site-packages" in file_path or "node_modules" in file_path:
            continue

        # 核心改进：智能上下文提取
        context_str = f"--- 文件: {file_path} (函数: {step['func']}, 第 {line_number} 行) ---\n"
        code_snippet = None
        
        if file_path.endswith('.py'):
            # 尝试提取完整的 Python 函数
            code_snippet = get_python_function_context(file_path, line_number)
            
        if not code_snippet:
            # 如果不是 Python，或者提取函数失败，回退到传统的上下 5 行
            code_snippet = get_fallback_context(file_path, line_number, context_lines)
            
        if code_snippet:
            context_str += code_snippet
            extracted_contexts.append(context_str)
            short_name = os.path.basename(file_path)
            valid_chain.append({"id": short_name, "label": f"{short_name}\n(行 {line_number})"})

    if not extracted_contexts:
        return None, []

    return "\n\n".join(extracted_contexts), valid_chain

if __name__ == "__main__":
    pass
