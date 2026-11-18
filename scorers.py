import re
import math
from typing import Dict, List, Any
import pandas as pd


# ==========================================
# ابزارهای نرمال‌سازی متن، اعداد و شماره تماس
# ==========================================

PERSIAN_TO_EN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def to_en_digits(val: Any) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    return str(val).translate(PERSIAN_TO_EN_DIGITS)


def normalize_phone(val: Any) -> str:
    s = re.sub(r"\D", "", to_en_digits(val))
    if len(s) >= 10:
        return s[-10:]
    return s


def format_phone_display(norm_phone: str) -> str:
    if len(norm_phone) == 10 and norm_phone.startswith("9"):
        return "0" + norm_phone
    return norm_phone or "-"


def normalize_name(val: Any) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    s = str(val).strip()
    s = s.replace("ي", "ی").replace("ك", "ک").replace("\u200c", "")
    s = re.sub(r"\s+", "", s)
    return s


def clean_text(val: Any) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    s = str(val).replace("ي", "ی").replace("ك", "ک").strip()
    s = re.sub(r"[ \t]+", " ", s)
    return s


def clean_multiline_text(val: Any) -> str:
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return ""
    s = str(val).replace("ي", "ی").replace("ك", "ک").strip()
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in s.splitlines()]
    lines = [ln for ln in lines if ln]
    return "\n".join(lines)


def clean_national_id(val: Any) -> str:
    s = re.sub(r"\D", "", to_en_digits(val))
    if not s:
        return ""
    if 8 <= len(s) < 10:
        s = s.zfill(10)
    return s


def extract_porsline_rows(file_obj) -> pd.DataFrame:
    """خواندن خروجی پرس‌لاین و عبور خودکار از ردیف‌های سرستون ادغام‌شده"""
    df = pd.read_excel(file_obj, header=None, dtype=str)
    valid_indices = []
    for idx, row in df.iterrows():
        c0 = clean_text(row.iloc[0]) if len(row) > 0 else ""
        c2 = clean_text(row.iloc[2]) if len(row) > 2 else ""
        c3 = clean_text(row.iloc[3]) if len(row) > 3 else ""
        if idx >= 1 and (c0.startswith("http") or (c2 and normalize_phone(c3))):
            valid_indices.append(idx)
    if not valid_indices:
        return pd.DataFrame()
    return df.loc[valid_indices].reset_index(drop=True)


def extract_option_letter(val: Any) -> str:
    s = clean_text(val)
    if not s:
        return ""
    ch = s[0]
    if ch in ("ا", "آ"):
        return "الف"
    if ch == "ب":
        return "ب"
    if ch == "ج":
        return "ج"
    return ""


# ==========================================
# ۱. تست هوش چندگانه گاردنر (۸۰ سوالی)
# ==========================================

GARDNER_NAMES = [
    ("linguistic", "کلامی - زبانی"),
    ("logical", "منطقی - ریاضی"),
    ("spatial", "دیداری - فضایی"),
    ("kinesthetic", "بدنی - جنبشی"),
    ("interpersonal", "میان‌فردی"),
    ("intrapersonal", "درون‌فردی"),
    ("musical", "موسیقیایی"),
    ("naturalistic", "طبیعت‌گرا"),
]


def score_gardner_row(row: pd.Series) -> Dict[str, Any]:
    sums = [0] * 8
    for q_idx in range(80):
        col = 5 + q_idx
        if col < len(row):
            raw_val = to_en_digits(row.iloc[col]).strip()
            try:
                num = int(float(raw_val))
            except (ValueError, TypeError):
                num = 0
            if 1 <= num <= 5:
                sums[q_idx % 8] += num

    items = []
    for i, (key, title) in enumerate(GARDNER_NAMES):
        score = sums[i]
        pct = round((score / 50.0) * 100, 1)
        items.append({
            "key": key,
            "name": title,
            "score": score,
            "max_score": 50,
            "percent": pct,
        })

    ranked = sorted(items, key=lambda x: x["score"], reverse=True)
    return {
        "items": items,
        "ranked": ranked,
        "top3": ranked[:3],
        "date": clean_text(row.iloc[86]) if len(row) > 86 else "",
    }


# ==========================================
# ۲. تست رغبت شغلی هالند SDS (۲۲۶ گویه)
# ==========================================

HOLLAND_DOMAINS = [
    ("R", "واقع‌گرا (R)", "واقع‌گرا"),
    ("I", "جستجوگر (I)", "جستجوگر"),
    ("A", "هنری (A)", "هنری"),
    ("S", "اجتماعی (S)", "اجتماعی"),
    ("E", "متهور/کارآفرین (E)", "متهور"),
    ("C", "قراردادی (C)", "قراردادی"),
]


def score_holland_row(row: pd.Series) -> Dict[str, Any]:
    scores = {"R": 0, "S": 0, "I": 0, "E": 0, "A": 0, "C": 0}
    breakdown = {k: {"activities": 0, "competencies": 0, "occupations": 0, "self_est": 0} for k in scores}

    part1_ranges = [
        ("R", 5, 16),
        ("S", 16, 27),
        ("I", 27, 38),
        ("E", 38, 48),
        ("A", 48, 58),
        ("C", 58, 69),
    ]
    for code, start, end in part1_ranges:
        for col in range(start, end):
            if col < len(row) and clean_text(row.iloc[col]):
                scores[code] += 1
                breakdown[code]["activities"] += 1

    order = ["R", "S", "I", "E", "A", "C"]
    for idx, code in enumerate(order):
        start = 69 + idx * 11
        for col in range(start, start + 11):
            if col < len(row) and clean_text(row.iloc[col]):
                scores[code] += 1
                breakdown[code]["competencies"] += 1

    for idx, code in enumerate(order):
        start = 135 + idx * 14
        for col in range(start, start + 14):
            if col < len(row) and clean_text(row.iloc[col]):
                scores[code] += 1
                breakdown[code]["occupations"] += 1

    for offset in (219, 225):
        for idx, code in enumerate(order):
            col = offset + idx
            if col < len(row):
                try:
                    val = int(float(to_en_digits(row.iloc[col]).strip()))
                except (ValueError, TypeError):
                    val = 0
                if 1 <= val <= 7:
                    scores[code] += val
                    breakdown[code]["self_est"] += val

    max_possible = {"R": 50, "I": 50, "A": 49, "S": 50, "E": 49, "C": 50}
    items = []
    for code, full_title, short_title in HOLLAND_DOMAINS:
        sc = scores[code]
        mx = max_possible[code]
        items.append({
            "code": code,
            "name": full_title,
            "short_name": short_title,
            "score": sc,
            "max_score": mx,
            "percent": round((sc / mx) * 100, 1),
            "breakdown": breakdown[code],
        })

    ranked = sorted(items, key=lambda x: x["score"], reverse=True)
    holland_code = "".join(x["code"] for x in ranked[:3])
    holland_code_fa = " - ".join(x["short_name"] for x in ranked[:3])

    return {
        "code": holland_code,
        "code_fa": holland_code_fa,
        "items": items,
        "ranked": ranked,
        "date": clean_text(row.iloc[233]) if len(row) > 233 else "",
    }


# ==========================================
# ۳. تست شخصیت‌شناسی MBTI (۶۰ سوالی)
# ==========================================

MBTI_TYPE_TITLES = {
    "ISTJ": "بازرس / وظیفه‌شناس",
    "ISFJ": "حامی / مدافع",
    "INFJ": "مشاور / حامی آرمان‌گرا",
    "INTJ": "معمار / استراتژیست",
    "ISTP": "صنعت‌گر / تحلیل‌گر عمل‌گرا",
    "ISFP": "هنرمند / کاوشگر",
    "INFP": "واسطه / آرمان‌گرا",
    "INTP": "منطق‌دان / متفکر",
    "ESTP": "کارآفرین / عمل‌گرا",
    "ESFP": "سرگرم‌کننده / بازیگر",
    "ENFP": "مبارز / الهام‌بخش",
    "ENTP": "مناظره‌گر / مبتکر",
    "ESTJ": "مجری / مدیر اجرایی",
    "ESFJ": "کنسول / میزبان",
    "ENFJ": "سردمدار / مربی",
    "ENTJ": "فرمانده / راهبر",
}

MBTI_DIM_NAMES = {
    "E": "برون‌گرایی (E)",
    "I": "درون‌گرایی (I)",
    "S": "حسی (S)",
    "N": "شهودی (N)",
    "T": "منطقی (T)",
    "F": "احساسی (F)",
    "J": "قضاوتی/ساختارمند (J)",
    "P": "ادراکی/منعطف (P)",
}


def score_mbti_row(row: pd.Series) -> Dict[str, Any]:
    counts = {"E": 0, "I": 0, "S": 0, "N": 0, "T": 0, "F": 0, "J": 0, "P": 0}
    for q_num in range(1, 61):
        col = 7 + q_num
        if col >= len(row):
            continue
        letter = extract_option_letter(row.iloc[col])
        if letter not in ("الف", "ب"):
            continue
        mod = q_num % 4
        if mod == 1:
            counts["I" if letter == "الف" else "E"] += 1
        elif mod == 2:
            counts["S" if letter == "الف" else "N"] += 1
        elif mod == 3:
            counts["T" if letter == "الف" else "F"] += 1
        else:
            counts["P" if letter == "الف" else "J"] += 1

    pairs = [("E", "I"), ("S", "N"), ("T", "F"), ("J", "P")]
    mbti_type = ""
    pair_details = []
    for a, b in pairs:
        va, vb = counts[a], counts[b]
        total = max(va + vb, 1)
        dominant = a if va > vb else b
        mbti_type += dominant
        pair_details.append({
            "pair": f"{a}/{b}",
            "first": a,
            "second": b,
            "first_score": va,
            "second_score": vb,
            "first_pct": round(va / total * 100, 1),
            "second_pct": round(vb / total * 100, 1),
            "dominant": dominant,
        })

    radar_order = ["E", "S", "T", "J", "I", "N", "F", "P"]
    dimensions = []
    for k in radar_order:
        dimensions.append({
            "code": k,
            "name": MBTI_DIM_NAMES[k],
            "score": counts[k],
            "max_score": 15,
            "percent": round(counts[k] / 15.0 * 100, 1),
        })

    ranked = sorted(dimensions, key=lambda x: x["score"], reverse=True)
    return {
        "type": mbti_type,
        "type_title": MBTI_TYPE_TITLES.get(mbti_type, ""),
        "counts": counts,
        "dimensions": dimensions,
        "ranked": ranked,
        "pairs": pair_details,
        "date": clean_text(row.iloc[69]) if len(row) > 69 else "",
    }


# ==========================================
# ۴. تست هوش ریون (۶۰ سوالی)
# ==========================================

RAVEN_KEY = (
    [4, 5, 1, 2, 6, 3, 6, 2, 1, 3, 4, 5] +
    [2, 6, 1, 2, 1, 3, 5, 6, 4, 3, 4, 5] +
    [8, 2, 3, 8, 7, 4, 5, 1, 7, 6, 1, 2] +
    [3, 4, 3, 7, 8, 6, 5, 4, 1, 2, 5, 6] +
    [7, 6, 8, 2, 1, 5, 1, 6, 3, 2, 4, 5]
)


def score_raven_row(row: pd.Series) -> Dict[str, Any]:
    set_names = ["A", "B", "C", "D", "E"]
    set_scores = {s: 0 for s in set_names}
    answered = 0

    for idx in range(60):
        col = 6 + idx
        if col < len(row):
            raw = to_en_digits(row.iloc[col]).strip()
            try:
                ans = int(float(raw))
            except (ValueError, TypeError):
                ans = 0
            if ans > 0:
                answered += 1
                if ans == RAVEN_KEY[idx]:
                    set_scores[set_names[idx // 12]] += 1

    calc_total = sum(set_scores.values())
    porsline_score = None
    if len(row) > 66:
        try:
            porsline_score = int(float(to_en_digits(row.iloc[66]).strip()))
        except (ValueError, TypeError):
            porsline_score = None

    final_score = calc_total if answered > 0 else (porsline_score or 0)
    return {
        "raw_score": final_score,
        "max_score": 60,
        "percent": round((final_score / 60.0) * 100, 1),
        "sets": set_scores,
        "date": clean_text(row.iloc[68]) if len(row) > 68 else "",
    }


# ==========================================
# ۵. تست شخصیت کتل ۱۶ عاملی (۱۸۷ سوالی - فرم A)
# ==========================================

CATTELL_FACTORS_META = [
    ("A", "خونگرمی (A)", "گوشه‌گیر / سرد", "خونگرم / معاشرتی"),
    ("B", "استدلال‌گری / هوش (B)", "تفکر عینی", "تفکر انتزاعی"),
    ("C", "پایداری هیجانی (C)", "حساس / زودرنج", "باثبات / آرام"),
    ("E", "سلطه‌گری (E)", "مطیع / ملایم", "مسلط / قاطع"),
    ("F", "سرزندگی (F)", "جدی / خویشتن‌دار", "پرجوش / شاداب"),
    ("G", "قانون‌مداری (G)", "سهل‌گیر / بی‌قید", "باوجدان / پایبند"),
    ("H", "جسارت اجتماعی (H)", "کمرو / محتاط", "بی‌پروا / اجتماعی"),
    ("I", "حساسیت عاطفی (I)", "واقع‌بین / سرسخت", "لطیف / حساس"),
    ("L", "هوشیاری / بدبینی (L)", "خوش‌بین / پذیرا", "محتاط / شکاک"),
    ("M", "تخیل‌گرایی (M)", "عمل‌گرا / زمینی", "خیال‌پرداز / ذهنی"),
    ("N", "زیرکی اجتماعی (N)", "ساده / بی‌تکلف", "تودار / سیاست‌مدار"),
    ("O", "اضطراب و دغدغه (O)", "خونسرد / مطمئن", "نگران / خودسرزنش‌گر"),
    ("Q1", "گشودگی به تغییر (Q1)", "سنتی / محافظه‌کار", "تحول‌خواه / منتقد"),
    ("Q2", "اتکا به خود (Q2)", "گروه‌وابسته", "مستقل / خودکفا"),
    ("Q3", "کمال‌گرایی / انضباط (Q3)", "بی‌نظم / رها", "منظم / خودکنترل"),
    ("Q4", "تنش و فشار روانی (Q4)", "آرام / خونسرد", "پرتنش / بی‌قرار"),
]

CATTELL_KEY = {
    "A":  {"الف": [3, 52, 101, 126, 176], "ج": [26, 27, 51, 76, 151]},
    "C":  {"الف": [4, 30, 55, 104, 105, 130, 179], "ج": [5, 29, 79, 80, 129, 154]},
    "E":  {"الف": [7, 56, 131, 155, 156, 180, 181], "ج": [6, 31, 32, 57, 81, 106]},
    "F":  {"الف": [33, 58, 83, 132, 133, 182, 183], "ج": [8, 82, 107, 108, 157, 158]},
    "G":  {"الف": [109, 134, 160, 184, 185], "ج": [9, 34, 59, 84, 159]},
    "H":  {"الف": [10, 36, 110, 111, 135, 136, 186], "ج": [35, 60, 61, 85, 86, 161]},
    "I":  {"الف": [12, 37, 112, 138, 163], "ج": [11, 62, 87, 137, 162]},
    "L":  {"الف": [38, 88, 113, 114, 164], "ج": [13, 63, 64, 89, 139]},
    "M":  {"الف": [39, 40, 65, 91, 115, 116, 140], "ج": [14, 15, 90, 141, 165, 166]},
    "N":  {"الف": [17, 42, 117, 142, 167], "ج": [16, 41, 66, 67, 92]},
    "O":  {"الف": [18, 43, 69, 94, 118, 119, 143], "ج": [19, 44, 68, 93, 144, 168]},
    "Q1": {"الف": [20, 46, 70, 145, 169], "ج": [21, 45, 95, 120, 170]},
    "Q2": {"الف": [47, 71, 72, 146, 171], "ج": [22, 96, 97, 121, 122]},
    "Q3": {"الف": [48, 73, 98, 148, 173], "ج": [23, 24, 123, 147, 172]},
    "Q4": {"الف": [49, 50, 74, 99, 124, 149, 174], "ج": [25, 75, 100, 125, 150, 175]},
}

CATTELL_B_KEY = {
    28: "ب", 53: "ج", 54: "ب", 77: "ج", 78: "ب",
    102: "ج", 103: "الف", 127: "ج", 128: "الف",
    152: "الف", 153: "الف", 177: "ب", 178: "ب",
}

CATTELL_STEN_GENERAL = {
    "A":  [1, 1, 1, 2, 2, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    "B":  [1, 1, 2, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    "C":  [1, 1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 10, 10],
    "E":  [1, 1, 1, 1, 1, 2, 3, 3, 4, 5, 5, 6, 6, 7, 8, 8, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    "F":  [1, 1, 1, 1, 1, 1, 2, 2, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 10, 10, 10, 10],
    "G":  [1, 1, 1, 1, 1, 2, 2, 3, 4, 4, 5, 5, 6, 7, 7, 8, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    "H":  [1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 10, 10, 10, 10],
    "I":  [1, 1, 1, 1, 2, 3, 3, 4, 5, 5, 6, 6, 7, 8, 8, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    "L":  [1, 1, 2, 3, 3, 4, 5, 6, 6, 7, 8, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    "M":  [1, 1, 1, 1, 1, 1, 2, 2, 3, 4, 4, 5, 6, 6, 7, 8, 8, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10],
    "N":  [1, 1, 1, 1, 2, 2, 3, 4, 4, 5, 6, 6, 7, 8, 8, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    "O":  [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    "Q1": [1, 1, 1, 1, 2, 2, 3, 4, 5, 5, 6, 7, 7, 8, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    "Q2": [1, 1, 1, 1, 2, 3, 3, 4, 5, 5, 6, 7, 7, 8, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10],
    "Q3": [1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 7, 7, 8, 8, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10],
    "Q4": [1, 1, 1, 2, 2, 3, 3, 3, 4, 4, 5, 5, 6, 6, 6, 7, 7, 8, 8, 9, 9, 9, 10, 10, 10, 10, 10],
}

SECOND_ORDER_INTERPRETATIONS = {
    "برون‌گرایی": {
        "low": "نمرات پایین نشان‌دهنده تمایل به تنهایی و دوری از دیگران است؛ فرد ممکن است خجالتی و کمرو بوده و در تعامل با دیگران مشکل داشته باشد و فعالیت‌های فردی را ترجیح دهد.",
        "normal": "در حد تعادل؛ فرد هم توانایی برقراری ارتباط گرم با جمع را دارد و هم می‌تواند در موقعیت‌های فردی تمرکز کافی داشته باشد.",
        "high": "نمرات بالا نشان‌دهنده جمع‌گرایی، خونگرمی و روابط اجتماعی قوی است؛ فرد از ارتباط با دیگران لذت می‌برد و تمایل زیادی به انجام کارهای گروهی دارد.",
    },
    "اضطراب": {
        "low": "نمرات پایین نشان‌دهنده آرامش درونی، بی‌خیالی و نداشتن دلشوره نسبت به امور است؛ تاب‌آوری در برابر شرایط فشارزا و تغییرناپذیر بالاست.",
        "normal": "در حد تعادل؛ میزان نگرانی و حساسیت فرد در سطح متناسب با واقعیت‌های روزمره است و مانع عملکرد او نمی‌شود.",
        "high": "نمرات بالا نشان‌دهنده تنش درونی، زودرنجی و تحریک‌پذیری است؛ فرد ممکن است در برابر ناکامی‌ها بی‌قرار شود که نیازمند توجه در مدیریت استرس است.",
    },
    "حساسیت": {
        "low": "نمرات پایین نشان‌دهنده خونسردی، انعطاف‌پذیری و راحتی در جمع است؛ فرد دیدگاه واقع‌بینانه‌تری در برخورد با مسائل دارد.",
        "normal": "در حد تعادل؛ فرد تعادل خوبی بین منطق، قاطعیت و ملاحظه عواطف برقرار می‌کند.",
        "high": "نمرات بالا نشان‌دهنده حساسیت بالا و زودرنجی است؛ فرد ممکن است به موضوعات عاطفی واکنش سریع‌تری نشان دهد و نیازمند حمایت عاطفی در تصمیم‌گیری‌ها باشد.",
    },
    "سازگاری": {
        "low": "نمرات پایین نشان‌دهنده میل به همراهی و تبعیت در روابط است؛ فرد به راحتی با خواسته‌های دیگران کنار می‌آید و از تقابل پرهیز می‌کند.",
        "normal": "در حد تعادل؛ فرد ضمن احترام به جمع، در مواقع لزوم می‌تواند نظر مستقل خود را نیز حفظ کند.",
        "high": "نمرات بالا نشان‌دهنده جدیت، مقرراتی بودن و قاطعیت در روابط بین‌فردی است؛ فرد بر اصول خود پافشاری دارد و انعطاف کمتری در برابر خواسته‌های غیرمنطقی نشان می‌دهد.",
    },
    "کنترل": {
        "low": "نمرات پایین نشان‌دهنده شتابزدگی، تکانشگری و ضعف در کنترل هیجانات یا تمایلات آنی است؛ در برنامه‌ریزی بلندمدت نیازمند ساختار بیرونی است.",
        "normal": "در حد تعادل؛ فرد توانایی مناسبی در مدیریت هیجانات و عمل به وظایف روزمره دارد.",
        "high": "نمرات بالا نشان‌دهنده پختگی، خودکنترلی قوی و توانایی بالا در مدیریت تمایلات و هیجانات است؛ فرد با برنامه و انضباط درونی عمل می‌کند.",
    },
    "سنت‌گرا": {
        "low": "نمرات پایین نشان‌دهنده تفکر انتقادی، نوگرایی و تمایل به تحول است؛ فرد ایده‌های جدید را به راحتی می‌پذیرد و از چارچوب‌های ثابت فراتر می‌رود.",
        "normal": "در حد تعادل؛ فرد هم به تجربه‌های ارزشمند گذشته احترام می‌گذارد و هم در برابر تغییرات منطقی منعطف است.",
        "high": "نمرات بالا نشان‌دهنده احتیاط، پایبندی به ارزش‌ها، سنت‌ها و چارچوب‌های مرسوم است؛ فرد تغییرهای ناگهانی را با تردید می‌پذیرد.",
    },
    "مدیریت": {
        "low": "نمرات پایین نشان‌دهنده احساس وابستگی و تردید در پذیرش نقش‌های رهبری است؛ فرد ممکن است اعتماد به نفس کافی برای هدایت جمع نداشته باشد.",
        "normal": "در حد تعادل؛ فرد در محیط‌های آشنا توان مدیریت و همکاری را دارد اما لزوماً به دنبال سلطه‌گری نیست.",
        "high": "نمرات بالا نشان‌دهنده عزت نفس، احساس شایستگی و توانمندی در رهبری است؛ فرد در موقعیت‌های چالشی مسئولیت‌پذیر و تصمیم‌گیر است.",
    },
    "تخیل": {
        "low": "نمرات پایین نشان‌دهنده واقع‌گرایی، عمل‌گرایی و تبعیت از روش‌های مرسوم و اثبات‌شده است؛ فرد کارهای ملموس و مشخص را ترجیح می‌دهد.",
        "normal": "در حد تعادل؛ فرد ترکیب مناسبی از واقع‌بینی عملی و قدرت ایده‌پردازی دارد.",
        "high": "نمرات بالا نشان‌دهنده خلاقیت، ایده‌پردازی، نگاه هنری و توان ارائه راهکارهای نوآورانه است؛ فرد به مفاهیم انتزاعی علاقه زیادی دارد.",
    },
}


def score_cattell_row(row: pd.Series) -> Dict[str, Any]:
    answers = {}
    for item_num in range(3, 188):
        col = item_num + 12
        answers[item_num] = extract_option_letter(row.iloc[col]) if col < len(row) else ""

    raw_scores = {}
    b_score = 0
    for q_num, correct_ans in CATTELL_B_KEY.items():
        if answers.get(q_num) == correct_ans:
            b_score += 1
    raw_scores["B"] = b_score

    for factor, key_dict in CATTELL_KEY.items():
        sc = 0
        all_items = set(key_dict["الف"]) | set(key_dict["ج"])
        for q_num in key_dict["الف"]:
            if answers.get(q_num) == "الف":
                sc += 2
        for q_num in key_dict["ج"]:
            if answers.get(q_num) == "ج":
                sc += 2
        for q_num in all_items:
            if answers.get(q_num) == "ب":
                sc += 1
        raw_scores[factor] = sc

    sten_scores = {}
    for factor, raw in raw_scores.items():
        idx = max(0, min(26, raw))
        sten_scores[factor] = CATTELL_STEN_GENERAL[factor][idx]

    primary_factors = []
    for code, title, low_desc, high_desc in CATTELL_FACTORS_META:
        st = sten_scores[code]
        level = "پایین" if st <= 3 else ("بالا" if st >= 8 else "متوسط")
        primary_factors.append({
            "code": code,
            "name": title,
            "raw": raw_scores[code],
            "sten": st,
            "low_pole": low_desc,
            "high_pole": high_desc,
            "level": level,
        })

    s = sten_scores
    gender = clean_text(row.iloc[7]) if len(row) > 7 else ""
    is_male = "مرد" in gender

    extraversion = (11 + 2 * s["A"] + 3 * s["E"] + 4 * s["F"] + 5 * s["H"] - 2 * s["Q2"]) / 10.0
    anxiety = (38 + 2 * s["L"] + 3 * s["O"] + 4 * s["Q4"] - 2 * s["C"] - 2 * s["H"] - 2 * s["Q3"]) / 10.0
    if is_male:
        sensitivity = (77 + 2 * s["C"] + 2 * s["E"] + 2 * s["F"] + 2 * s["N"] - 4 * s["A"] - 6 * s["I"] - 2 * s["M"]) / 10.0
    else:
        sensitivity = (74 + 3 * s["E"] + 3 * s["F"] + 2 * s["N"] - 4 * s["A"] - 4 * s["I"] - 2 * s["M"] - 2 * s["L"]) / 10.0
    adjustment = (40 + 2 * s["C"] + 3 * s["G"] + 2 * s["N"] - 2 * s["A"] - 2 * s["E"] - 2 * s["F"] - 2 * s["H"] - 2 * s["Q1"]) / 10.0
    control = (33 + 2 * s["G"] + 2 * s["N"] + 2 * s["Q3"] - 2 * s["E"] - 2 * s["F"] - 2 * s["H"] - 2 * s["Q1"]) / 10.0
    traditional = (40 + 2 * s["Q1"] + 2 * s["Q3"] + 3 * s["I"] - s["Q2"] - 2 * s["A"] - 2 * s["G"] - s["L"]) / 10.0
    leadership = (27 + 3 * s["B"] + 2 * s["C"] + 5 * s["G"] + 5 * s["H"] + 5 * s["Q3"] - 3 * s["F"] - 4 * s["I"] - 3 * s["M"] - 4 * s["O"] - 2 * s["Q4"]) / 10.0
    imagination = (27 + 4 * s["B"] + 2 * s["I"] + 2 * s["M"] + 2 * s["Q1"] + 4 * s["Q2"] - 4 * s["A"] - 2 * s["E"] - 3 * s["F"] - 2 * s["N"]) / 10.0

    raw_second_order = [
        ("برون‌گرایی", extraversion),
        ("اضطراب", anxiety),
        ("حساسیت", sensitivity),
        ("سازگاری", adjustment),
        ("کنترل", control),
        ("سنت‌گرا", traditional),
        ("مدیریت", leadership),
        ("تخیل", imagination),
    ]

    second_order = []
    for name, val in raw_second_order:
        score_12 = max(1, min(12, int(round(val))))
        if score_12 <= 4:
            band = "low"
            band_fa = "پایین (۱-۴)"
        elif score_12 <= 8:
            band = "normal"
            band_fa = "نرمال (۵-۸)"
        else:
            band = "high"
            band_fa = "بالا (۹-۱۲)"
        second_order.append({
            "name": name,
            "score": score_12,
            "band": band,
            "band_fa": band_fa,
            "description": SECOND_ORDER_INTERPRETATIONS[name][band],
        })

    caution_flags = sum([
        s["Q4"] > 6,
        s["Q3"] < 4,
        s["O"] > 5,
        s["L"] > 4,
        s["H"] < 6,
        s["C"] < 3,
    ])
    caution_warning = caution_flags > 4

    exec_date = clean_text(row.iloc[12]) if len(row) > 12 else ""
    end_date = clean_text(row.iloc[201]) if len(row) > 201 else ""

    return {
        "primary_factors": primary_factors,
        "sten_scores": sten_scores,
        "second_order": second_order,
        "caution_warning": caution_warning,
        "gender": gender,
        "date": exec_date or end_date,
    }


# ==========================================
# ۶. فرم شناخت فردی، اهداف و سبک زندگی
# ==========================================

INTAKE_FIELDS = [
    (5, "هدف اصلی از زندگی و مسیر پیش رو", True),
    (6, "آرزوها و چشم‌انداز بلندمدت", True),
    (7, "الگوها و شخصیت‌های الهام‌بخش", False),
    (8, "برنامه آینده و مسیر دستیابی به هدف", True),
    (14, "مشاغل و رشته‌های مورد علاقه", False),
    (15, "برنامه علمی و تحصیلی", False),
    (9, "برنامه روزانه و هفتگی", True),
    (10, "نحوه گذران اوقات فراغت", False),
    (11, "منابع مطالعاتی", False),
    (12, "افراد و منابع حجت‌ساز (مرجع فکری)", False),
    (13, "نگرش سیاسی و اجتماعی", False),
    (16, "معرفی خانواده", True),
    (17, "معرفی دوستان", True),
    (18, "صفات اخلاقی از نگاه خود فرد", True),
    (19, "نقاط قوت و ضعف از نگاه خود فرد", True),
    (20, "نقاط قوت و ضعف از دیدگاه دیگران", True),
]


def score_intake_row(row: pd.Series) -> Dict[str, Any]:
    fields = []
    for col_idx, label, is_wide in INTAKE_FIELDS:
        val = clean_multiline_text(row.iloc[col_idx]) if col_idx < len(row) else ""
        fields.append({
            "label": label,
            "value": val if val else "پاسخی ثبت نشده است.",
            "wide": is_wide or len(val) > 140,
        })
    return {
        "fields": fields,
        "date": clean_text(row.iloc[22]) if len(row) > 22 else "",
    }


# ==========================================
# تجمیع و تطبیق ۶ فایل اکسل بر اساس موبایل/نام
# ==========================================

def merge_client_tests(
    gardner_file=None,
    holland_file=None,
    mbti_file=None,
    cattell_file=None,
    raven_file=None,
    intake_file=None,
) -> List[Dict[str, Any]]:
    clients: Dict[str, Dict[str, Any]] = {}

    def get_or_create_client(name: str, phone: str, nid: str = "") -> Dict[str, Any]:
        norm_ph = normalize_phone(phone)
        norm_nm = normalize_name(name)
        key = norm_ph if norm_ph else f"name:{norm_nm}"

        if key not in clients and norm_nm:
            for existing_key, cdata in clients.items():
                if normalize_name(cdata["full_name"]) == norm_nm:
                    key = existing_key
                    break

        if key not in clients:
            clients[key] = {
                "key": key,
                "full_name": clean_text(name) or "نامشخص",
                "phone": format_phone_display(norm_ph),
                "national_id": clean_national_id(nid),
                "date": "",
                "gardner": None,
                "holland": None,
                "mbti": None,
                "cattell": None,
                "raven": None,
                "intake": None,
            }
        else:
            if not clients[key]["national_id"] and nid:
                clients[key]["national_id"] = clean_national_id(nid)
            if (not clients[key]["full_name"] or clients[key]["full_name"] == "نامشخص") and name:
                clients[key]["full_name"] = clean_text(name)
            if clients[key]["phone"] == "-" and norm_ph:
                clients[key]["phone"] = format_phone_display(norm_ph)
        return clients[key]

    def update_date(client: Dict[str, Any], test_date: str):
        if test_date:
            short_d = test_date.split("-")[0].strip()
            if short_d > client["date"]:
                client["date"] = short_d

    if gardner_file is not None:
        df = extract_porsline_rows(gardner_file)
        for _, row in df.iterrows():
            c = get_or_create_client(row.iloc[2], row.iloc[3], row.iloc[4] if len(row) > 4 else "")
            res = score_gardner_row(row)
            c["gardner"] = res
            update_date(c, res["date"])

    if holland_file is not None:
        df = extract_porsline_rows(holland_file)
        for _, row in df.iterrows():
            c = get_or_create_client(row.iloc[2], row.iloc[3], row.iloc[4] if len(row) > 4 else "")
            res = score_holland_row(row)
            c["holland"] = res
            update_date(c, res["date"])

    if mbti_file is not None:
        df = extract_porsline_rows(mbti_file)
        for _, row in df.iterrows():
            c = get_or_create_client(row.iloc[2], row.iloc[3], row.iloc[4] if len(row) > 4 else "")
            res = score_mbti_row(row)
            c["mbti"] = res
            update_date(c, res["date"])

    if cattell_file is not None:
        df = extract_porsline_rows(cattell_file)
        for _, row in df.iterrows():
            c = get_or_create_client(row.iloc[2], row.iloc[3], row.iloc[11] if len(row) > 11 else "")
            res = score_cattell_row(row)
            c["cattell"] = res
            update_date(c, res["date"])

    if raven_file is not None:
        df = extract_porsline_rows(raven_file)
        for _, row in df.iterrows():
            c = get_or_create_client(row.iloc[2], row.iloc[3], "")
            res = score_raven_row(row)
            c["raven"] = res
            update_date(c, res["date"])

    if intake_file is not None:
        df = extract_porsline_rows(intake_file)
        for _, row in df.iterrows():
            c = get_or_create_client(row.iloc[2], row.iloc[3], row.iloc[4] if len(row) > 4 else "")
            res = score_intake_row(row)
            c["intake"] = res
            update_date(c, res["date"])

    return list(clients.values())