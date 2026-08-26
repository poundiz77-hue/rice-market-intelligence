import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. Google Sheets Authorization & Setup
# ---------------------------------------------------------
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

spreadsheet_id = os.environ.get("SPREADSHEET_ID")
sheet = client.open_by_key(spreadsheet_id).worksheet("Dashboard")

# ---------------------------------------------------------
# 2. Gemini Client Initialization
# ---------------------------------------------------------
ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# ---------------------------------------------------------
# 3. Step 1: Real-time Super Macro & Domestic Stock Analysis
# ---------------------------------------------------------
super_macro_prompt = """
คุณคือ Chief Agricultural Economist & Strategic Supply Chain Director ประจำอุตสาหกรรมข้าวไทย
จงประมวลผลและวิเคราะห์แนวโน้มตลาดข้าว เพื่อเขียนบทวิเคราะห์ระดับผู้บริหาร ความยาว 4-5 บรรทัด โดยครอบคลุม:

1. Global Macro: ค่าเงิน THB/USD, ค่าขนส่ง/เรือ (Freight), ราคาน้ำมัน, สถานการณ์สงคราม/การเมืองโลก และนโยบายส่งออกของอินเดีย/เวียดนาม
2. Domestic Inventory & Seasonality: ปริมาณผลผลิตข้าวเปลือกเข้าโรงสีในไทย, สภาพอากาศ, ต้นทุนการถือครองคลัง (Holding Cost)
3. Must-Stock Target: ระบุชัดเจนว่าข้าวเกรดใดในไทยที่ "น่ากักตุนมากที่สุด (Top Must-Stock Pick)" เพราะเหตุใด (เช่น Margin สูง หรือ Supply กำลังจะตึงตัว)

เน้นข้อมูลเชิงตัวเลข ทิศทางราคา และบทสรุปที่เฉียบคม นำไปใช้ตัดสินใจเชิงกลยุทธ์ได้ทันที
"""

print("Executing Super Macro Analysis via Gemini Pro...")
macro_response = ai_client.models.generate_content(
    model='gemini-2.5-pro',
    contents=super_macro_prompt,
    config=types.GenerateContentConfig(
        temperature=0.1
    )
)

# ---------------------------------------------------------
# 4. Step 2: 9-Grade Precision Inventory Strategy (JSON Schema)
# ---------------------------------------------------------
grade_prompt = """
ประเมินและวิเคราะห์กลยุทธ์สินค้าคงคลังและราคาสำหรับข้าว 9 เกรดหลักของไทย:
1. ข้าวหอมมะลิ (105/กข15)
2. ข้าวออร์แกนิก (Organic - EU/US)
3. ข้าวปทุมธานี
4. ข้าวขาว 5%
5. ข้าวหอม (เก่า) [Premium Margin]
6. ข้าวเหนียว
7. ปลายหอม (ใหม่)
8. ปลายหอมเก่า (ตลาดแปรรูป)
9. ปลายปลาทู (A1 Extra)

ตอบเป็น JSON Array เท่านั้น โดยแต่ละรายการต้องประกอบด้วย:
- grade_name: ชื่อเกรดสินค้าตามรายการข้างต้น
- market_status: "Tight" หรือ "Balanced" หรือ "Surplus"
- fob_forecast: ราคาคาดการณ์ FOB (USD/MT) เช่น "920-940 USD/MT"
- strategy_action: "⭐ MUST STOCK", "Hold / ดันราคา", "ขายตามรอบ", หรือ "เร่งระบาย"
- target_markets: ตลาดเป้าหมายหลัก
"""

json_schema = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "grade_name": {"type": "STRING"},
            "market_status": {"type": "STRING"},
            "fob_forecast": {"type": "STRING"},
            "strategy_action": {"type": "STRING"},
            "target_markets": {"type": "STRING"}
        },
        "required": ["grade_name", "market_status", "fob_forecast", "strategy_action", "target_markets"]
    }
}

print("Executing 9-Grade Precision Forecasting...")
grid_response = ai_client.models.generate_content(
    model='gemini-2.5-pro',
    contents=grade_prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=json_schema,
        temperature=0.1
    )
)

# ---------------------------------------------------------
# 5. Step 3: Clean & Precise Google Sheets Output Mapping
# ---------------------------------------------------------
sheet.batch_clear(['A12:E12', 'A15:E18'])

# 1. เขียนบทวิเคราะห์ Super Macro สรุปลงช่อง A8
sheet.update('A8', [[macro_response.text]])

# 2. แปลง JSON อัปเดตตารางแนะนำหลักช่วง A22:E30
try:
    data_items = json.loads(grid_response.text)
    table_rows = []
    for item in data_items:
        table_rows.append([
            item["grade_name"],
            item["market_status"],
            item["fob_forecast"],
            item["strategy_action"],
            item["target_markets"]
        ])
    
    sheet.update('A22:E30', table_rows)
    print("✅ Super Data Analysis Completed & Sheet Updated Successfully!")

except Exception as e:
    print(f"❌ Execution Error: {e}")
