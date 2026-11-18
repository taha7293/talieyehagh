import os
import re
import io
import zipfile
from pathlib import Path
import pandas as pd
import streamlit as st

from scorers import merge_client_tests
from pdf_generator import (
    DEFAULT_INSTITUTE_NAME,
    load_default_logo_bytes,
    build_report_html,
    html_to_pdf_bytes,
)


IS_WINDOWS = hasattr(os, "startfile")
OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)


def safe_filename(text: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", text).strip().replace(" ", "_")


def get_app_password() -> str:
    try:
        if "APP_PASSWORD" in st.secrets:
            return str(st.secrets["APP_PASSWORD"])
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD", "")


st.set_page_config(
    page_title="سامانه استعدادسنجی طلیعه حق الیقین",
    page_icon="🌿",
    layout="wide",
)

st.markdown("""
<style>
    html, body, [class*="css"] { direction: rtl; text-align: right; font-family: Tahoma, sans-serif; }
</style>
""", unsafe_allow_html=True)

# قفل ورود در صورت تنظیم رمز در نسخه آنلاین
required_pw = get_app_password()
if required_pw:
    if not st.session_state.get("authenticated", False):
        st.title("🔐 ورود به سامانه استعدادسنجی طلیعه حق الیقین")
        pw_input = st.text_input("رمز عبور مشاورین را وارد کنید:", type="password")
        if st.button("ورود"):
            if pw_input == required_pw:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("رمز عبور اشتباه است.")
        st.stop()

st.title("🌿 سامانه تحلیل تست‌ها و فرم شناخت — مؤسسه فرهنگی طلیعه حق الیقین")
st.caption("فایل‌های اکسل خروجی پرس‌لاین را آپلود کنید؛ برنامه به صورت خودکار همه ۶ فایل را از روی شماره تماس (و نام) به هم متصل کرده و کارنامه جامع مشاوره تولید می‌کند.")

default_logo = load_default_logo_bytes()

with st.sidebar:
    st.header("تنظیمات ثابت گزارش")
    institute_name = st.text_input("نام مؤسسه", value=DEFAULT_INSTITUTE_NAME)

    if default_logo:
        st.success("✅ لوگوی پیش‌فرض مؤسسه فعال است.")
        st.image(default_logo, width=130)
    else:
        st.warning("برای نمایش دائمی لوگو، عکس لوگو را با نام logo.png در پوشه برنامه قرار دهید.")

    uploaded_logo = st.file_uploader("تغییر موقت لوگو (اختیاری)", type=["png", "jpg", "jpeg"])
    logo_bytes = uploaded_logo.read() if uploaded_logo else default_logo

    if IS_WINDOWS:
        st.divider()
        if st.button("📂 باز کردن پوشه خروجی‌ها"):
            os.startfile(OUTPUT_DIR)

r1c1, r1c2, r1c3 = st.columns(3)
with r1c1:
    f_gardner = st.file_uploader("۱. هوش چندگانه گاردنر", type=["xlsx"])
with r1c2:
    f_holland = st.file_uploader("۲. رغبت شغلی هالند", type=["xlsx"])
with r1c3:
    f_mbti = st.file_uploader("۳. تیپ شخصیتی MBTI", type=["xlsx"])

r2c1, r2c2, r2c3 = st.columns(3)
with r2c1:
    f_cattell = st.file_uploader("۴. شخصیت کتل (۱۸۷ سوالی)", type=["xlsx"])
with r2c2:
    f_raven = st.file_uploader("۵. هوش ریون", type=["xlsx"])
with r2c3:
    f_intake = st.file_uploader("۶. فرم شناخت فردی و اهداف", type=["xlsx"])

if any([f_gardner, f_holland, f_mbti, f_cattell, f_raven, f_intake]):
    clients = merge_client_tests(
        gardner_file=f_gardner,
        holland_file=f_holland,
        mbti_file=f_mbti,
        cattell_file=f_cattell,
        raven_file=f_raven,
        intake_file=f_intake,
    )

    st.success(f"تعداد {len(clients)} مراجع شناسایی و تطبیق داده شد.")

    summary_rows = []
    for c in clients:
        summary_rows.append({
            "نام و نام خانوادگی": c["full_name"],
            "شماره تماس": c["phone"],
            "کد ملی": c["national_id"] or "ندارد",
            "گاردنر": "✅" if c["gardner"] else "❌",
            "هالند": c["holland"]["code"] if c["holland"] else "❌",
            "MBTI": c["mbti"]["type"] if c["mbti"] else "❌",
            "کتل": "✅" if c["cattell"] else "❌",
            "ریون": f"{c['raven']['raw_score']}/60" if c["raven"] else "❌",
            "فرم شناخت": "✅" if c["intake"] else "❌",
        })

    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

    st.divider()
    col_dl1, col_dl2 = st.columns([1, 2])

    with col_dl1:
        if st.button("📦 ساخت همه PDFها (فایل ZIP)", type="primary"):
            zip_buffer = io.BytesIO()
            progress = st.progress(0)
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for idx, c in enumerate(clients):
                    html_doc = build_report_html(c, institute_name=institute_name, logo_bytes=logo_bytes)
                    pdf_data = html_to_pdf_bytes(html_doc)
                    fname = f"{safe_filename(c['full_name'])}_{c['phone']}.pdf"
                    if IS_WINDOWS:
                        (OUTPUT_DIR / fname).write_bytes(pdf_data)
                    zf.writestr(fname, pdf_data)
                    progress.progress((idx + 1) / len(clients))

            st.session_state["zip_bytes"] = zip_buffer.getvalue()
            if IS_WINDOWS:
                st.success("همه فایل‌ها داخل پوشه outputs ذخیره شدند!")
                os.startfile(OUTPUT_DIR)

        if st.session_state.get("zip_bytes"):
            st.download_button(
                label="⬇️ دانلود فایل ZIP همه گزارش‌ها",
                data=st.session_state["zip_bytes"],
                file_name="reports_all.zip",
                mime="application/zip",
            )

    with col_dl2:
        selected_idx = st.selectbox(
            "یا ساخت تکی برای یک مراجع:",
            options=range(len(clients)),
            format_func=lambda i: f"{clients[i]['full_name']} ({clients[i]['phone']})",
        )
        if st.button("📄 ساخت PDF همین مراجع"):
            target = clients[selected_idx]
            html_doc = build_report_html(target, institute_name=institute_name, logo_bytes=logo_bytes)
            pdf_data = html_to_pdf_bytes(html_doc)
            fname = f"{safe_filename(target['full_name'])}_{target['phone']}.pdf"
            st.session_state["single_pdf"] = (fname, pdf_data)
            if IS_WINDOWS:
                out_path = OUTPUT_DIR / fname
                out_path.write_bytes(pdf_data)
                st.success(f"فایل با نام {fname} در پوشه outputs ذخیره شد!")
                os.startfile(out_path)

        if st.session_state.get("single_pdf"):
            fname, pdf_data = st.session_state["single_pdf"]
            st.download_button(
                label=f"⬇️ دانلود PDF ({fname})",
                data=pdf_data,
                file_name=fname,
                mime="application/pdf",
            )
else:
    st.info("لطفاً فایل‌های اکسل پرس‌لاین را در بالا بارگذاری کنید.")