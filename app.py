import os
import json
import traceback
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai

try:
    # 1. Google Sheets Authorization & Setup
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)

    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    sheet = client.open_by_key(spreadsheet_id).worksheet("Dashboard")

    # 2. Gemini Client Setup
    ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    # 3. Step 1: Real-time Super Macro Analysis (gemini-3.6-flash)
    super_macro_prompt = """
    คุณคือ Chief Agricultural Economist & Strategic Supply Chain Director ประจำอุตสาหกรรมข้าวไทย
    จงประมวลผลและวิเคราะห์แนวโน้มตลาดข้าว เพื่อเขียนบทวิเคราะห์ระดับผู้บริหาร ความยาว 4-5 บรรทัด โดยครอบคลุม:
    1. Global Macro: ค่าเงิน THB/USD, ค่าขนส่ง/เรือ, ราคาน้ำมัน, สถานการณ์สงคราม/การเมืองโลก และนโยบายส่งออกของอินเดีย/เวียดนาม
    2. Domestic Inventory & Seasonality: ปริมาณผลผลิตข้าวเปลือกเข้าโรงสีในไทย, สภาพอากาศ, ต้นทุนการถือครองคลัง (Holding Cost)
    3. Must-Stock Target: ระบุชัดเจนว่าข้าวเกรดใดในไทยที่ "น่ากักตุนมากที่สุด (Top Must-Stock Pick)" เพราะเหตุใด

    เน้นข้อมูลเชิงตัวเลข ทิศทางราคา และบทสรุปที่เฉียบคม นำไปใช้ตัดสินใจเชิงกลยุทธ์ได้ทันที
    """

    print("Executing Super Macro Analysis with gemini-3.6-flash...")
    macro_response = ai_client.models.generate_content(
        model='gemini-3.6-flash',
        contents=super_macro_prompt
    )

    # 4. Step 2: 9-Grade Precision Inventory Strategy (gemini-3.6-flash)
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

    ตอบกลับเป็น JSON array เท่านั้น ห้ามใส่ markdown หรือข้อความอื่น:
    [
      {
        "grade_name": "ชื่อเกรด",
        "market_status": "Tight / Balanced / Surplus",
        "fob_forecast": "ราคา FOB (USD/MT)",
        "strategy_action": "⭐ MUST STOCK หรือ Hold / ดันราคา หรือ ขายตามรอบ หรือ เร่งระบาย",
        "target_markets": "ตลาดเป้าหมาย"
      }
    ]
    """

    print("Executing 9-Grade Inventory Forecasting with gemini-3.6-flash...")
    grid_response = ai_client.models.generate_content(
        model='gemini-3.6-flash',
        contents=grade_prompt
    )

    # 5. Clean Garbage Cells & Update Sheets
    sheet.batch_clear(['A12:E12', 'A15:E18'])
    
    # อัปเดต Macro Narrative ลง A8
    sheet.update('A8', [[macro_response.text]])

    # แปลงผลลัพธ์ JSON และอัปเดตลงตาราง A22:E30
    clean_json = grid_response.text.strip().replace('```json', '').replace('```', '')
    data_items = json.loads(clean_json)
    
    table_rows = []
    for item in data_items:
        table_rows.append([
            item.get("grade_name", ""),
            item.get("market_status", ""),
            item.get("fob_forecast", ""),
            item.get("strategy_action", ""),
            item.get("target_markets", "")
        ])
    
    sheet.update('A22:E30', table_rows)
    print("✅ Super Data Analysis Completed & Sheet Updated Successfully!")

except Exception as e:
    print(f"❌ Execution Failure Details:")
    traceback.print_exc()
    raise e
