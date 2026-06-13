"""找今日目標球隊比賽，回傳比賽資訊 dict 或 None。"""
import logging, requests

import config

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}
SCOREBOARD_URL = (
    "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
)


def get_game():
    """
    回傳 dict：
      game_id, status ("PRE"/"LIVE"/"FINAL"),
      home, away, home_score, away_score, period, clock
    或 None（今日無賽事 / 網路失敗）。
    """
    try:
        r = requests.get(SCOREBOARD_URL, headers=HEADERS, timeout=10)
        r.raise_for_status()
        games = r.json().get("scoreboard", {}).get("games", [])
    except Exception as e:
        log.warning("get_game 失敗：%s", e)
        return None

    for g in games:
        home = g.get("homeTeam", {})
        away = g.get("awayTeam", {})
        if config.TEAM_ABBR not in (home.get("teamTricode"), away.get("teamTricode")):
            continue

        status_text = g.get("gameStatusText", "")
        period      = int(g.get("period", 0))

        if "final" in status_text.lower():
            status = "FINAL"
        elif period > 0:
            status = "LIVE"
        else:
            status = "PRE"

        return {
            "game_id":    str(g.get("gameId", "")),
            "status":     status,
            "home":       home.get("teamTricode", ""),
            "away":       away.get("teamTricode", ""),
            "home_score": int(home.get("score", 0) or 0),
            "away_score": int(away.get("score", 0) or 0),
            "period":     period,
            "clock":      g.get("gameClock", ""),
            "arena":      g.get("arena", {}).get("arenaName", ""),
        }

    log.info("今日無 %s 賽事", config.TEAM_ABBR)
    return None
