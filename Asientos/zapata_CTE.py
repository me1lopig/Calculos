import math

def calcular_carga_admisible(B, L, D, c, phi_grados, gamma, gamma_sat, zw, FS=3.0, ex=0, ey=0, V=1, H=0):
    """
    Calcula la carga de hundimiento (qh) y admisible (qadm) de una zapata.
    
    Parámetros:
    B, L : Ancho y largo real de la zapata (m)
    D    : Profundidad de empotramiento (m)
    c    : Cohesión del terreno (kPa o kN/m2)
    phi_grados : Ángulo de rozamiento interno (grados)
    gamma      : Peso específico natural del terreno (kN/m3)
    gamma_sat  : Peso específico saturado del terreno (kN/m3)
    zw   : Profundidad del nivel freático desde la superficie (m)
    FS   : Factor de seguridad (Típicamente 3 para CTE)
    ex, ey : Excentricidades de la carga (m)
    V, H : Cargas vertical y horizontal para factores de inclinación (kN), en caso de que no se tengan no se aplica
    """
    
    gamma_w = 9.81 # Peso específico del agua (kN/m3)
    phi = math.radians(phi_grados)
    
    # 1. Dimensiones efectivas (Ancho y Largo equivalente)
    B_eff = B - 2 * ex
    L_eff = L - 2 * ey
    if B_eff > L_eff: # Asegurar que B es el lado menor
        B_eff, L_eff = L_eff, B_eff
        
    # 2. Efecto del Nivel Freático (Corrección de gamma y q)
    if zw <= D:
        # Nivel freático por encima o en la base
        q = (gamma * zw) + ((gamma_sat - gamma_w) * (D - zw))
        gamma_base = gamma_sat - gamma_w
    elif D < zw < (D + B_eff):
        # Nivel freático dentro del bulbo de presiones (interpola)
        q = gamma * D
        gamma_eff = gamma_sat - gamma_w
        gamma_base = gamma_eff + (gamma - gamma_eff) * ((zw - D) / B_eff)
    else:
        # Nivel freático no afecta
        q = gamma * D
        gamma_base = gamma

    # 3. Factores de Capacidad Portante (Nc, Nq, Ngamma)
    if phi_grados > 0:
        Nq = math.exp(math.pi * math.tan(phi)) * (math.tan(math.radians(45) + phi/2))**2
        Nc = (Nq - 1) / math.tan(phi)
        Ngamma = 2 * (Nq - 1) * math.tan(phi)
    else:
        Nq = 1.0
        Nc = 5.14
        Ngamma = 0.0

    # 4. Factores de Forma (sc, sq, sgamma)
    if phi_grados > 0:
        sq = 1 + (B_eff / L_eff) * math.sin(phi)
        sgamma = 1 - 0.3 * (B_eff / L_eff)
        sc = (sq * Nq - 1) / (Nq - 1)
    else:
        sq = 1.0
        sgamma = 1.0
        sc = 1 + 0.2 * (B_eff / L_eff)

    # 5. Factores de Profundidad (dc, dq, dgamma)
    k = D / B_eff if (D / B_eff) <= 1 else math.atan(D / B_eff)
    if phi_grados > 0:
        dq = 1 + 2 * math.tan(phi) * ((1 - math.sin(phi))**2) * k
        dgamma = 1.0
        dc = dq - (1 - dq) / (Nc * math.tan(phi))
    else:
        dq = 1.0
        dgamma = 1.0
        dc = 1 + 0.4 * k

    # 6. Factores de Inclinación de la Carga (ic, iq, igamma)
    if H > 0 and V > 0:
        m = (2 + (B_eff/L_eff)) / (1 + (B_eff/L_eff))
        iq = (1 - (H / (V + B_eff * L_eff * c * (1/math.tan(phi)) if phi_grados > 0 else V))) ** m
        igamma = (1 - (H / (V + B_eff * L_eff * c * (1/math.tan(phi)) if phi_grados > 0 else V))) ** (m + 1)
        if phi_grados > 0:
            ic = iq - (1 - iq) / (Nc * math.tan(phi))
        else:
            ic = 1 - (m * H) / (B_eff * L_eff * c * Nc)
    else:
        ic, iq, igamma = 1.0, 1.0, 1.0

    # 7. Cálculo de la Carga de Hundimiento (qh)
    termino_cohesion = c * Nc * sc * dc * ic
    termino_sobrecarga = q * Nq * sq * dq * iq
    termino_peso = 0.5 * gamma_base * B_eff * Ngamma * sgamma * dgamma * igamma

    qh = termino_cohesion + termino_sobrecarga + termino_peso
    qadm = qh / FS

    # Imprimir resultados detallados
    print(f"--- RESULTADOS DEL CÁLCULO ---")
    print(f"Dimensiones equivalentes : B* = {B_eff:.2f} m, L* = {L_eff:.2f} m")
    print(f"Peso esp. bajo la base   : gamma* = {gamma_base:.2f} kN/m3")
    print(f"Sobrecarga efectiva (q)  : {q:.2f} kPa")
    print(f"Factores Portantes       : Nc={Nc:.2f}, Nq={Nq:.2f}, Ngamma={Ngamma:.2f}")
    print(f"Término de Cohesión      : {termino_cohesion:.2f} kPa")
    print(f"Término de Sobrecarga    : {termino_sobrecarga:.2f} kPa")
    print(f"Término de Peso del Suelo: {termino_peso:.2f} kPa")
    print(f"-"*30)
    print(f"CARGA DE HUNDIMIENTO (qh) : {qh:.2f} kPa")
    print(f"CARGA ADMISIBLE (q_adm)   : {qadm:.2f} kPa (Con F.S. = {FS})")
    
    return qh, qadm

# --- EJEMPLO DE USO ---
# Zapata de 2x2m, a 1.5m de profundidad. NF a 1.0m (por encima de la base)
# Terreno: cohesión 10 kPa, phi 30º, gamma 18 kN/m3, gamma_sat 20 kN/m3
for B in range(1, 10):
    calcular_carga_admisible(B, B, D=2.5, c=100, phi_grados=0, gamma=18, gamma_sat=20, zw=10.0)