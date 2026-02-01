import os
import requests
from datetime import datetime, timedelta, timezone

# הגדרות
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WORLDTIDES_KEY = os.getenv('WORLDTIDES_KEY')

# קואורדינטות טונג סאלה
LAT = 9.7126
LON = 99.9912

# --- הגדרת שעון תאילנד (UTC+7) ---
THAI_OFFSET = timedelta(hours=7)

def get_thai_now():
    """מחזיר את הזמן הנוכחי בתאילנד"""
    return datetime.utcnow() + THAI_OFFSET

def to_thai_time(timestamp):
    """ממיר חותמת זמן (Unix) לשעון תאילנד"""
    return datetime.utcfromtimestamp(timestamp) + THAI_OFFSET

def get_tide_data():
    # שים לב: אנחנו מבקשים נתונים ליומיים קדימה כדי לכסות את המעבר בין ימים
    url = f"https://www.worldtides.info/api/v3?extremes&heights&step=3600&days=2&lat={LAT}&lon={LON}&key={WORLDTIDES_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if 'error' in data:
            print(f"API Error: {data['error']}")
            return None, None

        if 'extremes' not in data or 'heights' not in data:
            return None, None
            
        # 1. מציאת השיא (השפל הכי נמוך שעדיין לא קרה)
        now_thai = get_thai_now()
        # אנחנו מסננים לפי ה-Timestamp (שהוא אוניברסלי)
        now_ts = datetime.utcnow().timestamp()
        
        lows = [e for e in data['extremes'] if e['type'] == 'Low' and e['dt'] > now_ts]
        
        best_low = None
        if lows:
            # לוקחים את הראשון ברשימה
            best_low = lows[0]
            # ממירים את הזמן שלו לשעון תאילנד
            best_low['time'] = to_thai_time(best_low['dt'])

        # 2. מציאת גובה המים בבוקר (08:00 שעון תאילנד)
        morning_tide = None
        target_hour = 8
        
        # אם מריצים את הבוט בערב (אחרי 20:00), אולי נרצה לראות את הבוקר של מחר?
        # כרגע נשאיר את זה פשוט: הבוקר של "היום הנוכחי בתאילנד"
        today_date_thai = now_thai.strftime('%Y-%m-%d')
        
        for h in data['heights']:
            dt_thai = to_thai_time(h['dt'])
            
            # בדיקה: האם זה הבוקר של היום?
            if dt_thai.strftime('%Y-%m-%d') == today_date_thai and dt_thai.hour == target_hour:
                morning_tide = {'time': dt_thai, 'height': h['height']}
                break
        
        # גיבוי: אם לא מצאנו את 08:00 (אולי עכשיו כבר צהריים?), ניקח את המצב *עכשיו*
        if not morning_tide and data['heights']:
             # מוצאים את המדידה הכי קרובה לזמן הנוכחי
             closest = min(data['heights'], key=lambda x: abs(to_thai_time(x['dt']) - now_thai))
             morning_tide = {'time': to_thai_time(closest['dt']), 'height': closest['height']}

        return best_low, morning_tide

    except Exception as e:
        print(f"Error: {e}")
        return None, None

def get_weather(target_time):
    # ב-Open Meteo אנחנו מבקשים timezone=Asia/Bangkok ולכן הנתונים כבר בתאילנד
    # אבל צריך להיזהר עם ההשוואה
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=Asia%2FBangkok"
    try:
        data = requests.get(url).json()
        hourly = data['hourly']
        
        # המרת הזמן לפורמט שה-API מחזיר (ISO ללא timezone offset כי ביקשנו בנגקוק)
        target_str = target_time.strftime('%Y-%m-%dT%H:00')
        
        if target_str in hourly['time']:
            index = hourly['time'].index(target_str)
            return hourly['temperature_2m'][index], hourly['relative_humidity_2m'][index], hourly['wind_speed_10m'][index]
        return "N/A", "N/A", "N/A"
    except:
        return "N/A", "N/A", "N/A"

def get_morning_vibe(height):
    if height < 0.4: return "✨ **בוקר מושלם!** המים נמוכים ממש, אפשר לצאת להליכה כבר עכשיו."
    elif height < 0.7: return "☕ **בוקר טוב.** המים קצת עמוקים להליכה מלאה, אבל מתאים לטיול רטוב."
    else: return "🌊 **בוקר כחול.** הים גבוה עכשיו, עדיף לחכות לאחר הצהריים להליכה."

def get_beach_details(height):
    report = ""
    # Ko Tae Nai
    if height < 0.3: s1 = "השביל פתוח לגמרי, תענוג של הליכה 🏝️"
    elif height < 0.6: s1 = "השביל עביר, אבל תתכוננו להירטב עד הברכיים 🌊"
    else: s1 = "השביל מכוסה מים, עדיף לשחות או לחתור 🛶"
    report += f"<b>השביל לאי (Ko Tae Nai):</b>\n{s1}\n"
    
    # Ao Bang Charu
    if height < 0.8: s2 = "רצועת חוף רחבה ונוחה, מעולה לריצה 🏃"
    elif height < 1.2: s2 = "יש רצועת חול, אבל היא צרה ורטובה 👣"
    else: s2 = "המים מגיעים עד החומה, אין איפה ללכת כרגע 🚫"
    report += f"<b>חוף באנג צ'ארו:</b>\n{s2}"
    return report

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, json=payload)

def main():
    best_low, morning_tide = get_tide_data()
    
    if best_low:
        peak_time = best_low['time'] # זה כבר בשעון תאילנד
        peak_height = best_low['height']
        temp, humidity, wind = get_weather(peak_time)
        beach_report = get_beach_details(peak_height)
        
        morning_msg = ""
        if morning_tide:
            m_time_obj = morning_tide['time']
            # לוגיקה: אם השעה בין 06:00 ל-10:00 בבוקר
            if 6 <= m_time_obj.hour <= 10:
                morning_msg = get_morning_vibe(morning_tide['height'])
            else:
                # אם אנחנו כבר לא בבוקר (כמו עכשיו), נציג את המצב הנוכחי
                morning_msg = f"⏱️ **המצב כרגע ({m_time_obj.strftime('%H:%M')}):** גובה {morning_tide['height']:.2f}m"

        date_str = peak_time.strftime("%d/%m")
        
        msg = (
            f"🥥 <b>יומן גאות - קופנגן</b> | {date_str}\n"
            f"────────────────\n\n"
            f"{morning_msg}\n\n"
            f"📉 <b>מתי הכי כדאי לצאת?</b>\n"
            f"השפל יגיע לשיא בשעה <b>{peak_time.strftime('%H:%M')}</b>.\n"
            f"(גובה המים: {peak_height:.2f}m)\n\n"
            f"🌤️ <b>מה בחוץ?</b>\n"
            f"יהיה נעים ({temp}°C) עם רוח של {wind} קמ\"ש.\n\n"
            f"🏝️ <b>מצב המסלולים בשיא השפל:</b>\n"
            f"{beach_report}\n\n"
            f"יום מקסים! 😎"
        )
        send_telegram(msg)
    else:
        print("No Data found")

if __name__ == "__main__":
    main()
