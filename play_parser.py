"""
解析 NBA play-by-play，回傳新事件 list。
每個事件是一個 dict，保證有 id / type / text 三個欄位。
"""
import logging, requests

import config

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}

# 事件類型對應 emoji
_EMOJI = {
    "2pt":          "🏀",
    "3pt":          "🎯",
    "freethrow":    "⚡",
    "foul":         "🚨",
    "timeout":      "⏸",
    "substitution": "🔄",
    "period":       "🔔",
    "game":         "🏁",
}

_PERIOD = {1:"Q1", 2:"Q2", 3:"Q3", 4:"Q4", 5:"OT", 6:"2OT"}


def _clock(raw: str) -> str:
    if raw and raw.startswith("PT"):
        try:
            raw = raw[2:]
            m, s = raw.split("M")
            return f"{int(m)}:{int(float(s.replace('S',''))):02d}"
        except Exception:
            pass
    return raw or ""


def _safe_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _score_str(action: dict, game: dict) -> str:
    hs = _safe_int(action.get("scoreHome"), game["home_score"])
    aws = _safe_int(action.get("scoreAway"), game["away_score"])
    return f"{game['away']} {aws} - {hs} {game['home']}"


def _format(action: dict, game: dict) -> str:
    atype  = (action.get("actionType") or "").lower()
    emoji  = _EMOJI.get(atype, "•")
    period = _PERIOD.get(int(action.get("period", 0)), "")
    clock  = _clock(action.get("clock") or action.get("gameClock") or "")
    player = action.get("playerNameI") or action.get("playerName") or ""
    team   = action.get("teamTricode") or ""
    desc   = action.get("description") or ""
    score  = _score_str(action, game)

    # 終場 / 節末
    if atype == "game":
        return f"🏁 終場！{score}"
    if atype == "period":
        p = int(action.get("period", 0))
        if p == 2 and "half" in desc.lower():
            return f"🏟 中場休息\n{score}"
        return f"🔔 {period} 結束\n{score}"

    # 一般事件
    header = f"{emoji} [{period} {clock}]"
    t_label = "馬刺" if team == config.TEAM_ABBR else team

    if atype == "3pt":
        return f"{header}\n{t_label} {player} 三分命中！\n{score}"
    if atype == "2pt":
        shot = "灌籃" if "dunk" in desc.lower() else "上籃" if "layup" in desc.lower() else "得分"
        return f"{header}\n{t_label} {player} {shot}\n{score}"
    if atype == "freethrow":
        return f"{header}\n{t_label} {player} 罰球\n{score}"
    if atype == "foul":
        return f"{header}\n{t_label} {player} 犯規"
    if atype == "timeout":
        return f"{header}\n{t_label} 暫停\n{score}"
    if atype == "substitution":
        return f"{header}\n{t_label} 換人：{player}"

    return f"{header}\n{desc}"


def fetch_events(game: dict) -> list[dict]:
    """
    抓 play-by-play，回傳事件 list。
    每個事件：{id, type, text, period, is_score}
    """
    url = f"https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{game['game_id']}.json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        actions = r.json().get("game", {}).get("actions", [])
    except Exception as e:
        log.warning("fetch_events 失敗：%s", e)
        return []

    events = []
    for a in actions:
        eid = str(a.get("actionNumber") or a.get("orderNumber") or "")
        if not eid:
            continue
        atype = (a.get("actionType") or "").lower()
        is_score = atype in ("2pt", "3pt", "freethrow")
        events.append({
            "id":       f"{game['game_id']}_{eid}",
            "type":     atype,
            "text":     _format(a, game),
            "period":   int(a.get("period", 0)),
            "is_score": is_score,
        })

    return events
