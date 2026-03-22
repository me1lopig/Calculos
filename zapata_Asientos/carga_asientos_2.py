import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io
from datetime import datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL

# ══════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ══════════════════════════════════════════════════════════════════════════
GAMMA_AGUA = 9.81  # kN/m³
P_REF = 100.0      # Presión ficticia de referencia para el escalado elástico (kPa)

# ══════════════════════════════════════════════════════════════════════════
# TENSIONES DE HOLL — BAJO EL CENTRO (compartido por ambos métodos)
# ══════════════════════════════════════════════════════════════════════════
def holl_esquina(p, B, L, z):
    """Tensiones bajo la ESQUINA de una carga rectangular BxL (Solución de Holl)."""
    if z <= 1e-6:
        return p, p / 2.0, p / 2.0
    R1 = np.sqrt(L**2 + z**2)
    R2 = np.sqrt(B**2 + z**2)
    R3 = np.sqrt(L**2 + B**2 + z**2)
    arc = np.arctan((B * L) / (z * R3))
    sz = (p / (2*np.pi)) * (arc + B*L*(1/R1**2 + 1/R2**2)*(z/R3))
    sx = (p / (2*np.pi)) * (arc - (B*L*z)/(R1**2*R3))
    sy = (p / (2*np.pi)) * (arc - (B*L*z)/(R2**2*R3))
    return sz, sx, sy

def holl_centro(p, B, L, z):
    """Tensiones bajo el CENTRO: superposición ×4 de cuadrantes B/2 × L/2."""
    sz, sx, sy = holl_esquina(p, B/2.0, L/2.0, z)
    return 4*sz, 4*sx, 4*sy

# ══════════════════════════════════════════════════════════════════════════
# MÉTODO 1 — STEINBRENNER (φ1, φ2, s(z) analítico)
# ══════════════════════════════════════════════════════════════════════════
def phi1(m, n):
    if m == 0:
        t1 = np.log(np.sqrt(1+n**2)+n)
        t2 = n*np.log((np.sqrt(1+n**2)+1)/n)
    else:
        t1 = np.log((np.sqrt(1+m**2+n**2)+n)/np.sqrt(1+m**2))
        t2 = n*np.log((np.sqrt(1+m**2+n**2)+1)/np.sqrt(n**2+m**2))
    return (1/np.pi)*(t1+t2)

def phi2(m, n):
    if m == 0: return 0.0
    return (m/np.pi)*np.arctan(n/(m*np.sqrt(1+m**2+n**2)))

def s_z(p, B, E, nu, z, L):
    """Asiento teórico acumulado desde superficie hasta z (Steinbrenner)."""
    n = L/B
    m = z/B  # Factor de profundidad corregido
    corchete = (1-nu**2)*phi1(m,n) - (1-nu-2*nu**2)*phi2(m,n)
    return (p*B/E)*corchete

def calcular_steinbrenner(p, B, L, df, z_max):
    total = 0.0
    resultados = []
    z_actual = 0.0
    n_factor = L / B

    for _, row in df.iterrows():
        if z_actual >= z_max:
            break
        h_i   = float(row["Espesor (m)"])
        E_i   = float(row["E (kPa)"])
        nu_i  = float(row["nu"])
        nombre= str(row["Descripción"])

        z_techo = z_actual
        z_base  = min(z_actual + h_i, z_max)

        m_t = z_techo / (B/2)
        m_b = z_base  / (B/2)
        
        s_t = 4 * s_z(p, B/2, E_i, nu_i, z_techo, L/2)
        s_b = 4 * s_z(p, B/2, E_i, nu_i, z_base,  L/2)
        ds  = s_t - s_b
        total += ds

        resultados.append({
            "Capa":               nombre,
            "z Techo [m]":        round(z_techo, 3),
            "z Base [m]":         round(z_base,  3),
            "m_techo":            round(m_t, 4),
            "φ1_techo":           round(phi1(m_t, n_factor), 4),
            "φ2_techo":           round(phi2(m_t, n_factor), 4),
            "s_techo [mm]":       s_t*1000,
            "m_base":             round(m_b, 4),
            "φ1_base":            round(phi1(m_b, n_factor), 4),
            "φ2_base":            round(phi2(m_b, n_factor), 4),
            "s_base [mm]":        s_b*1000,
            "Δs [mm]":            ds*1000,
        })
        z_actual = z_base

    return total, pd.DataFrame(resultados)

# ══════════════════════════════════════════════════════════════════════════
# MÉTODO 2 — (integración directa de deformaciones unitarias)
# ══════════════════════════════════════════════════════════════════════════
def calcular_ec68(p, B, L, df, z_max, dz_sub=0.25):
    total = 0.0
    resultados = []
    z_actual = 0.0

    for _, row in df.iterrows():
        if z_actual >= z_max:
            break
        h_i    = float(row["Espesor (m)"])
        E_i    = float(row["E (kPa)"])
        nu_i   = float(row["nu"])
        nombre = str(row["Descripción"])

        z_techo = z_actual
        z_base  = min(z_actual + h_i, z_max)
        h_ef    = z_base - z_techo

        n_sub  = max(1, int(np.ceil(h_ef / dz_sub)))
        dz     = h_ef / n_sub

        ds_capa  = 0.0
        sz_medio = 0.0
        sx_medio = 0.0
        sy_medio = 0.0
        ez_medio = 0.0

        for k in range(n_sub):
            z_sub_t = z_techo + k * dz
            z_mid   = z_sub_t + dz / 2.0
            dsz, dsx, dsy = holl_centro(p, B, L, z_mid)
            dep_z  = (dsz - nu_i*(dsx+dsy)) / E_i
            ds_sub = dep_z * dz
            ds_capa  += ds_sub
            sz_medio += dsz
            sx_medio += dsx
            sy_medio += dsy
            ez_medio += dep_z

        sz_medio /= n_sub
        sx_medio /= n_sub
        sy_medio /= n_sub
        ez_medio /= n_sub

        total += ds_capa

        resultados.append({
            "Capa":          nombre,
            "z Techo [m]":   round(z_techo,  3),
            "z Base [m]":    round(z_base,   3),
            "h_ef [m]":      round(h_ef,     3),
            "Sub-capas":      n_sub,
            "Δσz med [kPa]": sz_medio,
            "Δσx med [kPa]": sx_medio,
            "Δσy med [kPa]": sy_medio,
            "Δεz med [-]":   ez_medio,
            "Δs [mm]":       ds_capa*1000,
        })
        z_actual = z_base

    return total, pd.DataFrame(resultados)

# ══════════════════════════════════════════════════════════════════════════
# TENSIÓN EFECTIVA
# ══════════════════════════════════════════════════════════════════════════
def sigma_v0(z, df, NF):
    sv = 0.0; z_act = 0.0
    for _, row in df.iterrows():
        h  = float(row["Espesor (m)"])
        g  = float(row["Peso Esp. (kN/m³)"])
        gs = float(row["Peso Esp. Sat (kN/m³)"])
        zt = z_act; zb = z_act + h
        if z <= zt: break
        ze = min(z, zb)
        z_sec_b = min(ze, NF)
        if z_sec_b > zt: sv += g*(z_sec_b-zt)
        z_sat_t = max(zt, NF)
        if ze > z_sat_t: sv += (gs-GAMMA_AGUA)*(ze-z_sat_t)
        z_act = zb
    return sv

# ══════════════════════════════════════════════════════════════════════════
# INFORME WORD ESTÉTICO
# ══════════════════════════════════════════════════════════════════════════
def _fig_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=250, bbox_inches='tight')
    buf.seek(0)
    return buf

def _add_styled_table(doc, df, title):
    h = doc.add_heading(title, level=2)
    h.runs[0].font.color.rgb = RGBColor(31, 73, 125)
    
    df = df.astype(str)
    table = doc.add_table(rows=1+len(df), cols=len(df.columns))
    
    table.style = 'Light Shading Accent 1' 
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    hdr_cells = table.rows[0].cells
    for i, column in enumerate(df.columns):
        hdr_cells[i].text = column
        hdr_cells[i].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        for paragraph in hdr_cells[i].paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(8) 
                run.font.color.rgb = RGBColor(23, 54, 93) 
    
    for i, row in enumerate(df.itertuples(index=False)):
        row_cells = table.rows[i+1].cells
        for j, value in enumerate(row):
            row_cells[j].text = str(value)
            row_cells[j].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for paragraph in row_cells[j].paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
                    run.font.size = Pt(8)
                    
    doc.add_paragraph()

def generar_word(B, L, s_adm, p_adm_st, p_adm_ec, NF, z_max, factor_bulbo, df_terreno,
                 df_st, df_ec, fig_bulbo_bytes):
    fecha = datetime.now().strftime("%d de %B de %Y — %H:%M")
    doc = Document()
    
    for sec in doc.sections:
        sec.top_margin = Cm(2.5)
        sec.bottom_margin = Cm(2.5)
        sec.left_margin = Cm(2.0) 
        sec.right_margin = Cm(2.0)
        
        footer = sec.footer
        footer_para = footer.paragraphs[0]
        footer_para.text = f"Memoria de Cálculo de Carga Admisible — Generado automáticamente el {fecha}"
        footer_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        footer_para.runs[0].font.size = Pt(8)
        footer_para.runs[0].font.color.rgb = RGBColor(128, 128, 128)

    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(10)

    h1_style = doc.styles['Heading 1']
    h1_font = h1_style.font
    h1_font.name = 'Calibri Light'
    h1_font.size = Pt(14)
    h1_font.color.rgb = RGBColor(23, 54, 93)
    h1_font.bold = True

    doc.add_paragraph()
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run('CÁLCULO DE PRESIÓN ADMISIBLE (POR ASIENTO)')
    r_title.bold = True
    r_title.font.size = Pt(20)
    r_title.font.color.rgb = RGBColor(23, 54, 93) 
    
    doc.add_paragraph()
    
    doc.add_heading('1. Datos de Diseño', level=1)
    table_params = doc.add_table(rows=5, cols=2)
    table_params.style = 'Light Shading Accent 1'
    
    data = [
        ('Dimensiones en planta (B × L)', f'{B:.2f} m  ×  {L:.2f} m'),
        ('Asiento Máximo Admisible (s_adm)', f'{s_adm:.1f} mm'),
        ('Profundidad del Nivel Freático (NF)', f'{NF:.1f} m'),
        (f'Profundidad de Integración ({factor_bulbo}B)', f'{z_max:.2f} m'),
        ('Criterio de análisis elástico', 'Tensión bajo centro (Escalado lineal directo)')
    ]
    
    for i, (key, val) in enumerate(data):
        row = table_params.rows[i].cells
        row[0].text = key
        row[1].text = val
        row[0].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        row[1].vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        row[0].paragraphs[0].runs[0].font.bold = True
        
    doc.add_paragraph()
    _add_styled_table(doc, df_terreno, '1.1 Estratigrafía del Perfil Geotécnico')
    doc.add_page_break()

    doc.add_heading('2. Presión Neta Admisible Calculada', level=1)
    
    table_res = doc.add_table(rows=1, cols=2)
    table_res.style = 'Light Shading Accent 1'
    table_res.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    c1, c2 = table_res.rows[0].cells
    c1.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    c2.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    
    p1 = c1.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1a = p1.add_run('Presión Admisible (Steinbrenner)\n')
    r1a.font.size = Pt(11); r1a.font.color.rgb = RGBColor(89, 89, 89); r1a.bold = True
    r1b = p1.add_run(f'{p_adm_st:.1f} kPa')
    r1b.font.size = Pt(16); r1b.bold = True; r1b.font.color.rgb = RGBColor(23, 54, 93)
    
    p2 = c2.paragraphs[0]
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2a = p2.add_run('Presión Admisible (Ec. Elástica)\n')
    r2a.font.size = Pt(11); r2a.font.color.rgb = RGBColor(89, 89, 89); r2a.bold = True
    r2b = p2.add_run(f'{p_adm_ec:.1f} kPa')
    r2b.font.size = Pt(16); r2b.bold = True; r2b.font.color.rgb = RGBColor(33, 115, 70)

    doc.add_paragraph()
    doc.add_paragraph()
    
    df_comp = pd.DataFrame({
        "Capa": df_st["Capa"],
        "Asiento aportado [mm]": df_st["Δs [mm]"].round(3)
    })
    _add_styled_table(doc, df_comp, '2.1 Distribución del asiento límite por estrato')
    doc.add_page_break()

    doc.add_heading('3. Cuadro de Tensiones (Correspondientes a p_adm)', level=1)
    _add_styled_table(doc, df_ec.round(3), 'Desglose Ec. Elástica para la Presión Admisible')
    doc.add_page_break()

    doc.add_heading('4. Gráfica del Bulbo de Tensiones Límite', level=1)
    p_fig = doc.add_paragraph()
    p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_fig = p_fig.add_run()
    r_fig.add_picture(fig_bulbo_bytes, width=Cm(14))
    
    nota = doc.add_paragraph(f'Evolución de las tensiones para la Presión Admisible restrictiva. La línea discontinua marca la profundidad de integración {factor_bulbo}B ({z_max:.2f} m).')
    nota.alignment = WD_ALIGN_PARAGRAPH.CENTER
    nota.runs[0].font.size = Pt(9)
    nota.runs[0].font.italic = True
    nota.runs[0].font.color.rgb = RGBColor(128,128,128)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════════════════════════════════
def reset_calculo():
    st.session_state.calculo_realizado = False

if 'calculo_realizado' not in st.session_state:
    st.session_state.calculo_realizado = False

if 'df_terreno' not in st.session_state:
    st.session_state.df_terreno = pd.DataFrame({
        "Descripción":           ["Relleno",  "Arcilla",  "Grava"],
        "Espesor (m)":           [1.5,         3.0,        5.0],
        "E (kPa)":               [10000.0,     15000.0,     40000.0],
        "nu":                    [0.30,         0.45,       0.25],
        "Peso Esp. (kN/m³)":     [18.0,         19.0,       21.0],
        "Peso Esp. Sat (kN/m³)": [20.0,         20.0,       22.0],
    })

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN UI
# ══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Carga Admisible por Asiento",
    layout="wide", page_icon="🏗️"
)

st.sidebar.title("Navegación")
modo = st.sidebar.radio("Vista:", [
    "🧮 Panel de Resultados",
    "📋 Detalle Capas Escalas",
    "📉 Bulbo Límite",
    "📖 Fundamento Teórico y Algoritmo",
])

st.sidebar.markdown("---")
st.sidebar.header("📥 Datos de Entrada")

B     = st.sidebar.number_input("Ancho (B) [m]",             min_value=0.1, value=2.0,   step=0.1,  on_change=reset_calculo)
L     = st.sidebar.number_input("Longitud (L) [m]",          min_value=0.1, value=3.0,   step=0.1,  on_change=reset_calculo)
s_adm = st.sidebar.number_input("Asiento Admisible [mm]",    min_value=1.0, value=25.0,  step=1.0, on_change=reset_calculo)
NF    = st.sidebar.number_input("Nivel Freático [m]",        min_value=0.0, value=100.0, step=0.5,  on_change=reset_calculo)

if L < B:
    B, L = L, B
    st.sidebar.warning("⚠️ L<B: valores intercambiados automáticamente.")

# Calculamos el espesor total de los estratos definidos en la tabla actual
espesor_total = float(pd.to_numeric(st.session_state.df_terreno["Espesor (m)"]).sum())

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Geometría de Integración")

factor_bulbo = st.sidebar.selectbox(
    "Profundidad del bulbo activo",
    options=[1.5, 2.0],
    format_func=lambda x: f"{x}B",
    on_change=reset_calculo,
    help="Define el espesor del terreno sobre el que se integrarán las deformaciones."
)

# Determinamos profundidad estática basada en la selección
z_max_calc = factor_bulbo * min(B, L)

# ALERTA CRÍTICA SI EL BULBO SUPERA LOS ESTRATOS
if z_max_calc > espesor_total:
    st.sidebar.error(
        f"🚨 **¡ALERTA GEOTÉCNICA!**\n\n"
        f"El bulbo de integración (**{z_max_calc:.2f} m**) supera la profundidad total de los "
        f"estratos definidos (**{espesor_total:.2f} m**).\n\n"
        f"**Añade más espesor en la tabla de terreno.**"
    )
else:
    st.sidebar.success(f"💡 **Bulbo fijado en {factor_bulbo}B = {z_max_calc:.2f} m**\n\n*(Terreno disponible: {espesor_total:.2f} m)*")

dz_sub = st.sidebar.select_slider(
    "Tamaño de subcapa elástica (dz) [m]",
    options=[2.0, 1.0, 0.5, 0.25, 0.10, 0.05],
    value=0.10,
    on_change=reset_calculo
)

# ══════════════════════════════════════════════════════════════════════════
# BOTÓN CALCULAR (THE DUMMY LOAD ALGORITHM)
# ══════════════════════════════════════════════════════════════════════════
st.sidebar.markdown("---")
if st.sidebar.button("🚀 Calcular Presión Admisible", type="primary", use_container_width=True):
    # 1. Calculamos usando la carga de referencia
    tot_st_ref, df_st = calcular_steinbrenner(P_REF, B, L, st.session_state.df_terreno, z_max_calc)
    tot_ec_ref, df_ec = calcular_ec68(        P_REF, B, L, st.session_state.df_terreno, z_max_calc, dz_sub)

    # 2. Factores de Escala (Linealidad)
    # Convertimos tot (metros) a milímetros para la proporción
    scale_st = s_adm / (tot_st_ref * 1000)
    scale_ec = s_adm / (tot_ec_ref * 1000)

    # 3. Presiones Admisibles Finales
    p_adm_st = P_REF * scale_st
    p_adm_ec = P_REF * scale_ec

    # 4. Escalamos los Dataframes para que reflejen la presión admisible
    df_st['s_techo [mm]'] *= scale_st
    df_st['s_base [mm]']  *= scale_st
    df_st['Δs [mm]']      *= scale_st

    df_ec['Δσz med [kPa]'] *= scale_ec
    df_ec['Δσx med [kPa]'] *= scale_ec
    df_ec['Δσy med [kPa]'] *= scale_ec
    df_ec['Δεz med [-]']   *= scale_ec
    df_ec['Δs [mm]']       *= scale_ec

    st.session_state.p_adm_st = p_adm_st
    st.session_state.p_adm_ec = p_adm_ec
    st.session_state.df_st    = df_st
    st.session_state.df_ec    = df_ec
    st.session_state.dz_used  = dz_sub
    st.session_state.z_max_calc = z_max_calc
    st.session_state.factor_bulbo = factor_bulbo 
    st.session_state.calculo_realizado = True

# ══════════════════════════════════════════════════════════════════════════
# BOTÓN INFORME WORD
# ══════════════════════════════════════════════════════════════════════════
st.sidebar.markdown("---")
if st.session_state.calculo_realizado:
    p_adm_st = st.session_state.p_adm_st
    p_adm_ec = st.session_state.p_adm_ec
    df_st    = st.session_state.df_st
    df_ec    = st.session_state.df_ec
    z_max    = st.session_state.z_max_calc
    factor_b = st.session_state.factor_bulbo

    p_plot = min(p_adm_st, p_adm_ec)

    z_vals = np.linspace(0.05, z_max * 1.5, 200) 
    sz_v,sx_v,sy_v,sv0_v = [],[],[],[]
    for z in z_vals:
        sz,sx,sy = holl_centro(p_plot, B, L, z)
        sz_v.append(sz); sx_v.append(sx); sy_v.append(sy)
        sv0_v.append(sigma_v0(z, st.session_state.df_terreno, NF)*0.20)
        
    fig_b, ax_b = plt.subplots(figsize=(5, 7))
    ax_b.plot(sz_v, z_vals, label=r"$\Delta\sigma_z$", color='red', lw=2)
    ax_b.plot(sx_v, z_vals, label=r"$\Delta\sigma_x$", color='blue', ls='--')
    ax_b.plot(sy_v, z_vals, label=r"$\Delta\sigma_y$", color='purple', ls='-.')
    ax_b.plot(sv0_v,z_vals, label=r"$0.20\sigma'_{v0}$ (Ref. EC7)", color='green', lw=1, ls=':')
    ax_b.axhline(y=z_max, color='orange', ls='--', lw=2, label=f'Corte Integración ({factor_b}B) = {z_max:.2f} m')
    
    if NF < z_max * 1.5:
        ax_b.axhline(y=NF, color='deepskyblue', ls='-.', lw=1.2, label=f'NF={NF:.1f} m')
        
    ax_b.set_ylim(z_max * 1.5, 0); ax_b.set_xlim(left=0)
    ax_b.set_xlabel("Tensión (kPa)"); ax_b.set_ylabel("Profundidad z (m)")
    ax_b.set_title(f"Bulbo Límite (p = {p_plot:.1f} kPa)"); ax_b.legend(fontsize=8)
    ax_b.grid(True, linestyle=':', alpha=0.4)
    ax_b.spines[['top','right']].set_visible(False)
    plt.tight_layout()
    fig_bulbo_bytes = _fig_bytes(fig_b)
    plt.close(fig_b)

    word_buf = generar_word(
        B, L, s_adm, p_adm_st, p_adm_ec, NF, z_max, factor_b,
        st.session_state.df_terreno,
        df_st, df_ec, fig_bulbo_bytes
    )
    st.sidebar.download_button(
        "📝 Descargar Informe Diseño", data=word_buf,
        file_name=f"diseno_carga_admisible_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True
    )
else:
    st.sidebar.button("📝 Descargar Informe Diseño", disabled=True,
                      use_container_width=True,
                      help="Primero calcula.")

# ══════════════════════════════════════════════════════════════════════════
# ÁREA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════
st.title("🏗️ Presión Admisible por Asiento")
st.markdown("**Cálculo de la presión admisible limitando la integración a la profundidad de influencia del bulbo**")
st.markdown("---")

if modo == "🧮 Panel de Resultados":
    st.header("1. Estratigrafía del Terreno")
    df_edit = st.data_editor(
        st.session_state.df_terreno,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "E (kPa)":               st.column_config.NumberColumn("E (kPa)",      min_value=100.0, step=500.0),
            "nu":                    st.column_config.NumberColumn("ν",             min_value=0.0, max_value=0.5, step=0.01, format="%.2f"),
            "Peso Esp. (kN/m³)":     st.column_config.NumberColumn("γ (kN/m³)",    min_value=10.0, max_value=25.0, step=0.5),
            "Peso Esp. Sat (kN/m³)": st.column_config.NumberColumn("γsat (kN/m³)", min_value=10.0, max_value=25.0, step=0.5),
        }
    )
    if not df_edit.equals(st.session_state.df_terreno):
        st.session_state.df_terreno = df_edit
        st.session_state.calculo_realizado = False
        st.rerun()

    st.markdown("---")
    st.header("2. Presión Neta Admisible")

    if not st.session_state.calculo_realizado:
        st.info("👈 Introduce el Asiento Límite y pulsa **Calcular** en el panel izquierdo.")
    else:
        # AVISO EN RESULTADOS SI HAY TRUNCAMIENTO
        espesor_total = float(pd.to_numeric(st.session_state.df_terreno["Espesor (m)"]).sum())
        if st.session_state.z_max_calc > espesor_total:
            st.error(f"⛔ **CÁLCULO INSEGURO:** El bulbo requería integrar hasta **{st.session_state.z_max_calc:.2f} m**, pero se ha truncado a **{espesor_total:.2f} m** por falta de estratos. Las presiones admisibles mostradas a continuación están SOBREESTIMADAS y no son válidas.")

        p_st = st.session_state.p_adm_st
        p_ec = st.session_state.p_adm_ec

        st.success(f"✅ Para no superar un asiento de **{s_adm} mm**, la cimentación soporta las siguientes presiones netas:")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🔵 p_adm (Steinbrenner)",f"{p_st:.1f} kPa")
        c2.metric("🟢 p_adm (Ec. Elástica)", f"{p_ec:.1f} kPa")
        dif = abs(p_st - p_ec)
        pct = (dif / min(p_st, p_ec)) * 100
        c3.metric("📊 Diferencia (Seguridad)", f"{dif:.1f} kPa", f"{pct:.1f}%")

        st.markdown("---")
        st.subheader(f"Distribución del asiento límite ({s_adm} mm) por estrato")
        df_comp = pd.DataFrame({
            "Capa": st.session_state.df_st["Capa"],
            "Asiento aportado [mm]": st.session_state.df_st["Δs [mm]"].round(3)
        })
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

elif modo == "📋 Detalle Capas Escalas":
    st.header("Detalle de Parámetros Escalados")
    if not st.session_state.calculo_realizado:
        st.warning("⚠️ Calcula primero.")
    else:
        st.subheader("🔵 Método de Steinbrenner")
        st.dataframe(st.session_state.df_st.round(4), use_container_width=True, hide_index=True)
        
        st.subheader("🟢 Ecuación Elástica (Ec. Elástica)")
        st.dataframe(st.session_state.df_ec.round(4), use_container_width=True, hide_index=True)

elif modo == "📉 Bulbo Límite":
    st.header("Bulbo de Tensiones (Estado Límite de Servicio)")
    if not st.session_state.calculo_realizado:
        st.warning("⚠️ Calcula primero.")
    else:
        z_max = st.session_state.z_max_calc
        factor_b = st.session_state.factor_bulbo
        p_plot = min(st.session_state.p_adm_st, st.session_state.p_adm_ec)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            z_gr = st.slider("Profundidad de gráfica [m]:", 1.0, z_max * 2.5, z_max * 1.5, 0.5)
            st.metric("p_admisible graficada", f"{p_plot:.1f} kPa")
            st.info(f"Profundidad de integración estática:\n **{factor_b}B = {z_max:.2f} m**")
        with col2:
            z_vals = np.linspace(0.05, z_gr, 200)
            sz_v,sx_v,sy_v,sv0_v = [],[],[],[]
            for z in z_vals:
                sz,sx,sy = holl_centro(p_plot, B, L, z)
                sv = sigma_v0(z, st.session_state.df_terreno, NF)
                sz_v.append(sz); sx_v.append(sx); sy_v.append(sy)
                sv0_v.append(sv * 0.2)

            fig, ax = plt.subplots(figsize=(9, 7))
            ax.plot(sz_v,   z_vals, label=r"Vertical $\Delta\sigma_z$",           color='red',         lw=2)
            ax.plot(sx_v,   z_vals, label=r"Horiz. Trans. $\Delta\sigma_x$",      color='blue',        ls='--')
            ax.plot(sy_v,   z_vals, label=r"Horiz. Long. $\Delta\sigma_y$",       color='purple',      ls='-.')
            ax.plot(sv0_v,  z_vals, label=r"$0.20\,\sigma'_{v0}$ (Ref EC7)",      color='green',       lw=1.5, ls=':')
            
            ax.axhline(y=z_max, color='orange', ls='--', lw=2, label=f'Base integración ({factor_b}B) = {z_max:.2f} m')
            
            if NF < z_gr:
                ax.axhline(y=NF, color='deepskyblue', ls='-.', lw=1.2, label=f'NF = {NF:.1f} m')
                
            ax.set_ylim(z_gr, 0); ax.set_xlim(left=0)
            ax.set_xlabel("Tensión (kPa)", fontsize=11)
            ax.set_ylabel("Profundidad z (m)", fontsize=11)
            ax.legend(loc='lower right', fontsize=9)
            ax.grid(True, linestyle=':', alpha=0.5)
            ax.spines[['top','right']].set_visible(False)
            st.pyplot(fig); plt.close(fig)

elif modo == "📖 Fundamento Teórico y Algoritmo":
    st.header("Fundamento Teórico y Algoritmo de Diseño")

    st.subheader("1. Algoritmo de Cálculo Inverso (Escalado Lineal Directo)")
    st.markdown(
        "Dado que se asume un comportamiento **elástico lineal** del terreno y se fija la "
        "profundidad de integración a una geometría constante (ej. 1.5B o 2.0B), el asiento resultante es "
        "directamente proporcional a la presión aplicada. El algoritmo de diseño aprovecha esta linealidad:"
    )
    st.markdown("1. Se aplica una presión ficticia de referencia internamente ($p_{ref} = 100$ kPa).")
    st.markdown("2. Se calcula el asiento de referencia ($s_{ref}$) generado por esa presión en la profundidad de bulbo estipulada.")
    st.markdown("3. Se obtiene la presión neta admisible ($p_{adm}$) aplicando una proporción exacta con el asiento límite fijado por el usuario ($s_{adm}$):")
    st.latex(r"p_{adm} = p_{ref} \cdot \frac{s_{adm}}{s_{ref}}")

    st.markdown("---")
    
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🔵 Método 1 — Steinbrenner")
        st.markdown("Integración analítica del campo de asientos usando los factores geométricos φ₁ y φ₂:")
        st.latex(r"s(z) = \frac{p \cdot B}{E}\left[(1-\nu^2)\phi_1 - (1-\nu-2\nu^2)\phi_2\right]")
        st.latex(r"\phi_1 = \frac{1}{\pi}\left[\ln\frac{\sqrt{1+m^2+n^2}+n}{\sqrt{1+m^2}} + n\ln\frac{\sqrt{1+m^2+n^2}+1}{\sqrt{n^2+m^2}}\right]")
        st.latex(r"\phi_2 = \frac{m}{\pi}\arctan\frac{n}{m\sqrt{1+m^2+n^2}}")
        st.markdown(r"Con $n = L/B$ y $m = z/B_{cuadrante}$. El asiento elástico de cada estrato se evalúa como la diferencia entre la base y el techo:")
        st.latex(r"\Delta s_i = s(z_{techo}) - s(z_{base})")

    with col_b:
        st.subheader("🟢 Método 2 — Ecuación Elástica")
        st.markdown("Integración numérica explícita de la deformación unitaria vertical en cada estrato:")
        st.latex(r"s = \sum_{i=1}^{n}\left[\frac{h}{E}\left(\Delta\sigma_z - \nu(\Delta\sigma_x+\Delta\sigma_y)\right)\right]_i")
        st.markdown(r"Las tensiones se evalúan en el **punto medio** de cada subcapa ($z_{mid}$):")
        st.latex(r"\Delta\varepsilon_z = \frac{\Delta\sigma_z - \nu(\Delta\sigma_x+\Delta\sigma_y)}{E}")
        st.latex(r"\Delta s_i = \Delta\varepsilon_z \cdot dz")

    st.markdown("---")
    st.subheader("🔁 Tensiones de Holl — compartidas por ambos métodos")
    st.markdown(
        r"Ambas formulaciones usan las tensiones de Holl bajo la **esquina** de una carga rectangular, "
        r"aplicando superposición elástica ($\times 4$) con sub-cuadrantes de $B/2 \times L/2$ para obtener el valor bajo el **centro** geométrico de la zapata:"
    )
    st.latex(r"\sigma_z = \frac{p}{2\pi}\left[\arctan\frac{BL}{zR_3} + BL\left(\frac{1}{R_1^2}+\frac{1}{R_2^2}\right)\frac{z}{R_3}\right]")
    st.latex(r"\sigma_x = \frac{p}{2\pi}\left[\arctan\frac{BL}{zR_3} - \frac{BLz}{R_1^2 R_3}\right]")
    st.latex(r"\sigma_y = \frac{p}{2\pi}\left[\arctan\frac{BL}{zR_3} - \frac{BLz}{R_2^2 R_3}\right]")
    st.latex(r"R_1=\sqrt{L^2+z^2}\quad R_2=\sqrt{B^2+z^2}\quad R_3=\sqrt{L^2+B^2+z^2}")