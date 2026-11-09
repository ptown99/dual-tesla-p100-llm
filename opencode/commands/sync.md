---
description: Automatically sync the latest models, context windows, and MCP tools from the Homelab cluster
---

Fetch the latest dynamic configuration directly from the homelab cluster and reload OpenCode:

1. Run the following command in terminal to update the global OpenCode config:
   `powershell -Command "Invoke-RestMethod -Uri 'http://192.168.1.67:8001/opencode.json' -OutFile \"$env:USERPROFILE\.config\opencode\opencode.json\""`
2. Then trigger OpenCode to reload its configuration:
   `powershell -Command "$cli = \"$env:LOCALAPPDATA\Programs\ai.opencode.desktop\resources\opencode-cli.exe\"; if (Test-Path $cli) { & $cli reload } else { opencode reload }"`
3. Verify the models loaded:
   `powershell -Command "$cli = \"$env:LOCALAPPDATA\Programs\ai.opencode.desktop\resources\opencode-cli.exe\"; if (Test-Path $cli) { & $cli models } else { opencode models }"`
4. Summarize the synced models, their context limits (e.g. 256k for mae-qwen38-35b-256k, 128k for mae-qwen38-35b-moe), and active remote MCP servers to the user.
