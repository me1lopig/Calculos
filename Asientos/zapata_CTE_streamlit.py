import streamlit as st
import math

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Cálculo Carga Admisible DB-SE-C", layout="wide")

st.title("Cálculo de Carga Admisible en Cimentaciones Superficiales")
st.markdown("**Según el Método Analítico del Código Técnico de la Edificación (DB-SE-C)**")

# --- BARRA LATERAL: ENTRADA DE DATOS ---
st.sidebar.header("1. Geometría de la Zapata")
B = st.sidebar.number_input("Ancho de la zapata, B (m)", min_value=0.1, value=2.0, step=0.1)
L = st.sidebar.number_input("Largo de la zapata, L (m)", min_value=0.1, value=3.0, step=0.1)
D = st.sidebar.number_input("Profundidad de apoyo, D (m)", min_value=0.0, value=1.5, step=0.1)

st.sidebar.header("2. Cargas y Excentricidades")
considerar_cargas = st.sidebar.checkbox("Considerar cargas horizontales y excentricidades", value=False, 
                                        help="Desmarca para un cálculo de capacidad portante bruta (carga centrada y puramente vertical).")

if considerar_cargas:
    V = st.sidebar.number_input("Carga Vertical, V (kN)", min_value=1.0, value=1000.0, step=10.0)
    H = st.sidebar.number_input("Carga Horizontal, H (kN)", min_value=0.0, value=50.0, step=10.0)
    e_B = st.sidebar.number_input("Excentricidad en B, e_B (m)", min_value=0.0, value=0.1, step=0.05)
    e_L = st.sidebar.number_input("Excentricidad en L, e_L (m)", min_value=0.0, value=0.1, step=0.05)
else:
    V = 1000.0  # Valor dummy para evitar divisiones por cero en el código
    H = 0.0
    e_B = 0.0
    e_L = 0.0

st.sidebar.header("3. Parámetros del Terreno")
phi = st.sidebar.number_input("Ángulo de rozamiento, φ (°)", min_value=0.0, max_value=45.0, value=30.0)
c_k = st.sidebar.number_input("Cohesión característica, ck (kPa)", min_value=0.0, value=10.0)

st.sidebar.subheader("Densidades del Suelo")
gamma_w = 9.81  # Peso específico del agua en kN/m³

st.sidebar.markdown("*Terreno POR ENCIMA de la cota de apoyo:*")
gamma_sup_ap = st.sidebar.number_input("Peso esp. aparente, γ_sup (kN/m³)", min_value=10.0, value=18.0)
gamma_sup_sat = st.sidebar.number_input("Peso esp. saturado, γ_sat_sup (kN/m³)", min_value=10.0, value=20.0)

st.sidebar.markdown("*Terreno POR DEBAJO de la cota de apoyo:*")
gamma_inf_ap = st.sidebar.number_input("Peso esp. aparente, γ_inf (kN/m³)", min_value=10.0, value=19.0)
gamma_inf_sat = st.sidebar.number_input("Peso esp. saturado, γ_sat_inf (kN/m³)", min_value=10.0, value=21.0)

st.sidebar.header("4. Nivel Freático y Talud")
D_w = st.sidebar.number_input("Profundidad del Nivel Freático desde la SUPERFICIE, Dw (m)", min_value=0.0, value=5.0, step=0.5)
beta = st.sidebar.number_input("Inclinación de talud próximo, β (°)", min_value=0.0, max_value=45.0, value=0.0)


# --- CÁLCULOS PREVIOS Y GEOMETRÍA EQUIVALENTE ---

# 1. Dimensiones equivalentes (B* y L*)
B_star = B - 2 * e_B
L_star = L - 2 * e_L

# Según normativa, B* debe ser siempre la dimensión menor
if B_star > L_star:
    B_star, L_star = L_star, B_star

if B_star <= 0 or L_star <= 0:
    st.error("❌ Las excentricidades son demasiado grandes. La zapata equivalente es nula o negativa. El vuelco es inminente.")
    st.stop()


# --- 2. CÁLCULO DE PESOS SUMERGIDOS AUTOMÁTICO ---
gamma_sup_sub = gamma_sup_sat - gamma_w
gamma_inf_sub = gamma_inf_sat - gamma_w


# --- 3. GESTIÓN DEL NIVEL FREÁTICO (Presiones Efectivas DB-SE-C) ---

# A. Presión efectiva de sobrecarga (q_0k) -> Terreno por ENCIMA de la base
if D_w >= D:
    # NF por debajo de la base. Todo el estrato superior está aparente (no sumergido).
    q_0k = gamma_sup_ap * D
else:
    # NF por encima de la base. Hay un tramo superior aparente y un tramo sumergido.
    q_0k = (gamma_sup_ap * D_w) + (gamma_sup_sub * (D - D_w))

# B. Peso específico efectivo de la cuña de rotura (gamma_k) -> Terreno por DEBAJO de la base
z = D_w - D  # Distancia desde la base hasta donde empieza el agua

if z <= 0:
    # El agua está por encima o justo en la base. Toda la cuña de rotura está sumergida.
    gamma_k = gamma_inf_sub
elif z >= B_star:
    # El agua está profunda. No afecta a la cuña de rotura.
    gamma_k = gamma_inf_ap
else:
    # Situación intermedia: el nivel freático corta la cuña de rotura. Interpolación lineal.
    gamma_k = gamma_inf_sub + (gamma_inf_ap - gamma_inf_sub) * (z / B_star)


# --- FACTORES DE CAPACIDAD DE CARGA (Nc, Nq, Ny) ---
phi_rad = math.radians(phi)
if phi == 0:
    Nq = 1.0
    Nc = 5.14
    Ny = 0.0
else:
    Nq = math.exp(math.pi * math.tan(phi_rad)) * (math.tan(math.radians(45 + phi/2)))**2
    Nc = (Nq - 1) / math.tan(phi_rad)
    Ny = 1.5 * (Nq - 1) * math.tan(phi_rad)


# --- FACTORES DE FORMA (s) ---
sc = 1 + 0.2 * (B_star / L_star)
sq = 1 + 1.5 * math.tan(phi_rad) * (B_star / L_star) if phi > 0 else 1.0
sy = 1 - 0.3 * (B_star / L_star)


# --- FACTORES DE PROFUNDIDAD (d) ---
# Normativa: Solo se aplican si D >= 2.0m. D introducido en la fórmula no será > 2B*
if D >= 2.0:
    D_calc = min(D, 2 * B_star)
    dc = 1 + 0.34 * math.atan(D_calc / B_star)
    if phi == 0:
        dq = 1.0
    else:
        dq = 1 + 2 * math.tan(phi_rad) * (1 - math.sin(phi_rad))**2 * math.atan(D_calc / B_star)
    dy = 1.0
else:
    dc = dq = dy = 1.0


# --- FACTORES DE INCLINACIÓN DE CARGA (i) ---
# Normativa: Si H < 10% de V, se consideran = 1
if H / V < 0.1 or not considerar_cargas:
    ic = iq = iy = 1.0
else:
    delta_rad = math.atan(H / V)
    iq = (1 - 0.7 * math.tan(delta_rad))**3
    iy = (1 - math.tan(delta_rad))**3
    if phi == 0:
        # Condición para suelos puramente cohesivos
        if c_k > 0:
            ic = 0.5 * (1 + math.sqrt(1 - min(1.0, H / (B_star * L_star * c_k))))
        else:
            ic = 1.0
    else:
        ic = (iq * Nq - 1) / (Nq - 1)


# --- FACTORES DE PROXIMIDAD A TALUD (t) ---
beta_rad = math.radians(beta)
if beta <= 5:
    tc = tq = ty = 1.0
else:
    tq = (1 - math.sin(2 * beta_rad))
    ty = (1 - math.sin(2 * beta_rad))
    tc = math.exp(-2 * beta_rad * math.tan(phi_rad)) if phi > 0 else 1.0


# --- CÁLCULO DE LA PRESIÓN DE HUNDIMIENTO Y ADMISIBLE ---
# Sumandos de la ecuación trinomia
term_c = c_k * Nc * dc * sc * ic * tc
term_q = q_0k * Nq * dq * sq * iq * tq
term_y = 0.5 * B_star * gamma_k * Ny * dy * sy * iy * ty

q_h = term_c + term_q + term_y
FS = 3.0  # Coeficiente parcial de seguridad gamma_R (Tabla 2.1 para situación persistente)
q_adm = q_h / FS 


# --- INTERFAZ DE USUARIO: PRESENTACIÓN DE RESULTADOS ---
st.header("Resultados del Cálculo")

col1, col2, col3 = st.columns(3)
col1.metric("Zapata Equivalente (B* x L*)", f"{B_star:.2f} x {L_star:.2f} m")
col2.metric("Peso Esp. Cuña Rotura (γ_k)", f"{gamma_k:.2f} kN/m³")
col3.metric("Sobrecarga Efectiva (q_0k)", f"{q_0k:.2f} kPa")

st.subheader("Desglose de la Fórmula Trinomia")
desglose_data = {
    "Término": ["Cohesión (c)", "Sobrecarga (q)", "Peso Específico (γ)"],
    "Factores N": [f"{Nc:.2f}", f"{Nq:.2f}", f"{Ny:.2f}"],
    "Fact. Forma (s)": [f"{sc:.2f}", f"{sq:.2f}", f"{sy:.2f}"],
    "Fact. Prof. (d)": [f"{dc:.2f}", f"{dq:.2f}", f"{dy:.2f}"],
    "Fact. Inclin. (i)": [f"{ic:.2f}", f"{iq:.2f}", f"{iy:.2f}"],
    "Fact. Talud (t)": [f"{tc:.2f}", f"{tq:.2f}", f"{ty:.2f}"],
    "Subtotal por Término (kPa)": [f"{term_c:.2f}", f"{term_q:.2f}", f"{term_y:.2f}"]
}
st.table(desglose_data)

st.success(f"### Presión de Hundimiento ($q_h$): {q_h:.2f} kPa")
st.info(f"### Carga Admisible de Cálculo ($q_{{adm}}$): {q_adm:.2f} kPa  *(FS = {FS})*")


# --- ALERTAS NORMATIVAS Y DIAGNÓSTICOS ---
st.subheader("⚠️ Avisos Normativos y Verificaciones DB-SE-C")

# Alertas sobre cargas y excentricidades
if not considerar_cargas:
    st.info("ℹ️ Cálculo realizado suponiendo **carga perfectamente centrada y vertical**. No se penalizan las dimensiones (B*=B) ni se aplican factores de inclinación.")
else:
    if H / V < 0.1:
        st.success("✅ La componente horizontal es menor al 10% de la vertical. Según la norma, se ignora el efecto de inclinación de la carga (i = 1).")
    else:
        st.warning("⚠️ La componente horizontal penaliza la capacidad portante (factores 'i' < 1). Recuerda verificar el Estado Límite de **Deslizamiento**.")

# Alertas sobre la profundidad (d)
if D < 2.0:
    st.warning("⚠️ Los factores de profundidad (d) se asumen igual a 1.0 porque la cota de apoyo D es menor a 2.0 m.")

# Alertas sobre el Nivel Freático
if D_w <= D:
    st.error(f"💧 **Nivel Freático crítico:** El agua aflora por encima de la base (Dw = {D_w} m). Se han calculado las presiones efectivas superiores ($q_{{0k}}$) restando la presión intersticial, y se ha usado el **peso específico sumergido** para la cuña de rotura inferior.")
elif D_w < (D + B_star):
    st.warning(f"💧 **Nivel Freático intermedio:** El agua (Dw = {D_w} m) no afecta a la sobrecarga, pero corta la cuña de rotura inferior. Se ha **interpolado** el peso específico de la cuña.")
else:
    st.success(f"✅ Nivel Freático profundo (Dw = {D_w} m). Queda por debajo del bulbo de tensiones críticas (D + B* = {D + B_star:.2f} m). No afecta la capacidad portante.")

# Alertas sobre el Talud
if beta > (phi / 2):
    st.error("🛑 **Talud excesivo:** La inclinación del talud supera la mitad del ángulo de rozamiento interno (β > φ/2). **El DB-SE-C exige un análisis global de estabilidad al deslizamiento profundo.**")