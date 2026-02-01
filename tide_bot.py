import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# הגדרות
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# קואורדינטות הים ליד טונג סאלה
LAT_SEA = 9.75  
LON_SEA = 99.98 

def get_sea_status():
    # שליפת נתונים מ-Open Meteo
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_SEA}&longitude={LON_SEA}&hourly=wave_height&timezone=Asia%2FBangkok"
    
    try:
        response = requests.get(url).json()
        hourly = response['hourly']
        
        # יצירת טבלה
        df = pd.DataFrame({
            'time': hourly['time'],
            'height': hourly['wave_height']
        })
        df['time'] = pd.to_datetime(df['time'])
        
        # סינון: רק זמנים מעכשיו ועד סוף היום
        now = datetime.now()
        end_of_day = now.replace(hour=23, minute=59, second=59)
        today_data = df[(df['time'] >= now) & (df['time'] <= end_of_day)]
        
        if today_data.empty:
            return None, None
            
        # מציאת הרגע הכי שקט (הכי נמוך) היום
        min_row = today_data.loc[today_data['height'].idxmin()]
        
        return min_row['time'], min_row['height']
        
    except Exception as e:
        print(f"Error: {e}")
        return None, None

def interpret_conditions(height):
    # פרשנות פשוטה לגובה הגלים
    if height < 0.15:
        return "🏝️ **ים פלטה (Glassy)!**\nתנאים מושלמים. המים כנראה נמוכים מאוד ורגועים."
    elif height < 0.3:
        return "✅ **ים רגוע**\nתנאים טובים להליכה במים (Sandbar Walk)."
    elif height < 0.6:
        return "⚠️ **קצת גלי**\nהמים עשויים להיות עמוקים יותר."
    else:
        return "🌊 **ים סוער**\nלא מומלץ להליכה."

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    print("Running Tide Walker...")
    best_time, min_height = get_sea_status()
    
    if best_time:
        time_str = best_time.strftime("%H:%M")
        date_str = best_time.strftime("%d/%m")
        status = interpret_conditions(min_height)
        
        msg = (
            f"🌊 **עדכון טונג סאלה** | {date_str} 🌊\n\n"
            f"📉 השעה הכי רגועה היום: **{time_str}**\n"
            f"📏 גובה גלים: **{min_height:.2f}m**\n\n"
            f"{status}\n\n"
            f"Join: @thongsala_tides"
        )
        print(msg)
        send_telegram(msg)
    else:
        print("No data available.")

if __name__ == "__main__":
    main()
