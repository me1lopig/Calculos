import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ==========================================
# FUNCIONES MATEMÁTICAS: ASIENTOS (Ec. 69, 70, 71)
# ==========================================
def calcular_phi1(m, n):
    if m == 0:
        term1 = np.log(np.sqrt(1 + n**2) + n)
        term2 = n * np.log((np.sqrt(1 + n**2) + 1) / n)
    else:
        term1 = np.log((np.sqrt(1 + m**2 + n**2) + n) / np.sqrt(1 + m**2))
        term2 = n * np.log((np.sqrt(1 + m**2 + n**2) + 1) / np.sqrt(n**2 + m**2))
    return (1 / np.pi) * (term1 + term2)

def calcular_phi2(m, n):
    if m == 0: return 0.0
    return (m / np.pi) * np.arctan(n / (m * np.sqrt(1 + m**2 + n**2)))

def calcular_s_z(p, B, E, nu, z, L):
    n = L / B
    m = (2 * z) / B
    phi1 = calcular_phi1(m, n)
    phi2 = calcular_phi2(m, n)
    corchete = ((1 - nu**2) * phi1) - ((1 - nu - 2 * nu**2) * phi2)
    return (p * B / E) * corchete

# ==========================================
# FUNCIONES MATEMÁTICAS: TENSIONES HOLL
# ==========================================
def tensiones_holl_centro(p, B, L, z):
    if z <= 0.01: 
        return p, p/2, p/2 
        
    B_cuad = B / 2.0
    L_cuad = L / 2.0
    
    R1 = np.sqrt(L_cuad**2 + z**2)
    R2 = np.sqrt(B_cuad**2 + z**2)
    R3 = np.sqrt(L_cuad**2 + B_cuad**2 + z**2)
    
    term_arctan = np.arctan((B_cuad * L_cuad) / (z * R3))
    
    sigma_z_esq = (p / (2 * np.pi)) * (term_arctan + B_cuad * L_cuad * (1/R1**2 + 1/R2**2) * (z / R3))
    sigma_x_esq = (p / (2 * np.pi)) * (term_arctan - (B_cuad * L_cuad * z) / (R1**2 * R3))
    sigma_y_esq = (p / (2 * np.pi)) * (term_arctan - (B_cuad * L_cuad * z) / (R2**2 * R3))
    
    return 4 * sigma_z_esq, 4 * sigma_x_esq, 4 * sigma_y_esq

# ==========================================
# GESTIÓN DE ESTADO (SESSION STATE)
# ==========================================
def reset_calculo():
    st.session_state.calculo_realizado = False

if 'calculo_realizado' not in st.session_state:
    st.session_state.calculo_realizado = False

if 'df_terreno' not in st.session_state:
    st.session_state.df_terreno = pd.DataFrame({
        "Descripción": ["Relleno", "Arcilla", "Grava"],
        "Espesor (m)": [1.5, 3.0, 5.0],
        "Módulo Deformación E (kPa)": [10000.0, 5000.0, 40000.0],
        "Coef. Poisson (nu)": [0.30, 0.45, 0.25]
    })

# ==========================================
# CONFIGURACIÓN DE PÁGINA Y BARRA LATERAL
# ==========================================
st.set_page_config(page_title="Cálculo de Cimentaciones EC7", layout="wide", page_icon="🏗️")

st.sidebar.title("Navegación")
modo_vista = st.sidebar.radio(
    "Selecciona la vista principal:",
    ("🧮 Panel de Cálculo", "🔍 Desglose de Asientos", "📉 Incremento de Tensiones", "📖 Fundamento Teórico")
)

st.sidebar.markdown("---")
st.sidebar.header("📥 Datos Geométricos")

B = st.sidebar.number_input("Ancho zapata (B) [m]", min_value=0.1, value=2.0, step=0.1, on_change=reset_calculo)
L = st.sidebar.number_input("Longitud zapata (L) [m]", min_value=0.1, value=3.0, step=0.1, on_change=reset_calculo)
p = st.sidebar.number_input("Presión neta (p) [kPa]", min_value=1.0, value=150.0, step=10.0, on_change=reset_calculo)

if L < B:
    st.sidebar.warning("⚠️ L debería ser $\ge$ B. Se intercambian internamente.")
    B, L = L, B
    
st.sidebar.info(f"**Esbeltez (n = L/B):** {L/B:.2f}")

st.sidebar.markdown("---")

# --- NUEVA UBICACIÓN DEL BOTÓN DE CÁLCULO ---
if st.sidebar.button("🚀 Calcular Asiento Total", type="primary", use_container_width=True):
    asiento_total = 0.0
    z_actual = 0.0
    resultados_basicos = []
    resultados_detallados = []
    n_factor = L / B
    
    for index, row in st.session_state.df_terreno.iterrows():
        espesor = float(row["Espesor (m)"])
        E = float(row["Módulo Deformación E (kPa)"])
        nu = float(row["Coef. Poisson (nu)"])
        nombre = str(row["Descripción"])
        
        z_techo = z_actual
        z_base = z_actual + espesor
        
        m_techo = (2 * z_techo) / B
        m_base = (2 * z_base) / B
        
        s_techo = calcular_s_z(p, B, E, nu, z_techo, L)
        s_base = calcular_s_z(p, B, E, nu, z_base, L)
        
        delta_s = s_techo - s_base
        asiento_total += delta_s
        
        resultados_basicos.append({
            "Capa": nombre,
            "Prof. Techo [m]": round(z_techo, 2),
            "Prof. Base [m]": round(z_base, 2),
            "Asiento Aportado [mm]": round(delta_s * 1000, 2)
        })
        
        resultados_detallados.append({
            "Capa": nombre,
            "z_techo [m]": round(z_techo, 2),
            "m_techo": round(m_techo, 4),
            "φ1_techo": round(calcular_phi1(m_techo, n_factor), 4),
            "φ2_techo": round(calcular_phi2(m_techo, n_factor), 4),
            "s_techo_teórico [mm]": round(s_techo * 1000, 3),
            "z_base [m]": round(z_base, 2),
            "m_base": round(m_base, 4),
            "φ1_base": round(calcular_phi1(m_base, n_factor), 4),
            "φ2_base": round(calcular_phi2(m_base, n_factor), 4),
            "s_base_teórico [mm]": round(s_base * 1000, 3),
            "Δs Real [mm]": round(delta_s * 1000, 2)
        })
        
        z_actual = z_base
        
    st.session_state.df_basico = pd.DataFrame(resultados_basicos)
    st.session_state.df_detallado = pd.DataFrame(resultados_detallados)
    st.session_state.asiento_total = asiento_total
    st.session_state.calculo_realizado = True

# ==========================================
# ÁREA PRINCIPAL CENTRAL
# ==========================================
st.title("🏗️ Proyecto de Cimentaciones Superficiales")
st.markdown("Basado en la **Guía de Cimentaciones con Eurocódigo 7** (Ministerio de Transportes).")
st.markdown("---")

# --- VISTA 1: PANEL DE CÁLCULO ---
if modo_vista == "🧮 Panel de Cálculo":
    
    st.header("1. Estratigrafía del Terreno")
    st.write("Introduce las capas de terreno debajo de tu cimentación. Puedes añadir o borrar filas.")
    
    df_actualizado = st.data_editor(
        st.session_state.df_terreno, 
        num_rows="dynamic", 
        use_container_width=True
    )
    
    if not df_actualizado.equals(st.session_state.df_terreno):
        st.session_state.df_terreno = df_actualizado
        st.session_state.calculo_realizado = False
        st.rerun() 
    
    st.markdown("---")
    st.header("2. Resultados del Cálculo")
        
    if st.session_state.calculo_realizado:
        col_res1, col_res2 = st.columns([2, 1])
        with col_res1:
            st.dataframe(st.session_state.df_basico, use_container_width=True)
            st.bar_chart(st.session_state.df_basico.set_index("Capa")["Asiento Aportado [mm]"])
        with col_res2:
            st.success("Cálculo actualizado.")
            st.metric(label="Asiento Total Estimado", value=f"{round(st.session_state.asiento_total * 1000, 2)} mm")
    else:
        st.info("👈 Modifica los datos y haz clic en **Calcular Asiento Total** en el panel izquierdo.")

# --- VISTA 2: DESGLOSE DE ASIENTOS ---
elif modo_vista == "🔍 Desglose de Asientos":
    st.header("📋 Cálculos Intermedios y Factores Geométricos")
    
    if not st.session_state.calculo_realizado:
        st.warning("⚠️ Los datos han cambiado o no se ha calculado aún. Pulsa el botón de calcular en el panel izquierdo.")
    else:
        st.write("En esta tabla se muestran los valores evaluados tanto en el techo como en la base de cada estrato.")
        st.dataframe(st.session_state.df_detallado, use_container_width=True)
        st.info(f"**Nota:** El factor de esbeltez global para este cálculo ha sido **n = {L/B:.4f}**")

# --- VISTA 3: INCREMENTO DE TENSIONES ---
elif modo_vista == "📉 Incremento de Tensiones":
    st.header("Disipación de Tensiones en Profundidad (Solución de Holl)")
    st.write("Evolución de las tensiones bajo el **centro** de la zapata aplicando el principio de superposición sobre las fórmulas de Holl.")
    
    # --- CÁLCULO DEL ESPESOR TOTAL DEL TERRENO ---
    espesor_total = float(pd.to_numeric(st.session_state.df_terreno["Espesor (m)"]).sum())
    espesor_total = max(1.0, espesor_total) # Por seguridad, evitamos que el máximo sea 0
    
    col1, col2 = st.columns([1, 3])
    with col1:
        # Limitamos el slider al espesor_total del terreno
        val_inicial = min(15.0, espesor_total) # Para que por defecto no se pase de la raya
        z_max = st.slider("Profundidad máxima a graficar [m]:", min_value=1.0, max_value=espesor_total, value=val_inicial, step=0.5)
        
        st.markdown(f"**$p$ (Carga):** {p} kPa  \n**$B$ (Ancho):** {B} m  \n**$L$ (Largo):** {L} m")
        st.info(f"**Profundidad del estudio:** {espesor_total:.1f} m\n(Suma de las capas de la tabla).")
        st.success(f"**Límite 10%:**\nCriterio normativo de profundidad de influencia ($0.1p = {p*0.1:.1f}$ kPa).")

    with col2:
        z_vals = np.linspace(0.1, z_max, 100)
        sigma_z_vals, sigma_x_vals, sigma_y_vals = [], [], []
        
        for z in z_vals:
            sz, sx, sy = tensiones_holl_centro(p, B, L, z)
            sigma_z_vals.append(sz)
            sigma_x_vals.append(sx)
            sigma_y_vals.append(sy)
            
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(sigma_z_vals, z_vals, label=r'Vertical ($\sigma_z$)', color='red', linewidth=2)
        ax.plot(sigma_x_vals, z_vals, label=r'Horiz. Transversal ($\sigma_x$)', color='blue', linestyle='--')
        ax.plot(sigma_y_vals, z_vals, label=r'Horiz. Longitudinal ($\sigma_y$)', color='green', linestyle='-.')
        
        ax.axvline(x=p*0.1, color='gray', linestyle=':', label='Límite 10% ($0.1p$)')
        ax.set_ylim(z_max, 0)
        ax.set_xlim(0, p * 1.05)
        ax.set_xlabel("Incremento de Tensión (kPa)", fontsize=11)
        ax.set_ylabel("Profundidad z (m)", fontsize=11)
        ax.set_title("Bulbo de presiones bajo el centro de la cimentación", fontsize=13)
        ax.grid(True, linestyle=':', alpha=0.6)
        ax.legend()
        st.pyplot(fig)

# --- VISTA 4: TEORÍA ---
elif modo_vista == "📖 Fundamento Teórico":
    st.header("Metodología de Cálculo")
    
    st.subheader("1. Cálculo de Asientos (Steinbrenner)")
    st.markdown("Basado en el Apartado 5.2.8.3 de la Guía EC7. El asiento a profundidad $z$ en medio semi-infinito es:")
    st.latex(r"s(z) = \frac{p \cdot B}{E} \left[ (1 - \nu^2) \phi_1 - (1 - \nu - 2\nu^2) \phi_2 \right]")
    st.markdown("Donde $\phi_1$ y $\phi_2$ dependen de $n = L/B$ y $m = 2z/B$:")
    st.latex(r"\phi_1 = \frac{1}{\pi} \left[ \ln \left( \frac{\sqrt{1+m^2+n^2}+n}{\sqrt{1+m^2}} \right) + n \ln \left( \frac{\sqrt{1+m^2+n^2}+1}{\sqrt{n^2+m^2}} \right) \right]")
    st.latex(r"\phi_2 = \frac{m}{\pi} \arctan \left( \frac{n}{m \sqrt{1+m^2+n^2}} \right)")
    st.markdown("Para estratos múltiples, se aplica superposición (asiento techo - asiento base con mismos parámetros):")
    st.latex(r"\Delta s_i = s(z_i) - s(z_{i+1}) \quad \rightarrow \quad s_{total} = \sum \Delta s_i")
    
    st.subheader("2. Distribución de Tensiones (Holl)")
    st.markdown("Incrementos de tensión bajo la **esquina** de un rectángulo $B \times L$ a profundidad $z$. En esta app, se evalúa para $B/2 \times L/2$ y se multiplica por 4 (centro de la zapata).")
    st.latex(r"\sigma_z = \frac{p}{2\pi} \left[ \arctan\left(\frac{BL}{zR_3}\right) + \frac{BLz}{R_3} \left(\frac{1}{R_1^2} + \frac{1}{R_2^2}\right) \right]")
    st.latex(r"\sigma_x = \frac{p}{2\pi} \left[ \arctan\left(\frac{BL}{zR_3}\right) - \frac{BLz}{R_1^2 R_3} \right]")
    st.latex(r"\sigma_y = \frac{p}{2\pi} \left[ \arctan\left(\frac{BL}{zR_3}\right) - \frac{BLz}{R_2^2 R_3} \right]")
    st.markdown("Siendo $R_1 = \sqrt{L^2+z^2}$, $R_2 = \sqrt{B^2+z^2}$ y $R_3 = \sqrt{L^2+B^2+z^2}$.")