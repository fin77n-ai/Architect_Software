"""
architect MCP server — exposes architect tools to any MCP-compatible client (Claude Code, Hermes, etc.)

Usage:
  python3 mcp_server.py          # starts stdio MCP server
  architect mcp                  # same, via CLI alias
"""

import os
import sys
import json

SOFTWARE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SOFTWARE_DIR)

from fastmcp import FastMCP
from scanner.static_mapper import scan_project, save_cache, detect_run_command
from scanner.brief_generator import generate_brief, diff_architecture, format_diff
from scanner.js_checker import check_frontend
from tracer.error_catcher import run_and_catch
from tracer.multi_extractor import extract_multi_file_context

mcp = FastMCP("architect")


@mcp.tool()
def project_scan(project_path: str) -> str:
    """Scan a project directory and return its architecture: files, layers, dependencies, and run command."""
    project_path = os.path.abspath(project_path)
    if not os.path.isdir(project_path):
        return f"Error: {project_path} is not a directory"

    run_command = detect_run_command(project_path)
    graph_data = scan_project(project_path, run_command)
    save_cache(project_path, graph_data, run_command)

    nodes = graph_data["nodes"]
    edges = graph_data["edges"]

    groups: dict = {}
    for node in nodes:
        g = node.get("group", "Unknown")
        groups.setdefault(g, []).append(node["id"])

    lines = [f"Architecture scan: {project_path}", f"Run command: {' '.join(run_command) if run_command else '(unknown)'}"]
    lines.append(f"{len(nodes)} files, {len(edges)} dependency edges\n")
    for g, files in groups.items():
        lines.append(f"[{g}]")
        for f in files:
            lines.append(f"  - {f}")
    lines.append("\nDependencies:")
    for e in edges:
        lines.append(f"  {e['from']} → {e['to']}")

    return "\n".join(lines)


@mcp.tool()
def get_brief(project_path: str, module: str = "") -> str:
    """Return the Architect brief for a project. Optionally filter to a specific layer (Entry/UI/Logic/Data/Utils)."""
    project_path = os.path.abspath(project_path)
    cache_path = os.path.join(project_path, ".architect", "index.json")

    # Prefer hand-written brief if it exists
    brief_md = os.path.join(project_path, "ARCHITECTURE_BRIEF.MD")
    if os.path.exists(brief_md) and not module:
        with open(brief_md, "r", encoding="utf-8") as f:
            return f.read()

    if not os.path.exists(cache_path):
        return "No architecture cache found. Run project_scan first."

    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)

    return generate_brief(cache, project_path, module or None)


@mcp.tool()
def project_health(project_path: str) -> str:
    """Run frontend static check + smoke test on a project. Returns pass/fail + details."""
    project_path = os.path.abspath(project_path)
    cache_path = os.path.join(project_path, ".architect", "index.json")

    if not os.path.exists(cache_path):
        return "No architecture cache found. Run project_scan first."

    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)

    results = []

    # Frontend check
    fe_issues, fe_stats = check_frontend(project_path)
    if fe_issues:
        results.append(f"FAIL Frontend: {fe_stats['missing']} issues")
        for issue in fe_issues:
            results.append(f"  {issue}")
    else:
        results.append(f"PASS Frontend ({fe_stats['html']} HTML / {fe_stats['js']} JS)")

    # Smoke test
    run_command = cache.get("run_command")
    if not run_command:
        results.append("SKIP Smoke test (no run command in cache)")
    else:
        error_text = run_and_catch(run_command, cwd=project_path)
        if error_text:
            results.append(f"FAIL Smoke test:")
            for line in error_text.splitlines()[:15]:
                results.append(f"  {line}")
        else:
            results.append("PASS Smoke test")

    return "\n".join(results)


@mcp.tool()
def get_file_context(project_path: str, file_path: str) -> str:
    """Read the source code of a file inside a project. file_path is relative to project_path."""
    project_path = os.path.abspath(project_path)
    abs_path = os.path.join(project_path, file_path)

    if not os.path.isfile(abs_path):
        return f"File not found: {abs_path}"

    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        lines = content.splitlines()
        if len(lines) > 500:
            content = "\n".join(lines[:500]) + f"\n\n... [{len(lines) - 500} more lines truncated]"
        return f"// {file_path}\n{content}"
    except Exception as e:
        return f"Error reading file: {e}"


@mcp.tool()
def architecture_diff(project_path: str) -> str:
    """Compare current project structure against the cached snapshot. Returns what files/deps changed."""
    project_path = os.path.abspath(project_path)
    cache_path = os.path.join(project_path, ".architect", "index.json")

    if not os.path.exists(cache_path):
        return "No architecture cache found. Run project_scan first."

    with open(cache_path, "r", encoding="utf-8") as f:
        old_cache = json.load(f)

    new_data = scan_project(project_path)
    diff = diff_architecture(old_cache, new_data)
    return format_diff(diff)


if __name__ == "__main__":
    mcp.run()
