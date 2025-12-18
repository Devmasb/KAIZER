import random

# Parametros
NUM_SESIONES = 50
OPERACIONES_POR_SESION = 10
MONTO_BASE = 1.0
ESCALADO_FACTOR = 1.93
PAYOUT = 0.93
RETENCION = 0.50
PROB_GANAR = 0.55  # Probabilidad de acierto por operacion

# Metricas acumuladas
ganancia_total = 0
drawdown_max = 0

def generar_operaciones(probabilidad, n):
    return ['G' if random.random() < probabilidad else 'P' for _ in range(n)]

def aplicar_martingala(operaciones_finales, monto_inicial, sesion_log):
    saldo = 0
    monto = monto_inicial
    for i, resultado in enumerate(operaciones_finales, start=8):
        if resultado == 'G':
            ganancia = monto * PAYOUT
            saldo += ganancia
            sesion_log.append((i, resultado, monto, ganancia, 0))
            monto = monto_inicial
        else:
            saldo -= monto
            sesion_log.append((i, resultado, monto, 0, monto))
            monto *= 2
    return saldo

for sesion in range(1, NUM_SESIONES + 1):
    operaciones = generar_operaciones(PROB_GANAR, OPERACIONES_POR_SESION)
    saldo_sesion = 0
    sesion_log = []

    escalamiento_activo = operaciones[:3] != ['G', 'P', 'G']

    # Operaciones 1 a 3
    for i in range(3):
        monto = MONTO_BASE
        if operaciones[i] == 'G':
            ganancia = monto * PAYOUT
            saldo_sesion += ganancia
            sesion_log.append((i + 1, 'G', monto, ganancia, 0))
        else:
            saldo_sesion -= monto
            sesion_log.append((i + 1, 'P', monto, 0, monto))

    # Operaciones 4 a 7
    for i in range(3, 7):
        if escalamiento_activo and operaciones[i - 1] == 'G':
            monto = MONTO_BASE * ESCALADO_FACTOR
        else:
            monto = MONTO_BASE

        if operaciones[i] == 'G':
            ganancia = monto * PAYOUT
            saldo_sesion += ganancia
            sesion_log.append((i + 1, 'G', monto, ganancia, 0))
        else:
            saldo_sesion -= monto
            sesion_log.append((i + 1, 'P', monto, 0, monto))

    # Evaluar si aplicar martingala en las ultimas 3
    primeras_7 = operaciones[:7]
    if primeras_7.count('P') >= 5:
        saldo_sesion += aplicar_martingala(operaciones[7:], MONTO_BASE, sesion_log)
    else:
        for i in range(7, 10):
            monto = MONTO_BASE
            if operaciones[i] == 'G':
                ganancia = monto * PAYOUT
                saldo_sesion += ganancia
                sesion_log.append((i + 1, 'G', monto, ganancia, 0))
            else:
                saldo_sesion -= monto
                sesion_log.append((i + 1, 'P', monto, 0, monto))

    ganancia_total += saldo_sesion
    drawdown_max = min(drawdown_max, saldo_sesion)

    # Imprimir trazabilidad de la sesion
    print(f"\nSesion #{sesion} - Resultado: {'G' if saldo_sesion >= 0 else 'P'} | Saldo: ${saldo_sesion:.2f}")
    print("Operacion | Resultado | Monto | Ganancia | Perdida")
    for op_num, res, monto, ganancia, perdida in sesion_log:
        print(f"{op_num:^9}| {res:^9} | ${monto:<6.2f}| ${ganancia:<8.2f}| ${perdida:<8.2f}")

# Resumen final
roi_promedio = ganancia_total / NUM_SESIONES
print("\nRESUMEN DE LA SIMULACION")
print(f"Sesiones simuladas: {NUM_SESIONES}")
print(f"ROI total: ${ganancia_total:.2f}")
print(f"ROI promedio por sesion: ${roi_promedio:.2f}")
print(f"Drawdown maximo por sesion: ${drawdown_max:.2f}")