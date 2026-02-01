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
    """שליפת נתוני שפל מ-WorldTides"""
    url = f"https://www.worldtides.info/api/v3?extremes&days=2&lat={LAT}&lon={LON}&key={WORLDTIDES_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        if 'extremes' not in data: return None
        
        # סינון לשפל (Low) עתידי בלבד
        now_ts = datetime.now().timestamp()
        lows = [e for e in data['extremes'] if e['type'] == 'Low' and e['dt'] > now_ts]
        
        if not lows: return None
        
        # לוקחים את השפל הקרוב ביותר
        best_low = lows[0]
        return datetime.fromtimestamp(best_low['dt']), best_low['height']
    except Exception as e:
        print(f"Tide Error: {e}")
        return None

def get_weather_at_time(target_time):
    """
    שליפת מזג אוויר מ-Open-Meteo עבור שעה ספציפית
    אנחנו מבקשים תחזית שעתית ומחפשים את השעה הכי קרובה לשפל
    """
    # מבקשים טמפרטורה, לחות ומהירות רוח
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=Asia%2FBangkok"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        hourly = data['hourly']
        times = hourly['time']
        
        # המרת השעה שקיבלנו לפורמט של ה-API (כדי למצוא את ההתאמה)
        # ה-API מחזיר זמנים בפורמט ISO, למשל: "2026-02-02T14:00"
        target_str = target_time.strftime('%Y-%m-%dT%H:00')
        
        # חיפוש האינדקס של השעה הרצויה (או הקרובה ביותר)
        try:
            index = times.index(target_str)
        except ValueError:
            # אם השעה המדויקת לא נמצאת (למשל 14:30), לוקחים את השעה העגולה הקרובה
            # זה פתרון פשוט: לוקחים את האינדקס הראשון שגדול מהזמן הנוכחי אם לא מוצאים בול
            return "לא זמין", "לא זמין", "לא זמין"

        temp = hourly['temperature_2m'][index]
        humidity = hourly['relative_humidity_2m'][index]
        wind = hourly['wind_speed_10m'][index]
        
        return temp, humidity, wind
        
    except Exception as e:
        print(f"Weather Error: {e}")
        return "N/A", "N/A", "N/A"

def get_beach_status(height):
    report = ""
    # Ko Tae Nai Sandbar
    if height < 0.3: status_sandbar = "✅ <b>פתוח לגמרי</b> (חול יבש)"
    elif height < 0.6: status_sandbar = "⚠️ <b>עביר במים</b> (גובה ברכיים)"
    else: status_sandbar = "❌ <b>סגור</b> (שחייה בלבד)"
    report += f"🏝️ <b>Ko Tae Nai Sandbar:</b>\n{status_sandbar}\n"

    # Ao Bang Charu
    if height < 0.8: status_charu = "✅ <b>רחב ונוח</b> (הליכה/ריצה)"
    elif height < 1.2: status_charu = "⚠️ <b>רצועה צרה</b> (חול רטוב)"
    else: status_charu = "❌ <b>אין חוף</b>"
    report += f"🏖️ <b>Ao Bang Charu:</b>\n{status_charu}"
    return report

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def main():
    print("Fetching full report...")
    tide_result = get_tide_data()
    
    if tide_result:
        tide_time, height = tide_result
        
        # שליפת מזג האוויר לאותה שעה בדיוק
        temp, humidity, wind = get_weather_at_time(tide_time)
        
        time_str = tide_time.strftime("%H:%M")
        date_str = tide_time.strftime("%d/%m")
        beach_report = get_beach_status(height)
        
        msg = (
            f"🚶 <b>תחזית הליכה מלאה</b> | {date_str}\n"
            f"──────────────────\n"
            f"📉 שיא השפל: <b>{time_str}</b>\n"
            f"📏 גובה המים: <b>{height:.2f}m</b>\n"
            f"──────────────────\n"
            f"🌤️ <b>מזג אוויר לשעת ההליכה:</b>\n"
            f"🌡️ טמפרטורה: <b>{temp}°C</b>\n"
            f"💨 רוח: <b>{wind} קמ\"ש</b>\n"
            f"💧 לחות: <b>{humidity}%</b>\n"
            f"──────────────────\n"
            f"{beach_report}\n\n"
            f"תהנה בטיול! 🥥"
        )
        send_telegram(msg)
        print("Report sent successfully.")
    else:
        print("No tide data found.")

if __name__ == "__main__":
    main()
