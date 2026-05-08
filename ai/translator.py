import os
import json
import urllib.request
import urllib.error
import ssl

def translate_error_with_deepseek(error_text, code_context=None, arch_context=None):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return "⚠️ 错误: 找不到 DEEPSEEK_API_KEY 环境变量。"

    print("🧠 正在呼叫 AI 架构师分析报错与代码...")

    url = "https://api.deepseek.com/chat/completions"

    system_prompt = "你是一个资深的程序员导师。用简洁的大白话解释报错原因，然后直接给出可以粘贴使用的修复代码片段。不要废话，直接给结论和代码。"

    user_prompt = f"我的程序崩溃了，报错信息：\n```\n{error_text}\n```\n"
    if arch_context:
        user_prompt += f"\n项目架构依赖关系（供参考）：\n{arch_context}\n"
    if code_context:
        user_prompt += f"\n报错位置的代码（👉 是出错行）：\n```python\n{code_context}\n```\n"
    user_prompt += "\n请回答：\n1. **根本原因**：一句话解释为什么报错\n2. **修复代码**：直接给出改好的代码片段（可以直接粘贴）\n3. **预防建议**：一句话说如何避免"

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
            result = json.loads(response.read().decode('utf-8'))
            ai_reply = result['choices'][0]['message']['content']
            return ai_reply
    except urllib.error.URLError as e:
        return f"⚠️ 调用 AI 失败: {e}"
