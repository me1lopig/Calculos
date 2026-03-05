import streamlit as st
import numpy as np
import pandas as pd
import io 
from docx import Document # Nueva librería para crear archivos Word

# --- INICIALIZACIÓN DE LA MEMORIA DE LA APP ---
if 'documentacion_generada' not in st.session_state:
    st.session_state.documentacion_generada = False

# Configuración de la página
st.set_page_config(page_title="Calculadora Ábaco de Monnet", layout="wide")

st.title("🏗️ Calculadora del Coeficiente de Balasto ($K_h$) - Método de Monnet")

# --- BARRA LATERAL: Parámetros de la Estructura ---
st.sidebar.header("1. Parámetros de la Pantalla")
material = st.sidebar.selectbox("Selecciona un material:", ["Hormigón (≈ 30 GPa)", "Acero (≈ 210 GPa)", "Personalizado"])
e_defecto = 30000000.0 if material.startswith("Hormigón") else (210000000.0 if material.startswith("Acero") else 20000000.0)

E = st.sidebar.number_input("Valor de E (kPa):", value=e_defecto, step=1000000.0, format="%.0f")

metodo_inercia = st.sidebar.radio("Definir inercia (m⁴/m):", ["Calcular a partir del espesor", "Introducir valor directo"])
if metodo_inercia == "Calcular a partir del espesor":
    espesor = st.sidebar.number_input("Espesor del muro continuo (m):", value=0.60, step=0.05)
    I = (1.0 * espesor**3) / 12.0
else:
    I = st.sidebar.number_input("Momento de Inercia I (m⁴/m):", value=0.0018, format="%.5f")

EI = E * I
st.sidebar.success(f"**Rigidez a flexión (EI):** {EI:,.0f} kN·m²/m")

# --- PARÁMETROS AVANZADOS OCULTOS ---
st.sidebar.header("2. Parámetros del Modelo")
with st.sidebar.expander("⚙️ Configuración Avanzada (Calibración)"):
    st.warning("⚠️ Modifica estos valores solo si vas a calibrar el modelo con ensayos reales.")
    dro = st.number_input("Desplazamiento ref. d_ro (m)", value=0.015, format="%.3f")
    c0 = st.number_input("Cohesión ref. c_0 (kPa) [Fija en 30]", value=30.0)
    Ap = st.number_input("Coef. ajuste empírico A_p", value=10.0)

# --- ÁREA PRINCIPAL: Estratigrafía ---
st.header("Estratigrafía del Terreno")
st.write("Edita la tabla inferior. El cálculo base se actualiza al instante.")

datos_iniciales = {
    "Capa": ["Rellenos", "Arcilla Firme", "Arena Densa"],
    "Profundidad Base (m)": [2.0, 6.0, 12.0],
    "Peso Específico γ (kN/m³)": [18.0, 20.0, 21.0],
    "Ángulo Rozamiento φ (º)": [25.0, 15.0, 35.0],
    "Cohesión c (kPa)": [5.0, 40.0, 0.0]
}
df_editado = st.data_editor(pd.DataFrame(datos_iniciales), num_rows="dynamic", use_container_width=True)

# --- CÁLCULO REACTIVO ---
resultados = df_editado.copy()
kh_lista = []

for index, row in resultados.iterrows():
    gamma, phi_deg, c = row["Peso Específico γ (kN/m³)"], row["Ángulo Rozamiento φ (º)"], row["Cohesión c (kPa)"]
    phi_rad = np.radians(phi_deg)
    K0, Kp = 1 - np.sin(phi_rad), (1 + np.sin(phi_rad)) / (1 - np.sin(phi_rad))
    
    termino_friccion = ((20 * EI * gamma * (Kp - K0)) / (dro**4))**(1/5)
    termino_cohesion = (Ap * c * np.tanh(c / c0)) / dro
    kh_lista.append(round(termino_friccion + termino_cohesion, 2))

resultados["K_h Monnet (kN/m³)"] = kh_lista

st.header("📊 Resultados del Coeficiente de Balasto")
st.dataframe(resultados[["Capa", "Profundidad Base (m)", "K_h Monnet (kN/m³)"]], use_container_width=True)

# --- SECCIÓN: GENERACIÓN Y DESCARGA ---
st.header("📄 Exportación de Resultados")

if st.button("Generar Documentación", type="primary"):
    st.session_state.documentacion_generada = True
    st.success("¡Documentación generada con éxito! Ya puedes descargar los archivos.")

if st.session_state.documentacion_generada:
    col1, col2 = st.columns(2)

    # 1. Preparar archivo Excel
    buffer_excel = io.BytesIO()
    with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
        resultados.to_excel(writer, index=False, sheet_name='Balasto_Monnet')

    with col1:
        st.download_button(
            label="📊 Descargar Tabla en Excel",
            data=buffer_excel.getvalue(),
            file_name="Calculo_Balasto_Monnet.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # 2. Preparar Informe en Word (DOCX)
    doc = Document()
    doc.add_heading('MEMORIA DE CÁLCULO: COEFICIENTE DE BALASTO', 0)
    doc.add_paragraph('Cálculo realizado mediante el Método Analítico de Monnet.')

    doc.add_heading('1. Parámetros de la Estructura (Pantalla)', level=1)
    doc.add_paragraph(f"Material seleccionado: {material}", style='List Bullet')
    doc.add_paragraph(f"Módulo de Elasticidad (E): {E:,.2f} kPa", style='List Bullet')
    doc.add_paragraph(f"Momento de Inercia (I): {I:.5f} m⁴/m", style='List Bullet')
    doc.add_paragraph(f"Rigidez a flexión (EI): {EI:,.2f} kN·m²/m", style='List Bullet')

    doc.add_heading('2. Parámetros del Modelo Cinemático', level=1)
    doc.add_paragraph(f"Desplazamiento de referencia (d_ro): {dro:.3f} m", style='List Bullet')
    doc.add_paragraph(f"Cohesión de referencia (c_0): {c0:.2f} kPa", style='List Bullet')
    doc.add_paragraph(f"Coeficiente empírico de ajuste (A_p): {Ap:.2f}", style='List Bullet')

    doc.add_heading('3. Resultados por Estrato', level=1)
    
    # Crear la tabla en Word
    columnas_mostrar = ["Capa", "Profundidad Base (m)", "K_h Monnet (kN/m³)"]
    tabla_word = doc.add_table(rows=1, cols=len(columnas_mostrar))
    tabla_word.style = 'Table Grid' # Le da los bordes típicos de tabla
    
    # Rellenar cabeceras
    hdr_cells = tabla_word.rows[0].cells
    for i, nombre_col in enumerate(columnas_mostrar):
        hdr_cells[i].text = nombre_col

    # Rellenar datos
    for index, row in resultados.iterrows():
        row_cells = tabla_word.add_row().cells
        for i, nombre_col in enumerate(columnas_mostrar):
            row_cells[i].text = str(row[nombre_col])

    doc.add_paragraph("\nNota: El cálculo asume un comportamiento lineal por estrato según la formulación analítica de Monnet para pantallas flexibles/rígidas.")

    # Guardar en buffer de memoria
    buffer_word = io.BytesIO()
    doc.save(buffer_word)
    buffer_word.seek(0) # Rebobinar el buffer

    with col2:
        st.download_button(
            label="📝 Descargar Memoria de Cálculo (.docx)",
            data=buffer_word,
            file_name="Memoria_Calculo_Monnet.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )