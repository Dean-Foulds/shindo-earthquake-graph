"""
Server-side localisation.

The frontend sends `Accept-Language: en` or `ja` on every request. Error details
are the only prose the API returns directly, so they are translated here rather
than mapped back to strings in the client — the client would have to pattern-match
on English text to know which message it received.

`instruction()` is separate: it tells the language models which language to answer
in, and is injected into the prompt rather than returned to the caller.
"""

from typing import Optional

from fastapi import Request

DEFAULT = "en"
SUPPORTED = ("en", "ja")


def lang_of(request: Optional[Request]) -> str:
    """First supported tag in Accept-Language, else English."""
    if request is None:
        return DEFAULT
    for part in request.headers.get("accept-language", "").split(","):
        tag = part.split(";")[0].strip().lower()
        if tag.startswith("ja"):
            return "ja"
        if tag.startswith("en"):
            return "en"
    return DEFAULT


MESSAGES: dict[str, dict[str, str]] = {
    # ── auth ─────────────────────────────────────────────────────
    "auth.signin_required": {
        "en": "Sign in to run a simulation",
        "ja": "シミュレーションを実行するにはログインしてください",
    },
    "auth.session_expired": {
        "en": "Session expired — sign in again",
        "ja": "セッションの有効期限が切れました。再度ログインしてください",
    },
    "auth.invalid_session": {
        "en": "Invalid session",
        "ja": "セッションが無効です",
    },
    "auth.account_gone": {
        "en": "Account no longer exists",
        "ja": "アカウントが存在しません",
    },
    "auth.invalid_email": {
        "en": "Enter a valid email address",
        "ja": "有効なメールアドレスを入力してください",
    },
    "auth.email_taken": {
        "en": "An account with that email already exists",
        "ja": "そのメールアドレスのアカウントは既に登録されています",
    },
    "auth.bad_credentials": {
        "en": "Email or password is incorrect",
        "ja": "メールアドレスまたはパスワードが正しくありません",
    },
    "auth.quota_reached": {
        "en": "Simulation limit reached ({quota} per 30 days). Resets {resets}.",
        "ja": "シミュレーションの上限に達しました（30日あたり{quota}回）。{resets}にリセットされます。",
    },
    # ── simulation ───────────────────────────────────────────────
    "sim.unavailable": {
        "en": "Simulation is unavailable — ANTHROPIC_API_KEY is not set",
        "ja": "シミュレーションを利用できません — ANTHROPIC_API_KEY が設定されていません",
    },
    "sim.rate_limited": {
        "en": "Model is rate limited — try again shortly",
        "ja": "モデルがレート制限中です。しばらくしてから再試行してください",
    },
    "sim.unreachable": {
        "en": "Could not reach the model API",
        "ja": "モデルAPIに接続できませんでした",
    },
    "sim.api_error": {
        "en": "Model API error ({status})",
        "ja": "モデルAPIエラー ({status})",
    },
    "sim.refused": {
        "en": "The model declined to analyse this scenario",
        "ja": "モデルはこのシナリオの解析を拒否しました",
    },
    "sim.truncated": {
        "en": "Model response was truncated",
        "ja": "モデルの応答が途中で打ち切られました",
    },
    "sim.unparseable": {
        "en": "Model returned unparseable output",
        "ja": "モデルの出力を解析できませんでした",
    },
    # ── graph / agent ────────────────────────────────────────────
    "graph.risk_unavailable": {
        "en": "Risk analysis is unavailable — the seismic graph could not be "
              "reached ({error}). Recent events on the map are unaffected.",
        "ja": "リスク解析を利用できません — 地震グラフに接続できませんでした ({error})。"
              "地図上の最近の地震には影響ありません。",
    },
    "agent.not_configured": {
        "en": "AURA_AGENT_URL not set",
        "ja": "AURA_AGENT_URL が設定されていません",
    },
    "agent.oauth_failed": {
        "en": "Aura OAuth failed",
        "ja": "Aura の認証に失敗しました",
    },
    "agent.error": {
        "en": "Aura agent error ({status})",
        "ja": "Aura エージェントのエラー ({status})",
    },
}


def msg(lang: str, key: str, **params) -> str:
    entry = MESSAGES.get(key, {})
    text = entry.get(lang) or entry.get(DEFAULT) or key
    return text.format(**params) if params else text


# ── model prompt instructions ────────────────────────────────────

_CHAT_INSTRUCTION = {
    "ja": "[LANGUAGE] 必ず日本語で回答してください。地名・断層名・施設名も日本語で表記し、"
          "見出しや箇条書きも日本語にしてください。\n",
    "en": "[LANGUAGE] Respond in English.\n",
}

# The analysis response is validated against a JSON schema whose enums are English
# identifiers, so those have to be excluded by name or the model translates them
# and the response fails validation.
_ANALYSIS_INSTRUCTION = {
    "ja": "Write every free-text field in Japanese: fault_zone, each cascade_chain entry, "
          "affected_prefectures[].name, nuclear_risk[].name, historical_analogs[].name "
          "and insight. Leave all id values, the shindo scale string, and the "
          "severity / fault_type / risk enum values exactly as the English "
          "identifiers given above — those are not prose.",
    "en": "",
}


def chat_instruction(lang: str) -> str:
    return _CHAT_INSTRUCTION.get(lang, _CHAT_INSTRUCTION["en"])


def analysis_instruction(lang: str) -> str:
    return _ANALYSIS_INSTRUCTION.get(lang, "")
