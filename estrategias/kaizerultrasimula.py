import random

# Parametros
DIAS_OPERACION = 24
SESIONES_MAXIMAS_POR_DIA = 5
OPERACIONES_POR_SESION = 10
MONTO_BASE = 1
ESCALADO_FACTOR = 2.93
PAYOUT = 0.93
PROB_GANAR = 0.52

# Metricas acumuladas
ganancia_total = 0
drawdown_max = 0
sesiones_totales = 0
dias_cerrados_anticipadamente = 0
dias_con_recuperacion = 0
dias_con_ganancia = 0
dias_con_perdida = 0
dias_consecutivos_perdida = 0
max_dias_consecutivos_perdida = 0
sesiones_consecutivas_perdida = 0
total_rachas_sesion_perdida = 0
cantidad_rachas_sesion_perdida = 0

# Generador de operaciones simuladas
def generar_operaciones(probabilidad, n):
    return ['G' if random.random() < probabilidad else 'P' for _ in range(n)]

# Aplicar martingala en ultimas 3 operaciones
def aplicar_martingala(operaciones_finales, monto_inicial, sesion_log):
    saldo = 0
    monto = monto_inicial
    for i, resultado in enumerate(operaciones_finales, start=8):
        if resultado == 'G':
            ganancia = monto * PAYOUT
            saldo += ganancia
            sesion_log.append((i + 1, resultado, monto, ganancia, 0))
            monto = monto_inicial
        else:
            saldo -= monto
            sesion_log.append((i + 1, resultado, monto, 0, monto))
            monto *= 2
    return saldo

# Simulacion por dia
for dia in range(1, DIAS_OPERACION + 1):
    print(f"\n====== DIA {dia} ======")
    saldo_dia = 0
    sesiones_realizadas = 0

    for sesion in range(1, SESIONES_MAXIMAS_POR_DIA + 1):
        operaciones = generar_operaciones(PROB_GANAR, OPERACIONES_POR_SESION)
        saldo_sesion = 0
        sesion_log = []
        escalamiento_activo = operaciones[:3] != ['G', 'P', 'G']
        escalado_realizado = False

        for i in range(OPERACIONES_POR_SESION):
            if i == 0:
                monto = MONTO_BASE
            elif escalamiento_activo and not escalado_realizado and operaciones[i - 1] == 'G' and operaciones[i] == 'G':
                monto = MONTO_BASE * ESCALADO_FACTOR
                escalado_realizado = True
            else:
                monto = MONTO_BASE

            if i >= 7 and operaciones[:7].count('P') >= 5:
                break

            if operaciones[i] == 'G':
                ganancia = monto * PAYOUT
                saldo_sesion += ganancia
                sesion_log.append((i + 1, 'G', monto, ganancia, 0))
            else:
                saldo_sesion -= monto
                sesion_log.append((i + 1, 'P', monto, 0, monto))

            # Cierre anticipado de sesion si despues de la quinta operacion hay ganancia
            # if i == 5 and saldo_sesion > 0:
                # print(f"\nCierre anticipado de la sesion {sesion} con ganancia parcial: ${saldo_sesion:.2f}")
                # break

        if operaciones[:7].count('P') >= 5:
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
        saldo_dia += saldo_sesion
        sesiones_realizadas += 1
        sesiones_totales += 1

        # Rachas de sesiones perdidas
        if saldo_sesion < 0:
            sesiones_consecutivas_perdida += 1
        else:
            if sesiones_consecutivas_perdida > 0:
                total_rachas_sesion_perdida += sesiones_consecutivas_perdida
                cantidad_rachas_sesion_perdida += 1
            sesiones_consecutivas_perdida = 0

        # Imprimir trazabilidad
        print(f"\nSesion {sesion} - Resultado: {'G' if saldo_sesion >= 0 else 'P'} | Saldo: ${saldo_sesion:.2f}")
        print("Operacion | Resultado | Monto | Ganancia | Perdida")
        for op_num, res, monto, ganancia, perdida in sesion_log:
            print(f"{op_num:^9}| {res:^9} | ${monto:<6.2f}| ${ganancia:<8.2f}| ${perdida:<8.2f}")

        if sesion == 3 and saldo_dia > 0:
            print(f"\nCierre anticipado del dia {dia} con ganancia: ${saldo_dia:.2f}")
            dias_cerrados_anticipadamente += 1
            break

    if sesiones_realizadas == 5:
        dias_con_recuperacion += 1

    if saldo_dia >= 0:
        dias_con_ganancia += 1
        dias_consecutivos_perdida = 0
    else:
        dias_con_perdida += 1
        dias_consecutivos_perdida += 1
        max_dias_consecutivos_perdida = max(max_dias_consecutivos_perdida, dias_consecutivos_perdida)

    print(f"\nResumen del dia {dia}: Sesiones realizadas: {sesiones_realizadas}, Ganancia neta: ${saldo_dia:.2f}")

# Cierre de racha si quedo abierta
if sesiones_consecutivas_perdida > 0:
    total_rachas_sesion_perdida += sesiones_consecutivas_perdida
    cantidad_rachas_sesion_perdida += 1

promedio_rachas_sesion_perdida = (
    total_rachas_sesion_perdida / cantidad_rachas_sesion_perdida
    if cantidad_rachas_sesion_perdida > 0 else 0
)

# Resumen final
roi_promedio = ganancia_total / sesiones_totales
print("\n====== RESUMEN GENERAL ======")
print(f"Dias simulados: {DIAS_OPERACION}")
print(f"Sesiones totales realizadas: {sesiones_totales}")
print(f"Dias cerrados anticipadamente (tras 3 sesiones con ganancia): {dias_cerrados_anticipadamente}")
print(f"Dias con recuperacion (5 sesiones completas): {dias_con_recuperacion}")
print(f"Dias con ganancia: {dias_con_ganancia}")
print(f"Dias con perdida: {dias_con_perdida}")
print(f"Maximo de dias consecutivos en perdida: {max_dias_consecutivos_perdida}")
print(f"Promedio de sesiones consecutivas en perdida: {promedio_rachas_sesion_perdida:.2f}")
print(f"ROI total: ${ganancia_total:.2f}")
print(f"ROI promedio por sesion: ${roi_promedio:.2f}")
print(f"Drawdown maximo por sesion: ${drawdown_max:.2f}")