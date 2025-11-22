import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import pytz
import plotly.express as px
import plotly.graph_objects as go

# --- 1. إعداد الصفحة ---
st.set_page_config(
    page_title="نواعم بوتيك", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="collapsed"
)

# --- 2. CSS مخصص (إخفاء السايد بار + تنسيق شريط التنقل) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap');
    
    * {font-family: 'Cairo', sans-serif !important;}
    .stApp {direction: rtl; background-color: #f8f9fa;}

    /* إخفاء القائمة الجانبية تماماً */
    [data-testid="stSidebar"] {display: none;}
    [data-testid="collapsedControl"] {display: none;}
    
    /* تنسيق شريط التنقل العلوي (Radio Button كأزرار) */
    div[role="radiogroup"] {
        flex-direction: row-reverse;
        background-color: white;
        padding: 5px;
        border-radius: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        justify-content: space-between;
        display: flex;
        width: 100%;
        overflow-x: auto; /* للسماح بالتمرير في الشاشات الصغيرة جدا */
    }
    
    /* تصميم كل زر في القائمة */
    div[role="radiogroup"] label {
        background-color: white !important;
        border: 1px solid #eee !important;
        border-radius: 10px !important;
        padding: 5px 10px !important;
        margin: 0 2px !important;
        flex-grow: 1;
        text-align: center;
        font-size: 14px !important;
        transition: all 0.3s;
    }

    /* تصميم الزر المختار */
    div[role="radiogroup"] label[data-testid="stWidgetLabel"][aria-checked="true"] {
        background-color: #e91e63 !important; /* لون وردي */
        color: white !important;
        border-color: #e91e63 !important;
        font-weight: bold;
    }

    /* تنسيق البطاقات */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        padding: 15px;
        border: 1px solid #eee;
    }

    /* الأزرار العامة */
    .stButton button {
        width: 100%; border-radius: 12px; font-weight: 600; height: 45px;
    }
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #e91e63; border: none; color: white;
    }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# --- 3. دوال قاعدة البيانات ---
@st.cache_resource
def init_connection():
    try:
        return psycopg2.connect(st.secrets["DB_URL"])
    except Exception:
        return None

def run_query(query, params=(), fetch_data=False, commit=True):
    conn = init_connection()
    if conn:
        try:
            if conn.closed: conn = init_connection()
            cur = conn.cursor()
            cur.execute(query, params)
            if fetch_data:
                columns = [desc[0] for desc in cur.description]
                data = cur.fetchall()
                cur.close()
                return pd.DataFrame(data, columns=columns)
            else:
                if commit: conn.commit()
                cur.close()
                return True
        except Exception:
            conn.rollback()
            return None
    return None

# --- 4. الجلسة ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'auth' not in st.session_state: st.session_state.auth = False

# --- 5. واجهة تسجيل الدخول ---
def login_ui():
    c1, c2, c3 = st.columns([1, 5, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #e91e63;'>🌸 نواعم</h1>", unsafe_allow_html=True)
        with st.container(border=True):
            pwd = st.text_input("🔑 الرمز السري", type="password")
            if st.button("دخول", type="primary"):
                if pwd == st.secrets.get("ADMIN_PASS", "admin"):
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.toast("خطأ في الرمز", icon="❌")

def process_sale(customer_name):
    conn = init_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        dt = datetime.now(pytz.timezone('Asia/Baghdad'))
        inv_id = dt.strftime("%Y%m%d%H%M")
        
        # معالجة العميل
        cur.execute("SELECT id FROM customers WHERE name = %s", (customer_name,))
        res = cur.fetchone()
        cust_id = res[0] if res else None
        if not cust_id:
            cur.execute("INSERT INTO customers (name) VALUES (%s) RETURNING id", (customer_name,))
            cust_id = cur.fetchone()[0]
        
        # معالجة السلة
        for item in st.session_state.cart:
            cur.execute("SELECT stock FROM variants WHERE id = %s FOR UPDATE", (item['id'],))
            stock = cur.fetchone()[0]
            if stock < item['qty']: raise Exception(f"نفذ: {item['name']}")
            
            cur.execute("UPDATE variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
            profit = (item['price'] - item['cost']) * item['qty']
            cur.execute("""
                INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, dt, inv_id))
            
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        st.toast(f"خطأ: {e}", icon="⚠️")
        return False

# --- 6. التطبيق الرئيسي ---
def main_app():
    # شريط العنوان والخروج
    top_col1, top_col2 = st.columns([4, 1])
    top_col1.markdown("### 🌸 بوتيك نواعم")
    if top_col2.button("خروج", key="logout_btn"):
        st.session_state.auth = False
        st.rerun()

    # --- شريط التنقل البديل (NavBar) ---
    # نستخدم st.radio بشكل أفقي بدلاً من sidebar
    selected_page = st.radio(
        "القائمة",
        ["نقطة البيع 🛒", "المخزون 📦", "التقارير 📊", "الفواتير 🧾"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.markdown("---")

    # === صفحة نقطة البيع ===
    if "نقطة البيع" in selected_page:
        tab1, tab2 = st.tabs(["المنتجات", f"السلة ({len(st.session_state.cart)})"])
        
        with tab1: # المنتجات
            search = st.text_input("بحث", placeholder="اسم أو لون...", label_visibility="collapsed")
            q = "SELECT * FROM variants WHERE is_active = TRUE AND stock > 0"
            p = []
            if search:
                q += " AND (name ILIKE %s OR color ILIKE %s)"
                p = [f"%{search}%", f"%{search}%"]
            q += " ORDER BY id DESC LIMIT 20"
            
            items = run_query(q, tuple(p), fetch_data=True)
            if items is not None and not items.empty:
                cols = st.columns(2)
                for idx, row in items.iterrows():
                    with cols[idx % 2]:
                        with st.container(border=True):
                            st.markdown(f"**{row['name']}**")
                            st.caption(f"{row['color']} | {int(row['price']):,} د.ع")
                            c_qty, c_add = st.columns([1, 2])
                            qty = c_qty.number_input("ع", 1, 10, key=f"q_{row['id']}", label_visibility="collapsed")
                            if c_add.button("أضف", key=f"a_{row['id']}"):
                                found = False
                                for i in st.session_state.cart:
                                    if i['id'] == row['id']:
                                        i['qty'] += qty
                                        i['total'] += (qty * row['price'])
                                        found = True; break
                                if not found:
                                    st.session_state.cart.append({"id":row['id'], "name":row['name'], "price":row['price'], "qty":qty, "total":qty*row['price'], "cost":row['cost']})
                                st.toast("تمت الإضافة", icon="✅")
                                st.rerun()
            else:
                st.info("لا توجد نتائج")

        with tab2: # السلة
            if st.session_state.cart:
                for i, item in enumerate(st.session_state.cart):
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.text(f"{item['name']} (x{item['qty']})")
                        c1.caption(f"{item['total']:,.0f} د.ع")
                        if c2.button("❌", key=f"d_{i}"):
                            st.session_state.cart.pop(i); st.rerun()
                
                total = sum(x['total'] for x in st.session_state.cart)
                st.success(f"المجموع: {total:,.0f} د.ع")
                name = st.text_input("اسم الزبون")
                if st.button("✅ إتمام البيع", type="primary"):
                    if name:
                        if process_sale(name):
                            st.session_state.cart = []
                            st.balloons()
                            st.rerun()
                    else:
                        st.toast("اكتب الاسم", icon="⚠️")
            else:
                st.info("السلة فارغة")

    # === صفحة المخزون ===
    elif "المخزون" in selected_page:
        st.info("يمكنك التعديل مباشرة على الجدول")
        df = run_query("SELECT id, name, color, size, stock, price, cost FROM variants ORDER BY id DESC", fetch_data=True)
        if df is not None:
            edited = st.data_editor(
                df, 
                column_config={"id":None, "stock": st.column_config.NumberColumn("مخزون"), "price": st.column_config.NumberColumn("سعر", format="%d")},
                num_rows="dynamic", use_container_width=True, key="editor"
            )
            if st.button("حفظ التعديلات", type="primary"):
                conn = init_connection(); cur = conn.cursor()
                try:
                    for i, row in edited.iterrows():
                        if row['id'] is None or pd.isna(row['id']):
                            cur.execute("INSERT INTO variants (name, color, size, stock, price, cost) VALUES (%s,%s,%s,%s,%s,%s)", 
                                (row['name'], row['color'], row['size'], row['stock'], row['price'], row['cost']))
                        else:
                            cur.execute("UPDATE variants SET name=%s, color=%s, size=%s, stock=%s, price=%s, cost=%s WHERE id=%s", 
                                (row['name'], row['color'], row['size'], row['stock'], row['price'], row['cost'], row['id']))
                    conn.commit(); st.toast("تم الحفظ", icon="💾")
                except Exception: conn.rollback()

    # === التقارير ===
    elif "التقارير" in selected_page:
        days = st.selectbox("المدة", [1, 7, 30], format_func=lambda x: "اليوم" if x==1 else f"{x} أيام")
        d = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        df = run_query(f"SELECT SUM(total) as s, SUM(profit) as p FROM sales WHERE date >= '{d}'", fetch_data=True)
        if df is not None:
            c1, c2 = st.columns(2)
            c1.metric("مبيعات", f"{df.iloc[0]['s'] or 0:,.0f}")
            c2.metric("أرباح", f"{df.iloc[0]['p'] or 0:,.0f}")

    # === الفواتير ===
    elif "الفواتير" in selected_page:
        df = run_query("SELECT s.invoice_id, c.name, s.total, s.date FROM sales s JOIN customers c ON s.customer_id=c.id ORDER BY s.id DESC LIMIT 30", fetch_data=True)
        st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    if st.session_state.auth: main_app()
    else: login_ui()
