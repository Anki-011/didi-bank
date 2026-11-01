import sqlite3
import streamlit as st
from datetime import datetime

# Configuración de página para vista celular
st.set_page_config(page_title="Didi bank", page_icon="💳", layout="centered")

# ================= SEGURIDAD Y LOGIN =================
# Cambia esta contraseña por la clave secreta que tú quieras usar
CONTRASEÑA_CORRECTA = "6616"

def verificar_password():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.title("🔒 Acceso Restringido")
        clave = st.text_input("Ingresa la contraseña de Didi bank:", type="password")
        if st.button("Ingresar", type="primary"):
            if clave == CONTRASEÑA_CORRECTA:
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        return False
    return True

# Si no ha puesto la contraseña correcta, detiene la ejecución aquí
if not verificar_password():
    st.stop()

# ================= BASE DE DATOS =================
RUTA_DB = "mis_finanzas.db"

def consultar(sql, params=()):
    con = sqlite3.connect(RUTA_DB)
    try:
        filas = con.execute(sql, params).fetchall()
        con.commit()
        return filas
    finally:
        con.close()

def saldos():
    sql = """SELECT cuenta, SUM(CASE WHEN tipo = 'Ingreso' THEN monto
                                    WHEN tipo IN ('Egreso', 'Gasto') THEN -monto
                                    ELSE monto END)
             FROM Finanzas GROUP BY cuenta"""
    res = {"Banco": 0.0, "Efectivo": 0.0}
    for cuenta, total in consultar(sql):
        res[cuenta or "Banco"] += total or 0.0
    return res

def totales():
    ing = consultar("SELECT SUM(monto) FROM Finanzas WHERE tipo = 'Ingreso'")[0][0] or 0.0
    egr = consultar("SELECT SUM(monto) FROM Finanzas WHERE tipo IN ('Egreso', 'Gasto')")[0][0] or 0.0
    return ing, egr

# ================= INTERFAZ STREAMLIT =================
st.title("💳 Didi bank")

# Botón opcional para cerrar sesión
if st.sidebar.button("Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.rerun()

# Pestañas para navegación en celular
tab_menu, tab_agregar, tab_planes = st.tabs(["Menú Principal", "Agregar Movimiento", "Planes y Compras"])

# ---------- PESTAÑA 1: MENÚ PRINCIPAL ----------
with tab_menu:
    s = saldos()
    ing, egr = totales()
    total_gral = sum(s.values())

    col1, col2, col3 = st.columns(3)
    col1.metric("DINERO EN BANCO", f"${s['Banco']:,.2f}")
    col2.metric("DINERO EN EFECTIVO", f"${s['Efectivo']:,.2f}")
    col3.metric("DINERO EN TOTAL", f"${total_gral:,.2f}")

    st.divider()

    col_i, col_e = st.columns(2)
    col_i.metric("Ingresos", f"+${ing:,.2f}")
    col_e.metric("Egresos", f"-${egr:,.2f}")

    st.subheader("Últimos movimientos")
    filas = consultar("SELECT fecha, tipo, descripcion, monto, cuenta FROM Finanzas ORDER BY id DESC LIMIT 15")
    for fecha, tipo, desc, monto, cuenta in filas:
        monto = monto or 0
        signo = "+" if tipo == "Ingreso" else "-"
        st.write(f"**{fecha}** | {tipo} ({cuenta}) | {desc} | **{signo}${abs(monto):,.2f}**")

# ---------- PESTAÑA 2: AGREGAR MOVIMIENTO ----------
with tab_agregar:
    st.subheader("Registrar Movimiento")
    tipo = st.radio("Tipo de movimiento:", ["Ingreso", "Egreso"], horizontal=True)
    cuenta = st.radio("Cuenta:", ["Banco", "Efectivo"], horizontal=True)
    monto = st.number_input("Monto ($):", min_value=0.01, step=10.0)
    desc = st.text_input("Descripción:")
    cat = st.text_input("Categoría:", value="General")

    if st.button("Guardar Registro", type="primary"):
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        consultar(
            "INSERT INTO Finanzas (fecha, tipo, monto, descripcion, categoria, cuenta) VALUES (?, ?, ?, ?, ?, ?)",
            (fecha_hoy, tipo, monto, desc or "Sin descripción", cat, cuenta)
        )
        st.success("¡Movimiento registrado con éxito!")
        st.rerun()

    st.divider()
    st.subheader("Traspasos")
    monto_traspaso = st.number_input("Monto a traspasar ($):", min_value=0.01, step=10.0, key="traspaso")
    col_t1, col_t2 = st.columns(2)
    
    if col_t1.button("Banco ➔ Efectivo"):
        if saldos()["Banco"] >= monto_traspaso:
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            desc_t = "Traspaso Banco ➔ Efectivo"
            consultar("INSERT INTO Finanzas (fecha, tipo, monto, descripcion, categoria, cuenta) VALUES (?, 'Traspaso', ?, ?, 'Traspaso', 'Banco')", (fecha_hoy, -monto_traspaso, desc_t))
            consultar("INSERT INTO Finanzas (fecha, tipo, monto, descripcion, categoria, cuenta) VALUES (?, 'Traspaso', ?, ?, 'Traspaso', 'Efectivo')", (fecha_hoy, monto_traspaso, desc_t))
            st.success("Traspaso realizado")
            st.rerun()
        else:
            st.error("Saldo insuficiente en Banco")

    if col_t2.button("Efectivo ➔ Banco"):
        if saldos()["Efectivo"] >= monto_traspaso:
            fecha_hoy = datetime.now().strftime("%Y-%m-%d")
            desc_t = "Traspaso Efectivo ➔ Banco"
            consultar("INSERT INTO Finanzas (fecha, tipo, monto, descripcion, categoria, cuenta) VALUES (?, 'Traspaso', ?, ?, 'Traspaso', 'Efectivo')", (fecha_hoy, -monto_traspaso, desc_t))
            consultar("INSERT INTO Finanzas (fecha, tipo, monto, descripcion, categoria, cuenta) VALUES (?, 'Traspaso', ?, ?, 'Traspaso', 'Banco')", (fecha_hoy, monto_traspaso, desc_t))
            st.success("Traspaso realizado")
            st.rerun()
        else:
            st.error("Saldo insuficiente en Efectivo")

# ---------- PESTAÑA 3: PLANES Y COMPRAS ----------
with tab_planes:
    st.subheader("Planes y Compras")
    nombre_p = st.text_input("Nombre del plan:")
    costo_p = st.number_input("Costo estimado ($):", min_value=1.0, step=50.0)

    if st.button("Agregar Plan"):
        if nombre_p:
            consultar("INSERT INTO Planes (nombre, costo, estado) VALUES (?, ?, 'Pendiente')", (nombre_p, costo_p))
            st.success("Plan agregado")
            st.rerun()

    st.divider()
    planes = consultar("SELECT id, nombre, costo, estado FROM Planes ORDER BY id DESC")
    for id_p, nom, cos, est in planes:
        col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
        col_p1.write(f"**{nom}** - ${cos:,.2f} MXN [{est}]")
        if col_p2.button("Cambiar", key=f"est_{id_p}"):
            nuevo = "Pendiente" if est == "Comprado" else "Comprado"
            consultar("UPDATE Planes SET estado = ? WHERE id = ?", (nuevo, id_p))
            st.rerun()
        if col_p3.button("✕", key=f"del_{id_p}"):
            consultar("DELETE FROM Planes WHERE id = ?", (id_p))
            st.rerun()
