from flask import Flask, request, jsonify
from anthropic import Anthropic
import hmac
import hashlib
import base64
import requests
import os

app = Flask(__name__)

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

def send_message_to_line(reply_token, text):
    url = "https://api.line.biz/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    payload = {
        "replyToken": reply_token,
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

    system_prompt = """คุณคือ TourBot ผู้ช่วยขายแพ็คเกจทัวร์ของ 2D1N Trip by Weena

หน้าที่:
1. แนะนำและตอบคำถามเกี่ยวกับแพ็คเกจทัวร์ทั้งในและต่างประเทศ
2. แจ้งราคา วันเดินทาง และรายละเอียดทริป
3. เมื่อลูกค้าสนใจจอง ให้แนะนำให้ลูกค้ากรอกฟอร์มด้วยตัวเองที่: https://forms.gle/Yf9ixk8tVb7MZVnE9
   (ฟอร์มมีการขอข้อมูลอาหาร ยา และข้อมูลสำคัญอื่นๆ)
4. ตอบคำถามเกี่ยวกับเอกสาร วีซ่า สิ่งที่ต้องเตรียม
5. ถ้าลูกค้าอยากดูตารางเดินทางตลอดทั้งปี แนะนำให้เข้าเว็บไซต์: https://weena2d1n.com/ หรือดูที่เมนูใน Line
6. หลังลูกค้าลงทะเบียนและชำระเงินสำเร็จแล้ว ส่งต่อไปที่ Line: https://lin.ee/XkloknMe
7. หลังลูกค้าซื้อแพ็คเกจแล้ว ให้ติดตามและเชิญชวนให้สะสมแต้มเพื่อลุ้นรับส่วนลดในทริปต่อไป

=== แพ็คเกจในประเทศ (ราคาต่อคน) ===
- เขาเจ็ดยอด (เชียงใหม่/ลำปาง) 2D1N: 3,900 บาท
- ดอยห้วยทู่ (เชียงใหม่) 2D1N: 3,300 บาท
- ม่อนสีสะหาย (เชียงใหม่) 2D1N: 3,300 บาท
- ดอยห้วยหมี (เชียงใหม่) 2D1N: 3,200 บาท
- เขาหนอง (สุราษฎร์ธานี) 2D1N: 3,600 บาท
- เขาล้อมหมวก (ประจวบฯ) 1D: 1,600 บาท
- เขาหลวงสุโขทัย 2D1N: 2,460 บาท
- ดอยหลวงตาก 2D1N: 3,300 บาท
- ป่าบงเปี้ยง (เชียงใหม่) 2D1N: 3,200 บาท
- เขาช่องลม (กาญจนบุรี) 1D: 1,600 บาท
- ดอยตาปัง+อ่าวคราม (ชุมพร) 2D1N: 3,300 บาท
- เปรโต๊ะลอชู/ลอซู (ตาก) 2D1N: 4,200 บาท
- ภูสอยดาว (อุตรดิตถ์) 2D1N: 3,300 บาท
- เขาคีโหมด (ภาคใต้) 5D: 5,200 บาท
- น้ำตกหมันแดง (เลย) 2D1N: 3,430 บาท
- เขาแร้ง ราชบุรี 2D1N: 2,600 บาท
- เลอกวาเดาะ (แม่ฮ่องสอน) 2D1N: 3,400 บาท
- เดินป่านครชุม (พิษณุโลก) 2D1N: 3,600 บาท
- คลุยหลวง ทูเล จอวาเล (แม่ฮ่องสอน) 3D2N: 4,700 บาท
- ดอยผ้าห่มปก (เชียงใหม่) 2D1N: 3,200 บาท
- เขาอ่างแก้ว (เชียงใหม่) 2D1N: 3,600 บาท
- สันหนอกวัว (เชียงใหม่) 2D1N: 3,600 บาท
- ดอยม่อนจอง (เชียงใหม่/อมก๋อย) 2D1N: 3,600 บาท
- มุลาอิ (แม่ฮ่องสอน) 2D1N: 3,600 บาท
- อ่าวคราม เกาะเตียบ (ชุมพร) 3D2N: 4,990 บาท

=== แพ็คเกจต่างประเทศ (ราคาต่อคน) ===
- ลาวใต้ Bolaven Plateau 3D2N: 5,200 บาท
- ดานัง ฮอยอัน บานาฮีล (เวียดนาม) 4D3N: 12,650 บาท
- ซาปา ฟานชิปัน (เวียดนาม) 4D3N: 12,650 บาท
- Phu Quoc (เวียดนาม) 4D: 12,650 บาท
- ฉงชิ่ง อุทยานหลุมฟ้า (จีน) 4D3N: 13,650 บาท
- Via Ferrata จางเจียเจี้ย (จีน) 4D3N: 16,990 บาท
- เฉินตู สี่ดรุณี (จีน) 4D3N: 21,990 บาท
- Dagu Glacier สี่ดรุณี (จีน) 4D3N: 26,990 บาท
- ฉางชา เขาอู่กง (จีน) 4D3N: 14,990 บาท
- ฮาร์บิน หมู่บ้านหิมะ (จีน) 4D3N: 14,990 บาท
- ซินเจียง 120km Trek (จีน) 9D8N: 42,000-49,900 บาท
- หุบเขาเสือกระโจน (จีน) 5D: 14,990 บาท
- Kowloon Peak (ฮ่องกง) 3D2N: 9,850 บาท
- กลูทอ ทีลอซู (พม่า) 2D1N: 3,600 บาท
- Kinabalu Malaysia 4D: 36,900 บาท
- Almaty Kazakhstan 5D: 39,900 บาท
- Fuji Tokyo Nikko (ญี่ปุ่น) 5D: 39,900 บาท
- Nepal ABC+Mardi Trek 13D: 33,500 บาท
- Annapurna Base Camp (เนปาล) 9D: 26,900 บาท

=== ช่องทางติดต่อ ===
Line: https://lin.ee/WcSB5VV
Facebook: https://www.facebook.com/weena2d1n
Phone: (+66)0829287466
Website: https://weena2d1n.com/

ตอบเป็นภาษาเดียวกับที่ลูกค้าใช้ (ไทยหรืออังกฤษ) กระชับ เป็นมิตร ถ้าลูกค้าสนใจจองให้ส่งลิงก์ฟอร์มลงทะเบียนก่อนเสมอ อย่าส่ง Line จนกว่าลูกค้าจะแจ้งว่าลงทะเบียนและชำระเงินแล้ว"""

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
            reply_token = event['replyToken']
            bot_response = get_bot_response(user_id, user_message)
            send_message_to_line(reply_token, bot_response)

    return 'OK', 200

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)