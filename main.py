"""
main.py
Flask 應用 + APScheduler 輪詢。
所有狀態存在 _state dict，單 worker 運行。
"""
import threading, logging
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from apscheduler.schedulers.background import BackgroundScheduler

import config, game_detector, play_parser, notifier

log = logging.getLogger(__name__)
app = Flask(__name__)

# ── 全域狀態 ────────────────────────────────────────────
_lock = threading.Lock()
_state = {
    "game":         None,     # 最新 game dict
    "seen":         set(),    # 已推事件 id
    "log":          [],       # 最近 30 筆推播記錄
    "total":        0,
    "last_push":    None,
    "last_poll":    None,
    "errors":       [],
    "paused":       False,    # 是否暫停推播
}

def _add_log(text: str):
    with _lock:
        _state["log"].insert(0, {
            "text": text[:120],
            "at": datetime.utcnow().strftime("%H:%M:%S"),
        })
        _state["log"] = _state["log"][:30]
        _state["total"] += 1
        _state["last_push"] = datetime.utcnow().strftime("%H:%M:%S UTC")

# ── 輪詢主邏輯 ──────────────────────────────────────────
_scheduler = BackgroundScheduler(job_defaults={"coalesce": True, "max_instances": 1})
_JOB = "poll"


def tick():
    try:
        _tick()
    except Exception as e:
        log.exception("tick error: %s", e)
        with _lock:
            _state["errors"].insert(0, str(e))
            _state["errors"] = _state["errors"][:10]


def _tick():
    with _lock:
        _state["last_poll"] = datetime.utcnow().strftime("%H:%M:%S UTC")
        paused = _state["paused"]

    game = game_detector.get_game()
    with _lock:
        _state["game"] = game

    if game is None:
        _set_interval(config.POLL_NO_GAME)
        return

    if game["status"] == "PRE":
        _set_interval(config.POLL_PRE)
        return

    if game["status"] == "FINAL":
        _set_interval(config.POLL_NO_GAME)
        if paused:
            return
        # 終場只通知一次
        fid = f"{game['game_id']}_final"
        with _lock:
            already = fid in _state["seen"]
        if not already:
            hs, aws = game["home_score"], game["away_score"]
            text = f"🏁 終場！{game['away']} {aws} - {hs} {game['home']}"
            if notifier.push(text):
                with _lock:
                    _state["seen"].add(fid)
                _add_log(text)
        return

    # LIVE
    _set_interval(config.POLL_LIVE)
    events = play_parser.fetch_events(game)

    if paused:
        # 暫停期間仍標記事件為已見，避免恢復後一次補推大量舊事件
        with _lock:
            for evt in events:
                _state["seen"].add(evt["id"])
        return

    for evt in events:
        with _lock:
            already = evt["id"] in _state["seen"]
        if already:
            continue
        # 只推有意義的事件類型
        if evt["type"] not in ("2pt","3pt","freethrow","foul","timeout","period","game"):
            with _lock:
                _state["seen"].add(evt["id"])
            continue
        if notifier.push(evt["text"]):
            with _lock:
                _state["seen"].add(evt["id"])
            _add_log(evt["text"])


def _set_interval(secs: int):
    try:
        job = _scheduler.get_job(_JOB)
        if job:
            from apscheduler.triggers.interval import IntervalTrigger
            _scheduler.reschedule_job(_JOB, trigger=IntervalTrigger(seconds=secs))
    except Exception:
        pass


# ── Flask 路由 ──────────────────────────────────────────
@app.route("/")
@app.route("/dashboard")
def dashboard():
    with _lock:
        s = dict(_state)
        s["log"] = list(_state["log"])
        s["errors"] = list(_state["errors"])
    return render_template("dashboard.html", **s)


@app.route("/health")
def health():
    return jsonify({"ok": True})


@app.route("/test-line", methods=["POST"])
def test_line():
    ok = notifier.push("🏀 NBA 監控測試推播 — 系統正常！(Telegram)")
    return jsonify({"ok": ok})


@app.route("/toggle-pause", methods=["POST"])
def toggle_pause():
    with _lock:
        _state["paused"] = not _state["paused"]
        paused = _state["paused"]
    return jsonify({"ok": True, "paused": paused})


@app.route("/simulate", methods=["POST"])
def simulate():
    text = (request.get_json(silent=True) or {}).get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "msg": "請提供 text"}), 400
    ok = notifier.push(f"[模擬] {text}")
    return jsonify({"ok": ok})


# ── 啟動 ────────────────────────────────────────────────
def _start():
    from apscheduler.triggers.interval import IntervalTrigger
    _scheduler.add_job(tick, IntervalTrigger(seconds=config.POLL_NO_GAME), id=_JOB)
    _scheduler.start()
    log.info("排程器啟動，初始間隔 %ds", config.POLL_NO_GAME)


if __name__ == "__main__":
    _start()
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
else:
    _once = threading.Lock()
    with _once:
        _start()
