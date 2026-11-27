"""保底版預報：AI 正式版沒發布時，App 改讀 fallback.json。
只放天氣（Open-Meteo）與一般通勤經驗規則，不寫任何活動、散場、交管。"""
import json, urllib.request, datetime, sys
TZ = datetime.timezone(datetime.timedelta(hours=8))
now = datetime.datetime.now(TZ)
today = now.date().isoformat()
wd = now.weekday()  # 0=Mon

def om(lat, lon):
    u = ("https://api.open-meteo.com/v1/forecast?latitude=%s&longitude=%s"
         "&hourly=precipitation_probability,temperature_2m&timezone=Asia%%2FTaipei&forecast_days=1") % (lat, lon)
    with urllib.request.urlopen(u, timeout=20) as r:
        h = json.load(r)["hourly"]
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

wet = bool(weather) and any(max(s["tp"], s["nt"]) >= 60 for s in weather["slots"])
P = lambda s, e, t, pl, ar, m, b, nav, why: {"start": s, "end": e, "title": t, "place": pl, "areas": ar, "main": m, "backup": b,
        "arrive_by": s, "nav": nav, "conf": "推測", "why": why}
peaks = []
if wd < 5:
    peaks.append(P("07:30", "09:30", "上班尖峰" + ("（雨）" if wet else ""), "住宅區→市區", ["三重", "新莊", "板橋", "中和", "永和"],
                   "住宅區往台北市區", "捷運站周邊短程", "台北車站", "平日通勤經驗規則"))
    peaks.append(P("17:00", "19:30", "下班尖峰" + ("（雨）" if wet else ""), "信義區", ["信義", "內湖", "中山"],
                   "信義區、內湖科技園區", "南京東路商圈", "台北101", "平日下班經驗規則"))
    if wd == 4:
        peaks.append(P("21:30", "01:00", "週五夜歸", "東區", ["大安", "信義", "中山"],
                       "東區、信義、林森北路", "台北車站", "忠孝敦化站", "週五聚餐夜歸經驗規則"))
else:
    peaks.append(P("11:00", "14:00", "假日商圈", "信義區", ["信義", "大安", "中正"],
                   "信義、東區、西門", "台北車站", "台北101", "假日出遊經驗規則"))
    peaks.append(P("21:00", "00:30", "假日夜歸", "東區", ["大安", "信義", "中山"],
                   "東區、信義、林森北路", "西門町", "忠孝敦化站", "假日夜歸經驗規則"))

try:
    venues = json.load(open("forecast.json", encoding="utf-8")).get("venues", [])
except Exception:
    venues = []
out = {"version": 1, "kind": "fallback", "date": today, "generated": now.isoformat(timespec="seconds"),
       "status": "fallback", "status_note": "保底版：只有天氣與一般尖峰，沒有活動資訊",
       "weather": weather, "peaks": peaks, "upcoming": [], "venues": venues}
if weather is None:
    del out["weather"]
json.dump(out, open("fallback.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("fallback.json", today, "weather" if weather else "no-weather", len(peaks), "peaks")
