import math
from itertools import product
from openpyxl import Workbook

def calcular_factores_capacidad(phi_deg):
    """Calcula Nc, Nq, Ngamma según Brinch-Hansen (1970)."""
    phi_rad = math.radians(phi_deg)
    Nq = math.exp(math.pi * math.tan(phi_rad)) * (math.tan(math.pi/4 + phi_rad/2))**2
    Nc = (Nq - 1) * (1 / math.tan(phi_rad)) if phi_deg > 0 else 5.14
    Ngamma = 2 * (Nq + 1) * math.tan(phi_rad)
    return Nc, Nq, Ngamma

def peso_especifico_sumergido(gamma_sat, gamma_w=9.81):
    """Calcula el peso específico sumergido (gamma')."""
    return gamma_sat - gamma_w

def factores_forma(B, L):
    """Factores de forma (sc, sq, sgamma)."""
    if L == 0:
        return 1.0, 1.0, 0.6
    sc = 1 + 0.2 * (B / L)
    sq = 1 + 0.2 * (B / L)
    sgamma = 1 - 0.4 * (B / L)
    return sc, sq, sgamma

def factores_profundidad(D, B):
    """Factores de profundidad (dc, dq, dgamma)."""
    if B == 0:
        return 1.0, 1.0, 1.0
    dq = 1 + 0.2 * (D / B)
    dc = 1 + 0.2 * (D / B)
    dgamma = 1.0
    return dc, dq, dgamma

def factores_inclinacion(alpha_deg=0):
    """Factores de inclinación (ic, iq, igamma)."""
    ic = max(0, 1 - alpha_deg / 45)
    iq = (1 - alpha_deg / 90)**2
    igamma = (1 - alpha_deg / 90)**2
    return ic, iq, igamma

def obtener_float(mensaje, min_val=None, max_val=None):
    """Solicita un valor float al usuario con validación básica."""
    while True:
        try:
            valor = float(input(mensaje))
            if min_val is not None and valor < min_val:
                print(f"El valor debe ser >= {min_val}. Inténtalo de nuevo.")
                continue
            if max_val is not None and valor > max_val:
                print(f"El valor debe ser <= {max_val}. Inténtalo de nuevo.")
                continue
            return valor
        except ValueError:
            print("Entrada no válida. Introduce un número.")

def preguntar_sobrecarga():
    """Pregunta al usuario si quiere considerar la sobrecarga de tierras."""
    while True:
        respuesta = input("¿Considerar sobrecarga de tierras sobre la cimentación? (s/n): ").strip().lower()
        if respuesta in ['s', 'n', 'si', 'no']:
            return respuesta in ['s', 'si']
        print("Respuesta no válida. Introduce 's' (sí) o 'n' (no).")

def calcular_carga_admisible(B, L, D, c, phi_deg, gamma, gamma_sat, D_w, FS, alpha_deg, considerar_sobrecarga):
    """Calcula la carga admisible para una combinación de B y L."""
    Nc, Nq, Ngamma = calcular_factores_capacidad(phi_deg)
    gamma_efectivo = peso_especifico_sumergido(gamma_sat) if D_w <= D else gamma
    sc, sq, sgamma = factores_forma(B, L)
    dc, dq, dgamma = factores_profundidad(D, B)
    ic, iq, igamma = factores_inclinacion(alpha_deg)

    termino_c = c * Nc * sc * dc * ic

    if considerar_sobrecarga:
        if D_w <= D:
            gamma_sobre_NF = gamma
            gamma_bajo_NF = peso_especifico_sumergido(gamma_sat)
            termino_q = (gamma_sobre_NF * min(D_w, D) + gamma_bajo_NF * max(D - D_w, 0)) * Nq * sq * dq * iq
        else:
            termino_q = gamma * D * Nq * sq * dq * iq
    else:
        termino_q = 0

    termino_gamma = 0.5 * gamma_efectivo * B * Ngamma * sgamma * dgamma * igamma
    q_ult = termino_c + termino_q + termino_gamma
    gamma_base = peso_especifico_sumergido(gamma_sat) if D_w <= D else gamma
    q_net_ult = q_ult - gamma_base * D
    q_adm = q_net_ult / FS
    carga_adm_total = q_adm * B * L

    return q_ult, q_net_ult, q_adm, carga_adm_total

def generar_combinaciones_B_L(B_inicio, B_fin, B_paso, L_inicio, L_fin, L_paso):
    """Genera combinaciones de B y L donde B <= L."""
    valores_B = [round(B_inicio + i * B_paso, 2) for i in range(int((B_fin - B_inicio) / B_paso) + 1)]
    valores_L = [round(L_inicio + i * L_paso, 2) for i in range(int((L_fin - L_inicio) / L_paso) + 1)]
    combinaciones = [(B, L) for B in valores_B for L in valores_L if B <= L]
    return combinaciones

def exportar_a_excel(resultados, nombre_archivo="resultados_cimentacion.xlsx"):
    """Exporta los resultados a un archivo Excel."""
    wb = Workbook()
    ws = wb.active
    ws.append(["B (m)", "L (m)", "q_ult (kPa)", "q_net_ult (kPa)", "q_adm (kPa)", "Carga admisible (kN)"])
    for resultado in resultados:
        ws.append(resultado)
    wb.save(nombre_archivo)
    print(f"\nLos resultados se han exportado a {nombre_archivo}.")

def main():
    print("=== CÁLCULO DE CARGA ADMISIBLE PARA CIMENTACIONES SUPERFICIALES (CTE-DB-SE-C) ===")

    # Datos de entrada
    D = obtener_float("Profundidad de empotramiento (D, en metros): ", 0)
    c = obtener_float("Cohesión efectiva (c, en kPa): ", 0)
    phi_deg = obtener_float("Ángulo de rozamiento interno (phi, en grados): ", 0, 45)
    gamma = obtener_float("Peso específico natural (gamma, en kN/m³): ", 10, 30)
    gamma_sat = obtener_float("Peso específico saturado (gamma_sat, en kN/m³): ", gamma, 30)
    D_w = obtener_float("Profundidad del nivel freático (D_w, en metros desde superficie): ", 0)
    FS = obtener_float("Factor de seguridad (FS, default=3): ", 1, 10) or 3.0
    alpha_deg = obtener_float("Inclinación de la carga (alpha, en grados, default=0): ", 0, 45) or 0.0
    considerar_sobrecarga = preguntar_sobrecarga()

    # Intervalos para B y L
    B_inicio = obtener_float("Valor inicial de B (m): ", 0.1)
    B_fin = obtener_float("Valor final de B (m): ", B_inicio)
    B_paso = obtener_float("Incremento de B (m): ", 0.1)

    L_inicio = obtener_float("Valor inicial de L (m): ", B_inicio)
    L_fin = obtener_float("Valor final de L (m): ", L_inicio)
    L_paso = obtener_float("Incremento de L (m): ", 0.1)

    # Generar combinaciones válidas (B <= L)
    combinaciones = generar_combinaciones_B_L(B_inicio, B_fin, B_paso, L_inicio, L_fin, L_paso)

    if not combinaciones:
        print("No hay combinaciones válidas de B y L (B <= L). Ajusta los intervalos.")
        return

    # Calcular para cada combinación
    resultados = []
    for B, L in combinaciones:
        q_ult, q_net_ult, q_adm, carga_adm_total = calcular_carga_admisible(
            B, L, D, c, phi_deg, gamma, gamma_sat, D_w, FS, alpha_deg, considerar_sobrecarga
        )
        resultados.append([B, L, q_ult, q_net_ult, q_adm, carga_adm_total])

    # Mostrar resultados en tabla
    print("\n--- RESULTADOS ---")
    print(f"{'B (m)':<6} {'L (m)':<6} {'q_ult (kPa)':<12} {'q_net_ult (kPa)':<15} {'q_adm (kPa)':<12} {'Carga adm (kN)':<15}")
    print("-" * 70)
    for resultado in resultados:
        print(f"{resultado[0]:<6.2f} {resultado[1]:<6.2f} {resultado[2]:<12.2f} {resultado[3]:<15.2f} {resultado[4]:<12.2f} {resultado[5]:<15.2f}")

    # Exportar a Excel
    exportar = input("\n¿Deseas exportar los resultados a un archivo Excel? (s/n): ").strip().lower()
    if exportar in ['s', 'si']:
        nombre_archivo = input("Introduce el nombre del archivo Excel (sin extensión): ") or "resultados_cimentacion"
        exportar_a_excel(resultados, f"{nombre_archivo}.xlsx")

# --- Ejecutar el programa ---
if __name__ == "__main__":
    try:
        main()
    except ImportError:
        print("Error: No se encontró la librería 'openpyxl'. Instálala con: pip install openpyxl")