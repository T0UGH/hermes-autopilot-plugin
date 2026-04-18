# Hermes Autopilot Plugin

A small Hermes user plugin that adds **mechanical turn chaining** for Feishu sessions.

It lets you say things like `autopilot 3`, then Hermes keeps pushing the current task forward for a few more turns by sending follow-up messages back into the same Feishu chat via `lark-cli`.

## What it does

- Detects explicit commands like `autopilot 3`
- Also accepts natural variants such as:
  - `autopilot 3轮`
  - `3轮 autopilot`
  - `我们对这本书进行3轮autopilot`
- Arms a per-session counter with `N` future turns
- After each completed turn, sends one continuation message to the current Feishu chat
- Decrements the counter until it reaches zero
- Supports stopping with:
  - `autopilot stop`
  - `autopilot off`
  - `autopilot cancel`

## Important behavior

- The control message itself does **not** consume one autopilot turn
- A new normal user message automatically takes back control and clears autopilot for that session
- Designed for **Feishu** sessions only (`HERMES_SESSION_PLATFORM=feishu`)
- No Hermes source repo changes are required
- Plugin state is stored under `~/.hermes/autopilot/`

## How it works

The plugin hooks into Hermes session lifecycle events:

- `pre_llm_call`
  - detects `autopilot N`
  - detects stop commands
  - clears autopilot if a real user message takes over
- `on_session_end`
  - if the turn completed successfully and autopilot is still armed, sends the next continuation message
- `on_session_finalize` / `on_session_reset`
  - clears session state

The continuation message is sent through `lark-cli` to the **current Feishu chat**.

## Default send path

```bash
lark-cli im +messages-send --chat-id <current_chat_id> --text <continue_message> --as user
```

Default continuation message:

```text
[AUTOPILOT_CONTINUE]
继续自动推进当前任务一轮。除非你被明确阻塞，否则不要停下来征求是否继续。
本轮之后剩余自动轮数：N。
```

## Requirements

- Hermes with user plugin support
- Feishu session context available to Hermes
- `lark-cli` installed and usable in the current environment
- A working Feishu send path with `--as user` if you want the gateway to treat the message as a user-originated follow-up

## Installation

Copy this repository into your Hermes plugins directory as `autopilot`:

```bash
mkdir -p ~/.hermes/plugins/autopilot
cp __init__.py plugin.yaml README.md ~/.hermes/plugins/autopilot/
```

Then restart Hermes or the gateway so the plugin is discovered.

## Usage

### Start autopilot

```text
autopilot 3
```

Hermes should briefly confirm that autopilot mode is enabled, then continue for the next 3 turns unless interrupted.

### Natural-language variants

```text
autopilot 3轮
3轮 autopilot
我们对这本书进行3轮autopilot
```

### Stop autopilot

```text
autopilot stop
```

Also supported:

```text
autopilot off
autopilot cancel
```

## Environment variables

Optional overrides:

- `HERMES_AUTOPILOT_LARK_CLI` — override the `lark-cli` executable path
- `HERMES_AUTOPILOT_LARK_PROFILE` — pass a specific `lark-cli` profile
- `HERMES_AUTOPILOT_LARK_AS` — override sender identity (`user` by default)

## Repository layout

```text
hermes-autopilot-plugin/
├── __init__.py
├── plugin.yaml
├── README.md
└── .gitignore
```

## Troubleshooting

### Autopilot does not continue

Check the likely causes first:

- session platform is not `feishu`
- current session has no valid `chat_id`
- `lark-cli` is not installed or not in `PATH`
- `lark-cli` send failed
- the Hermes turn did not complete successfully

### A normal user message should stop autopilot

That is expected behavior. The plugin intentionally gives control back to the user as soon as a fresh normal message arrives.

### State gets stuck

You can clear the per-session state files under:

```bash
~/.hermes/autopilot/
```

## License

MIT
