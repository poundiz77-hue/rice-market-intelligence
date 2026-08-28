import os
import re
import json
import time
import datetime
import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google import genai
from google.genai import types

# ===========================================================
# WHAT CHANGED FROM v1, AND WHY
# ===========================================================
# The old version asked Gemini to find FX / rice FOB prices via web
# search. Grounded search is *better than guessing* but it is still
# an LLM reading pages and summarizing -- it can misread a table or
ฃ#
# The Thai Rice Exporters Association (TREA) publishes an actual
# official weekly table -- FOB prices per grade AND the FX rate,
# sourced from the Bank of Thailand -- on a plain HTML page, free,
# no login: http://www.thairiceexporters.or.th/price.#
# So for FX and the grades that appear on that page, this version
ฃ# source itself.
#
# # HONEST LIMITS (please read before treating this as fully solved)# 1. That page updates WEEKLY, not daily. Confirmed != real-time.# 2. Only 4 of your 9 grades appear on the public page (Hom Mali,#    White 5%, Glutinous, A.1 Super broken). The#    feed wired up here. Oil could be added via a free-tier key from#    ask and I'll wire it in once you h# 4. TREA's page has no stable HTML classes/ids (it's an old-style
#    government/association site), so this scraper matches rows TREA_URL = "http://www.thairiceexporters.or.th/price.htm"
# Map: your internal 9 grades -> the label text TREA uses for the
# grades that ARE on the public page. Only add a mapping here once
# you've visually confirmed the label wording still matches the s   s"ข้าวหอมมะลิ (105/กข15)": ["Thai Hom Mali Rice - Premium (2025/26)"],
    "ข้าวขาว 5%": ["White Rice 5%"],
    "ข้าวเหนียว": ["White Glutinous Rice 10%"],
    "ปลายป [Premium Margin]",
    "ข้าวเหนียว",ข้าวเหนียว",
    "ปลายหอม (ใหม่)",
    "ปลายหอมเก่า (ตลาดแปรรูป)",
    "ปลายปลาทู (A1 Extra)",
]


# ---------------------------------------------------------
# 1. Scrape TREA official page for FX + confirmed grade prices
# ---------------------------------------------------------
def fetch_trea_soup():
    resp = requests.get(TREA_URL, timeout=20)
    resp.encoding = 'tis-620'  # this site is not UTF-8
    return BeautifulSoup(resp.text, 'html.parser')


def extract_latest_value(soup, keywords):
    """Find the row whose visible label contains one of `keywords`,
    return the right-most numeric column (= most recent week)."""
    for row in soup.find_all('tr'):
        cells = row.find_all(['h
        label = cells[0].get_text(strip=True)
        if any(kw in label for kw in keywords):
            numeric_cells = [c.get_text(strip=True) for c in cells[1:]]
            numeric_cells = [c for c in numeric_cells if re.match(r'^[\d.,]+$', c)]
            if numeric_cells:
                return numeric_cells[-1]
    return None


def get_trea_data():
    try:
        soup = fetch_trea_soup()
    except Exception as e:
        print(f"Could not reach TREA page ({e}) -- all fields fall back to AI estimate.")
        return {"fx_selling": None, "grades": {}}

    data = {"fx_selling": extract_latest_value(soup, ["Average Selling Rates"]), "grades": {}}
    for grade_name, keywords in TREA_GRADE_KEYWORDS.items():
        val = extract_latest_value(soup, keywords)
        data["grades"][grade_name] = val
        if val is None:
            print(f"WARNING: could not find a confirmed TREA price for '{grade_name}' "
                  f"-- label wording on the site may have changed, check manually.")
    return data


# ---------------------------------------------------------
# 2. Google Sheets Authorization & Setup (with retry)
# ---------------------------------------------------------
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
spreadsheet_id = os.environ.get("SPREADSHEET_ID")

sheet = None
for attempt in range(3):
    try:
        sheet = client.open_by_key(spreadsheet_id).worksheet("Dashboard")
        break
    except Exception as e:
        if attempt == 2:
            raise e
        print(f"Google Sheets API unavailable. Retrying in 5s... ({attempt+1}/3)")
        time.sleep(5)

# ---------------------------------------------------------
# 3. Gemini client + retry wrapper (used ONLY for narrative + the
#    5 grades TREA doesn't publish -- never for FX or the 4 confirmed
#    grades)
# ---------------------------------------------------------
ai_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
search_tool = types.Tool(google_search=types.GoogleSearch())


# Minimum gap enforced BEFORE every call, regardless of success/failure.
# This is preventive -- it spaces out the 6-7 calls this script makes per
# run so we don't burst past a per-minute rate limit in the first place.
# Tune this up if you're still seeing 429s after adding it (e.g. 20-30s
# on a very restrictive free-tier key).
MIN_SECONDS_BETWEEN_CALLS = 12
_last_call_time = [0.0]


def call_gemini(prompt, model='gemini-3.6-flash', use_search=True, temperature=0.2, max_retries=5):
    config_kwargs = {"temperature": temperature}
    if use_search:
        config_kwargs["tools"] = [search_tool]

    last_err = None
    for attempt in range(max_retries):
        # Preventive spacing: always wait out the minimum gap since the
        # last call landed, success or failure, before trying again.
        elapsed = time.time() - _last_call_time[0]
        if elapsed < MIN_SECONDS_BETWEEN_CALLS:
            time.sleep(MIN_SECONDS_BETWEEN_CALLS - elapsed)

        try:
            result = ai_client.models.generate_content(
                model=model, contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs)
            )
            _last_call_time[0] = time.time()
            return result
        except Exception as e:
            _last_call_time[0] = time.time()
            last_err = e
            err_text = str(e)

            if "429" in err_text or "RESOURCE_EXHAUSTED" in err_text:
                # Rate/quota limit -- back off hard and increasing, since a
                # quick retry will almost certainly hit the same wall.
                # If this is a full DAILY quota (not just per-minute), no
                # amount of backoff here will fix it -- it'll keep failing
                # every attempt, and the real fix is enabling billing or
                # waiting for the daily reset.
                backoff = 20 * (attempt + 1)
                print(f"Gemini rate/quota limit hit (attempt {attempt+1}/{max_retries}). "
                      f"Waiting {backoff}s before retry. Detail: {err_text[:200]}")
                time.sleep(backoff)
            else:
                print(f"Gemini call failed ({attempt+1}/{max_retries}): {err_text[:200]}")
                time.sleep(4)
    raise last_err


current_year = datetime.datetime.now().year
today_str = datetime.datetime.now().strftime("%d/%m/%Y")

trea = get_trea_data()
confirmed_fx = trea["fx_selling"]
confirmed_grades = trea["grades"]  # grade_name -> price string or None

# Fallback: only ask Gemini to *guess* FX if TREA scrape truly failed.
# This keeps a confirmed number in front of estimated ones at every step.
if confirmed_fx:
    current_fx = confirmed_fx
    fx_source_label = "Confirmed (TREA, sourced from Bank of Thailand)"
else:
    fallback = call_gemini(
        f"วันนี้ {today_str} ใช้ Google Search หา THB/USD ล่าสุด ตอบแค่ตัวเลข", temperature=0.0
    )
    current_fx = fallback.text.strip() if hasattr(fallback, 'text') else "N/A"
    fx_source_label = "AI Estimate (unconfirmed -- TREA page unreachable)"

print(f"FX: {current_fx} [{fx_source_label}]")

# ---------------------------------------------------------
# 4. Global research, split by topic -- each grounded call digs into
#    ONE domain instead of one call trying to cover everything at
#    once (which in practice means it searches each topic shallowly).
#    Every sub-call is asked for short, factual bullet findings, not
#    prose -- that's what gets combined in the synthesis step below.
# ---------------------------------------------------------
RESEARCH_TOPICS = {
    "oil_and_freight": f"""
วันนี้ {today_str}. ใช้ Google Search หาข้อมูลล่าสุด (เช็คว่าไม่ใช่ข่าวเก่าที่พ้นสมัย) เกี่ยวกับ:
- ราคาน้ำมันดิบ Brent ปัจจุบันและทิศทางช่วง 1-2 เดือนข้างหน้า
- ค่าระวางเรือ (Container/Bulk Freight Rate) เส้นทางเอเชีย-ตะวันออกกลาง/แอฟริกา และแนวโน้ม
ตอบเป็น bullet สั้นๆ 3-5 บรรทัด ระบุตัวเลขและวันที่ของข้อมูลที่เจอ พร้อมชื่อแหล่งข่าวท้ายแต่ละ bullet
""",
    "competitor_policy": f"""
วันนี้ {today_str}. ใช้ Google Search หาข่าว/นโยบายล่าสุด (ไม่ใช่ข่าวเก่าที่พ้นสมัยหรือถูกยกเลิกไปแล้ว) เกี่ยวกับ:
- นโยบายส่งออกข้าวล่าสุดของอินเดีย (ภาษี, โควตา, ข้อจำกัดส่งออก)
- นโยบายส่งออกข้าวล่าสุดของเวียดนาม (ราคาขาย, ปริมาณ, ข้อตกลงการค้า)
ตอบเป็น bullet สั้นๆ 3-5 บรรทัด ระบุวันที่ของข่าวและชื่อแหล่งข่าวท้ายแต่ละ bullet
""",
    "global_macro": f"""
วันนี้ {today_str}. ใช้ Google Search หาข้อมูลล่าสุดเกี่ยวกับ:
- ทิศทางเศรษฐกิจโลก/ดอกเบี้ยธนาคารกลางสหรัฐ (Fed) ที่กระทบค่าเงินดอลลาร์
- เหตุการณ์ภูมิรัฐศาสตร์สำคัญที่กระทบห่วงโซ่อุปทานอาหารโลกตอนนี้
ตอบเป็น bullet สั้นๆ 3-5 บรรทัด ระบุวันที่และแหล่งข่าวท้ายแต่ละ bullet
""",
    "weather_and_crop": f"""
วันนี้ {today_str}. ใช้ Google Search หาข้อมูลล่าสุดเกี่ยวกับ:
- สถานะ El Niño/La Niña ปัจจุบันและผลกระทบต่อผลผลิตข้าวในเอเชีย (ไทย, เวียดนาม, อินเดีย)
- ปริมาณผลผลิตข้าวเปลือกเข้าโรงสีในไทยฤดูกาลปัจจุบัน
ตอบเป็น bullet สั้นๆ 3-5 บรรทัด ระบุวันที่และแหล่งข่าวท้ายแต่ละ bullet
""",
}

research_findings = {}
for topic_key, topic_prompt in RESEARCH_TOPICS.items():
    resp = call_gemini(topic_prompt, use_search=True, temperature=0.0)
    research_findings[topic_key] = resp.text.strip() if hasattr(resp, 'text') else "(no data returned)"
    print(f"--- {topic_key} ---\n{research_findings[topic_key]}\n")

# ---------------------------------------------------------
# 5. Synthesis call -- NO web search here. This step only reasons
#    over what was already found above plus the TREA-confirmed
#    numbers, so the executive summary can't quietly introduce a
#    number that wasn't actually grounded in one of the research
#    calls.
# ---------------------------------------------------------
synthesis_prompt = f"""
คุณคือ Chief Agricultural Economist & Strategic Supply Chain Director ประจำอุตสาหกรรมข้าวไทยระดับสถาบัน
วันนี้คือ {today_str} (ปี {current_year})

ข้อมูลยืนยันแล้ว:
- อัตราแลกเปลี่ยน: {current_fx} THB/USD ({fx_source_label})

ผลการวิจัยที่ทีมงานค้นมาให้แล้ว (ใช้เฉพาะข้อมูลนี้ ห้ามเติมตัวเลขหรือข้อเท็จจริงใหม่ที่ไม่ได้อยู่ในนี้):

[น้ำมันและค่าระวางเรือ]
{research_findings['oil_and_freight']}

[นโยบายคู่แข่ง อินเดีย/เวียดนาม]
{research_findings['competitor_policy']}

[เศรษฐกิจมหภาคโลก]
{research_findings['global_macro']}

[สภาพอากาศและผลผลิต]
{research_findings['weather_and_crop']}

จากข้อมูลทั้งหมดข้างต้น เขียนบทวิเคราะห์ระดับผู้บริหาร (Executive Briefing) ความยาว 5-7 บรรทัด
สรุปทิศทางตลาดข้าวโลกและระบุ Top Must-Stock Pick พร้อมเหตุผลที่อ้างอิงจากข้อมูลข้างต้นเท่านั้น
"""
macro_response = call_gemini(synthesis_prompt, use_search=False, temperature=0.2)

# ---------------------------------------------------------
# 5. Grade table: use TREA numbers where confirmed, AI estimate
#    (clearly labeled) for the rest
# ---------------------------------------------------------
unconfirmed_grades = [g for g in ALL_GRADES if g not in confirmed_grades or confirmed_grades[g] is None]

grade_prompt = f"""
วันนี้คือ {today_str}
อัตราแลกเปลี่ยนยืนยันแล้ว: {current_fx} THB/USD

ใช้ Google Search ประเมินกลยุทธ์สินค้าคงคลังและราคาสำหรับข้าวเกรดต่อไปนี้เท่านั้น (ห้ามรวมเกรดอื่นนอกลิสต์นี้):
{chr(10).join(f"- {g}" for g in unconfirmed_grades)}

ตอบกลับเป็น JSON Array เท่านั้น ห้ามมีข้อความอื่น ห้ามใส่ ``` แต่ละรายการมี key:
grade_name, market_status ("Tight"/"Balanced"/"Surplus"), fob_forecast, strategy_action, target_markets
"""
grid_response = call_gemini(grade_prompt, use_search=True, temperature=0.1)

# ---------------------------------------------------------
# 6. Assemble final table: confirmed rows first, then AI-estimated
#    rows, each tagged so nobody confuses one for the other
# ---------------------------------------------------------
table_rows = []

for grade_name, keywords in TREA_GRADE_KEYWORDS.items():
    price = confirmed_grades.get(grade_name)
    if price:
        table_rows.append([
            grade_name, "-", f"{price} USD/MT (TREA confirmed)",
            "See confirmed price", "TREA weekly bulletin"
        ])

try:
    raw_text = grid_response.text.strip() if hasattr(grid_response, 'text') else ""
    clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.MULTILINE).strip()
    ai_items = json.loads(clean_json)
    for item in ai_items:
        table_rows.append([
            item.get("grade_name", "") + " (AI Estimate)",
            item.get("market_status", ""),
            item.get("fob_forecast", ""),
            item.get("strategy_action", ""),
            item.get("target_markets", "")
        ])
except Exception as e:
    print(f"Could not parse AI grade estimates: {e}")
    print(grid_response.text if hasattr(grid_response, 'text') else "(no text)")

# ---------------------------------------------------------
# 7. Write to sheet
# ---------------------------------------------------------
sheet.batch_clear(['A5', 'C5', 'E5', 'A8', 'A22:E30'])
sheet.update('A5', [[f"{current_fx} ({fx_source_label})"]])
if hasattr(macro_response, 'text') and macro_response.text:
    sheet.update('A8', [[macro_response.text]])
if table_rows:
    sheet.update(f'A22:E{22 + len(table_rows) - 1}', table_rows)

print("Done. Confirmed vs AI-estimated rows are labeled in column A of the grade table.")
