
# -*- coding: utf-8 -*-
import plotly.express as px
import streamlit as st
import pandas as pd
import os
import csv
from classifier import classify_message

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "sample_transactions.csv")

st.set_page_config(page_title="Budget SMS Classifier", layout="wide")

st.title("💰 حــســـاب الــمــيزانــية")
# st.caption("ألصق نص رسالة البنك، والنظام يستخرج المبلغ ويصنف العملية تلقائيًا. يخزن في CSV عشان ما يتعارض مع ملف Excel المفتوح.")

with st.sidebar:
    # st.header("⚙️ إعدادات سريعة")
    st.write("الملف اللي نخزن فيه العمليات:")
    st.code(CSV_PATH, language="bash")
    export_excel = st.button("⬇️ تصدير إلى Excel (Dashboard)")

# Ensure CSV exists
if not os.path.exists(CSV_PATH):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
                                "date", "account", "merchant", "category", "payment_method", "amount", "type", "raw"])
        writer.writeheader()

tab1, tab2 = st.tabs(["📩 إضافة عملية", "📒 السجل"])

with tab1:
    with st.form("add_form", clear_on_submit=True):
        msg = st.text_area(
            "أضـــف عــمـــلية",
            height=140,
            placeholder="مثال: شراء من محطة بنزين بقيمة 100 ريال"
        )
        submitted = st.form_submit_button("إدراج العـــمــلية")
        if submitted:
            if msg.strip():
                res = classify_message(msg.strip())
                # حفظ في CSV
                import csv
                import os
                BASE_DIR = os.path.dirname(os.path.abspath(__file__))
                CSV_PATH = os.path.join(BASE_DIR, "sample_transactions.csv")
                with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=[
                                            "date", "account", "merchant", "category", "payment_method", "amount", "type", "raw"])
                    writer.writerow(res)
                st.success("تمت الإضافة ✔️")
                st.json(res, expanded=False)
            else:
                st.warning("يا حــبيبي ما فــيه شيء نضــــيفه")


with tab2:
    import pandas as pd
    import os
    import csv
    import streamlit as st

    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    # لو فاضي: لا تعرض أدوات الحذف
    if df.empty:
        st.info("📭 ما فيه عمليات حالياً.")
    else:
        st.dataframe(df, use_container_width=True)

        # نضمن وجود del_idx ونقيّدها ضمن المدى
        if "del_idx" not in st.session_state:
            st.session_state.del_idx = 0

        max_idx = len(df) - 1
        # لو المؤشر أكبر من الحد بعد حذف سابق، ننزّله لآخر صف
        if st.session_state.del_idx > max_idx:
            st.session_state.del_idx = max_idx

        # واجهة اختيار الصف للحذف (رقم الصف يبدأ من 0)
        st.write("اختر رقم الصف للحذف (0 = أول صف):")
        del_idx = st.number_input(
            "رقم الصف",
            min_value=0,
            max_value=max_idx,
            step=1,
            key="del_idx"
        )

        if st.button("🗑️ حذف العملية المحددة"):
            df = df.drop(del_idx).reset_index(drop=True)
            df.to_csv(CSV_PATH, index=False, encoding="utf-8")
            st.success("تم الحذف ✔️")
            st.rerun()

   # إجماليات
total_exp = df.loc[df["type"] == "Expense", "amount"].sum() if not df.empty else 0
total_inc = df.loc[df["type"] == "Income", "amount"].sum() if not df.empty else 0

save_mask = df["type"].isin(["Saving", "Investment"]) if not df.empty else False
total_save_signed = df.loc[save_mask, "amount"].sum() if not df.empty else 0
total_save = abs(total_save_signed)

# الصافي القابل للصرف = الدخل - المصروفات - الادخار
net_spendable = total_inc + total_exp - total_save

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("💸 إجمالي المصروفات", f"{-total_exp:,.2f} SAR")
with c2: st.metric("💰 إجمالي الدخل", f"{total_inc:,.2f} SAR")
with c3: st.metric("🏦 ادخار/استثمار", f"{total_save:,.2f} SAR")
with c4: st.metric("⚖️ الصافي القابل للصرف", f"{net_spendable:,.2f} SAR")



# مصروفات استهلاكية فقط (بدون Saving/Investment)
exp_only = df[df["type"] == "Expense"] if not df.empty else df
exp_by_cat = exp_only.groupby("category")["amount"].sum().abs().reset_index() if not exp_only.empty else pd.DataFrame(columns=["category","amount"])

if not exp_by_cat.empty:
    fig = px.pie(exp_by_cat, values="amount", names="category", title="توزيع المصروفات حسب التصنيف")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📭 ما فيه مصروفات لعرضها في الرسم البياني.")



if export_excel:
    # Export CSV to an Excel with a simple pivot-like summary
    try:
        import openpyxl
        from openpyxl import Workbook
        from openpyxl.styles import Font
        from collections import defaultdict

        df = pd.read_csv(CSV_PATH, encoding="utf-8")
        wb = Workbook()
        ws = wb.active
        ws.title = "Transactions"
        ws.append(list(df.columns))
        for row in df.itertuples(index=False):
            ws.append(list(row))

        # Summary
        ws2 = wb.create_sheet("Summary")
        ws2.append(["Category", "Spent (SAR)"])
        cat_sum = defaultdict(float)
        for _, r in df.iterrows():
            if r["type"] == "Expense":
                cat_sum[r["category"]] += abs(float(r["amount"]))
        for k, v in sorted(cat_sum.items(), key=lambda x: x[0]):
            ws2.append([k, v])
        ws2["A1"].font = Font(bold=True)
        ws2["B1"].font = Font(bold=True)

        out_path = os.path.join(BASE_DIR, "Exported-Budget.xlsx")
        wb.save(out_path)
        st.success("تم التصدير لملف Excel: Exported-Budget.xlsx")
        with open(out_path, "rb") as f:
            st.download_button("تحميل Exported-Budget.xlsx",
                               f, file_name="Exported-Budget.xlsx")
    except Exception as e:
        st.error(f"تعذر التصدير: {e}")
