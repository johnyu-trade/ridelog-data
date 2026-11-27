"""保底版預報：AI 正式版沒發布時，App 改讀 fallback.json。
只放天氣（Open-Meteo 數值），不放任何熱區。"""
import json, urllib.request, datetime, sys
TZ = datetime.timezone(datetime.timedelta(hours=8))
now = datetime.datetime.now(TZ)
today = now.date().isoformat()
wd = now.weekday()  # 0=Mon

def om(lat, lon):
    u = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
         "&hourly=precipitation_probability,temperature_2m&timezone=Asia%%2FTaipei&forecast_days=1") % (lat, lon)
    import time, subprocess
    last = None
    for i in range(4):
        try:
            with urllib.request.urlopen(u, timeout=40) as r:
                h = json.load(r)["hourly"]
            break
        except Exception as e:
            last = e
            try:  # 改用 curl 再試
                h = json.loads(subprocess.check_output(["curl", "-sS", "--retry", "2", "-m", "40", u]))["hourly"]
                break
            except Exception as e2:
                last = e2
            time.sleep(10 * (i + 1))
    else:
        raise last
    return h["time"], h["precipitation_probability"], h["temperature_2m"]

weather = None
try:
    t1, p1, c1 = om(25.04, 121.56)   # 臺北市
    t2, p2, c2 = om(25.01, 121.46)   # 新北市（板橋）
    def mx(ps, ts, a, b):
        v = [p for p, t in zip(ps, ts) if a <= int(t[11:13]) < b and p is not None]
        return max(v) if v else None
    slots = []
    for name, a, b in (("白天", 6, 18), ("晚上", 18, 24)):
        tp, nt = mx(p1, t1, a, b), mx(p2, t2, a, b)
        if tp is not None and nt is not None:
            slots.append({"t": name, "tp": int(tp), "nt": int(nt)})
    temps = [c for c in c1 if c is not None]
    rmax = max([s["tp"] for s in slots] + [s["nt"] for s in slots] + [0])
    rain = "可能下雨" if rmax >= 60 else ("偶有零星雨" if rmax >= 30 else "降雨機會低")
    weather = {"text": "雙北%s，%d–%d 度" % (rain, round(min(temps)), round(max(temps))),
               "rain": rain, "temp": "%d–%d°" % (round(min(temps)), round(max(temps))),
               "slots": slots, "demand": "下雨時短程需求通常增加" if rmax >= 60 else "需求主要看通勤時段",
               "conf": "估（數值模式）", "src": "Open-Meteo 數值預報（保底版）"}
except Exception as e:
    print("weather failed:", e, file=sys.stderr)

peaks = []  # 規則 R4：保底版只放天氣，不放任何沒有公開來源的熱區

try:
    venues = json.load(open("forecast.json", encoding="utf-8")).get("venues", [])
except Exception:
    venues = []
out = {"version": 1, "kind": "fallback", "date": today, "generated": now.isoformat(timespec="seconds"),
       "status": "fallback", "status_note": "今日熱區預報尚未發布，只顯示天氣",
       "weather": weather, "peaks": peaks, "upcoming": [], "venues": venues}
if weather is None:
    del out["weather"]
json.dump(out, open("fallback.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fallback.json", today, "weather" if weather else "no-weather", len(peaks), "peaks")
