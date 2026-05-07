import os
import json
import urllib.request
import urllib.error
import ssl

def translate_error_with_deepseek(error_text, code_context=None):
    """
    调用 DeepSeek API，结合报错信息和代码上下文进行诊断。
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        return "⚠️ 错误: 找不到 DEEPSEEK_API_KEY 环境变量。"

    print("🧠 正在呼叫 AI 架构师分析报错与代码...")

    url = "https://api.deepseek.com/chat/completions"
    
    system_prompt = "你是一个资深的程序员导师。你的任务是用最简单、通俗的大白话向新手解释程序报错的原因，并给出具体的修改建议。不要说废话，直接指出问题所在。"
    
    # 将代码上下文加入到 Prompt 中
    user_prompt = f"我的程序崩溃了，以下是截获的报错信息：\n```\n{error_text}\n```\n"
    if code_context:
        user_prompt += f"\n这是报错位置附近的代码（带有 👉 标记的是出错行）：\n```python\n{code_context}\n```\n"
        
    user_prompt += "\n请告诉我：1. 为什么报错？ 2. 结合代码，我具体应该怎么修改？"

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
        with urllib.request.urlopen(req, context=ctx) as response:
            result = json.loads(response.read().decode('utf-8'))
            ai_reply = result['choices'][0]['message']['content']
            return ai_reply
    except urllib.error.URLError as e:
        return f"⚠️ 调用 AI 失败: {e}"
