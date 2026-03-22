"""CLI entry point for file-event-hub."""

import argparse
import json
import sys
from pathlib import Path


def _cmd_serve(args: argparse.Namespace) -> None:
    """Start the file-event-hub server."""
    import uvicorn

    uvicorn.run(
        "file_event_hub.server:app",
        host=args.host,
        port=args.port,
    )


def _cmd_install_hook(_args: argparse.Namespace) -> None:
    """Install the Claude Code PostToolUse hook."""
    settings_path = Path.home() / ".claude" / "settings.json"

    # Read existing settings or start fresh
    if settings_path.exists():
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    else:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings = {}

    # Resolve hook script path from package directory
    hook_script = Path(__file__).resolve().parent / "hook" / "post_tool_use.sh"

    hook_entry = {
        "matcher": "Edit|Write",
        "hooks": [
            {
                "type": "command",
                "command": str(hook_script),
            }
        ],
    }

    # Ensure hooks.PostToolUse exists
    if "hooks" not in settings:
        settings["hooks"] = {}
    if "PostToolUse" not in settings["hooks"]:
        settings["hooks"]["PostToolUse"] = []

    post_tool_use = settings["hooks"]["PostToolUse"]

    # Update existing entry or add new one
    updated = False
    for i, entry in enumerate(post_tool_use):
        if entry.get("matcher") == "Edit|Write":
            post_tool_use[i] = hook_entry
            updated = True
            break

    if not updated:
        post_tool_use.append(hook_entry)

    # Write back
    settings_path.write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Hook installed successfully.")
    print(f"  Settings: {settings_path}")
    print(f"  Script:   {hook_script}")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="file-event-hub",
        description="A decoupled file change event bus for AI coding assistants",
    )
    subparsers = parser.add_subparsers(dest="command")

    # serve
    serve_parser = subparsers.add_parser("serve", help="Start the event hub server")
    serve_parser.add_argument(
        "--port", type=int, default=9120, help="Port to listen on (default: 9120)"
    )
    serve_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )

    # install-hook
    subparsers.add_parser(
        "install-hook", help="Install Claude Code PostToolUse hook"
    )

    args = parser.parse_args()

    if args.command == "serve":
        _cmd_serve(args)
    elif args.command == "install-hook":
        _cmd_install_hook(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
