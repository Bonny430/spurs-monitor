import os, logging

TG_TOKEN    = os.environ.get("TG_TOKEN", "")     # Telegram Bot Token
TG_CHAT_ID  = os.environ.get("TG_CHAT_ID", "")   # Telegram Chat ID
TEAM_ABBR   = os.environ.get("TEAM_ABBR", "SAS") # 追蹤球隊縮寫

POLL_LIVE    = int(os.environ.get("POLL_LIVE",    "8"))
POLL_PRE     = int(os.environ.get("POLL_PRE",     "60"))
POLL_NO_GAME = int(os.environ.get("POLL_NO_GAME", "300"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
