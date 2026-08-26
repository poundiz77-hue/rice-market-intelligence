import os
import json
import time
import urllib.request
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai

# ==========================================
# 1. ตั้งค่า API Key และ Google Sheets ID
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")

print("🚀 Starting Advanced Rice Intelligence & Inventory Forecast Engine...")

# เชื่อมต่อ Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(creds)
sheet = gc.open_by_key(SPREADSHEET_ID)

# ==========================================
# 2. ดึงอัตราแลกเปลี่ยน Real-time (USD/THB)
# ==========================================
try:
    url = "https://open.er-api.com/v6/latest/USD"
    req = urllib.request.urlopen(url)
    data = json.loads(req.read().decode('utf-8'))
    usd_thb = round(data['rates']['THB'], 2)
    print(f"✅ Real-time FX Rate Pulled: 1 USD = {usd_thb} THB")
except Exception as e:
    usd_thb = 36.50

# ==========================================
# 3. Gemini Deep Analytical & Forecasting Prompt
# ==========================================
print("🧠 Executing Deep Data Analysis & 30-60 Day Market Forecasting...")
client = genai.Client(api_key=GEMINI_API_KEY)

prompt = f"""
คุณคือ Chief Data Analyst และผู้เชี่ยวชาญด้านการคาดการณ์ตลาดข้าวส่งออกระดับโลก สำหรับโรงงานส่งออกข้าวไทย 100%

ภารกิจของคุณคือการทำ Market Forecasting 30-60 วันข้างหน้า และกำหนดกลยุทธ์บริหารคลังสินค้า (Inventory Strategy) 
โดยใช้กรอบการวิเคราะห์ 7 มิติเชิงลึก:
1. Macro Economy & FX (USD/THB ปัจจุบัน: {usd_thb} THB)
2. Competitor Trade Policies (อินเดีย, เวียดนาม, ปากีสถาน)
3. Climate & Supply Chain (El Niño/La Niña, ปริมาณน้ำในเขื่อน, คาดการณ์ผลผลิต)
4. Freight & Energy Costs (ราคาน้ำมันดิบ Brent, ค่าระวางเรือ Container/Bulk)
5. Demand Trends (ตลาดตะวันออกกลาง, แอฟริกา, สหรัฐฯ, ยุโรป, จีน)
6. Price Structure & Margin (ส่วนต่างราคาข้าวเก่า vs ข้าวใหม่, Margin Gap)
7. Geopolitics & Food Security

ให้ประเมินเกรดข้าวทั้ง 9 เกรดของโรงงานอย่างละเอียดและเจาะจง:
1. ข้าวหอมมะลิ (105/กข15)
2. ข้าวออร์แกนิก (Organic Rice EU/US Std)
3. ข้าวปทุมธานี
4. ข้าวห้า (ข้าวขาว 5% ใหม่)
5. ข้าวห้าเก่า (Premium Margin)
6. ข้าวเหนียว
7. ปลายหอม (ปลายใหม่)
8. ปลายหอมเก่า (แปรรูปเฉพาะทาง)
9. ปลายปลาทู (A1 Extra)

ตอบกลับมาเป็น JSON Format เท่านั้น โครงสร้างตามนี้ (ห้ามเว้นว่าง):
{{
  "today_date": "2026-08-26",
  "brent_price_est": "78.50",
  "fob_jasmine_est": "890",
  "fob_white5_est": "570",
  "fob_broken_est": "440",
  "market_trend": "🟢 Bullish (ขาขึ้น) / 🔴 Bearish (ขาลง) / 🟡 Sideways (แกว่งตัว)",
  "forecast_30d": "บทคาดการณ์ทิศทางราคาและซัพพลายใน 30-60 วันข้างหน้าอย่างละเอียด",
  "macro_analysis": "บทวิเคราะห์อัตราแลกเปลี่ยน โลจิสติกส์ และนโยบายคู่แข่ง",
  "risk_warning": "ความเสี่ยงวิกฤตที่ต้องเฝ้าระวัง (เช่น ภัยแล้ง, อินเดียเปิด/ปิดส่งออก, ค่าเงินผันผวน)",
  "grades_forecast": [
    {{
      "grade_name": "ข้าวหอมมะลิ (105/กข15)",
      "action": "🔴 MUST STOCK / 🟡 HOLD / 🟢 RELEASE",
      "shortage_risk": "HIGH / MEDIUM / LOW",
      "price_trend": "📈 ขึ้น / 📉 ลง / ➡️ ทรงตัว",
      "reason_forecast": "เหตุผลเชิงวิเคราะห์คาดการณ์ลึก (ปัจจัยดีมานด์ ซัพพลาย ค่าเงิน และจังหวะซื้อ)"
    }},
    {{
      "grade_name": "ข้าวออร์แกนิก (Organic Rice)",
      "action": "🔴 MUST STOCK / 🟡 HOLD / 🟢 RELEASE",
      "shortage_risk": "HIGH / MEDIUM / LOW",
      "price_trend": "📈 ขึ้น / 📉 ลง / ➡️ ทรงตัว",
      "reason_forecast": "เหตุผลเชิงวิเคราะห์และข้อแนะนำการเก็บในคลังความเย็น"
    }},
    {{
      "grade_name": "ข้าวปทุมธานี",
      "action": "🔴 MUST STOCK / 🟡 HOLD / 🟢 RELEASE",
      "shortage_risk": "HIGH / MEDIUM / LOW",
      "price_trend": "📈 ขึ้น / 📉 ลง / ➡️ ทรงตัว",
      "reason_forecast": "เหตุผลเชิงวิเคราะห์และทิศทางราคา"
    }},
    {{
      "grade_name": "ข้าวห้า (ข้าวขาว 5% ใหม่)",
      "action": "🔴 MUST STOCK / 🟡 HOLD / 🟢 RELEASE",
      "shortage_risk": "HIGH / MEDIUM / LOW",
      "price_trend": "📈 ขึ้น / 📉 ลง / ➡️ ทรงตัว",
      "reason_forecast": "เหตุผลเชิงวิเคราะห์การแข่งขันกับเวียดนาม/อินเดีย"
    }},
    {{
      "grade_name": "ข้าวห้าเก่า (Premium Margin)",
      "action": "🔴 MUST STOCK / 🟡 HOLD / 🟢 RELEASE",
      "shortage_risk": "HIGH / MEDIUM / LOW",
      "price_trend": "📈 ขึ้น / 📉 ลง / ➡️ ทรงตัว",
      "reason_forecast": "เหตุผลประเมินส่วนต่างราคา Premium Margin ข้าวเก่าขาดแคลน"
    }},
    {{
      "grade_name": "ข้าวเหนียว",
      "action": "🔴 MUST STOCK / 🟡 HOLD / 🟢 RELEASE",
      "shortage_risk": "HIGH / MEDIUM / LOW",
      "price_trend": "📈 ขึ้น / 📉 ลง / ➡️ ทรงตัว",
      "reason_forecast": "เหตุผลประเมินซัพพลายภาคเหนือ/อีสาน"
    }},
    {{
      "grade_name": "ปลายหอม (ปลายใหม่)",
      "action": "🔴 MUST STOCK / 🟡 HOLD / 🟢 RELEASE",
      "shortage_risk": "HIGH / MEDIUM / LOW",
      "price_trend": "📈 ขึ้น / 📉 ลง / ➡️ ทรงตัว",
      "reason_forecast": "เหตุผลและดีมานด์อุตสาหกรรมแปรรูป"
    }},
    {{
      "grade_name": "ปลายหอมเก่า (แปรรูปเฉพาะทาง)",
      "action": "🔴 MUST STOCK / 🟡 HOLD / 🟢 RELEASE",
      "shortage_risk": "HIGH / MEDIUM / LOW",
      "price_trend": "📈 ขึ้น / 📉 ลง / ➡️ ทรงตัว",
      "reason_forecast": "เหตุผลความต้องการเฉพาะกลุ่มแป้ง/เส้นก๋วยเตี๋ยว"
    }},
    {{
      "grade_name": "ปลายปลาทู (A1 Extra)",
      "action": "🔴 MUST STOCK / 🟡 HOLD / 🟢 RELEASE",
      "shortage_risk": "HIGH / MEDIUM / LOW",
      "price_trend": "📈 ขึ้น / 📉 ลง / ➡️ ทรงตัว",
      "reason_forecast": "เหตุผลดีมานด์โรงงานอาหารสัตว์และส่งออกแอฟริกา"
    }}
  ]
}}
"""

res = None
for attempt in range(3):
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        res = json.loads(response.text)
        print("✅ Data Analysis & Forecasting Generated Successfully!")
        break
    except Exception as e:
        print(f"⚠️ Retrying API Call (Attempt {attempt+1}/3)... Error: {e}")
        time.sleep(5)

if not res:
    raise Exception("❌ Failed to retrieve analytical data from Gemini API.")

# ==========================================
# 4. บันทึกข้อมูลลง Google Sheets
# ==========================================
print("📝 Updating Analytics & Forecasts into Google Sheets...")

sheet.worksheet("Daily_Input").append_row([
    res.get('today_date'), usd_thb, res.get('brent_price_est'),
    res.get('fob_jasmine_est'), res.get('fob_white5_est'), res.get('fob_broken_est'),
    res.get('macro_analysis')
])

gf = res.get('grades_forecast', [])
sheet.worksheet("AI_Output").append_row([
    res.get('today_date'), res.get('market_trend'), res.get('forecast_30d'),
    res.get('macro_analysis'), res.get('risk_warning'),
    json.dumps(gf, ensure_ascii=False)
])

dash = sheet.worksheet("Dashboard")
dash.update('B3', [[usd_thb]])
dash.update('D3', [[res.get('brent_price_est')]])
dash.update('F3', [[res.get('market_trend')]])
dash.update('B6', [[f"📌 บทคาดการณ์ 30-60 วัน: {res.get('forecast_30d')}\n\n🌐 ปัจจัย Macro & โลจิสติกส์: {res.get('macro_analysis')}\n\n⚠️ เตือนความเสี่ยง: {res.get('risk_warning')}"]])

dashboard_rows = []
for g in gf:
    dashboard_rows.append([
        g.get('grade_name'),
        g.get('action'),
        g.get('shortage_risk'),
        g.get('price_trend'),
        g.get('reason_forecast')
    ])

dash.update('B10:F18', dashboard_rows)

print("🎉 Executive Forecast & Data Analysis Complete!")
