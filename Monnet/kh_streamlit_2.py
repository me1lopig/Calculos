import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Geotecnia Pro: Chadeisson Dual", layout="wide")

# --- CONSTANTES DE CONVERSIÓN ---
KPA_TO_TM2 = 1.0 / 9.80665
TM3_TO_KNM3 = 9.80665

# --- MÉTODO 1: POLINOMIO DE GRANADOS ---
def calc_chadeisson_granados(phi_d, c_kpa):
    """Ajuste polinómico de Granados (2018) con 18 coeficientes."""
    phi_rad = math.radians(phi_d)
    c_t_m2 = c_kpa * KPA_TO_TM2
    
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
            kh_sum += a[alpha] * (phi_rad**j) * (c_t_m2**k)
            
    return max(kh_sum * 1000.0 * TM3_TO_KNM3, 0.0)

# --- MÉTODO 2: INTERPOLACIÓN GEOMÉTRICA DE RECTAS ---
def calc_chadeisson_geometrico(phi_d, c_kpa):
    """Decodificación visual en familias de rectas y posterior interpolación."""
    c_tm2 = c_kpa * KPA_TO_TM2
    
    # Ecuaciones de las rectas originales decodificadas: Kh -> (pendiente m, ordenada n)
    # Formato de la recta: phi = m * C + n
    rectas_chadeisson = {
        700:   (-2.0, 4.0),
        800:   (-2.0, 6.0),
        900:   (-2.0, 8.0),
        1000:  (-2.0, 10.0),
        1200:  (-2.0, 14.0),
        1500:  (-2.0, 20.0),
        2000:  (-2.5, 25.0),
        3000:  (-2.0, 32.0),
        4000:  (-1.5, 36.0),
        5000:  (-1.5, 40.0),
        6000:  (-1.5, 44.0),
        8000:  (-1.5, 50.0),
        10000: (-1.5, 56.0),
        12000: (-1.5, 57.0),
        14000: (-1.5, 57.5),
        16000: (-1.5, 58.5) # Anclada en (C=9, phi=45) visualmente
    }
    
    # 1. Calculamos a qué altura (grados phi) pasa cada recta para la cohesión dada
    alturas_phi = []
    for kh, (m, n) in rectas_chadeisson.items():
        phi_recta = m * c_tm2 + n
        alturas_phi.append((phi_recta, kh))
        
    # Ordenar de menor a mayor altura (para poder interpolar)
    alturas_phi.sort()
    
    # 2. Comprobar límites (Exclusión y Tope)
    if phi_d < alturas_phi[0][0]:
        return 0.0 # Zona rayada de exclusión (fango/arena suelta)
    if phi_d >= alturas_phi[-1][0]:
        return alturas_phi[-1][1] * TM3_TO_KNM3 # Supera la línea de 16000
        
    # 3. Interpolar linealmente el Kh
    for i in range(len(alturas_phi) - 1):
        phi_inf, kh_inf = alturas_phi[i]
        phi_sup, kh_sup = alturas_phi[i+1]
        
        if phi_inf <= phi_d <= phi_sup:
            # Distancia proporcional entre la curva de abajo y la de arriba
            if phi_sup == phi_inf: # Evitar división por cero en casos extremos
                kh_interp = kh_inf
            else:
                peso = (phi_d - phi_inf) / (phi_sup - phi_inf)
                kh_interp = kh_inf + peso * (kh_sup - kh_inf)
            
            return kh_interp * TM3_TO_KNM3
            
    return 0.0

# --- INTERFAZ UI ---
st.title("🧮 Calculadora de Balasto: Auditoría Dual")
st.markdown("""
Esta herramienta audita el ábaco de Chadeisson comparando dos enfoques: 
1. **Modelo de Granados:** Regresión polinómica por mínimos cuadrados (caja negra matemática).
2. **Modelo Geométrico:** Interpolación lineal basada en el escaneo topológico de las rectas originales.
""")

st.subheader("📋 Estratigrafía del Terreno")

df_init = pd.DataFrame([
    {"Estrato": "Relleno superficial", "phi [°]": 25.0, "c [kPa]": 5.0},
    {"Estrato": "Arena media", "phi [°]": 32.0, "c [kPa]": 0.0},
    {"Estrato": "Arcilla rígida", "phi [°]": 15.0, "c [kPa]": 40.0}
])

df_input = st.data_editor(
    df_init, 
    num_rows="dynamic", 
    use_container_width=True,
    column_config={
        "Estrato": st.column_config.TextColumn("Nombre del estrato"),
        "phi [°]": st.column_config.NumberColumn("Áng. Rozamiento φ (°)", min_value=0.0, max_value=48.0, step=1.0),
        "c [kPa]": st.column_config.NumberColumn("Cohesión c' (kPa)", min_value=0.0, max_value=100.0, step=1.0)
    }
)

if not df_input.empty:
    # Cálculos simultáneos
    df_input['kh Granados [kN/m³]'] = df_input.apply(
        lambda row: calc_chadeisson_granados(row['phi [°]'], row['c [kPa]']), axis=1
    )
    df_input['kh Geométrico [kN/m³]'] = df_input.apply(
        lambda row: calc_chadeisson_geometrico(row['phi [°]'], row['c [kPa]']), axis=1
    )
    
    # Columna de comprobación de error/desviación
    df_input['Desviación (%)'] = np.where(
        df_input['kh Geométrico [kN/m³]'] > 0,
        abs(df_input['kh Granados [kN/m³]'] - df_input['kh Geométrico [kN/m³]']) / df_input['kh Geométrico [kN/m³]'] * 100,
        0.0
    )
    
    st.subheader("📈 Auditoría de Resultados")
    # Formatear la tabla visualmente
    st.dataframe(
        df_input.style.format({
            'kh Granados [kN/m³]': "{:,.0f}",
            'kh Geométrico [kN/m³]': "{:,.0f}",
            'Desviación (%)': "{:.1f}%"
        }).background_gradient(subset=['Desviación (%)'], cmap='OrRd', vmin=0, vmax=15),
        use_container_width=True
    )

    # Gráfico de barras comparativo
    st.write("---")
    st.subheader("📊 Comparativa Visual de Modelos")
    
    fig, ax = plt.subplots(figsize=(10, 4))
    x = np.arange(len(df_input))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, df_input['kh Granados [kN/m³]'], width, label='Polinomio Granados', color='#2b59c3')
    bars2 = ax.bar(x + width/2, df_input['kh Geométrico [kN/m³]'], width, label='Interpolación Rectas', color='#e67e22')
    
    ax.set_ylabel('kh [kN/m³]')
    ax.set_title('Contraste de Modelos de Cálculo para el Ábaco de Chadeisson')
    ax.set_xticks(x)
    ax.set_xticklabels(df_input['Estrato'], rotation=0)
    ax.legend()
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    
    st.pyplot(fig)
    
    # --- EXPORTACIÓN ---
    @st.cache_data
    def convert_df(df):
        return df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')

    st.download_button(
        label="⬇️ Descargar Reporte a Excel (CSV)",
        data=convert_df(df_input),
        file_name='auditoria_balasto_chadeisson.csv',
        mime='text/csv',
    )