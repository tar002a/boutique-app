@@ -3,208 +3,307 @@
import pandas as pd
from datetime import datetime
import pytz
from contextlib import contextmanager

# --- إعداد الصفحة ---
st.set_page_config(page_title="Nawaem System", layout="wide", page_icon="📊", initial_sidebar_state="collapsed")

# --- تحسين الاتصال بقاعدة البيانات (Context Manager) ---
DB_NAME = 'boutique_v3.db'

@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER, is_active BOOLEAN DEFAULT 1
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT, username TEXT
        )""")
        c.execute("""CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
            qty INTEGER, total REAL, profit REAL, date TEXT, invoice_id TEXT
        )""")
        conn.commit()

# استدعاء التهيئة مرة واحدة عند التشغيل
init_db()

# --- دالة توقيت بغداد ---
def get_baghdad_time():
    tz = pytz.timezone('Asia/Baghdad')
    return datetime.now(tz)

# --- CSS (نفس التنسيق السابق) ---
# --- CSS ---
st.markdown("""
<style>
    .stApp {direction: rtl;}
    div[data-testid="column"] {text-align: right;}
    .stock-warning {color: red; font-weight: bold; font-size: 0.8em;}
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
    /* تنسيق خاص للأرقام المالية */
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

# --- إدارة الجلسة ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
# --- 1. إدارة الجلسة ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'sale_success' not in st.session_state:
    st.session_state.sale_success = False
if 'last_invoice_text' not in st.session_state:
    st.session_state.last_invoice_text = ""

# --- 4. شاشة الدخول (محسنة) ---
def login_screen():
    st.title("🌸 نواعم بوتيك - تسجيل الدخول")
    
    # كلمة المرور الافتراضية (يمكنك تغييرها أو وضعها في st.secrets)
    CORRECT_PASSWORD = "admin" 
    
    c1, c2, c3 = st.columns([1,2,1])
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
        with st.form("login_form"):
            password = st.text_input("كلمة المرور", type="password")
            submit = st.form_submit_button("دخول 🔐")
            
            if submit:
                if password == CORRECT_PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("كلمة المرور خاطئة!")

# --- دوال مساعدة ---
def add_to_cart(item, qty, price):
    st.session_state.cart.append({
        "id": int(item['id']), "name": item['name'], 
        "color": item['color'], "size": item['size'], 
        "cost": item['cost'], "price": price, 
        "qty": qty, "total": price*qty
    })
    st.toast("تمت الإضافة للسلة", icon="✅")

# --- التطبيق الرئيسي ---
def main_app():
    # زر تسجيل الخروج
    with st.sidebar:
        if st.button("تسجيل خروج 🚪"):
            st.session_state.logged_in = False
            st.rerun()
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
            conn.commit(); st.rerun()
    if st.button("🗑️ حذف نهائي"):
        conn.execute("DELETE FROM variants WHERE id=?", (item_id,))
        conn.commit(); st.rerun()

# --- 4. تسجيل الدخول ---
def login_screen():
    st.title("🌸 نواعم بوتيك")
    if st.button("دخول للنظام"):
        st.session_state.logged_in = True
        st.rerun()

    tabs = st.tabs(["🛒 نقطة البيع", "📋 السجل", "👥 العملاء", "📦 المخزون", "📊 التقارير"])
# --- 5. التطبيق الرئيسي ---
def main_app():
    tabs = st.tabs(["🛒 بيع", "📋 سجل", "👥 عملاء", "📦 مخزن", "📊 تقارير ذكية"])

    # === 1. البيع (تحسين البحث والأداء) ===
    # === 1. البيع ===
    with tabs[0]:
        col_pos, col_cart = st.columns([2, 1])
        
        with col_pos:
            st.subheader("بحث عن منتج")
            search_term = st.text_input("🔍 ابحث باسم المنتج أو اللون...", label_visibility="collapsed")
            
            query = "SELECT * FROM variants WHERE stock > 0 AND is_active = 1"
            params = []
            if search_term:
                query += " AND (name LIKE ? OR color LIKE ?)"
                params = [f'%{search_term}%', f'%{search_term}%']
            
            with get_db_connection() as conn:
                df = pd.read_sql(query, conn, params=params)

            if not df.empty:
                # عرض النتائج كبطاقات بدل القائمة المنسدلة لتحسين التجربة
                for _, row in df.iterrows():
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                        with c1:
                            st.markdown(f"**{row['name']}**")
                            st.caption(f"{row['color']} | {row['size']}")
                            if row['stock'] < 3:
                                st.markdown(f"<span class='stock-warning'>⚠️ باقي {row['stock']} فقط</span>", unsafe_allow_html=True)
                        with c2:
                            price_val = st.number_input("السعر", value=float(row['price']), key=f"p_{row['id']}")
                        with c3:
                            qty_val = st.number_input("العدد", 1, int(row['stock']), 1, key=f"q_{row['id']}")
                        with c4:
                            st.write("") # مسافة
                            if st.button("أضف", key=f"add_{row['id']}", type="primary"):
                                add_to_cart(row, qty_val, price_val)

        # سلة المشتريات (على اليسار)
        with col_cart:
            st.subheader("🛒 السلة")
        if st.session_state.sale_success:
            st.success("✅ تم حجز الطلب!")
            st.balloons()
            st.markdown("### 📋 انسخ الرسالة:")
            st.code(st.session_state.last_invoice_text, language="text")
            if st.button("🔄 طلب جديد", type="primary"):
                st.session_state.sale_success = False; st.session_state.last_invoice_text = ""; st.rerun()
        else:
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
                            st.session_state.cart.append({"id": int(r['id']), "name": r['name'], "color": r['color'], "size": r['size'], "cost": r['cost'], "price": p, "qty": q, "total": p*q})
                            st.toast("تمت الإضافة", icon="✅")

            if st.session_state.cart:
                total_cart = 0
                for idx, item in enumerate(st.session_state.cart):
                    with st.container(border=True):
                        st.text(f"{item['name']} - {item['color']}")
                        c_a, c_b = st.columns(2)
                        c_a.text(f"{item['qty']} x {item['price']:,.0f}")
                        c_b.text(f"= {item['total']:,.0f}")
                        total_cart += item['total']
                        if st.button("❌", key=f"del_{idx}"):
                            st.session_state.cart.pop(idx)
                            st.rerun()
                
                st.divider()
                st.markdown(f"### المجموع: {total_cart:,.0f} د.ع")
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

                # إتمام البيع
                cust_name = st.text_input("اسم العميل (اختياري)")
                if st.button("✅ إتمام العملية", type="primary", use_container_width=True):
                    with get_db_connection() as conn:
                        cur = conn.cursor()
                        # (يمكن إضافة منطق حفظ العميل هنا)
                        cust_id = 0 # افتراضي
                        if cust_name:
                            cur.execute("INSERT INTO customers (name, phone, address) VALUES (?,?,?)", (cust_name, "", ""))
                            cust_id = cur.lastrowid
                        
                        baghdad_now = get_baghdad_time()
                        inv_id = baghdad_now.strftime("%Y%m%d%H%M")
                        dt = baghdad_now.strftime("%Y-%m-%d %H:%M")
                        
                        for item in st.session_state.cart:
                            cur.execute("UPDATE variants SET stock=stock-? WHERE id=?", (item['qty'], item['id']))
                            profit = (item['price'] - item['cost']) * item['qty']
                            cur.execute("""
                                INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) 
                                VALUES (?,?,?,?,?,?,?,?)
                            """, (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, dt, inv_id))
                        
                        conn.commit()
                    
                    st.session_state.cart = []
                    st.success("تم حفظ العملية بنجاح!")
                    st.balloons()
                    st.rerun()

    # === 5. التقارير الذكية (تحديث الأداء) ===
                tot = 0; invoice_msg = "تم حجز الطلب ✅\n"
                for x in st.session_state.cart:
                    tot += x['total']
                    invoice_msg += f"{x['name']}\n{x['color']}\n{x['size']}\n"
                    if len(st.session_state.cart) > 1: invoice_msg += "---\n"
                invoice_msg += f"{tot:,.0f}\nالتوصيل مجاني\nالف عافية حياتي 🌸🌸🌸🌸"
                st.markdown(f"**الإجمالي: {tot:,.0f} د.ع**")

                if st.button("✅ إتمام البيع ونسخ", type="primary"):
                    if not cust_name_val: st.error("الاسم مطلوب!"); st.stop()
                    cur = conn.cursor()
                    if cust_type == "جديد":
                        cur.execute("INSERT INTO customers (name, phone, address) VALUES (?,?,?)", (c_n, c_p, c_a))
                        cust_id_val = cur.lastrowid
                    baghdad_now = get_baghdad_time()
                    inv = baghdad_now.strftime("%Y%m%d%H%M")
                    dt = baghdad_now.strftime("%Y-%m-%d %H:%M")
                    for x in st.session_state.cart:
                        cur.execute("UPDATE variants SET stock=stock-? WHERE id=?", (x['qty'], x['id']))
                        prf = (x['price']-x['cost'])*x['qty']
                        cur.execute("INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) VALUES (?,?,?,?,?,?,?,?)", (cust_id_val, x['id'], x['name'], x['qty'], x['total'], prf, dt, inv))
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
                    for c in cl.replace('،',',').split(','):
                        for s in sz.replace('،',',').split(','):
                            if c.strip() and s.strip(): conn.execute("INSERT INTO variants (name,color,size,stock,price,cost) VALUES (?,?,?,?,?,?)", (nm, c.strip(), s.strip(), stk, pr, cst))
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

    # === 5. التقارير الذكية (تم التطوير هنا) ===
    with tabs[4]:
        st.header("📊 لوحة المعلومات")
        st.header("📊 ذكاء الأعمال (BI)")
        
        # 1. ملخص اليوم
        today_baghdad = get_baghdad_time().strftime("%Y-%m-%d")
        df_tdy = pd.read_sql(f"SELECT SUM(total), SUM(profit) FROM sales WHERE date LIKE '{today_baghdad}%'", conn).iloc[0]
        
        st.subheader(f"📅 أداء اليوم ({today_baghdad})")
        col_t1, col_t2 = st.columns(2)
        col_t1.metric("مبيعات اليوم", f"{df_tdy[0] or 0:,.0f} د.ع")
        col_t2.metric("أرباح اليوم الصافية", f"{df_tdy[1] or 0:,.0f} د.ع", help="الربح بعد خصم تكلفة القطعة")
        
        st.markdown("---")

        with get_db_connection() as conn:
            # استخدام استعلامات مجمعة بدل تحميل كل البيانات
            today_str = get_baghdad_time().strftime("%Y-%m-%d")
            
            df_today = pd.read_sql("SELECT SUM(total) as sales, SUM(profit) as net FROM sales WHERE date LIKE ?", conn, params=(f'{today_str}%',))
            sales_today = df_today['sales'].iloc[0] or 0
            profit_today = df_today['net'].iloc[0] or 0
            
            col1, col2 = st.columns(2)
            col1.metric("مبيعات اليوم", f"{sales_today:,.0f}", delta="د.ع")
            col2.metric("أرباح اليوم", f"{profit_today:,.0f}", delta_color="normal")
            
            st.divider()
            
            # رسم بياني لأكثر المنتجات مبيعاً
            st.subheader("أكثر الأصناف مبيعاً (العدد)")
            df_chart = pd.read_sql("SELECT product_name, SUM(qty) as total_qty FROM sales GROUP BY product_name ORDER BY total_qty DESC LIMIT 10", conn)
            if not df_chart.empty:
                st.bar_chart(df_chart.set_index('product_name'))

# نقطة الدخول
        # 2. تقييم المخزون (Assets Valuation)
        st.subheader("📦 القيمة المالية للمخزون (رأس المال)")
        # حساب تكلفة المخزون وسعر البيع المتوقع
        df_stock_val = pd.read_sql("""
            SELECT 
                SUM(stock * cost) as total_cost,
                SUM(stock * price) as total_revenue
            FROM variants
        """, conn).iloc[0]
        
        total_cost_stock = df_stock_val['total_cost'] or 0
        total_rev_stock = df_stock_val['total_revenue'] or 0
        potential_profit = total_rev_stock - total_cost_stock
        
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.metric("رأس المال المجمد (التكلفة)", f"{total_cost_stock:,.0f} د.ع", help="مجموع المبالغ التي دفعتها لشراء البضاعة الحالية")
        col_s2.metric("المبيعات المتوقعة", f"{total_rev_stock:,.0f} د.ع", help="المبلغ الذي ستحصل عليه لو بعت كل شيء")
        col_s3.metric("الربح الكامن", f"{potential_profit:,.0f} د.ع", delta="مكسب مستقبلي", help="الربح الذي ستحققه عند بيع المخزون بالكامل")
        
        st.markdown("---")
        
        # 3. الأفضل مبيعاً والزبائن
        c_best1, c_best2 = st.columns(2)
        
        with c_best1:
            st.subheader("🏆 أكثر القطع مبيعاً")
            df_top_items = pd.read_sql("""
                SELECT product_name as 'المنتج', SUM(qty) as 'العدد المباع' 
                FROM sales 
                GROUP BY product_name 
                ORDER BY SUM(qty) DESC 
                LIMIT 5
            """, conn)
            if not df_top_items.empty:
                st.dataframe(df_top_items, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد بيانات كافية")
                
        with c_best2:
            st.subheader("🌟 أفضل الزبائن")
            df_top_cust = pd.read_sql("""
                SELECT c.name as 'العميل', SUM(s.total) as 'مجموع الشراء'
                FROM sales s
                JOIN customers c ON s.customer_id = c.id
                GROUP BY c.name
                ORDER BY SUM(s.total) DESC
                LIMIT 5
            """, conn)
            if not df_top_cust.empty:
                st.dataframe(df_top_cust, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد بيانات كافية")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
