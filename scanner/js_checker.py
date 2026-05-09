import re
import os

# JS built-ins and browser globals that don't need to be user-defined
_BUILTINS = {
    'alert', 'confirm', 'prompt', 'console', 'setTimeout', 'clearTimeout',
    'setInterval', 'clearInterval', 'parseInt', 'parseFloat', 'isNaN',
    'JSON', 'Math', 'Date', 'Array', 'Object', 'String', 'Boolean', 'Number',
    'document', 'window', 'event', 'fetch', 'location', 'history',
    'Promise', 'Error', 'this', 'if', 'return', 'new',
}

def _extract_html_calls(html):
    """Return set of top-level function names invoked in HTML event attributes.
    Handles both double- and single-quoted attributes, and skips method calls."""
    calls = set()
    # Double-quoted attributes: on*="..." (inner single quotes are fine)
    for attr_val in re.findall(r'on\w+\s*=\s*"([^"]+)"', html):
        for name in re.findall(r'(?<!\.)(?<![.\w])([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(', attr_val):
            calls.add(name)
    # Single-quoted attributes: on*='...' (inner double quotes are fine)
    for attr_val in re.findall(r"on\w+\s*=\s*'([^']+)'", html):
        for name in re.findall(r'(?<!\.)(?<![.\w])([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(', attr_val):
            calls.add(name)
    return calls

def _extract_js_definitions(js):
    """Return set of top-level function names defined in JS source."""
    defined = set()
    patterns = [
        r'function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*\(',
        r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s*)?\(',
        r'(?:const|let|var)\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=\s*(?:async\s+)?function',
        r'([a-zA-Z_$][a-zA-Z0-9_$]*)\s*[:=]\s*(?:async\s+)?function',
    ]
    for p in patterns:
        defined.update(re.findall(p, js))
    return defined

def check_frontend(project_root):
    """
    Statically check that every JS function called from HTML is defined
    somewhere in the project's JS files.

    Returns (issues, stats) where issues is a list of human-readable strings
    and stats is a dict with counts.
    """
    html_files, js_files = [], []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if not d.startswith('.')
                   and d not in ('node_modules', '__pycache__', 'venv', '.venv', 'env', 'dist', 'build')]
        for f in files:
            path = os.path.join(root, f)
            if f.endswith('.html'):
                html_files.append(path)
            elif f.endswith('.js'):
                js_files.append(path)

    if not html_files:
        return [], {'html': 0, 'js': len(js_files), 'missing': 0}

    # Collect all defined functions across JS files
    defined = set()
    for p in js_files:
        try:
            with open(p, encoding='utf-8') as f:
                defined.update(_extract_js_definitions(f.read()))
        except Exception:
            pass

    issues = []
    for html_path in html_files:
        try:
            with open(html_path, encoding='utf-8') as f:
                html = f.read()
        except Exception:
            continue
        called = _extract_html_calls(html)
        missing = sorted(called - defined - _BUILTINS)
        rel = os.path.relpath(html_path, project_root)
        for fn in missing:
            issues.append(f"  ❌ [{rel}] 调用了未定义的 JS 函数: {fn}()")

    stats = {'html': len(html_files), 'js': len(js_files), 'missing': len(issues)}
    return issues, stats
