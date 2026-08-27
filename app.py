import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime, date
import os

# --- UPLOAD KLASÖRÜ ---
if not os.path.exists("uploads"):
    os.makedirs("uploads")

# --- VERİTABANI VE AKILLI GÜNCELLEME İŞLEMLERİ ---
def init_db():
    conn = sqlite3.connect("insaat_takip.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Kullanıcılar tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    cursor.execute("PRAGMA table_info(users)")
    user_cols = [col[1] for col in cursor.fetchall()]
    if "is_admin" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
    
    # Ayarlar tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # Projeler tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            total_apartments INTEGER
        )
    ''')
    cursor.execute("PRAGMA table_info(projects)")
    proj_cols = [col[1] for col in cursor.fetchall()]
    if "total_apartments" not in proj_cols:
        cursor.execute("ALTER TABLE projects ADD COLUMN total_apartments INTEGER")
    
    # Proje Kat Planı tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_floors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            floor_name TEXT,
            apartment_count INTEGER,
            unit_price REAL
        )
    ''')
    
    # Ev Sahipleri / Müşteriler tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            name TEXT,
            blok TEXT,
            kat TEXT,
            daire TEXT,
            description TEXT,
            total_price REAL,
            sale_date TEXT,
            contract_file_path TEXT
        )
    ''')
    cursor.execute("PRAGMA table_info(customers)")
    cust_cols = [col[1] for col in cursor.fetchall()]
    if "blok" not in cust_cols:
        cursor.execute("ALTER TABLE customers ADD COLUMN blok TEXT")
    if "kat" not in cust_cols:
        cursor.execute("ALTER TABLE customers ADD COLUMN kat TEXT")
    if "daire" not in cust_cols:
        cursor.execute("ALTER TABLE customers ADD COLUMN daire TEXT")
    if "description" not in cust_cols:
        cursor.execute("ALTER TABLE customers ADD COLUMN description TEXT")
    if "sale_date" not in cust_cols:
        cursor.execute("ALTER TABLE customers ADD COLUMN sale_date TEXT")
    if "contract_file_path" not in cust_cols:
        cursor.execute("ALTER TABLE customers ADD COLUMN contract_file_path TEXT")
    
    # Müşteri Ödeme Planı (Taksitler ve Vade Tarihleri) tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_payment_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            installment_name TEXT,
            amount REAL,
            due_date TEXT
        )
    ''')
    
    # Müşteri Ödemeleri tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            date TEXT,
            amount REAL,
            payment_method TEXT,
            description TEXT,
            receipt_file_path TEXT
        )
    ''')
    cursor.execute("PRAGMA table_info(customer_payments)")
    cp_cols = [col[1] for col in cursor.fetchall()]
    if "payment_method" not in cp_cols:
        cursor.execute("ALTER TABLE customer_payments ADD COLUMN payment_method TEXT")
    if "receipt_file_path" not in cp_cols:
        cursor.execute("ALTER TABLE customer_payments ADD COLUMN receipt_file_path TEXT")
    
    # Ustalar / Taşeronlar tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tradesmen (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            name TEXT,
            trade_type TEXT,
            description TEXT,
            start_date TEXT,
            contract_file_path TEXT
        )
    ''')
    cursor.execute("PRAGMA table_info(tradesmen)")
    trade_cols = [col[1] for col in cursor.fetchall()]
    if "description" not in trade_cols:
        cursor.execute("ALTER TABLE tradesmen ADD COLUMN description TEXT")
    if "start_date" not in trade_cols:
        cursor.execute("ALTER TABLE tradesmen ADD COLUMN start_date TEXT")
    if "contract_file_path" not in trade_cols:
        cursor.execute("ALTER TABLE tradesmen ADD COLUMN contract_file_path TEXT")
    
    # Usta İşlemleri tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tradesman_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tradesman_id INTEGER,
            trans_type TEXT, 
            date TEXT,
            amount REAL,
            payment_method TEXT,
            description TEXT,
            doc_file_path TEXT
        )
    ''')
    cursor.execute("PRAGMA table_info(tradesman_transactions)")
    tt_cols = [col[1] for col in cursor.fetchall()]
    if "payment_method" not in tt_cols:
        cursor.execute("ALTER TABLE tradesman_transactions ADD COLUMN payment_method TEXT")
    if "doc_file_path" not in tt_cols:
        cursor.execute("ALTER TABLE tradesman_transactions ADD COLUMN doc_file_path TEXT")
    
    # Varsayılan yönetici hesabı
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)", ("admin", "12345", 1))
        
    cursor.execute("SELECT value FROM settings WHERE key = 'invite_code'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO settings (key, value) VALUES ('invite_code', 'santiye2026')")
    
    conn.commit()
    conn.close()

init_db()

def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect("insaat_takip.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(query, params)
    if fetch:
        result = cursor.fetchall()
        conn.close()
        return result
    conn.commit()
    conn.close()

# --- OTURUM YÖNETİMİ ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.is_admin = 0

st.set_page_config(page_title="Şantiye ve Cari Takip Sistemi", layout="wide")

if st.session_state.user_id is None:
    st.title("🏗️ Şantiye Yönetim Sistemi")
    
    tab1, tab2, tab3 = st.tabs(["Giriş Yap", "Kayıt Ol (Davet Kodu)", "Şifremi Unuttum"])
    
    with tab1:
        st.subheader("Sisteme Giriş Yap")
        with st.form("login_form"):
            username = st.text_input("Kullanıcı Adı", key="login_user")
            password = st.text_input("Şifre", type="password", key="login_pass")
            submit_login = st.form_submit_button("Giriş Yap")
            
            if submit_login:
                if username and password:
                    user = run_query("SELECT id, username, is_admin FROM users WHERE username = ? AND password = ?", (username, password), fetch=True)
                    if user:
                        st.session_state.user_id = user[0][0]
                        st.session_state.username = user[0][1]
                        st.session_state.is_admin = user[0][2]
                        st.rerun()
                    else:
                        st.error("Kullanıcı adı veya şifre hatalı!")
                else:
                    st.warning("Lütfen tüm alanları doldurun.")
                
    with tab2:
        st.subheader("Yeni Müteahhit Kaydı")
        st.info("Sisteme kayıt olabilmeniz için yönetici tarafından size verilen **Davet Kodu**'nu girmeniz gerekmektedir.")
        with st.form("reg_form"):
            reg_user = st.text_input("Yeni Kullanıcı Adı Belirleyin", key="reg_user")
            reg_pass = st.text_input("Yeni Şifre Belirleyin", type="password", key="reg_pass")
            reg_code = st.text_input("Gizli Davet Kodu", type="password", key="reg_code")
            submit_reg = st.form_submit_button("Hesabımı Oluştur")
            
            if submit_reg:
                if reg_user and reg_pass and reg_code:
                    db_code = run_query("SELECT value FROM settings WHERE key = 'invite_code'", fetch=True)[0][0]
                    if reg_code == db_code:
                        try:
                            run_query("INSERT INTO users (username, password, is_admin) VALUES (?, ?, 0)", (reg_user, reg_pass))
                            st.success("Kayıt başarılı! 'Giriş Yap' sekmesinden giriş yapabilirsiniz.")
                        except:
                            st.error("Bu kullanıcı adı zaten alınmış, lütfen başka bir tane deneyin.")
                    else:
                        st.error("Hatalı Davet Kodu!")
                else:
                    st.warning("Lütfen tüm alanları doldurun.")

    with tab3:
        st.subheader("Şifre Sıfırlama")
        st.info("Şifrenizi unuttuysanız kullanıcı adınızı, yeni şifrenizi ve sistemin **Gizli Davet Kodu**'nu girerek şifrenizi yenileyebilirsiniz.")
        with st.form("forgot_form"):
            f_user = st.text_input("Kullanıcı Adınız", key="f_user")
            f_new_pass = st.text_input("Yeni Şifreniz", type="password", key="f_new_pass")
            f_code = st.text_input("Gizli Davet Kodu", type="password", key="f_code")
            submit_forgot = st.form_submit_button("Şifremi Sıfırla")
            
            if submit_forgot:
                if f_user and f_new_pass and f_code:
                    db_code = run_query("SELECT value FROM settings WHERE key = 'invite_code'", fetch=True)[0][0]
                    if f_code == db_code:
                        user_check = run_query("SELECT id FROM users WHERE username = ?", (f_user,), fetch=True)
                        if user_check:
                            run_query("UPDATE users SET password = ? WHERE username = ?", (f_new_pass, f_user))
                            st.success("Şifreniz başarıyla güncellendi! 'Giriş Yap' sekmesinden giriş yapabilirsiniz.")
                        else:
                            st.error("Böyle bir kullanıcı adı bulunamadı.")
                    else:
                        st.error("Hatalı Davet Kodu!")
                else:
                    st.warning("Lütfen tüm alanları doldurun.")
else:
    # --- ANA UYGULAMA ---
    st.sidebar.title(f"Hoş geldiniz, {st.session_state.username}")
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.user_id = None
        st.session_state.username = None
        st.session_state.is_admin = 0
        st.rerun()
        
    # ŞİFRE DEĞİŞTİRME PANELİ
    with st.sidebar.expander("⚙️ Şifremi Değiştir"):
        with st.form("change_pass_form"):
            old_pass = st.text_input("Mevcut Şifre", type="password", key="old_p")
            new_pass_1 = st.text_input("Yeni Şifre", type="password", key="new_p1")
            new_pass_2 = st.text_input("Yeni Şifre (Tekrar)", type="password", key="new_p2")
            submit_pass = st.form_submit_button("Şifreyi Güncelle")
            
            if submit_pass:
                if old_pass and new_pass_1 and new_pass_2:
                    current_db_pass = run_query("SELECT password FROM users WHERE id = ?", (st.session_state.user_id,), fetch=True)[0][0]
                    if old_pass == current_db_pass:
                        if new_pass_1 == new_pass_2:
                            run_query("UPDATE users SET password = ? WHERE id = ?", (new_pass_1, st.session_state.user_id))
                            st.success("Şifreniz başarıyla değiştirildi!")
                        else:
                            st.error("Yeni şifreler birbiriyle uyuşmuyor.")
                    else:
                        st.error("Mevcut şifrenizi hatalı girdiniz.")
                else:
                    st.warning("Lütfen tüm alanları doldurun.")

    # YÖNETİCİ PANELİ
    if st.session_state.is_admin == 1:
        with st.sidebar.expander("🛠️ Yönetici Ayarları"):
            current_code = run_query("SELECT value FROM settings WHERE key = 'invite_code'", fetch=True)[0][0]
            st.write(f"Mevcut Davet Kodu: **{current_code}**")
            
            with st.form("admin_settings_form"):
                new_invite = st.text_input("Yeni Davet Kodu Belirle", key="new_inv")
                submit_inv = st.form_submit_button("Kodu Güncelle")
                if submit_inv:
                    if new_invite:
                        run_query("UPDATE settings SET value = ? WHERE key = 'invite_code'", (new_invite,))
                        st.success("Davet kodu güncellendi!")
                        st.rerun()
                    else:
                        st.warning("Kod boş olamaz.")

    st.sidebar.header("Proje Yönetimi")
    projects = run_query("SELECT id, name, total_apartments FROM projects WHERE user_id = ?", (st.session_state.user_id,), fetch=True)
    project_dict = {p[1]: p[0] for p in projects}
    
    if project_dict:
        selected_project_name = st.sidebar.selectbox("Aktif Projeyi Seçin", list(project_dict.keys()))
        project_id = project_dict[selected_project_name]
        
        # PROJE DÜZENLE / SİL PANELİ
        with st.sidebar.expander("⚙️ Projeyi Düzenle / Sil"):
            with st.form("edit_project_form"):
                current_proj_info = run_query("SELECT name, total_apartments FROM projects WHERE id = ?", (project_id,), fetch=True)[0]
                edit_name = st.text_input("Proje Adı", value=current_proj_info[0])
                edit_aps = st.number_input("Toplam Daire Sayısı", min_value=1, value=int(current_proj_info[1]) if current_proj_info[1] else 12, step=1)
                submit_edit = st.form_submit_button("Projeyi Güncelle")
                
                if submit_edit:
                    if edit_name:
                        run_query("UPDATE projects SET name = ?, total_apartments = ? WHERE id = ?", (edit_name, edit_aps, project_id))
                        st.success("Proje güncellendi!")
                        st.rerun()
                    else:
                        st.warning("Proje adı boş olamaz.")
            
            if st.button("Bu Projeyi Tamamen Sil", type="primary"):
                custs = run_query("SELECT id FROM customers WHERE project_id = ?", (project_id,), fetch=True)
                for c in custs:
                    run_query("DELETE FROM customer_payments WHERE customer_id = ?", (c[0],))
                    run_query("DELETE FROM customer_payment_plans WHERE customer_id = ?", (c[0],))
                run_query("DELETE FROM customers WHERE project_id = ?", (project_id,))
                
                trades = run_query("SELECT id FROM tradesmen WHERE project_id = ?", (project_id,), fetch=True)
                for t in trades:
                    run_query("DELETE FROM tradesman_transactions WHERE tradesman_id = ?", (t[0],))
                run_query("DELETE FROM tradesmen WHERE project_id = ?", (project_id,))
                
                run_query("DELETE FROM project_floors WHERE project_id = ?", (project_id,))
                run_query("DELETE FROM projects WHERE id = ?", (project_id,))
                st.success("Proje silindi!")
                st.rerun()
    else:
        selected_project_name = st.sidebar.selectbox("Aktif Projeyi Seçin", ["Proje Yok"])
    
    with st.sidebar.expander("➕ Yeni Proje Ekle"):
        with st.form("new_project_form"):
            new_proj_name = st.text_input("Proje Adı (Örn: Moda Rezidans)")
            total_aps = st.number_input("Toplam Daire Sayısı", min_value=1, value=12, step=1)
            
            submit_proj = st.form_submit_button("Proje Oluştur")
            if submit_proj:
                if new_proj_name:
                    run_query("INSERT INTO projects (user_id, name, total_apartments) VALUES (?, ?, ?)", 
                              (st.session_state.user_id, new_proj_name, total_aps))
                    st.success("Proje eklendi!")
                    st.rerun()
                else:
                    st.warning("Proje adı boş olamaz.")

    if not project_dict:
        st.warning("Lütfen sol menüden yeni bir proje oluşturun.")
    else:
        project_id = project_dict[selected_project_name]
        st.title(f"📍 Proje: {selected_project_name}")
        
        tab_homeowners, tab_tradesmen, tab_summary = st.tabs(["🏠 Ev Sahipleri & Gelirler", "👷 Ustalar & Taşeronlar", "📊 Genel Durum & Kâr/Zarar"])
        
        # --- EV SAHİPLERİ SEKMESİ ---
        with tab_homeowners:
            st.subheader("Ev Sahipleri, Ödeme Planı ve Kalan Borç Takibi")
            
            with st.form("new_customer"):
                col1, col2, col3, col4 = st.columns(4)
                c_name = col1.text_input("Ev Sahibi Adı Soyadı")
                c_blok = col2.text_input("Blok (Örn: A Blok)")
                c_kat = col3.text_input("Kat (Örn: 3. Kat)")
                c_daire = col4.text_input("Daire No (Örn: 12)")
                
                col5, col6, col7 = st.columns(3)
                c_price = col5.number_input("Toplam Satış Bedeli (TL)", min_value=0.0, step=1000.0)
                c_date = col6.date_input("Satış / Sözleşme Tarihi", datetime.now())
                c_desc = col7.text_area("Açıklama / Notlar", placeholder="Örn: Kapora alındı, tapu aşamasında...")
                
                c_file = st.file_uploader("Sözleşme Belgesi Yükle (PDF, Fotoğraf / Kamera)", type=["pdf", "png", "jpg", "jpeg"], key="c_contract_file")
                
                submit_c = st.form_submit_button("Ev Sahibi Ekle")
                if submit_c and c_name:
                    file_path = None
                    if c_file is not None:
                        file_path = os.path.join("uploads", f"c_{int(datetime.now().timestamp())}_{c_file.name}")
                        with open(file_path, "wb") as f:
                            f.write(c_file.getbuffer())
                            
                    run_query("INSERT INTO customers (project_id, name, blok, kat, daire, description, total_price, sale_date, contract_file_path) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                              (project_id, c_name, c_blok, c_kat, c_daire, c_desc, c_price, str(c_date), file_path))
                    st.success("Ev sahibi ve sözleşme eklendi!")
                    st.rerun()
                    
            st.divider()
            customers = run_query("SELECT id, name, blok, kat, daire, description, total_price, sale_date, contract_file_path FROM customers WHERE project_id = ?", (project_id,), fetch=True)
            
            if customers:
                customer_dict = {f"{c[1]} (Blok: {c[2]} | Kat: {c[3]} | Daire: {c[4]})": c[0] for c in customers}
                selected_cust = st.selectbox("İşlem Yapılacak Ev Sahibini Seçin", list(customer_dict.keys()))
                cust_id = customer_dict[selected_cust]
                
                c_info = [c for c in customers if c[0] == cust_id][0]
                total_price = c_info[6]
                c_description = c_info[5]
                c_sale_date = c_info[7]
                c_contract_path = c_info[8]
                
                if c_sale_date:
                    st.write(f"📅 **Sözleşme / Satış Tarihi:** {c_sale_date}")
                if c_description:
                    st.info(f"📝 **Not / Açıklama:** {c_description}")
                    
                if c_contract_path and os.path.exists(c_contract_path):
                    with st.expander("📄 Yüklenen Sözleşme Belgesini Görüntüle"):
                        if c_contract_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                            st.image(c_contract_path, caption="Sözleşme Görseli", use_column_width=True)
                        with open(c_contract_path, "rb") as file_download:
                            st.download_button(
                                label="📥 Sözleşmeyi İndir",
                                data=file_download,
                                file_name=os.path.basename(c_contract_path),
                                mime="application/octet-stream",
                                key="down_c_contract"
                            )
                
                # --- VADE & GECİKME KONTROLÜ ---
                total_paid = run_query("SELECT SUM(amount) FROM customer_payments WHERE customer_id = ?", (cust_id,), fetch=True)[0][0] or 0.0
                payment_plans = run_query("SELECT id, installment_name, amount, due_date FROM customer_payment_plans WHERE customer_id = ? ORDER BY due_date ASC", (cust_id,), fetch=True)
                
                today_date = date.today()
                cumulative_plan = 0
                
                for plan in payment_plans:
                    p_id, p_name, p_amt, p_due = plan
                    try:
                        p_due_date = datetime.strptime(p_due, "%Y-%m-%d").date()
                    except:
                        continue
                    cumulative_plan += p_amt
                    if p_due_date < today_date and total_paid < cumulative_plan:
                        st.error(f"⚠️ **Vadesi Geçmiş Ödeme Uyarısı:** `{p_name}` ({p_amt:,.2f} TL) vadesi **{p_due}** tarihinde dolmuş ancak henüz ödenmemiştir!")

                remaining_debt = total_price - total_paid
                
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Toplam Satış Bedeli", f"{total_price:,.2f} TL")
                col_b.metric("Ödenen Toplam", f"{total_paid:,.2f} TL")
                col_c.metric("Kalan Borç", f"{remaining_debt:,.2f} TL", delta_color="inverse")
                
                st.divider()
                
                # --- DOĞRUDAN ALT ALTA SIRALI BÖLÜMLER ---
                
                # 1. BÖLÜM: ÖDEME PLANI (PEŞİNAT, 1. TAKSİT VB. ALT ALTA)
                st.markdown("### 📅 Ödeme Planı (Taksitler ve Vadeler)")
                
                # Yeni Taksit Ekleme Formu
                with st.form(f"plan_form_{cust_id}"):
                    col_pl1, col_pl2, col_pl3 = st.columns(3)
                    pl_name = col_pl1.text_input("Taksit Adı (Örn: Peşinat, 1. Taksit, 2. Taksit)")
                    pl_amount = col_pl2.number_input("Tutar (TL)", min_value=0.0, step=500.0, key=f"pl_amt_{cust_id}")
                    pl_date = col_pl3.date_input("Vade Tarihi", datetime.now(), key=f"pl_date_{cust_id}")
                    
                    submit_plan = st.form_submit_button("Plana Taksit Ekle")
                    if submit_plan and pl_name and pl_amount > 0:
                        run_query("INSERT INTO customer_payment_plans (customer_id, installment_name, amount, due_date) VALUES (?, ?, ?, ?)",
                                  (cust_id, pl_name, pl_amount, str(pl_date)))
                        st.success("Taksit vade planına eklendi!")
                        st.rerun()

                # Taksitleri Alt Alta Listeleme
                if payment_plans:
                    for p in payment_plans:
                        p_id, p_name, p_amt, p_due = p
                        status_badge = "⏳ Bekliyor"
                        try:
                            d_date = datetime.strptime(p_due, "%Y-%m-%d").date()
                            if d_date < today_date and total_paid < p_amt:
                                status_badge = "🔴 Vadesi Geçti!"
                            elif total_paid >= p_amt:
                                status_badge = "🟢 Ödendi"
                        except:
                            pass
                        
                        st.info(f"📌 **{p_name}** | Tutar: **{p_amt:,.2f} TL** | Vade: **{p_due}** | Durum: **{status_badge}**")
                else:
                    st.info("Bu müşteri için henüz alt alta sıralı bir taksit planı girilmemiş.")

                st.divider()

                # 2. BÖLÜM: ÖDEME YAP / TAHSİLAT & DEKONT YÜKLE
                st.markdown("### 💳 Ödeme Al / Tahsilat Gir ve Dekont Yükle")
                with st.form(f"pay_form_{cust_id}"):
                    col_p1, col_p2, col_p3 = st.columns(3)
                    p_date = col_p1.date_input("Ödeme Tarihi", datetime.now(), key=f"p_date_{cust_id}")
                    p_amount = col_p2.number_input("Ödeme Miktarı (TL)", min_value=0.0, step=500.0, key=f"p_amt_{cust_id}")
                    p_method = col_p3.selectbox("Ödeme Yöntemi", ["Banka Havalesi / EFT", "Elden Nakit", "Çek / Senet", "Kredi Kartı", "Diğer"], key=f"p_meth_{cust_id}")
                    
                    col_p4, col_p5 = st.columns(2)
                    p_desc = col_p4.text_input("Açıklama (Örn: Peşinat ödemesi, 1. Taksit vb.)", key=f"p_desc_{cust_id}")
                    p_receipt = col_p5.file_uploader("Dekont / Makbuz Yükle (PDF, Fotoğraf)", type=["pdf", "png", "jpg", "jpeg"], key=f"p_rec_{cust_id}")
                    
                    sub_p = st.form_submit_button("Tahsilatı Kaydet")
                    if sub_p and p_amount > 0:
                        receipt_path = None
                        if p_receipt is not None:
                            receipt_path = os.path.join("uploads", f"rec_{int(datetime.now().timestamp())}_{p_receipt.name}")
                            with open(receipt_path, "wb") as f:
                                f.write(p_receipt.getbuffer())
                                
                        run_query("INSERT INTO customer_payments (customer_id, date, amount, payment_method, description, receipt_file_path) VALUES (?, ?, ?, ?, ?, ?)",
                                  (cust_id, str(p_date), p_amount, p_method, p_desc, receipt_path))
                        st.success("Ödeme ve dekont kaydedildi!")
                        st.rerun()
                        
                st.markdown("#### 📜 Geçmiş Ödemeler ve Dekontlar")
                pay_history = run_query("SELECT id, date, amount, payment_method, description, receipt_file_path FROM customer_payments WHERE customer_id = ?", (cust_id,), fetch=True)
                if pay_history:
                    table_data = [[p[1], f"{p[2]:,.2f} TL", p[3] or "-", p[4] or "-", "✅ Var" if p[5] else "Yok"] for p in pay_history]
                    df_pay = pd.DataFrame(table_data, columns=["Tarih", "Tutar", "Ödeme Yöntemi", "Açıklama", "Dekont"])
                    st.dataframe(df_pay, use_container_width=True)
                    
                    receipt_list = [p for p in pay_history if p[5] and os.path.exists(p[5])]
                    if receipt_list:
                        with st.expander("📎 Kayıtlı Dekontları İncele / İndir"):
                            for rec in receipt_list:
                                r_id, r_date, r_amt, r_meth, r_desc, r_path = rec
                                st.write(f"**Tarih:** {r_date} | **Tutar:** {r_amt:,.2f} TL ({r_meth})")
                                if r_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                                    st.image(r_path, width=250)
                                with open(r_path, "rb") as rf:
                                    st.download_button(
                                        label=f"📥 Dekontu İndir ({os.path.basename(r_path)})",
                                        data=rf,
                                        file_name=os.path.basename(r_path),
                                        mime="application/octet-stream",
                                        key=f"down_rec_{r_id}"
                                    )
                                st.divider()
                else:
                    st.info("Henüz ödeme kaydı bulunmuyor.")

        # --- USTALAR / TAŞERONLAR SEKMESİ ---
        with tab_tradesmen:
            st.subheader("Usta ve Taşeron Cari Takibi")
            
            col_t1, col_t2 = st.columns(2)
            t_name = col_t1.text_input("Usta / Firma Adı (Örn: Ahmet Usta)", key="t_name_input")
            t_type_select = col_t2.selectbox("Usta Branşı", ["Sıvacı", "Kalıpçı", "Camcı", "Parkeci", "Elektrikçi", "Tesisatçı", "Demirci", "Mermerci", "Boyacı", "Çatıcı", "Diğer"], key="t_type_sel")
            
            custom_trade = ""
            if t_type_select == "Diğer":
                custom_trade = st.text_input("Lütfen Usta Branşını Yazın (Örn: Asansörcü, İskeleci)", key="custom_trade_input")
                final_trade = custom_trade if custom_trade else "Diğer"
            else:
                final_trade = t_type_select
                
            with st.form("new_tradesman"):
                col_t3, col_t4 = st.columns(2)
                t_date = col_t3.date_input("Anlaşma / Başlangıç Tarihi", datetime.now(), key="t_start_date")
                t_file = col_t4.file_uploader("Usta Sözleşmesi / Teklif Belgesi", type=["pdf", "png", "jpg", "jpeg"], key="t_contract_file")
                t_desc = st.text_area("Usta / İş Açıklaması / Notlar", placeholder="Örn: 1. kat ince sıva işi...")
                
                submit_t = st.form_submit_button("Usta Ekle")
                if submit_t and t_name:
                    t_doc_path = None
                    if t_file is not None:
                        t_doc_path = os.path.join("uploads", f"t_doc_{int(datetime.now().timestamp())}_{t_file.name}")
                        with open(t_doc_path, "wb") as f:
                            f.write(t_file.getbuffer())
                            
                    run_query("INSERT INTO tradesmen (project_id, name, trade_type, description, start_date, contract_file_path) VALUES (?, ?, ?, ?, ?, ?)", 
                              (project_id, t_name, final_trade, t_desc, str(t_date), t_doc_path))
                    st.success(f"{final_trade} - {t_name} kartı açıldı!")
                    st.rerun()
            
            st.divider()
            tradesmen_list = run_query("SELECT id, name, trade_type, description, start_date, contract_file_path FROM tradesmen WHERE project_id = ?", (project_id,), fetch=True)
            
            if tradesmen_list:
                t_dict = {f"{t[1]} - ({t[2]})": t[0] for t in tradesmen_list}
                sel_t_str = st.selectbox("İşlem Yapılacak Ustayı Seçin", list(t_dict.keys()))
                t_id = t_dict[sel_t_str]
                
                t_info = [t for t in tradesmen_list if t[0] == t_id][0]
                t_description = t_info[3]
                t_start_date = t_info[4]
                t_contract_path = t_info[5]
                
                if t_start_date:
                    st.write(f"📅 **Anlaşma / Başlangıç Tarihi:** {t_start_date}")
                if t_description:
                    st.info(f"📝 **Usta Notu / Açıklama:** {t_description}")
                    
                if t_contract_path and os.path.exists(t_contract_path):
                    with st.expander("📄 Usta Sözleşmesi / Teklif Belgesini Görüntüle"):
                        if t_contract_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                            st.image(t_contract_path, width=300)
                        with open(t_contract_path, "rb") as tf_down:
                            st.download_button(
                                label="📥 Usta Sözleşmesini İndir",
                                data=tf_down,
                                file_name=os.path.basename(t_contract_path),
                                mime="application/octet-stream",
                                key="down_t_contract"
                            )
                
                t_trans = run_query("SELECT trans_type, amount FROM tradesman_transactions WHERE tradesman_id = ?", (t_id,), fetch=True)
                total_debt = sum([t[1] for t in t_trans if t[0] == 'Hakediş (Borç)'])
                total_paid = sum([t[1] for t in t_trans if t[0] == 'Ödeme'])
                remaining_balance = total_debt - total_paid 
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Toplam Hakediş (Borç)", f"{total_debt:,.2f} TL")
                col2.metric("Yapılan Ödemeler", f"{total_paid:,.2f} TL")
                col3.metric("Kalan Bakiye (Ustaya Borç)", f"{remaining_balance:,.2f} TL")
                
                with st.form("t_trans_form"):
                    col_tr1, col_tr2, col_tr3 = st.columns(3)
                    ttype = col_tr1.selectbox("İşlem Türü", ["Hakediş (Borç)", "Ödeme"])
                    t_date_trans = col_tr2.date_input("İşlem Tarihi", datetime.now(), key="t_date_tr")
                    t_amount = col_tr3.number_input("Tutar (TL)", min_value=0.0, step=500.0, key="t_amt")
                    
                    col_tr4, col_tr5 = st.columns(2)
                    t_method = col_tr4.selectbox("Ödeme Yöntemi / İşlem Kanalı", ["Banka Havalesi / EFT", "Elden Nakit", "Çek / Senet", "Fatura Karşılığı", "Diğer"])
                    t_trans_file = col_tr5.file_uploader("Fatura / Dekont / Hakediş Belgesi", type=["pdf", "png", "jpg", "jpeg"], key="t_tr_file")
                    
                    t_desc_trans = st.text_input("Açıklama (Örn: 1. kat sıva hakedişi / Nakit avans)", key="t_desc_tr")
                    sub_tr = st.form_submit_button("İşlemi Kaydet")
                    
                    if sub_tr and t_amount > 0:
                        tr_doc_path = None
                        if t_trans_file is not None:
                            tr_doc_path = os.path.join("uploads", f"tr_{int(datetime.now().timestamp())}_{t_trans_file.name}")
                            with open(tr_doc_path, "wb") as f:
                                f.write(t_trans_file.getbuffer())
                                
                        run_query("INSERT INTO tradesman_transactions (tradesman_id, trans_type, date, amount, payment_method, description, doc_file_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  (t_id, ttype, str(t_date_trans), t_amount, t_method, t_desc_trans, tr_doc_path))
                        st.success("İşlem eklendi!")
                        st.rerun()
                        
                st.text("Cari Hesap Hareketleri")
                t_history = run_query("SELECT id, trans_type, date, amount, payment_method, description, doc_file_path FROM tradesman_transactions WHERE tradesman_id = ?", (t_id,), fetch=True)
                if t_history:
                    table_tr_data = [[h[1], h[2], f"{h[3]:,.2f} TL", h[4] or "-", h[5] or "-", "✅ Var" if h[6] else "Yok"] for h in t_history]
                    df_t = pd.DataFrame(table_tr_data, columns=["İşlem Türü", "Tarih", "Tutar", "Ödeme Yöntemi", "Açıklama", "Belge"])
                    st.dataframe(df_t, use_container_width=True)
                    
                    tr_docs_list = [h for h in t_history if h[6] and os.path.exists(h[6])]
                    if tr_docs_list:
                        with st.expander("📎 Kayıtlı Fatura / Dekont / Belgeleri İncele"):
                            for doc in tr_docs_list:
                                d_id, d_type, d_date, d_amt, d_meth, d_desc, d_path = doc
                                st.write(f"**[{d_type}]** {d_date} | {d_amt:,.2f} TL - {d_desc or ''}")
                                if d_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                                    st.image(d_path, width=250)
                                with open(d_path, "rb") as df_file:
                                    st.download_button(
                                        label=f"📥 Belgeyi İndir ({os.path.basename(d_path)})",
                                        data=df_file,
                                        file_name=os.path.basename(d_path),
                                        mime="application/octet-stream",
                                        key=f"down_trdoc_{d_id}"
                                    )
                                st.divider()
                else:
                    st.info("Bu ustaya ait henüz hareket girilmemiş.")

        # --- GENEL DURUM VE KÂR/ZARAR SEKMESİ ---
        with tab_summary:
            st.subheader(f"📊 {selected_project_name} - Finansal Özet ve Kâr/Zarar Durumu")
            
            p_aps = run_query("SELECT total_apartments FROM projects WHERE id = ?", (project_id,), fetch=True)[0][0] or 0
            st.write(f"🏢 **Toplam Daire Kapasitesi:** {p_aps} Daire")
            
            floor_plans = run_query("SELECT apartment_count, unit_price FROM project_floors WHERE project_id = ?", (project_id,), fetch=True)
            if floor_plans:
                potential_revenue = sum([f[0] * f[1] for f in floor_plans])
                st.write(f"💡 *Kat Fiyatlandırma Planına Göre Tahmini Toplam Proje Değeri:* **{potential_revenue:,.2f} TL**")
            else:
                potential_revenue = 0
                
            all_cust = run_query("SELECT id, total_price FROM customers WHERE project_id = ?", (project_id,), fetch=True)
            total_sales_value = sum([c[1] for c in all_cust])
            total_collected = 0
            total_receivable = 0
            for c in all_cust:
                cid = c[0]
                tp = c[1]
                paid = run_query("SELECT SUM(amount) FROM customer_payments WHERE customer_id = ?", (cid,), fetch=True)[0][0] or 0
                total_collected += paid
                total_receivable += (tp - paid)
                
            all_t = run_query("SELECT id FROM tradesmen WHERE project_id = ?", (project_id,), fetch=True)
            total_tradesman_paid = 0
            total_tradesman_debt = 0
            for t in all_t:
                tid = t[0]
                t_trans = run_query("SELECT trans_type, amount FROM tradesman_transactions WHERE tradesman_id = ?", (tid,), fetch=True)
                total_tradesman_debt += sum([x[1] for x in t_trans if x[0] == 'Hakediş (Borç)'])
                total_tradesman_paid += sum([x[1] for x in t_trans if x[0] == 'Ödeme'])
                
            base_revenue = potential_revenue if potential_revenue > 0 else total_sales_value
            estimated_profit = base_revenue - total_tradesman_debt
            
            st.divider()
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 💰 Gelir & Tahsilat Durumu")
                st.metric("Toplam Satış Sözleşme Bedeli", f"{total_sales_value:,.2f} TL")
                st.metric("Kasaya Giren (Tahsil Edilen)", f"{total_collected:,.2f} TL")
                st.metric("Ev Sahiplerinden Kalan Alacak", f"{total_receivable:,.2f} TL")
                
            with col2:
                st.markdown("### 👷 Gider & Maliyet Durumu")
                st.metric("Ustaların Toplam Hakedişi (Maliyet)", f"{total_tradesman_debt:,.2f} TL")
                st.metric("Ustaya Yapılan Ödemeler", f"{total_tradesman_paid:,.2f} TL")
                st.metric("Ustaların Kalan Alacağı", f"{total_tradesman_debt - total_tradesman_paid:,.2f} TL")
                
            st.divider()
            st.markdown("### 📈 Net Kâr / Zarar Durumu")
            st.metric("Tahmini Net Kâr (Gelir - Toplam Maliyet)", f"{estimated_profit:,.2f} TL", delta_color="normal")
