import streamlit as st
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Geotecnia Pro: Chadeisson", layout="wide")

# --- CONSTANTES DE CONVERSIÓN ---
# 1 T/m² ≈ 9.80665 kPa
KPA_TO_TM2 = 1.0 / 9.80665 
TM3_TO_KNM3 = 9.80665 

# --- FUNCIONES DE CÁLCULO ---
def calc_chadeisson_granados(phi_d, c_kpa):
    """
    Regresión polinómica de Granados (2018) para el ábaco de Chadeisson.
    Realiza un ajuste bidimensional de 5º grado en φ y 2º grado en c.
    """
    phi_rad = math.radians(phi_d)
    c_t_m2 = c_kpa * KPA_TO_TM2
    
    # Coeficientes exactos del ajuste de mínimos cuadrados
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
            
    # El resultado final se escala por 10^3 y se pasa de T/m³ a kN/m³
    return max(kh_sum * 1000.0 * TM3_TO_KNM3, 0.0)

# --- INTERFAZ ---
st.title("🧮 Calculadora de Balasto: Ábaco de Chadeisson")
st.markdown("""
Esta herramienta digitaliza el clásico ábaco empírico de Chadeisson utilizando el modelo polinómico de **Granados (2018)**. 
Calcula el coeficiente de balasto horizontal ($k_h$) basándose exclusivamente en los parámetros resistentes del terreno.
""")

# Tabla de entrada de datos
st.subheader("📋 Estratigrafía del Terreno")
st.write("Añade, edita o elimina capas de suelo directamente en la tabla.")

# Datos por defecto
df_init = pd.DataFrame([
    {"Estrato": "Relleno superficial", "phi [°]": 25.0, "c [kPa]": 5.0},
    {"Estrato": "Arena media", "phi [°]": 32.0, "c [kPa]": 0.0},
    {"Estrato": "Arcilla rígida", "phi [°]": 15.0, "c [kPa]": 40.0}
])

# Editor interactivo (hemos eliminado el parámetro gamma por no ser necesario en Chadeisson)
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
    # Cálculo automático de la nueva columna
    df_input['kh Chadeisson [kN/m³]'] = df_input.apply(
        lambda row: calc_chadeisson_granados(row['phi [°]'], row['c [kPa]']), axis=1
    )
    
    # Mostrar tabla de resultados con formato
    st.subheader("📈 Resultados Calculados")
    st.dataframe(
        df_input.style.format({'kh Chadeisson [kN/m³]': "{:,.1f}"})
                      .background_gradient(subset=['kh Chadeisson [kN/m³]'], cmap='Blues'),
        use_container_width=True
    )

    # Gráfico de barras mejorado
    st.write("---")
    st.subheader("📊 Visualización del Balasto por Capa")
    
    fig, ax = plt.subplots(figsize=(10, 4))
    x = np.arange(len(df_input))
    
    # Dibujar barras
    bars = ax.bar(x, df_input['kh Chadeisson [kN/m³]'], color='#2b59c3', width=0.5)
    
    ax.set_ylabel('kh [kN/m³]')
    ax.set_title('Módulo de Balasto Horizontal (Método Chadeisson)')
    ax.set_xticks(x)
    ax.set_xticklabels(df_input['Estrato'], rotation=0)
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    
    # Añadir etiquetas de valor numérico justo encima de cada barra
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + (yval*0.02), f'{yval:,.0f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    st.pyplot(fig)
    
    # --- BOTÓN DE EXPORTACIÓN ---
    st.write("---")
    @st.cache_data
    def convert_df(df):
        # Convertir a CSV separando por punto y coma (mejor para Excel en español)
        return df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')

    csv = convert_df(df_input)
    st.download_button(
        label="⬇️ Descargar Resultados a Excel (CSV)",
        data=csv,
        file_name='estratigrafia_balasto_chadeisson.csv',
        mime='text/csv',
    )
else:
    st.warning("Añada al menos una fila a la tabla para realizar los cálculos.")