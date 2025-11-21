import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- إعداد الصفحة ---
st.set_page_config(page_title="بوتيك كلاود", layout="wide", page_icon="👗")

# --- دوال قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('boutique_web_v2.db', check_same_thread=False)
    c = conn.cursor()
    
    # جدول المنتجات (كما هو)
    c.execute("""CREATE TABLE IF NOT EXISTS variants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        color TEXT,
        size TEXT,
        cost REAL,
        price REAL,
        stock INTEGER
    )""")
    
    # جدول المبيعات (تم تحديثه لإضافة بيانات العميل)
    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        variant_id INTEGER,
        product_name TEXT,
        qty INTEGER,
        total REAL,
        profit REAL,
        customer_name TEXT,
        customer_phone TEXT,
        customer_address TEXT,
        customer_username TEXT,
        date TEXT
    )""")
    conn.commit()
    return conn

conn = init_db()

# --- الواجهة الجانبية ---
st.sidebar.title("نظام إدارة البوتيك")
menu = st.sidebar.radio("القائمة الرئيسية", ["نقطة البيع (POS)", "إدخال بضاعة (Matrix)", "سجل المبيعات والعملاء"])

# ==========================
# صفحة 1: إدخال بضاعة (Matrix)
# ==========================
if menu == "إدخال بضاعة (Matrix)":
    st.header("📦 إدخال منتج جديد")
    st.info("هنا تقوم بتعريف البضاعة وأسعارها الأساسية.")
    
    with st.form("add_product_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("اسم الموديل")
            colors = st.text_input("الألوان (افصل بفاصلة ،) مثال: أحمر, أسود")
        with col2:
            sizes = st.text_input("القياسات (افصل بفاصلة ،) مثال: S, M, L")
            stock_per_item = st.number_input("العدد لكل قطعة", min_value=1, value=1)
        
        col3, col4 = st.columns(2)
        with col3:
            cost = st.number_input("سعر التكلفة (للقطعة الواحدة)", min_value=0.0, step=1000.0)
        with col4:
            price = st.number_input("سعر البيع الافتراضي", min_value=0.0, step=1000.0)
            
        submitted = st.form_submit_button("توليد الأصناف وحفظها")
        
        if submitted:
            if name and colors and sizes:
                color_list = [c.strip() for c in colors.split(',')]
                size_list = [s.strip() for s in sizes.split(',')]
                count = 0
                c = conn.cursor()
                for color in color_list:
                    for size in size_list:
                        if color and size:
                            c.execute("""INSERT INTO variants (name, color, size, cost, price, stock) 
                                         VALUES (?, ?, ?, ?, ?, ?)""", 
                                      (name, color, size, cost, price, stock_per_item))
                            count += 1
                conn.commit()
                st.success(f"تم إضافة {count} صنف للمخزون!")
            else:
                st.error("يرجى ملء جميع الحقول!")

# ==========================
# صفحة 2: نقطة البيع (POS)
# ==========================
elif menu == "نقطة البيع (POS)":
    st.header("🛒 تسجيل عملية بيع")

    df = pd.read_sql("SELECT * FROM variants WHERE stock > 0", conn)
    
    if not df.empty:
        # 1. البحث واختيار المنتج
        search_term = st.text_input("🔍 بحث عن منتج:", placeholder="اسم الموديل او اللون...")
        if search_term:
            mask = df['name'].str.contains(search_term, case=False) | df['color'].str.contains(search_term, case=False)
            filtered_df = df[mask]
        else:
            filtered_df = df

        # إنشاء قائمة العرض
        filtered_df['display'] = filtered_df.apply(
            lambda x: f"{x['name']} | {x['color']} | {x['size']} (متبقي: {x['stock']})", axis=1
        )
        
        selected_item_str = st.selectbox("اختر القطعة:", options=filtered_df['display'].tolist())
        
        if selected_item_str:
            # جلب بيانات المنتج المختار
            item = filtered_df[filtered_df['display'] == selected_item_str].iloc[0]
            
            st.markdown("---")
            st.write(f"**المنتج المختار:** {item['name']} - {item['color']} - {item['size']}")
            
            # نموذج إدخال بيانات البيع
            with st.form("sale_process_form"):
                st.subheader("📝 بيانات الفاتورة والعميل")
                
                # بيانات العميل
                c1, c2 = st.columns(2)
                with c1:
                    cust_name = st.text_input("اسم المشتري")
                    cust_phone = st.text_input("رقم الهاتف")
                with c2:
                    cust_addr = st.text_input("العنوان")
                    cust_user = st.text_input("User Name / حساب انستغرام")
                
                st.markdown("---")
                # تعديل السعر
                p1, p2 = st.columns(2)
                with p1:
                    # السعر الافتراضي يأتي من قاعدة البيانات، لكن يمكن تعديله هنا
                    final_sell_price = st.number_input("سعر البيع النهائي (للواحدة)", 
                                                     min_value=0.0, 
                                                     value=float(item['price']), 
                                                     step=1000.0)
                with p2:
                    qty_sell = st.number_input("الكمية المباعة", min_value=1, max_value=int(item['stock']), value=1)

                # حساب الإجمالي لحظياً للعرض فقط داخل الزر
                total_bill = final_sell_price * qty_sell
                
                btn_confirm = st.form_submit_button(f"✅ إتمام البيع (الإجمالي: {total_bill:,.0f})")
                
                if btn_confirm:
                    if cust_name: # التحقق من إدخال اسم العميل على الأقل
                        c = conn.cursor()
                        
                        # 1. خصم المخزون
                        c.execute("UPDATE variants SET stock = stock - ? WHERE id = ?", (qty_sell, int(item['id'])))
                        
                        # 2. حساب الربح الفعلي (بناء على السعر المدخل يدوياً)
                        actual_profit = (final_sell_price - item['cost']) * qty_sell
                        date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # 3. حفظ بيانات البيع والعميل
                        c.execute("""INSERT INTO sales 
                                     (variant_id, product_name, qty, total, profit, 
                                      customer_name, customer_phone, customer_address, customer_username, date) 
                                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                  (int(item['id']), item['name'], qty_sell, total_bill, actual_profit, 
                                   cust_name, cust_phone, cust_addr, cust_user, date_now))
                        
                        conn.commit()
                        st.success(f"تم بيع {item['name']} للعميل {cust_name} بنجاح!")
                        st.rerun()
                    else:
                        st.warning("⚠️ يرجى كتابة اسم المشتري على الأقل لإتمام العملية.")

    else:
        st.warning("المخزون فارغ أو نفذت الكميات.")

# ==========================
# صفحة 3: التقارير وسجل العملاء
# ==========================
elif menu == "سجل المبيعات والعملاء":
    st.header("📊 التقارير")
    
    tab1, tab2, tab3 = st.tabs(["سجل المبيعات", "قائمة العملاء", "جرد المخزون"])
    
    with tab1:
        st.subheader("تفاصيل العمليات")
        # عرض الجدول مع البيانات الجديدة
        sales_df = pd.read_sql("""
            SELECT 
                id as 'رقم الفاتورة',
                date as 'التاريخ',
                customer_name as 'العميل',
                product_name as 'المنتج',
                total as 'المبلغ',
                profit as 'الربح',
                customer_phone as 'هاتف',
                customer_username as 'User'
            FROM sales ORDER BY id DESC
        """, conn)
        
        st.dataframe(sales_df, use_container_width=True)
        
        if not sales_df.empty:
            st.success(f"إجمالي المبيعات: {sales_df['المبلغ'].sum():,.0f} د.ع")
            st.info(f"صافي الأرباح: {sales_df['الربح'].sum():,.0f} د.ع")

    with tab2:
        st.subheader("بيانات العملاء للتوصيل")
        # استعلام لجلب بيانات العملاء فقط
        customers_df = pd.read_sql("""
            SELECT DISTINCT customer_name, customer_phone, customer_address, customer_username 
            FROM sales
        """, conn)
        st.dataframe(customers_df, use_container_width=True)

    with tab3:
        st.subheader("المخزون المتبقي")
        stock_df = pd.read_sql("SELECT name, color, size, price, stock FROM variants", conn)
        st.dataframe(stock_df, use_container_width=True)
