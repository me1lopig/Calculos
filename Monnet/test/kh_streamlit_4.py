import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Geotecnia Pro: Chadeisson Empírico", layout="wide")

# --- CONSTANTES DE CONVERSIÓN ---
KPA_TO_TM2 = 1.0 / 9.80665
TM3_TO_KNM3 = 9.80665

# =====================================================================
# DATOS EMPÍRICOS EXACTOS (Extraídos por el usuario)
# =====================================================================
datos_usuario = [
    {'Kh': 700,   'c1': 0,    'phi1': 7.0,  'c2': 1.64, 'phi2': 0.0},
    {'Kh': 800,   'c1': 0,    'phi1': 10.0, 'c2': 2.47, 'phi2': 0.0},
    {'Kh': 900,   'c1': 0,    'phi1': 12.0, 'c2': 3.19, 'phi2': 0.0},
    {'Kh': 1000,  'c1': 0,    'phi1': 14.0, 'c2': 4.0,  'phi2': 0.0},
    {'Kh': 1100,  'c1': 0,    'phi1': 16.0, 'c2': 4.84, 'phi2': 0.0},
    {'Kh': 1200,  'c1': 0,    'phi1': 18.0, 'c2': 5.69, 'phi2': 0.0},
    {'Kh': 1300,  'c1': 0,    'phi1': 19.2, 'c2': 6.46, 'phi2': 0.0},
    {'Kh': 1400,  'c1': 0,    'phi1': 20.0, 'c2': 7.29, 'phi2': 0.0},
    {'Kh': 1500,  'c1': 0,    'phi1': 21.5, 'c2': 8.0,  'phi2': 0.0},
    {'Kh': 2000,  'c1': 0,    'phi1': 26.0, 'c2': 9.0,  'phi2': 7.0},
    {'Kh': 3000,  'c1': 0,    'phi1': 31.5, 'c2': 9.0,  'phi2': 18.0},
    {'Kh': 4000,  'c1': 0,    'phi1': 35.0, 'c2': 9.0,  'phi2': 24.74},
    {'Kh': 5000,  'c1': 0,    'phi1': 38.0, 'c2': 9.0,  'phi2': 28.4},
    {'Kh': 6000,  'c1': 0,    'phi1': 40.0, 'c2': 9.0,  'phi2': 31.5},
    {'Kh': 7000,  'c1': 0,    'phi1': 41.5, 'c2': 9.0,  'phi2': 34.0},
    {'Kh': 8000,  'c1': 0,    'phi1': 43.0, 'c2': 9.0,  'phi2': 36.0},
    {'Kh': 9000,  'c1': 0,    'phi1': 44.0, 'c2': 9.0,  'phi2': 38.0},
    {'Kh': 10000, 'c1': 0,    'phi1': 45.0, 'c2': 9.0,  'phi2': 39.2},
    {'Kh': 12000, 'c1': 3.17, 'phi1': 45.0, 'c2': 9.0,  'phi2': 41.5},
    {'Kh': 14000, 'c1': 6.0,  'phi1': 45.0, 'c2': 9.0,  'phi2': 43.2},
    {'Kh': 16000, 'c1': 8.38, 'phi1': 46.0, 'c2': 9.0,  'phi2': 45.0}
]

# Generador automático de ecuaciones (m: pendiente, n: ordenada origen)
rectas_chadeisson_empiricas = {}
for fila in datos_usuario:
    kh = fila['Kh']
    m = (fila['phi2'] - fila['phi1']) / (fila['c2'] - fila['c1'])
    # Ahora n se calcula correctamente aunque c1 no sea cero
    n = fila['phi1'] - (m * fila['c1'])
    rectas_chadeisson_empiricas[kh] = (m, n)


# =====================================================================
# MÉTODO 1: POLINOMIO DE GRANADOS (Auditor)
# =====================================================================
def calc_chadeisson_granados_tm3(phi_d, c_tm2):
    phi_rad = math.radians(phi_d)
    a = {
        1: 0.2780567713112, 2: 5.57961020316, 3: -35.301673725713,
        4: 147.66061817668381, 5: -245.6043814457953, 6: 164.0109185222536,
        7: 0.1188816874005, 8: 0.3480332606123, 9: -1.0388796245679,
        10: 3.6912996582687, 11: -5.0917695015669, 12: 3.657829914242,
        13: 0.0000376350382, 14: -0.0084577071902, 15: 0.1117470768513,
        16: -0.4859679131769, 17: 0.8440710781142, 18: -0.5066994114313
    }
    kh_sum = 0
    for k in range(3):
        for j in range(6):
            alpha = 1 + j + 6 * k
            kh_sum += a[alpha] * (phi_rad**j) * (c_tm2**k)
    return max(kh_sum * 1000.0, 0.0)

def calc_chadeisson_granados(phi_d, c_kpa):
    return calc_chadeisson_granados_tm3(phi_d, c_kpa * KPA_TO_TM2) * TM3_TO_KNM3

# =====================================================================
# MÉTODO 2: GEOMÉTRICO EMPÍRICO (Interpolación de Rectas Reales)
# =====================================================================
def calc_chadeisson_geometrico_tm3(phi_d, c_tm2):
    alturas_phi = []
    for kh, (m, n) in rectas_chadeisson_empiricas.items():
        phi_recta = m * c_tm2 + n
        alturas_phi.append((phi_recta, kh))
        
    alturas_phi.sort()
    
    if phi_d < alturas_phi[0][0]: return 0.0
    if phi_d >= alturas_phi[-1][0]: return alturas_phi[-1][1]
        
    for i in range(len(alturas_phi) - 1):
        phi_inf, kh_inf = alturas_phi[i]
        phi_sup, kh_sup = alturas_phi[i+1]
        
        if phi_inf <= phi_d <= phi_sup:
            if phi_sup == phi_inf: return kh_inf
            peso = (phi_d - phi_inf) / (phi_sup - phi_inf)
            return kh_inf + peso * (kh_sup - kh_inf)
            
    return 0.0

def calc_chadeisson_geometrico(phi_d, c_kpa):
    return calc_chadeisson_geometrico_tm3(phi_d, c_kpa * KPA_TO_TM2) * TM3_TO_KNM3


# =====================================================================
# INTERFAZ STREAMLIT
# =====================================================================
st.title("🧮 Calculadora de Balasto (Motor Empírico)")

tab_calc, tab_abacos = st.tabs(["📝 Tabla de Cálculo y Auditoría", "📊 Proyección Visual (φ máx = 45°)"])

with tab_calc:
    st.markdown("Calculadora basada en tu digitalización empírica de las rectas, enfrentada al modelo de regresión de Granados.")
    
    df_init = pd.DataFrame([
        {"Estrato": "Arcilla blanda", "phi [°]": 5.0, "c [kPa]": 15.0},
        {"Estrato": "Arena compacta", "phi [°]": 35.0, "c [kPa]": 0.0},
        {"Estrato": "Terreno rocoso", "phi [°]": 45.0, "c [kPa]": 9.0/KPA_TO_TM2}
    ])

    df_input = st.data_editor(
        df_init, 
        num_rows="dynamic", 
        use_container_width=True,
        column_config={
            "Estrato": st.column_config.TextColumn("Nombre del estrato"),
            "phi [°]": st.column_config.NumberColumn("Áng. Rozamiento φ (°)", min_value=0.0, max_value=45.0, step=1.0),
            "c [kPa]": st.column_config.NumberColumn("Cohesión c' (kPa)", min_value=0.0, step=1.0)
        }
    )

    if not df_input.empty:
        df_input['kh Granados'] = df_input.apply(lambda r: calc_chadeisson_granados(r['phi [°]'], r['c [kPa]']), axis=1)
        df_input['kh Geométrico'] = df_input.apply(lambda r: calc_chadeisson_geometrico(r['phi [°]'], r['c [kPa]']), axis=1)
        
        df_input['Desviación (%)'] = np.where(
            df_input['kh Geométrico'] > 0,
            abs(df_input['kh Granados'] - df_input['kh Geométrico']) / df_input['kh Geométrico'] * 100, 
            0.0
        )
        
        st.dataframe(
            df_input.style.format({
                'kh Granados': "{:,.0f}", 
                'kh Geométrico': "{:,.0f}", 
                'Desviación (%)': "{:.1f}%"
            }).background_gradient(subset=['Desviación (%)'], cmap='OrRd', vmin=0, vmax=15), 
            use_container_width=True
        )

with tab_abacos:
    st.subheader("Comparativa Visual Directa")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 6))
    niveles_completos = list(rectas_chadeisson_empiricas.keys())
    
    # Malla matemática cortada a 45 grados (alta resolución para el renderizado suave)
    c_vals = np.linspace(0, 9, 250)
    phi_vals = np.linspace(0, 45, 250)
    C_grid, Phi_grid = np.meshgrid(c_vals, phi_vals)
    
    # --- GRÁFICO 1: GRANADOS ---
    Kh_grid_granados = np.zeros_like(C_grid)
    for i in range(C_grid.shape[0]):
        for j in range(C_grid.shape[1]):
            Kh_grid_granados[i, j] = calc_chadeisson_granados_tm3(Phi_grid[i, j], C_grid[i, j])
            
    contornos_g = ax1.contour(C_grid, Phi_grid, Kh_grid_granados, levels=niveles_completos, colors='#2b59c3', linewidths=1.0, alpha=0.8)
    ax1.clabel(contornos_g, inline=True, fontsize=7, fmt='%1.0f')
    ax1.set_title("Modelo Granados (Polinomio Grado 5)", fontweight='bold', fontsize=10)
    
    # --- GRÁFICO 2: GEOMÉTRICO (Basado 100% en los puntos del usuario) ---
    Kh_grid_geom = np.zeros_like(C_grid)
    for i in range(C_grid.shape[0]):
        for j in range(C_grid.shape[1]):
            Kh_grid_geom[i, j] = calc_chadeisson_geometrico_tm3(Phi_grid[i, j], C_grid[i, j])
            
    contornos_m = ax2.contour(C_grid, Phi_grid, Kh_grid_geom, levels=niveles_completos, colors='#e67e22', linewidths=1.0, alpha=0.9)
    ax2.clabel(contornos_m, inline=True, fontsize=7, fmt='%1.0f')
    ax2.set_title("Modelo Geométrico Empírico (Tus Datos)", fontweight='bold', fontsize=10)
    
    # --- FORMATO COMÚN ---
    for ax in [ax1, ax2]:
        ax.set_xlim(0, 9)
        ax.set_ylim(0, 45) # Techo estricto a 45
        ax.set_xticks(np.arange(0, 10, 1))
        ax.set_yticks(np.arange(0, 50, 5))
        
        ax.xaxis.grid(True, linestyle='-', color='#e0e0e0', linewidth=0.5)
        ax.yaxis.grid(True, linestyle='--', color='#e0e0e0', linewidth=0.5)
        
        ax.set_xlabel('C (t/m²) (cohésion)', fontsize=9)
        ax.set_ylabel('Degrés (φ)', fontsize=9)
        ax.tick_params(axis='both', which='major', labelsize=8)
        
        # Calcular dinámicamente el triángulo de exclusión (basado en la recta 700)
        m_700, n_700 = rectas_chadeisson_empiricas[700]
        corte_x = -n_700 / m_700 
        ax.add_patch(plt.Polygon([[0,0], [corte_x, 0], [0, n_700]], color='gray', alpha=0.15, hatch='///'))
        
        # Pintar los puntos de entrada de la tabla
        if not df_input.empty:
            for _, row in df_input.iterrows():
                phi_p = row['phi [°]']
                c_p = row['c [kPa]'] * KPA_TO_TM2
                if 0 <= phi_p <= 45 and 0 <= c_p <= 9:
                    ax.scatter(c_p, phi_p, color='#e74c3c', s=40, edgecolors='black', zorder=5)
    
    plt.tight_layout()
    st.pyplot(fig)