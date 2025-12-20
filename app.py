import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor

# --- إعداد الصفحة ---
st.set_page_config(page_title="Nawaem System", layout="wide", page_icon="📊", initial_sidebar_state="collapsed")

# --- كلمة مرور الطوارئ (في حال لم يتم ضبط secrets) ---
DEFAULT_PASS = "1234"
ADMIN_PASSWORD = st.secrets.get("APP_PASSWORD", DEFAULT_PASS)

# --- دالة توقيت بغداد ---
def get_baghdad_time():
    tz = pytz.timezone('Asia/Baghdad')
    return datetime.now(tz)

# --- CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@200;300;400;500;600;700;800;900&display=swap');
    :root {
        --primary-color: #B76E79; --secondary-color: #D4A5A5;
        --bg-color: #1C1C1E; --card-bg: #2C2C2E;
        --text-color: #FFFFFF; --subtext-color: #AEAEB2;
        --border-radius: 16px; --input-bg: #2C2C2E; --border-color: #3A3A3C;
    }
    .stApp { direction: rtl; font-family: 'Cairo', sans-serif; background-color: var(--bg-color); color: var(--text-color); }
    .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, div, label, .stButton, .stTextInput, .stNumberInput, .stSelectbox {
        text-align: right !important; direction: rtl !important;
    }
    .stButton button {
        width: 100%; height: 50px; border-radius: 50px; border: none;
        background-color: var(--primary-color); color: white; font-weight: 700;
        box-shadow: 0 4px 10px rgba(183, 110, 121, 0.3); transition: all 0.3s;
    }
    .stButton button:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(183, 110, 121, 0.4); }
    div[data-testid="metric-container"] {
        background-color: var(--card-bg); padding: 20px; border-radius: var(--border-radius);
        border: 1px solid var(--border-color); text-align: center;
    }
    div[data-baseweb="input"], div[data-baseweb="select"] > div {
        background-color: var(--input-bg); border-radius: 12px; border: 1px solid var(--border-color); color: white;
    }
    div[data-baseweb="input"] input, div[data-baseweb="select"] span { color: white !important; }
    .css-card {
        background-color: var(--card-bg); padding: 18px; border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2); margin-bottom: 12px;
        border: 1px solid var(--border-color); transition: all 0.2s ease;
    }
    .css-card:hover { transform: translateY(-1px); }
</style>
""", unsafe_allow_html=True)

# --- 1. إدارة الجلسة ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'sale_success' not in st.session_state: st.session_state.sale_success = False
if 'last_invoice_text' not in st.session_state: st.session_state.last_invoice_text = ""
if 'last_customer_username' not in st.session_state: st.session_state.last_customer_username = None

# --- 2. إدارة قاعدة البيانات ---
def get_connection():
    return psycopg2.connect(**st.secrets["postgres"])

def run_query(query, params=None, fetch=False, commit=False):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if commit: conn.commit()
            if fetch: return cur.fetchall()
            return True
    except Exception as e:
        if conn: conn.rollback()
        # لا نوقف التطبيق عند الخطأ، بل نطبع رسالة في الكونسول فقط
        print(f"DB Error: {e}") 
        return None
    finally:
        if conn: conn.close()

def run_insert_returning(query, params):
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, params)
            new_id = cur.fetchone()[0]
            conn.commit()
            return new_id
    except Exception as e:
        if conn: conn.rollback()
        st.error(f"خطأ في الإدخال: {e}")
        return None
    finally:
        if conn: conn.close()

# --- إصلاح تلقائي لقاعدة البيانات (مهم جداً لحل مشكلتك) ---
def fix_schema():
    """تحويل الأعمدة القديمة النصية إلى تواريخ صحيحة"""
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # محاولة تحويل عمود التاريخ في المبيعات
            try:
                cur.execute("ALTER TABLE public.sales ALTER COLUMN date TYPE TIMESTAMP USING date::timestamp")
            except:
                conn.rollback() # العمود محول بالفعل أو هناك مشكلة بسيطة
            
            # محاولة تحويل عمود التاريخ في المصاريف
            try:
                cur.execute("ALTER TABLE public.expenses ALTER COLUMN date TYPE TIMESTAMP USING date::timestamp")
            except:
                conn.rollback()
            
            conn.commit()
    except Exception:
        pass # تجاهل الأخطاء إذا كانت القاعدة سليمة
    finally:
        if conn: conn.close()

# تهيئة الجداول
def init_db():
    queries = [
        """CREATE TABLE IF NOT EXISTS public.variants (
            id SERIAL PRIMARY KEY, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
        )""",
        """CREATE TABLE IF NOT EXISTS public.customers (
            id SERIAL PRIMARY KEY, name TEXT, phone TEXT, address TEXT, username TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS public.sales (
            id SERIAL PRIMARY KEY, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
            qty INTEGER, total REAL, profit REAL, date TIMESTAMP, invoice_id TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS public.expenses (
            id SERIAL PRIMARY KEY, amount REAL, reason TEXT, date TIMESTAMP
        )"""
    ]
    for q in queries:
        run_query(q, commit=True)
    
    # تشغيل الإصلاح مرة واحدة
    fix_schema()

init_db()

# --- 3. النوافذ المنبثقة ---
@st.dialog("تعديل عملية بيع")
def edit_sale_dialog(sale_id, current_qty, current_total, variant_id, product_name):
    st.warning(f"فاتورة: {product_name}")
    new_qty = st.number_input("الكمية", min_value=1, value=int(current_qty))
    new_total = st.number_input("الإجمالي", value=float(current_total))
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 حفظ التعديلات", type="primary"):
            diff = new_qty - int(current_qty)
            if diff != 0:
                run_query("UPDATE public.variants SET stock = stock - %s WHERE id = %s", (int(diff), int(variant_id)), commit=True)
            run_query("UPDATE public.sales SET qty = %s, total = %s WHERE id = %s", (int(new_qty), float(new_total), int(sale_id)), commit=True)
            st.rerun()
    with c2:
        if st.button("🗑️ حذف العملية"):
            run_query("UPDATE public.variants SET stock = stock + %s WHERE id = %s", (int(current_qty), int(variant_id)), commit=True)
            run_query("DELETE FROM public.sales WHERE id = %s", (int(sale_id),), commit=True)
            st.rerun()

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
        if st.form_submit_button("💾 حفظ التعديلات"):
            run_query("""
                UPDATE public.variants 
                SET name=%s, color=%s, size=%s, cost=%s, price=%s, stock=%s 
                WHERE id=%s
            """, (n_name, n_col, n_siz, float(n_cst), float(n_prc), int(n_stk), int(item_id)), commit=True)
            st.rerun()
    if st.button("🗑️ حذف الصنف نهائياً"):
        run_query("DELETE FROM public.variants WHERE id=%s", (int(item_id),), commit=True)
        st.rerun()

# --- 4. تسجيل الدخول ---
def login_screen():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>✨ نواعم بوتيك</h1>", unsafe_allow_html=True)
        with st.form("login"):
            password = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("🔓 دخول للنظام"):
                if password == ADMIN_PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("كلمة المرور غير صحيحة")

# --- 5. التطبيق الرئيسي ---
def main_app():
    with st.sidebar:
        if st.button("تسجيل الخروج"):
            st.session_state.logged_in = False
            st.rerun()

    tabs = st.tabs(["🛍️ بيع", "📝 سجل", "👥 عملاء", "📦 مخزن", "💸 مصاريف", "📊 تقارير"])

    # === 1. البيع ===
    with tabs[0]:
        if st.session_state.sale_success:
            st.success("✅ تم حجز الطلب!")
            st.balloons()
            st.code(st.session_state.last_invoice_text, language="text")
            if st.session_state.last_customer_username:
                st.link_button(" إرسال الفاتورة عبر انستغرام", f"https://ig.me/m/{st.session_state.last_customer_username}", type="primary")
            st.divider()
            if st.button("🔄 طلب جديد", type="primary"):
                st.session_state.sale_success = False; st.session_state.last_invoice_text = ""; st.rerun()
        else:
            with st.container(border=True):
                srch = st.text_input("🔍 بحث عن منتج...", placeholder="اكتب اسم المنتج أو اللون...")
                results = []
                if srch:
                    search_term = f"%{srch}%"
                    results = run_query("SELECT * FROM public.variants WHERE (name ILIKE %s OR color ILIKE %s) AND stock > 0 LIMIT 20", (search_term, search_term), fetch=True)
                else:
                    results = run_query("SELECT * FROM public.variants WHERE stock > 0 ORDER BY id DESC LIMIT 5", fetch=True)

                if results:
                    opts = {f"{r['name']} | {r['color']} ({r['size']})": r for r in results}
                    sel_key = st.selectbox("اختر المنتج:", list(opts.keys()), label_visibility="collapsed")
                    if sel_key:
                        r = opts[sel_key]
                        st.caption(f"سعر: {r['price']:,.0f} | متوفر: {r['stock']}")
                        c1, c2 = st.columns(2)
                        q = c1.number_input("العدد", 1, int(r['stock']), 1)
                        p = c2.number_input("سعر البيع", value=float(r['price']))
                        if st.button("🛒 أضف للسلة", type="secondary"):
                            st.session_state.cart.append({"id": int(r['id']), "name": r['name'], "color": r['color'], "size": r['size'], "cost": float(r['cost']), "price": float(p), "qty": int(q), "total": float(p*q)})
                            st.toast("تمت الإضافة", icon="✅")

            if st.session_state.cart:
                st.divider()
                st.markdown("### 🛒 سلة المشتريات")
                for item in st.session_state.cart:
                    st.markdown(f"""<div class="css-card" style="display:flex;justify-content:space-between;"><div><b>{item['name']}</b><br><small>{item['color']} | {item['size']}</small></div><div style="color:var(--primary-color)"><b>{item['total']:,.0f}</b></div></div>""", unsafe_allow_html=True)
                
                if st.button("إفراغ السلة"): st.session_state.cart = []; st.rerun()
                st.divider()
                with st.container(border=True):
                    cust_type = st.radio("العميل", ["جديد", "سابق"], horizontal=True)
                    cust_id_val, cust_name_val, cust_phone_val, cust_address_val, cust_username_val = None, "", "", "", ""
                    if cust_type == "سابق":
                        all_custs = run_query("SELECT id, name, phone, username, address FROM public.customers ORDER BY name", fetch=True)
                        if all_custs:
                            c_sel = st.selectbox("الاسم:", [f"{x['name']} - {x['phone']}" for x in all_custs])
                            if c_sel:
                                selected = next(x for x in all_custs if f"{x['name']} - {x['phone']}" == c_sel)
                                cust_id_val, cust_name_val, cust_phone_val, cust_address_val, cust_username_val = selected['id'], selected['name'], selected['phone'], selected['address'], selected['username']
                    else:
                        cust_name_val = st.text_input("الاسم")
                        cust_phone_val = st.text_input("الهاتف")
                        cust_address_val = st.text_input("العنوان")
                        cust_username_val = cust_name_val

                tot = sum(x['total'] for x in st.session_state.cart)
                st.markdown(f"<h2 style='text-align:center; color:var(--primary-color)'>{tot:,.0f} د.ع</h2>", unsafe_allow_html=True)

                if st.button("✅ إتمام البيع", type="primary"):
                    if not cust_name_val: st.error("الاسم مطلوب!"); st.stop()
                    try:
                        if cust_type == "جديد":
                            exist = run_query("SELECT id FROM public.customers WHERE phone = %s", (cust_phone_val,), fetch=True)
                            if exist: cust_id_val = exist[0]['id']
                            else: cust_id_val = run_insert_returning("INSERT INTO public.customers (name, phone, address, username) VALUES (%s,%s,%s,%s) RETURNING id", (cust_name_val, cust_phone_val, cust_address_val, cust_username_val))
                        
                        baghdad_now = get_baghdad_time()
                        inv_id = baghdad_now.strftime("%Y%m%d%H%M")
                        invoice_msg = f"🌸 طلب جديد\nالاسم: {cust_name_val}\nالعنوان: {cust_address_val}\n---\n"
                        
                        for x in st.session_state.cart:
                            run_query("UPDATE public.variants SET stock=stock-%s WHERE id=%s", (int(x['qty']), int(x['id'])), commit=True)
                            profit = (x['price'] - x['cost']) * x['qty']
                            run_query("INSERT INTO public.sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (cust_id_val, x['id'], x['name'], x['qty'], x['total'], profit, baghdad_now, inv_id), commit=True)
                            invoice_msg += f"{x['name']} ({x['qty']}) - {x['price']:,.0f}\n"
                        
                        invoice_msg += f"---\nالمجموع: {tot:,.0f} د.ع"
                        st.session_state.cart = []
                        st.session_state.sale_success = True
                        st.session_state.last_invoice_text = invoice_msg
                        st.session_state.last_customer_username = cust_username_val
                        st.rerun()
                    except Exception as e: st.error(f"حدث خطأ: {e}")

    # === 2. السجل ===
    with tabs[1]:
        log = run_query("SELECT s.*, c.name as cname FROM public.sales s LEFT JOIN public.customers c ON s.customer_id=c.id ORDER BY s.id DESC LIMIT 30", fetch=True)
        if log:
            for r in log:
                with st.container(border=True):
                    c1, c2 = st.columns([4,1])
                    c1.markdown(f"**{r['product_name']}** ({r['qty']}) | {r['total']:,.0f}")
                    c1.caption(f"{r['cname']} | {r['date']}")
                    if c2.button("⚙️", key=f"e{r['id']}"): edit_sale_dialog(r['id'], r['qty'], r['total'], r['variant_id'], r['product_name'])
        else: st.info("السجل فارغ")

    # === 3. العملاء ===
    with tabs[2]:
        sq = st.text_input("بحث عميل...")
        q = "SELECT c.*, SUM(s.total) as tot FROM public.customers c LEFT JOIN public.sales s ON c.id=s.customer_id"
        p = ()
        if sq: q += " WHERE c.name ILIKE %s OR c.phone ILIKE %s"; p = (f"%{sq}%", f"%{sq}%")
        q += " GROUP BY c.id ORDER BY tot DESC LIMIT 50"
        custs = run_query(q, p, fetch=True)
        if custs:
            for c in custs:
                with st.container(border=True):
                    st.markdown(f"**{c['name']}** - {c['phone']}")
                    st.caption(f"العنوان: {c['address']} | المشتريات: {c['tot'] or 0:,.0f}")

    # === 4. المخزون ===
    with tabs[3]:
        res = run_query("SELECT SUM(stock) as s, SUM(stock*price) as v FROM public.variants", fetch=True)
        # حماية ضد القيم الفارغة
        if res and res[0]['s']:
            st.metric("📦 المخزون", f"{res[0]['s']}", f"{res[0]['v']:,.0f} د.ع قيمة بيعية")
        
        c1, c2 = st.columns([3,1])
        s_term = c1.text_input("بحث مخزون...", label_visibility="collapsed")
        with c2.popover("➕ إضافة"):
            with st.form("new_prod"):
                n, cl, sz = st.text_input("الاسم"), st.text_input("لون"), st.text_input("قياس")
                stk, pr, cst = st.number_input("العدد", 1), st.number_input("بيع", 0.0), st.number_input("كلفة", 0.0)
                if st.form_submit_button("حفظ"):
                    run_query("INSERT INTO public.variants (name,color,size,stock,price,cost) VALUES (%s,%s,%s,%s,%s,%s)", (n,cl,sz,stk,pr,cst), commit=True); st.rerun()
        
        q_inv = "SELECT * FROM public.variants"
        p_inv = ()
        if s_term: q_inv += " WHERE name ILIKE %s OR color ILIKE %s"; p_inv = (f"%{s_term}%", f"%{s_term}%")
        inv = run_query(q_inv + " ORDER BY name", p_inv, fetch=True)
        
        if inv:
            for r in inv:
                with st.container(border=True):
                    c1, c2 = st.columns([4,1])
                    c1.markdown(f"**{r['name']}** | {r['color']} - {r['size']}")
                    c1.caption(f"عدد: {r['stock']} | سعر: {r['price']:,.0f}")
                    if c2.button("✏️", key=f"ei{r['id']}"): edit_stock_dialog(r['id'], r['name'], r['color'], r['size'], r['cost'], r['price'], r['stock'])

    # === 5. المصاريف ===
    with tabs[4]:
        with st.form("exp"):
            a, r = st.number_input("مبلغ"), st.text_input("سبب")
            if st.form_submit_button("حفظ") and r:
                run_query("INSERT INTO public.expenses (amount, reason, date) VALUES (%s,%s,%s)", (a, r, get_baghdad_time()), commit=True); st.rerun()
        
        exps = run_query("SELECT * FROM public.expenses ORDER BY id DESC LIMIT 20", fetch=True)
        if exps:
            for x in exps:
                c1, c2, c3 = st.columns([1,3,1])
                c1.write(f"{x['amount']:,.0f}"); c2.write(x['reason']); 
                if c3.button("🗑️", key=f"de{x['id']}"): run_query("DELETE FROM public.expenses WHERE id=%s", (x['id'],), commit=True); st.rerun()

    # === 6. التقارير ===
    with tabs[5]:
        st.subheader("📊 التقارير")
        
        # حماية ضد الأخطاء في التقارير
        def safe_get_stats(cond):
            res = run_query(f"SELECT COALESCE(SUM(total),0) as s, COALESCE(SUM(profit),0) as p FROM public.sales WHERE {cond}", fetch=True)
            return res[0] if res else {'s': 0, 'p': 0}

        def safe_get_exp(cond):
            res = run_query(f"SELECT COALESCE(SUM(amount),0) as a FROM public.expenses WHERE {cond}", fetch=True)
            return res[0]['a'] if res else 0

        # اليوم
        d_stat = safe_get_stats("date::date = CURRENT_DATE")
        d_exp = safe_get_exp("date::date = CURRENT_DATE")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("مبيعات اليوم", f"{d_stat['s']:,.0f}")
        c2.metric("أرباح اليوم", f"{d_stat['p']:,.0f}")
        c3.metric("صافي اليوم", f"{d_stat['p'] - d_exp:,.0f}")
        st.divider()
        
        # الأسبوع
        w_stat = safe_get_stats("date >= CURRENT_DATE - INTERVAL '7 days'")
        w_exp = safe_get_exp("date >= CURRENT_DATE - INTERVAL '7 days'")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("مبيعات أسبوع", f"{w_stat['s']:,.0f}")
        c2.metric("مصاريف أسبوع", f"{w_exp:,.0f}")
        c3.metric("صافي أسبوع", f"{w_stat['p'] - w_exp:,.0f}")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
