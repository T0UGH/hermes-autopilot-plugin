from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

ARM_RE = re.compile(r"^\s*autopilot\s+(\d+)\s*$", re.IGNORECASE)
ARM_PATTERNS = [
    re.compile(r"^\s*autopilot\s+(\d+)\s*(?:轮|轮吧|轮了)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*(\d+)\s*轮\s*autopilot\s*$", re.IGNORECASE),
    re.compile(r"autopilot\s*(\d+)\s*轮?", re.IGNORECASE),
    re.compile(r"(\d+)\s*轮\s*autopilot", re.IGNORECASE),
]
STOP_RE = re.compile(r"^\s*autopilot\s+(stop|off|cancel)\s*$", re.IGNORECASE)
CONTINUE_MARKER = "[AUTOPILOT_CONTINUE]"
STATE_DIR = get_hermes_home() / "autopilot"


def _state_path(session_id: str) -> Path:
    return STATE_DIR / f"{session_id}.json"


def _load_state(session_id: str) -> Optional[Dict[str, Any]]:
    path = _state_path(session_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("autopilot: failed reading state %s: %s", path, exc)
        return None


def _save_state(session_id: str, data: Dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    _state_path(session_id).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _clear_state(session_id: str) -> None:
    try:
        _state_path(session_id).unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("autopilot: failed clearing state for %s: %s", session_id, exc)



def _platform() -> str:
    return (os.getenv("HERMES_SESSION_PLATFORM") or "").strip().lower()



def _chat_id() -> str:
    return (os.getenv("HERMES_SESSION_CHAT_ID") or "").strip()



def _thread_id() -> str:
    return (os.getenv("HERMES_SESSION_THREAD_ID") or "").strip()



def _lark_cli() -> str:
    return os.getenv("HERMES_AUTOPILOT_LARK_CLI", "lark-cli")



def _build_continue_text(remaining_after_this_turn: int) -> str:
    return (
        f"{CONTINUE_MARKER}\n"
        "继续自动推进当前任务一轮。"
        "除非你被明确阻塞，否则不要停下来征求是否继续。"
        f"本轮之后剩余自动轮数：{remaining_after_this_turn}。"
    )



def _send_to_current_feishu_channel(text: str, chat_id: str) -> bool:
    cmd = [_lark_cli(), "im", "+messages-send", "--chat-id", chat_id, "--text", text]
    profile = (os.getenv("HERMES_AUTOPILOT_LARK_PROFILE") or "").strip()
    if profile:
        cmd.extend(["--profile", profile])
    sender = (os.getenv("HERMES_AUTOPILOT_LARK_AS") or "user").strip()
    if sender:
        cmd.extend(["--as", sender])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        logger.warning("autopilot: lark-cli send failed: %s", exc)
        return False

    if result.returncode != 0:
        logger.warning(
            "autopilot: lark-cli send returned %s; stdout=%s stderr=%s",
            result.returncode,
            result.stdout[-500:],
            result.stderr[-500:],
        )
        return False
    return True



def _arm_autopilot(session_id: str, turns: int) -> None:
    _save_state(
        session_id,
        {
            "remaining": int(turns),
            "platform": _platform(),
            "chat_id": _chat_id(),
            "thread_id": _thread_id(),
            "armed_at": time.time(),
        },
    )


def _extract_arm_turns(message: str) -> Optional[int]:
    text = (message or "").strip()
    for pattern in ARM_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        try:
            turns = int(m.group(1))
        except Exception:
            continue
        if turns > 0:
            return turns
    return None



def _pre_llm_call(
    session_id: str,
    user_message: str,
    conversation_history=None,
    is_first_turn: bool = False,
    model: str = "",
    platform: str = "",
) -> Optional[Dict[str, str]]:
    message = (user_message or "").strip()
    state = _load_state(session_id)

    stop_match = STOP_RE.match(message)
    if stop_match:
        _clear_state(session_id)
        return {
            "context": "[Autopilot control] 机械续跑已关闭。请只做简短确认，不要继续自动续轮。"
        }

    turns = _extract_arm_turns(message)
    if turns is not None:
        logger.info("autopilot: armed for session %s with %s turns from message=%r", session_id, turns, message)
        _arm_autopilot(session_id, turns)
        return {
            "context": (
                f"[Autopilot control] 用户刚刚开启机械续跑，共 {turns} 轮。"
                "这一条控制消息本身不计入自动轮次。"
                "请只做简短确认：说明已进入 autopilot 模式，并将自动继续，不要继续追问是否要往下做。"
            )
        }

    if message.startswith(CONTINUE_MARKER):
        if state:
            remaining = int(state.get("remaining", 0))
            return {
                "context": (
                    f"[Autopilot control] 这是机械续跑触发的一轮。"
                    f"当前在 autopilot 模式中，剩余轮数（含未来轮）约为 {remaining}。"
                    "请直接沿当前任务继续推进一轮；除非被明确阻塞，不要停下来征求是否继续。"
                )
            }
        return None

    # Real user intervention takes back control.
    if state:
        _clear_state(session_id)
        return {
            "context": "[Autopilot control] 用户发送了新的普通消息，机械续跑已自动让位给人工输入。请按用户这条新消息正常处理。"
        }

    return None



def _on_session_end(
    session_id: str,
    completed: bool = False,
    interrupted: bool = False,
    model: str = "",
    platform: str = "",
) -> None:
    state = _load_state(session_id)
    if not state:
        return

    if interrupted or not completed:
        logger.info("autopilot: stopping for session %s because completed=%s interrupted=%s", session_id, completed, interrupted)
        _clear_state(session_id)
        return

    remaining = int(state.get("remaining", 0))
    if remaining <= 0:
        _clear_state(session_id)
        return

    current_platform = _platform() or (platform or "").lower()
    chat_id = _chat_id() or str(state.get("chat_id", "")).strip()
    if current_platform != "feishu" or not chat_id:
        logger.warning(
            "autopilot: session %s has unsupported platform/chat context platform=%s chat_id=%s; stopping",
            session_id,
            current_platform,
            bool(chat_id),
        )
        _clear_state(session_id)
        return

    remaining_after_send = remaining - 1
    text = _build_continue_text(remaining_after_send)
    ok = _send_to_current_feishu_channel(text, chat_id)
    if not ok:
        return

    if remaining_after_send <= 0:
        _clear_state(session_id)
    else:
        state["remaining"] = remaining_after_send
        state["last_sent_at"] = time.time()
        _save_state(session_id, state)



def _on_session_boundary(session_id: Optional[str] = None, **kwargs: Any) -> None:
    if session_id:
        _clear_state(session_id)



def register(ctx) -> None:
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_hook("on_session_finalize", _on_session_boundary)
    ctx.register_hook("on_session_reset", _on_session_boundary)
