import os
import requests
import pandas as pd
from datetime import datetime

# הדפסה ראשונית כדי לוודא שהקובץ בכלל רץ
print("--- STARTING TIDE BOT DIAGNOSTICS ---")

# הגדרות
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

print(f"Token exists: {bool(TELEGRAM_TOKEN)}")
print(f"Chat ID exists: {bool(CHAT_ID)}")
print(f"Chat ID Value: {CHAT_ID}") # זה ידפיס את ה-ID בלוג כדי שנבדוק אותו

# קואורדינטות טונג סאלה
LAT = 9.7126
LON = 99.9912

def get_tides():
    print("Step 1: Fetching data from Open-Meteo...")
    # שימוש בנקודה ימית עמוקה יותר כדי למנוע שגיאות
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude=9.75&longitude=99.98&hourly=wave_height&timezone=Asia%2FBangkok"
    
    try:
        response = requests.get(url)
        print(f"API Status Code: {response.status_code}")
        
        if response.status_code != 200:
            print(f"API Error: {response.text}")
            return None, None
            
        data = response.json()
        if 'hourly' not in data:
            print("No 'hourly' data found in response.")
            return None, None

        # עיבוד נתונים
        hourly = data['hourly']
        df = pd.DataFrame({
            'time': hourly['time'],
            'height': hourly['wave_height']
        })
        
        # לקיחת נתון ראשון לעתיד
        df['time'] = pd.to_datetime(df['time'])
        now = datetime.now()
        future = df[df['time'] > now]
        
        if future.empty:
            print("No future data found.")
            return None, None
            
        # מציאת המינימום
        min_row = future.loc[future['height'].idxmin()]
        print(f"Data found: Time={min_row['time']}, Height={min_row['height']}")
        return min_row['time'], min_row['height']

    except Exception as e:
        print(f"CRITICAL ERROR in get_tides: {e}")
        return None, None

def send_telegram(message):
    print("Step 2: Sending to Telegram...")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload)
        print(f"--- TELEGRAM RESPONSE ---")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
        print(f"-------------------------")
    except Exception as e:
        print(f"Error sending telegram: {e}")

def main():
    print("Entering Main Loop...")
    time, height = get_tides()
    
    if time:
        time_str = time.strftime("%H:%M")
        msg = f"🧪 **בדיקת מערכת**\nנמצאו נתונים!\nשעה: {time_str}\nגובה גלים: {height:.2f}m"
        send_telegram(msg)
    else:
        print("No data returned, attempting to send error log to Telegram...")
        send_telegram("⚠️ בדיקה: הבוט רץ אבל לא הצליח למשוך נתונים.")

if __name__ == "__main__":
    main()
