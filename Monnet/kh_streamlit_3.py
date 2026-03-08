import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Geotecnia Pro: Chadeisson Auditor", layout="wide")

# --- CONSTANTES DE CONVERSIÓN ---
KPA_TO_TM2 = 1.0 / 9.80665
TM3_TO_KNM3 = 9.80665

# =====================================================================
# MÉTODO 1: POLINOMIO DE GRANADOS (Auditor Matemático)
# =====================================================================
def calc_chadeisson_granados_tm3(phi_d, c_tm2):
    """Evalúa el polinomio en T/m³ para generar la malla del gráfico."""
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
    """Envoltura SI para los cálculos de la tabla."""
    return calc_chadeisson_granados_tm3(phi_d, c_kpa * KPA_TO_TM2) * TM3_TO_KNM3


# =====================================================================
# MÉTODO 2: MODELO GEOMÉTRICO (Decodificación Vectorial)
# =====================================================================
# Diccionario maestro de rectas: Kh -> (pendiente m, ordenada n)
# Calibrado milimétricamente limitando a phi=45 y ajustando familias.
rectas_chadeisson_recalibradas = {
    # Familia 1 (Blandos): Pendiente -2.5
    700:  (-2.5, 4.0), 800:  (-2.5, 6.0), 900:  (-2.5, 8.0), 1000: (-2.5, 10.0),
    1100: (-2.5, 12.0), 1200: (-2.5, 14.0), 1300: (-2.5, 16.0), 1400: (-2.5, 18.0),
    1500: (-2.5, 20.0), 2000: (-2.5, 25.0), 
    # Familia 2 (Transición): Pendiente -2.0
    3000: (-2.0, 32.0), 
    # Familia 3 y 4 (Duros/Rocas): Pendiente -1.5 unificada
    4000: (-1.5, 36.0), 5000: (-1.5, 40.0), 6000: (-1.5, 44.0), 7000: (-1.5, 47.0), 
    8000: (-1.5, 50.0), 9000: (-1.5, 53.0), 10000: (-1.5, 56.0), 12000: (-1.5, 57.0), 
    14000: (-1.5, 57.75), 
    16000: (-1.5, 58.5) # Anclaje perfecto forzado en el vértice (C=9, phi=45)
}

def calc_chadeisson_geometrico_tm3(phi_d, c_tm2):
    """Evalúa la interpolación de rectas en T/m³ para generar el gráfico contour."""
    alturas_phi = []
    for kh, (m, n) in rectas_chadeisson_recalibradas.items():
        phi_recta = m * c_tm2 + n
        alturas_phi.append((phi_recta, kh))
        
    alturas_phi.sort() # Ordenar de menor a mayor altura en el eje Y
    
    # Exclusión y topes
    if phi_d < alturas_phi[0][0]: return 0.0 # Por debajo de la línea de 700
    if phi_d >= alturas_phi[-1][0]: return alturas_phi[-1][1] # Por encima de la línea 16000
        
    # Interpolación lineal pura
    for i in range(len(alturas_phi) - 1):
        phi_inf, kh_inf = alturas_phi[i]
        phi_sup, kh_sup = alturas_phi[i+1]
        
        if phi_inf <= phi_d <= phi_sup:
            if phi_sup == phi_inf: return kh_inf
            peso = (phi_d - phi_inf) / (phi_sup - phi_inf)
            return kh_inf + peso * (kh_sup - kh_inf)
            
    return 0.0

def calc_chadeisson_geometrico(phi_d, c_kpa):
    """Envoltura SI para la tabla de resultados."""
    return calc_chadeisson_geometrico_tm3(phi_d, c_kpa * KPA_TO_TM2) * TM3_TO_KNM3


# =====================================================================
# INTERFAZ DE USUARIO (STREAMLIT)
# =====================================================================
st.title("🧮 Calculadora de Balasto Horizontal (Auditor Dual)")

tab_calc, tab_abacos = st.tabs(["📝 Tabla de Cálculo y Auditoría", "📊 Proyección Visual (φ máx = 45°)"])

# --- PESTAÑA 1: TABLA ---
with tab_calc:
    st.markdown("Cálculo simultáneo limitando el ángulo de rozamiento al marco real del ábaco original (45°).")
    
    df_init = pd.DataFrame([
        {"Estrato": "Relleno superficial", "phi [°]": 25.0, "c [kPa]": 5.0},
        {"Estrato": "Arena media", "phi [°]": 32.0, "c [kPa]": 0.0},
        {"Estrato": "Roca Blanda (Tope)", "phi [°]": 45.0, "c [kPa]": 9.0/KPA_TO_TM2}
    ])

    # Data Editor con limitador estricto a 45 grados
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
        # Ejecutar los dos modelos
        df_input['kh Granados'] = df_input.apply(lambda r: calc_chadeisson_granados(r['phi [°]'], r['c [kPa]']), axis=1)
        df_input['kh Geométrico'] = df_input.apply(lambda r: calc_chadeisson_geometrico(r['phi [°]'], r['c [kPa]']), axis=1)
        
        # Calcular desviación (evitando divisiones por cero en zonas de exclusión)
        df_input['Desviación (%)'] = np.where(
            df_input['kh Geométrico'] > 0,
            abs(df_input['kh Granados'] - df_input['kh Geométrico']) / df_input['kh Geométrico'] * 100, 
            0.0
        )
        
        # Formatear la tabla final
        st.dataframe(
            df_input.style.format({
                'kh Granados': "{:,.0f}", 
                'kh Geométrico': "{:,.0f}", 
                'Desviación (%)': "{:.1f}%"
            }).background_gradient(subset=['Desviación (%)'], cmap='OrRd', vmin=0, vmax=15), 
            use_container_width=True
        )

# --- PESTAÑA 2: GRÁFICOS COMPACTOS ---
with tab_abacos:
    st.subheader("Comparativa Visual Directa (Etiquetas Inline)")
    
    # Figura más pequeña para mejor estética visual
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 6))
    niveles_completos = list(rectas_chadeisson_recalibradas.keys())
    
    # Generar la malla matemática (Cortada exactamente a 45 grados)
    c_vals = np.linspace(0, 9, 200)
    phi_vals = np.linspace(0, 45, 200)
    C_grid, Phi_grid = np.meshgrid(c_vals, phi_vals)
    
    # 1. Gráfico de Granados
    Kh_grid_granados = np.zeros_like(C_grid)
    for i in range(C_grid.shape[0]):
        for j in range(C_grid.shape[1]):
            Kh_grid_granados[i, j] = calc_chadeisson_granados_tm3(Phi_grid[i, j], C_grid[i, j])
            
    contornos_g = ax1.contour(C_grid, Phi_grid, Kh_grid_granados, levels=niveles_completos, colors='#2b59c3', linewidths=1.0, alpha=0.8)
    ax1.clabel(contornos_g, inline=True, fontsize=7, fmt='%1.0f')
    ax1.set_title("Modelo Granados (Polinomio Grado 5)", fontweight='bold', fontsize=10)
    
    # 2. Gráfico Geométrico (Mallas de interpolación para permitir etiquetas inline)
    Kh_grid_geom = np.zeros_like(C_grid)
    for i in range(C_grid.shape[0]):
        for j in range(C_grid.shape[1]):
            Kh_grid_geom[i, j] = calc_chadeisson_geometrico_tm3(Phi_grid[i, j], C_grid[i, j])
            
    contornos_m = ax2.contour(C_grid, Phi_grid, Kh_grid_geom, levels=niveles_completos, colors='#e67e22', linewidths=1.0, alpha=0.9)
    ax2.clabel(contornos_m, inline=True, fontsize=7, fmt='%1.0f')
    ax2.set_title("Modelo Geométrico Vectorial", fontweight='bold', fontsize=10)
    
    # 3. Formato compartido para ambos lienzos
    for ax in [ax1, ax2]:
        ax.set_xlim(0, 9)
        ax.set_ylim(0, 45) # Techo inamovible
        ax.set_xticks(np.arange(0, 10, 1))
        ax.set_yticks(np.arange(0, 50, 5))
        
        # Cuadrícula sutil
        ax.xaxis.grid(True, linestyle='-', color='#e0e0e0', linewidth=0.5)
        ax.yaxis.grid(True, linestyle='--', color='#e0e0e0', linewidth=0.5)
        
        # Textos ajustados
        ax.set_xlabel('C (t/m²) (cohésion)', fontsize=9)
        ax.set_ylabel('Degrés (φ)', fontsize=9)
        ax.tick_params(axis='both', which='major', labelsize=8)
        
        # Zona de exclusión (Ajustada matemáticamente a la recta de 700: cruza X en 4/2.5 = 1.6)
        ax.add_patch(plt.Polygon([[0,0], [1.6, 0], [0, 4]], color='gray', alpha=0.15, hatch='///'))
        
        # Pintar los puntos de la tabla
        if not df_input.empty:
            for _, row in df_input.iterrows():
                phi_p = row['phi [°]']
                c_p = row['c [kPa]'] * KPA_TO_TM2
                if 0 <= phi_p <= 45 and 0 <= c_p <= 9:
                    ax.scatter(c_p, phi_p, color='#e74c3c', s=40, edgecolors='black', zorder=5)
    
    # Ajuste automático de márgenes para que nada se solape
    plt.tight_layout()
    st.pyplot(fig)