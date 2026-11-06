import sqlite3
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
import os

# Configuración de la página en navegador
st.set_page_config(
    page_title="Control de Rol de Prácticas — E.M.E.F.A.",
    page_icon="✈️",
    layout="wide"
)

# ==========================================
# GESTIÓN DE BASE DE DATOS
# ==========================================
class BaseDeDatos:
    def __init__(self, db_name="rol_militar.db"):
        self.db_name = db_name
        self.inicializar_db()

    def conectar(self):
        return sqlite3.connect(self.db_name)

    def inicializar_db(self):
        conn = self.conectar()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personal (
                numero_lista INTEGER PRIMARY KEY,
                nombre TEXT NOT NULL,
                estado TEXT DEFAULT 'DISPONIBLE',
                tipo_ausencia TEXT DEFAULT 'NINGUNO',
                motivo_ausencia TEXT DEFAULT '',
                fecha_inicio_ausencia TEXT DEFAULT '',
                fecha_fin_ausencia TEXT DEFAULT ''
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dias_suspendidos (
                lunes_semana TEXT,
                dia TEXT,
                PRIMARY KEY (lunes_semana, dia)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion_inicio (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                fecha_base TEXT,
                numero_inicial INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion_seguridad (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                password TEXT
            )
        ''')
        cursor.execute("INSERT OR IGNORE INTO configuracion_seguridad (id, password) VALUES (1, '2026')")

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intercambios_puntuales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                num1 INTEGER,
                num2 INTEGER
            )
        ''')

        conn.commit()
        self.verificar_y_expirar_ausencias()
        conn.close()

    def obtener_password(self):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM configuracion_seguridad WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else "2026"

    def actualizar_password(self, nueva_password):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("UPDATE configuracion_seguridad SET password = ? WHERE id = 1", (nueva_password,))
        conn.commit()
        conn.close()

    def verificar_y_expirar_ausencias(self):
        conn = self.conectar()
        cursor = conn.cursor()
        hoy_str = datetime.now().date().strftime("%Y-%m-%d")
        cursor.execute('''
            UPDATE personal 
            SET estado = 'DISPONIBLE', tipo_ausencia = 'NINGUNO', motivo_ausencia = '', fecha_inicio_ausencia = '', fecha_fin_ausencia = ''
            WHERE estado = 'AUSENTE' AND tipo_ausencia = 'TEMPORAL' AND fecha_fin_ausencia != '' AND fecha_fin_ausencia < ?
        ''', (hoy_str,))
        conn.commit()
        conn.close()

    def obtener_personal(self):
        self.verificar_y_expirar_ausencias()
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT numero_lista, nombre, estado, tipo_ausencia, motivo_ausencia, fecha_inicio_ausencia, fecha_fin_ausencia FROM personal ORDER BY numero_lista ASC")
        datos = cursor.fetchall()
        conn.close()
        return datos

    def agregar_personal(self, numero_lista, nombre):
        conn = self.conectar()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO personal (numero_lista, nombre) VALUES (?, ?)", (numero_lista, nombre))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def eliminar_personal(self, numero_lista):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM personal WHERE numero_lista = ?", (numero_lista,))
        conn.commit()
        conn.close()

    def actualizar_ausencia(self, numero_lista, tipo_ausencia, motivo, fecha_inicio, fecha_fin):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE personal 
            SET estado = 'AUSENTE', tipo_ausencia = ?, motivo_ausencia = ?, fecha_inicio_ausencia = ?, fecha_fin_ausencia = ?
            WHERE numero_lista = ?
        ''', (tipo_ausencia, motivo, fecha_inicio, fecha_fin, numero_lista))
        conn.commit()
        conn.close()

    def dar_de_alta(self, numero_lista):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE personal 
            SET estado = 'DISPONIBLE', tipo_ausencia = 'NINGUNO', motivo_ausencia = '', fecha_inicio_ausencia = '', fecha_fin_ausencia = ''
            WHERE numero_lista = ?
        ''', (numero_lista,))
        conn.commit()
        conn.close()

    def guardar_dias_suspendidos(self, lunes_semana, dias_lista):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dias_suspendidos WHERE lunes_semana = ?", (lunes_semana,))
        for dia in dias_lista:
            cursor.execute("INSERT OR IGNORE INTO dias_suspendidos (lunes_semana, dia) VALUES (?, ?)", (lunes_semana, dia))
        conn.commit()
        conn.close()

    def obtener_dias_suspendidos(self, lunes_semana):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT dia FROM dias_suspendidos WHERE lunes_semana = ?", (lunes_semana,))
        datos = [row[0] for row in cursor.fetchall()]
        conn.close()
        return datos

    def guardar_config_inicio(self, fecha_base, numero_inicial):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO configuracion_inicio (id, fecha_base, numero_inicial)
            VALUES (1, ?, ?)
        ''', (fecha_base, numero_inicial))
        conn.commit()
        conn.close()

    def obtener_config_inicio(self):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT fecha_base, numero_inicial FROM configuracion_inicio WHERE id = 1")
        row = cursor.fetchone()
        conn.close()
        return row if row else (datetime.now().date().strftime("%Y-%m-%d"), 1)

    def guardar_intercambio(self, fecha, num1, num2):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO intercambios_puntuales (fecha, num1, num2) VALUES (?, ?, ?)", (fecha, num1, num2))
        conn.commit()
        conn.close()

    def obtener_intercambios_por_fecha(self, fecha):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT num1, num2 FROM intercambios_puntuales WHERE fecha = ?", (fecha,))
        datos = cursor.fetchall()
        conn.close()
        return datos

    def obtener_todos_intercambios(self):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("SELECT id, fecha, num1, num2 FROM intercambios_puntuales ORDER BY fecha DESC")
        datos = cursor.fetchall()
        conn.close()
        return datos

    def eliminar_intercambio(self, intercambio_id):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM intercambios_puntuales WHERE id = ?", (intercambio_id,))
        conn.commit()
        conn.close()

    def borrar_todo_historial_intercambios(self):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM intercambios_puntuales")
        conn.commit()
        conn.close()

    def reiniciar_semestre(self):
        conn = self.conectar()
        cursor = conn.cursor()
        cursor.execute("UPDATE personal SET estado = 'DISPONIBLE', tipo_ausencia = 'NINGUNO', motivo_ausencia = '', fecha_inicio_ausencia = '', fecha_fin_ausencia = ''")
        cursor.execute("DELETE FROM intercambios_puntuales")
        conn.commit()
        conn.close()

db = BaseDeDatos()

# ==========================================
# GENERADOR PDF
# ==========================================
def generar_pdf_bytes(df_rol):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    logo_izq = "logo_izquierda.png"
    if os.path.exists(logo_izq):
        pdf.image(logo_izq, x=15, y=8, w=25)

    logo_der = "rodela_escuela.png"
    if os.path.exists(logo_der):
        pdf.image(logo_der, x=256, y=8, w=25)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(277, 5, txt="COLEGIO DEL AIRE", ln=True, align="C")
    pdf.set_font("Arial", "B", 10)
    pdf.cell(277, 5, txt="ESCUELA MILITAR DE ESPECIALISTAS DE FUERZA AEREA", ln=True, align="C")
    pdf.set_font("Arial", "B", 11)
    pdf.cell(277, 6, txt="ROL DE SERVICIO DE PRACTICAS - 3/ER. ANO MET. (44/A. GEN.)", ln=True, align="C")
    pdf.set_font("Arial", "", 8)
    pdf.cell(277, 4, txt=f"Emision: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
    pdf.ln(5)

    col_widths = [28, 25, 55, 102, 40, 27]
    headers = ["Fecha", "Dia", "Actividad / Servicio", "Personal Asignado", "Observaciones", "Firma"]

    pdf.set_fill_color(11, 37, 69)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 9)
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 8, h, border=1, align="C", fill=True)
    pdf.ln()

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "", 8.5)
    fill = False

    for _, row in df_rol.iterrows():
        if fill:
            pdf.set_fill_color(241, 245, 249)
        else:
            pdf.set_fill_color(255, 255, 255)

        pdf.cell(col_widths[0], 7, str(row["Fecha"]), border=1, align="C", fill=True)
        pdf.cell(col_widths[1], 7, str(row["Día"]), border=1, align="C", fill=True)
        pdf.cell(col_widths[2], 7, str(row["Actividad / Servicio"]), border=1, align="L", fill=True)
        pdf.cell(col_widths[3], 7, str(row["Personal Asignado"]), border=1, align="L", fill=True)
        pdf.cell(col_widths[4], 7, str(row["Observaciones"]), border=1, align="C", fill=True)
        pdf.cell(col_widths[5], 7, "", border=1, align="C", fill=True)
        pdf.ln()
        fill = not fill

    pdf.ln(5)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(277, 5, txt="Nota: Rol sujeto a cambios por comisiones, servicios y/o exceptuaciones.", ln=True, align="L")
    pdf.ln(3)

    y_inicio = pdf.get_y()
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(35, y_inicio)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(90, 5, "Superviso:", 0, 0, "C")
    pdf.set_xy(172, y_inicio)
    pdf.cell(90, 5, "Aprobo:", 0, 0, "C")
    
    y_grado = y_inicio + 7
    pdf.set_xy(35, y_grado)
    pdf.set_font("Arial", "", 8.5)
    pdf.cell(90, 5, "Grado: ________________________________", 0, 0, "C")
    pdf.set_xy(172, y_grado)
    pdf.cell(90, 5, "Grado: ________________________________", 0, 0, "C")
    
    y_nombre = y_grado + 16  
    pdf.set_xy(35, y_nombre)
    pdf.cell(90, 5, "Nombre: _______________________________", 0, 0, "C")
    pdf.set_xy(172, y_nombre)
    pdf.cell(90, 5, "Nombre: _______________________________", 0, 0, "C")
    
    y_mat = y_nombre + 6
    pdf.set_xy(35, y_mat)
    pdf.cell(90, 5, "Matricula: _____________________________", 0, 0, "C")
    pdf.set_xy(172, y_mat)
    pdf.cell(90, 5, "Matricula: _____________________________", 0, 0, "C")

    return bytes(pdf.output(dest='S'))

# ==========================================
# INTERFAZ Y LÓGICA DE CONTROL (STREAMLIT)
# ==========================================

# Login de Seguridad
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    st.title("🛡️ Acceso E.M.E.F.A. - 44/a. Gen.")
    st.caption("3/er. Año Meteorología | Powered by Vera Javier")
    
    pwd_input = st.text_input("Contraseña de Acceso:", type="password")
    if st.button("INGRESAR AL SISTEMA"):
        if pwd_input == db.obtener_password():
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop()

# ENCABEZADO PRINCIPAL
st.title("✈️ Rol de Servicio de Prácticas — E.M.E.F.A.")
st.caption("COLEGIO DEL AIRE • 3/ER. AÑO MET. (44/A. GEN.) • Powered by Vera Javier")

# NAVEGACIÓN EN PESTAÑAS
tab_rol, tab_personal, tab_config = st.tabs(["📅 Generar y Control de Rol", "👥 Personal e Incidencias", "⚙️ Configuración y Seguridad"])

# ----------------------------------------------------
# PESTAÑA 1: GENERAR Y CONTROL DE ROL
# ----------------------------------------------------
with tab_rol:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Semana y Días Inhábiles")
        lunes_def = datetime.now().date() - timedelta(days=datetime.now().date().weekday())
        lunes_sel = st.date_input("Lunes de la semana:", value=lunes_def)
        lunes_str = lunes_sel.strftime("%Y-%m-%d")

        suspendidos_db = db.obtener_dias_suspendidos(lunes_str)
        dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        
        dias_marcados = []
        for d in dias_nombres:
            chk = st.checkbox(f"Suspender {d}", value=(d in suspendidos_db))
            if chk:
                dias_marcados.append(d)
        
        db.guardar_dias_suspendidos(lunes_str, dias_marcados)

        st.divider()
        st.subheader("Permuto de Única Ocasión")
        f_perm = st.date_input("Fecha del permuto:", value=datetime.now().date())
        n1 = st.number_input("N° Lista Elemento A:", min_value=1, step=1)
        n2 = st.number_input("N° Lista Elemento B:", min_value=1, step=1)
        
        if st.button("🔄 Registrar Permuto"):
            db.guardar_intercambio(f_perm.strftime("%Y-%m-%d"), n1, n2)
            st.success(f"Permuto registrado para el {f_perm} entre #{n1} y #{n2}.")
            st.rerun()

        with st.expander("📋 Ver / Borrar Permutos Registrados"):
            perms = db.obtener_todos_intercambios()
            if perms:
                df_p = pd.DataFrame(perms, columns=["ID", "Fecha", "Elem. A", "Elem. B"])
                st.dataframe(df_p, hide_index=True)
                p_del = st.number_input("ID a eliminar:", min_value=1, step=1)
                if st.button("Eliminar Permuto"):
                    db.eliminar_intercambio(p_del)
                    st.success("Permuto eliminado.")
                    st.rerun()
            else:
                st.info("No hay permutos registrados.")

    with col2:
        st.subheader("Vista Previa del Rol Sincronizado")
        
        personal_completo = db.obtener_personal()
        personal_activo = [p for p in personal_completo if not (p[2] == "AUSENTE" and p[3] == "INDEFINIDO")]

        if personal_activo:
            total_activos = len(personal_activo)
            f_base_str, num_inicial = db.obtener_config_inicio()
            try:
                fecha_base_obj = datetime.strptime(f_base_str, "%Y-%m-%d").date()
            except ValueError:
                fecha_base_obj = lunes_sel

            puntero_base = 0
            for idx, p in enumerate(personal_activo):
                if p[0] == num_inicial:
                    puntero_base = idx
                    break

            slots_diferencia = 0
            if lunes_sel >= fecha_base_obj:
                curr_date = fecha_base_obj
                while curr_date < lunes_sel:
                    if curr_date.weekday() < 5:
                        d_nom = dias_nombres[curr_date.weekday()]
                        l_curr = curr_date - timedelta(days=curr_date.weekday())
                        if d_nom not in db.obtener_dias_suspendidos(l_curr.strftime("%Y-%m-%d")):
                            slots_diferencia += 2
                    curr_date += timedelta(days=1)
                puntero_inicio = (puntero_base + slots_diferencia) % total_activos
            else:
                curr_date = fecha_base_obj - timedelta(days=1)
                while curr_date >= lunes_sel:
                    if curr_date.weekday() < 5:
                        d_nom = dias_nombres[curr_date.weekday()]
                        l_curr = curr_date - timedelta(days=curr_date.weekday())
                        if d_nom not in db.obtener_dias_suspendidos(l_curr.strftime("%Y-%m-%d")):
                            slots_diferencia += 2
                    curr_date -= timedelta(days=1)
                puntero_inicio = (puntero_base - slots_diferencia) % total_activos

            dias_suspendidos = db.obtener_dias_suspendidos(lunes_str)
            dias_habiles = [d for d in dias_nombres if d not in dias_suspendidos]

            pareja_viernes_previo = []
            idx_v = puntero_inicio - 2
            intentos_v = 0
            while len(pareja_viernes_previo) < 2 and intentos_v < total_activos:
                p_v = personal_activo[idx_v % total_activos]
                pareja_viernes_previo.append((p_v[0], p_v[1]))
                idx_v += 1
                intentos_v += 1

            asignaciones_por_dia = {dia: {'auditorio': [], 'practicas': []} for dia in dias_nombres}
            if dias_habiles:
                asignaciones_por_dia[dias_habiles[0]]['auditorio'] = pareja_viernes_previo

            pool_semana = [personal_activo[(puntero_inicio + i) % total_activos] for i in range(total_activos)]
            slots_asignados = {dia: [] for dia in dias_nombres}
            alumnos_usados = set()

            def disponible(cand, f_obj):
                if cand[2] == "DISPONIBLE": return True
                if cand[2] == "AUSENTE" and cand[3] == "TEMPORAL":
                    try:
                        f_i = datetime.strptime(cand[5], "%Y-%m-%d").date()
                        f_f = datetime.strptime(cand[6], "%Y-%m-%d").date()
                        if f_i <= f_obj <= f_f: return False
                    except: pass
                return True

            for dia in dias_habiles:
                f_actual = lunes_sel + timedelta(days=dias_nombres.index(dia))
                practicas_hoy = []
                for cand in pool_semana:
                    if len(practicas_hoy) >= 2: break
                    if cand[0] in alumnos_usados: continue
                    if disponible(cand, f_actual):
                        practicas_hoy.append((cand[0], cand[1]))
                        alumnos_usados.add(cand[0])
                slots_asignados[dia] = practicas_hoy

            mapa_personal = {p[0]: p[1] for p in personal_completo}
            for dia in dias_nombres:
                f_actual = lunes_sel + timedelta(days=dias_nombres.index(dia))
                f_str = f_actual.strftime("%Y-%m-%d")
                intercambios = db.obtener_intercambios_por_fecha(f_str)
                if intercambios:
                    if dia == dias_habiles[0] and asignaciones_por_dia[dia]['auditorio']:
                        aud_l = list(asignaciones_por_dia[dia]['auditorio'])
                        asignaciones_por_dia[dia]['auditorio'] = [(n2 if p[0] == n1 else (n1 if p[0] == n2 else p[0]), mapa_personal.get(n2 if p[0] == n1 else (n1 if p[0] == n2 else p[0]), "")) for n1, n2 in intercambios for p in aud_l]
                    if slots_asignados[dia]:
                        prac_l = list(slots_asignados[dia])
                        nuevos_prac = []
                        for p in prac_l:
                            n_fin = p[0]
                            for n1, n2 in intercambios:
                                if p[0] == n1: n_fin = n2
                                elif p[0] == n2: n_fin = n1
                            nuevos_prac.append((n_fin, mapa_personal.get(n_fin, "")))
                        slots_asignados[dia] = nuevos_prac

            filas_tabla = []
            for dia in dias_nombres:
                f_actual = lunes_sel + timedelta(days=dias_nombres.index(dia))
                f_str = f_actual.strftime("%Y-%m-%d")

                if dia in dias_suspendidos:
                    filas_tabla.append({"Fecha": f_str, "Día": dia, "Actividad / Servicio": "DÍA SUSPENDIDO", "Personal Asignado": "N/A", "Observaciones": "N/A"})
                    continue

                if dia == dias_habiles[0]:
                    aud = asignaciones_por_dia[dia]['auditorio']
                else:
                    h_idx = dias_habiles.index(dia)
                    aud = slots_asignados[dias_habiles[h_idx - 1]]

                nom_aud = ", ".join([f"#{p[0]} {p[1]}" for p in aud]) if aud else "Sin asignación"
                filas_tabla.append({"Fecha": f_str, "Día": dia, "Actividad / Servicio": "07:00 HRS - AUDITORIO", "Personal Asignado": nom_aud, "Observaciones": "Auditorio"})

                prac = slots_asignados[dia]
                nom_prac = ", ".join([f"#{p[0]} {p[1]}" for p in prac]) if prac else "Insuficiente"
                filas_tabla.append({"Fecha": f_str, "Día": dia, "Actividad / Servicio": "PRÁCTICAS (TODO EL DÍA)", "Personal Asignado": nom_prac, "Observaciones": "Estación Met."})

            df_rol = pd.DataFrame(filas_tabla)
            st.dataframe(df_rol, use_container_width=True, hide_index=True)

            pdf_bytes = generar_pdf_bytes(df_rol)
            st.download_button(
                label="📥 Exportar Rol a PDF",
                data=pdf_bytes,
                file_name=f"Rol_Practicas_{lunes_str}.pdf",
                mime="application/pdf"
            )
        else:
            st.warning("No hay personal activo registrado.")

# ----------------------------------------------------
# PESTAÑA 2: PERSONAL E INCIDENCIAS
# ----------------------------------------------------
with tab_personal:
    st.subheader("Registro de Elementos")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1: num_in = st.number_input("N° Lista", min_value=1, step=1)
    with c2: nom_in = st.text_input("Nombre Completo")
    with c3:
        st.write("")
        if st.button("➕ Agregar"):
            if nom_in.strip():
                if db.agregar_personal(num_in, nom_in.strip()):
                    st.success("Elemento agregado.")
                    st.rerun()
                else: st.error("Ese número ya existe.")

    st.subheader("Calendario de Incidencias / Ausencias")
    pers = db.obtener_personal()
    if pers:
        dict_pers = {f"#{p[0]} - {p[1]}": p[0] for p in pers}
        sel_p = st.selectbox("Seleccionar Elemento:", list(dict_dict := dict_pers.keys()))
        elem_num = dict_pers[sel_p]

        c_t, c_m = st.columns(2)
        with c_t: tipo_a = st.selectbox("Tipo de Ausencia:", ["Temporal (Rango de Fechas)", "Indefinido"])
        with c_m: mot_a = st.text_input("Motivo (ej. Médico, Cuartelero, Comisión):")

        if "Temporal" in tipo_a:
            f_i = st.date_input("Desde:", value=datetime.now().date())
            f_f = st.date_input("Hasta:", value=datetime.now().date())
            str_i, str_f = f_i.strftime("%Y-%m-%d"), f_f.strftime("%Y-%m-%d")
        else:
            str_i, str_f = "Indefinido", "Indefinido"

        btn_a, btn_d = st.columns(2)
        with btn_a:
            if st.button("💾 Registrar Ausencia"):
                db.actualizar_ausencia(elem_num, "TEMPORAL" if "Temporal" in tipo_a else "INDEFINIDO", mot_a, str_i, str_f)
                st.success("Ausencia guardada.")
                st.rerun()
        with btn_d:
            if st.button("✨ Dar de Alta (Disponible)"):
                db.dar_de_alta(elem_num)
                st.success("Elemento en estado Disponible.")
                st.rerun()

    st.subheader("Lista del Personal Registrado")
    if pers:
        df_per = pd.DataFrame(pers, columns=["N° Lista", "Nombre", "Estado", "Tipo", "Motivo", "Desde", "Hasta"])
        st.dataframe(df_per, use_container_width=True, hide_index=True)

# ----------------------------------------------------
# PESTAÑA 3: CONFIGURACIÓN Y SEGURIDAD
# ----------------------------------------------------
with tab_config:
    st.subheader("Arranque Inicial del Ciclo")
    f_b_db, n_i_db = db.obtener_config_inicio()
    
    cb1, cb2 = st.columns(2)
    with cb1: f_b_in = st.date_input("Fecha Base de Inicio:", value=datetime.strptime(f_b_db, "%Y-%m-%d").date())
    with cb2: n_i_in = st.number_input("N° Lista Inicial:", value=n_i_db, min_value=1, step=1)
    
    if st.button("💾 Sincronizar Punto de Partida"):
        db.guardar_config_inicio(f_b_in.strftime("%Y-%m-%d"), n_i_in)
        st.success("Configuración de inicio sincronizada.")
        st.rerun()

    st.divider()
    st.subheader("Seguridad")
    with st.expander("🔑 Cambiar Contraseña"):
        p_act = st.text_input("Contraseña Actual:", type="password")
        p_n1 = st.text_input("Nueva Contraseña:", type="password")
        p_n2 = st.text_input("Confirmar Nueva Contraseña:", type="password")
        if st.button("Guardar Nueva Contraseña"):
            if p_act == db.obtener_password():
                if p_n1 == p_n2 and len(p_n1) >= 4:
                    db.actualizar_password(p_n1)
                    st.success("Contraseña actualizada.")
                else: st.error("La contraseña nueva no coincide o tiene menos de 4 caracteres.")
            else: st.error("Contraseña actual incorrecta.")

    with st.expander("⚠️ Reinicio de Semestre / Borrado General"):
        p_confirm = st.text_input("Ingrese contraseña para autorizar reinicio completo:", type="password")
        if st.button("🔄 Reiniciar Semestre y Borrar Permutos"):
            if p_confirm == db.obtener_password():
                db.reiniciar_semestre()
                st.success("Semestre reiniciado completamente.")
                st.rerun()
            else: st.error("Contraseña de autorización incorrecta.")