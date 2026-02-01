import os
import requests
from datetime import datetime

# הגדרות
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WORLDTIDES_KEY = os.getenv('WORLDTIDES_KEY')

# קואורדינטות טונג סאלה
LAT = 9.7126
LON = 99.9912

def get_tide_data():
    """שליפת נתונים משולבת עם טווח ביטחון של יומיים"""
    # הרחבתי ל-days=2 כדי לא לפספס שפל אם אנחנו בסוף היום
    url = f"https://www.worldtides.info/api/v3?extremes&heights&step=3600&days=2&lat={LAT}&lon={LON}&key={WORLDTIDES_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # בדיקת שגיאות מה-API
        if 'error' in data:
            print(f"WorldTides API Error: {data['error']}")
            return None, None
            
        if 'extremes' not in data or 'heights' not in data:
            print(f"Missing data in response. Keys found: {data.keys()}")
            return None, None
            
        # 1. מציאת השיא (הכי נמוך עתידי)
        now_ts = datetime.now().timestamp()
        lows = [e for e in data['extremes'] if e['type'] == 'Low' and e['dt'] > now_ts]
        
        best_low = None
        if lows:
            best_low = lows[0]
            best_low['time'] = datetime.fromtimestamp(best_low['dt'])
        else:
            print("No future low tide found in the next 48 hours.")

        # 2. מציאת גובה המים בבוקר (08:00)
        morning_tide = None
        target_hour = 8 
        today_date = datetime.now().strftime('%Y-%m-%d')
        
        for h in data['heights']:
            dt_object = datetime.fromtimestamp(h['dt'])
            if dt_object.strftime('%Y-%m-%d') == today_date and dt_object.hour == target_hour:
                morning_tide = {'time': dt_object, 'height': h['height']}
                break
        
        # גיבוי: אם לא מצאנו את 08:00 (אולי כבר צהריים?), ניקח את המדידה הכי קרובה לעכשיו
        if not morning_tide and data['heights']:
             # מחפשים את המדידה הקרובה ביותר לזמן הנוכחי
             current_time = datetime.now()
             closest_height = min(data['heights'], key=lambda x: abs(datetime.fromtimestamp(x['dt']) - current_time))
             morning_tide = {'time': datetime.fromtimestamp(closest_height['dt']), 'height': closest_height['height']}

        return best_low, morning_tide

    except Exception as e:
        print(f"Critical Error in get_tide_data: {e}")
        return None, None

def get_weather(target_time):
    # מזג אוויר
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=Asia%2FBangkok"
    try:
        data = requests.get(url).json()
        hourly = data['hourly']
        target_str = target_time.strftime('%Y-%m-%dT%H:00')
        
        if target_str in hourly['time']:
            index = hourly['time'].index(target_str)
            return hourly['temperature_2m'][index], hourly['relative_humidity_2m'][index], hourly['wind_speed_10m'][index]
        return "N/A", "N/A", "N/A"
    except Exception as e:
        print(f"Weather Error: {e}")
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
    try:
        response = requests.post(url, json=payload)
        print(f"Telegram status: {response.status_code}")
    except Exception as e:
        print(f"Telegram Connection Error: {e}")

def main():
    print("Starting Tide Bot - Island Vibes Edition V2...")
    best_low, morning_tide = get_tide_data()
    
    if best_low:
        peak_time = best_low['time']
        peak_height = best_low['height']
        temp, humidity, wind = get_weather(peak_time)
        beach_report = get_beach_details(peak_height)
        
        morning_msg = ""
        if morning_tide:
            # אם השעה שמצאנו היא בבוקר, נשתמש בהודעת הבוקר. אחרת, נציין שזה המצב הנוכחי.
            m_time_obj = morning_tide['time']
            if 6 <= m_time_obj.hour <= 10:
                morning_msg = get_morning_vibe(morning_tide['height'])
            else:
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
        print("Still No Data. Check logs above for specific error.")

if __name__ == "__main__":
    main()
