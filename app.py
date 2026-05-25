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

# ===== TRIPS DATABASE (ข้อมูลทรip ทั้งปี) =====
trips_database = {
    "June": [
        {"name": "เขาล้อมหมวก", "country": "🇹🇭", "date": "1 มิ.ย.", "duration": "1 วัน", "price": 1600},
        {"name": "เขาหลวงสุโขทัย", "country": "🇹🇭", "date": "6-7 มิ.ย.", "duration": "2 วัน", "price": 2460},
        {"name": "ดอยห้วยทู่", "country": "🇹🇭", "date": "6-7 มิ.ย.", "duration": "2 วัน", "price": 3300},
        {"name": "ดอยหลวงตาก", "country": "🇹🇭", "date": "6-7 มิ.ย.", "duration": "2 วัน", "price": 3300},
        {"name": "ป่าบงเปียง", "country": "🇹🇭", "date": "6-7 มิ.ย.", "duration": "2 วัน", "price": 3200},
        {"name": "เขาหลวงสุโขทัย", "country": "🇹🇭", "date": "13-14 มิ.ย.", "duration": "2 วัน", "price": 2460},
        {"name": "ดอยตาปัง", "country": "🇹🇭", "date": "13-14 มิ.ย.", "duration": "2 วัน", "price": 3300},
        {"name": "เขาช่องลม", "country": "🇹🇭", "date": "14 มิ.ย.", "duration": "1 วัน", "price": 1600},
        {"name": "ดอยห้วยทู่", "country": "🇹🇭", "date": "20-21 มิ.ย.", "duration": "2 วัน", "price": 3300},
        {"name": "ม่อนสี่สหาย", "country": "🇹🇭", "date": "20-21 มิ.ย.", "duration": "2 วัน", "price": 3300},
        {"name": "เขาหลวงสุโขทัย", "country": "🇹🇭", "date": "20-21 มิ.ย.", "duration": "2 วัน", "price": 2460},
        {"name": "ลาวใต้ Bolaven", "country": "🇱🇦", "date": "26-28 มิ.ย.", "duration": "3 วัน", "price": 5200},
        {"name": "ดอยหลวงตาก", "country": "🇹🇭", "date": "27-28 มิ.ย.", "duration": "2 วัน", "price": 3300},
        {"name": "ดอยห้วยหมี", "country": "🇹🇭", "date": "27-28 มิ.ย.", "duration": "2 วัน", "price": 3200},
    ],
    "July": [
        {"name": "ลาวใต้ Bolaven", "country": "🇱🇦", "date": "3-5 ก.ค.", "duration": "3 วัน", "price": 5200},
        {"name": "เขาหลวงสุโขทัย", "country": "🇹🇭", "date": "4-5 ก.ค.", "duration": "2 วัน", "price": 2460},
        {"name": "ดอยหลวงตาก", "country": "🇹🇭", "date": "4-5 ก.ค.", "duration": "2 วัน", "price": 3300},
        {"name": "Bromo Ijen Tumpak Sewu", "country": "🇮🇩", "date": "4-7 ก.ค.", "duration": "4 วัน", "price": 13900},
        {"name": "Kinabalu Malaysia", "country": "🇲🇾", "date": "23-26 ก.ค.", "duration": "4 วัน", "price": 36900},
    ],
    "August": [
        {"name": "เขาหลวงสุโขทัย", "country": "🇹🇭", "date": "1-2 ส.ค.", "duration": "2 วัน", "price": 2460},
        {"name": "ม่อนสี่สหาย", "country": "🇹🇭", "date": "1-2 ส.ค.", "duration": "2 วัน", "price": 3300},
        {"name": "Kinabalu Malaysia", "country": "🇲🇾", "date": "6-9 ส.ค.", "duration": "4 วัน", "price": 36900},
        {"name": "ซินเจียง 120km", "country": "🇨🇳", "date": "7-13 ส.ค.", "duration": "7 วัน", "price": 49900},
        {"name": "เขาคีโหมด", "country": "🇹🇭", "date": "8-12 ส.ค.", "duration": "5 วัน", "price": 5200},
    ],
    "September": [
        {"name": "เลอกวาเดาะ", "country": "🇹🇭", "date": "3-4 ก.ย.", "duration": "2 วัน", "price": 3400},
        {"name": "ลาวใต้ Bolaven", "country": "🇱🇦", "date": "4-6 ก.ย.", "duration": "3 วัน", "price": 5200},
        {"name": "Kowloon Peak", "country": "🇭🇰", "date": "4-7 ก.ย.", "duration": "3 วัน", "price": 9850},
        {"name": "ดอยหลวงตาก", "country": "🇹🇭", "date": "5-6 ก.ย.", "duration": "2 วัน", "price": 3300},
    ],
    "October": [
        {"name": "ฉงชิ่ง อุทยานหลุมฟ้า", "country": "🇨🇳", "date": "1-4 ต.ค.", "duration": "4 วัน", "price": 13650},
        {"name": "ซาปา ฟานชิปัน", "country": "🇻🇳", "date": "3-6 ต.ค.", "duration": "4 วัน", "price": 12650},
        {"name": "Bromo Ijen Tumpak Sewu", "country": "🇮🇩", "date": "5-8 ต.ค.", "duration": "4 วัน", "price": 13900},
        {"name": "ดานัง ฮอยอัน บานาฮีล", "country": "🇻🇳", "date": "9-12 ต.ค.", "duration": "4 วัน", "price": 12650},
    ],
    "November": [
        {"name": "ดอยม่อนจอง", "country": "🇹🇭", "date": "5-6 พ.ย.", "duration": "2 วัน", "price": 3600},
        {"name": "ดานัง ฮอยอัน บานาฮีล", "country": "🇻🇳", "date": "5-8 พ.ย.", "duration": "4 วัน", "price": 12650},
        {"name": "Almaty Kazakhstan", "country": "🇰🇿", "date": "6-10 พ.ย.", "duration": "5 วัน", "price": 39900},
        {"name": "Fuji Tokyo Nikko", "country": "🇯🇵", "date": "11-15 พ.ย.", "duration": "5 วัน", "price": 39900},
    ],
    "December": [
        {"name": "Kowloon Peak", "country": "🇭🇰", "date": "4-6 ธ.ค.", "duration": "3 วัน", "price": 9850},
        {"name": "Almaty Kazakhstan", "country": "🇰🇿", "date": "4-8 ธ.ค.", "duration": "5 วัน", "price": 39900},
        {"name": "ดานัง ฮอยอัน บานาฮีล", "country": "🇻🇳", "date": "5-8 ธ.ค.", "duration": "4 วัน", "price": 12650},
        {"name": "เฉินตู สี่ดรุณี", "country": "🇨🇳", "date": "18-21 ธ.ค.", "duration": "4 วัน", "price": 21990},
    ],
    "January": [
        {"name": "Almaty Kazakhstan", "country": "🇰🇿", "date": "2-6 ม.ค.", "duration": "5 วัน", "price": 39900},
        {"name": "ดานัง ฮอยอัน บานาฮีล", "country": "🇻🇳", "date": "9-12 ม.ค.", "duration": "4 วัน", "price": 12650},
        {"name": "ฮาร์บิน หมู่บ้านหิมะ", "country": "🇨🇳", "date": "10-13 ม.ค.", "duration": "4 วัน", "price": 14990},
        {"name": "Phu Quoc Vietnam", "country": "🇻🇳", "date": "22-25 ม.ค.", "duration": "4 วัน", "price": 12650},
    ],
    "February": [
        {"name": "ฮาร์บิน หมู่บ้านหิมะ", "country": "🇨🇳", "date": "6-9 ก.พ.", "duration": "4 วัน", "price": 14990},
        {"name": "ซาปา ฟานชิปัน", "country": "🇻🇳", "date": "12-15 ก.พ.", "duration": "4 วัน", "price": 12650},
        {"name": "Kinabalu Malaysia", "country": "🇲🇾", "date": "14-17 ก.พ.", "duration": "4 วัน", "price": 36900},
        {"name": "ดานัง ฮอยอัน บานาฮีล", "country": "🇻🇳", "date": "20-23 ก.พ.", "duration": "4 วัน", "price": 12650},
    ],
    "March": [
        {"name": "เขาอู่กง ฉางชา", "country": "🇨🇳", "date": "5-8 มี.ค.", "duration": "4 วัน", "price": 14990},
        {"name": "ดานัง ฮอยอัน บานาฮีล", "country": "🇻🇳", "date": "6-9 มี.ค.", "duration": "4 วัน", "price": 12650},
        {"name": "Annapurna Base Camp", "country": "🇳🇵", "date": "10-18 มี.ค.", "duration": "9 วัน", "price": 26900},
    ],
    "April": [
        {"name": "Annapurna Base Camp", "country": "🇳🇵", "date": "9-17 เม.ย.", "duration": "9 วัน", "price": 26900},
        {"name": "เฉินตู สี่ดรุณี", "country": "🇨🇳", "date": "10-13 เม.ย.", "duration": "4 วัน", "price": 21990},
        {"name": "ฉงชิ่ง อุทยานหลุมฟ้า", "country": "🇨🇳", "date": "12-15 เม.ย.", "duration": "4 วัน", "price": 13650},
    ],
    "May": [
        {"name": "อ่าวคราม เกาะเตียบ", "country": "🇹🇭", "date": "1-3 พ.ค.", "duration": "3 วัน", "price": 4990},
        {"name": "ฉงชิ่ง อุทยานหลุมฟ้า", "country": "🇨🇳", "date": "1-4 พ.ค.", "duration": "4 วัน", "price": 13650},
        {"name": "เขาเจ็ดยอด", "country": "🇹🇭", "date": "9-10 พ.ค.", "duration": "2 วัน", "price": 3900},
    ],
}

# ===== COMPANY INFO =====
company_info = {
    "name": "เข้าป่า Two Day One Trip",
    "license_number": "51/01141",
    "description": "บริษัทดำเนินการจัดทริปท่องเที่ยว เดินป่า ทริปชิวล์ ทริปกลุ่ม ทั้ง Private และ Joiner",
    "operating_years": 4,
    "highlights": [
        "ประสบการณ์ 4 ปี ต่อเนื่อง",
        "บริษัทมีจริง เชื่อถือได้",
        "รีวิวจริง organic",
        "ดำเนินงานอย่างมีระบบ",
        "คำนึงถึงความปลอดภัยและรับผิดชอบสูงสุด",
        "โปร่งใส"
    ],
    "payment_policy": "มัดจำเก็บก่อน 50% หรือจ่ายเต็ม",
    "price_includes": [
        "รถตู้ VIP ไป-กลับ กทม พร้อมคนขับ",
        "ค่าน้ำมันเชื้อเพลิง",
        "ค่าเข้าอุทยาน",
        "ค่าพื้นที่กางเต๊นท์",
        "ค่าอาหาร 2 มื้อบนเขา",
        "ค่าลูกหาบส่วนกลาง",
        "ค่าเจ้าหน้าที่นำทาง",
        "ค่าประกันการเดินทาง",
        "ค่าสตาฟฟ์ดูแลตลอดทั้งทริป",
        "ประกันอุบัติเหตุทุกทริป"
    ],
    "faq": {
        "guide_license": "ไกด์มีใบอนุญาตทุกคน สามารถแจ้งข้อมูลให้ลูกค้าได้",
        "insurance": "มีประกันอุบัติเหตุทุกทริป",
        "guide_ratio": "ไกด์ 1 คน ต่อลูกค้า 9 คน (ขึ้นอยู่กับเส้นทางและจำนวนลูกค้า)",
        "advance_booking": "จองล่วงหน้าได้ข้ามปี ไม่ต่ำกว่า 15 วัน",
        "deposit_cancellation": "มีมัดจำเพื่อยืนยันสิทธิ์ เป็นไปตามเงื่อนไขของแต่ละทริป",
        "bad_weather": "มีแผนสำรองอยู่แล้ว คำนึงถึงความปลอดภัยเป็นหลัก"
    },
    "legal_compliance": "ดำเนินการถูกต้องตามกฎหมาย มีใบอนุญาตชัดเจน เน้นการดูแลที่ใกล้ชิดเพื่อให้คุณได้ภาพสวยและประสบการณ์ที่ดีที่สุดกลับบ้าน"
}

def get_trips_by_month(month_name):
    """ดึงทริปตามเดือนและจัดรูปแบบให้อ่านง่าย"""
    if month_name not in trips_database:
        return None
    
    trips = trips_database[month_name]
    result = f"เดือนนี้เรามีทริปดี ๆ อยู่นะคะ:\n"
    
    # แสดง 5 รายการแรก
    for i, trip in enumerate(trips[:5], 1):
        result += f"{i}. {trip['name']} {trip['country']}\n   {trip['date']} | {trip['duration']} | {trip['price']} บาท\n"
    
    if len(trips) > 5:
        result += f"\n(และอีก {len(trips) - 5} ทริปอีก)\n"
    
    result += f"\nดูเต็มที่ที่ https://weena2d1n.com/ ค่ะ"
    return result

def get_company_info(info_type):
    """ดึงข้อมูลบริษัท"""
    if info_type == "about":
        return f"{company_info['name']}\n✓ ใบอนุญาต: {company_info['license_number']}\n✓ {company_info['description']}\n✓ ดำเนินการมาแล้ว {company_info['operating_years']} ปี"
    elif info_type == "price_includes":
        result = "ราคารวม:\n"
        for i, item in enumerate(company_info['price_includes'], 1):
            result += f"{i}. {item}\n"
        return result
    elif info_type == "faq":
        result = "คำถามที่พบบ่อย:\n\n"
        for q, a in company_info['faq'].items():
            q_display = q.replace("_", " ").title()
            result += f"❓ {q_display}\n{a}\n\n"
        return result
    return None

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

=== ฐานข้อมูลทริป (Database Available) ===
มีข้อมูลทริปเต็มปี 12 เดือน: June, July, August, September, October, November, December, January, February, March, April, May
- เมื่อลูกค้าถาม "เดือนไหนมีที่เที่ยว" ให้ตอบจาก trips_database
- แสดง 5 ทริปแรก + ลิงก์ https://weena2d1n.com/

=== ข้อมูลบริษัท (Company Info Available) ===
ชื่อ: เข้าป่า Two Day One Trip
ใบอนุญาต: 51/01141
ประเภท: ท่องเที่ยว เดินป่า ทริปชิวล์ (Private & Joiner)
ดำเนินการมาแล้ว: 4 ปี เชื่อถือได้ รีวิวจริง ระบบอย่างมีวินัย ความปลอดภัยสูงสุด
ค่ามัดจำ: 50% สำหรับยืนยันสิทธิ์
ประกัน: มีประกันอุบัติเหตุทุกทริป ไกด์ทุกคนมีใบอนุญาต
อัตราส่วน: ไกด์ 1 คน ต่อลูกค้า 9 คน (ขึ้นอยู่กับเส้นทาง)
เงื่อนไข: จองล่วงหน้า 15+ วัน มีแผนสำรองเมื่ออากาศไม่ดี

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