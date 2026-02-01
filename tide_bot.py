import os
import requests
from datetime import datetime, timedelta

# הגדרות
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
WORLDTIDES_KEY = os.getenv('WORLDTIDES_KEY')

# קואורדינטות טונג סאלה
LAT = 9.7126
LON = 99.9912

# שעון תאילנד (UTC+7)
THAI_OFFSET = timedelta(hours=7)

def get_thai_now():
    return datetime.utcnow() + THAI_OFFSET

def to_thai_time(timestamp):
    return datetime.utcfromtimestamp(timestamp) + THAI_OFFSET

def get_daytime_low():
    """
    מחפש את השפל בשעות האור (06:00-16:00).
    אם עכשיו ערב -> מביא תחזית למחר.
    אם עכשיו בוקר -> מביא תחזית להיום.
    """
    url = f"https://www.worldtides.info/api/v3?heights&step=3600&days=2&lat={LAT}&lon={LON}&key={WORLDTIDES_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if 'heights' not in data:
            print(f"API Error or No Data. Response keys: {data.keys()}")
            return None, None, None

        now_thai = get_thai_now()
        
        # --- ההחלטה החכמה ---
        # אם השעה אחרי 16:00, עוברים למחר
        if now_thai.hour >= 16:
            target_date = (now_thai + timedelta(days=1)).strftime('%Y-%m-%d')
            day_label = "מחר"
        else:
            target_date = now_thai.strftime('%Y-%m-%d')
            day_label = "היום"
            
        print(f"Debug: Planning for {day_label} ({target_date})") # לוג לבדיקה

        # סינון הנתונים לפי התאריך הנבחר ושעות האור
        daytime_slots = []
        for h in data['heights']:
            dt_thai = to_thai_time(h['dt'])
            
            if dt_thai.strftime('%Y-%m-%d') == target_date:
                if 6 <= dt_thai.hour <= 16:
                    daytime_slots.append({
                        'time': dt_thai,
                        'height': h['height']
                    })

        if not daytime_slots:
            print(f"No slots found for date {target_date} between 06:00-16:00")
            return None, None, None
            
        # מציאת השעה הכי טובה (הכי נמוכה)
        best_slot = min(daytime_slots, key=lambda x: x['height'])
        
        # מציאת מצב הבוקר (08:00) באותו יום
        morning_slot = next((s for s in daytime_slots if s['time'].hour == 8), None)
        if not morning_slot:
            morning_slot = daytime_slots[0]

        return best_slot, morning_slot, day_label

    except Exception as e:
        print(f"Error: {e}")
        return None, None, None

def get_weather(target_time):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=Asia%2FBangkok"
    try:
        data = requests.get(url).json()
        hourly = data['hourly']
        target_str = target_time.strftime('%Y-%m-%dT%H:00')
        if target_str in hourly['time']:
            index = hourly['time'].index(target_str)
            return hourly['temperature_2m'][index], hourly['relative_humidity_2m'][index], hourly['wind_speed_10m'][index]
        return "N/A", "N/A", "N/A"
    except:
        return "N/A", "N/A", "N/A"

def get_beach_details(height):
    report = ""
    # Ko Tae Nai
    if height < 0.3: s1 = "פתוח לגמרי, תענוג של הליכה 🏝️"
    elif height < 0.6: s1 = "השביל עביר, גובה מים: קרסול/ברך 🌊"
    else: s1 = "השביל מכוסה מים, לא מתאים להליכה 🛶"
    report += f"<b>השביל לאי (Ko Tae Nai):</b>\n{s1}\n"
    
    # Ao Bang Charu
    if height < 0.8: s2 = "רצועה רחבה, מעולה לריצה/הליכה 🏃"
    elif height < 1.2: s2 = "רצועה צרה של חול רטוב 👣"
    else: s2 = "אין חוף (המים גבוהים) 🚫"
    report += f"<b>חוף באנג צ'ארו:</b>\n{s2}"
    return report

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram Error: {e}")

def main():
    print("Running Tide Bot V3 (Auto-Tomorrow Logic)...")
    best_slot, morning_slot, day_label = get_daytime_low()
    
    if best_slot:
        peak_time = best_slot['time']
        peak_height = best_slot['height']
        
        # בניית הודעת בוקר
        morning_msg = ""
        if morning_slot:
             morning_msg = f"🌅 <b>בבוקר (08:00):</b> גובה {morning_slot['height']:.2f}m"

        temp, humidity, wind = get_weather(peak_time)
        beach_report = get_beach_details(peak_height)
        date_str = peak_time.strftime("%d/%m")
        
        msg = (
            f"☀️ <b>תחזית הליכה - {day_label}</b> | {date_str}\n"
            f"(בשעות האור בלבד: 06:00-16:00)\n"
            f"────────────────\n\n"
            f"{morning_msg}\n\n"
            f"📉 <b>הזמן הכי טוב לצאת {day_label}:</b>\n"
            f"השפל הכי נמוך יהיה ב-<b>{peak_time.strftime('%H:%M')}</b>\n"
            f"(גובה המים: <b>{peak_height:.2f}m</b>)\n\n"
            f"🌤️ <b>מזג אוויר לזמן ההליכה:</b>\n"
            f"{temp}°C | רוח: {wind} קמ\"ש\n\n"
            f"🏝️ <b>מצב המסלולים:</b>\n"
            f"{beach_report}\n\n"
            f"תבלו! 😎"
        )
        send_telegram(msg)
        print("Message sent!")
    else:
        print("No data found (Logs likely show why).")

if __name__ == "__main__":
    main()
