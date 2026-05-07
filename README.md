# 🗺️ Architect (架构师助手)

> **把复杂项目“小白化”，用极低成本找 Bug 的可视化架构师助手。**

Architect 是一个运行在本地的轻量级 CLI 工具。它结合了**传统静态代码分析**与**大语言模型（LLM）的智能诊断**，为你提供上帝视角的项目拓扑图，并在程序报错时，提供精准的跨文件链路追踪和“大白话”修复建议。

## ✨ 核心特性

- **🚀 极低成本的 AI 诊断**：不把整个项目塞给 AI。本地引擎精准提取“案发现场”及跨文件调用链，每次诊断仅需几百 Token（不到一分钱）。
- **🕸️ 全局架构可视化 (`architect map`)**：一键扫描项目，在浏览器中生成交互式架构拓扑图。支持节点高亮、源码穿透查看。
- **🧠 AI 智能分类与打标**：自动提取函数名，利用 AI 将文件智能归类为 `[Entry, UI, Logic, Data, Utils]`，并在拓扑图上以不同颜色区分。
- **📄 自动生成交接文档**：自动提取项目依赖（`package.json` / `requirements.txt`），并在项目根目录生成 `ARCHITECTURE.md`，供新开发者或 AI 编程助手（如 Cursor/Aider）快速接手。
- **🌍 多语言支持**：原生支持 Python (`.py`) 及现代前端生态 (`.js`, `.jsx`, `.ts`, `.tsx`, `.vue`)，智能推断前端路径别名。
- **🎛️ 智能噪音过滤**：网页端内置分类过滤器，一键隐藏 `Utils` 等边缘节点，让核心业务逻辑一目了然。

## 🛠️ 安装与配置

1. **克隆项目到本地**
   ```bash
   # 假设放在桌面
   cd ~/Desktop
   git clone <你的仓库地址> Architect_Software
   ```

2. **配置 DeepSeek API Key**
   Architect 默认使用极具性价比的 `deepseek-chat` (Flash) 模型。
   ```bash
   # 将这行添加到你的 ~/.zshrc 或 ~/.bashrc 中
   export DEEPSEEK_API_KEY="your_api_key_here"
   ```

3. **注册为全局命令**
   ```bash
   mkdir -p ~/.local/bin
   cat << 'SCRIPT' > ~/.local/bin/architect
   #!/bin/bash
   python3 "$HOME/Desktop/Architect_Software/main.py" "$@"
   SCRIPT
   chmod +x ~/.local/bin/architect
   ```
   *(确保 `~/.local/bin` 在你的系统 `$PATH` 中)*

## 🎮 使用指南

### 模式一：找 Bug 模式 (Error Tracing)
当你的程序跑不通时，不要直接运行它，而是用 `architect` 接管：
```bash
architect python3 my_script.py
# 或者
architect node server.js
```
**它会做什么？**
1. 拦截终端里的红色报错堆栈。
2. 顺藤摸瓜，提取出错文件及其上游调用者的真实代码（跨文件追踪）。
3. 呼叫 AI 给出大白话修改建议。
4. 自动打开浏览器，画出故障链路图，并高亮案发现场。

### 模式二：看全景模式 (Global Mapping)
接手一个新项目，或者想梳理现有架构时，在项目根目录下运行：
```bash
architect map
```
**它会做什么？**
1. 深度扫描所有支持的源码文件，解析 `import/require` 依赖关系。
2. 呼叫 AI 对所有文件进行业务语义分类。
3. 在浏览器中生成一张五颜六色的、带智能过滤器的全景架构图。
4. 在当前目录下生成 `ARCHITECTURE.md` 交接文档。

## 📦 依赖说明
- **后端**: 纯 Python 3 原生实现，**零第三方依赖**（无需 `pip install`）。
- **前端**: 网页端通过 CDN 引入 `Vis.js` (画图) 和 `Highlight.js` (代码高亮)。

## 💡 为什么做这个工具？
目前的 AI 编程工具（如 Cursor）在处理大型项目时，往往面临“上下文过长、成本高昂、容易幻觉”的问题。Architect 的哲学是：**让传统静态分析工具干苦力（寻址、画图），让 AI 做大脑（局部诊断、语义分类）**。通过这种混合架构，实现了体验与成本的完美平衡。

---
*Built with passion and a lot of prompts.* 🚀
