import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# הגדרות
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# קואורדינטות טונג סאלה (Thong Sala Pier area)
LAT = 9.7126
LON = 99.9912

def get_tides():
    # שליפת נתונים מ-Open Meteo (Marine API)
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&hourly=tide_height&timezone=Asia%2FBangkok"
    
    try:
        response = requests.get(url).json()
        
        # המרת הנתונים ל-DataFrame
        hourly = response['hourly']
        df = pd.DataFrame({
            'time': hourly['time'],
            'height': hourly['tide_height']
        })
        
        # סינון להיום ומחר (כדי למצוא את השפל הקרוב ב-24 שעות)
        now = datetime.now()
        # המרה לפורמט של ה-API
        df['time'] = pd.to_datetime(df['time'])
        
        # לוקחים רק זמנים מעכשיו והלאה (עד סוף היום)
        future_tides = df[df['time'] > now]
        # לוקחים את 12 השעות הקרובות
        next_12_hours = future_tides.head(12)
        
        # מציאת המינימום (השפל)
        min_row = next_12_hours.loc[next_12_hours['height'].idxmin()]
        
        return min_row['time'], min_row['height']
        
    except Exception as e:
        print(f"Error fetching tides: {e}")
        return None, None

def interpret_walkability(height):
    # כאן בעתיד נכניס את ה"זיכרון" והלמידה
    # בינתיים זו הערכה גסה
    if height < 0.2:
        return "🏝️ **מצב הליכה: מושלם!**\nהמים נמוכים מאוד. סנדבר (Sandbar) חשוף לגמרי."
    elif height < 0.6:
        return "✅ **מצב הליכה: אפשרי**\nהמים בערך בגובה הברכיים/מותניים. אפשר ללכת רחוק."
    elif height < 1.0:
        return "⚠️ **מצב הליכה: גבולי**\nרק לשחייה או הליכה קצרה במים עמוקים."
    else:
        return "🌊 **מצב הליכה: בלתי אפשרי**\nגאות גבוהה."

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    print("Checking tides for Thong Sala...")
    time, height = get_tides()
    
    if time:
        # עיצוב השעה לתצוגה יפה
        time_str = time.strftime("%H:%M")
        date_str = time.strftime("%d/%m")
        
        walk_status = interpret_walkability(height)
        
        msg = (
            f"🌊 **עדכון שפל - טונג סאלה** 🌊\n"
            f"📅 תאריך: {date_str}\n"
            f"📉 שפל נמוך בשעה: **{time_str}**\n"
            f"📏 גובה המים: **{height:.2f} מטר**\n\n"
            f"{walk_status}\n\n"
            f"Join us: @thongsala_tides"
        )
        
        print(msg)
        send_telegram(msg)
    else:
        print("Failed to get tide data.")

if __name__ == "__main__":
    main()
