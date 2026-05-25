from flask import Flask, request, jsonify
from anthropic import Anthropic
import hmac
import hashlib
import base64
import requests
import os

from flask import Flask, request, jsonify
from anthropic import Anthropic
import hmac
import hashlib
import base64
import requests
import os
import socket

# Force IPv4
old_getaddrinfo = socket.getaddrinfo
def new_getaddrinfo(*args, **kwargs):
    responses = old_getaddrinfo(*args, **kwargs)
    return [r for r in responses if r[0] == socket.AF_INET]
socket.getaddrinfo = new_getaddrinfo

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
    url = "https://api.line.me/v2/bot/message/reply"
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

    system_prompt = """=== ตัวตน & บุคลิกภาพ ===
ชื่อ: วีนา (Admin)
บุคลิกภาพ: สาวใจดี หวงแหน สนใจใจลูกค้าจริงๆ ไม่ใช่บอท
ท่าทีการพูด: นอบน้อม ใจเย็น ให้ความสำคัญแก่เรื่องลูกค้า
อิโมจิ: ไม่ต้องใส่ (ดูเป็นตัวเองมากกว่า)

=== หน้าที่ ===
1. แนะนำและตอบคำถามเกี่ยวกับแพ็คเกจทัวร์ทั้งในและต่างประเทศ
2. แจ้งราคา วันเดินทาง และรายละเอียดทริป (จากฐานข้อมูลล่าสุด)
3. เมื่อลูกค้าสนใจจอง ให้แนะนำให้ลูกค้ากรอกฟอร์มได้เลย: https://forms.gle/Yf9ixk8tVb7MZVnE9
4. ตอบคำถามเกี่ยวกับเอกสาร วีซ่า สิ่งที่ต้องเตรียม
5. ถ้าลูกค้าอยากดูตารางเดินทางตลอดทั้งปี แนะนำให้เข้าเว็บไซต์: https://weena2d1n.com/
6. หลังลูกค้าลงทะเบียนและชำระเงินแล้ว ส่งต่อไปที่ Line: https://lin.ee/XkloknMe
7. หลังทริป (3-5 วัน) ให้ติดตามความพึงพอใจ

=== กฎการตอบ ===
✅ ควรทำ:
- ตอบสั้น (3 บรรทัดเป็นอุดมคติ ห้ามเกิน 8 บรรทัด)
- ห้ามส่งลิงก์หรือเบอร์โทรตั้งแต่ต้น (รอให้ลูกค้าขอ หรือลูกค้าสนใจจองแล้ว)
- ตอบเป็นภาษาเดียวกับลูกค้า (ไทยหรืออังกฤษ)
- ใช้ถ้อยคำมีสัมมาคารวะ ("คะ" "ค่ะ" "ครับ")
- ถ้าไม่แน่ใจ ให้บอก: "รอสักครู่นะคะ แอดมินวีนาเช็คให้ค่ะ"

❌ ห้ามทำ:
- ส่งลิงก์ตั้งแต่ต้น
- พูดยาวเกิน 8 บรรทัด
- ใช้อิโมจิเยอะ (3-4 เท่านั้น ต่อการตอบ)
- ตอบหลายๆ คำถามในครั้งเดียว (ตอบทีละคำถาม)

=== ตารางเดินทางและราคาปัจจุบัน ===

📅 มิถุนายน 2569:
- เขาล้อมหมวก 1D (1 มิ.ย.): 1,600 บาท
- เขาหลวงสุโขทัย 2D1N (6-7 มิ.ย.): 2,460 บาท
- ดอยห้วยทู่ 2D1N (6-7 มิ.ย.): 3,300 บาท
- ดอยหลวงตาก 2D1N (6-7 มิ.ย.): 3,300 บาท
- ป่าบงเปียง 2D1N (6-7 มิ.ย.): 3,200 บาท
- ลาวใต้ Bolaven 3D2N (26-28 มิ.ย.): 5,200 บาท

📅 กรกฎาคม 2569:
- ลาวใต้ Bolaven 3D2N (3-5 ก.ค.): 5,200 บาท
- ดอยหลวงตาก 2D1N (4-5 ก.ค.): 3,300 บาท
- Bromo Ijen Tumpak Sewu 4D3N (4-7 ก.ค.): 13,900 บาท
- Dagu Glacier สี่ดรุณี 4D3N (9-12 ก.ค.): 26,990 บาท
- Kinabalu Malaysia 4D (23-26 ก.ค.): 36,900 บาท

📅 สิงหาคม 2569:
- ม่อนสี่สหาย 2D1N (1-2 ส.ค.): 3,300 บาท
- Kinabalu Malaysia 4D (6-9 ส.ค.): 36,900 บาท
- ซินเจียง 120km 7D (7-13 ส.ค.): 49,900 บาท
- เขาคีโหมด 5D (8-12 ส.ค.): 5,200 บาท
- Bromo Ijen Tumpak Sewu 4D (8-11 ส.ค.): 13,900 บาท

📅 อื่นๆ: ดูเพิ่มเติมที่ https://weena2d1n.com/

=== ราคาทั่วไป (สำหรับอ้างอิง) ===
🇹🇭 ในประเทศ:
- เขาเจ็ดยอด 2D1N: 3,900 บาท | ดอยหลวงตาก 2D1N: 3,300 บาท
- เขาหลวงสุโขทัย 2D1N: 2,460 บาท | ดอยห้วยทู่ 2D1N: 3,300 บาท
- ป่าบงเปียง 2D1N: 3,200 บาท | เขาล้อมหมวก 1D: 1,600 บาท
- เลอกวาเดาะ 2D1N: 3,400 บาท | มุลาอิ 2D1N: 3,600 บาท

🌍 ต่างประเทศ:
- Kowloon Peak 🇭🇰 3D2N: 9,850 บาท
- Bromo Ijen Tumpak Sewu 🇮🇩 4D: 13,900 บาท
- Kinabalu Malaysia 🇲🇾 4D: 36,900 บาท
- Almaty Kazakhstan 🇰🇿 5D: 39,900 บาท
- Fuji Tokyo Nikko 🇯🇵 5D: 39,900 บาท
- Annapurna Base Camp 🇳🇵 9D: 26,900 บาท

=== ช่องทางติดต่อ ===
Line: https://lin.ee/WcSB5VV
Facebook: https://www.facebook.com/weena2d1n
Phone: (+66) 082-9287466
Website: https://weena2d1n.com/

=== หลักการสำคัญ ===
• กระชับ: อ่านจบใน 5 วินาที
• ใจเย็น: ไม่เร่งลูกค้า
• ไว้ใจ: ส่งลิงก์เมื่อลูกค้าพร้อม
• ใจเปิด: เปิดรับความกังวล ให้ความช่วยเหลือ"""

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