import os
import datetime
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
import datetime

current_year = datetime.datetime.now().year
next_year = current_year + 1

super_macro_prompt = f"""
คุณคือ Chief Agricultural Economist & Strategic Supply Chain Director ประจำอุตสาหกรรมข้าวไทย
*คำเตือนสำคัญที่สุด: ปัจจุบันคือปี {current_year} (และมองข้ามไปถึงปี {next_year}) ห้ามอ้างอิงปี ค.ศ. ในอดีตเด็ดขาด*
จงค้นหาและประมวลผลข้อมูลตลาดข้าว ณ ปัจจุบัน (ปี {current_year}) เพื่อเขียนบทวิเคราะห์ระดับผู้บริหาร ความยาว 4-5 บรรทัด โดยครอบคลุม:

1. Global Macro: ค่าเงิน THB/USD, ค่าขนส่ง/เรือ (Freight), ราคาน้ำมัน, สถานการณ์สงคราม/การเมืองโลก และนโยบายส่งออกของอินเดีย/เวียดนาม ในปี {current_year}
2. Domestic Inventory & Seasonality: ปริมาณผลผลิตข้าวเปลือกเข้าโรงสีในไทย, สภาพอากาศ, ต้นทุนการถือครองคลัง (Holding Cost) 
3. Must-Stock Target: ระบุชัดเจนว่าข้าวเกรดใดในไทยที่ "น่ากักตุนมากที่สุด (Top Must-Stock Pick)" ในปี {current_year} เพราะเหตุใด

เน้นข้อมูลเชิงตัวเลข ทิศทางราคา และบทสรุปที่เฉียบคม นำไปใช้ตัดสินใจเชิงกลยุทธ์ได้ทันที
"""

    print("Executing Super Macro Analysis with gemini-3.6-flash...")
    macro_response = ai_client.models.generate_content(
        model='gemini-3.6-flash',
        contents=super_macro_prompt
    )

    # 4. Step 2: 9-Grade Precision Inventory Strategy
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

    # 5. Clean Garbage Cells
    sheet.batch_clear(['A12:E12', 'A14:E18'])
    
    # อัปเดต Macro Narrative ลง A8
    sheet.update('A8', [[macro_response.text]])

    # แปลงผลลัพธ์ JSON
    clean_json = grid_response.text.strip().replace('```json', '').replace('```', '')
    data_items = json.loads(clean_json)
    
    table_rows = []
    must_stock_items = []

    for item in data_items:
        grade = item.get("grade_name", "")
        status = item.get("market_status", "")
        forecast = item.get("fob_forecast", "")
        action = item.get("strategy_action", "")
        target = item.get("target_markets", "")

        table_rows.append([grade, status, forecast, action, target])

        # ถ้าเป็นตัวที่น่ากักตุน (MUST STOCK) ให้เก็บไว้เอาไปโชว์โซนบน (บรรทัด 14 เป็นต้นไป)
        if "MUST STOCK" in action:
            must_stock_items.append([grade, status, action])

    # อัปเดตตารางหลัก 9 เกรด (A22:E30)
    sheet.update('A22:E30', table_rows)

    # หยอดตัว MUST STOCK เข้าไปในโซนบน (เริ่มบรรทัด 14) อัตโนมัติ
    if must_stock_items:
        sheet.update(f'A14:C{13 + len(must_stock_items)}', must_stock_items)

    print("✅ Super Data Analysis Completed & Sheet Updated Successfully!")

except Exception as e:
    print(f"❌ Execution Failure Details:")
    traceback.print_exc()
    raise e
