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

def get_tide_extremes():
    print("--- 1. בדיקת מפתח ---")
    if not WORLDTIDES_KEY:
        print("CRITICAL ERROR: WORLDTIDES_KEY is missing!")
        return None
    else:
        print(f"Key exists (Length: {len(WORLDTIDES_KEY)})")

    print("--- 2. פנייה ל-API ---")
    # הוספתי ימים=7 כדי להבטיח שנמצא שפל גם אם הוא רחוק
    url = f"https://www.worldtides.info/api/v3?extremes&days=2&lat={LAT}&lon={LON}&key={WORLDTIDES_KEY}"
    
    try:
        response = requests.get(url)
        print(f"HTTP Status: {response.status_code}")
        
        # הדפסת התשובה הגולמית - זה החלק הכי חשוב!
        print(f"RAW RESPONSE: {response.text}") 
        
        data = response.json()
        
        if 'extremes' not in data:
            print("Error: 'extremes' key missing in JSON.")
            return None
            
        extremes = data['extremes']
        print(f"Found {len(extremes)} data points.")
        
        # סינון: רק נקודות שפל (Low) עתידיות
        now_timestamp = datetime.now().timestamp()
        future_lows = [e for e in extremes if e['type'] == 'Low' and e['dt'] > now_timestamp]
        
        if not future_lows:
            print("No future low tides found in the next 48 hours.")
            return None
            
        # לקיחת השפל הקרוב ביותר
        next_low = future_lows[0]
        tide_time = datetime.fromtimestamp(next_low['dt'])
        height = next_low['height']
        
        return tide_time, height

    except Exception as e:
        print(f"EXCEPTION: {e}")
        return None

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
    print("--- 3. שליחה לטלגרם ---")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload)
        print(f"Telegram response: {resp.text}")
    except Exception as e:
        print(f"Telegram Error: {e}")

def main():
    print("Starting Diagnosis...")
    result = get_tide_extremes()
    
    if result:
        time, height = result
        time_str = time.strftime("%H:%M")
        date_str = time.strftime("%d/%m")
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
        send_telegram(msg)
    else:
        print("No tide data found (check RAW RESPONSE above).")

if __name__ == "__main__":
    main()
