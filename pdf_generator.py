import os
import html
import base64
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from charts import (
    svg_radar_chart,
    svg_bar_chart,
    svg_line_chart,
    eslimi_rosette_svg,
    eslimi_corner_svg,
)


DEFAULT_INSTITUTE_NAME = "مؤسسه فرهنگی طلیعه حق الیقین"


def load_default_logo_bytes() -> Optional[bytes]:
    base_dir = Path(__file__).parent
    for fname in ("logo.png", "logo.jpg", "logo.jpeg", "logo.webp"):
        p = base_dir / fname
        if p.exists():
            return p.read_bytes()
    return None


def _page_header(title: str, subtitle: str, logo_html: str) -> str:
    return f"""
    <div class="header-bar">
        <div class="header-corner-right">{eslimi_corner_svg(flip_x=True, flip_y=False)}</div>
        <div class="header-text">
            <div class="inst-title">{html.escape(title)}</div>
            <div class="doc-subtitle">{subtitle}</div>
        </div>
        <div class="header-logo">{logo_html}</div>
    </div>
    """


def build_report_html(
    client: Dict[str, Any],
    institute_name: str = DEFAULT_INSTITUTE_NAME,
    logo_bytes: Optional[bytes] = None,
) -> str:
    name = html.escape(client.get("full_name", "-"))
    nid = html.escape(client.get("national_id") or "ثبت نشده")
    phone = html.escape(client.get("phone") or "-")
    date = html.escape(client.get("date") or "-")

    if logo_bytes is None:
        logo_bytes = load_default_logo_bytes()

    logo_html = ""
    if logo_bytes:
        b64 = base64.b64encode(logo_bytes).decode("ascii")
        logo_html = f'<img src="data:image/png;base64,{b64}" class="logo-img" alt="logo"/>'

    rosette = eslimi_rosette_svg("#0e7490", "#16a34a")
    rosette_green = eslimi_rosette_svg("#15803d", "#0d9488")

    # ----- متن معرفی و راهنمای صفحه اول -----
    intro_html = """
    <div class="intro-box">
        <div class="bismillah">بسمه تعالی</div>
        <p class="intro-p">
            استعدادسنجی فرایندی است که شخص طی آن با ویژگی‌های مثبت و منفی شخصیتی خود و یا به عبارتی با نقاط ضعف و قوت خود آشنا می‌شود و با این خودشناسی سراغ انتخاب مسیر تحصیلی یا شغلی‌ای می‌رود که در آن توانمندی دارد و احتمال موفقیت در آن برایش بیشتر از سایر گزینه‌هاست. استعدادسنجی محدود به سن خاصی نیست و همه افراد در هر سن و شغل و موقعیتی که باشند می‌توانند این مشاوره را انجام دهند؛ اما در برخی از برهه‌های زندگی این کار ضروری به نظر می‌رسد از جمله انتخاب رشته پایه نهم و همچنین انتخاب رشته دانشگاه.
            مؤسسه طلیعه حق الیقین با همکاری مشاوران با تجربه در کنار شماست تا با انجام این فرایند بتوانید انتخاب‌های درستی در شکل‌گیری مسیر تحصیلی، شغلی و در نهایت مسیر زندگی خود داشته باشید.
        </p>
        <p class="intro-p" style="margin-bottom: 0;">
            <b>شیوه انجام استعدادسنجی:</b> مشاوره استعدادسنجی طی فرایند پاسخگویی به چند تست معتبر شخصیت‌شناسی و هوش انجام می‌شود. فرد همچنین با تکمیل فرم خودشناسی به نتیجه‌گیری دقیق‌تر جلسه کمک می‌کند و در پایان، طی یک جلسه مصاحبه، نتیجه فرایند به شخص ارائه خواهد شد.
        </p>
    </div>

    <div class="tips-green">
        <div><span class="tip-icon-ok">✔</span> لطفاً قبل از انجام هر تست قوانین و شیوه انجام آن را مطالعه کنید.</div>
        <div><span class="tip-icon-ok">✔</span> زمانی آزمون را انجام دهید که تمرکز کافی دارید و خسته نیستید.</div>
        <div><span class="tip-icon-ok">✔</span> روی هر سوال بیش از ۳۰ ثانیه مکث نکنید و نخستین پاسخ ذهنی را انتخاب کنید.</div>
    </div>

    <div class="tips-warn">
        <div><span class="tip-icon-no">✖</span> تست‌ها را توصیفی پاسخ دهید، یعنی آنچه واقعاً درباره شما صدق می‌کند، نه آنچه پسندیده‌تر است.</div>
        <div><span class="tip-icon-no">✖</span> در تست کتل فقط در ۸ تا ۹ مورد مجاز به انتخاب گزینه «ب» هستید.</div>
        <div><span class="tip-icon-note">✦</span> پاسخ‌ها باید بدون اثرگذاری عوامل بیرونی مانند فرهنگ، قومیت و مذهب ارائه شوند.</div>
    </div>
    """

    # ----- بخش ریون -----
    raven = client.get("raven")
    if raven:
        raven_html = f"""
        <div class="raven-box">
            <div class="raven-score-circle">
                <span class="big-num">{raven['raw_score']}</span>
                <span class="sub-num">از ۶۰ امتیاز</span>
            </div>
            <div class="raven-details">
                <div class="raven-title">نتیجه آزمون هوش غیرکلامی ریون (SPM)</div>
                <div class="progress-track">
                    <div class="progress-fill" style="width:{raven['percent']}%"></div>
                </div>
                <div class="raven-sets">
                    <span>سری A: <b>{raven['sets']['A']}/12</b></span>
                    <span>سری B: <b>{raven['sets']['B']}/12</b></span>
                    <span>سری C: <b>{raven['sets']['C']}/12</b></span>
                    <span>سری D: <b>{raven['sets']['D']}/12</b></span>
                    <span>سری E: <b>{raven['sets']['E']}/12</b></span>
                </div>
            </div>
        </div>
        """
    else:
        raven_html = '<div class="empty-msg">اطلاعات آزمون هوش ریون برای این مراجع ثبت نشده است.</div>'

    # ----- بخش هالند -----
    holland = client.get("holland")
    if holland:
        h_labels = [x["short_name"] for x in holland["items"]]
        h_vals = [x["score"] for x in holland["items"]]
        h_bar_svg = svg_bar_chart(h_labels, h_vals, max_val=50, width=420, height=220)
        h_rows = "".join(
            f"""<tr>
                <td><b>{x['name']}</b></td>
                <td>{x['breakdown']['activities']}</td>
                <td>{x['breakdown']['competencies']}</td>
                <td>{x['breakdown']['occupations']}</td>
                <td>{x['breakdown']['self_est']}</td>
                <td class="highlight-cell">{x['score']}</td>
            </tr>"""
            for x in holland["ranked"]
        )
        holland_html = f"""
        <div class="badge-row">
            <span>کد رغبت شغلی نمونه:</span>
            <span class="code-badge teal" dir="ltr">{holland['code']}</span>
            <span class="code-badge-fa">({holland['code_fa']})</span>
        </div>
        <div class="two-col">
            <div class="col-table">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>حوزه شغلی</th>
                            <th>فعالیت</th>
                            <th>تجربه</th>
                            <th>مشاغل</th>
                            <th>خودارزیابی</th>
                            <th>کل</th>
                        </tr>
                    </thead>
                    <tbody>{h_rows}</tbody>
                </table>
            </div>
            <div class="col-chart">{h_bar_svg}</div>
        </div>
        """
    else:
        holland_html = '<div class="empty-msg">اطلاعات آزمون رغبت شغلی هالند ثبت نشده است.</div>'

    # ----- بخش MBTI -----
    mbti = client.get("mbti")
    if mbti:
        m_labels = [x["code"] for x in mbti["dimensions"]]
        m_vals = [x["score"] for x in mbti["dimensions"]]
        m_radar_svg = svg_radar_chart(m_labels, m_vals, max_val=15, color="#0284c7", width=330, height=255, rings=3)
        m_rows = "".join(
            f"""<tr>
                <td>{i + 1}</td>
                <td><b>{x['name']}</b></td>
                <td>{x['score']} از ۱۵</td>
                <td>{x['percent']}٪</td>
            </tr>"""
            for i, x in enumerate(mbti["ranked"])
        )
        mbti_html = f"""
        <div class="badge-row">
            <span>تیپ شخصیتی غالب:</span>
            <span class="code-badge blue" dir="ltr">{mbti['type']}</span>
            <span class="code-badge-fa">({mbti['type_title']})</span>
        </div>
        <div class="two-col">
            <div class="col-chart">{m_radar_svg}</div>
            <div class="col-table">
                <table class="data-table">
                    <thead>
                        <tr><th>رتبه</th><th>شاخص</th><th>امتیاز</th><th>درصد</th></tr>
                    </thead>
                    <tbody>{m_rows}</tbody>
                </table>
            </div>
        </div>
        """
    else:
        mbti_html = '<div class="empty-msg">اطلاعات آزمون شخصیت MBTI ثبت نشده است.</div>'

    # ----- بخش گاردنر -----
    gardner = client.get("gardner")
    if gardner:
        g_labels = [x["name"] for x in gardner["items"]]
        g_vals = [x["score"] for x in gardner["items"]]
        g_radar_svg = svg_radar_chart(g_labels, g_vals, max_val=50, color="#0d9488", width=360, height=260, rings=5)
        g_short_labels = ["کلامی", "منطقی", "فضایی", "بدنی", "میان‌فردی", "درون‌فردی", "موسیقی", "طبیعت‌گرا"]
        g_line_svg = svg_line_chart(g_short_labels, g_vals, min_val=0, max_val=50, color="#15803d", width=540, height=215, y_step=10)
        g_rows = "".join(
            f"""<tr>
                <td><b>{x['name']}</b></td>
                <td>{x['score']} از ۵۰</td>
                <td>{x['percent']}٪</td>
            </tr>"""
            for x in gardner["ranked"]
        )
        gardner_html = f"""
        <div class="two-col">
            <div class="col-table">
                <table class="data-table">
                    <thead><tr><th>نوع هوش</th><th>امتیاز</th><th>درصد</th></tr></thead>
                    <tbody>{g_rows}</tbody>
                </table>
            </div>
            <div class="col-chart">{g_radar_svg}</div>
        </div>
        <div class="chart-wide" style="margin-top: 14px;">
            <div class="mini-caption">نمودار خطی مقایسه توزیع هوش‌های هشت‌گانه</div>
            {g_line_svg}
        </div>
        """
    else:
        gardner_html = '<div class="empty-msg">اطلاعات آزمون هوش چندگانه گاردنر ثبت نشده است.</div>'

    # ----- بخش کتل -----
    cattell = client.get("cattell")
    if cattell:
        c_labels = [x["code"] for x in cattell["primary_factors"]]
        c_vals = [x["sten"] for x in cattell["primary_factors"]]
        c_line_svg = svg_line_chart(
            c_labels, c_vals, min_val=1, max_val=10, color="#0e7490",
            normal_band=(4, 7), width=680, height=205, y_step=1
        )

        c_cells_top = "".join(f"<th>{x['code']}</th>" for x in cattell["primary_factors"])
        c_cells_sten = "".join(f"<td><b>{x['sten']}</b></td>" for x in cattell["primary_factors"])

        so_cards = "".join(
            f"""<div class="so-card band-{x['band']}">
                <div class="so-head">
                    <span class="so-name">{x['name']}</span>
                    <span class="so-score">امتیاز: {x['score']} از ۱۲ &nbsp;|&nbsp; {x['band_fa']}</span>
                </div>
                <div class="so-desc">{x['description']}</div>
            </div>"""
            for x in cattell["second_order"]
        )
        warn_html = '<div class="warn-box">تذکر بالینی: بر اساس الگوی پاسخ‌دهی شاخص‌های اضطراب و کنترل، توصیه می‌شود این نیمرخ با احتیاط تفسیر شود.</div>' if cattell["caution_warning"] else ""

        cattell_html = f"""
        {warn_html}
        <div class="chart-wide">
            <div class="mini-caption">نمودار خطی نیمرخ ۱۶ عامل کتل (بخش فیروزه‌ای کمرنگ: محدوده میانگین ۴ تا ۷)</div>
            {c_line_svg}
            <table class="sten-strip">
                <tr><th>عامل</th>{c_cells_top}</tr>
                <tr><th>تراز</th>{c_cells_sten}</tr>
            </table>
        </div>
        <h3 class="sub-sec-title">تحلیل توصیفی عوامل مرتبه دوم کتل</h3>
        <div class="so-grid">{so_cards}</div>
        """
    else:
        cattell_html = '<div class="empty-msg">اطلاعات آزمون شخصیت ۱۶ عاملی کتل ثبت نشده است.</div>'

    # ----- بخش فرم شناخت فردی (اکسل ششم) -----
    intake = client.get("intake")
    if intake:
        qa_cards = []
        for item in intake["fields"]:
            span_cls = "qa-wide" if item["wide"] else ""
            safe_val = html.escape(item["value"]).replace("\n", "<br/>")
            qa_cards.append(
                f"""<div class="qa-card {span_cls}">
                    <div class="qa-q">{html.escape(item['label'])}</div>
                    <div class="qa-a">{safe_val}</div>
                </div>"""
            )
        intake_html = f'<div class="qa-grid">{"".join(qa_cards)}</div>'
    else:
        intake_html = '<div class="empty-msg">فرم شناخت فردی، اهداف و سبک زندگی برای این مراجع ثبت نشده است.</div>'

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8"/>
<title>پرونده جامع استعدادسنجی - {name}</title>
<style>
    @import url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
    @page {{
        size: A4 portrait;
        margin: 10mm 12mm;
    }}
    * {{
        box-sizing: border-box;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }}
    body {{
        font-family: Vazirmatn, 'Noto Sans Arabic', Nazli, Tahoma, 'Segoe UI', Arial, sans-serif;
        color: #1e293b;
        margin: 0;
        padding: 0;
        font-size: 10.8px;
        line-height: 1.55;
        background: #ffffff;
    }}
    .page {{
        page-break-after: always;
        position: relative;
        border: 1.5px solid #99f6e4;
        border-radius: 12px;
        padding: 12px 14px;
        background: linear-gradient(180deg, #f0fdfa 0%, #ffffff 100px);
    }}
    .page:last-child {{
        page-break-after: auto;
    }}
    .header-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 10px;
        padding-bottom: 8px;
        margin-bottom: 11px;
        border-bottom: 2px solid #0d9488;
    }}
    .header-corner-right {{
        width: 46px;
        height: 46px;
        flex-shrink: 0;
    }}
    .header-text {{
        flex: 1;
        text-align: center;
    }}
    .header-logo {{
        min-width: 65px;
        text-align: left;
    }}
    .inst-title {{
        font-size: 16px;
        font-weight: 900;
        color: #0f4c5c;
    }}
    .doc-subtitle {{
        font-size: 10.5px;
        font-weight: 600;
        color: #0d9488;
        margin-top: 2px;
    }}
    .logo-img {{
        max-height: 56px;
        max-width: 82px;
        object-fit: contain;
    }}
    .info-grid {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
        background: linear-gradient(135deg, #ecfeff 0%, #f0fdf4 100%);
        border: 1.5px solid #5eead4;
        border-radius: 9px;
        padding: 8px 12px;
        margin-bottom: 10px;
    }}
    .info-item span {{
        display: block;
        font-size: 9px;
        color: #0f766e;
        font-weight: 600;
    }}
    .info-item b {{
        font-size: 11.5px;
        color: #0f172a;
    }}
    .intro-box {{
        background: #ffffff;
        border: 1px solid #bae6fd;
        border-right: 4px solid #0e7490;
        border-radius: 9px;
        padding: 10px 14px;
        margin-bottom: 9px;
    }}
    .bismillah {{
        text-align: center;
        font-size: 13px;
        font-weight: 900;
        color: #0f4c5c;
        margin-bottom: 6px;
    }}
    .intro-p {{
        margin: 0 0 7px 0;
        font-size: 10.2px;
        line-height: 1.68;
        text-align: justify;
        color: #1e293b;
    }}
    .tips-green {{
        background: #f0fdf4;
        border: 1px solid #86efac;
        border-right: 4px solid #16a34a;
        border-radius: 8px;
        padding: 7px 12px;
        margin-bottom: 8px;
        font-size: 10px;
        line-height: 1.65;
        color: #14532d;
    }}
    .tips-warn {{
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-right: 4px solid #dc2626;
        border-radius: 8px;
        padding: 7px 12px;
        margin-bottom: 10px;
        font-size: 10px;
        line-height: 1.65;
        color: #7f1d1d;
    }}
    .tip-icon-ok {{ color: #16a34a; font-weight: 900; margin-left: 5px; }}
    .tip-icon-no {{ color: #dc2626; font-weight: 900; margin-left: 5px; }}
    .tip-icon-note {{ color: #d97706; font-weight: 900; margin-left: 5px; }}
    .section {{
        border: 1px solid #bae6fd;
        border-top: 3px solid #0d9488;
        border-radius: 10px;
        padding: 10px 13px;
        margin-bottom: 11px;
        background: #ffffff;
    }}
    .sec-title {{
        display: flex;
        align-items: center;
        margin: 0 0 9px 0;
        font-size: 13px;
        font-weight: 800;
        color: #0f4c5c;
        padding-bottom: 5px;
        border-bottom: 1px dashed #99f6e4;
    }}
    .sub-sec-title {{
        margin: 10px 0 6px 0;
        font-size: 11.8px;
        font-weight: 800;
        color: #0f766e;
    }}
    .raven-box {{
        display: flex;
        align-items: center;
        gap: 16px;
        background: linear-gradient(135deg, #ecfeff 0%, #f0fdf4 100%);
        border: 1px solid #99f6e4;
        border-radius: 9px;
        padding: 9px 14px;
    }}
    .raven-score-circle {{
        min-width: 92px;
        text-align: center;
        background: linear-gradient(135deg, #0e7490 0%, #15803d 100%);
        color: #fff;
        border-radius: 10px;
        padding: 7px 10px;
    }}
    .raven-score-circle .big-num {{
        display: block;
        font-size: 22px;
        font-weight: 900;
        line-height: 1.1;
    }}
    .raven-score-circle .sub-num {{
        font-size: 9.2px;
        opacity: 0.95;
    }}
    .raven-details {{ flex: 1; }}
    .raven-title {{ font-weight: 800; margin-bottom: 6px; color: #0f4c5c; }}
    .progress-track {{
        height: 10px;
        background: #ccfbf1;
        border-radius: 99px;
        overflow: hidden;
        margin-bottom: 7px;
    }}
    .progress-fill {{
        height: 100%;
        background: linear-gradient(90deg, #0284c7, #0d9488, #16a34a);
        border-radius: 99px;
    }}
    .raven-sets {{
        display: flex;
        justify-content: space-between;
        font-size: 10px;
        color: #334155;
    }}
    .badge-row {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 9px;
        font-size: 11.5px;
    }}
    .code-badge {{
        background: #0e7490;
        color: #fff;
        font-weight: 800;
        padding: 2px 13px;
        border-radius: 6px;
        font-size: 13px;
        letter-spacing: 1px;
    }}
    .code-badge.teal {{ background: linear-gradient(135deg, #0e7490, #0d9488); }}
    .code-badge.blue {{ background: linear-gradient(135deg, #0284c7, #0e7490); }}
    .code-badge-fa {{ font-weight: 700; color: #15803d; }}
    .two-col {{
        display: flex;
        align-items: center;
        gap: 12px;
    }}
    .col-table {{ flex: 1.15; }}
    .col-chart {{ flex: 1; text-align: center; }}
    .data-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 10px;
    }}
    .data-table th, .data-table td {{
        border: 1px solid #cbd5e1;
        padding: 4.5px 6px;
        text-align: center;
    }}
    .data-table th {{
        background: #ecfeff;
        color: #0f4c5c;
        font-weight: 800;
    }}
    .data-table td:first-child {{ text-align: right; }}
    .highlight-cell {{
        background: #f0fdf4;
        font-weight: 800;
        color: #15803d;
    }}
    .chart-wide {{
        margin-top: 8px;
        text-align: center;
    }}
    .mini-caption {{
        font-size: 10px;
        font-weight: 700;
        color: #0f766e;
        margin-bottom: 4px;
        text-align: right;
    }}
    .sten-strip {{
        width: 100%;
        border-collapse: collapse;
        font-size: 9.5px;
        margin-top: 4px;
    }}
    .sten-strip th, .sten-strip td {{
        border: 1px solid #99f6e4;
        padding: 3px 2px;
        text-align: center;
    }}
    .sten-strip th {{ background: #ecfeff; color: #0f4c5c; }}
    .so-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 7px;
    }}
    .so-card {{
        border: 1px solid #cbd5e1;
        border-radius: 7px;
        padding: 6px 9px;
        background: #f8fafc;
    }}
    .so-card.band-high {{ border-right: 4px solid #0284c7; background: #f0f9ff; }}
    .so-card.band-low {{ border-right: 4px solid #0d9488; background: #f0fdfa; }}
    .so-card.band-normal {{ border-right: 4px solid #16a34a; background: #f0fdf4; }}
    .so-head {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 3px;
    }}
    .so-name {{ font-weight: 800; font-size: 10.5px; color: #0f4c5c; }}
    .so-score {{ font-size: 9px; font-weight: 700; color: #334155; }}
    .so-desc {{ font-size: 9.2px; color: #334155; text-align: justify; }}
    .warn-box {{
        background: #fffbeb;
        border: 1px solid #fcd34d;
        color: #92400e;
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 10px;
        font-weight: 700;
        margin-bottom: 6px;
    }}
    .empty-msg {{
        color: #64748b;
        font-style: italic;
        padding: 12px;
        text-align: center;
        background: #f8fafc;
        border-radius: 6px;
    }}
    .qa-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
    }}
    .qa-card {{
        border: 1px solid #bae6fd;
        border-right: 3.5px solid #0d9488;
        border-radius: 7px;
        padding: 6px 9px;
        background: #fafefe;
        break-inside: avoid;
        page-break-inside: avoid;
    }}
    .qa-card.qa-wide {{
        grid-column: span 2;
        border-right-color: #15803d;
        background: #f9fefb;
    }}
    .qa-q {{
        font-size: 9.8px;
        font-weight: 800;
        color: #0e7490;
        margin-bottom: 3px;
    }}
    .qa-a {{
        font-size: 9.6px;
        color: #1e293b;
        text-align: justify;
        line-height: 1.5;
    }}
    .ws-box {{
        border: 1.5px solid #5eead4;
        border-right: 4.5px solid #0e7490;
        border-radius: 8px;
        padding: 8px 12px;
        margin-bottom: 11px;
        background: #ffffff;
    }}
    .ws-title {{
        font-weight: 800;
        font-size: 11.5px;
        color: #0f4c5c;
        margin-bottom: 5px;
        border-bottom: 1px dashed #99f6e4;
        padding-bottom: 4px;
    }}
    .write-line {{
        border-bottom: 1px dotted #94a3b8;
        height: 23px;
    }}
    .sign-row {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 24px;
        margin-top: 14px;
    }}
    .sign-box {{
        border: 1.5px dashed #0d9488;
        border-radius: 9px;
        height: 80px;
        padding: 8px 12px;
        font-weight: 800;
        color: #0f4c5c;
        background: #f0fdfa;
    }}
    .footer-ornament {{
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        margin-top: 6px;
    }}
</style>
</head>
<body>

<!-- صفحه ۱: شناسنامه + متن معرفی و راهنما + آزمون هوش ریون -->
<div class="page">
    {_page_header(institute_name, "پرونده تخصصی استعدادسنجی، رغبت شغلی و مشاوره تحصیلی", logo_html)}

    <div class="info-grid">
        <div class="info-item"><span>نام و نام خانوادگی مراجع</span><b>{name}</b></div>
        <div class="info-item"><span>کد ملی</span><b dir="ltr">{nid}</b></div>
        <div class="info-item"><span>شماره تماس</span><b dir="ltr">{phone}</b></div>
        <div class="info-item"><span>تاریخ</span><b dir="ltr">{date}</b></div>
    </div>

    {intro_html}

    <div class="section" style="margin-bottom: 0;">
        <h2 class="sec-title">{rosette} آزمون هوش غیرکلامی ریون</h2>
        {raven_html}
    </div>
</div>

<!-- صفحه ۲: رغبت شغلی هالند + MBTI -->
<div class="page">
    {_page_header(institute_name, f"تحلیل رغبت شغلی و تیپ شخصیت &nbsp;|&nbsp; مراجع: <b>{name}</b>", logo_html)}

    <div class="section">
        <h2 class="sec-title">{rosette_green} آزمون رغبت شغلی هالند (SDS)</h2>
        {holland_html}
    </div>

    <div class="section" style="margin-bottom: 0;">
        <h2 class="sec-title">{rosette} تیپ‌شناسی شخصیت (MBTI)</h2>
        {mbti_html}
    </div>
</div>

<!-- صفحه ۳: هوش‌های چندگانه گاردنر -->
<div class="page">
    {_page_header(institute_name, f"تحلیل هوش‌های چندگانه گاردنر &nbsp;|&nbsp; مراجع: <b>{name}</b>", logo_html)}

    <div class="section" style="margin-bottom: 0;">
        <h2 class="sec-title">{rosette_green} آزمون هوش‌های چندگانه گاردنر</h2>
        {gardner_html}
    </div>
</div>

<!-- صفحه ۴: کتل ۱۶ عاملی + تحلیل توصیفی عوامل مرتبه دوم -->
<div class="page">
    {_page_header(institute_name, f"نیمرخ ۱۶ عاملی شخصیت کتل &nbsp;|&nbsp; مراجع: <b>{name}</b>", logo_html)}

    <div class="section" style="margin-bottom: 0;">
        <h2 class="sec-title">{rosette} آزمون شخصیت ۱۶ عاملی کتل (16PF)</h2>
        {cattell_html}
    </div>
</div>

<!-- صفحه ۵: فرم شناخت فردی، اهداف و سبک زندگی -->
<div class="page">
    {_page_header(institute_name, f"فرم شناخت فردی، اهداف، ارزش‌ها و سبک زندگی &nbsp;|&nbsp; مراجع: <b>{name}</b>", logo_html)}

    <div class="section" style="margin-bottom: 0;">
        <h2 class="sec-title">{rosette_green} اطلاعات تکمیلی و خودارزیابی کیفی مراجع</h2>
        {intake_html}
    </div>
</div>

<!-- صفحه پایانی: کاربرگ جلسه مشاوره -->
<div class="page">
    {_page_header(institute_name, f"کاربرگ ثبت جمع‌بندی جلسه مشاوره &nbsp;|&nbsp; مراجع: <b>{name}</b> &nbsp;|&nbsp; کد ملی: <b>{nid}</b>", logo_html)}

    <div class="ws-box">
        <div class="ws-title">{rosette} جمع‌بندی و یادداشت مشاور</div>
        {''.join('<div class="write-line"></div>' for _ in range(7))}
    </div>

    <div class="ws-box">
        <div class="ws-title">{rosette_green} نتیجه نهایی جلسه</div>
        {''.join('<div class="write-line"></div>' for _ in range(4))}
    </div>

    <div class="ws-box">
        <div class="ws-title">{rosette} رشته‌های پیشنهادی</div>
        {''.join('<div class="write-line"></div>' for _ in range(4))}
    </div>

    <div class="ws-box">
        <div class="ws-title">{rosette_green} برنامه رشد و اقدام</div>
        {''.join('<div class="write-line"></div>' for _ in range(5))}
    </div>

    <div class="sign-row">
        <div class="sign-box">امضای مشاور:</div>
        <div class="sign-box">امضای مراجع:</div>
    </div>

    <div class="footer-ornament">
        <div>{eslimi_corner_svg(flip_x=True, flip_y=True)}</div>
        <div style="font-size:9px; color:#0f766e; font-weight:600;">{html.escape(institute_name)}</div>
        <div>{eslimi_corner_svg(flip_x=False, flip_y=True)}</div>
    </div>
</div>

</body>
</html>"""


def _find_chromium_executable() -> Optional[str]:
    candidates = [
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("msedge"),
        shutil.which("chrome"),
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return None


def html_to_pdf_bytes(html_content: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = Path(tmpdir) / "report.html"
        pdf_path = Path(tmpdir) / "report.pdf"
        profile_dir = Path(tmpdir) / "profile"
        html_path.write_text(html_content, encoding="utf-8")

        browser = _find_chromium_executable()
        if browser:
            cmd = [
                browser,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                f"--user-data-dir={profile_dir}",
                "--virtual-time-budget=3000",
                f"--print-to-pdf={pdf_path}",
                "--no-pdf-header-footer",
                html_path.as_uri(),
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pdf_path.exists():
                return pdf_path.read_bytes()

        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b = p.chromium.launch()
                page = b.new_page()
                page.goto(html_path.as_uri(), wait_until="networkidle")
                pdf_bytes = page.pdf(format="A4", print_background=True)
                b.close()
                return pdf_bytes
        except Exception as exc:
            raise RuntimeError(
                "مرورگر Chromium/Edge/Chrome برای ساخت PDF پیدا نشد."
            ) from exc