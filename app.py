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
    st.subheader("حساب الميزانية")
    with st.form("add_form", clear_on_submit=True, border=True):
        st.write("إضافة عملية | إدخال")
        msg = st.text_area(
            "ألصق رسالة البنك هنا",
            height=120,
            placeholder="… تم شراء 22.50 ر.س …"
        )

        # ✅ (1) Check box: تصنيف يدوي
        force_type = st.checkbox("تصنيف يدوي للمصروف/الادخار/الدخل")
        colx1, colx2 = st.columns([1,1])
        with colx1:
            manual_kind = st.radio(
                "النوع",
                ["Expense", "Saving", "Income"],
                index=0, horizontal=True,
                disabled=not force_type
            )
        with colx2:
            cats = [
                "Food & Coffee","Shopping","Entertainment","Travel",
                "Internet & Phone","Transport","Education","Health & Fitness",
                "Gifts & Family","Savings & Investment","Misc"
            ]
            manual_cat = st.selectbox(
                "التصنيف",
                cats,
                index=cats.index("Misc"),
                disabled=not force_type
            )

        # ✅ (2) عدّاد/مبلغ جاهز لكل تصنيف (تقدر تغيّره من هنا)
        st.markdown("**مبالغ جاهزة لكل تصنيف (تُستخدم في الإضافة السريعة):**")
        g1,g2,g3,g4 = st.columns(4)
        with g1:
            st.number_input("🍔 مطاعم/قهوة", min_value=0.0, step=1.0, key="preset_Food & Coffee")
            st.number_input("🛍️ تسوّق", min_value=0.0, step=1.0, key="preset_Shopping")
            st.number_input("🎬 ترفيه", min_value=0.0, step=1.0, key="preset_Entertainment")
        with g2:
            st.number_input("✈️ سفر", min_value=0.0, step=5.0, key="preset_Travel")
            st.number_input("📶 نت/جوال", min_value=0.0, step=1.0, key="preset_Internet & Phone")
            st.number_input("🚗 تنقّل", min_value=0.0, step=1.0, key="preset_Transport")
        with g3:
            st.number_input("📚 تعليم", min_value=0.0, step=1.0, key="preset_Education")
            st.number_input("💊 صحة", min_value=0.0, step=1.0, key="preset_Health & Fitness")
            st.number_input("🎁 هدايا/عائلة", min_value=0.0, step=1.0, key="preset_Gifts & Family")
        with g4:
            st.number_input("🏦 ادخار/استثمار", min_value=0.0, step=5.0, key="preset_Savings & Investment")
            st.number_input("📦 متفرقات", min_value=0.0, step=1.0, key="preset_Misc")

        # إدخال سريع بالمبالغ الجاهزة
        st.divider()
        st.write("**إدخال سريع بمبلغ جاهز**")
        q1,q2,q3 = st.columns([1,1,1])
        with q1:
            quick_cat = st.selectbox("اختر التصنيف السريع", cats, index=cats.index("Food & Coffee"))
        with q2:
            quick_amount = st.number_input(
                "المبلغ الجاهز",
                min_value=0.0, step=1.0,
                value=float(st.session_state.get(f"preset_{quick_cat}", 0.0))
            )
        with q3:
            quick_kind = st.radio("نوعه", ["Expense","Saving","Income"], index=0, horizontal=True)

        colb1, colb2 = st.columns([1,1])
        add_btn   = colb1.form_submit_button("تصنيف وإضافة ➕")
        quick_btn = colb2.form_submit_button("إضافة سريعة ⏱️")

        if add_btn:
            if msg.strip():
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
                st.warning("أكتب نص الرسالة أول.")

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

# ------------------------------------------------------------------------------------
# Tab 2: السجل + فلاتر + حذف + إحصائيات + رسوم
# ------------------------------------------------------------------------------------
with tab2:
    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    st.subheader("حساب الميزانية")
    st.write("إضافة عملية | السجل")

    # فلاتر حسب الرسم: تفاصيل / طوارئ / التمتع / الالتزامات
    fcol = st.columns(4)
    chosen  = fcol[0].button("التفاصيل")
    chosen2 = fcol[1].button("الطوارئ")
    chosen3 = fcol[2].button("التمتع")
    chosen4 = fcol[3].button("الالتزامات")

    active = None
    if chosen:  active = "التفاصيل"
    if chosen2: active = "الطوارئ"
    if chosen3: active = "التمتع"
    if chosen4: active = "الالتزامات"

    df_f = df.copy()
    if active and AR_FILTERS[active]:
        df_f = df_f[df_f["category"].isin(AR_FILTERS[active])]

    # نطاق تاريخ + بحث (اختياري، يساعدك بالتعامل)
    filt1, filt2 = st.columns([1,1])
    with filt1:
        min_d = pd.to_datetime(df_f["date"]).min().date() if not df_f.empty else date.today()
        max_d = pd.to_datetime(df_f["date"]).max().date() if not df_f.empty else date.today()
        date_range = st.date_input("نطاق التاريخ", (min_d, max_d))
    with filt2:
        q = st.text_input("بحث بالمتجر/النص", "", placeholder="مثال: شاورمر / STC / مكافأة")

    if isinstance(date_range, tuple) and len(date_range) == 2:
        s, e = date_range
        if s and e:
            dts = pd.to_datetime(df_f["date"]).dt.date
            df_f = df_f[(dts >= s) & (dts <= e)]
    if q.strip():
        ql = q.strip().lower()
        df_f = df_f[
            df_f["merchant"].str.lower().str.contains(ql, na=False) |
            df_f["raw"].str.lower().str.contains(ql, na=False)
        ]

    # عرض الجدول مع عمود Row = رقم الصف الحقيقي في الملف
    if df_f.empty:
        st.info("📭 ما فيه عمليات مطابقة للفلاتر.")
    else:
        df_view = df_f.reset_index().rename(columns={"index":"Row"})
        st.dataframe(df_view, use_container_width=True, hide_index=True)

        # حذف بالاعتماد على رقم الصف الحقيقي (Row)
        del_min, del_max = int(df_view["Row"].min()), int(df_view["Row"].max())
        del_row = st.number_input("رقم الصف للحذف (Row من الجدول)", min_value=del_min, max_value=del_max, step=1, value=del_min)
        if st.button("🗑️ حذف العملية المحددة"):
            df2 = df.drop(index=int(del_row)).reset_index(drop=True)
            df2.to_csv(CSV_PATH, index=False, encoding="utf-8")
            st.success("تم الحذف ✔️")
            st.rerun()

    # إجماليات تُحسب من البيانات بعد الفلترة
    calc_df = df_f if not df_f.empty else df
    total_exp = calc_df.loc[calc_df["type"]=="Expense", "amount"].sum() if not calc_df.empty else 0
    total_inc = calc_df.loc[calc_df["type"]=="Income", "amount"].sum() if not calc_df.empty else 0
    save_mask = calc_df["type"].isin(["Saving","Investment"]) if not calc_df.empty else False
    total_save_signed = calc_df.loc[save_mask, "amount"].sum() if not calc_df.empty else 0
    total_save = abs(total_save_signed)
    net_spendable = total_inc + total_exp - total_save  # لأن المصروفات بالسالب

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("💸 إجمالي المصروفات", f"{-total_exp:,.2f} SAR")
    with c2: st.metric("💰 إجمالي الدخل", f"{total_inc:,.2f} SAR")
    with c3: st.metric("🏦 ادخار/استثمار", f"{total_save:,.2f} SAR")
    with c4: st.metric("⚖️ الصافي القابل للصرف", f"{net_spendable:,.2f} SAR")

    # رسوم: نعرض مصروفات استهلاكية فقط (بدون ادخار)
    exp_only = calc_df[calc_df["type"] == "Expense"] if not calc_df.empty else calc_df
    exp_by_cat = (exp_only.groupby("category")["amount"].sum().abs().reset_index()
                  if not exp_only.empty else pd.DataFrame(columns=["category","amount"]))

    if not exp_by_cat.empty:
        cL, cR = st.columns(2)
        with cL:
            fig = px.pie(exp_by_cat, values="amount", names="category", hole=0.5, title="توزيع المصروفات")
            st.plotly_chart(fig, use_container_width=True)
        with cR:
            fig_bar = px.bar(exp_by_cat, x="category", y="amount", text_auto=True, title="المصروفات حسب التصنيف")
            st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("📭 لا يوجد مصروفات لعرضها في الرسوم.")

# ------------------------------------------------------------------------------------
# Tab 3: الضبطيات (تصدير + أهداف مالية رقمية)
# ------------------------------------------------------------------------------------
with tab3:
    lc, rc = st.columns([1,2])
    with lc:
        st.button("تصدير Excel Dashboard")  # زر شكلي حسب رسمك (التصدير الحقيقي تحت)
        st.write("**إعدادات الأهداف:**")
        st.session_state["goal_saving"] = st.number_input(
            "مبلغ الادخار (هدف) ر.س", min_value=0.0, step=50.0,
            value=st.session_state.get("goal_saving", 500.0)
        )
        st.session_state["goal_obligation"] = st.number_input(
            "مبلغ الالتزامات (هدف) ر.س", min_value=0.0, step=50.0,
            value=st.session_state.get("goal_obligation", 1000.0)
        )
        st.session_state["goal_luxury"] = st.number_input(
            "مبلغ الكماليات (هدف) ر.س", min_value=0.0, step=50.0,
            value=st.session_state.get("goal_luxury", 600.0)
        )
    with rc:
        st.empty()  # مساحة لأي لوحة مستقبلية

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
