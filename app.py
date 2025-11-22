import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import pytz

# --- 1. إعداد الصفحة وتصميم الواجهة ---
st.set_page_config(
    page_title="نواعم بوتيك", 
    layout="wide", 
    page_icon="🌸", 
    initial_sidebar_state="collapsed"
)

# CSS لتحسين المظهر ودعم اللغة العربية والتوافق مع الموبايل
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;700&display=swap');
    
    * {
        font-family: 'Tajawal', sans-serif !important;
    }
    
    .stApp {
        direction: rtl;
    }
    
    /* محاذاة النصوص لليمين */
    div[data-testid="column"] {
        text-align: right;
    }
    
    /* تنسيق الأزرار */
    .stButton button {
        width: 100%;
        height: 50px;
        border-radius: 12px;
        font-weight: bold;
        font-size: 16px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    
    /* تنسيق البطاقات */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* إخفاء القوائم الجانبية للموبايل */
    [data-testid="stSidebar"] {display: none;}
    
    /* تحسين حقول الإدخال */
    input, select, textarea {
        direction: rtl;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. إدارة الجلسة والمتغيرات ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'sale_success' not in st.session_state: st.session_state.sale_success = False
if 'last_invoice_text' not in st.session_state: st.session_state.last_invoice_text = ""

# --- 3. الاتصال بقاعدة البيانات (Supabase/PostgreSQL) ---
def get_baghdad_time():
    """إرجاع الوقت الحالي بتوقيت بغداد"""
    return datetime.now(pytz.timezone('Asia/Baghdad'))

@st.cache_resource
def init_connection():
    """إنشاء اتصال آمن ومخزن مؤقتاً بقاعدة البيانات"""
    try:
        return psycopg2.connect(st.secrets["DB_URL"])
    except Exception as e:
        return None

def run_query(query, params=(), fetch=False, commit=True):
    """دالة موحدة لتنفيذ الاستعلامات (CRUD)"""
    conn = init_connection()
    if conn:
        try:
            # التأكد من أن الاتصال مفتوح
            if conn.closed: conn = init_connection()
            cur = conn.cursor()
            
            cur.execute(query, params)
            
            if fetch:
                # جلب البيانات (لتقارير وجداول العرض)
                columns = [desc[0] for desc in cur.description]
                data = cur.fetchall()
                cur.close()
                return pd.DataFrame(data, columns=columns)
            else:
                # تنفيذ التعديلات (إضافة/حذف/تحديث)
                if commit: conn.commit()
                
                # إذا كان الاستعلام يطلب إرجاع ID (مثل إضافة عميل جديد)
                last_id = None
                # تصحيح: التأكد من حالة الأحرف عند البحث عن RETURNING ID
                if "RETURNING ID" in query.upper():
                    last_id = cur.fetchone()[0]
                
                cur.close()
                return last_id if last_id else True
        except Exception as e:
            if commit: conn.rollback()
            st.toast(f"خطأ في قاعدة البيانات: {e}", icon="❌")
            return None
    else:
        st.error("فشل الاتصال بقاعدة البيانات. تأكد من إعدادات Secrets.")
        return None

# --- 4. النوافذ المنبثقة (Dialogs) ---

@st.dialog("تعديل فاتورة")
def edit_sale_dialog(sale_id, current_qty, current_total, variant_id, product_name):
    st.write(f"المنتج: **{product_name}**")
    
    col1, col2 = st.columns(2)
    new_qty = col1.number_input("العدد الجديد", min_value=1, value=int(current_qty))
    new_total = col2.number_input("الإجمالي الجديد", value=float(current_total))
    
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💾 حفظ التعديلات", type="primary"):
            # حساب فرق الكمية لتعديل المخزون
            diff = new_qty - int(current_qty)
            if diff != 0:
                run_query("UPDATE variants SET stock = stock - %s WHERE id = %s", (diff, variant_id))
            
            # تحديث سجل البيع
            run_query("UPDATE sales SET qty = %s, total = %s WHERE id = %s", (new_qty, new_total, sale_id))
            st.success("تم التعديل بنجاح")
            st.rerun()
            
    with c2:
        if st.button("🗑️ استرجاع وحذف"):
            # إعادة الكمية للمخزون
            run_query("UPDATE variants SET stock = stock + %s WHERE id = %s", (int(current_qty), variant_id))
            # حذف البيع
            run_query("DELETE FROM sales WHERE id = %s", (sale_id,))
            st.success("تم الحذف واسترجاع الكمية")
            st.rerun()

@st.dialog("إدارة المنتج")
def edit_stock_dialog(item_id, name, color, size, cost, price, stock):
    with st.form("edit_stock_form"):
        st.subheader(f"تعديل: {name}")
        n_name = st.text_input("اسم المنتج", value=name)
        
        c1, c2 = st.columns(2)
        n_col = c1.text_input("اللون", value=color)
        n_siz = c2.text_input("القياس", value=size)
        
        c3, c4, c5 = st.columns(3)
        n_cst = c3.number_input("التكلفة", value=float(cost))
        n_prc = c4.number_input("سعر البيع", value=float(price))
        n_stk = c5.number_input("المخزون الحالي", value=int(stock))
        
        if st.form_submit_button("💾 حفظ التغييرات"):
            run_query("""
                UPDATE variants 
                SET name=%s, color=%s, size=%s, cost=%s, price=%s, stock=%s 
                WHERE id=%s
            """, (n_name, n_col, n_siz, n_cst, n_prc, n_stk, item_id))
            st.rerun()
            
    st.divider()
    if st.button("❌ حذف المنتج نهائياً"):
        run_query("DELETE FROM variants WHERE id=%s", (item_id,))
        st.rerun()

# --- 5. شاشة تسجيل الدخول ---
def login_screen():
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #E91E63;'>🌸 نواعم بوتيك</h1>", unsafe_allow_html=True)
        
        with st.container(border=True):
            pwd = st.text_input("الرمز السري", type="password")
            if st.button("تسجيل الدخول", type="primary"):
                admin_pass = st.secrets.get("ADMIN_PASS", "admin")
                if pwd == admin_pass:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("الرمز السري غير صحيح")

# --- 6. التطبيق الرئيسي ---
def main_app():
    # الشريط العلوي
    col_head, col_logout = st.columns([6, 1])
    col_head.markdown("### 🌸 نظام إدارة المبيعات")
    if col_logout.button("خروج"):
        st.session_state.logged_in = False
        st.rerun()

    # التبويبات الرئيسية
    tabs = st.tabs(["🛒 نقطة البيع", "📦 المخزون", "📋 السجل", "👥 العملاء", "📊 التقارير"])

    # ==========================================
    # تبويب 1: نقطة البيع (POS)
    # ==========================================
    with tabs[0]:
        if st.session_state.sale_success:
            st.success("✅ تم إكمال الطلب بنجاح!")
            st.balloons()
            st.markdown("##### تفاصيل الرسالة (للنسخ):")
            st.text_area("msg", st.session_state.last_invoice_text, height=150)
            if st.button("🔄 فاتورة جديدة", type="primary"):
                st.session_state.sale_success = False
                st.session_state.last_invoice_text = ""
                st.rerun()
        else:
            # قسم البحث والإضافة
            with st.container(border=True):
                # جلب المنتجات المتوفرة فقط
                df_vars = run_query("SELECT * FROM variants WHERE stock > 0 AND is_active = TRUE ORDER BY name", fetch=True)
                
                if df_vars is not None and not df_vars.empty:
                    # إنشاء قائمة منسدلة ذكية للبحث
                    df_vars['label'] = df_vars.apply(lambda x: f"{x['name']} | {x['color']} | {x['size']}", axis=1)
                    opts = ["اختر منتجاً..."] + df_vars['label'].tolist()
                    
                    selection = st.selectbox("🔍 ابحث عن منتج", opts, label_visibility="collapsed")
                    
                    if selection and selection != "اختر منتجاً...":
                        # جلب بيانات المنتج المختار
                        item = df_vars[df_vars['label'] == selection].iloc[0]
                        
                        st.markdown(f"**{item['name']}** - <span style='color:#E91E63'>{item['color']} ({item['size']})</span>", unsafe_allow_html=True)
                        st.caption(f"المتوفر: {item['stock']} | السعر: {item['price']:,.0f}")
                        
                        c_q, c_p, c_add = st.columns([1, 1, 2])
                        qty = c_q.number_input("الكمية", min_value=1, max_value=int(item['stock']), value=1)
                        price = c_p.number_input("السعر", value=float(item['price']))
                        
                        if c_add.button("أضف للسلة ➕", type="primary"):
                            st.session_state.cart.append({
                                "id": int(item['id']),
                                "name": item['name'],
                                "color": item['color'],
                                "size": item['size'],
                                "cost": item['cost'],
                                "price": price,
                                "qty": qty,
                                "total": price * qty
                            })
                            st.toast("تمت الإضافة للسلة", icon="✅")
                else:
                    st.info("المخزون فارغ أو نفذت الكميات")

            # قسم السلة وإتمام البيع
            if st.session_state.cart:
                st.divider()
                st.markdown("##### 🛒 سلة المشتريات")
                
                # معلومات العميل
                with st.container(border=True):
                    cust_mode = st.radio("بيانات العميل", ["عميل جديد", "مسجل سابقاً"], horizontal=True)
                    cust_id, cust_name = None, ""
                    
                    if cust_mode == "مسجل سابقاً":
                        existing_custs = run_query("SELECT id, name, phone FROM customers ORDER BY name", fetch=True)
                        if existing_custs is not None and not existing_custs.empty:
                            c_opts = existing_custs.apply(lambda x: f"{x['name']} - {x['phone']}", axis=1).tolist()
                            c_sel = st.selectbox("اختر العميل", c_opts)
                            cust_name = c_sel.split(" - ")[0]
                            # البحث عن المعرف
                            cust_id = int(existing_custs[existing_custs['name'] == cust_name]['id'].iloc[0])
                        else:
                            st.warning("لا يوجد عملاء مسجلين")
                    else:
                        c_name = st.text_input("اسم العميل")
                        c_phone = st.text_input("رقم الهاتف")
                        c_addr = st.text_input("العنوان")
                        cust_name = c_name

                # عرض عناصر السلة
                total_bill = 0
                invoice_text = f"مرحبا {cust_name} 🌸\nتم حجز طلبك:\n\n"
                
                for idx, i in enumerate(st.session_state.cart):
                    total_bill += i['total']
                    invoice_text += f"▫️ {i['name']} ({i['color']}) - {i['size']}\n   العدد: {i['qty']} | السعر: {i['price']:,.0f}\n"
                    
                    cc1, cc2, cc3 = st.columns([3, 1, 1])
                    cc1.text(f"{i['name']} - {i['color']}")
                    cc2.text(f"{i['total']:,.0f}")
                    if cc3.button("❌", key=f"del_{idx}"):
                        st.session_state.cart.pop(idx)
                        st.rerun()

                invoice_text += f"\nالمجموع الكلي: {total_bill:,.0f} د.ع\nالتوصيل مجاني 🚕\nشكراً لتسوقكم مع نواعم بوتيك 🛍️"
                
                st.subheader(f"المجموع: {total_bill:,.0f} د.ع")
                
                if st.button("✅ إتمام البيع وحفظ الفاتورة", type="primary"):
                    if not cust_name:
                        st.error("الرجاء إدخال اسم العميل")
                    else:
                        try:
                            # 1. إنشاء العميل الجديد إذا لزم الأمر
                            if cust_mode == "عميل جديد":
                                cust_id = run_query(
                                    "INSERT INTO customers (name, phone, address) VALUES (%s, %s, %s) RETURNING id",
                                    (c_name, c_phone, c_addr)
                                )
                            
                            # 2. تحضير بيانات الفاتورة
                            dt_baghdad = get_baghdad_time()
                            inv_code = dt_baghdad.strftime("%Y%m%d%H%M")
                            
                            # 3. حلقة لحفظ المبيعات وتحديث المخزون
                            for item in st.session_state.cart:
                                # خصم المخزون
                                run_query("UPDATE variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
                                
                                # حساب الربح
                                profit = (item['price'] - item['cost']) * item['qty']
                                
                                # إدراج البيع
                                run_query("""
                                    INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                """, (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, dt_baghdad, inv_code))
                            
                            # 4. إنهاء العملية
                            st.session_state.sale_success = True
                            st.session_state.last_invoice_text = invoice_text
                            st.session_state.cart = []
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء المعالجة: {e}")

    # ==========================================
    # تبويب 2: المخزون (Inventory)
    # ==========================================
    with tabs[1]:
        with st.expander("➕ إضافة منتجات جديدة (Bulk Add)"):
            with st.form("bulk_add_form"):
                st.info("يمكنك إضافة عدة ألوان ومقاسات دفعة واحدة بفصلها بفاصلة (،)")
                b_name = st.text_input("اسم المنتج")
                b_colors = st.text_input("الألوان (مثال: أحمر، أسود)")
                b_sizes = st.text_input("المقاسات (مثال: S، M، L)")
                
                bc1, bc2, bc3 = st.columns(3)
                b_qty = bc1.number_input("العدد لكل قطعة", 1)
                b_price = bc2.number_input("سعر البيع", 0.0)
                b_cost = bc3.number_input("سعر التكلفة", 0.0)
                
                if st.form_submit_button("توليد وإضافة للمخزون"):
                    # معالجة الفواصل العربية والإنجليزية
                    colors_list = [c.strip() for c in b_colors.replace('،', ',').split(',') if c.strip()]
                    sizes_list = [s.strip() for s in b_sizes.replace('،', ',').split(',') if s.strip()]
                    
                    count = 0
                    for col in colors_list:
                        for siz in sizes_list:
                            run_query("""
                                INSERT INTO variants (name, color, size, stock, price, cost, is_active)
                                VALUES (%s, %s, %s, %s, %s, %s, TRUE)
                            """, (b_name, col, siz, b_qty, b_price, b_cost))
                            count += 1
                    
                    st.success(f"تمت إضافة {count} منتج بنجاح!")
                    st.rerun()
        
        st.divider()
        st.markdown("### جرد المخزون الحالي")
        
        # عرض المخزون مجمّعاً حسب الاسم
        df_inv = run_query("SELECT * FROM variants WHERE is_active = TRUE ORDER BY name, id DESC", fetch=True)
        
        if df_inv is not None and not df_inv.empty:
            unique_names = df_inv['name'].unique()
            for uname in unique_names:
                with st.container(border=True):
                    st.markdown(f"#### 👗 {uname}")
                    # جلب جميع متغيرات هذا المنتج
                    sub_df = df_inv[df_inv['name'] == uname]
                    
                    # عرضها كأزرار للتعديل
                    cols = st.columns(4)
                    for idx, row in sub_df.iterrows():
                        col_idx = idx % 4
                        btn_label = f"{row['color']} | {row['size']} (العدد: {row['stock']})"
                        if cols[col_idx].button(btn_label, key=f"inv_{row['id']}"):
                            edit_stock_dialog(
                                row['id'], row['name'], row['color'], row['size'], 
                                row['cost'], row['price'], row['stock']
                            )
        else:
            st.info("المخزون فارغ حالياً")

    # ==========================================
    # تبويب 3: سجل المبيعات (Log)
    # ==========================================
    with tabs[2]:
        st.markdown("### آخر عمليات البيع")
        
        # استعلام مع JOIN لجلب اسم العميل
        df_sales = run_query("""
            SELECT s.*, c.name as customer_name 
            FROM sales s 
            LEFT JOIN customers c ON s.customer_id = c.id 
            ORDER BY s.date DESC LIMIT 50
        """, fetch=True)
        
        if df_sales is not None and not df_sales.empty:
            for idx, row in df_sales.iterrows():
                with st.container(border=True):
                    sc1, sc2, sc3 = st.columns([3, 2, 1])
                    
                    # تنسيق التاريخ
                    s_date = row['date'].strftime("%Y-%m-%d %I:%M %p") if row['date'] else ""
                    
                    sc1.markdown(f"**{row['product_name']}**")
                    sc1.caption(f"العميل: {row['customer_name']} | {s_date}")
                    
                    sc2.text(f"العدد: {row['qty']} | الإجمالي: {row['total']:,.0f}")
                    
                    if sc3.button("تعديل", key=f"sale_edit_{row['id']}"):
                        edit_sale_dialog(
                            row['id'], row['qty'], row['total'], 
                            row['variant_id'], row['product_name']
                        )
        else:
            st.info("لا توجد مبيعات مسجلة")

    # ==========================================
    # تبويب 4: العملاء (Customers)
    # ==========================================
    with tabs[3]:
        st.markdown("### قاعدة بيانات العملاء")
        df_customers = run_query("SELECT * FROM customers ORDER BY id DESC", fetch=True)
        if df_customers is not None:
            st.dataframe(df_customers, use_container_width=True)

    # ==========================================
    # تبويب 5: التقارير (Reports)
    # ==========================================
    with tabs[4]:
        st.markdown("### 📊 ذكاء الأعمال والتقارير")
        
        today_str = get_baghdad_time().strftime("%Y-%m-%d")
        
        # --- 1. إحصائيات اليوم (تم الإصلاح هنا) ---
        # استخدام المعاملات %s بدلاً من f-string لتجنب مشكلة tuple index out of range
        today_query = "SELECT SUM(total), SUM(profit) FROM sales WHERE TO_CHAR(date, 'YYYY-MM-DD') = %s"
        df_today = run_query(today_query, (today_str,), fetch=True)
        
        val_sales = 0
        val_profit = 0
        
        if df_today is not None and not df_today.empty:
            val_sales = df_today.iloc[0, 0] if df_today.iloc[0, 0] is not None else 0
            val_profit = df_today.iloc[0, 1] if df_today.iloc[0, 1] is not None else 0
        
        col_r1, col_r2 = st.columns(2)
        col_r1.metric("مبيعات اليوم", f"{val_sales:,.0f} د.ع")
        col_r2.metric("أرباح اليوم", f"{val_profit:,.0f} د.ع")
        
        st.divider()
        
        # 2. قيمة المخزون (Assets)
        df_assets = run_query("SELECT SUM(stock * cost), SUM(stock * price) FROM variants", fetch=True)
        
        asset_cost = 0
        asset_rev = 0
        
        if df_assets is not None and not df_assets.empty:
            asset_cost = df_assets.iloc[0, 0] if df_assets.iloc[0, 0] is not None else 0
            asset_rev = df_assets.iloc[0, 1] if df_assets.iloc[0, 1] is not None else 0
        
        st.subheader("💰 التقييم المالي للمخزون")
        ac1, ac2, ac3 = st.columns(3)
        ac1.metric("رأس المال (التكلفة)", f"{asset_cost:,.0f} د.ع")
        ac2.metric("القيمة السوقية (البيع)", f"{asset_rev:,.0f} د.ع")
        ac3.metric("الأرباح المتوقعة", f"{(asset_rev - asset_cost):,.0f} د.ع")
        
        st.divider()
        
        # 3. الأكثر مبيعاً
        st.subheader("🏆 المنتجات الأكثر طلباً")
        df_top = run_query("""
            SELECT product_name as "المنتج", SUM(qty) as "الكمية المباعة"
            FROM sales
            GROUP BY product_name
            ORDER BY SUM(qty) DESC
            LIMIT 5
        """, fetch=True)
        
        if df_top is not None:
            st.table(df_top)

# --- نقطة الانطلاق ---
if __name__ == "__main__":
    if st.session_state.logged_in:
        main_app()
    else:
        login_screen()
