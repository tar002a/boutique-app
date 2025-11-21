import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- إعداد الصفحة ---
st.set_page_config(page_title="Nawaem Pro System", layout="wide", page_icon="🛍️", initial_sidebar_state="collapsed")

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
    .stock-card {
        background-color: #f9f9f9;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #eee;
        margin-bottom: 10px;
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

# --- 2. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('boutique_v3.db', check_same_thread=False)
    c = conn.cursor()
    
    # المنتجات
    c.execute("""CREATE TABLE IF NOT EXISTS variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
    )""")
    
    # العملاء (تم التأكد من وجوده)
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT, username TEXT
    )""")
    
    # المبيعات (تم التأكد من وجود customer_id)
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
        qty INTEGER, total REAL, profit REAL, date TEXT, invoice_id TEXT
    )""")
    conn.commit()
    return conn

conn = init_db()

# --- 3. النوافذ المنبثقة ---
@st.dialog("تعديل عملية بيع")
def edit_sale_dialog(sale_id, current_qty, current_total, variant_id, product_name):
    st.warning(f"فاتورة: {product_name}")
    new_qty = st.number_input("الكمية", min_value=1, value=int(current_qty))
    new_total = st.number_input("الإجمالي", value=float(current_total))
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 حفظ", type="primary"):
            cur = conn.cursor()
            diff = new_qty - int(current_qty)
            if diff != 0:
                cur.execute("UPDATE variants SET stock = stock - ? WHERE id = ?", (diff, variant_id))
            cur.execute("UPDATE sales SET qty = ?, total = ? WHERE id = ?", (new_qty, new_total, sale_id))
            conn.commit(); st.rerun()
    with c2:
        if st.button("🗑️ حذف"):
            cur = conn.cursor()
            cur.execute("UPDATE variants SET stock = stock + ? WHERE id = ?", (int(current_qty), variant_id))
            cur.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
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
            conn.execute("UPDATE variants SET name=?, color=?, size=?, cost=?, price=?, stock=? WHERE id=?", 
                         (n_name, n_col, n_siz, n_cst, n_prc, n_stk, item_id))
            conn.commit(); st.success("تم"); st.rerun()
    if st.button("🗑️ حذف نهائي"):
        conn.execute("DELETE FROM variants WHERE id=?", (item_id,))
        conn.commit(); st.rerun()

# --- 4. تسجيل الدخول ---
def login_screen():
    st.title("🌸 نواعم بوتيك")
    if st.button("دخول للنظام"):
        st.session_state.logged_in = True
        st.rerun()

# --- 5. التطبيق الرئيسي ---
def main_app():
    # إضافة تبويب العملاء
    tabs = st.tabs(["🛒 بيع", "📋 سجل", "👥 عملاء", "📦 مخزن", "🏠 تقرير"])

    # === 1. البيع ===
    with tabs[0]:
        if st.session_state.sale_success:
            st.success("✅ تم حجز الطلب وحفظ بيانات العميل!")
            st.balloons()
            st.markdown("### 📋 انسخ الرسالة:")
            st.code(st.session_state.last_invoice_text, language="text")
            
            if st.button("🔄 طلب جديد", type="primary"):
                st.session_state.sale_success = False
                st.session_state.last_invoice_text = ""
                st.rerun()
        else:
            # اختيار المنتجات
            with st.container(border=True):
                df = pd.read_sql("SELECT * FROM variants WHERE stock > 0", conn)
                srch = st.text_input("🔍 بحث عن منتج...", label_visibility="collapsed")
                if srch:
                    mask = df['name'].str.contains(srch, case=False) | df['color'].str.contains(srch, case=False)
                    df = df[mask]
                
                if not df.empty:
                    opts = df.apply(lambda x: f"{x['name']} | {x['color']} ({x['size']})", axis=1).tolist()
                    sel = st.selectbox("اختر:", opts, label_visibility="collapsed")
                    if sel:
                        r = df[df.apply(lambda x: f"{x['name']} | {x['color']} ({x['size']})", axis=1) == sel].iloc[0]
                        st.caption(f"سعر: {r['price']:,.0f} | متوفر: {r['stock']}")
                        c1, c2 = st.columns(2)
                        q = c1.number_input("العدد", 1, int(r['stock']), 1)
                        p = c2.number_input("سعر", value=float(r['price']))
                        if st.button("أضف للسلة ➕", type="secondary"):
                            st.session_state.cart.append({
                                "id": int(r['id']), "name": r['name'], "color": r['color'], "size": r['size'],
                                "cost": r['cost'], "price": p, "qty": q, "total": p*q
                            })
                            st.toast("تمت الإضافة", icon="✅")

            # السلة وإتمام البيع
            if st.session_state.cart:
                st.divider()
                st.markdown("##### بيانات العميل (مطلوب)")
                
                # --- قسم بيانات العميل (تمت إعادته) ---
                with st.container(border=True):
                    cust_type = st.radio("نوع العميل", ["جديد", "سابق"], horizontal=True)
                    cust_id_val, cust_name_val = None, ""
                    
                    if cust_type == "سابق":
                        curr_custs = pd.read_sql("SELECT id, name, phone FROM customers", conn)
                        if not curr_custs.empty:
                            c_sel = st.selectbox("ابحث عن الاسم:", curr_custs.apply(lambda x: f"{x['name']} - {x['phone']}", axis=1).tolist())
                            cust_name_val = c_sel.split(" - ")[0]
                            cust_id_val = curr_custs[curr_custs['name'] == cust_name_val]['id'].iloc[0]
                        else:
                            st.warning("لا يوجد عملاء سابقين")
                    else:
                        c_n = st.text_input("الاسم")
                        c_p = st.text_input("الهاتف")
                        c_a = st.text_input("العنوان")
                        cust_name_val = c_n
                
                # عرض السلة
                tot = 0
                invoice_msg = "تم حجز الطلب ✅\n"
                
                for i, x in enumerate(st.session_state.cart):
                    tot += x['total']
                    invoice_msg += f"{x['name']}\n{x['color']}\n{x['size']}\n"
                    if len(st.session_state.cart) > 1: invoice_msg += "---\n"
                
                invoice_msg += f"{tot:,.0f}\nالتوصيل مجاني\nالف عافية حياتي 🌸🌸🌸🌸"
                
                st.markdown(f"**الإجمالي: {tot:,.0f} د.ع**")

                # زر الإتمام
                if st.button("✅ إتمام البيع ونسخ", type="primary"):
                    # التحقق من اسم العميل
                    if not cust_name_val:
                        st.error("⚠️ يجب إدخال اسم العميل!")
                        st.stop()
                    
                    cur = conn.cursor()
                    # حفظ العميل الجديد
                    if cust_type == "جديد":
                        cur.execute("INSERT INTO customers (name, phone, address) VALUES (?,?,?)", (c_n, c_p, c_a))
                        cust_id_val = cur.lastrowid
                    
                    inv = datetime.now().strftime("%Y%m%d%H%M")
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    # حفظ المبيعات
                    for x in st.session_state.cart:
                        cur.execute("UPDATE variants SET stock=stock-? WHERE id=?", (x['qty'], x['id']))
                        prf = (x['price']-x['cost'])*x['qty']
                        # هنا يتم حفظ customer_id
                        cur.execute("INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) VALUES (?,?,?,?,?,?,?,?)",
                                    (cust_id_val, x['id'], x['name'], x['qty'], x['total'], prf, dt, inv))
                    
                    conn.commit()
                    st.session_state.cart = []
                    st.session_state.sale_success = True
                    st.session_state.last_invoice_text = invoice_msg
                    st.rerun()

    # === 2. السجل (تم الإصلاح لإظهار اسم العميل) ===
    with tabs[1]:
        st.caption("آخر 30 عملية بيع")
        # ربط الجدولين لإظهار الاسم
        df_s = pd.read_sql("""
            SELECT s.*, c.name as customer_name 
            FROM sales s 
            LEFT JOIN customers c ON s.customer_id = c.id 
            ORDER BY s.id DESC LIMIT 30
        """, conn)
        
        for i, r in df_s.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4,1])
                # عرض اسم العميل بوضوح
                c_name = r['customer_name'] if r['customer_name'] else "غير مسجل"
                c1.markdown(f"**{r['product_name']}** ({r['qty']})")
                c1.caption(f"👤 {c_name} | 📅 {r['date']} | 💰 {r['total']:,.0f}")
                if c2.button("⚙️", key=f"e{r['id']}"):
                    edit_sale_dialog(r['id'], r['qty'], r['total'], r['variant_id'], r['product_name'])

    # === 3. العملاء (تبويب جديد) ===
    with tabs[2]:
        st.header("قائمة المشترين")
        df_cust = pd.read_sql("SELECT * FROM customers ORDER BY id DESC", conn)
        if not df_cust.empty:
            st.dataframe(df_cust, use_container_width=True)
        else:
            st.info("لا يوجد عملاء مسجلين بعد")

    # === 4. المخزون ===
    with tabs[3]:
        with st.expander("➕ إضافة جديد"):
            with st.form("add"):
                nm = st.text_input("اسم")
                cl = st.text_input("ألوان (،)")
                sz = st.text_input("قياسات (،)")
                stk = st.number_input("عدد", 1)
                pr = st.number_input("بيع", 0.0)
                cst = st.number_input("كلفة", 0.0)
                if st.form_submit_button("توليد"):
                    for c in cl.replace('،',',').split(','):
                        for s in sz.replace('،',',').split(','):
                            if c.strip() and s.strip():
                                conn.execute("INSERT INTO variants (name,color,size,stock,price,cost) VALUES (?,?,?,?,?,?)",
                                             (nm, c.strip(), s.strip(), stk, pr, cst))
                    conn.commit(); st.rerun()
        
        st.divider()
        df_inv = pd.read_sql("SELECT * FROM variants WHERE stock > 0 ORDER BY name", conn)
        if not df_inv.empty:
            products = df_inv['name'].unique()
            for p in products:
                with st.container(border=True):
                    pdf = df_inv[df_inv['name']==p]
                    st.markdown(f"#### 👗 {p}")
                    st.caption(f"سعر: {pdf['price'].max():,.0f}")
                    for c in pdf['color'].unique():
                        szs = " | ".join([f"{r['size']} ({r['stock']})" for _,r in pdf[pdf['color']==c].iterrows()])
                        st.markdown(f"🎨 {c}: {szs}")
                    with st.expander("تعديل"):
                        for _,r in pdf.iterrows():
                            if st.button(f"تعديل {r['color']} {r['size']}", key=f"bx{r['id']}"):
                                edit_stock_dialog(r['id'], r['name'], r['color'], r['size'], r['cost'], r['price'], r['stock'])

    # === 5. تقرير ===
    with tabs[4]:
        today = datetime.now().strftime("%Y-%m-%d")
        df_tdy = pd.read_sql(f"SELECT SUM(total), SUM(profit) FROM sales WHERE date LIKE '{today}%'", conn).iloc[0]
        st.metric("مبيعات اليوم", f"{df_tdy[0] or 0:,.0f}")
        st.metric("أرباح اليوم", f"{df_tdy[1] or 0:,.0f}")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
