"""LINE push，失敗只記 log，不拋例外。"""
import logging, requests
import config

log = logging.getLogger(__name__)

_URL = "https://api.line.me/v2/bot/message/push"


def push(text: str) -> bool:
    if not config.LINE_TOKEN or not config.LINE_TO:
        log.warning("LINE 設定不完整，略過推播")
        return False
    try:
        r = requests.post(
            _URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.LINE_TOKEN}",
            },
            json={
                "to": config.LINE_TO,
                "messages": [{"type": "text", "text": text}],
            },
            timeout=10,
        )
        if r.status_code == 200:
            log.info("LINE push 成功：%s", text[:50].replace("\n", " "))
            return True
        log.warning("LINE push 失敗 %d：%s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        log.warning("LINE push 例外：%s", e)
        return False
