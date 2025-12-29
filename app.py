import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import psycopg2
from psycopg2.extras import execute_values
import time

# --- 1. إعداد الصفحة والتصميم (Configuration & CSS) ---
st.set_page_config(
    page_title="Nawaem POS 🚀", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="expanded"
)

# تصميم عصري (Glassmorphism & Dark Mode)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800&display=swap');
    
    :root {
        --primary: #D48896;
        --bg-dark: #0E1117;
        --card-bg: rgba(30, 30, 30, 0.4);
    }

    * { font-family: 'Cairo', sans-serif !important; direction: rtl; }
    
    .stApp { background-color: var(--bg-dark); }
    
    /* تحسين القائمة الجانبية */
    section[data-testid="stSidebar"] {
        background-color: #161a20;
        border-left: 1px solid #333;
    }

    /* الكروت والحاويات */
    div.stContainer {
        background: var(--card-bg);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 15px;
    }

    /* تحسين حقول الإدخال */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #1E1E1E !important;
        border: 1px solid #444 !important;
        color: white !important;
        border-radius: 8px !important;
    }

    /* الأزرار */
    .stButton button {
        border-radius: 8px;
        font-weight: 700;
        border: none;
        transition: all 0.2s ease-in-out;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(212, 136, 150, 0.3);
    }
    
    /* تكبير أرقام المقاييس */
    div[data-testid="stMetricValue"] {
        color: var(--primary) !important;
        font-weight: 800 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. الاتصال بقاعدة البيانات (Database Layer) ---

@st.cache_resource
def get_db_connection():
    """إنشاء اتصال دائم (Singleton)"""
    try:
        return psycopg2.connect(**st.secrets["postgres"])
    except Exception as e:
        st.error(f"❌ خطأ في الاتصال بقاعدة البيانات: {e}")
        st.stop()

def run_query(query, params=None, fetch=True, commit=False):
    """دالة مساعدة لتنفيذ الاستعلامات بأمان"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if commit:
                conn.commit()
                return True
            if fetch:
                col_names = [desc[0] for desc in cur.description]
                data = cur.fetchall()
                return pd.DataFrame(data, columns=col_names)
    except Exception as e:
        conn.rollback()
        st.error(f"Database Error: {e}")
        return None

def init_db():
    """تهيئة الجداول عند أول تشغيل"""
    conn = get_db_connection()
    with conn.cursor() as c:
        # جدول المنتجات
        c.execute("""CREATE TABLE IF NOT EXISTS public.variants (
            id SERIAL PRIMARY KEY, name TEXT, color TEXT, size TEXT, 
            cost REAL, price REAL, stock INTEGER
        )""")
        # جدول العملاء
        c.execute("""CREATE TABLE IF NOT EXISTS public.customers (
            id SERIAL PRIMARY KEY, name TEXT, phone TEXT, address TEXT, username TEXT
        )""")
        # جدول المبيعات
        c.execute("""CREATE TABLE IF NOT EXISTS public.sales (
            id SERIAL PRIMARY KEY, customer_id INTEGER, variant_id INTEGER, product_name TEXT, 
            qty INTEGER, total REAL, profit REAL, date TIMESTAMP, invoice_id TEXT, delivery_duration TEXT
        )""")
        # جدول المصاريف
        c.execute("""CREATE TABLE IF NOT EXISTS public.expenses (
            id SERIAL PRIMARY KEY, amount REAL, reason TEXT, date TIMESTAMP
        )""")
        # جدول الرواجع
        c.execute("""CREATE TABLE IF NOT EXISTS public.returns (
            id SERIAL PRIMARY KEY, sale_id INTEGER, variant_id INTEGER, customer_id INTEGER,
            product_name TEXT, product_details TEXT, qty INTEGER, return_amount REAL, 
            return_date TIMESTAMP, status TEXT
        )""")
        conn.commit()

# --- 3. جلب البيانات (Caching & Optimization) ---

@st.cache_data(ttl=60)
def get_inventory():
    return run_query("SELECT * FROM public.variants ORDER BY name")

@st.cache_data(ttl=300)
def get_customers():
    return run_query("SELECT * FROM public.customers ORDER BY name")

@st.cache_data(ttl=60)
def get_sales(limit=100):
    return run_query(f"SELECT * FROM public.sales ORDER BY date DESC LIMIT {limit}")

def clear_all_cache():
    """تفريغ الكاش لتحديث البيانات"""
    get_inventory.clear()
    get_customers.clear()
    get_sales.clear()

def get_time():
    return datetime.now(pytz.timezone('Asia/Baghdad'))

# --- 4. منطق التطبيق (Callbacks Logic) ---
# استخدام Callbacks يجعل التطبيق أسرع لأنه ينفذ الكود قبل إعادة تحميل الصفحة

if 'cart' not in st.session_state: st.session_state.cart = []
if 'db_inited' not in st.session_state:
    init_db()
    st.session_state.db_inited = True

def add_to_cart_callback():
    selection = st.session_state.get('pos_selection')
    if not selection: return
    
    # استخراج البيانات من النص المختار
    df = get_inventory()
    # التنسيق المتوقع: "Name | Color (Size)"
    try:
        prod_name = selection.split(" | ")[0]
        prod_color = selection.split(" | ")[1].split(" (")[0]
        item_row = df[(df['name'] == prod_name) & (df['color'] == prod_color)].iloc[0]
        
        qty = st.session_state.get('pos_qty', 1)
        price = st.session_state.get('pos_price', item_row['price'])
        
        cart_item = {
            "id": int(item_row['id']), "name": item_row['name'],
            "color": item_row['color'], "size": item_row['size'],
            "price": price, "qty": qty, "cost": float(item_row['cost']),
            "total": price * qty
        }
        st.session_state.cart.append(cart_item)
        st.toast(f"🛒 أضيف: {item_row['name']}", icon="✅")
    except:
        st.error("حدث خطأ أثناء إضافة المنتج")

def remove_from_cart_callback(idx):
    st.session_state.cart.pop(idx)

def checkout_callback():
    if not st.session_state.cart:
        st.error("السلة فارغة"); return

    # التحقق من العميل
    c_select = st.session_state.get('c_select')
    c_name = st.session_state.get('c_name')
    if c_select == "عميل جديد" and not c_name:
        st.error("الاسم مطلوب"); return

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. معالجة العميل
            cust_id = None
            if c_select == "عميل جديد":
                cur.execute("INSERT INTO public.customers (name, phone, address, username) VALUES (%s, %s, %s, %s) RETURNING id", 
                           (c_name, st.session_state.c_phone, st.session_state.c_addr, c_name))
                cust_id = cur.fetchone()[0]
                customer_display = c_name
                customer_addr = st.session_state.c_addr
            else:
                df_cust = get_customers()
                cust_data = df_cust[df_cust['name'] == c_select].iloc[0]
                cust_id = int(cust_data['id'])
                customer_display = cust_data['name']
                customer_addr = cust_data['address']

            # 2. تحضير البيانات للإدخال الدفعي (Batch Insert)
            inv_id = get_time().strftime("%Y%m%d%H%M")
            sales_data = []
            
            for item in st.session_state.cart:
                # خصم المخزون
                cur.execute("UPDATE public.variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
                # تحضير بيانات البيع
                profit = (item['price'] - item['cost']) * item['qty']
                sales_data.append((
                    cust_id, item['id'], item['name'], item['qty'], item['total'], 
                    profit, get_time(), inv_id, st.session_state.c_dur
                ))

            # 3. تنفيذ البيع دفعة واحدة
            execute_values(cur, """
                INSERT INTO public.sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id, delivery_duration)
                VALUES %s
            """, sales_data)

            conn.commit()
            
            # 4. إنشاء نص الفاتورة
            msg = f"🧾 فاتورة ({inv_id})\n👤 {customer_display}\n" + "-"*20 + "\n"
            total = 0
            for it in st.session_state.cart:
                msg += f"▫️ {it['name']} ({it['color']}) x{it['qty']} = {it['total']:,.0f}\n"
                total += it['total']
            msg += "-"*20 + f"\n💰 الإجمالي: {total:,.0f} د.ع\n📍 {customer_addr}"
            
            st.session_state.last_inv = msg
            st.session_state.cart = []
            clear_all_cache() # تحديث الواجهة فوراً
            
    except Exception as e:
        conn.rollback()
        st.error(f"فشلت العملية: {e}")

# --- 5. واجهة المستخدم (Layout) ---

with st.sidebar:
    st.markdown("### 🌸 نواعم بوتيك")
    page = st.radio("التنقل", 
        ["🛒 نقطة البيع", "📦 المخزون", "📊 التقارير", "👥 العملاء", "📜 السجل", "💸 المصاريف"],
        label_visibility="collapsed"
    )
    st.divider()
    if st.button("🔄 تحديث النظام", use_container_width=True):
        clear_all_cache()
        st.rerun()

# ==========================================
# صفحة 1: نقطة البيع (POS)
# ==========================================
if page == "🛒 نقطة البيع":
    col_pos, col_cart = st.columns([2, 1.2], gap="large")

    # >> القسم الأيمن: المنتجات والبحث
    with col_pos:
        st.subheader("🔍 البحث والمنتجات")
        df_inv = get_inventory()
        
        if not df_inv.empty:
            df_active = df_inv[df_inv['stock'] > 0].copy()
            df_active['display'] = df_active['name'] + " | " + df_active['color'] + " (" + df_active['size'] + ")"
            
            # بحث ذكي وسريع (Selectbox يعمل كبحث)
            st.selectbox(
                "بحث عن منتج:", 
                options=df_active['display'].tolist(), 
                index=None, 
                key="pos_selection",
                placeholder="اكتب اسم المنتج أو اللون..."
            )

            # عرض تفاصيل المنتج المختار
            if st.session_state.pos_selection:
                sel = st.session_state.pos_selection
                item = df_active[df_active['display'] == sel].iloc[0]
                
                with st.container():
                    c1, c2, c3 = st.columns(3)
                    c1.metric("المتوفر", f"{item['stock']}", border=True)
                    c2.metric("السعر", f"{item['price']:,.0f}", border=True)
                    c3.metric("القياس", item['size'], border=True)
                
                # نموذج الإضافة
                c_qty, c_price, c_btn = st.columns([1, 1, 2])
                c_qty.number_input("العدد", 1, int(item['stock']), 1, key="pos_qty")
                c_price.number_input("سعر البيع", value=float(item['price']), key="pos_price")
                c_btn.markdown("<br>", unsafe_allow_html=True) # spacer
                c_btn.button("➕ إضافة للسلة", type="primary", use_container_width=True, on_click=add_to_cart_callback)

    # >> القسم الأيسر: السلة والدفع
    with col_cart:
        st.subheader("🧾 الفاتورة")
        
        total_bill = sum(item['total'] for item in st.session_state.cart)
        
        with st.container():
            # عرض الإجمالي بشكل بارز
            st.markdown(f"""
            <div style="text-align: center; padding: 15px; background: rgba(212, 136, 150, 0.15); border-radius: 12px; margin-bottom: 15px;">
                <span style="font-size: 14px; color: #bbb;">الإجمالي النهائي</span><br>
                <span style="font-size: 32px; font-weight: 800; color: #D48896;">{total_bill:,.0f} <span style="font-size:18px">د.ع</span></span>
            </div>
            """, unsafe_allow_html=True)
            
            if not st.session_state.cart:
                st.info("السلة فارغة")
            else:
                for i, item in enumerate(st.session_state.cart):
                    c_txt, c_del = st.columns([5, 1])
                    c_txt.markdown(f"**{item['name']}** ({item['qty']}) <br><span style='color:#888; font-size:12px'>{item['color']} | {item['total']:,.0f}</span>", unsafe_allow_html=True)
                    c_del.button("✖", key=f"del_{i}", on_click=remove_from_cart_callback, args=(i,))
                    st.divider()

            # نموذج الدفع
            with st.expander("معلومات العميل", expanded=bool(st.session_state.cart)):
                df_cust = get_customers()
                st.selectbox("العميل", ["عميل جديد"] + df_cust['name'].tolist(), key="c_select")
                
                if st.session_state.c_select == "عميل جديد":
                    st.text_input("الاسم", key="c_name")
                    st.text_input("الهاتف", key="c_phone")
                    st.text_input("العنوان", key="c_addr")
                else:
                    curr = df_cust[df_cust['name'] == st.session_state.c_select].iloc[0]
                    st.caption(f"📞 {curr['phone']} | 📍 {curr['address']}")

                st.selectbox("مدة التوصيل", ["24 ساعة", "48 ساعة", "فوري"], key="c_dur")
                
                if st.button("✅ إتمام وطباعة", type="primary", use_container_width=True, on_click=checkout_callback):
                    pass

        # نافذة الفاتورة بعد الدفع
        if 'last_inv' in st.session_state:
            st.success("تم البيع بنجاح!")
            st.text_area("نص الفاتورة", st.session_state.last_inv, height=150)
            if st.button("بدء طلب جديد"):
                del st.session_state.last_inv
                st.rerun()

# ==========================================
# صفحة 2: المخزون (المحسنة - At a Glance)
# ==========================================
elif page == "📦 المخزون":
    st.title("📦 لوحة التحكم بالمخزون")

    df = get_inventory()
    if not df.empty:
        # 1. مؤشرات الأداء (KPIs)
        df['total_cost_value'] = df['stock'] * df['cost']
        df['total_sale_potential'] = df['stock'] * df['price']

        c1, c2, c3, c4 = st.columns(4)
        total_items = df['stock'].sum()
        total_cost = df['total_cost_value'].sum()
        total_sales = df['total_sale_potential'].sum()
        low_stock = len(df[df['stock'] < 3])

        c1.metric("إجمالي القطع", f"{total_items}", border=True)
        c2.metric("قيمة رأس المال", f"{total_cost:,.0f} د.ع", border=True)
        c3.metric("القيمة البيعية", f"{total_sales:,.0f} د.ع", delta=f"أرباح: {(total_sales-total_cost):,.0f}", border=True)
        c4.metric("نواقص المخزون", f"{low_stock} موديل", delta_color="inverse", border=True)

        st.divider()

        # 2. خيارات العرض
        view_type = st.radio("طريقة العرض:", ["📊 ملخص الموديلات (بنظرة واحدة)", "📝 تفاصيل كاملة (للتعديل)"], horizontal=True)

        if "ملخص" in view_type:
            # تجميع البيانات حسب الاسم فقط
            grouped = df.groupby('name').agg({
                'stock': 'sum',
                'color': 'count', # عدد الأنواع
                'total_sale_potential': 'sum'
            }).reset_index()
            
            grouped.columns = ['الموديل', 'الكمية الكلية', 'عدد الألوان', 'القيمة السوقية']
            
            st.dataframe(
                grouped,
                use_container_width=True,
                column_config={
                    "الكمية الكلية": st.column_config.ProgressColumn(
                        "توفر المخزون", format="%d", min_value=0, max_value=int(grouped['الكمية الكلية'].max())
                    ),
                    "القيمة السوقية": st.column_config.NumberColumn("قيمة الموديل", format="%d د.ع")
                },
                hide_index=True
            )
        else:
            # العرض التفصيلي القابل للتعديل
            search = st.text_input("بحث سريع في الجدول:", placeholder="اكتب للفلترة...")
            if search:
                df = df[df['name'].str.contains(search, case=False) | df['color'].str.contains(search, case=False)]
            
            edited_df = st.data_editor(
                df,
                key="editor_inv",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "id": None, "total_cost_value": None, "total_sale_potential": None,
                    "name": "الاسم", "color": "اللون", "size": "القياس",
                    "stock": st.column_config.NumberColumn("العدد", min_value=0, format="%d 📦"),
                    "price": st.column_config.NumberColumn("البيع", format="%d د.ع"),
                    "cost": st.column_config.NumberColumn("التكلفة", format="%d د.ع"),
                }
            )
            
            if st.button("💾 حفظ التعديلات", type="primary"):
                # منطق حفظ مبسط (تحديث الكل للأمان)
                changes = []
                for i, row in edited_df.iterrows():
                    changes.append((int(row['stock']), float(row['price']), float(row['cost']), row['size'], row['name'], row['color'], int(row['id'])))
                
                if changes:
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        cur.executemany("UPDATE public.variants SET stock=%s, price=%s, cost=%s, size=%s, name=%s, color=%s WHERE id=%s", changes)
                        conn.commit()
                    clear_all_cache()
                    st.toast("تم الحفظ بنجاح!", icon="✅")
                    time.sleep(1); st.rerun()

    else:
        st.info("المخزون فارغ.")

    # 3. إضافة صنف جديد
    with st.expander("➕ إضافة منتج جديد"):
        with st.form("new_item"):
            c1, c2, c3 = st.columns(3)
            n = c1.text_input("الاسم")
            co = c2.text_input("اللون")
            sz = c3.selectbox("القياس", ["S", "M", "L", "XL", "XXL", "Free"])
            c4, c5, c6 = st.columns(3)
            s = c4.number_input("العدد", 1)
            cs = c5.number_input("التكلفة", 0.0)
            p = c6.number_input("سعر البيع", 0.0)
            if st.form_submit_button("حفظ"):
                run_query("INSERT INTO public.variants (name, color, size, stock, cost, price) VALUES (%s,%s,%s,%s,%s,%s)", 
                          (n, co, sz, s, cs, p), commit=True, fetch=False)
                clear_all_cache(); st.rerun()

# ==========================================
# صفحة 3: التقارير (Dashboard)
# ==========================================
elif page == "📊 التقارير":
    st.title("📊 لوحة المعلومات")
    df_s = get_sales(1000)
    
    if not df_s.empty:
        df_s['date'] = pd.to_datetime(df_s['date'])
        today = pd.Timestamp.now().normalize()
        daily = df_s[df_s['date'] >= today]
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("مبيعات اليوم", f"{daily['total'].sum():,.0f}", border=True)
        m2.metric("الطلبات", len(daily), border=True)
        m3.metric("الأرباح", f"{daily['profit'].sum():,.0f}", border=True)
        m4.metric("متوسط السلة", f"{daily['total'].mean() if not daily.empty else 0:,.0f}", border=True)
        
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📈 النمو اليومي")
            daily_trend = df_s.groupby(df_s['date'].dt.date)['total'].sum()
            st.line_chart(daily_trend, color="#D48896")
        
        with c2:
            st.subheader("🏆 الأكثر مبيعاً")
            top = df_s.groupby('product_name')['qty'].sum().nlargest(5)
            st.bar_chart(top, color="#333333")

# ==========================================
# الصفحات الأخرى (بسيطة)
# ==========================================
elif page == "👥 العملاء":
    st.title("دليل العملاء")
    st.dataframe(get_customers(), use_container_width=True)

elif page == "💸 المصاريف":
    st.title("تسجيل المصاريف")
    with st.form("exp_form"):
        amt = st.number_input("المبلغ")
        rsn = st.text_input("السبب")
        if st.form_submit_button("تسجيل"):
            run_query("INSERT INTO public.expenses (amount, reason, date) VALUES (%s,%s,%s)", (amt, rsn, get_time()), commit=True, fetch=False)
            st.success("تم")

elif page == "📜 السجل":
    st.title("سجل العمليات والرواجع")
    df_sales_log = get_sales(100)
    st.dataframe(df_sales_log, use_container_width=True)
    
    st.divider()
    st.subheader("↩️ إرجاع منتج")
    
    ret_id = st.number_input("أدخل رقم العملية (ID) للإرجاع:", min_value=1, step=1)
    if st.button("بحث عن العملية"):
        sale_rec = df_sales_log[df_sales_log['id'] == ret_id]
        if not sale_rec.empty:
            r = sale_rec.iloc[0]
            st.warning(f"هل أنت متأكد من إرجاع: {r['product_name']} (العدد: {r['qty']})؟")
            if st.button("تأكيد الإرجاع"):
                # 1. إرجاع للمخزن
                run_query("UPDATE public.variants SET stock = stock + %s WHERE id = %s", (int(r['qty']), int(r['variant_id'])), commit=True, fetch=False)
                # 2. تسجيل المرتجع
                run_query("INSERT INTO public.returns (sale_id, product_name, qty, return_amount, return_date, status) VALUES (%s,%s,%s,%s,%s,%s)",
                          (int(r['id']), r['product_name'], int(r['qty']), float(r['total']), get_time(), 'Returned'), commit=True, fetch=False)
                # 3. تسجيل كمصروف عكسي (اختياري لضبط الصندوق)
                run_query("INSERT INTO public.expenses (amount, reason, date) VALUES (%s, %s, %s)", (float(r['total']), f"مرتجع فاتورة #{r['id']}", get_time()), commit=True, fetch=False)
                
                clear_all_cache()
                st.success("تمت عملية الإرجاع بنجاح")
        else:
            st.error("رقم العملية غير صحيح")
