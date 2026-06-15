"""Telegram push，失敗只記 log，不拋例外。"""
import logging, requests
import config

log = logging.getLogger(__name__)


def push(text: str) -> bool:
    if not config.TG_TOKEN or not config.TG_CHAT_ID:
        log.warning("Telegram 設定不完整，略過推播")
        return False
    url = f"https://api.telegram.org/bot{config.TG_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url,
            json={
                "chat_id": config.TG_CHAT_ID,
                "text": text,
            },
            timeout=10,
        )
        if r.status_code == 200:
            log.info("Telegram push 成功：%s", text[:50].replace("\n", " "))
            return True
        log.warning("Telegram push 失敗 %d：%s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        log.warning("Telegram push 例外：%s", e)
        return False
