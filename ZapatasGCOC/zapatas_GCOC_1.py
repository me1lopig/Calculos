import math

def comprobacion_hundimiento(V, H, c, phi_deg, gamma_ap, gamma_sat, D_w, D, B_star, L_star, psi_deg=0.0, eta_deg=0.0, F_h_exigido=3.0):
    """
    Comprobación analítica de la carga de hundimiento (Brinch-Hansen modificado).
    
    NUEVOS PARÁMETROS:
    -----------
    V         : Fuerza vertical efectiva total sobre el plano de cimentación (kN)
    H         : Fuerza horizontal total aplicada (kN)
    """
    
    # ------------------------------------------------------------------
    # 1. CÁLCULO DE LA PRESIÓN DE SERVICIO E INCLINACIÓN
    # ------------------------------------------------------------------
    # Presión vertical media real transmitida al terreno
    p_v = V / (B_star * L_star)
    
    # Ángulo de inclinación de la resultante (delta)
    if V > 0:
        delta = math.atan(H / V)  # En radianes
    else:
        delta = 0.0

    # ------------------------------------------------------------------
    # 2. EVALUACIÓN DEL EFECTO DEL NIVEL FREÁTICO (Agua)
    # ------------------------------------------------------------------
    gamma_w = 9.81  
    gamma_prima = gamma_sat - gamma_w  
    
    if D_w >= D:
        D1 = D
        D2 = 0
        h_w = D_w - D  
    else:
        D1 = max(0, D_w)
        D2 = D - D1
        h_w = 0  
        
    q = (gamma_ap * D1) + (gamma_prima * D2)
    
    if h_w == 0:
        gamma_calc = gamma_prima
    else:
        gamma_calc = gamma_prima + 0.6 * (gamma_ap - gamma_prima) * (h_w / B_star)
        gamma_calc = min(gamma_calc, gamma_ap)  

    # ------------------------------------------------------------------
    # 3. CONVERSIÓN DE ÁNGULOS Y DETECCIÓN DE CORTO PLAZO
    # ------------------------------------------------------------------
    phi = math.radians(phi_deg)
    psi = math.radians(psi_deg)
    eta = math.radians(eta_deg)
    
    es_corto_plazo = phi_deg < 0.1  

    # ------------------------------------------------------------------
    # 4. FACTORES DE CAPACIDAD DE CARGA Y CORRECCIÓN
    # ------------------------------------------------------------------
    if es_corto_plazo:
        Nq, Nc, Ngamma = 1.0, math.pi + 2, 0.0
    else:
        Nq = ((1 + math.sin(phi)) / (1 - math.sin(phi))) * math.exp(math.pi * math.tan(phi))
        Nc = (Nq - 1) / math.tan(phi)
        Ngamma = 2 * (Nq - 1) * math.tan(phi)

    D_cal = min(D, 2 * B_star)
    
    if es_corto_plazo:
        dq, dc, dgamma = 1.0, 1 + 2 * (1 / Nc) * math.atan(D_cal / B_star), 1.0
        
        iq = 1.0
        radicando = 1 - (H / (B_star * L_star * max(c, 0.001)))
        ic = 0.5 * (1 + math.sqrt(max(0, radicando)))
        igamma = 0.0
        
        tq, tc, tgamma = (1 - 0.5 * math.tan(psi))**5, 1 - 0.4 * psi, 0.0
        rq, rc, rgamma = 1.0, 1 - 0.4 * eta, 0.0
    else:
        dq = 1 + 2 * math.tan(phi) * (1 - math.sin(phi))**2 * math.atan(D_cal / B_star)
        dc = 1 + 2 * (Nq / Nc) * (1 - math.sin(phi))**2 * math.atan(D_cal / B_star)
        dgamma = 1.0
        
        iq = (1 - 0.7 * math.tan(delta))**3
        ic = iq - (1 - iq) / (Nc * math.tan(phi))
        igamma = (1 - math.tan(delta))**3
        
        tq = (1 - 0.5 * math.tan(psi))**5
        tc, tgamma = tq - (1 - tq) / (Nc * math.tan(phi)), tq
        
        rq = math.exp(-2 * eta * math.tan(phi))
        rc, rgamma = rq - (1 - rq) / (Nc * math.tan(phi)), rq

    sq = 1 + (B_star / L_star) * math.tan(phi)
    sc = 1 + 0.2 * (B_star / L_star)
    sgamma = 1 - 0.3 * (B_star / L_star)

    # ------------------------------------------------------------------
    # 5. CÁLCULO DE HUNDIMIENTO Y COEFICIENTE DE SEGURIDAD
    # ------------------------------------------------------------------
    termino_q = q * Nq * dq * iq * sq * tq * rq
    termino_c = c * Nc * dc * ic * sc * tc * rc
    termino_gamma = 0.5 * gamma_calc * B_star * Ngamma * dgamma * igamma * sgamma * tgamma * rgamma

    # Presión última de hundimiento
    p_vh = termino_q + termino_c + termino_gamma
    
    # Presión admisible teórica
    p_v_adm = p_vh / F_h_exigido  
    
    # Factor de seguridad real obtenido
    F_real = p_vh / p_v if p_v > 0 else float('inf')
    cumple_normativa = F_real >= F_h_exigido

    # ------------------------------------------------------------------
    # 6. IMPRESIÓN DE RESULTADOS
    # ------------------------------------------------------------------
    print("=" * 60)
    print("INFORME DE COMPROBACIÓN FRENTE A HUNDIMIENTO")
    print("=" * 60)
    print(f"Cargas actuantes:")
    print(f"  Fuerza Vertical (V)               : {V:.2f} kN")
    print(f"  Fuerza Horizontal (H)             : {H:.2f} kN")
    print(f"  Inclinación deducida (delta)      : {math.degrees(delta):.2f}º")
    print(f"  Presión real transmitida (p_v)    : {p_v:.2f} kPa")
    print("-" * 60)
    print(f"Presión última de hundimiento (p_vh): {p_vh:.2f} kPa")
    print(f"Presión admisible según norma       : {p_v_adm:.2f} kPa")
    print("-" * 60)
    print(f"C. DE SEGURIDAD EXIGIDO (F_exigido) : {F_h_exigido:.2f}")
    print(f"C. DE SEGURIDAD OBTENIDO (F_real)   : {F_real:.2f}")
    print("-" * 60)
    
    if cumple_normativa:
        print(">>> RESULTADO: LA CIMENTACIÓN CUMPLE LA NORMATIVA <<<")
    else:
        print(">>> ALERTA: LA CIMENTACIÓN NO CUMPLE (F_real < F_exigido) <<<")
    print("=" * 60)

    return F_real >= F_h_exigido

# =====================================================================
# EJEMPLO DE USO PRÁCTICO
# =====================================================================
if __name__ == "__main__":
    
    # Supongamos una zapata de 2m x 3m (B* x L* = 6 m2)
    # Recibe una carga vertical de 1500 kN y un empuje horizontal de 150 kN
    
    cumple = comprobacion_hundimiento(
        V = 1500.0,         # Fuerza vertical
        H = 150.0,          # Empuje horizontal
        c = 15.0,           
        phi_deg = 28.0,     
        gamma_ap = 18.0,    
        gamma_sat = 20.0,   
        D_w = 0.5,          
        D = 1.5,            
        B_star = 2.0,       
        L_star = 2.0,       
        psi_deg = 0.0,      
        eta_deg = 0.0,      
        F_h_exigido = 3.0   
    )