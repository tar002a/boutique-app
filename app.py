import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
    /* --- Imports --- */
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@200;300;400;500;600;700;800;900&display=swap');

    /* --- Roots (Dark Mode) --- */
    :root {
        --primary-color: #B76E79; /* Dusty Rose */
        --secondary-color: #D4A5A5;
        --bg-color: #1C1C1E; /* iOS High Contrast Dark */
        --card-bg: #2C2C2E; /* Elevation 1 */
        --text-color: #FFFFFF; /* High Contrast White */
        --subtext-color: #AEAEB2; /* iOS Gray */
        --border-radius: 16px;
        --input-bg: #2C2C2E;
        --border-color: #3A3A3C;
    }

    /* --- Global RTL & Fonts --- */
    .stApp {
        direction: rtl;
        font-family: 'Cairo', sans-serif;
        background-color: var(--bg-color);
        color: var(--text-color);
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    
    /* Strict RTL Enforcement */
    .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, div, label, .stButton, .stTextInput, .stNumberInput, .stSelectbox {
        text-align: right !important;
        direction: rtl !important;
    }
    
    /* Input Labels */
    .stTextInput label, .stNumberInput label, .stSelectbox label {
        color: var(--subtext-color) !important;
        font-weight: 600 !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Cairo', sans-serif;
        font-weight: 700 !important;
        color: var(--text-color);
        margin-bottom: 10px;
    }

    /* --- Buttons (iOS Style) --- */
    .stButton button {
        width: 100%;
        height: 50px;
        border-radius: 50px; /* Pill shape */
        border: none;
        background-color: var(--primary-color);
        color: white;
        font-weight: 700;
        font-size: 16px;
        box-shadow: 0 4px 10px rgba(183, 110, 121, 0.3);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    .stButton button:hover {
        background-color: #a05a65;
        box-shadow: 0 6px 15px rgba(183, 110, 121, 0.4);
        transform: translateY(-2px);
    }
    .stButton button:active {
        transform: scale(0.96);
    }
    /* Secondary/Outline Button Tweak (if needed) */
    button[kind="secondary"] {
        background-color: transparent !important;
        border: 2px solid var(--primary-color) !important;
        color: var(--primary-color) !important;
        box-shadow: none !important;
    }

    /* --- Metric Cards --- */
    div[data-testid="metric-container"] {
        background-color: var(--card-bg);
        padding: 20px;
        border-radius: var(--border-radius);
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        border: 1px solid var(--border-color);
        transition: transform 0.2s;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
    }
    div[data-testid="metric-container"] > label {
        color: var(--subtext-color);
        font-size: 0.9rem;
    }

    /* --- Inputs & Selectboxes --- */
    /* --- Inputs & Selectboxes --- */
    div[data-baseweb="input"] {
        background-color: var(--input-bg);
        border-radius: 12px;
        border: 1px solid var(--border-color);
        color: white;
    }
    div[data-baseweb="input"] input {
        color: white !important; /* Ensure text is white */
        background-color: transparent !important;
    }
    div[data-baseweb="select"] > div {
        background-color: var(--input-bg);
        border-radius: 12px;
        border: 1px solid var(--border-color);
        color: white;
    }
    div[data-baseweb="select"] span {
        color: white !important;
    }
    
    /* --- Tabs (iOS Segmented Control Look) --- */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        border-radius: 12px;
        padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        background-color: rgba(44, 44, 46, 0.5);
        border-radius: 10px;
        border: none;
        color: var(--subtext-color);
        font-weight: 600;
        transition: all 0.2s;
        box-shadow: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3A3A3C !important;
        color: var(--primary-color) !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }

    /* --- Custom Item Card --- */
    /* --- Custom Item Card --- */
    .css-card {
        background-color: var(--card-bg);
        padding: 18px;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        margin-bottom: 12px;
        border: 1px solid var(--border-color);
        transition: all 0.2s ease;
    }
    .css-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        transform: translateY(-1px);
    }
    
    /* Toast override */
    div[data-baseweb="toast"] {
        font-family: 'Cairo', sans-serif;
    }
    /* --- Alerts Override --- */
    .stSuccess {
        background-color: #d1e7dd;
        color: #0f5132;
        border-color: #badbcc;
    }
    .stInfo {
        background-color: #e2e3e5;
        color: #41464b;
        border-color: #d3d6d8;
    }
    .stWarning {
        background-color: #fff3cd;
        color: #664d03;
        border-color: #ffecb5;
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
if 'last_customer_username' not in st.session_state:
    st.session_state.last_customer_username = None

# --- 2. اتصال قاعدة البيانات (Supabase) ---
@st.cache_resource
def init_connection():
    return psycopg2.connect(**st.secrets["postgres"])

try:
    conn = init_connection()
except Exception as e:
    st.error(f"فشل الاتصال بقاعدة البيانات: {e}")
    st.stop()

# دالة لتهيئة الجداول
def init_db():
    try:
        with conn.cursor() as c:
            c.execute("""CREATE TABLE IF NOT EXISTS public.variants (
                id SERIAL PRIMARY KEY, name TEXT, color TEXT, size TEXT, cost REAL, price REAL, stock INTEGER
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS public.customers (
                id SERIAL PRIMARY KEY, name TEXT, phone TEXT, address TEXT, username TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS public.sales (
                id SERIAL PRIMARY KEY, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
                qty INTEGER, total REAL, profit REAL, date TEXT, invoice_id TEXT
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS public.expenses (
                id SERIAL PRIMARY KEY, amount REAL, reason TEXT, date TEXT
            )""")
            conn.commit()
    except Exception as e:
        conn.rollback()

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
            try:
                with conn.cursor() as cur:
                    diff = new_qty - int(current_qty)
                    if diff != 0:
                        cur.execute("UPDATE public.variants SET stock = stock - %s WHERE id = %s", (int(diff), int(variant_id)))
                    cur.execute("UPDATE public.sales SET qty = %s, total = %s WHERE id = %s", (int(new_qty), float(new_total), int(sale_id)))
                    conn.commit(); st.rerun()
            except: conn.rollback()
    with c2:
        if st.button("🗑️ حذف العملية"):
            try:
                with conn.cursor() as cur:
                    cur.execute("UPDATE public.variants SET stock = stock + %s WHERE id = %s", (int(current_qty), int(variant_id)))
                    cur.execute("DELETE FROM public.sales WHERE id = %s", (int(sale_id),))
                    conn.commit(); st.rerun()
            except: conn.rollback()

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
            try:
                with conn.cursor() as cur:
                    cur.execute("UPDATE public.variants SET name=%s, color=%s, size=%s, cost=%s, price=%s, stock=%s WHERE id=%s", 
                                 (n_name, n_col, n_siz, float(n_cst), float(n_prc), int(n_stk), int(item_id)))
                    conn.commit(); st.rerun()
            except: conn.rollback()
    if st.button("🗑️ حذف الصنف نهائياً"):
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM public.variants WHERE id=%s", (int(item_id),))
                conn.commit(); st.rerun()
        except: conn.rollback()

# --- 4. تسجيل الدخول ---
def login_screen():
    st.title("✨ نواعم بوتيك")
    if st.button("🔓 دخول للنظام"):
        st.session_state.logged_in = True
        st.rerun()

# --- 5. التطبيق الرئيسي ---
def main_app():
    tabs = st.tabs(["🛍️ بيع", "📝 سجل", "👥 عملاء", "📦 مخزن", "💸 مصاريف", "📊 تقارير"])

    # === 1. البيع ===
    with tabs[0]:
        if st.session_state.sale_success:
            st.success("✅ تم حجز الطلب!")
            st.balloons()
            st.markdown("### 📋 انسخ الرسالة:")
            st.code(st.session_state.last_invoice_text, language="text")
            
            # Instagram Button
            if st.session_state.last_customer_username:
                ig_url = f"https://ig.me/m/{st.session_state.last_customer_username}"
                st.link_button(" إرسال الفاتورة عبر انستغرام", ig_url, type="primary")
            
            st.divider()
            if st.button("🔄 طلب جديد", type="primary"):
                st.session_state.sale_success = False; st.session_state.last_invoice_text = ""; st.rerun()
        else:
            with st.container(border=True):
                try:
                    df = pd.read_sql("SELECT * FROM public.variants WHERE stock > 0", conn)
                except: df = pd.DataFrame()

                srch = st.text_input("🔍 بحث...", label_visibility="collapsed")
                if srch and not df.empty:
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
                        
                        if st.button("🛒 أضف للسلة", type="secondary"):
                            item_dict = {
                                "id": int(r['id']),  
                                "name": r['name'], 
                                "color": r['color'], 
                                "size": r['size'], 
                                "cost": float(r['cost']), 
                                "price": float(p), 
                                "qty": int(q), 
                                "total": float(p*q)
                            }
                            st.session_state.cart.append(item_dict)
                            st.toast("تمت الإضافة", icon="✅")

            if st.session_state.cart:
                st.divider()
                st.markdown("### 🛒 سلة المشتريات")
                
                # Cart Items as Cards
                for i, item in enumerate(st.session_state.cart):
                    with st.container():
                        st.markdown(f"""
                        <div class="css-card" style="display: flex; justify-content: space-between; align-items: center;">
                            <div style="text-align: right;">
                                <div style="font-weight: 800; font-size: 1.1em; color: var(--text-color);">{item['name']}</div>
                                <div style="color: var(--subtext-color); font-size: 0.9em; margin-top: 4px;">{item['color']} | {item['size']}</div>
                                <div style="color: var(--primary-color); font-weight: 600; margin-top: 4px;">{item['qty']} × {item['price']:,.0f}</div>
                            </div>
                            <div style="text-align: left; font-weight: 800; color: var(--primary-color); font-size: 1.2em;">
                                {item['total']:,.0f}
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        # Option to remove item could be added here if needed in future

                st.divider()
                st.markdown("##### 👤 بيانات العميل")
                with st.container(border=True):
                    cust_type = st.radio("نوع العميل", ["جديد", "سابق"], horizontal=True)
                    cust_id_val, cust_name_val, cust_username_val, cust_phone_val, cust_address_val = None, "", "", "", ""
                    if cust_type == "سابق":
                        try:
                            curr_custs = pd.read_sql("SELECT id, name, phone, username, address FROM public.customers", conn)
                        except: curr_custs = pd.DataFrame()
                        
                        if not curr_custs.empty:
                            c_sel = st.selectbox("الاسم:", curr_custs.apply(lambda x: f"{x['name']} - {x['phone']}", axis=1).tolist())
                            cust_name_val = c_sel.split(" - ")[0]
                            selected_row = curr_custs[curr_custs['name'] == cust_name_val].iloc[0]
                            cust_id_val = int(selected_row['id'])
                            # Auto-fill username if exists
                            cust_username_val = selected_row['username'] if pd.notna(selected_row['username']) else ""
                            cust_phone_val = selected_row['phone'] if pd.notna(selected_row['phone']) else ""
                            cust_address_val = selected_row['address'] if pd.notna(selected_row['address']) else ""
                        else: st.warning("لا يوجد")
                    else:
                        c_n = st.text_input("الاسم (حساب الانستغرام)")
                        c_p = st.text_input("الهاتف")
                        c_a = st.text_input("العنوان")
                        cust_name_val = c_n
                        cust_username_val = c_n
                        cust_phone_val = c_p
                        cust_address_val = c_a
                
                tot = sum(x['total'] for x in st.session_state.cart)
                
                # Invoice Text Generation
                # Invoice Text Generation
                invoice_msg = "🌸 تم تثبيت طلبج بنجاح حبيبتي\n📄 تفاصيل الطلب:\n"
                for i, x in enumerate(st.session_state.cart):
                    invoice_msg += f"القطعة: {x['name']}\n"
                    invoice_msg += f"اللون: {x['color']} | القياس: {x['size']}\n"
                    invoice_msg += f"العدد: {x['qty']}\n"
                    invoice_msg += f"السعر: {x['price']:,.0f}\n"
                    if len(st.session_state.cart) > 1 and i < len(st.session_state.cart) - 1:
                        invoice_msg += "---\n"
                
                invoice_msg += f"التوصيل: مجاني 🎁\n"
                invoice_msg += f"المجموع الكلي: {tot:,.0f} د.ع\n"
                invoice_msg += f"📍 معلومات التوصيل:\n"
                invoice_msg += f"العنوان: {cust_address_val}\n"
                invoice_msg += f"الرقم: {cust_phone_val}\n"
                invoice_msg += f"✨ ملاحظة مهمة: من يوصل المندوب، ضروري تفتحين الطلب وتقيسين القطعة وتتأكدين منها قبل الدفع. هذا حقج حتى تضمنين قياسج وموديلج 100%.\n"
                invoice_msg += f"🚚 مدة التوصيل: خلال 2-4 أيام إن شاء الله. المندوب راح يتصل بيج قبل ما يوصل.\n\n"
                invoice_msg += f"تتهنين بيها مقدماً، وشكراً لثقتج بـ نواعم بوتيك 🤍"
                
                # Total Price Display
                st.markdown(f"""
                <div style="background-color: var(--input-bg); padding: 15px; border-radius: 12px; text-align: center; margin-bottom: 20px; border: 1px solid var(--border-color);">
                    <div style="font-size: 0.9em; color: var(--subtext-color);">المجموع الكلي</div>
                    <div style="font-size: 1.8em; font-weight: bold; color: var(--primary-color);">{tot:,.0f} د.ع</div>
                </div>
                """, unsafe_allow_html=True)

                if st.button("✅ إتمام البيع", type="primary"):
                    if not cust_name_val: st.error("الاسم مطلوب!"); st.stop()
                    
                    try:
                        with conn.cursor() as cur:
                            if cust_type == "جديد":
                                cur.execute("INSERT INTO public.customers (name, phone, address, username) VALUES (%s,%s,%s,%s) RETURNING id", (c_n, c_p, c_a, c_n))
                                cust_id_val = cur.fetchone()[0]
                            elif cust_type == "سابق" and cust_username_val:
                                # Update username for existing customer if we found it (or if we add an edit feature later, but for now just using what we fetched)
                                pass 
                            
                            baghdad_now = get_baghdad_time()
                            inv = baghdad_now.strftime("%Y%m%d%H%M")
                            dt = baghdad_now.strftime("%Y-%m-%d %H:%M")
                            
                            for x in st.session_state.cart:
                                cur.execute("UPDATE public.variants SET stock=stock-%s WHERE id=%s", (int(x['qty']), int(x['id'])))
                                profit_calc = (x['price'] - x['cost']) * x['qty']
                                cur.execute("""
                                    INSERT INTO public.sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id) 
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                                """, (int(cust_id_val), int(x['id']), x['name'], int(x['qty']), float(x['total']), float(profit_calc), dt, inv))
                            
                            conn.commit()
                            st.session_state.cart = []
                            st.session_state.sale_success = True
                            st.session_state.last_invoice_text = invoice_msg
                            st.session_state.last_customer_username = cust_username_val
                            st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"حدث خطأ: {e}")

    # === 2. السجل ===
    with tabs[1]:
        st.caption("آخر العمليات")
        try:
            df_s = pd.read_sql("""
                SELECT s.*, c.name as customer_name, v.color, v.size 
                FROM public.sales s 
                LEFT JOIN public.customers c ON s.customer_id = c.id 
                LEFT JOIN public.variants v ON s.variant_id = v.id 
                ORDER BY s.id DESC LIMIT 30
            """, conn)
            for i, r in df_s.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([4,1])
                    c_name = r['customer_name'] if r['customer_name'] else "غير مسجل"
                    
                    # تحضير نص اللون والقياس
                    details = ""
                    if pd.notna(r['color']) and pd.notna(r['size']):
                        details = f" | 🎨 {r['color']} - {r['size']}"
                    
                    c1.markdown(f"**{r['product_name']}** ({r['qty']})")
                    c1.caption(f"👤 {c_name} | 💰 {r['total']:,.0f}{details}")
                    if c2.button("⚙️", key=f"e{r['id']}"): edit_sale_dialog(r['id'], r['qty'], r['total'], r['variant_id'], r['product_name'])
        except: st.info("لا توجد مبيعات بعد")

    # === 3. العملاء ===
    with tabs[2]:
        try:
            # جلب بيانات العملاء مع إحصائيات المبيعات
            df_cust = pd.read_sql("""
                SELECT 
                    c.id, c.name, c.phone, c.username, c.address,
                    COALESCE(SUM(s.total), 0) as total_spend,
                    MAX(s.date) as last_purchase
                FROM public.customers c
                LEFT JOIN public.sales s ON c.id = s.customer_id
                GROUP BY c.id, c.name, c.phone, c.username, c.address
                ORDER BY total_spend DESC
            """, conn)
            
            if not df_cust.empty:
                # البحث
                search_query = st.text_input("🔍 بحث عن عميل (الاسم أو الهاتف)", "")
                if search_query:
                    mask = (
                        df_cust['name'].str.contains(search_query, case=False) | 
                        df_cust['phone'].str.contains(search_query, case=False) |
                        df_cust['username'].str.contains(search_query, case=False)
                    )
                    df_cust = df_cust[mask]
                
                st.divider()
                
                # عرض كارتات العملاء
                col1, col2 = st.columns(2)
                for i, r in df_cust.iterrows():
                    # توزيع الكارتات على عمودين
                    with (col1 if i % 2 == 0 else col2):
                        with st.container(border=True):
                            # تنسيق العنوان والتواصل
                            username_display = f"@{r['username']}" if r['username'] and r['username'] != r['name'] else ""
                            phone_display = f"📞 {r['phone']}" if r['phone'] else ""
                            
                            st.markdown(f"""
                            <div style="direction: rtl; text-align: right;">
                                <div style="font-weight: 800; font-size: 1.2em; color: var(--primary-color); margin-bottom: 4px;">
                                    {r['name']}
                                </div>
                                <div style="font-size: 0.9em; color: var(--subtext-color); margin-bottom: 8px;">
                                    {username_display} &nbsp; {phone_display}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # إحصائيات سريعة
                            c_stat1, c_stat2 = st.columns(2)
                            c_stat1.metric("مجموع الشراء", f"{r['total_spend']:,.0f}")
                            if r['last_purchase']:
                                # محاولة تنسيق التاريخ بشكل أفضل
                                try:
                                    last_date = r['last_purchase'].split(' ')[0]
                                except: last_date = r['last_purchase']
                                c_stat2.metric("آخر ظهور", last_date)
                            else:
                                c_stat2.caption("لم يشتري بعد")
                                
                            if r['address']:
                                st.caption(f"📍 {r['address']}")
                            
                            # زر واتساب إذا وجد الهاتف
                            if r['phone']:
                                wa_url = f"https://wa.me/{r['phone'].replace('+', '').replace(' ', '')}"
                                st.link_button("💬 واتساب", wa_url)
                                
            else:
                st.info("لا يوجد عملاء مسجلين حالياً")
        except Exception as e:
            st.error(f"حدث خطأ في عرض العملاء: {e}")

    # === 4. المخزون ===
    with tabs[3]:
        # --- 1. Metrics & Header ---
        try:
            # Metrics Calculation
            df_inv = pd.read_sql("SELECT * FROM public.variants ORDER BY name", conn)
            
            total_items_count = df_inv['stock'].sum() if not df_inv.empty else 0
            total_value_cost = (df_inv['stock'] * df_inv['cost']).sum() if not df_inv.empty else 0
            total_value_sell = (df_inv['stock'] * df_inv['price']).sum() if not df_inv.empty else 0
            total_potential_profit = total_value_sell - total_value_cost
            low_stock_count = df_inv[df_inv['stock'] < 5].shape[0] if not df_inv.empty else 0

            # Display Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("📦 عدد القطع", f"{total_items_count}")
            m2.metric("💰 قيمة المخزون (بيع)", f"{total_value_sell:,.0f}")
            m3.metric("📉 نواقص (<5)", f"{low_stock_count}", delta_color="inverse")
            m4.metric("💵 ربح متوقع", f"{total_potential_profit:,.0f}")
            
        except Exception as e:
            st.error(f"خطأ في الحسابات: {e}")
            df_inv = pd.DataFrame()

        st.divider()

        # --- 2. Controls (Search & Add) ---
        c_ctrl1, c_ctrl2 = st.columns([3, 1])
        with c_ctrl1:
            search_query = st.text_input("🔍 بحث عن صنف (الاسم، اللون، القياس)...", label_visibility="collapsed")
        with c_ctrl2:
            with st.popover("➕ إضافة صنف جديد", use_container_width=True):
                with st.form("add_new_stock"):
                    st.markdown("##### إضافة بضاعة جديدة")
                    nm = st.text_input("اسم المنتج")
                    cl = st.text_input("اللون")
                    sz = st.text_input("القياس")
                    c_f1, c_f2 = st.columns(2)
                    stk = c_f1.number_input("العدد", 1)
                    pr = c_f2.number_input("سعر البيع", 0.0)
                    cst = st.number_input("سعر التكلفة", 0.0)
                    if st.form_submit_button("حفظ", type="primary"):
                        try:
                            with conn.cursor() as cur:
                                cur.execute("INSERT INTO public.variants (name,color,size,stock,price,cost) VALUES (%s,%s,%s,%s,%s,%s)", 
                                            (nm, cl, sz, int(stk), float(pr), float(cst)))
                                conn.commit()
                                st.toast("تم الحفظ بنجاح", icon="✅")
                                st.rerun()
                        except Exception as e:
                            st.error(f"خطأ: {e}")

        # --- 3. Filter Logic ---
        if not df_inv.empty:
            filtered_df = df_inv.copy()
            if search_query:
                mask = (
                    filtered_df['name'].str.contains(search_query, case=False) | 
                    filtered_df['color'].str.contains(search_query, case=False) |
                    filtered_df['size'].str.contains(search_query, case=False)
                )
                filtered_df = filtered_df[mask]
            
            # --- 4. View Mode Selection ---
            view_mode = st.radio("طريقة العرض", ["كروت 🆔", "جدول 📄"], horizontal=True, label_visibility="collapsed")

            if view_mode == "جدول 📄":
                st.dataframe(
                    filtered_df[['name', 'color', 'size', 'stock', 'price', 'cost']],
                    column_config={
                        "name": "الاسم",
                        "color": "اللون",
                        "size": "القياس",
                        "stock": st.column_config.NumberColumn("العدد", help="الكمية المتوفرة"),
                        "price": st.column_config.NumberColumn("سعر البيع", format="%d د.ع"),
                        "cost": st.column_config.NumberColumn("التكلفة", format="%d د.ع"),
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                # Card View
                # Group by Name only
                unique_names = filtered_df['name'].unique()
                for p_name in unique_names:
                    p_group = filtered_df[filtered_df['name'] == p_name]
                    
                    # Calculate Product-Level Stats
                    total_stock_for_product = p_group['stock'].sum()
                    total_value_for_product = (p_group['stock'] * p_group['price']).sum()
                    
                    with st.container(border=True):
                        # Header Row: Name + Stats
                        c_h1, c_h2, c_h3 = st.columns([2, 1, 1])
                        c_h1.markdown(f"#### 👗 {p_name}")
                        c_h2.markdown(f"**📦 العدد الكلي:** {total_stock_for_product}")
                        c_h3.markdown(f"**💰 القيمة الكلية:** {total_value_for_product:,.0f}")
                        
                        st.markdown("---")
                        
                        # Body: Group by Color
                        unique_colors = p_group['color'].unique()
                        for color in unique_colors:
                            c_group = p_group[p_group['color'] == color]
                            
                            # Row for each color
                            r1, r2 = st.columns([1, 4])
                            with r1:
                                st.markdown(f"##### 🎨 {color}")
                            
                            with r2:
                                # Items as Chips
                                # We'll use a flex container for the chips
                                chips_html = '<div style="display: flex; gap: 8px; flex-wrap: wrap;">'
                                for _, row in c_group.iterrows():
                                    # Determine chip color based on stock
                                    bg_color = "#2C2C2E" # Default dark
                                    border_color = "#3A3A3C"
                                    text_color = "#FFFFFF"
                                    
                                    if row['stock'] == 0:
                                        border_color = "#FF453A" # Red
                                        bg_color = "rgba(255, 69, 58, 0.1)"
                                    elif row['stock'] < 5:
                                        border_color = "#FF9F0A" # Orange
                                        bg_color = "rgba(255, 159, 10, 0.1)"
                                    else:
                                        border_color = "#30D158" # Green
                                        bg_color = "rgba(48, 209, 88, 0.1)"

                                    chips_html += f"""<div style="border: 1px solid {border_color}; background-color: {bg_color}; padding: 5px 12px; border-radius: 20px; font-size: 0.9em; display: flex; align-items: center; gap: 5px;"><span style="font-weight: bold;">{row['size']}</span><span style="font-size: 0.8em; opacity: 0.8;">| {row['stock']} قطعة</span></div>"""
                                chips_html += "</div>"
                                st.markdown(chips_html, unsafe_allow_html=True)
                            
                            # Edit Buttons (Collapsible for cleaner look)
                            with st.expander(f"تعديل {p_name} - {color}"):
                                cols = st.columns(4)
                                for idx, (_, row) in enumerate(c_group.iterrows()):
                                    with cols[idx % 4]:
                                        if st.button(f"✏️ {row['size']}", key=f"ed_{row['id']}"):
                                            edit_stock_dialog(row['id'], row['name'], row['color'], row['size'], row['cost'], row['price'], row['stock'])

        else:
            st.info("المخزون فارغ، أضيفي منتجات جديدة.")

    # === 5. المصاريف ===
    with tabs[4]:
        st.header("💸 إدارة المصاريف")
        
        # نموذج إضافة مصروف
        with st.form("add_expense_form"):
            c1, c2 = st.columns([1, 3])
            amount = c1.number_input("المبلغ (د.ع)", min_value=1.0, step=250.0)
            reason = c2.text_input("سبب الصرف / التفاصيل")
            
            if st.form_submit_button("➕ تسجيل مصروف"):
                if reason and amount > 0:
                    try:
                        with conn.cursor() as cur:
                            dt = get_baghdad_time().strftime("%Y-%m-%d %H:%M")
                            cur.execute("INSERT INTO public.expenses (amount, reason, date) VALUES (%s, %s, %s)", (float(amount), reason, dt))
                            conn.commit()
                        st.success(f"تم تسجيل مصروف: {amount:,.0f} - {reason}")
                        st.rerun()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"حدث خطأ: {e}")
                else:
                    st.error("يرجى إدخال المبلغ والسبب")
        
        st.divider()
        st.subheader("📋 سجل المصاريف (آخر 50)")
        
        try:
            df_exp = pd.read_sql("SELECT * FROM public.expenses ORDER BY id DESC LIMIT 50", conn)
            if not df_exp.empty:
                # تجميل العرض
                for i, row in df_exp.iterrows():
                    with st.container(border=True):
                        c_ex1, c_ex2, c_ex3 = st.columns([1, 3, 1])
                        c_ex1.markdown(f"**{row['amount']:,.0f} د.ع**")
                        c_ex2.markdown(f"{row['reason']}")
                        c_ex3.caption(f"{row['date']}")
                        
                        if c_ex3.button("🗑️", key=f"del_exp_{row['id']}"):
                            try:
                                with conn.cursor() as cur:
                                    cur.execute("DELETE FROM public.expenses WHERE id = %s", (int(row['id']),))
                                    conn.commit()
                                    st.rerun()
                            except: conn.rollback()
            else:
                st.info("لا توجد مصاريف مسجلة")
        except:
            st.info("لا توجد مصاريف بعد")

    # === 6. التقارير الذكية ===
    with tabs[5]:
        st.header("📊 ذكاء الأعمال (BI)")
        try:
            today_baghdad = get_baghdad_time().strftime("%Y-%m-%d")
            # --- حسابات التواريخ ---
            now = get_baghdad_time()
            today_str = now.strftime("%Y-%m-%d")
            
            # 1. اليوم
            # التحقق من أن التنسيق في قاعدة البيانات هو YYYY-MM-DD
            # الاستعلام يستخدم LIKE لأن التاريخ مع الوقت
            
            # 2. آخر 7 أيام (الأسبوع الحالي)
            week_start = (now - timedelta(days=6)).strftime("%Y-%m-%d") # 7 أيام تشمل اليوم
            
            # 3. الـ 7 أيام السابقة
            prev_week_end = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            prev_week_start = (now - timedelta(days=13)).strftime("%Y-%m-%d")
            
            # 4. الشهر الحالي
            month_curr_str = now.strftime("%Y-%m")
            
            # 5. الشهر السابق
            # لتجنب مشاكل أول الشهر، نرجع لليوم الأول ثم نطرح يوم
            first_day_curr = now.replace(day=1)
            prev_month_date = first_day_curr - timedelta(days=1)
            month_prev_str = prev_month_date.strftime("%Y-%m")

            def get_stats(where_clause, params=None):
                try:
                    query = f"""
                        SELECT 
                            COALESCE(SUM(total), 0), 
                            COALESCE(SUM(profit), 0), 
                            COUNT(DISTINCT invoice_id) 
                        FROM public.sales 
                        WHERE {where_clause}
                    """
                    return pd.read_sql(query, conn, params=params).iloc[0]
                except:
                    return [0, 0, 0]

            def get_exp(where_clause):
                try:
                    q = f"SELECT COALESCE(SUM(amount), 0) FROM public.expenses WHERE {where_clause}"
                    return pd.read_sql(q, conn).iloc[0,0]
                except: return 0

            # جلب البيانات (مبيعات)
            stats_today = get_stats(f"date LIKE '{today_str}%'")
            stats_week = get_stats(f"date >= '{week_start}'")
            stats_prev_week = get_stats(f"date >= '{prev_week_start}' AND date < '{week_start}'")
            stats_month = get_stats(f"date LIKE '{month_curr_str}%'")
            stats_prev_month = get_stats(f"date LIKE '{month_prev_str}%'")

            # جلب البيانات (مصاريف)
            exp_today = get_exp(f"date LIKE '{today_str}%'")
            exp_week = get_exp(f"date >= '{week_start}'")
            exp_prev_week = get_exp(f"date >= '{prev_week_start}' AND date < '{week_start}'")
            exp_month = get_exp(f"date LIKE '{month_curr_str}%'")
            exp_prev_month = get_exp(f"date LIKE '{month_prev_str}%'")

            # عرض البيانات
            st.subheader("📅 ملخص المبيعات")
            
            # صف اليوم
            st.markdown(f"##### اليوم ({today_str})")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("مبيعات", f"{stats_today[0]:,.0f}", f"{stats_today[2]} فاتورة")
            c2.metric("أرباح (خام)", f"{stats_today[1]:,.0f}")
            c3.metric("مصاريف", f"{exp_today:,.0f}", delta_color="inverse")
            c4.metric("صافي الربح", f"{stats_today[1]-exp_today:,.0f}")
            
            st.divider()
            
            # صف الأسبوع
            st.markdown("##### 📅 الأسبوع (آخر 7 أيام)")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("مبيعات", f"{stats_week[0]:,.0f}", delta=f"{stats_week[0]-stats_prev_week[0]:,.0f}")
            c2.metric("أرباح (خام)", f"{stats_week[1]:,.0f}", delta=f"{stats_week[1]-stats_prev_week[1]:,.0f}")
            c3.metric("مصاريف", f"{exp_week:,.0f}", delta=f"{exp_week-exp_prev_week:,.0f}", delta_color="inverse")
            c4.metric("صافي الربح", f"{(stats_week[1]-exp_week):,.0f}", delta=f"{(stats_week[1]-exp_week)-(stats_prev_week[1]-exp_prev_week):,.0f}")
            
            st.caption(f"**الأسبوع السابق:** مبيعات: {stats_prev_week[0]:,.0f} | أرباح: {stats_prev_week[1]:,.0f} | صافي: {stats_prev_week[1]-exp_prev_week:,.0f}")
            
            st.divider()
            
            # صف الشهر
            st.markdown("##### 🗓️ الشهر الحالي")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("مبيعات", f"{stats_month[0]:,.0f}", delta=f"{stats_month[0]-stats_prev_month[0]:,.0f}")
            c2.metric("أرباح (خام)", f"{stats_month[1]:,.0f}", delta=f"{stats_month[1]-stats_prev_month[1]:,.0f}")
            c3.metric("مصاريف", f"{exp_month:,.0f}", delta=f"{exp_month-exp_prev_month:,.0f}", delta_color="inverse")
            c4.metric("صافي الربح", f"{(stats_month[1]-exp_month):,.0f}", delta=f"{(stats_month[1]-exp_month)-(stats_prev_month[1]-exp_prev_month):,.0f}")

            st.caption(f"**الشهر السابق ({month_prev_str}):** مبيعات: {stats_prev_month[0]:,.0f} | صافي: {stats_prev_month[1]-exp_prev_month:,.0f}")
            
            st.markdown("---")
            
            st.subheader("📦 القيمة المالية للمخزون (رأس المال)")
            df_stock_val = pd.read_sql("""
                SELECT SUM(stock * cost) as total_cost, SUM(stock * price) as total_revenue FROM public.variants
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
                    SELECT 
                        SUM(profit) as total_profit,
                        SUM(total) as total_sales,
                        SUM(qty) as total_qty,
                        product_name as name
                    FROM public.sales 
                    GROUP BY product_name 
                    ORDER BY SUM(profit) DESC 
                    LIMIT 10
                """, conn)
                
                if not df_top_items.empty: 
                    st.dataframe(
                        df_top_items,
                        column_config={
                            "name": "المنتج",
                            "total_qty": st.column_config.NumberColumn("العدد", help="عدد القطع المباعة"),
                            "total_sales": st.column_config.NumberColumn("المبيعات", format="%d د.ع"),
                            "total_profit": st.column_config.ProgressColumn(
                                "الربح", 
                                help="مجموع الربح من هذا المنتج",
                                format="%d د.ع",
                                min_value=0,
                                max_value=int(df_top_items['total_profit'].max()),
                            ),
                        },
                        use_container_width=True, 
                        hide_index=True
                    )
                else: st.info("لا توجد بيانات كافية")
                    
            with c_best2:
                st.subheader("🌟 أفضل الزبائن")
                df_top_cust = pd.read_sql("""
                    SELECT 
                        SUM(s.total) as total_spend,
                        COUNT(s.id) as orders_count,
                        c.name as name
                    FROM public.sales s 
                    JOIN public.customers c ON s.customer_id = c.id
                    GROUP BY c.name 
                    ORDER BY SUM(s.total) DESC 
                    LIMIT 10
                """, conn)
                
                if not df_top_cust.empty: 
                    st.dataframe(
                        df_top_cust,
                        column_config={
                            "name": "العميل",
                            "orders_count": st.column_config.NumberColumn("عدد الطلبات"),
                            "total_spend": st.column_config.ProgressColumn(
                                "مجموع الشراء", 
                                format="%d د.ع",
                                min_value=0,
                                max_value=int(df_top_cust['total_spend'].max()),
                            ),
                        },
                        use_container_width=True, 
                        hide_index=True
                    )
                else: st.info("لا توجد بيانات كافية")
        except Exception as e:
            st.info("البيانات قيد التجميع...")

if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
