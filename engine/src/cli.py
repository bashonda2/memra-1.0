"""
Memra CLI — entry point for pip install memra.

Commands:
  memra serve     Start the MCP server (stdio, for Cursor/Claude Code)
  memra server    Start the HTTP API server (localhost:8000)
  memra setup     Auto-configure Cursor to use Memra
  memra status    Show profile stats and data directory
"""
import json
import os
import sys


def _find_cursor_mcp_config() -> str:
    candidates = [
        os.path.join(os.getcwd(), ".cursor", "mcp.json"),
        os.path.join(os.path.expanduser("~"), ".cursor", "mcp.json"),
    ]
    for path in candidates:
        if os.path.exists(os.path.dirname(path)):
            return path
    return candidates[0]


def cmd_setup():
    print()
    print("  Memra Setup")
    print("  ───────────")
    print()

    mcp_path = _find_cursor_mcp_config()
    memra_python = sys.executable
    engine_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    memra_config = {
        "command": memra_python,
        "args": ["-m", "src.mcp_server"],
        "cwd": engine_dir,
    }

    if os.path.exists(mcp_path):
        with open(mcp_path) as f:
            config = json.load(f)
    else:
        os.makedirs(os.path.dirname(mcp_path), exist_ok=True)
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["memra"] = memra_config

    with open(mcp_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"  Wrote MCP config to: {mcp_path}")
    print(f"  Python: {memra_python}")
    print(f"  Engine: {engine_dir}")
    print()
    print("  Restart Cursor. Memra will be available as MCP tools.")
    print()


def cmd_serve():
    from src.mcp_server import mcp
    mcp.run()


def cmd_server():
    import uvicorn
    uvicorn.run("src.server:app", host="127.0.0.1", port=8000)


def cmd_status():
    data_dir = os.environ.get("MEMRA_DATA_DIR", os.path.join(os.path.expanduser("~"), ".memra"))
    profile_path = os.path.join(data_dir, "profile", "profile.json")

    print()
    print("  Memra Status")
    print("  ────────────")
    print(f"  Data directory: {data_dir}")
    print(f"  Exists: {os.path.exists(data_dir)}")

    if os.path.exists(profile_path):
        with open(profile_path) as f:
            profile = json.load(f)
        print(f"  Profile facts: {len(profile.get('facts', []))}")
        print(f"  Last updated: {profile.get('last_updated', 'never')}")
    else:
        print("  Profile: not created yet")

    transcript_dir = os.path.join(data_dir, "transcripts")
    if os.path.exists(transcript_dir):
        sessions = [f for f in os.listdir(transcript_dir) if f.endswith(".jsonl")]
        print(f"  Sessions: {len(sessions)}")
    else:
        print("  Sessions: 0")

    print()


def main():
    if len(sys.argv) < 2:
        print("Usage: memra <command>")
        print("Commands: serve, server, setup, status")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "serve":
        cmd_serve()
    elif cmd == "server":
        cmd_server()
    elif cmd == "setup":
        cmd_setup()
    elif cmd == "status":
        cmd_status()
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: serve, server, setup, status")
        sys.exit(1)


if __name__ == "__main__":
    main()
