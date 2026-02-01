def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    
    # שליחה ושמירת התשובה
    response = requests.post(url, json=payload)
    
    # הדפסת התשובה ללוג כדי שנבין מה קרה
    print(f"Telegram Status Code: {response.status_code}")
    print(f"Telegram Response: {response.text}")
