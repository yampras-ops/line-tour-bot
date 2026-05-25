from flask import Flask, request, jsonify
from anthropic import Anthropic
import hmac
import hashlib
import base64
import requests
import os

app = Flask(__name__)

# Environment variables (ตั้งใน Railway)
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("CHANNEL_SECRET")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

client = Anthropic(api_key=ANTHROPIC_API_KEY)
user_conversations = {}

def verify_line_signature(body, signature):
    hash_obj = hmac.new(
        CHANNEL_SECRET.encode('utf-8'),
        body,
        hashlib.sha256
    )
    expected_signature = hash_obj.digest()
    return hmac.compare_digest(
        signature,
        base64.b64encode(expected_signature).decode('utf-8')
    )

def send_message_to_line(user_id, text):
    url = "https://api.line.biz/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(url, headers=headers, json=payload)

def get_bot_response(user_id, user_message):
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    user_conversations[user_id].append({
        "role": "user",
        "content": user_message
    })
    
    system_prompt = """คุณคือ TourBot ผู้ช่วยขายแพ็คเกจทัวร์อัตโนมัติ
    
หน้าที่:
1. ตอบคำถามเกี่ยวกับแพ็คเกจทัวร์
2. แนะนำแพ็คเกจตามความสนใจ
3. ช่วยจองทัวร์ (ขอ: ชื่อ, จำนวนคน, วันเดินทาง)
4. ตอบเกี่ยวกับเอกสาร, วีซ่า, สิ่งที่ต้องเตรียม

แพ็คเกจ:
- Thailand 3 Days: 15,000 บาท/คน
- Cambodia 4 Days: 18,000 บาท/คน
- Vietnam 5 Days: 22,000 บาท/คน

ตอบเป็นไทยกระชับและเป็นมิตร"""
    
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        system=system_prompt,
        messages=user_conversations[user_id]
    )
    
    bot_message = response.content[0].text
    user_conversations[user_id].append({
        "role": "assistant",
        "content": bot_message
    })
    
    if len(user_conversations[user_id]) > 10:
        user_conversations[user_id] = user_conversations[user_id][-10:]
    
    return bot_message

@app.route('/callback', methods=['POST'])
def handle_callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    if not verify_line_signature(body.encode('utf-8'), signature):
        return 'Invalid signature', 403
    
    events = request.json.get('events', [])
    
    for event in events:
        if event['type'] == 'message' and event['message'].get('type') == 'text':
            user_id = event['source']['userId']
            user_message = event['message']['text']
            
            bot_response = get_bot_response(user_id, user_message)
            send_message_to_line(user_id, bot_response)
    
    return 'OK', 200

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)