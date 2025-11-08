import requests
import time
import threading
import random
from collections import defaultdict

# -------------------- تنظیمات --------------------
API_URL = "https://api.binance.com/api/v3/klines"
TELEGRAM_BOT_TOKEN = "1465024519:AAHAFHFhW1jJwwnlTrB3iWaoOe5sM5hulHc"  # توکن ربات تلگرام شما
TELEGRAM_CHAT_ID = "901845453"  # چت‌آیدی شما

TIMEFRAME = "1m"  # تایم‌فریم کندل‌ها
CANDLE_SIZE = 14  # تعداد کندل‌های مورد نیاز برای محاسبه
VOLUME_MULTIPLIER = 5  # ضریب افزایش حجم برای هشدار
ATR_MULTIPLIER = 5  # ضریب افزایش ATR برای هشدار
DELAY_BETWEEN_REQUESTS = 0.1  # تاخیر بین درخواست‌ها (برای جلوگیری از Rate Limit)
MAX_MARKETS = 100  # تعداد ارزهای اصلی برای بررسی
SUMMARY_INTERVAL = 600  # هر ۱۰ دقیقه یک بار پیام خلاصه ارسال شود (بر حسب ثانیه)

# -------------------- سیستم لاگ --------------------
log_lock = threading.Lock()
def log(message):
    with log_lock:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

# -------------------- فقط ۱۰۰ ارز اصلی --------------------
def get_top_markets(limit=MAX_MARKETS):
    main_markets = [
        "BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","ADAUSDT","AVAXUSDT","TRXUSDT","TONUSDT",
        "LINKUSDT","DOTUSDT","MATICUSDT","UNIUSDT","LTCUSDT","BCHUSDT","NEARUSDT","ICPUSDT","APTUSDT","XLMUSDT",
        "INJUSDT","FILUSDT","ARBUSDT","OPUSDT","VETUSDT","SUIUSDT","ATOMUSDT","AAVEUSDT","MKRUSDT","ONDOUSDT",
        "EGLDUSDT","GRTUSDT","QNTUSDT","IMXUSDT","FLOWUSDT","FTMUSDT","THETAUSDT","SANDUSDT","MANAUSDT","WLDUSDT",
        "LDOUSDT","CRVUSDT","AXSUSDT","CHZUSDT","KAVAUSDT","STXUSDT","SNXUSDT","MINAUSDT","COMPUSDT","AEROUSDT",
        "DYDXUSDT","CAKEUSDT","ALGOUSDT","GALAUSDT","TWTUSDT","ZILUSDT","KSMUSDT","CFXUSDT","1INCHUSDT","SUSDT",
        "BATUSDT","ENJUSDT","HOTUSDT","RAYUSDT","MUSDT","2ZUSDT","CROUSDT","HEXUSDT","OKBUSDT","FTNUSDT","NEXOUSDT",
        "DASHUSDT","TIAUSDT","RENDERUSDT","PAXGUSDT","SPXUSDT","XDCUSDT","POLUSDT","MNTUSDT","XPLUSDT","WLFIUSDT",
        "JASMYUSDT","BDXUSDT","BGBUSDT","SEIUSDT","XAUTUSDT","KASUSDT","FLRUSDT","MORPHOUSDT","TAOUSDT","PENGUUSDT",
        "COAIUSDT","GRTUSDT","BONKUSDT","FLOKIUSDT","PUMPUSDT","PYTHUSDT","SFPUSDT","HBARUSDT","ZECUSDT","XMRUSDT",
        "HYPEUSDT","KAIAUSDT"
    ]
    return main_markets[:limit]

# -------------------- توابع اصلی --------------------
def get_candles(market):
    try:
        time.sleep(random.uniform(0.1, 0.3))
        params = {"symbol": market, "interval": TIMEFRAME, "limit": CANDLE_SIZE + 1}
        response = requests.get(API_URL, params=params, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def calculate_atr(candles):
    try:
        tr_values = [
            max(
                float(c[2]) - float(c[3]),
                abs(float(c[2]) - float(prev_c[4])),
                abs(float(c[3]) - float(prev_c[4]))
            )
            for prev_c, c in zip(candles, candles[1:])
        ]
        return sum(tr_values) / len(tr_values) if tr_values else 0
    except:
        return 0

def send_alert(market, data):
    try:
        message = (
            f"🚨 هشدار {market} ({TIMEFRAME})\n"
            f"📊 ATR: {int(data['atr_ratio'])}\n"
            f"📈 VOL: {int(data['volume_ratio'])}"
        )
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML"
            },
            timeout=10
        )
        with summary_lock:
            global alert_count
            alert_count += 1
            market_stats[market]["volume"] = data["volume_ratio"]
            market_stats[market]["atr"] = data["atr_ratio"]
    except Exception as e:
        log(f"❗خطا در ارسال هشدار برای {market}: {str(e)}")

# -------------------- کلاس مانیتورینگ --------------------
class MarketMonitor:
    def __init__(self, market):
        self.market = market
        self.last_check = 0
        self.interval = 60

    def check(self):
        try:
            now = time.time()
            if now - self.last_check >= self.interval:
                self.last_check = now
                candles = get_candles(self.market)
                if not candles or len(candles) < CANDLE_SIZE + 1:
                    return
                atr_14 = calculate_atr(candles[:-1])
                last_candle = candles[-1]
                high = float(last_candle[2])
                low = float(last_candle[3])
                close = float(last_candle[4])
                volume = float(last_candle[5])
                avg_volume = sum(float(c[5]) for c in candles[-CANDLE_SIZE - 1:-1]) / CANDLE_SIZE
                if (high - low > ATR_MULTIPLIER * atr_14 and volume > VOLUME_MULTIPLIER * avg_volume):
                    send_alert(self.market, {
                        "price": close,
                        "atr_ratio": (high - low) / atr_14,
                        "volume_ratio": volume / avg_volume
                    })
        except Exception as e:
            log(f"خطا در {self.market}: {str(e)}")

# -------------------- سیستم خلاصه‌سازی --------------------
summary_lock = threading.Lock()
alert_count = 0
market_stats = defaultdict(lambda: {"volume": 0, "atr": 0})

def send_summary():
    global alert_count, market_stats
    while True:
        time.sleep(SUMMARY_INTERVAL)
        with summary_lock:
            if alert_count == 0:
                message = "📊 خلاصه ۱۰ دقیقه اخیر:\n⚠️ هیچ هشداری ارسال نشده است."
            else:
                top_volume_market = max(market_stats.items(), key=lambda x: x[1]["volume"])[0]
                top_atr_market = max(market_stats.items(), key=lambda x: x[1]["atr"])[0]
                message = (
                    f"📊 خلاصه ۱۰ دقیقه اخیر:\n"
                    f"🔔 تعداد هشدارها: {alert_count}\n"
                    f"📈 بیشترین حجم: {top_volume_market} ({int(market_stats[top_volume_market]['volume'])})\n"
                    f"📉 بیشترین نوسان: {top_atr_market} ({int(market_stats[top_atr_market]['atr'])})"
                )
            try:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                    data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
                    timeout=10
                )
            except:
                pass
            alert_count = 0
            market_stats.clear()

# -------------------- اجرای اصلی --------------------
def main():
    markets = get_top_markets(limit=MAX_MARKETS)
    if not markets:
        log("❗هیچ بازاری یافت نشد")
        return
    log(f"شروع مانیتورینگ {len(markets)} بازار")
    monitors = [MarketMonitor(m) for m in markets]
    threading.Thread(target=send_summary, daemon=True).start()
    while True:
        try:
            for monitor in monitors:
                threading.Thread(target=monitor.check).start()
                time.sleep(DELAY_BETWEEN_REQUESTS)
            time.sleep(1)
        except Exception as e:
            log(f"خطای سیستمی: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()
