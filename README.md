# autopilot plugin

Mechanical turn chaining for Feishu without changing the Hermes source repo.

## What it does

- Watches for a user message requesting autopilot turns, including exact `autopilot N` and natural variants like `autopilot 3轮`, `3轮 autopilot`, `我们对这本书进行3轮autopilot`
- Arms a per-session counter with `N` future turns
- After each completed turn, sends one follow-up message to the current Feishu chat via `lark-cli`
- Decrements the counter until it reaches zero
- `autopilot stop` / `autopilot off` / `autopilot cancel` disables it

## Important behavior

- The control message itself does **not** consume one autopilot turn
- A new normal user message automatically takes back control and clears autopilot for that session
- Only intended for Feishu sessions (`HERMES_SESSION_PLATFORM=feishu`)
- No Hermes source code changes required; this is a user plugin under `~/.hermes/plugins/autopilot/`

## Default send path

Uses:

```bash
lark-cli im +messages-send --chat-id <current_chat_id> --text <continue_message> --as user
```

## Optional env vars

- `HERMES_AUTOPILOT_LARK_CLI` — override lark-cli path
- `HERMES_AUTOPILOT_LARK_PROFILE` — pass a specific lark-cli profile
- `HERMES_AUTOPILOT_LARK_AS` — override sender identity (`user` by default; Feishu gateway drops bot-originated inbound events)

## Activation

Restart Hermes/gateway so the plugin is discovered.

## Repository layout

```
hermes-autopilot-plugin/
├── __init__.py
├── plugin.yaml
├── README.md
└── .gitignore
```

## Installation

Copy this directory into your Hermes plugins directory:

```bash
mkdir -p ~/.hermes/plugins/autopilot
cp __init__.py plugin.yaml README.md ~/.hermes/plugins/autopilot/
```

Then restart Hermes or the gateway so the plugin is reloaded.
