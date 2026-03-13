import streamlit as st
import numpy as np
import pandas as pd

# --- FUNCIONES MATEMÁTICAS (Ecuaciones 69, 70, 71) ---
def calcular_phi1(m, n):
    if m == 0:
        term1 = np.log(np.sqrt(1 + n**2) + n)
        term2 = n * np.log((np.sqrt(1 + n**2) + 1) / n)
    else:
        term1 = np.log((np.sqrt(1 + m**2 + n**2) + n) / np.sqrt(1 + m**2))
        term2 = n * np.log((np.sqrt(1 + m**2 + n**2) + 1) / np.sqrt(n**2 + m**2))
    return (1 / np.pi) * (term1 + term2)

def calcular_phi2(m, n):
    if m == 0:
        return 0.0
    else:
        return (m / np.pi) * np.arctan(n / (m * np.sqrt(1 + m**2 + n**2)))

def calcular_s_z(p, B, E, nu, z, L):
    n = L / B
    m = (2 * z) / B
    phi1 = calcular_phi1(m, n)
    phi2 = calcular_phi2(m, n)
    corchete = ((1 - nu**2) * phi1) - ((1 - nu - 2 * nu**2) * phi2)
    s_z = (p * B / E) * corchete
    return s_z

# --- INICIALIZAR MEMORIA DE STREAMLIT (SESSION STATE) ---
if 'calculo_realizado' not in st.session_state:
    st.session_state.calculo_realizado = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Cálculo de Asientos EC7", layout="wide", page_icon="🏗️")

# ==========================================
# BARRA LATERAL (PANEL IZQUIERDO)
# ==========================================
st.sidebar.title("Navegación")
modo_vista = st.sidebar.radio(
    "Selecciona la vista principal:",
    ("🧮 Panel de Cálculo", "🔍 Desglose de Cálculos", "📖 Fundamento Teórico")
)

st.sidebar.markdown("---")
st.sidebar.header("📥 Datos Geométricos")

st.sidebar.subheader("Cimentación y Cargas")
B = st.sidebar.number_input("Ancho zapata (B) [m]", min_value=0.1, value=2.0, step=0.1)
L = st.sidebar.number_input("Longitud zapata (L) [m]", min_value=0.1, value=3.0, step=0.1)
p = st.sidebar.number_input("Presión neta (p) [kPa]", min_value=1.0, value=150.0, step=10.0)

if L < B:
    st.sidebar.warning("⚠️ L debería ser $\ge$ B. Se usarán intercambiados internamente.")
    B, L = L, B
    
st.sidebar.info(f"**Esbeltez (n = L/B):** {L/B:.2f}")

# ==========================================
# ÁREA PRINCIPAL CENTRAL
# ==========================================
st.title("🏗️ Cálculo de Asientos Elásticos")
st.markdown("Basado en la **Guía de Cimentaciones con Eurocódigo 7** (Ministerio de Transportes).")
st.markdown("---")

# --- VISTA 1: PANEL DE CÁLCULO ---
if modo_vista == "🧮 Panel de Cálculo":
    
    st.header("1. Estratigrafía del Terreno")
    st.write("Introduce las capas de terreno debajo de tu cimentación. Puedes añadir, borrar o modificar filas libremente.")
    
    datos_iniciales = pd.DataFrame({
        "Descripción": ["Relleno", "Arcilla", "Grava"],
        "Espesor (m)": [1.5, 3.0, 5.0],
        "Módulo Deformación E (kPa)": [10000.0, 5000.0, 40000.0],
        "Coef. Poisson (nu)": [0.30, 0.45, 0.25]
    })
    
    # Clave en el data_editor para que no se reinicie si cambiamos de vista
    df_capas = st.data_editor(datos_iniciales, num_rows="dynamic", use_container_width=True, key="tabla_terreno")
    
    st.markdown("---")
    st.header("2. Resultados del Cálculo")
    
    if st.button("🚀 Calcular Asiento Total", type="primary"):
        asiento_total = 0.0
        z_actual = 0.0
        resultados_basicos = []
        resultados_detallados = []
        n_factor = L / B
        
        for index, row in df_capas.iterrows():
            espesor = row["Espesor (m)"]
            E = row["Módulo Deformación E (kPa)"]
            nu = row["Coef. Poisson (nu)"]
            nombre = row["Descripción"]
            
            z_techo = z_actual
            z_base = z_actual + espesor
            
            # Cálculos intermedios para guardar en la tabla detallada
            m_techo = (2 * z_techo) / B
            m_base = (2 * z_base) / B
            
            s_techo = calcular_s_z(p, B, E, nu, z_techo, L)
            s_base = calcular_s_z(p, B, E, nu, z_base, L)
            
            delta_s = s_techo - s_base
            asiento_total += delta_s
            
            # Guardamos resultados básicos para el panel principal
            resultados_basicos.append({
                "Capa": nombre,
                "Prof. Techo [m]": round(z_techo, 2),
                "Prof. Base [m]": round(z_base, 2),
                "Asiento Aportado [mm]": round(delta_s * 1000, 2)
            })
            
            # Guardamos el desglose absoluto de variables matemáticas
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
            
        # GUARDAMOS EN MEMORIA PARA LA OTRA PESTAÑA
        st.session_state.df_basico = pd.DataFrame(resultados_basicos)
        st.session_state.df_detallado = pd.DataFrame(resultados_detallados)
        st.session_state.asiento_total = asiento_total
        st.session_state.calculo_realizado = True
        
    # Mostrar resultados si ya se ha calculado alguna vez en esta sesión
    if st.session_state.calculo_realizado:
        col_res1, col_res2 = st.columns([2, 1])
        with col_res1:
            st.dataframe(st.session_state.df_basico, use_container_width=True)
            st.bar_chart(st.session_state.df_basico.set_index("Capa")["Asiento Aportado [mm]"])
        with col_res2:
            st.success("Cálculo finalizado con éxito.")
            st.metric(label="Asiento Total Estimado", value=f"{round(st.session_state.asiento_total * 1000, 2)} mm")

# --- VISTA 2: DESGLOSE DE CÁLCULOS (NUEVO) ---
elif modo_vista == "🔍 Desglose de Cálculos":
    st.header("📋 Cálculos Intermedios y Factores Geométricos")
    
    if not st.session_state.calculo_realizado:
        st.warning("⚠️ Todavía no hay datos. Ve al 'Panel de Cálculo' y pulsa el botón 'Calcular Asiento Total' para generar el desglose.")
    else:
        st.write("En esta tabla se muestran los valores de los factores $m$, $\phi_1$ y $\phi_2$ evaluados tanto en el techo como en la base de cada estrato, junto con los asientos teóricos ($s$) previos a la resta (superposición).")
        
        # Mostramos la tabla detallada guardada en memoria
        st.dataframe(st.session_state.df_detallado, use_container_width=True)
        
        st.info(f"**Nota:** El factor de esbeltez global para este cálculo ha sido **n = {L/B:.4f}**")

# --- VISTA 3: TEORÍA ---
elif modo_vista == "📖 Fundamento Teórico":
    
    st.header("Metodología de Cálculo")
    st.markdown("""
    Esta aplicación resuelve el cálculo de asientos elásticos bajo el centro de un área rectangular cargada uniformemente, siguiendo el **Apartado 5.2.8.3** de la Guía para el proyecto de cimentaciones con el Eurocódigo 7.
    """)
    
    st.subheader("Formulación General (Ecuaciones 69, 70 y 71)")
    st.markdown("El asiento a una profundidad $z$ bajo el centro de la zapata en un medio semi-infinito se define como:")
    st.latex(r"s(z) = \frac{p \cdot B}{E} \left[ (1 - \nu^2) \phi_1 - (1 - \nu - 2\nu^2) \phi_2 \right]")
    
    st.markdown("Donde los factores geométricos $\phi_1$ y $\phi_2$ dependen de la esbeltez $n = L/B$ y la profundidad relativa $m = 2z/B$:")
    st.latex(r"\phi_1 = \frac{1}{\pi} \left[ \ln \left( \frac{\sqrt{1+m^2+n^2}+n}{\sqrt{1+m^2}} \right) + n \ln \left( \frac{\sqrt{1+m^2+n^2}+1}{\sqrt{n^2+m^2}} \right) \right]")
    st.latex(r"\phi_2 = \frac{m}{\pi} \arctan \left( \frac{n}{m \sqrt{1+m^2+n^2}} \right)")
    
    st.subheader("Terrenos Estratificados (Método de Steinbrenner)")
    st.markdown("""
    Para suelos compuestos por múltiples capas, se aplica el principio de superposición. El asiento que aporta cada estrato individual $i$ se obtiene restando el asiento teórico en su base al asiento teórico en su techo, **asumiendo en ambos cálculos los parámetros $E_i$ y $\nu_i$ propios de esa capa** (Ecuación 72):
    """)
    st.latex(r"\Delta s_i = s(z_i) - s(z_{i+1})")
    
    st.markdown("El asiento elástico total en superficie será el sumatorio de las deformaciones de todos los estratos (Ecuación 73):")
    st.latex(r"s = \sum_{i=1}^{n} \Delta s_i")