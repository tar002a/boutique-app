import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import pytz
import plotly.express as px
import plotly.graph_objects as go

# --- 1. إعداد الصفحة (يجب أن يكون أول أمر) ---
st.set_page_config(
    page_title="نواعم بوتيك", 
    layout="wide", 
    page_icon="🛍️", 
    initial_sidebar_state="collapsed" # القائمة مغلقة افتراضياً للموبايل
)

# --- 2. تصميم UX/UI احترافي (CSS) ---
st.markdown("""
<style>
    /* استيراد خط عربي جميل */
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;800&display=swap');
    
    /* تعميم الخط والاتجاه */
    * {
        font-family: 'Cairo', sans-serif !important;
    }
    .stApp {
        direction: rtl;
        background-color: #f8f9fa;
    }
    
    /* تنسيق العناوين */
    h1, h2, h3 {
        color: #2c3e50;
        font-weight: 800;
    }

    /* تحسين شكل البطاقات (Containers) */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        border: 1px solid #eee;
        padding: 10px;
        margin-bottom: 10px;
    }

    /* تنسيق الأزرار لتشبه تطبيقات الموبايل */
    .stButton button {
        width: 100%;
        border-radius: 12px;
        font-weight: 600;
        height: 45px;
        transition: all 0.2s;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .stButton button:active {
        transform: scale(0.98);
    }
    
    /* تخصيص الأزرار الأساسية */
    div[data-testid="stButton"] button[kind="primary"] {
        background-color: #e91e63; /* لون مميز للبوتيك */
        border: none;
    }

    /* تحسين حقول الإدخال */
    .stTextInput input, .stNumberInput input {
        border-radius: 10px;
        border: 1px solid #ddd;
        padding: 10px;
    }

    /* إخفاء عناصر ستريم ليت الافتراضية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* تحسين الجدول للموبايل */
    div[data-testid="stDataFrame"] {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. دوال قاعدة البيانات (نفس المنطق القوي السابق) ---
@st.cache_resource
def init_connection():
    try:
        return psycopg2.connect(st.secrets["DB_URL"])
    except Exception as e:
        st.error(f"⚠️ خطأ اتصال: {e}")
        return None

def run_query(query, params=(), fetch_data=False, commit=True):
    conn = init_connection()
    if conn:
        try:
            if conn.closed: conn = init_connection()
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
            conn.rollback()
            # st.error(f"Error: {e}") # إلغاء طباعة الخطأ للمستخدم العادي
            return None
    return None

# --- 4. منطق الجلسة (Session State) ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'auth' not in st.session_state: st.session_state.auth = False
# لتتبع التبويب النشط في نقطة البيع (منتجات vs سلة)
if 'pos_tab' not in st.session_state: st.session_state.pos_tab = "المنتجات"

# --- 5. الشاشات ---

def login_ui():
    col1, col2, col3 = st.columns([1, 8, 1])
    with col2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #e91e63;'>🌸 نواعم بوتيك</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: gray;'>نظام إدارة المبيعات الذكي</p>", unsafe_allow_html=True)
        
        with st.container(border=True):
            pwd = st.text_input("🔑 كلمة المرور", type="password")
            if st.button("دخول النظام", type="primary"):
                admin_pass = st.secrets.get("ADMIN_PASS", "admin")
                if pwd == admin_pass:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.toast("كلمة المرور غير صحيحة", icon="❌")

def process_sale(customer_name):
    # منطق البيع (نفس السابق مع تحسينات بسيطة)
    conn = init_connection()
    if not conn: return False
    try:
        cur = conn.cursor()
        dt = datetime.now(pytz.timezone('Asia/Baghdad'))
        inv_id = dt.strftime("%Y%m%d%H%M%S")
        
        # جلب أو إنشاء العميل
        cur.execute("SELECT id FROM customers WHERE name = %s", (customer_name,))
        res = cur.fetchone()
        if res:
            cust_id = res[0]
        else:
            cur.execute("INSERT INTO customers (name) VALUES (%s) RETURNING id", (customer_name,))
            cust_id = cur.fetchone()[0]
        
        for item in st.session_state.cart:
            cur.execute("SELECT stock FROM variants WHERE id = %s FOR UPDATE", (item['id'],))
            row = cur.fetchone()
            if not row or row[0] < item['qty']:
                raise Exception(f"نفذت الكمية: {item['name']}")
            
            cur.execute("UPDATE variants SET stock = stock - %s WHERE id = %s", (item['qty'], item['id']))
            profit = (item['price'] - item['cost']) * item['qty']
            cur.execute("""
                INSERT INTO sales (customer_id, variant_id, product_name, qty, total, profit, date, invoice_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (cust_id, item['id'], item['name'], item['qty'], item['total'], profit, dt, inv_id))
            
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        conn.rollback()
        st.toast(f"حدث خطأ: {e}", icon="⚠️")
        return False

def main_app():
    # --- الشريط الجانبي (Sidebar) ---
    with st.sidebar:
        st.title("🌸 القائمة")
        selected_page = st.radio(
            "اختر القسم:", 
            ["🛒 نقطة البيع", "📦 المخزون", "📊 التقارير", "🧾 الفواتير"],
            label_visibility="collapsed"
        )
        st.divider()
        if st.button("تسجيل خروج"):
            st.session_state.auth = False
            st.rerun()
        st.caption("v2.0 | تصميم متجاوب")

    # === الصفحة 1: نقطة البيع (POS) ===
    if selected_page == "🛒 نقطة البيع":
        st.markdown("### 🛒 نقطة البيع")
        
        # تبويبات للموبايل (المنتجات | السلة)
        tab_products, tab_cart = st.tabs(["🛍️ المنتجات", f"🛒 السلة ({len(st.session_state.cart)})"])
        
        # --- تبويب المنتجات ---
        with tab_products:
            # شريط البحث
            search = st.text_input("🔍 بحث سريع (الاسم / اللون)", placeholder="اكتب للبحث...", label_visibility="collapsed")
            
            # استعلام ذكي
            q = "SELECT * FROM variants WHERE is_active = TRUE AND stock > 0"
            p = []
            if search:
                q += " AND (name ILIKE %s OR color ILIKE %s)"
                p = [f"%{search}%", f"%{search}%"]
            q += " ORDER BY id DESC LIMIT 20"
            
            items = run_query(q, tuple(p), fetch_data=True)
            
            if items is not None and not items.empty:
                # عرض شبكي (Grid Layout) ليكون جميلاً
                # في الموبايل ستظهر واحدة تلو الأخرى، في الديسك توب 2 بجانب بعض
                cols = st.columns(2) 
                for idx, row in items.iterrows():
                    with cols[idx % 2]:
                        with st.container(border=True):
                            # Header: Name & Price
                            c1, c2 = st.columns([2, 1])
                            c1.markdown(f"**{row['name']}**")
                            c1.caption(f"🎨 {row['color']} | 📏 {row['size']}")
                            
                            c2.markdown(f"<div style='text-align:left; color:#e91e63; font-weight:bold'>{int(row['price']):,}</div>", unsafe_allow_html=True)
                            
                            # Controls: Qty & Add
                            cc1, cc2 = st.columns([1, 2])
                            qty = cc1.number_input("العدد", 1, max_value=row['stock'], key=f"q_{row['id']}", label_visibility="collapsed")
                            
                            if cc2.button("أضف للسلة 🛒", key=f"add_{row['id']}", type="secondary"):
                                # منطق الإضافة
                                found = False
                                for i in st.session_state.cart:
                                    if i['id'] == row['id']:
                                        i['qty'] += qty
                                        i['total'] += (qty * row['price'])
                                        found = True
                                        break
                                if not found:
                                    st.session_state.cart.append({
                                        "id": row['id'], "name": row['name'], 
                                        "price": row['price'], "qty": qty, 
                                        "total": qty * row['price'], "cost": row['cost']
                                    })
                                st.toast(f"تمت إضافة {row['name']}", icon="✅")
                                st.rerun()
            else:
                st.info("لا توجد منتجات مطابقة")

        # --- تبويب السلة ---
        with tab_cart:
            if st.session_state.cart:
                total_bill = sum(i['total'] for i in st.session_state.cart)
                
                for idx, item in enumerate(st.session_state.cart):
                    with st.container(border=True):
                        c_det, c_act = st.columns([3, 1])
                        c_det.markdown(f"**{item['name']}** (x{item['qty']})")
                        c_det.caption(f"السعر: {item['price']:,.0f} | الإجمالي: {item['total']:,.0f}")
                        if c_act.button("❌", key=f"rm_{idx}"):
                            st.session_state.cart.pop(idx)
                            st.rerun()
                
                st.divider()
                # ملخص الفاتورة الثابت
                st.markdown(
                    f"""
                    <div style="background:#e91e63; color:white; padding:15px; border-radius:10px; text-align:center; margin-bottom:10px;">
                        <h3 style="color:white; margin:0;">الإجمالي: {total_bill:,.0f} د.ع</h3>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
                
                c_name = st.text_input("👤 اسم العميل", placeholder="مطلوب لإتمام البيع")
                
                if st.button("✅ إتمام عملية البيع", type="primary", use_container_width=True):
                    if not c_name:
                        st.toast("الرجاء إدخال اسم العميل!", icon="⚠️")
                    else:
                        if process_sale(c_name):
                            st.session_state.cart = []
                            st.balloons()
                            st.success("تم حفظ الفاتورة بنجاح!")
                            st.rerun()
            else:
                st.empty()
                st.info("السلة فارغة حالياً")

    # === الصفحة 2: إدارة المخزون ===
    elif selected_page == "📦 المخزون":
        st.markdown("### 📦 إدارة المخزون")
        
        # جعل الجدول قابل للتعديل بشكل كامل
        df = run_query("SELECT id, name, color, size, stock, price, cost FROM variants ORDER BY id DESC", fetch_data=True)
        
        if df is not None:
            edited_df = st.data_editor(
                df,
                column_config={
                    "id": None, # إخفاء ال ID
                    "name": "المنتج",
                    "color": "اللون",
                    "size": "المقاس",
                    "stock": st.column_config.NumberColumn("الكمية", min_value=0, format="%d"),
                    "price": st.column_config.NumberColumn("سعر البيع", format="%d IQD"),
                    "cost": st.column_config.NumberColumn("التكلفة", format="%d IQD"),
                },
                use_container_width=True,
                num_rows="dynamic", # السماح بإضافة صفوف جديدة
                key="inventory_edit"
            )
            
            if st.button("💾 حفظ التغييرات في قاعدة البيانات", type="primary"):
                # ملاحظة: هذا كود مبسط للتحديث، في الإنتاج يفضل تتبع التغييرات فقط
                # لكن بما أن الداتا صغيرة، سنحدث الصفوف الموجودة ونضيف الجديد
                conn = init_connection()
                cur = conn.cursor()
                try:
                    # 1. التحديث والإضافة
                    for index, row in edited_df.iterrows():
                        if row['id'] is None or pd.isna(row['id']): # صف جديد
                            cur.execute(
                                "INSERT INTO variants (name, color, size, stock, price, cost) VALUES (%s, %s, %s, %s, %s, %s)",
                                (row['name'], row['color'], row['size'], row['stock'], row['price'], row['cost'])
                            )
                        else: # تحديث
                            cur.execute(
                                "UPDATE variants SET name=%s, color=%s, size=%s, stock=%s, price=%s, cost=%s WHERE id=%s",
                                (row['name'], row['color'], row['size'], row['stock'], row['price'], row['cost'], row['id'])
                            )
                    conn.commit()
                    st.toast("تم تحديث المخزون بنجاح", icon="💾")
                except Exception as e:
                    st.error(f"خطأ: {e}")
                    conn.rollback()
                finally:
                    cur.close()

    # === الصفحة 3: التقارير ===
    elif selected_page == "📊 التقارير":
        st.markdown("### 📊 لوحة المعلومات")
        
        # فلاتر سريعة
        days = st.selectbox("الفترة الزمنية", [1, 7, 30], format_func=lambda x: "اليوم" if x==1 else f"آخر {x} يوم")
        
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        df_res = run_query(f"""
            SELECT date::date as day, SUM(total) as total_sales, SUM(profit) as total_profit
            FROM sales WHERE date >= '{start_date}' GROUP BY day ORDER BY day
        """, fetch_data=True)
        
        if df_res is not None and not df_res.empty:
            sales = df_res['total_sales'].sum()
            profit = df_res['total_profit'].sum()
            
            # عرض بطاقات الأرقام
            c1, c2 = st.columns(2)
            c1.metric("المبيعات", f"{sales:,.0f}", delta="د.ع")
            c2.metric("الأرباح", f"{profit:,.0f}", delta_color="normal")
            
            # رسم بياني أنيق
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_res['day'], y=df_res['total_sales'], name='مبيعات', marker_color='#e91e63'))
            fig.add_trace(go.Scatter(x=df_res['day'], y=df_res['total_profit'], name='أرباح', line=dict(color='#2c3e50', width=3)))
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=0, r=0, t=30, b=0), height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("لا توجد مبيعات في هذه الفترة")

    # === الصفحة 4: الفواتير ===
    elif selected_page == "🧾 الفواتير":
        st.markdown("### 🧾 سجل الفواتير")
        df_inv = run_query("""
            SELECT s.invoice_id as "رقم الفاتورة", c.name as "العميل", s.product_name as "المنتج", 
                   s.total as "القيمة", s.date as "الوقت"
            FROM sales s JOIN customers c ON s.customer_id = c.id 
            ORDER BY s.id DESC LIMIT 50
        """, fetch_data=True)
        st.dataframe(df_inv, use_container_width=True, hide_index=True)

# --- نقطة الانطلاق ---
if __name__ == "__main__":
    if st.session_state.auth:
        main_app()
    else:
        login_ui()
