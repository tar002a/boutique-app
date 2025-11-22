import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import psycopg2

# --- إعداد الصفحة ---
st.set_page_config(page_title="Nawaem System", layout="wide", page_icon="📊", initial_sidebar_state="collapsed")

# --- دالة توقيت بغداد ---
def get_baghdad_time():
    tz = pytz.timezone('Asia/Baghdad')
    return datetime.now(tz)

# --- CSS ---
st.markdown("""
<style>
    .stApp {direction: rtl;}
    div[data-testid="column"] {text-align: right;}
    .stButton button {
        width: 100%;
        height: 45px;
        border-radius: 10px;
        font-weight: bold;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. إدارة الجلسة ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'sale_success' not in st.session_state:
    st.session_state.sale_success = False
if 'last_invoice_text' not in st.session_state:
    st.session_state.last_invoice_text = ""

# --- 2. اتصال قاعدة البيانات (Supabase) ---
@st.cache_resource
def init_connection():
    return psycopg2.connect(**st.secrets["postgres"])

try:
    conn = init_connection()
except Exception as e:
    st.error("فشل الاتصال بقاعدة البيانات. تأكد من إعداد Secrets")
    st.stop()

def init_db():
    # ملاحظة: في PostgreSQL يفضل إنشاء الجداول عبر واجهة Supabase SQL Editor لمرة واحدة، 
    # ولكن سنبقي الكود هنا للعمل، مع تعديل الصيغة لتناسب Postgres
    with conn.cursor() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS variants (
            id SERIAL PRIMARY KEY, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY, name TEXT, phone TEXT, address TEXT, username TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
            qty INTEGER, total REAL, profit REAL, date TEXT, invoice_id TEXT
        )""")
        conn.commit()

init_db()

# --- 3. النوافذ المنبثقة ---
@st.dialog("تعديل عملية بيع")
def edit_sale_dialog(sale_id, current_qty, current_total, variant_id, product_name):
    st.warning(f"فاتورة: {product_name}")
    new_qty = st.number_input("الكمية", min_value=1, value=int(current_qty))
    new_total = st.number_input("الإجمالي", value=float(current_total))
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 حفظ", type="primary"):
            with conn.cursor() as cur:
                diff = new_qty - int(current_qty)
                if diff != 0:
                    cur.execute("UPDATE variants SET stock = stock - %s WHERE id = %s", (diff, variant_id))
                cur.execute("UPDATE sales SET qty = %s, total = %s WHERE id = %s", (new_qty, new_total, sale_id))
                conn.commit(); st.rerun()
    with c2:
        if st.button("🗑️ حذف"):
            with conn.cursor() as cur:
                cur.execute("UPDATE variants SET stock = stock + %s WHERE id = %s", (int(current_qty), variant_id))
                cur.execute("DELETE FROM sales WHERE id = %s", (sale_id,))
                conn.commit(); st.rerun()

@st.dialog("تعديل المخزون")
def edit_stock_dialog(item_id, name, color, size, cost, price, stock):
    with st.form("edit_stk"):
        n_name = st.text_input("الاسم", value=name)
        c1, c2 = st.columns(2)
        n_col = c1.text_input("اللون", value=color)
        n_siz = c2.text_input("القياس", value=size)
        c3, c4, c5 = st.columns(3)
        n_cst = c3.number_input("كلفة", value=float(cost))
        n_prc = c4.number_input("بيع", value=float(price))
        n_stk = c5.number_input("عدد", value=int(stock))
        if st.form_submit_button("💾 حفظ"):
            with conn.cursor() as cur:
                cur.execute("UPDATE variants SET name=%s, color=%s, size=%s, cost=%s, price=%s, stock=%s WHERE id=%s", 
                             (n_name, n_col, n_siz, n_cst, n_prc, n_stk, item_id))
                conn.commit(); st.rerun()
    if st.button("🗑️ حذف نهائي"):
        with conn.cursor() as cur:
            cur.execute("DELETE FROM variants WHERE id=%s", (item_id,))
            conn.commit(); st.rerun()

# --- 4. تسجيل الدخول ---
def login_screen():
    st.title("🌸 نواعم بوتيك")
    if st.button("دخول للنظام"):
        st.session_state.logged_in = True
        st.rerun()

# --- 5. التطبيق الرئيسي ---
def main_app():
    tabs = st.tabs(["🛒 بيع", "📋 سجل", "👥 عملاء", "📦 مخزن", "📊 تقارير ذكية"])

    # === 1. البيع ===
    with tabs[0]:
        if st.session_state.sale_success:
            st.success("✅ تم حجز الطلب!")
            st.balloons()
            st.markdown("### 📋 انسخ الرسالة:")
            st.code(
