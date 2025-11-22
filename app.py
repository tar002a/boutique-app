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
            st.code(st.session_state.last_invoice_text, language="text")
            if st.button("🔄 طلب جديد", type="primary"):
                st.session_state.sale_success = False; st.session_state.last_invoice_text = ""; st.rerun()
        else:
            with st.container(border=True):
                # قراءة البيانات باستخدام pandas (يعمل مع postgres connection)
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
                            st.session_state.cart.append({"id": int(r['id']), "name": r['name'], "color": r['color'], "size": r['size'], "cost": r['cost'], "price": p, "qty": q, "total": p*q})
                            st.toast("تمت الإضافة", icon="✅")

            if st.session_state.cart:
                st.divider()
                st.markdown("##### بيانات العميل")
                with st.container(border=True):
                    cust_type = st.radio("نوع العميل", ["جديد", "سابق"], horizontal=True)
                    cust_id_val, cust_name_val = None, ""
                    if cust_type == "سابق":
                        curr_custs = pd.read_sql("SELECT id, name, phone FROM customers", conn)
                        if not curr_custs.empty:
                            c_sel = st.selectbox("الاسم:", curr_custs.apply(lambda x: f"{x['name']} - {x['phone']}", axis=1).tolist())
                            cust_name_val = c_sel.split(" - ")[0]
                            cust_id_val = curr_custs[curr_custs['name'] == cust_name_val]['id'].iloc[0]
                        else: st.warning("لا يوجد")
                    else:
                        c_n = st.text_input("الاسم")
                        c_p = st.text_input("الهاتف")
                        c_a = st.text_input("العنوان")
                        cust_name_val = c_n
                
                tot = 0; invoice_msg = "تم حجز الطلب ✅\n"
                for x in st.session_state.cart:
                    tot += x['total']
                    invoice_msg += f"{x['name']}\n{x['color']}\n{x['size']}\n"
                    if len(st.session_state.cart) > 1: invoice_msg += "---\n"
                invoice_msg += f"{tot:,.0f}\nالتوصيل مجاني\nالف عافية حياتي 🌸🌸🌸🌸"
                st.markdown(f"**الإجمالي: {tot:,.0f} د.ع**")

                if st.button("✅ إتمام البيع ونسخ", type="primary"):
                    if not cust_name_val: st.error("الاسم مطلوب!"); st.stop()
                    with conn.cursor() as cur:
                        if cust_type == "جديد":
                            cur.execute("INSERT INTO customers (name, phone, address) VALUES (%s,%s,%s) RETURNING id", (c_n, c_p, c_a))
                            cust_id_val = cur.fetchone()[0]
                        
                        baghdad_now = get_baghdad_time()
                        inv = baghdad_now.strftime("%Y%m%d%H%M")
                        dt = baghdad_now.strftime("%Y-%m-%d %H:%M")
                        for x in st.session_state.cart:
                            cur.execute("UPDATE variants SET stock=stock-%s WHERE id=%s", (x['qty'], x['id']))
                            prf = (x['price']-x['cost'])*x['qty']
                            cur.execute("INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", 
                                        (cust_id_val, x['id'], x['name'], x['qty'], x['total'], prf, dt, inv))
                        conn.commit(); st.session_state.cart = []; st.session_state.sale_success = True; st.session_state.last_invoice_text = invoice_msg; st.rerun()

    # === 2. السجل ===
    with tabs[1]:
        st.caption("آخر العمليات")
        df_s = pd.read_sql("SELECT s.*, c.name as customer_name FROM sales s LEFT JOIN customers c ON s.customer_id = c.id ORDER BY s.id DESC LIMIT 30", conn)
        for i, r in df_s.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4,1])
                c_name = r['customer_name'] if r['customer_name'] else "غير مسجل"
                c1.markdown(f"**{r['product_name']}** ({r['qty']})")
                c1.caption(f"👤 {c_name} | 💰 {r['total']:,.0f}")
                if c2.button("⚙️", key=f"e{r['id']}"): edit_sale_dialog(r['id'], r['qty'], r['total'], r['variant_id'], r['product_name'])

    # === 3. العملاء ===
    with tabs[2]:
        df_cust = pd.read_sql("SELECT * FROM customers ORDER BY id DESC", conn)
        if not df_cust.empty: st.dataframe(df_cust, use_container_width=True)
        else: st.info("فارغ")

    # === 4. المخزون ===
    with tabs[3]:
        with st.expander("➕ إضافة جديد"):
            with st.form("add"):
                nm = st.text_input("اسم"); cl = st.text_input("ألوان (،)"); sz = st.text_input("قياسات (،)")
                stk = st.number_input("عدد", 1); pr = st.number_input("بيع", 0.0); cst = st.number_input("كلفة", 0.0)
                if st.form_submit_button("توليد"):
                    with conn.cursor() as cur:
                        for c in cl.replace('،',',').split(','):
                            for s in sz.replace('،',',').split(','):
                                if c.strip() and s.strip(): 
                                    cur.execute("INSERT INTO variants (name,color,size,stock,price,cost) VALUES (%s,%s,%s,%s,%s,%s)", 
                                                 (nm, c.strip(), s.strip(), stk, pr, cst))
                        conn.commit(); st.rerun()
        st.divider()
        df_inv = pd.read_sql("SELECT * FROM variants WHERE stock > 0 ORDER BY name", conn)
        if not df_inv.empty:
            for p in df_inv['name'].unique():
                with st.container(border=True):
                    pdf = df_inv[df_inv['name']==p]
                    st.markdown(f"#### 👗 {p}")
                    for c in pdf['color'].unique():
                        szs = " | ".join([f"{r['size']} ({r['stock']})" for _,r in pdf[pdf['color']==c].iterrows()])
                        st.markdown(f"🎨 {c}: {szs}")
                    with st.expander("تعديل"):
                        for _,r in pdf.iterrows():
                            if st.button(f"{r['color']} {r['size']}", key=f"bx{r['id']}"): edit_stock_dialog(r['id'], r['name'], r['color'], r['size'], r['cost'], r['price'], r['stock'])

    # === 5. التقارير الذكية ===
    with tabs[4]:
        st.header("📊 ذكاء الأعمال (BI)")
        
        today_baghdad = get_baghdad_time().strftime("%Y-%m-%d")
        # ملاحظة: تم تعديل الاستعلام ليعمل مع Postgres باستخدام CAST للتاريخ إذا لزم الأمر، أو الاعتماد على أن التاريخ مخزن كنص
        df_tdy = pd.read_sql(f"SELECT SUM(total), SUM(profit) FROM sales WHERE date LIKE '{today_baghdad}%'", conn).iloc[0]
        
        st.subheader(f"📅 أداء اليوم ({today_baghdad})")
        col_t1, col_t2 = st.columns(2)
        col_t1.metric("مبيعات اليوم", f"{df_tdy[0] or 0:,.0f} د.ع")
        col_t2.metric("أرباح اليوم الصافية", f"{df_tdy[1] or 0:,.0f} د.ع", help="الربح بعد خصم تكلفة القطعة")
        st.markdown("---")
        
        st.subheader("📦 القيمة المالية للمخزون (رأس المال)")
        df_stock_val = pd.read_sql("""
            SELECT SUM(stock * cost) as total_cost, SUM(stock * price) as total_revenue FROM variants
        """, conn).iloc[0]
        
        total_cost_stock = df_stock_val['total_cost'] or 0
        total_rev_stock = df_stock_val['total_revenue'] or 0
        potential_profit = total_rev_stock - total_cost_stock
        
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("رأس المال المجمد (التكلفة)", f"{total_cost_stock:,.0f} د.ع")
        col_s2.metric("المبيعات المتوقعة", f"{total_rev_stock:,.0f} د.ع")
        col_s3.metric("الربح الكامن", f"{potential_profit:,.0f} د.ع", delta="مكسب مستقبلي")
        st.markdown("---")
        
        c_best1, c_best2 = st.columns(2)
        with c_best1:
            st.subheader("🏆 أكثر القطع مبيعاً")
            df_top_items = pd.read_sql("""
                SELECT product_name as "المنتج", SUM(qty) as "العدد المباع" 
                FROM sales GROUP BY product_name ORDER BY SUM(qty) DESC LIMIT 5
            """, conn)
            if not df_top_items.empty: st.dataframe(df_top_items, use_container_width=True, hide_index=True)
            else: st.info("لا توجد بيانات كافية")
                
        with c_best2:
            st.subheader("🌟 أفضل الزبائن")
            df_top_cust = pd.read_sql("""
                SELECT c.name as "العميل", SUM(s.total) as "مجموع الشراء"
                FROM sales s JOIN customers c ON s.customer_id = c.id
                GROUP BY c.name ORDER BY SUM(s.total) DESC LIMIT 5
            """, conn)
            if not df_top_cust.empty: st.dataframe(df_top_cust, use_container_width=True, hide_index=True)
            else: st.info("لا توجد بيانات كافية")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
