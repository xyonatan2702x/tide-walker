import os
import requests
from datetime import datetime

# הגדרות
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WORLDTIDES_KEY = os.getenv('WORLDTIDES_KEY')

# קואורדינטות טונג סאלה (מרכז)
LAT = 9.7126
LON = 99.9912

def get_tide_extremes():
    # WorldTides API
    url = f"https://www.worldtides.info/api/v3?extremes&lat={LAT}&lon={LON}&key={WORLDTIDES_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if 'extremes' not in data:
            return None
            
        extremes = data['extremes']
        # סינון: רק נקודות שפל (Low) עתידיות
        now_timestamp = datetime.now().timestamp()
        future_lows = [e for e in extremes if e['type'] == 'Low' and e['dt'] > now_timestamp]
        
        if not future_lows:
            return None
            
        # לקיחת השפל הקרוב ביותר
        next_low = future_lows[0]
        
        tide_time = datetime.fromtimestamp(next_low['dt'])
        height = next_low['height'] # גובה ביחס לממוצע (Datum)
        
        return tide_time, height

    except Exception as e:
        print(f"API Error: {e}")
        return None

def get_beach_status(height):
    """
    פונקציה שמתרגמת את גובה המים למצב ההליכה בחופים הספציפיים
    """
    report = ""
    
    # --- 1. Ko Tae Nai Sandbar (השביל לאי) ---
    if height < 0.3:
        status_sandbar = "✅ <b>פתוח לגמרי</b> (חול יבש)"
    elif height < 0.6:
        status_sandbar = "⚠️ <b>עביר במים</b> (גובה ברכיים)"
    else:
        status_sandbar = "❌ <b>סגור</b> (שחייה בלבד)"
        
    report += f"🏝️ <b>Ko Tae Nai Sandbar:</b>\n{status_sandbar}\n"

    # --- 2. Ao Bang Charu (החוף הארוך) ---
    if height < 0.8:
        status_charu = "✅ <b>רחב ונוח</b> (מעולה לריצה/הליכה)"
    elif height < 1.2:
        status_charu = "⚠️ <b>רצועה צרה</b> (חול רטוב)"
    else:
        status_charu = "❌ <b>אין חוף</b> (המים עד החומה/עצים)"
        
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
    print("Analyzing walking routes...")
    result = get_tide_extremes()
    
    if result:
        time, height = result
        time_str = time.strftime("%H:%M")
        date_str = time.strftime("%d/%m")
        
        # קבלת פירוט לפי חופים
        beach_report = get_beach_status(height)
        
        msg = (
            f"🚶 <b>תחזית הליכות - טונג סאלה</b> | {date_str}\n"
            f"──────────────────\n"
            f"📉 שפל שיא בשעה: <b>{time_str}</b>\n"
            f"📏 גובה מים: <b>{height:.2f}m</b>\n"
            f"──────────────────\n"
            f"{beach_report}\n\n"
            f"טיול נעים! 🥥"
        )
        print("Sending Report...")
        send_telegram(msg)
    else:
        print("No tide data found.")

if __name__ == "__main__":
    main()
