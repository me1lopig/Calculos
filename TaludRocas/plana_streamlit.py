import streamlit as st
import math
import pandas as pd
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="RocPlane - Diseño de Sostenimiento", layout="wide")

st.title("🏔️ Análisis y Diseño de Taludes (Falla Plana)")
st.markdown("Basado en el manual de verificación de RocPlane.")

# --- FUNCIONES DE CÁLCULO ---

def cot(angulo_rad):
    return 1 / math.tan(angulo_rad)

def calcular_sin_grieta(H, alpha_deg, beta_deg, gamma_r, gamma_w, c, phi_deg, sc, T, theta_deg):
    alpha = math.radians(alpha_deg)
    beta = math.radians(beta_deg)
    phi = math.radians(phi_deg)
    theta = math.radians(theta_deg)
    
    A = H / math.sin(alpha)
    W = (gamma_r * H**2 / 2) * (cot(alpha) - cot(beta))
    U = (gamma_w * H**2) / (4 * math.sin(alpha))
    
    # Fuerzas base (sin perno)
    res_base = c * A + (W * (math.cos(alpha) - sc * math.sin(alpha)) - U) * math.tan(phi)
    emp_base = W * (math.sin(alpha) + sc * math.cos(alpha))
    
    # Fuerzas totales (con perno)
    resistencia = res_base + T * math.cos(theta) * math.tan(phi)
    empuje = emp_base - T * math.sin(theta)
    
    FS = resistencia / empuje if empuje > 0 else float('inf')
    return FS, W, A, U, res_base, emp_base, resistencia, empuje

def calcular_con_grieta(H, alpha_deg, beta_deg, gamma_r, gamma_w, c, phi_deg, sc, T, theta_deg, pct_agua):
    alpha = math.radians(alpha_deg)
    beta = math.radians(beta_deg)
    phi = math.radians(phi_deg)
    theta = math.radians(theta_deg)
    
    z = H * (1 - math.sqrt(cot(beta) * math.tan(alpha)))
    z_w = z * (pct_agua / 100.0)
    
    A = (H - z) / math.sin(alpha)
    W = (gamma_r * H**2 / 2) * ((1 - (z/H)**2) * cot(alpha) - cot(beta))
    
    U = (gamma_w * z_w * A) / 2
    V = (gamma_w * z_w**2) / 2
    
    # Fuerzas base (sin perno)
    res_base = c * A + (W * (math.cos(alpha) - sc * math.sin(alpha)) - U - V * math.sin(alpha)) * math.tan(phi)
    emp_base = W * (math.sin(alpha) + sc * math.cos(alpha)) + V * math.cos(alpha)
    
    # Fuerzas totales (con perno)
    resistencia = res_base + T * math.cos(theta) * math.tan(phi)
    empuje = emp_base - T * math.sin(theta)
    
    FS = resistencia / empuje if empuje > 0 else float('inf')
    return FS, W, A, U, V, z, res_base, emp_base, resistencia, empuje

def calcular_perno_requerido(FS_obj, theta_deg, phi_deg, res_base, emp_base):
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    
    # Despeje de T de la fórmula del FS
    numerador = FS_obj * emp_base - res_base
    denominador = FS_obj * math.sin(theta) + math.cos(theta) * math.tan(phi)
    
    if denominador == 0:
        return float('inf')
    
    T_req = numerador / denominador
    return max(0.0, T_req) # Si es negativo, el talud ya cumple el FS sin perno

# --- INTERFAZ DE USUARIO (SIDEBAR) ---

st.sidebar.header("⚙️ Parámetros de Entrada")

st.sidebar.subheader("1. Geometría del Talud")
H = st.sidebar.number_input("Altura del Talud (H) [m]", value=60.0, step=1.0)
beta_deg = st.sidebar.slider("Ángulo del Talud (β) [°]", min_value=10.0, max_value=89.0, value=50.0)
alpha_deg = st.sidebar.slider("Ángulo de Falla (α) [°]", min_value=10.0, max_value=89.0, value=35.0)

st.sidebar.subheader("2. Propiedades del Material")
gamma_r = st.sidebar.number_input("Peso Específico Roca (γr) [MN/m³]", value=0.027, format="%.4f")
c = st.sidebar.number_input("Cohesión (c) [MPa]", value=0.10, format="%.3f")
phi_deg = st.sidebar.slider("Ángulo de Fricción (φ) [°]", min_value=0.0, max_value=60.0, value=35.0)

st.sidebar.subheader("3. Agua y Sismo")
gamma_w = st.sidebar.number_input("Peso Específico Agua (γw) [MN/m³]", value=0.010, format="%.4f")
sc = st.sidebar.number_input("Coeficiente Sísmico (sc) [g]", value=0.08, step=0.01)

st.sidebar.subheader("4. Diseño de Sostenimiento")
modo_diseno = st.sidebar.radio("Modo de Perno:", ["Ingresar Fuerza Manual", "Calcular para FS Objetivo"])
theta_deg = st.sidebar.slider("Inclinación del Perno (θ) [°]", min_value=0.0, max_value=90.0, value=0.0)

if modo_diseno == "Ingresar Fuerza Manual":
    T = st.sidebar.number_input("Fuerza del Perno (T) [MN]", value=0.0, step=0.1)
    FS_obj = None
else:
    FS_obj = st.sidebar.number_input("Factor de Seguridad Objetivo", value=1.50, step=0.1)
    T = 0.0 # Se calculará dinámicamente

# --- PANEL PRINCIPAL ---

st.subheader("Seleccione el Escenario")
escenario = st.radio("Modelo analítico:", ["Sin Grieta de Tracción", "Con Grieta de Tracción"], horizontal=True)
pct_agua = 0.0
if escenario == "Con Grieta de Tracción":
    pct_agua = st.slider("Agua en la grieta de tracción (%)", min_value=0.0, max_value=100.0, value=90.0)

if alpha_deg >= beta_deg:
    st.error("Error Geométrico: El ángulo del plano de falla (α) debe ser menor que el ángulo del talud (β).")
    st.stop()

# 1er Paso: Calcular fuerzas base (sin pernos)
if escenario == "Sin Grieta de Tracción":
    _, W, A, U, res_base, emp_base, _, _ = calcular_sin_grieta(H, alpha_deg, beta_deg, gamma_r, gamma_w, c, phi_deg, sc, 0, theta_deg)
else:
    _, W, A, U, V, z, res_base, emp_base, _, _ = calcular_con_grieta(H, alpha_deg, beta_deg, gamma_r, gamma_w, c, phi_deg, sc, 0, theta_deg, pct_agua)

# 2do Paso: Calcular Perno si estamos en modo diseño
if modo_diseno == "Calcular para FS Objetivo":
    T = calcular_perno_requerido(FS_obj, theta_deg, phi_deg, res_base, emp_base)
    if T == 0:
        st.success(f"¡El talud ya cumple o supera el FS de {FS_obj} de forma natural! No se requieren pernos.")
    else:
        st.info(f"💡 Para alcanzar un FS de **{FS_obj}**, necesitas instalar un perno con una fuerza de **{T:.4f} MN/m**.")

# 3er Paso: Calcular el FS final con la fuerza del perno (T manual o T calculada)
if escenario == "Sin Grieta de Tracción":
    FS_final, _, _, _, _, _, res_tot, emp_tot = calcular_sin_grieta(H, alpha_deg, beta_deg, gamma_r, gamma_w, c, phi_deg, sc, T, theta_deg)
else:
    FS_final, _, _, _, _, _, _, _, res_tot, emp_tot = calcular_con_grieta(H, alpha_deg, beta_deg, gamma_r, gamma_w, c, phi_deg, sc, T, theta_deg, pct_agua)


col1, col2 = st.columns([1, 1])

with col1:
    st.metric(label="Factor de Seguridad (FS)", value=f"{FS_final:.4f}", 
              delta="Aceptable" if FS_final >= 1.0 else "Falla Inminente", 
              delta_color="normal" if FS_final>=1.0 else "inverse")

with col2:
    with st.expander("Ver Detalles de Fuerzas", expanded=True):
        st.markdown(f"""
        * **Peso de la Cuña (W):** {W:.4f} MN
        * **Área de Falla (A):** {A:.4f} m²
        * **Fuerza Resistente Total:** {res_tot:.4f} MN
        * **Fuerza Desestabilizadora Total:** {emp_tot:.4f} MN
        * **Fuerza del Perno Aplicada (T):** {T:.4f} MN
        """)