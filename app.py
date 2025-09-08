# -*- coding: utf-8 -*-
import sys, os
sys.path.append(os.path.dirname(__file__))  # يضمن استيراد classifier من نفس المجلد

import csv
from datetime import datetime, date
import pandas as pd
import streamlit as st
import plotly.express as px
from classifier import classify_message

# ===== إعداد الصفحة =====
st.set_page_config(page_title="نظام الميزانية", page_icon="📊", layout="wide")
st.markdown("""
<style>
/* الحاوية العامة */
.block-container{max-width:1080px;padding-top:12px}

/* كارت بإطار أبيض بسيط */
.card{
  border:1px solid rgba(255,255,255,.35);
  border-radius:6px;
  padding:18px 18px 14px;
  background:rgba(255,255,255,.02);
  position:relative;
  margin-bottom:14px;
}

/* سهم صغير يسار أعلى الكارد */
.card:before{
  content:"›"; position:absolute; left:10px; top:8px;
  font-size:22px; color:#fff; opacity:.9;
  transform:translateY(-2px);
}

/* عنوان الصفحة داخل الكارد */
.page-title{
  text-align:center; font-weight:800; font-size:22px;
  letter-spacing:.5px; margin:4px 0 14px;
}

/* تسميات بسيطة يمين/يسار */
.subline{opacity:.85; font-size:14px; margin:2px 0 10px}

/* صف أزرار الشكل المرسوم */
.btn-row{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 4px}
.btn{
  border:1px solid rgba(255,255,255,.45);
  background:transparent; color:#fff;
  padding:6px 12px; border-radius:6px; cursor:pointer;
  font-size:14px;
}
.btn:hover{background:rgba(255,255,255,.08)}
.btn-primary{border-color:#a78bfa}

/* ميتريكس مبسطة على سطرين */
.metric-line{display:flex;gap:28px;flex-wrap:wrap;margin:8px 0}
.metric{min-width:220px;opacity:.95}
.metric .lbl{opacity:.75}
.metric .val{font-weight:800;font-size:18px;margin-top:2px}

/* فاصل رأسي للتاب 3 */
.two-pane{display:grid;grid-template-columns:340px 1fr;gap:16px}
.vsplit{width:1px;background:rgba(255,255,255,.35);height:100%;margin:auto}
.small{font-size:13px;opacity:.8}
</style>
""", unsafe_allow_html=True)

# ===== مسارات =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "sample_transactions.csv")

# ===== تهيئة ملف CSV لو مهو موجود =====
if not os.path.exists(CSV_PATH):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date","account","merchant","category","payment_method","amount","type","raw"]
        )
        writer.writeheader()

# ===== فلاتر عربية للسجل (حسب رسمك) =====
AR_FILTERS = {
    "التفاصيل": None,  # يعرض الكل
    "الطوارئ": ["Savings & Investment"],  # ادخار/استثمار
    "التمتع": ["Entertainment", "Food & Coffee", "Travel", "Shopping"],
    "الالتزامات": ["Internet & Phone", "Transport", "Education", "Health & Fitness", "Gifts & Family"]
}

# ===== مبالغ جاهزة (Presets) لكل تصنيف - نخزنها بالجلسة ونقدر نعدلها من الواجهة =====
DEFAULT_PRESETS = {
    "Food & Coffee": 20.0,
    "Shopping": 50.0,
    "Entertainment": 30.0,
    "Travel": 100.0,
    "Internet & Phone": 20.0,
    "Transport": 25.0,
    "Education": 20.0,
    "Health & Fitness": 20.0,
    "Gifts & Family": 25.0,
    "Savings & Investment": 100.0,
    "Misc": 10.0
}
for k, v in DEFAULT_PRESETS.items():
    st.session_state.setdefault(f"preset_{k}", v)

# ===== الشريط الجانبي =====
with st.sidebar:
    st.header("⚙️ إعدادات سريعة")
    st.write("ملف التخزين (CSV):")
    st.code(CSV_PATH, language="bash")
    export_excel = st.button("⬇️ تصدير إلى Excel (Dashboard)")

# ===== التبويبات =====
tab1, tab2, tab3 = st.tabs(["📩 إضافة عملية", "📒 السجل", "⚙️ الضبطيات"])

# ------------------------------------------------------------------------------------
# Tab 1: إضافة عملية (رسالة بنك + تصنيف يدوي + إدخال سريع بمبالغ جاهزة)
# ------------------------------------------------------------------------------------
with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="page-title">صفحة الهب (إضافة عملية)</div>', unsafe_allow_html=True)

    with st.form("add_form_ui", clear_on_submit=True, border=False):
        st.markdown('<div class="subline">إضافة عملية | إدخال</div>', unsafe_allow_html=True)
        msg = st.text_input(" ", placeholder="ألصق/اكتب نص العملية هنا …", label_visibility="collapsed")

        # تصنيف يدوي (Checkbox + نوع + تصنيف)
        force_type = st.checkbox("تصنيف يدوي")
        c1, c2 = st.columns(2)
        with c1:
            manual_kind = st.radio("النوع", ["Expense","Saving","Income"],
                                   index=0, horizontal=True, disabled=not force_type)
        with c2:
            cats = [
                "Food & Coffee","Shopping","Entertainment","Travel",
                "Internet & Phone","Transport","Education","Health & Fitness",
                "Gifts & Family","Savings & Investment","Misc"
            ]
            manual_cat = st.selectbox("التصنيف", cats, index=cats.index("Misc"), disabled=not force_type)

        # عدّادات مبالغ جاهزة (Presets)
        st.markdown('<div class="subline">اختر (اختياري): مبالغ سريعة</div>', unsafe_allow_html=True)
        g1,g2,g3,g4 = st.columns(4)
        with g1:
            st.number_input("🍔 مطاعم/قهوة", min_value=0.0, step=1.0, key="preset_Food & Coffee")
            st.number_input("🛍️ تسوّق", min_value=0.0, step=1.0, key="preset_Shopping")
        with g2:
            st.number_input("🎬 ترفيه", min_value=0.0, step=1.0, key="preset_Entertainment")
            st.number_input("✈️ سفر", min_value=0.0, step=5.0, key="preset_Travel")
        with g3:
            st.number_input("📶 نت/جوال", min_value=0.0, step=1.0, key="preset_Internet & Phone")
            st.number_input("🚗 تنقّل", min_value=0.0, step=1.0, key="preset_Transport")
        with g4:
            st.number_input("🏦 ادخار/استثمار", min_value=0.0, step=5.0, key="preset_Savings & Investment")
            st.number_input("📦 متفرقات", min_value=0.0, step=1.0, key="preset_Misc")

        # صف “إدخال سريع” بنفس الكارد
        st.markdown("---")
        q1,q2,q3 = st.columns([1,1,1])
        with q1:
            quick_cat = st.selectbox("التصنيف السريع", cats, index=cats.index("Food & Coffee"))
        with q2:
            quick_amount = st.number_input(
                "المبلغ", min_value=0.0, step=1.0,
                value=float(st.session_state.get(f"preset_{quick_cat}", 0.0))
            )
        with q3:
            quick_kind = st.radio("النوع", ["Expense","Saving","Income"], index=0, horizontal=True)

        b1,b2 = st.columns(2)
        add_btn   = b1.form_submit_button("➕ إضافة/تصنيف")
        quick_btn = b2.form_submit_button("⏱️ إضافة سريعة")

        if add_btn:
            if msg.strip():
                from classifier import classify_message
                res = classify_message(msg.strip())
                if force_type:
                    res["type"] = manual_kind
                    res["category"] = manual_cat
                with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["date","account","merchant","category","payment_method","amount","type","raw"])
                    writer.writerow(res)
                st.success("تمت الإضافة ✔️")
                st.json(res, expanded=False)
            else:
                st.warning("اكتب الرسالة أول.")

        if quick_btn:
            sign = 1 if quick_kind == "Income" else -1
            res = {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "account": "Main",
                "merchant": "",
                "category": quick_cat,
                "payment_method": "Manual",
                "amount": sign * abs(float(quick_amount)),
                "type": quick_kind,
                "raw": f"[Quick Add] {quick_kind} {quick_amount} SAR ({quick_cat})"
            }
            with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["date","account","merchant","category","payment_method","amount","type","raw"])
                writer.writerow(res)
            st.success("انضافت العملية السريعة ✔️")
            st.json(res, expanded=False)

    st.markdown('</div>', unsafe_allow_html=True)  # /card


# ------------------------------------------------------------------------------------
# Tab 2: السجل + فلاتر + حذف + إحصائيات + رسوم
# ------------------------------------------------------------------------------------
with tab2:
    df = pd.read_csv(CSV_PATH, encoding="utf-8")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="page-title">صفحة الهب (السجل)</div>', unsafe_allow_html=True)

    st.markdown('<div class="subline">إضافة عملية | السجل</div>', unsafe_allow_html=True)
    _dummy = st.text_input(" ", placeholder="العمليات", label_visibility="collapsed")

    # أزرار الفلاتر
    st.markdown('<div class="btn-row">', unsafe_allow_html=True)
    colb = st.columns(4)
    map_labels = ["التفاصيل","الطوارئ","التمتع","الالتزامات"]
    clicks = [
        colb[0].button("التفاصيل"),
        colb[1].button("الطوارئ"),
        colb[2].button("التمتع"),
        colb[3].button("الالتزامات")
    ]
    st.markdown('</div>', unsafe_allow_html=True)

    active = None
    for lbl, clicked in zip(map_labels, clicks):
        if clicked: active = lbl

    df_f = df.copy()
    if active and AR_FILTERS[active]:
        df_f = df_f[df_f["category"].isin(AR_FILTERS[active])]

    # الجدول
    df_view = df_f.reset_index().rename(columns={"index":"Row"})
    if df_view.empty:
        st.info("📭 ما فيه بيانات.")
    else:
        st.dataframe(df_view, use_container_width=True, hide_index=True)

    # خطوط الميتريكس مثل السكتش (سطرين)
    calc_df = df_f if not df_f.empty else df
    total_exp = calc_df.loc[calc_df["type"]=="Expense","amount"].sum() if not calc_df.empty else 0
    total_inc = calc_df.loc[calc_df["type"]=="Income","amount"].sum() if not calc_df.empty else 0
    save_mask = calc_df["type"].isin(["Saving","Investment"]) if not calc_df.empty else False
    total_save_signed = calc_df.loc[save_mask,"amount"].sum() if not calc_df.empty else 0
    total_save = abs(total_save_signed)
    net_spendable = total_inc + total_exp - total_save

    # السطر الأول
    st.markdown('<div class="metric-line">', unsafe_allow_html=True)
    st.markdown(f'<div class="metric"><div class="lbl">الصافي:</div><div class="val">{net_spendable:,.2f} ر.س</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric"><div class="lbl">المستثمر:</div><div class="val">{total_save:,.2f} ر.س</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric"><div class="lbl">الزيادة:</div><div class="val">{total_inc:,.2f} ر.س</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # السطر الثاني (أمثلة: تقدر تغيّر التوزيع)
    exp_only = calc_df[calc_df["type"]=="Expense"] if not calc_df.empty else calc_df
    by_cat = exp_only.groupby("category")["amount"].sum().abs().reset_index() if not exp_only.empty else pd.DataFrame(columns=["category","amount"])
    top_misc = float(by_cat.loc[by_cat["category"]=="Misc","amount"].sum()) if not by_cat.empty else 0.0
    top_food = float(by_cat.loc[by_cat["category"]=="Food & Coffee","amount"].sum()) if not by_cat.empty else 0.0

    st.markdown('<div class="metric-line">', unsafe_allow_html=True)
    st.markdown(f'<div class="metric"><div class="lbl">الكماليات:</div><div class="val">{top_food:,.2f} ر.س</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="metric"><div class="lbl">أخرى:</div><div class="val">{top_misc:,.2f} ر.س</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # حذف (اختياري تحت)
    if not df_view.empty:
        del_min, del_max = int(df_view["Row"].min()), int(df_view["Row"].max())
        del_row = st.number_input("رقم الصف للحذف (Row)", min_value=del_min, max_value=del_max, step=1, value=del_min)
        if st.button("🗑️ حذف العملية المحددة"):
            df2 = df.drop(index=int(del_row)).reset_index(drop=True)
            df2.to_csv(CSV_PATH, index=False, encoding="utf-8")
            st.success("تم الحذف ✔️"); st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # /card


# ------------------------------------------------------------------------------------
# Tab 3: الضبطيات (تصدير + أهداف مالية رقمية)
# ------------------------------------------------------------------------------------
with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="page-title">صفحة الهب (الضبطيات)</div>', unsafe_allow_html=True)

    st.markdown('<div class="two-pane">', unsafe_allow_html=True)
    # يسار
    c = st.container()
    with c:
        st.button("تصدير Excel Dashboard")
        st.markdown('<div class="small">إعدادات:</div>', unsafe_allow_html=True)
        st.session_state["goal_saving"] = st.number_input("مبلغ الادخار (هدف) ر.س", min_value=0.0, step=50.0,
                                                          value=st.session_state.get("goal_saving", 500.0))
        st.session_state["goal_obligation"] = st.number_input("مبلغ الالتزامات (هدف) ر.س", min_value=0.0, step=50.0,
                                                              value=st.session_state.get("goal_obligation", 1000.0))
        st.session_state["goal_luxury"] = st.number_input("مبلغ الكماليات (هدف) ر.س", min_value=0.0, step=50.0,
                                                          value=st.session_state.get("goal_luxury", 600.0))
    # فاصل رأسي
    st.markdown('<div class="vsplit"></div>', unsafe_allow_html=True)
    # يمين
    st.empty()
    st.markdown('</div>', unsafe_allow_html=True)  # /two-pane

    st.markdown('</div>', unsafe_allow_html=True)  # /card


# ------------------------------------------------------------------------------------
# تصدير إلى إكسل (نفس الزر في الشريط الجانبي)
# ------------------------------------------------------------------------------------
if export_excel:
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active; ws.title = "Transactions"
        cols = ["date","account","merchant","category","payment_method","amount","type","raw"]
        ws.append(cols)
        df2 = pd.read_csv(CSV_PATH, encoding="utf-8")
        for row in df2[cols].itertuples(index=False):
            ws.append(list(row))
        out_path = os.path.join(BASE_DIR, "Exported-Budget.xlsx")
        wb.save(out_path)
        st.success("تم التصدير إلى Exported-Budget.xlsx ✅")
        with open(out_path, "rb") as f:
            st.download_button("تحميل Exported-Budget.xlsx", f, file_name="Exported-Budget.xlsx")
    except Exception as e:
        st.error(f"تعذر التصدير: {e}")
