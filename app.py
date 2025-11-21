import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- إعداد الصفحة ---
st.set_page_config(page_title="Nawaem Copy Master", layout="wide", page_icon="🌸", initial_sidebar_state="collapsed")

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
# متغير جديد لحفظ حالة نجاح البيع لعرض الرسالة
if 'sale_success' not in st.session_state:
    st.session_state.sale_success = False
if 'last_invoice_text' not in st.session_state:
    st.session_state.last_invoice_text = ""

# --- 2. قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('boutique_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT, username TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
        qty INTEGER, total REAL, profit REAL, date TEXT, invoice_id TEXT
    )""")
    conn.commit()
    return conn

conn = init_db()

# --- 3. النوافذ المنبثقة (Dialogs) ---
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

# --- 4. الدخول ---
def login_screen():
    st.title("🌸 نواعم بوتيك")
    if st.button("دخول للنظام"):
        st.session_state.logged_in = True
        st.rerun()

# --- 5. التطبيق ---
def main_app():
    tabs = st.tabs(["🛒 بيع", "📋 سجل", "📦 مخزن", "🏠 تقرير"])

    # === 1. البيع (تم التعديل هنا للنسخ) ===
    with tabs[0]:
        # إذا تمت العملية بنجاح، نعرض الرسالة وزر النسخ
        if st.session_state.sale_success:
            st.success("✅ تم حجز الطلب بنجاح!")
            st.balloons()
            
            st.markdown("### 📋 انسخ النص التالي للزبونة:")
            # هنا نعرض النص داخل كود بلوك ليظهر زر النسخ تلقائياً
            st.code(st.session_state.last_invoice_text, language="text")
            
            if st.button("🔄 بدء طلب جديد (مسح الشاشة)", type="primary"):
                st.session_state.sale_success = False
                st.session_state.last_invoice_text = ""
                st.rerun()
        
        else:
            # واجهة البيع العادية
            with st.container(border=True):
                df = pd.read_sql("SELECT * FROM variants WHERE stock > 0", conn)
                srch = st.text_input("🔍 بحث...", label_visibility="collapsed")
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

            if st.session_state.cart:
                st.divider()
                tot = 0
                # تحضير نص الرسالة أثناء التجميع
                invoice_msg = "تم حجز الطلب ✅\n"
                
                for i, x in enumerate(st.session_state.cart):
                    with st.container(border=True):
                        ca, cb = st.columns([1,5])
                        if ca.button("❌", key=f"d{i}"): st.session_state.cart.pop(i); st.rerun()
                        cb.markdown(f"**{x['name']}** ({x['qty']}) - {x['total']:,.0f}")
                        tot += x['total']
                    
                    # بناء النص حسب النموذج المطلوب لكل قطعة
                    invoice_msg += f"{x['name']}\n"
                    invoice_msg += f"{x['color']}\n"
                    invoice_msg += f"{x['size']}\n"
                    # فاصل صغير اذا كان هناك اكثر من قطعة
                    if len(st.session_state.cart) > 1:
                        invoice_msg += "---\n"

                st.metric("الإجمالي", f"{tot:,.0f}")
                
                # تكملة نص الرسالة
                invoice_msg += f"{tot:,.0f}\n"
                invoice_msg += "التوصيل مجاني\n"
                invoice_msg += "الف عافية حياتي 🌸🌸🌸🌸"

                if st.button("✅ إتمام البيع ونسخ الرسالة", type="primary"):
                    inv = datetime.now().strftime("%Y%m%d%H%M")
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    cur = conn.cursor()
                    for x in st.session_state.cart:
                        cur.execute("UPDATE variants SET stock=stock-? WHERE id=?", (x['qty'], x['id']))
                        prf = (x['price']-x['cost'])*x['qty']
                        cur.execute("INSERT INTO sales (product_name, variant_id, qty, total, profit, date, invoice_id) VALUES (?,?,?,?,?,?,?)",
                                    (x['name'], x['id'], x['qty'], x['total'], prf, dt, inv))
                    conn.commit()
                    
                    # حفظ الحالة والنص للانتقال لشاشة النجاح
                    st.session_state.cart = []
                    st.session_state.sale_success = True
                    st.session_state.last_invoice_text = invoice_msg
                    st.rerun()

    # === 2. السجل ===
    with tabs[1]:
        df_s = pd.read_sql("SELECT * FROM sales ORDER BY id DESC LIMIT 20", conn)
        for i, r in df_s.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4,1])
                c1.markdown(f"**{r['product_name']}** ({r['qty']})")
                c1.caption(f"{r['date']} | {r['total']:,.0f}")
                if c2.button("⚙️", key=f"e{r['id']}"):
                    edit_sale_dialog(r['id'], r['qty'], r['total'], r['variant_id'], r['product_name'])

    # === 3. المخزون ===
    with tabs[2]:
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
            unique_products = df_inv['name'].unique()
            for product in unique_products:
                prod_df = df_inv[df_inv['name'] == product]
                with st.container(border=True):
                    avg_price = prod_df['price'].max()
                    st.markdown(f"#### 👗 {product}")
                    st.caption(f"سعر: {avg_price:,.0f}")
                    unique_colors = prod_df['color'].unique()
                    for color in unique_colors:
                        color_variants = prod_df[prod_df['color'] == color]
                        size_display = []
                        for _, row in color_variants.iterrows():
                            size_display.append(f"{row['size']} (<b>{row['stock']}</b>)")
                        sizes_str = "  |  ".join(size_display)
                        st.markdown(f"🎨 **{color}:** &nbsp; {sizes_str}", unsafe_allow_html=True)
                    with st.expander("⚙️ تعديل"):
                        for _, row in prod_df.iterrows():
                            c_info, c_btn = st.columns([3, 1])
                            c_info.text(f"{row['color']} - {row['size']} ({row['stock']})")
                            if c_btn.button("تعديل", key=f"stk_ed_{row['id']}"):
                                edit_stock_dialog(row['id'], row['name'], row['color'], row['size'], row['cost'], row['price'], row['stock'])

    # === 4. تقرير ===
    with tabs[3]:
        today = datetime.now().strftime("%Y-%m-%d")
        df_tdy = pd.read_sql(f"SELECT SUM(total), SUM(profit) FROM sales WHERE date LIKE '{today}%'", conn).iloc[0]
        st.metric("مبيعات اليوم", f"{df_tdy[0] or 0:,.0f}")
        st.metric("أرباح اليوم", f"{df_tdy[1] or 0:,.0f}")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
