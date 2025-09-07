
# -*- coding: utf-8 -*-
import re, json, os, unicodedata, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE_DIR, "keywords_config.json")

def load_config():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_digits(text: str) -> str:
    table = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬", "0123456789..")
    text = text.translate(table)
    text = unicodedata.normalize("NFKC", text)
    return text

def extract_amount(text: str):
    text = text.replace(",", ".")
    patterns = [
        r'(?:SAR|ر\.?س|ريال|RS|S\.?R\.?)\s*([0-9]+(?:\.[0-9]+)?)',
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:SAR|ر\.?س|ريال|RS|S\.?R\.?)',
        r'مبلغ(?:\s*وقدره)?\s*([0-9]+(?:\.[0-9]+)?)',
        r'([0-9]+(?:\.[0-9]+)?)\s*(?:ريالاً|ريال)'
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except:
                pass
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)', text)
    if m:
        return float(m.group(1))
    return None

def guess_type(text: str, income_keywords, saving_keywords):
    if any(k in text for k in income_keywords):
        return "Income"
    if any(k in text for k in saving_keywords):
        return "Saving"   # نوع ثالث
    expense_cues = ["خصم", "سحب", "شراء", "تم الشراء", "دفعة", "مدفوع"]
    if any(k in text for k in expense_cues):
        return "Expense"
    return "Expense"


def guess_category(text: str, categories_map):
    t = text.lower()
    for cat, kws in categories_map.items():
        for k in kws:
            if k.lower() in t:
                return cat
    if "محطة" in text or "بنزين" in text:
        return "Transport"
    if "صيدلية" in text:
        return "Health & Fitness"
    return "Misc"

def guess_account(text: str):
    if "الراجحي" in text or "Rajhi" in text:
        return "AlRajhi"
    if "الأهلي" in text or "اهلي" in text or "AlAhli" in text:
        return "AlAhli"
    if "Tekmoo" in text or "تيكمو" in text:
        return "Tekmoo"
    return "Main"

def guess_payment_method(text: str):
    if "بطاقة" in text or "مدى" in text or "Visa" in text or "Mastercard" in text:
        return "Card"
    if "تحويل" in text or "حوالة" in text:
        return "Bank Transfer"
    if "نقدي" in text:
        return "Cash"
    return "Card"

def extract_merchant(text: str):
    m = re.search(r'(?:في|من)\s+([^\n\r\.\-،:]+)', text)
    if m:
        return m.group(1).strip()[:40]
    m = re.search(r'\b([A-Z][A-Za-z0-9&\-\s]{2,})\b', text)
    if m:
        return m.group(1).strip()[:40]
    return ""

def classify_message(message: str):
    cfg = load_config()
    text = normalize_digits(message)
    amount = extract_amount(text) or 0.0
    tx_type = guess_type(text, cfg.get("income_keywords", []))
    account = guess_account(text)
    payment_method = guess_payment_method(text)
    merchant = extract_merchant(text)
    category = guess_category(text, cfg.get("categories", {}))
    signed = amount if tx_type == "Income" else -abs(amount)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return {
        "date": today,
        "account": account,
        "merchant": merchant,
        "category": category,
        "payment_method": payment_method,
        "amount": signed,
        "type": tx_type,
        "raw": message
    }
