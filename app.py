# -*- coding: utf-8 -*-
import os, csv
from datetime import datetime
import pandas as pd
import streamlit as st
from classifier import classify_message

# ---------------- إعداد الصفحة ----------------
st.set_page_config(page_title="نظام الميزانية", page_icon="📊", layout="wide")

# RTL + محاذاة يمين
st.markdown("""
<style>
body, .block-container { direction: rtl; text-align: right; }
[data-testid="stSidebar"] .block-container { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

# ---------------- المسارات وتهيئة CSV ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "sample_transactions.csv")

if not os.path.exists(CSV_PATH):
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date","account","merchant","category","payment_method","amount","type","raw"]
        )
        writer.writeheader()

# ---------------- تنقّل بأزرار ----------------
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "add"   # add | log

colA, colB = st.columns(2)
if colA.button("➕ إضافة عملية"):
    st.session_state.active_tab = "add"
if colB.button("📒 السجل"):
    st.session_state.active_tab = "log"

st.divider()

# ========================== تبويب: إضافة عملية ==========================
if st.session_state.active_tab == "add":
    st.markdown("### صفحة الهب (إضافة عملية)")
    st.markdown("<h3 style='text-align:center; font-weight:800'>حساب الميزانية</h3>", unsafe_allow_html=True)
    st.markdown("**إضافة عملية | سجل**")
    st.divider()

    with st.form("simple_add_form", clear_on_submit=True):
        # مربع نص
        st.write("**أضف عملية:**")
        msg = st.text_area(
            label="أضف عملية",
            value="",
            height=130,
            placeholder=".. Text",
            key="msg_simple",
        )

        # خانات اختيار للتصنيف (نختار أول واحدة مفعلة بالترتيب)
        st.write("**اختر التصنيف:**")
        c1, c2, c3, c4 = st.columns(4)
        with c1: pick_obl  = st.checkbox("الالتزام",  key="pick_obl")
        with c2: pick_lux  = st.checkbox("كماليات",   key="pick_lux")
        with c3: pick_save = st.checkbox("ادخار",     key="pick_save")
        with c4: pick_misc = st.checkbox("أخرى",      key="pick_misc")

        submitted = st.form_submit_button("＋ إدراج العملية")

        if submitted:
            if not msg.strip():
                st.warning("✋ اكتب نص العملية أول.")
            else:
                # نصنّف تلقائيًا ثم نطبّق اختيارك اليدوي إن وُجد
                res = classify_message(msg.strip())

                # نحسم التصنيف اليدوي إن المستخدم اختار أكثر من واحد
                chosen = None
                for val, name in [(pick_obl, "obl"), (pick_lux, "lux"), (pick_save, "save"), (pick_misc, "misc")]:
                    if val:
                        chosen = name
                        break

                if chosen == "save":
                    res["type"] = "Saving"
                    res["category"] = "Savings & Investment"
                elif chosen == "obl":
                    res["type"] = "Expense"
                    res["category"] = "الالتزام"
                elif chosen == "lux":
                    res["type"] = "Expense"
                    res["category"] = "الكماليات"
                elif chosen == "misc":
                    res["type"] = "Expense"
                    res["category"] = "أخرى"

                # حفظ بالسجل
                with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=["date","account","merchant","category","payment_method","amount","type","raw"]
                    )
                    writer.writerow(res)

                st.success("✔️ تمت الإضافة")
                st.json(res, expanded=False)

# ============================ تبويب: السجل ============================
elif st.session_state.active_tab == "log":
    st.markdown("### صفحة الهب (السجل)")
    st.markdown("<h3 style='text-align:center; font-weight:800'>حساب الميزانية</h3>", unsafe_allow_html=True)
    st.markdown("**إضافة عملية | السجل**")
    st.divider()

    df = pd.read_csv(CSV_PATH, encoding="utf-8")

    if df.empty:
        st.info("📭 لا توجد عمليات بعد.")
    else:
        # نعرض برقم الصف الحقيقي للحذف
        df_view = df.reset_index().rename(columns={"index": "Row"})
        st.dataframe(df_view, use_container_width=True, hide_index=True)

        del_min, del_max = int(df_view["Row"].min()), int(df_view["Row"].max())
        del_row = st.number_input(
            "اكتب رقم الصف للحذف (Row)",
            min_value=del_min, max_value=del_max, step=1, value=del_min, key="delete_row_input"
        )
        if st.button("🗑️ حذف العملية المحددة"):
            df2 = df.drop(index=int(del_row)).reset_index(drop=True)
            df2.to_csv(CSV_PATH, index=False, encoding="utf-8")
            st.success("تم الحذف ✔️")
            st.rerun()
