"""Hegelion MCP Setup Logic and CLI helper."""

import os
import sys
import json
import site
from pathlib import Path
from typing import Mapping
import hegelion


USAGE_NOTE = """
Hegelion MCP setup
------------------
Use this helper to generate the MCP snippet for MCP hosts like Cursor, Claude Desktop,
VS Code + Copilot, Windsurf, or Gemini CLI.

Examples:
  hegelion-setup-mcp                # print JSON snippet
  hegelion-setup-mcp --write        # write to ./mcp_config.json
  hegelion-setup-mcp --write "$HOME/Library/Application Support/Claude/claude_desktop_config.json"  # macOS Claude Desktop
  hegelion-setup-mcp --write "%APPDATA%\\Claude\\claude_desktop_config.json"  # Windows Claude Desktop
  hegelion-setup-mcp --host claude-desktop  # write to the host's default config path
  hegelion-setup-mcp --host cursor
  hegelion-setup-mcp --host vscode
  hegelion-setup-mcp --host windsurf

Optional: enable single-call CLI execution for `dialectical_single_shot` (no server-side API keys):
  hegelion-setup-mcp --llm-command-json '["codex","exec","--sandbox","read-only","-"]'
  hegelion-setup-mcp --auto-execute

Note: After modifying the config, restart your MCP host for changes to take effect.
"""


HOST_ALIASES = {
    "claude": "claude-desktop",
    "claude-desktop": "claude-desktop",
    "cursor": "cursor",
    "vscode": "vscode",
    "vs-code": "vscode",
    "windsurf": "windsurf",
}

KNOWN_HOSTS = sorted(set(HOST_ALIASES.values()))


def get_python_path():
    """Get the absolute path to the current python interpreter."""
    return sys.executable


def is_installed_in_site_packages():
    """Check if hegelion is installed in site-packages."""
    package_path = Path(hegelion.__file__).parent
    for site_package in site.getsitepackages():
        if str(package_path).startswith(site_package):
            return True
    # Also check user site packages
    if site.getusersitepackages() and str(package_path).startswith(site.getusersitepackages()):
        return True
    return False


def get_project_root():
    """Get the absolute path to the project root (if running from source)."""
    return Path(hegelion.__file__).parent.parent.absolute()


def _normalize_host(host: str) -> str:
    normalized = HOST_ALIASES.get(host.lower())
    if not normalized:
        raise ValueError(f"Unknown host '{host}'. Choose from: {', '.join(KNOWN_HOSTS)}")
    return normalized


def _windows_appdata(env: Mapping[str, str]) -> Path:
    appdata = env.get("APPDATA")
    if appdata:
        return Path(appdata)
    return Path.home() / "AppData" / "Roaming"


def resolve_host_path(
    host: str, platform: str | None = None, env: Mapping[str, str] | None = None
) -> Path:
    """Resolve a known MCP host to its default config path."""
    normalized = _normalize_host(host)
    platform = platform or sys.platform
    env = env or os.environ

    if normalized == "vscode":
        return Path(".vscode/mcp.json")

    if normalized == "cursor":
        if platform.startswith("win"):
            return _windows_appdata(env) / "Cursor" / "User" / "globalStorage" / "mcp.json"
        return Path("~/.cursor/mcp.json")

    if normalized == "windsurf":
        if platform.startswith("win"):
            return _windows_appdata(env) / "Codeium" / "Windsurf" / "mcp_config.json"
        return Path("~/.codeium/windsurf/mcp_config.json")

    if normalized == "claude-desktop":
        if platform == "darwin":
            return Path("~/Library/Application Support/Claude/claude_desktop_config.json")
        if platform.startswith("win"):
            return _windows_appdata(env) / "Claude" / "claude_desktop_config.json"
        return Path("~/.config/Claude/claude_desktop_config.json")

    raise ValueError(f"Unknown host '{host}'. Choose from: {', '.join(KNOWN_HOSTS)}")


def generate_config(
    python_path,
    project_root,
    is_installed,
    *,
    llm_command: str | None = None,
    llm_command_json: str | None = None,
    auto_execute: bool = False,
):
    """Generate the MCP config."""

    env = {}
    if not is_installed:
        # If not installed in site-packages, we likely need PYTHONPATH
        env["PYTHONPATH"] = str(project_root)

    if llm_command_json:
        env["HEGELION_LLM_COMMAND_JSON"] = llm_command_json
    elif llm_command:
        env["HEGELION_LLM_COMMAND"] = llm_command

    if auto_execute:
        env["HEGELION_MCP_AUTO_EXECUTE"] = "1"

    config = {
        "mcpServers": {
            "hegelion": {
                "command": python_path,
                "args": ["-m", "hegelion.mcp.server"],
            },
        }
    }

    if env:
        config["mcpServers"]["hegelion"]["env"] = env

    return config


def print_setup_instructions(
    dry_run: bool = False,
    *,
    llm_command: str | None = None,
    llm_command_json: str | None = None,
    auto_execute: bool = False,
):
    python_path = get_python_path()
    is_installed = is_installed_in_site_packages()
    project_root = get_project_root()

    config = generate_config(
        python_path,
        project_root,
        is_installed,
        llm_command=llm_command,
        llm_command_json=llm_command_json,
        auto_execute=auto_execute,
    )

    snippet = config["mcpServers"]
    json_output = json.dumps(snippet, indent=2)

    print("\n" + "=" * 60)
    print("MCP CONFIGURATION SNIPPET")
    print("=" * 60)
    print("Copy the snippet below into your MCP configuration file for your host:")
    print("-" * 60)
    print(json_output)
    print("-" * 60)

    print(
        "Tools available: dialectical_* (workflow/single_shot/thesis/antithesis/synthesis) "
        "and autocoding_* (init/workflow/player/coach/advance/single_shot/save/load)"
    )
    print("response_style options: json, sections, synthesis_only, conversational, bullet_points")
    print("\nCommon config paths:")
    print("  macOS Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json")
    print("  Windows Claude Desktop: %APPDATA%\\Claude\\claude_desktop_config.json")
    print("  Claude Code:          ~/.claude.json")
    print("  Cursor (macOS/Linux): ~/.cursor/mcp.json")
    print("  Cursor (Windows):     %APPDATA%\\Cursor\\User\\globalStorage\\mcp.json")
    print("  VS Code + Copilot:    .vscode/mcp.json")
    print("  Windsurf:             ~/.codeium/windsurf/mcp_config.json")
    print("\nHost shortcuts (writes config directly):")
    print("  hegelion-setup-mcp --host claude-desktop")
    print("  hegelion-setup-mcp --host cursor")
    print("  hegelion-setup-mcp --host vscode")
    print("  hegelion-setup-mcp --host windsurf")
    print("\n⚠️  Restart Required: Restart your MCP host after modifying the config.")

    if not is_installed:
        print(f"\nNOTE: Detected source installation at {project_root}")
        print("Added PYTHONPATH to ensure the server runs correctly.")
    else:
        print("\nNOTE: Detected installed package.")


def _write_config(target: Path, snippet: dict) -> None:
    target = target.expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        existing = {}
        try:
            existing = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        merged = existing.get("mcpServers", {})
        merged.update(snippet)
        payload = {"mcpServers": merged, **{k: v for k, v in existing.items() if k != "mcpServers"}}
    else:
        payload = {"mcpServers": snippet}
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote MCP config to {target}")


def main(argv=None):  # pragma: no cover - lightweight CLI
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate MCP config for Hegelion", epilog=USAGE_NOTE
    )
    parser.add_argument(
        "--host",
        help=f"Write to a host's default config path ({', '.join(KNOWN_HOSTS)})",
    )
    parser.add_argument(
        "--write",
        nargs="?",
        const="mcp_config.json",
        help="Write to path (default: mcp_config.json in CWD)",
    )
    parser.add_argument(
        "--llm-command",
        help="Set HEGELION_LLM_COMMAND for the MCP server (used when execute=true)",
    )
    parser.add_argument(
        "--llm-command-json",
        help="Set HEGELION_LLM_COMMAND_JSON for the MCP server (preferred; used when execute=true)",
    )
    parser.add_argument(
        "--auto-execute",
        action="store_true",
        help="Set HEGELION_MCP_AUTO_EXECUTE=1 so dialectical_single_shot executes by default",
    )
    args = parser.parse_args(argv)

    if args.host and args.write:
        parser.error("Use either --host or --write, not both.")
    if args.llm_command and args.llm_command_json:
        parser.error("Use either --llm-command or --llm-command-json, not both.")

    python_path = get_python_path()
    is_installed = is_installed_in_site_packages()
    project_root = get_project_root()
    config = generate_config(
        python_path,
        project_root,
        is_installed,
        llm_command=args.llm_command,
        llm_command_json=args.llm_command_json,
        auto_execute=args.auto_execute,
    )
    snippet = config["mcpServers"]

    if args.host:
        try:
            target = resolve_host_path(args.host)
        except ValueError as exc:
            parser.error(str(exc))
        _write_config(target, snippet)
    elif args.write:
        _write_config(Path(args.write), snippet)
    else:
        print_setup_instructions(
            llm_command=args.llm_command,
            llm_command_json=args.llm_command_json,
            auto_execute=args.auto_execute,
        )


if __name__ == "__main__":
    main()
