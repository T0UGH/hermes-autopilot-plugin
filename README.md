# Hermes Autopilot Plugin

A small Hermes user plugin that adds **mechanical turn chaining** for Feishu sessions.

一个给 Hermes 用的轻量插件，用来给飞书会话增加 **autopilot 机械续跑** 能力。

It lets you say things like `autopilot 3`, then Hermes keeps pushing the current task forward for a few more turns by sending follow-up messages back into the same Feishu chat via `lark-cli`.

你可以直接说 `autopilot 3`，随后 Hermes 会通过 `lark-cli` 向当前飞书会话继续发送跟进消息，把当前任务再自动推进几轮。

---

## English

### What it does

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

### Important behavior

- The control message itself does **not** consume one autopilot turn
- A new normal user message automatically takes back control and clears autopilot for that session
- Designed for **Feishu** sessions only (`HERMES_SESSION_PLATFORM=feishu`)
- No Hermes source repo changes are required
- Plugin state is stored under `~/.hermes/autopilot/`

### How it works

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

### Default send path

```bash
lark-cli im +messages-send --chat-id <current_chat_id> --text <continue_message>
```

Default continuation message:

```text
[AUTOPILOT_CONTINUE]
继续自动推进当前任务一轮。除非你被明确阻塞，否则不要停下来征求是否继续。
本轮之后剩余自动轮数：N。
```

### Requirements

- Hermes with user plugin support
- Feishu session context available to Hermes
- `lark-cli` installed and usable in the current environment
- A working Feishu send path. If you deliberately need user-originated follow-ups, set `HERMES_AUTOPILOT_LARK_AS=user` explicitly.

### Installation

Copy this repository into your Hermes plugins directory as `autopilot`:

```bash
mkdir -p ~/.hermes/plugins/autopilot
cp __init__.py plugin.yaml README.md ~/.hermes/plugins/autopilot/
```

Then restart Hermes or the gateway so the plugin is discovered.

### Usage

#### Start autopilot

```text
autopilot 3
```

Hermes should briefly confirm that autopilot mode is enabled, then continue for the next 3 turns unless interrupted.

#### Natural-language variants

```text
autopilot 3轮
3轮 autopilot
我们对这本书进行3轮autopilot
```

#### Stop autopilot

```text
autopilot stop
```

Also supported:

```text
autopilot off
autopilot cancel
```

### Environment variables

Optional overrides:

- `HERMES_AUTOPILOT_LARK_CLI` — override the `lark-cli` executable path
- `HERMES_AUTOPILOT_LARK_PROFILE` — pass a specific `lark-cli` profile
- `HERMES_AUTOPILOT_LARK_AS` — optional sender identity passed as `--as <value>`; unset by default

### Repository layout

```text
hermes-autopilot-plugin/
├── __init__.py
├── plugin.yaml
├── README.md
└── .gitignore
```

### Troubleshooting

#### Autopilot does not continue

Check the likely causes first:

- session platform is not `feishu`
- current session has no valid `chat_id`
- `lark-cli` is not installed or not in `PATH`
- `lark-cli` send failed
- the Hermes turn did not complete successfully

#### A normal user message should stop autopilot

That is expected behavior. The plugin intentionally gives control back to the user as soon as a fresh normal message arrives.

#### State gets stuck

You can clear the per-session state files under:

```bash
~/.hermes/autopilot/
```

---

## 中文说明

### 它是干什么的

- 识别显式命令，比如 `autopilot 3`
- 也支持更自然的说法，比如：
  - `autopilot 3轮`
  - `3轮 autopilot`
  - `我们对这本书进行3轮autopilot`
- 为当前 session 记录一个剩余轮数计数器
- 每轮成功结束后，自动向当前飞书会话发送一条续跑消息
- 每续跑一轮，计数减一，直到归零
- 支持以下关闭命令：
  - `autopilot stop`
  - `autopilot off`
  - `autopilot cancel`

### 关键行为

- 控制命令本身 **不消耗** 一轮 autopilot
- 只要用户发来一条新的普通消息，就会自动夺回控制权，并清掉当前 session 的 autopilot 状态
- 当前设计只面向 **飞书会话**（`HERMES_SESSION_PLATFORM=feishu`）
- 不需要改 Hermes 主仓源码
- 插件状态保存在 `~/.hermes/autopilot/`

### 工作原理

这个插件挂在 Hermes 的几个 session 生命周期 hook 上：

- `pre_llm_call`
  - 识别 `autopilot N`
  - 识别 stop/off/cancel
  - 如果用户发来新的普通消息，就自动取消 autopilot
- `on_session_end`
  - 如果这一轮成功完成，而且 autopilot 还在，就自动发送下一条续跑消息
- `on_session_finalize` / `on_session_reset`
  - 清理 session 状态

续跑消息通过 `lark-cli` 发送到**当前飞书会话**。

### 默认发送方式

```bash
lark-cli im +messages-send --chat-id <current_chat_id> --text <continue_message>
```

默认续跑消息内容：

```text
[AUTOPILOT_CONTINUE]
继续自动推进当前任务一轮。除非你被明确阻塞，否则不要停下来征求是否继续。
本轮之后剩余自动轮数：N。
```

### 依赖要求

- Hermes 已支持 user plugin
- 当前会话运行在 Feishu 上，并且 Hermes 能拿到会话上下文
- 当前环境里可用 `lark-cli`
- 如果你明确希望 gateway 把它当作用户跟进消息继续处理，需要显式设置 `HERMES_AUTOPILOT_LARK_AS=user`

### 安装方式

把这个仓库里的文件复制到 Hermes 插件目录，并命名为 `autopilot`：

```bash
mkdir -p ~/.hermes/plugins/autopilot
cp __init__.py plugin.yaml README.md ~/.hermes/plugins/autopilot/
```

然后重启 Hermes 或 gateway，让插件重新加载。

### 使用方法

#### 开启 autopilot

```text
autopilot 3
```

Hermes 一般会先做一个简短确认，然后继续自动推进接下来的 3 轮，除非中途被打断。

#### 自然语言变体

```text
autopilot 3轮
3轮 autopilot
我们对这本书进行3轮autopilot
```

#### 关闭 autopilot

```text
autopilot stop
```

也支持：

```text
autopilot off
autopilot cancel
```

### 环境变量

可选覆盖项：

- `HERMES_AUTOPILOT_LARK_CLI` — 自定义 `lark-cli` 可执行文件路径
- `HERMES_AUTOPILOT_LARK_PROFILE` — 指定 `lark-cli` profile
- `HERMES_AUTOPILOT_LARK_AS` — 可选发送身份，会透传为 `--as <value>`；默认不设置

### 仓库结构

```text
hermes-autopilot-plugin/
├── __init__.py
├── plugin.yaml
├── README.md
└── .gitignore
```

### 排查思路

#### autopilot 没有继续跑

先检查这几个常见原因：

- 当前 session 不是 `feishu`
- 当前 session 没有拿到有效 `chat_id`
- `lark-cli` 没装，或者不在 `PATH` 里
- `lark-cli` 发送失败
- 当前 Hermes 这一轮并没有正常完成

#### 用户一发新消息就停了

这是预期行为。这个插件故意把控制权优先让回给用户。

#### 状态卡住了

可以直接清理下面目录里的 session 状态文件：

```bash
~/.hermes/autopilot/
```

---

## License

MIT
