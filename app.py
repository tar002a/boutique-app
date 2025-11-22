import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import pytz
import plotly.express as px # مكتبة للرسوم البيانية الجميلة

# --- إعداد الصفحة ---
st.set_page_config(
    page_title="Nawaem Boutique Pro", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="expanded"
)

# --- CSS متقدم (RTL & UI) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    
    .stApp {direction: rtl; font-family: 'Tajawal', sans-serif;}
    div[data-testid="column"] {text-align: right;}
    h1, h2, h3, h4, h5, h6, p, div, span {font-family: 'Tajawal', sans-serif !important; text-align: right;}
    
    /* تنسيق الأزرار */
    .stButton button {
        width: 100%; 
        border-radius: 12px; 
        font-weight: bold; 
        transition: all 0.3s ease;
    }
    .stButton button:hover {transform: scale(1.02);}
    
    /* بطاقات الأرقام */
    div[data-testid="stMetricValue"] {font-family: 'Courier New', monospace;}
    
    /* جداول البيانات */
    .stDataFrame {direction: rtl;}
</style>
""", unsafe_allow_html=True)

# --- 1. إدارة الاتصال (المحسنة) ---
@st.cache_resource
def init_connection():
    """إنشاء اتصال واحد وتخزينه في الذاكرة (مهم جداً للسرعة)"""
    try:
        return psycopg2.connect(st.secrets["DB_URL"])
    except Exception as e:
        st.error(f"⚠️ خطأ في الاتصال بقاعدة البيانات: {e}")
        return None

def run_query(query, params=(), fetch_data=False, commit=True):
    """تنفيذ الاستعلامات بأمان"""
    conn = init_connection()
    if conn:
        try:
            # إعادة الاتصال إذا انقطع
            if conn.closed:
                conn = init_connection()
                
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
        except Exception as e:
            conn.rollback() # إلغاء العمليات في حال الخطأ
            st.error(f"⛔ خطأ SQL: {e}")
            return None
    return None

# --- تهيئة الجداول (مرة واحدة) ---
def init_db_structure():
    tables_sql = [
        """CREATE TABLE IF NOT EXISTS variants (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, color TEXT, size TEXT,
            cost FLOAT DEFAULT 0, price FLOAT DEFAULT 0, stock INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE
        );""",
        """CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY, name TEXT NOT NULL, phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY, customer_id INTEGER, variant_id INTEGER,
            product_name TEXT, qty INTEGER, total FLOAT, profit FLOAT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, invoice_id TEXT
        );"""
    ]
    for sql in tables_sql:
        run_query(sql)

if 'db_setup' not in st.session_state:
    init_db_structure()
    st.session_state.db_setup = True

# --- دوال مساعدة ---
def get_time():
    return datetime.now(pytz.timezone('Asia/Baghdad'))

# --- الجلسة (Session State) ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'auth' not in st.session_state: st.session_state.auth = False

# --- تسجيل الدخول ---
def login_ui():
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
        st.title("تسجيل الدخول")
        with st.form("login"):
            # يفضل وضع كلمة المرور في st.secrets["ADMIN_PASS"]
            pwd = st.text_input("كلمة المرور", type="password")
            if st.form_submit_button("دخول"):
                # استخدمنا كلمة مرور افتراضية، يفضل تغييرها
                admin_pass = st.secrets.get("ADMIN_PASS", "admin123") 
                if pwd == admin_pass:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("كلمة المرور خاطئة")

# --- تنفيذ عملية البيع (Transaction) ---
def process_sale(customer_name, cart_items):
    conn = init_connection()
    if not conn: return False
    
    try:
        cur = conn.cursor()
        dt = get_time()
        inv_id = dt.strftime("%Y%m%d%H%M%S")
        
        # 1. معالجة العميل
        cur.execute("INSERT INTO customers (name) VALUES (%s) RETURNING id", (customer_name,))
        cust_id = cur.fetchone()[0]
        
        # 2. معالجة كل عنصر في السلة
        for item in cart_items:
            # التحقق من المخزون أولاً
            cur.execute("SELECT stock FROM variants WHERE id = %s FOR UPDATE", (item['id'],))
            current_stock = cur.fetchone()[0]
            
            if current_stock < item['qty']:
                raise Exception(f"المخزون غير كافٍ للمنتج: {item['name']}")
            
            # خصم المخزون
            cur.execute("UPDATE variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
            
            # تسجيل البيع
            profit = (item['price'] - item['cost']) * item['qty']
            cur.execute("""
                INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, dt, inv_id))
            
        conn.commit() # اعتماد كل العمليات دفعة واحدة
        cur.close()
        return True, inv_id
        
    except Exception as e:
        conn.rollback() # التراجع عن كل شيء إذا حدث خطأ
        st.error(f"حدث خطأ أثناء الحفظ: {e}")
        return False, str(e)

# --- الواجهة الرئيسية ---
def main_app():
    # الشريط الجانبي
    with st.sidebar:
        st.title("🌸 لوحة التحكم")
        st.info(f"📅 {get_time().strftime('%Y-%m-%d | %I:%M %p')}")
        st.markdown("---")
        menu = st.radio("التنقل", ["🛒 نقطة البيع", "📦 إدارة المخزون", "📈 التقارير والتحليل", "🧾 الفواتير"])
        st.markdown("---")
        if st.button("خروج 🔒"):
            st.session_state.auth = False
            st.rerun()

    # === 1. نقطة البيع (POS) ===
    if menu == "🛒 نقطة البيع":
        st.header("نقطة البيع السريعة")
        col_search, col_cart = st.columns([2, 1.2])
        
        with col_search:
            search_term = st.text_input("🔍 بحث (اسم، لون، كود)", placeholder="اكتب للبحث...")
            
            # جلب البيانات
            q = "SELECT * FROM variants WHERE is_active = TRUE AND stock > 0"
            params = []
            if search_term:
                q += " AND (name ILIKE %s OR color ILIKE %s)"
                params = [f"%{search_term}%", f"%{search_term}%"]
            q += " LIMIT 20"
            
            items = run_query(q, tuple(params), fetch_data=True)
            
            if items is not None and not items.empty:
                st.markdown(f"وجد {len(items)} منتج")
                for _, row in items.iterrows():
                    with st.container():
                        c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
                        c1.markdown(f"**{row['name']}** <span style='color:gray; font-size:0.8em'>({row['color']})</span>", unsafe_allow_html=True)
                        c1.caption(f"المقاس: {row['size']} | مخزون: {row['stock']}")
                        price_val = c2.number_input("السعر", value=float(row['price']), key=f"p_{row['id']}", label_visibility="collapsed")
                        qty_val = c3.number_input("العدد", value=1, min_value=1, max_value=row['stock'], key=f"q_{row['id']}", label_visibility="collapsed")
                        
                        if c4.button("إضافة ➕", key=f"btn_{row['id']}"):
                            # إضافة للسلة (منطق التجميع)
                            found = False
                            for c_item in st.session_state.cart:
                                if c_item['id'] == row['id'] and c_item['price'] == price_val:
                                    c_item['qty'] += qty_val
                                    c_item['total'] += (price_val * qty_val)
                                    found = True
                                    break
                            if not found:
                                st.session_state.cart.append({
                                    "id": row['id'], "name": row['name'], "color": row['color'],
                                    "size": row['size'], "qty": qty_val, "price": price_val,
                                    "cost": row['cost'], "total": price_val * qty_val
                                })
                            st.toast("تمت الإضافة!", icon="✅")
                            st.rerun()
                        st.divider()
            else:
                st.warning("لا توجد نتائج مطابقة")

        with col_cart:
            with st.container(border=True):
                st.subheader("🧾 السلة الحالية")
                if st.session_state.cart:
                    grand_total = 0
                    for i, item in enumerate(st.session_state.cart):
                        c_del, c_info = st.columns([1, 5])
                        if c_del.button("🗑️", key=f"d_{i}"):
                            st.session_state.cart.pop(i)
                            st.rerun()
                        c_info.markdown(f"**{item['name']}** ({item['qty']})")
                        c_info.caption(f"الإجمالي: {item['total']:,.0f}")
                        grand_total += item['total']
                    
                    st.divider()
                    st.markdown(f"<h3 style='color:green; text-align:center'>{grand_total:,.0f} د.ع</h3>", unsafe_allow_html=True)
                    
                    cust_name = st.text_input("اسم العميل", placeholder="اسم الزبون...")
                    if st.button("✅ إتمام ودفع", type="primary", use_container_width=True):
                        if not cust_name:
                            st.error("يجب إدخال اسم العميل")
                        else:
                            success, msg = process_sale(cust_name, st.session_state.cart)
                            if success:
                                st.session_state.cart = []
                                st.balloons()
                                st.success(f"تمت العملية بنجاح! رقم الفاتورة: {msg}")
                                st.rerun()
                else:
                    st.info("السلة فارغة")

    # === 2. إدارة المخزون (مطور) ===
    elif menu == "📦 إدارة المخزون":
        st.header("المخزون والمنتجات")
        
        tab1, tab2 = st.tabs(["تعديل المخزون الحالي", "إضافة منتج جديد"])
        
        with tab1:
            st.info("📝 يمكنك تعديل السعر، التكلفة، والمخزون مباشرة من الجدول أدناه ثم الضغط على حفظ.")
            df_inv = run_query("SELECT id, name, color, size, stock, cost, price, is_active FROM variants ORDER BY id DESC", fetch_data=True)
            
            if df_inv is not None:
                edited_df = st.data_editor(
                    df_inv,
                    column_config={
                        "id": "ID",
                        "name": "الاسم",
                        "stock": st.column_config.NumberColumn("المخزون", min_value=0, step=1),
                        "price": st.column_config.NumberColumn("سعر البيع", format="%d د.ع"),
                        "cost": st.column_config.NumberColumn("التكلفة", format="%d د.ع"),
                        "is_active": "نشط؟"
                    },
                    disabled=["id"], # منع تعديل المعرف
                    hide_index=True,
                    use_container_width=True,
                    key="inventory_editor"
                )
                
                if st.button("💾 حفظ التغييرات"):
                    # مقارنة وتحديث التغييرات (هذا الجزء يحتاج منطق متقدم، هنا سنحدث الكل للتبسيط أو نستخدم التغييرات فقط)
                    # للتبسيط في Streamlit، سنقوم بتحديث القيم المعدلة فقط إذا كانت هناك طريقة لتتبعها،
                    # أو تحديث الصفوف التي تغيرت. في التطبيقات البسيطة نحدث الصفوف بناء على ID
                    
                    # ملاحظة: st.data_editor يُرجع الداتا فريم كاملة مع التعديلات
                    conn = init_connection()
                    cur = conn.cursor()
                    try:
                        for index, row in edited_df.iterrows():
                            cur.execute("""
                                UPDATE variants SET name=%s, color=%s, size=%s, stock=%s, cost=%s, price=%s, is_active=%s
                                WHERE id=%s
                            """, (row['name'], row['color'], row['size'], row['stock'], row['cost'], row['price'], row['is_active'], row['id']))
                        conn.commit()
                        st.success("تم تحديث المخزون!")
                    except Exception as e:
                        st.error(f"خطأ: {e}")
                    finally:
                        cur.close()

        with tab2:
            with st.form("new_prod"):
                c1, c2 = st.columns(2)
                name = c1.text_input("اسم المنتج")
                color = c2.text_input("اللون")
                c3, c4 = st.columns(2)
                size = c3.text_input("القياس")
                stock = c4.number_input("الكمية الأولية", 1)
                c5, c6 = st.columns(2)
                cost = c5.number_input("سعر التكلفة", 0.0)
                price = c6.number_input("سعر البيع", 0.0)
                if st.form_submit_button("إضافة للمخزون"):
                    run_query("INSERT INTO variants (name, color, size, stock, cost, price) VALUES (%s, %s, %s, %s, %s, %s)", 
                              (name, color, size, stock, cost, price))
                    st.success("تمت الإضافة")

    # === 3. التقارير (رسوم بيانية) ===
    elif menu == "📈 التقارير والتحليل":
        st.header("لوحة التحليل المالي")
        
        # فلاتر التاريخ
        c_filter1, c_filter2 = st.columns(2)
        days_back = c_filter1.selectbox("الفترة الزمنية", [7, 30, 90, 365], index=1, format_func=lambda x: f"آخر {x} يوم")
        
        # جلب البيانات
        start_date = (get_time() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        df_stats = run_query(f"""
            SELECT date::date as day, SUM(total) as daily_sales, SUM(profit) as daily_profit 
            FROM sales 
            WHERE date >= '{start_date}' 
            GROUP BY day ORDER BY day
        """, fetch_data=True)
        
        if df_stats is not None and not df_stats.empty:
            # بطاقات الملخص
            tot_sales = df_stats['daily_sales'].sum()
            tot_profit = df_stats['daily_profit'].sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("إجمالي المبيعات", f"{tot_sales:,.0f}", "د.ع")
            m2.metric("صافة الأرباح", f"{tot_profit:,.0f}", "د.ع")
            m3.metric("هامش الربح", f"{(tot_profit/tot_sales*100):.1f}%" if tot_sales > 0 else "0%")
            
            # الرسم البياني
            st.subheader("📊 حركة المبيعات")
            fig = px.bar(df_stats, x='day', y=['daily_sales', 'daily_profit'], 
                         labels={'value': 'المبلغ (د.ع)', 'day': 'التاريخ', 'variable': 'النوع'},
                         barmode='group', color_discrete_sequence=['#636EFA', '#00CC96'])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("لا توجد بيانات كافية في هذه الفترة")

    # === 4. الفواتير (سجل) ===
    elif menu == "🧾 الفواتير":
        st.subheader("سجل العمليات الأخيرة")
        df_invs = run_query("""
            SELECT s.invoice_id, c.name as customer, s.product_name, s.total, s.date 
            FROM sales s JOIN customers c ON s.customer_id = c.id 
            ORDER BY s.date DESC LIMIT 100
        """, fetch_data=True)
        st.dataframe(df_invs, use_container_width=True)

# --- التشغيل ---
if __name__ == "__main__":
    if st.session_state.auth:
        main_app()
    else:
        login_ui()
```

### أبرز التحسينات التي قمت بها:

1.  **`@st.cache_resource`:** أضفت هذا الـ Decorator لدالة الاتصال. هذا يضمن أن التطبيق لا يقوم بإنشاء اتصال جديد مع كل ضغطة زر (Refresh)، مما يحل مشكلة البطء ومشاكل Supabase.
2.  **محرر بيانات تفاعلي (`st.data_editor`):** في تبويب "المخزون"، يمكنك الآن تعديل السعر والكمية مباشرة داخل الجدول مثل Excel والضغط على "حفظ" لتحديث قاعدة البيانات دفعة واحدة.
3.  **نظام المعاملات (Transactions):** دالة `process_sale` الآن تستخدم `commit` و `rollback`. هذا يعني أنه إذا انقطع النت بعد خصم المخزون وقبل حفظ الفاتورة، سيتراجع النظام عن خصم المخزون تلقائياً.
4.  **الرسوم البيانية (Plotly):** أضفت رسماً بيانياً يوضح المبيعات والأرباح بشكل يومي، مع إمكانية فلترة المدة (أسبوع، شهر، سنة).
5.  **واجهة مستخدم أجمل:** استخدمت أيقونات، وتنسيق أعمدة أفضل، وأزرار تفاعلية، وقائمة جانبية للتنقل بدلاً من التبويبات العلوية المزدحمة.

### ما يجب عليك فعله الآن:

1.  قم بتحديث ملف `secrets.toml` في Streamlit Cloud ليحتوي على:
    ```toml
    DB_URL = "postgresql://postgres....."
    ADMIN_PASS = "ضع_كلمة_سر_قوية_هنا"
