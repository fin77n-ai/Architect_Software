import os
import re

def extract_code_context(error_text, context_lines=5):
    """
    从报错信息中解析出文件路径和行号，并提取该行附近的上下文代码。
    :param error_text: 完整的报错堆栈文本
    :param context_lines: 提取出错行上下各几行代码（默认上下各 5 行）
    :return: 提取到的代码字符串，如果没找到则返回 None
    """
    # 尝试匹配 Python 的报错格式：File "文件路径", line 行号
    # 例如：File "/Users/finn/Desktop/bad_code.py", line 1, in <module>
    python_match = re.search(r'File "([^"]+)", line (\d+)', error_text)
    
    # 尝试匹配 Node.js / JS 的报错格式：at 函数名 (文件路径:行号:列号)
    # 例如：at Object.<anonymous> (/Users/finn/Desktop/bad_app.js:2:1)
    js_match = re.search(r'at .*?\(([^:]+):(\d+):\d+\)', error_text)
    
    file_path = None
    line_number = None

    if python_match:
        file_path = python_match.group(1)
        line_number = int(python_match.group(2))
    elif js_match:
        file_path = js_match.group(1)
        line_number = int(js_match.group(2))
    else:
        # 如果没匹配到，说明可能不是标准的堆栈，或者没有文件信息
        return None

    # 检查文件是否存在
    if not os.path.exists(file_path):
        return f"[提取代码失败：找不到文件 {file_path}]"

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # 计算提取的起始和结束行号 (注意：行号从 1 开始，列表索引从 0 开始)
        start_idx = max(0, line_number - 1 - context_lines)
        end_idx = min(len(lines), line_number + context_lines)
        
        extracted_code = f"--- 案发现场: {file_path} (第 {line_number} 行附近) ---\n"
        for i in range(start_idx, end_idx):
            current_line_num = i + 1
            # 把真正出错的那一行用箭头标出来
            marker = "👉 " if current_line_num == line_number else "   "
            extracted_code += f"{marker}{current_line_num:4d} | {lines[i]}"
            
        return extracted_code
        
    except Exception as e:
        return f"[提取代码失败：无法读取文件 {e}]"

if __name__ == "__main__":
    # 测试代码
    dummy_error = 'Traceback (most recent call last):\n  File "/Users/finn/Desktop/Architect_Software/main.py", line 15, in <module>\n    main()'
    print(extract_code_context(dummy_error))
