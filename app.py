# -*- coding: utf-8 -*-
import sys, os
sys.path.append(os.path.dirname(__file__))  # يضمن استيراد classifier من نفس المجلد

import csv
import pandas as pd
import streamlit as st
import plotly.express as px
from classifier import classify_message

# إعداد الصفحة
st.set_page_config(page_title="حاسبة الميزانية", page_icon="💸", layout="wide")
st.title("💰 حــــســــاب الــــمــــيزانــــية")
# st.caption("ألصق رسالة البنك وسيتم استخراج المبلغ وتصنيف العملية تلقائيًا. يخزن في CSV، وتقدر تصدّر لإكسل.")

# مسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "sample_transactions.csv")

# تأكد من وجود CSV
if not os.path.exists(CSV_PATH):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date","account","merchant","category","payment_method","amount","type","raw"])
        writer.writeheader()

# الشريط الجانبي
with st.sidebar:
    # st.header("⚙️ إعدادات سريعة")
    st.write("ملف التخزين (CSV):")
    st.code(CSV_PATH, language="bash")
    export_excel = st.button("⬇️ تصدير إلى Excel (Dashboard)")

# التبويبات
tab1, tab2 = st.tabs(["📩 إضافة عملية", "📒 السجل"])

# ---------------- Tab 1: إضافة عملية ----------------
with tab1:
    with st.form("add_form", clear_on_submit=True):
        msg = st.text_area(
            "أضـــــف عــملــــية",
            height=140,
            placeholder="مثال: شراء من مطعم الرومانسية بقيمة 100 ريال"
        )
        force_save = st.checkbox("💪 اســـتثمرها يا وحــش")
        submitted = st.form_submit_button("إدراج العـــمــلـــــية➕")

        if submitted:
            if msg.strip():
                res = classify_message(msg.strip())
                if force_save:
                    res["type"] = "Saving"
                    res["category"] = "Savings & Investment"
                # إضافة للسجل
                with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["date","account","merchant","category","payment_method","amount","type","raw"])
                    writer.writerow(res)
                st.success("تمت الإضافة ✔️")
                st.json(res, expanded=False)
            else:
                st.warning("!يا حــــبيـــبي اكـــــتب الرســـــالة أول")

# ---------------- Tab 2: السجل + الحذف + الإحصائيات ----------------
with tab2:
    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    if df.empty:
        st.info("📭 ما فيه عمليات حالياً.")
    else:
        # عرض مع رقم صف واضح
        df_view = df.reset_index().rename(columns={"index":"Row"})
        st.dataframe(df_view, use_container_width=True, hide_index=True)

        # اختيار الصف للحذف
        row_options = list(range(len(df)))
        sel = st.selectbox("اختر رقم الصف للحذف (Row):", row_options, index=0 if row_options else None)
        if st.button("🗑️ حذف العملية المحددة"):
            df = df.drop(sel).reset_index(drop=True)
            df.to_csv(CSV_PATH, index=False, encoding="utf-8")
            st.success("تم الحذف ✔️")
            st.rerun()

    # إجماليات
    total_exp = df.loc[df["type"] == "Expense", "amount"].sum() if not df.empty else 0
    total_inc = df.loc[df["type"] == "Income", "amount"].sum() if not df.empty else 0

    save_mask = df["type"].isin(["Saving","Investment"]) if not df.empty else False
    total_save_signed = df.loc[save_mask, "amount"].sum() if not df.empty else 0
    total_save = abs(total_save_signed)

    # الصافي القابل للصرف = الدخل - المصروفات - الادخار
    net_spendable = total_inc + total_exp - total_save

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("💸 إجمالي المصروفات", f"{-total_exp:,.2f} SAR")
    with c2: st.metric("💰 إجمالي الايرادات", f"{total_inc:,.2f} SAR")
    with c3: st.metric("🏦 استثمار", f"{total_save:,.2f} SAR")
    with c4: st.metric("⚖️ الصافي", f"{net_spendable:,.2f} SAR")

    # 🎯 مصروفات استهلاكية فقط (بدون الادخار) — Pie
    exp_only = df[df["type"] == "Expense"] if not df.empty else df
    exp_by_cat = exp_only.groupby("category")["amount"].sum().abs().reset_index() if not exp_only.empty else pd.DataFrame(columns=["category","amount"])

    if not exp_by_cat.empty:
        fig = px.pie(exp_by_cat, values="amount", names="category", title="توزيع المصروفات حسب التصنيف")
        st.plotly_chart(fig, use_container_width=True)

        # (اختياري) بار تشارت
        fig_bar = px.bar(exp_by_cat, x="category", y="amount", title="المصروفات حسب التصنيف", text_auto=True)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("📭 ما فيه مصروفات لعرضها في الرسوم البيانية.")

# ---------------- Export to Excel ----------------
if export_excel:
    try:
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active; ws.title = "Transactions"
        # رأس الأعمدة
        cols = ["date","account","merchant","category","payment_method","amount","type","raw"]
        ws.append(cols)
        # بيانات
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
