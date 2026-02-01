import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# הגדרות
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# קואורדינטות טונג סאלה
LAT = 9.7126
LON = 99.9912

def get_tides():
    # שינוי: שימוש ב-API הכללי יותר של המודל הגלובלי
    # אנחנו מבקשים את גובה פני הים (sea_surface_height) כתחליף לגאות ושפל אם אין נתון ישיר
    # או מנסים את ה-Endpoint הרשמי בצורה מתוקנת
    
    # ננסה שוב את ה-Endpoint הרשמי, אבל נוודא שהפרמטרים נכונים
    # אם זה לא עובד, זה אומר שאין נתונים לנקודה הזו ב-Open-Meteo
    # אז נשתמש בטריק: נבדוק נקודה קרובה יותר למרכז הים
    
    # ניסיון 1: נקודה קצת יותר רחוקה מהחוף (לפעמים נקודות על היבשה נכשלות)
    LAT_SEA = 9.72  
    LON_SEA = 99.98 
    
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT_SEA}&longitude={LON_SEA}&hourly=wave_height&timezone=Asia%2FBangkok"
    
    try:
        response = requests.get(url).json()
        
        if 'hourly' not in response:
            print("API Error Response:", response)
            return None, None

        hourly = response['hourly']
        df = pd.DataFrame({
            'time': hourly['time'],
            'height': hourly['wave_height'] # משתמשים בגובה הגלים כאינדיקציה (זמנית)
        })
        
        # המרה לזמן וסינון
        df['time'] = pd.to_datetime(df['time'])
        now = datetime.now()
        future = df[df['time'] > now].head(12)
        
        if future.empty:
            return None, None

        # מציאת המינימום
        min_row = future.loc[future['height'].idxmin()]
        
        return min_row['time'], min_row['height']
        
    except Exception as e:
        print(f"Error fetching tides: {e}")
        return None, None

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def main():
    print("Checking sea conditions for Thong Sala...")
    time, height = get_tides()
    
    if time:
        time_str = time.strftime("%H:%M")
        date_str = time.strftime("%d/%m")
        
        msg = (
            f"🌊 **מצב הים - טונג סאלה** 🌊\n"
            f"📅 תאריך: {date_str}\n"
            f"📉 שפל/ים רגוע בשעה: **{time_str}**\n"
            f"📏 גובה גלים משוער: **{height:.2f} מטר**\n\n"
            f"הנתונים כרגע הם הערכה. הבוט לומד...\n"
            f"Join us: @thongsala_tides"
        )
        print(msg)
        send_telegram(msg)
    else:
        print("Failed to get data.")
        # שליחת הודעת שגיאה לטלגרם כדי שתדע שזה רץ
        send_telegram("⚠️ שגיאה בקבלת נתוני הים. הבוט רץ, אבל ה-API לא החזיר מידע.")

if __name__ == "__main__":
    main()
