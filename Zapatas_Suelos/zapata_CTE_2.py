import math

def calcular_factores_capacidad(phi_deg):
    """Calcula Nc, Nq, Ngamma según Brinch-Hansen (1970)."""
    phi_rad = math.radians(phi_deg)
    Nq = math.exp(math.pi * math.tan(phi_rad)) * (math.tan(math.pi/4 + phi_rad/2))**2
    Nc = (Nq - 1) * (1 / math.tan(phi_rad)) if phi_deg > 0 else 5.14  # Para phi=0, Nc=5.14
    Ngamma = 2 * (Nq + 1) * math.tan(phi_rad)
    return Nc, Nq, Ngamma

def peso_especifico_sumergido(gamma_sat, gamma_w=9.81):
    """Calcula el peso específico sumergido (gamma')."""
    return gamma_sat - gamma_w

def factores_forma(B, L):
    """Factores de forma (sc, sq, sgamma)."""
    if L == 0:
        return 1.0, 1.0, 0.6  # Zapata corrida
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
    alpha_rad = math.radians(alpha_deg)
    ic = max(0, 1 - alpha_deg / 45)  # Evitar valores negativos
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

def obtener_B_L():
    """Obtiene B y L asegurando que B <= L."""
    while True:
        B = obtener_float("Ancho de la zapata (B, en metros): ", 0.1)
        L = obtener_float("Largo de la zapata (L, en metros): ", 0.1)
        if B > L:
            print("Error: El ancho (B) debe ser menor o igual que el largo (L). Inténtalo de nuevo.")
        else:
            return B, L

def preguntar_sobrecarga():
    """Pregunta al usuario si quiere considerar la sobrecarga de tierras sobre la cimentación."""
    while True:
        respuesta = input("¿Considerar sobrecarga de tierras sobre la cimentación? (s/n): ").strip().lower()
        if respuesta in ['s', 'n', 'si', 'no']:
            return respuesta in ['s', 'si']
        print("Respuesta no válida. Introduce 's' (sí) o 'n' (no).")

def calcular_carga_admisible():
    """Programa principal con entrada por teclado."""
    print("=== CÁLCULO DE CARGA ADMISIBLE PARA CIMENTACIONES SUPERFICIALES (CTE-DB-SE-C) ===")

    # Datos geométricos (con validación B <= L)
    B, L = obtener_B_L()
    D = obtener_float("Profundidad de empotramiento (D, en metros): ", 0)

    # Parámetros del terreno
    c = obtener_float("Cohesión efectiva (c, en kPa): ", 0)
    phi_deg = obtener_float("Ángulo de rozamiento interno (phi, en grados): ", 0, 45)
    gamma = obtener_float("Peso específico natural (gamma, en kN/m³): ", 10, 30)
    gamma_sat = obtener_float("Peso específico saturado (gamma_sat, en kN/m³): ", gamma, 30)
    D_w = obtener_float("Profundidad del nivel freático (D_w, en metros desde superficie): ", 0)

    # Otros parámetros
    FS = obtener_float("Factor de seguridad (FS, default=3): ", 1, 10) or 3.0
    alpha_deg = obtener_float("Inclinación de la carga (alpha, en grados, default=0): ", 0, 45) or 0.0

    # Preguntar si se considera la sobrecarga de tierras
    considerar_sobrecarga = preguntar_sobrecarga()

    # 1. Factores de capacidad de carga
    Nc, Nq, Ngamma = calcular_factores_capacidad(phi_deg)

    # 2. Peso específico ajustado por nivel freático
    gamma_efectivo = peso_especifico_sumergido(gamma_sat) if D_w <= D else gamma

    # 3. Factores de forma
    sc, sq, sgamma = factores_forma(B, L)

    # 4. Factores de profundidad
    dc, dq, dgamma = factores_profundidad(D, B)

    # 5. Factores de inclinación
    ic, iq, igamma = factores_inclinacion(alpha_deg)

    # 6. Cálculo de la presión última (q_ult)
    termino_c = c * Nc * sc * dc * ic

    # Término de sobrecarga (gamma * D)
    if considerar_sobrecarga:
        if D_w <= D:
            gamma_sobre_NF = gamma
            gamma_bajo_NF = peso_especifico_sumergido(gamma_sat)
            termino_q = (gamma_sobre_NF * min(D_w, D) + gamma_bajo_NF * max(D - D_w, 0)) * Nq * sq * dq * iq
        else:
            termino_q = gamma * D * Nq * sq * dq * iq
    else:
        termino_q = 0  # No se considera la sobrecarga de tierras

    termino_gamma = 0.5 * gamma_efectivo * B * Ngamma * sgamma * dgamma * igamma

    q_ult = termino_c + termino_q + termino_gamma

    # 7. Presión neta última
    gamma_base = peso_especifico_sumergido(gamma_sat) if D_w <= D else gamma
    q_net_ult = q_ult - gamma_base * D

    # 8. Presión admisible
    q_adm = q_net_ult / FS

    # 9. Carga admisible total (kN)
    carga_adm_total = q_adm * B * L

    # Resultados
    print("\n--- RESULTADOS ---")
    print(f"Configuración: {'Con sobrecarga de tierras' if considerar_sobrecarga else 'Sin sobrecarga de tierras'}")
    print(f"Factores de capacidad: Nc = {Nc:.2f}, Nq = {Nq:.2f}, Nγ = {Ngamma:.2f}")
    print(f"Factores de forma: sc = {sc:.2f}, sq = {sq:.2f}, sγ = {sgamma:.2f}")
    print(f"Factores de profundidad: dc = {dc:.2f}, dq = {dq:.2f}, dγ = {dgamma:.2f}")
    print(f"Factores de inclinación: ic = {ic:.2f}, iq = {iq:.2f}, iγ = {igamma:.2f}")
    print(f"\nPresión última de hundimiento (q_ult): {q_ult:.2f} kPa")
    print(f"Presión neta última (q_net_ult): {q_net_ult:.2f} kPa")
    print(f"Presión admisible (q_adm): {q_adm:.2f} kPa")
    print(f"Carga admisible total para zapata {B}m x {L}m: {carga_adm_total:.2f} kN")

# --- Ejecutar el programa ---
if __name__ == "__main__":
    calcular_carga_admisible()