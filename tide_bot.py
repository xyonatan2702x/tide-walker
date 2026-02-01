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
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_SEA}&longitude={LON_SEA}&hourly=wave_height&timezone=Asia%2FBangkok"
    
    try:
        response = requests.get(url).json()
        if 'hourly' not in response:
            print("Error: No hourly data")
            return None, None

        hourly = response['hourly']
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
        return "🏝️ <b>ים פלטה (Glassy)!</b>\nתנאים מושלמים. המים כנראה נמוכים מאוד ורגועים."
    elif height < 0.3:
        return "✅ <b>ים רגוע</b>\nתנאים טובים להליכה במים (Sandbar Walk)."
    elif height < 0.6:
        return "⚠️ <b>קצת גלי</b>\nהמים עשויים להיות עמוקים יותר."
    else:
        return "🌊 <b>ים סוער</b>\nלא מומלץ להליכה."

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    # שינוי חשוב: עוברים ל-HTML שהוא יותר יציב
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    
    try:
        response = requests.post(url, json=payload)
        # הדפסת התשובה כדי שנראה אם יש שגיאה
        print(f"Telegram Response: {response.text}")
    except Exception as e:
        print(f"Connection Error: {e}")

def main():
    print("Running Tide Walker...")
    best_time, min_height = get_sea_status()
    
    if best_time:
        time_str = best_time.strftime("%H:%M")
        date_str = best_time.strftime("%d/%m")
        status = interpret_conditions(min_height)
        
        # בניית ההודעה ב-HTML (שימוש ב-<b> להדגשה)
        msg = (
            f"🌊 <b>עדכון טונג סאלה</b> | {date_str} 🌊\n\n"
            f"📉 השעה הכי רגועה היום: <b>{time_str}</b>\n"
            f"📏 גובה גלים: <b>{min_height:.2f}m</b>\n\n"
            f"{status}\n\n"
            f"Join: @thongsala_tides"
        )
        print("Sending message...")
        send_telegram(msg)
    else:
        print("No data available.")

if __name__ == "__main__":
    main()
