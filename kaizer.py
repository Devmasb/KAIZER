# -*- coding: utf-8 -*-
import asyncio
from pyquotex.config import credentials
from pyquotex.stable_api import Quotex
from pyquotex.cloudflare_helper import get_cloudflare_cookies, refresh_cookies_periodically

from capital import find_best_asset, especialfind_best_asset
from estrategias.martingala2 import estrategia_martingala
from estrategias.labouchere import estrategia_labouchere
from estrategias.orcar_grid import estrategia_orcar_grid
from estrategias.hibrida_martingala_orcar import estrategia_hibrida
import time
import logging
import traceback
import subprocess
import os, json



# 🔧 Configuración general

MONTO_BASE = 1
ESTRATEGIA = "martingala"  # Opciones: martingala, labouchere, orcar_grid, hibrida
ESCALADO_FACTOR_GLOBAL = 1.6
TAKE_PROFIT_SESION = MONTO_BASE * 300 # 🎯 Objetivo de ganancia por sesión
STOP_LOSS_SESION = MONTO_BASE * -500# 🎯 Objetivo de ganancia por sesión
MONTO_MAXIMO = 2500.0  # Tope por operación
MULTIPLICADOR_CIERRE = 2.0  # Cierre cuando saldo ≥ pérdidas × multiplicador
COEFICIENTE_ESCALA = 2.0  # Puedes ajustar este valor según tu capital o riesgo
# 🔐 Autenticación
email, password = credentials()
#client = Quotex(email=email, password=password, lang="es")
client = Quotex(
        email="tradingderivcluster@gmail.com",
        password="Danydarien2020",
        lang="es"
    )
    
SIMULATED_RESULTS = [
    'P', 'P', 'P', 'G', 'G', 'G', 'P', 'G', 'P', 
    # ... puedes pegar aquí tu secuencia completa

]
SIM_INDEX = 0
SALDO_INICIAL = 1000.0

balance = SALDO_INICIAL
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


async def execute_trade_simulado(monto_operacion, asset_name, direction, duration):
    """Simula una operación usando la lista de resultados predefinidos."""
    global SIM_INDEX, balance

    if SIM_INDEX >= len(SIMULATED_RESULTS):
        print("✅ Secuencia de resultados consumida. Fin de la simulación.")
        exit(0)  # termina la ejecución del programa

    resultado = SIMULATED_RESULTS[SIM_INDEX]
    SIM_INDEX += 1

    if resultado == "G":
        profit = monto_operacion * 0.93
        balance += profit
        return balance, "Win", profit
    else:
        if monto_operacion > balance:
            print(f"⚠️ Saldo insuficiente. Balance: {balance:.2f}, requerido: {monto_operacion:.2f}")
            exit(0)
        balance -= monto_operacion
        return balance, "Loss", -monto_operacion



# 🎯 Selector de estrategia
estrategias = {
    "martingala": estrategia_martingala,
    "labouchere": estrategia_labouchere,
    "orcar_grid": estrategia_orcar_grid,
    "hibrida": estrategia_hibrida
}

# ⏱️ Esperar hasta apertura de la próxima vela
def esperar_apertura_vela():
    ahora = int(time.time())
    segundos_restantes = 60 - (ahora % 60)
    print(f"⏳ Esperando {segundos_restantes} segundos para apertura de vela...")
    time.sleep(segundos_restantes)

def esperar_antes_de_cierre_vela(margen_segundos=5):
    ahora = int(time.time())
    segundos_restantes = 60 - (ahora % 60)
    espera = max(0, segundos_restantes - margen_segundos)
    print(f"⏳ Esperando {espera} segundos para entrar {margen_segundos}s antes del cierre de vela...")
    time.sleep(espera)
# 📂 Verificación post-fallo con espera y revisión única
async def verificar_historial(client, asset, amount, direction):
    print("⏳ Esperando 60 segundos para verificar historial...")
    await asyncio.sleep(120)
    historial = await client.get_history()
    if not historial:
        print("⚠️ No se recibió historial.")
        return "NoConfirmada", 0.0

    operacion = historial[0]
    if (
        operacion.get("symbol") == asset and
       # operacion.get("amount") == amount and
        operacion.get("directionType") == direction
    ):
        try:
            profit = float(operacion.get("profitAmount", "0"))
        except:
            profit = 0.0

        if profit > 0:
            return "Win", profit
        elif profit < 0:
            return "Loss", profit
        else:
            return "Doji", 0.0

    print("❌ La última operación no coincide con la esperada.")
    return "NoConfirmada", 0.0

#bot de telegram
import requests

def enviar_resumen_telegram(stats, balance_final, ganancia_total, perdida_total, recuperacion_neta):
    TOKEN = "8218293709:AAHhtbiAsVtG3HHflIunyzgv5q2uP41F5DI"
    CHAT_ID = "1155988084"

    mensaje = (
        f"📊 *Resumen de sesión completada*\n"
        f"Sesiones realizadas: {stats['sesiones_realizadas']}\n"
        f"Ganadas: {stats['ganadas']} | Perdidas: {stats['perdidas']} | Doji: {stats['doji']}\n"
        f"Profit total: ${ganancia_total:.2f}\n"
        f"Pérdida total: ${perdida_total:.2f}\n"
        f"Recuperación neta: ${recuperacion_neta:.2f}\n"
        f"Balance final: ${balance_final:.2f}"
    )

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ Resumen enviado por Telegram.")
        else:
            print(f"❌ Error al enviar mensaje: {response.text}")
    except Exception as e:
        print(f"⚠️ Excepción al enviar mensaje: {e}")
# 📈 Ejecución de operación con verificación segura

def enviar_nota_telegram(notaabot):
    TOKEN = "8218293709:AAHhtbiAsVtG3HHflIunyzgv5q2uP41F5DI"
    CHAT_ID = "1155988084"

    mensaje = notaabot
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": None
    }

    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ Resumen enviado por Telegram.")
        else:
            print(f"❌ Error al enviar mensaje: {response.text}")
    except Exception as e:
        print(f"⚠️ Excepción al enviar mensaje: {e}")
# 📈 Ejecución de operación con verificación segura
async def execute_trade(amount, asset_name, direction, duration):
    print(f"\n📌 Lanzando operación: Activo = {asset_name} | Dirección = {direction} | Monto = {amount:.2f}")
    try:   
        status, buy_info = await client.buy(amount, asset_name, direction, duration)
        if not status or "id" not in buy_info:
            print("⚠️ No se recibió ID de operación. Activando verificación por historial...")
            resultado, profit = await verificar_historial(client, asset_name, amount, direction)
           # await client.reconnect() 
            balance = await client.get_balance()
            if resultado != "NoConfirmada":
                print(f"📂 Resultado desde historial: {resultado} | Profit: {profit:.2f}")
                return balance, resultado, profit
            else:
                print("❌ No se pudo confirmar la operación.")
                return balance, "Failed", 0.0

        operation_id = buy_info["id"]
        print(f"🆔 Operación confirmada con ID: {operation_id}")
        await asyncio.sleep(duration + 10)

        result = await client.check_win(operation_id)
        profit = client.get_profit()
        balance = await client.get_balance()

        if result is True:
            print(f"✅ Resultado: Ganancia | Profit: {profit:.2f}")
            return balance, "Win", profit
        elif result is False:
            print(f"❌ Resultado: Pérdida | Profit: {profit:.2f}")
            return balance, "Loss", profit
        else:
            print("⚪ Resultado ambiguo (Doji).")
            return balance, "Doji", 0.0

    except Exception as e:
        print(f"💥 Error inesperado durante la operación: {str(e)}")
        balance = await client.get_balance()
        return balance, "Error", 0.0
# ?? Ciclo principal del bot con Labouchere por sesión y Oscar's Grind adaptativo por operación
# ?? Ciclo principal del bot con Labouchere por sesión y Oscar's Grind adaptativo por operación
async def trade_loop():
    ESCALADO_FACTOR_GLOBAL = 1.6
    ESCALADO_FACTOR = 1.3
    SECUENCIA_SESIONES = [0.6, 1, 0.6, 1]
    MONTO_MAXIMO_OPERACION = 175.0
    MULTIPLICADOR_CIERRE = 1.3
    COEFICIENTE_ESCALA = 1.3
    DETENER_EN_POSITIVO = False  # bandera que puedes activar/desactivar
    RETOMAR_ESTADO = False
    MARTINGALA_ACTIVA = False
   
    with open("config.env") as f:
        for line in f:
            if line.startswith("COEFICIENTE_ESCALA="):
                COEFICIENTE_ESCALA = float(line.strip().split("=")[1])
                ESCALADO_FACTOR = COEFICIENTE_ESCALA 
                MULTIPLICADOR_CIERRE = COEFICIENTE_ESCALA

            if line.startswith("DETENER_EN_POSITIVO="):
                valor = line.strip().split("=")[1].lower()
                DETENER_EN_POSITIVO = True if valor == "true" else False

            if line.startswith("RETOMAR_ESTADO="):
                valor = line.strip().split("=")[1].lower()
                RETOMAR_ESTADO = True if valor == "true" else False      

    print("Coeficiente Escala cargado:", COEFICIENTE_ESCALA)
    TAKE_PROFIT_TOTAL  = 2 * COEFICIENTE_ESCALA * (SECUENCIA_SESIONES[0] + SECUENCIA_SESIONES[-1])
    resultados = []
    estadofind = True

    print("?? Conectando al servidor de Quotex...")
    cookies = await get_cloudflare_cookies()
    client.set_session(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
        cookies=json.dumps(cookies)
    )
    asyncio.create_task(refresh_cookies_periodically(client.set_session, interval=1800))       
    #client.set_account_mode("REAL")
    conectado, mensaje = await client.connect()
    if not conectado:
        print(f"? Error de conexión: {mensaje}")
        return "error"

    duration = 60
    balance = await client.get_balance()
    STOP_LOSS_TOTAL = -500003
   # STOP_LOSS_TOTAL = - 0.50 * balance
    initial_balance = balance
    print(f"\n🚀 Bot iniciado con saldo inicial: {initial_balance:.2f}")
    print(f"📊 Estrategia: LABOUCHERE POR SESIÓN + OSCAR'S GRIND ADAPTATIVO | Secuencia inicial: {SECUENCIA_SESIONES}\n")

    notaabot = (
        f"\n🚀 Bot iniciado con saldo inicial: {initial_balance:.2f}\n"
        f"📊 Estrategia: LABOUCHERE POR SESIÓN + OSCAR'S GRIND ADAPTATIVO | Secuencia inicial: {SECUENCIA_SESIONES}\n"
    )
    enviar_nota_telegram(notaabot)

    registro_operaciones = []
    stats = {
        "ganadas": 0, "perdidas": 0, "doji": 0, "errores": 0,
        "sesiones_realizadas": 0, "sesiones_finalizadas": 0
    }

    sesion_actual = 1
    profit_total = 0
    perdida_acumulada_sesion = 0
    nume_escalamientos = 0
    incremento_base = 0.15
    sesiones_perdidas_consecutivas = 0  # contador de sesiones perdidas consecutivas
    operaciones_perdidas_consecutivas = 0  # contador de operaciones perdidas consecutivas

    if RETOMAR_ESTADO and os.path.exists("estado.json"):
        with open("estado.json") as f:
            estado = json.load(f)
        sesion_actual = estado["sesion_actual"]
        SECUENCIA_SESIONES = estado["SECUENCIA_SESIONES"]
        COEFICIENTE_ESCALA = estado["COEFICIENTE_ESCALA"]
        profit_total = estado["profit_total"]
        perdida_acumulada_sesion = estado["perdida_acumulada_sesion"]
        operaciones_perdidas_consecutivas = estado["operaciones_perdidas_consecutivas"]
        registro_operaciones = estado["registro_operaciones"]
        stats = estado["stats"]
        print("🔄 Estado restaurado desde archivo, retomando operación...")
        enviar_nota_telegram(f"🔄 Estado restaurado desde archivo, retomando operación...")
    else:
        sesion_actual = 1
        profit_total = 0
        perdida_acumulada_sesion = 0
        operaciones_perdidas_consecutivas = 0
        stats = {"ganadas":0,"perdidas":0,"doji":0,"errores":0,"sesiones_realizadas":0,"sesiones_finalizadas":0}
        print("🆕 Inicio limpio, sin restaurar estado.")


        
    # nivel de sesiones ***********************************
    while len(SECUENCIA_SESIONES) > 0: 
        print(f"\n?? Iniciando sesión {sesion_actual}...")
        take_profit_sesion = COEFICIENTE_ESCALA * (SECUENCIA_SESIONES[0] + SECUENCIA_SESIONES[-1]) if len(SECUENCIA_SESIONES) > 1 else COEFICIENTE_ESCALA * SECUENCIA_SESIONES[0]
        take_profit_sesion = round(take_profit_sesion, 2)
        stop_loss_sesion = -take_profit_sesion
        unidad_base = round(take_profit_sesion / 2)
        unidad_base = max(unidad_base, 1)
        rendimiento = 0.5
        
        monto_operacion = min(unidad_base, MONTO_MAXIMO_OPERACION)

        saldo_sesion = 0
        operaciones_realizadas = 0
        perdida_acumulada = 0

        # nivel de operaciones *********************************
        while True: 
            print(f"\n?? Sesión {sesion_actual} | TP: {take_profit_sesion:.2f} | SL: {stop_loss_sesion:.2f} | Monto actual: {monto_operacion:.2f}")
            print(f"?? | Secuencia Actual: {SECUENCIA_SESIONES}\n")
            print(f"\n?? PATRÓN RESULTADOS: {resultados}")

            while True:
                print("\n?? Buscando mejor activo para operar...")
                mibalance = await client.get_balance()
                #esperar_antes_de_cierre_vela(0)
                asset_name, direction = await find_best_asset(client, metodo_estructura="combinado", estado=rendimiento)
                if not asset_name or not direction:
                    print("? No se encontró activo válido. Reintentando en 60 segundos...")
                    #await asyncio.sleep(10)
                    continue
                esperar_antes_de_cierre_vela(0)
                print('Trade normal')
                balance, result, profit = await execute_trade(monto_operacion, asset_name, direction, duration)

                if result in ["Doji", "Failed"]:
                    print(f"?? Operación inválida ({result}). Reintentando con nuevo activo y mismo monto...")
                    stats["doji"] += 1 if result == "Doji" else 0
                    stats["errores"] += 1 if result == "Failed" else 0
                    await asyncio.sleep(3)
                    continue

                break  # operación válida

            operaciones_realizadas += 1
            registro_operaciones.append({
                "sesion": sesion_actual,
                "operacion": operaciones_realizadas,
                "resultado": result,
                "monto": monto_operacion,
                "profit": profit
            })
            
            estado = {
                "sesion_actual": sesion_actual,
                "SECUENCIA_SESIONES": SECUENCIA_SESIONES,
                "COEFICIENTE_ESCALA": COEFICIENTE_ESCALA,
                "profit_total": profit_total,
                "perdida_acumulada_sesion": perdida_acumulada_sesion,
                "operaciones_perdidas_consecutivas": operaciones_perdidas_consecutivas,
                "registro_operaciones":registro_operaciones,
                "stats": stats
            }

            with open("estado.json", "w") as f:
                json.dump(estado, f)
                       

            resultados.append("G" if result == "Win" else "P")
            ganancia_total = sum(op["profit"] for op in registro_operaciones if op["resultado"] == "Win")
            perdida_total = sum(op["monto"] for op in registro_operaciones if op["resultado"] == "Loss")
            recuperacion_neta = ganancia_total - perdida_total
            if result == "Win":
                stats["ganadas"] += 1
                saldo_sesion += profit
                perdida_acumulada = max(perdida_acumulada - profit, 0)
                #monto_operacion = max(monto_operacion * ESCALADO_FACTOR_GLOBAL, unidad_base)
                monto_operacion = max(monto_operacion * ESCALADO_FACTOR_GLOBAL, unidad_base) if saldo_sesion >= 0 and MARTINGALA_ACTIVA == False  else unidad_base
                #monto_operacion = max(monto_operacion / ESCALADO_FACTOR_GLOBAL, unidad_base)
                estadofind = True
                operaciones_perdidas_consecutivas = 0
                MARTINGALA_ACTIVA = False      # desactiva martingala tras ganar

            elif result == "Loss":
                operaciones_perdidas_consecutivas += 1
                stats["perdidas"] += 1
                saldo_sesion -= monto_operacion
                perdida_acumulada += monto_operacion
                
                if operaciones_perdidas_consecutivas >= 2:
                    MARTINGALA_ACTIVA = True

                if MARTINGALA_ACTIVA:
                    aux_monto = max(abs(perdida_acumulada_sesion), unidad_base) if perdida_acumulada_sesion > 0 else max(abs(saldo_sesion), unidad_base) 
                    if operaciones_perdidas_consecutivas == 2:
                        # primera martingala suavizada
                        monto_operacion = round(aux_monto * 1.10, 2)
                    else:
                        # segunda martingala fuerte
                        monto_operacion = round(aux_monto * 1.25, 2)
                    # else:
                        # # si llega a la sexta pérdida, cerrar sesión
                        # print(f"\n❌ Martingala fallida, sesión {sesion_actual} cerrada como perdedora.")
                        # SECUENCIA_SESIONES.append(int(take_profit_sesion / COEFICIENTE_ESCALA))
                        # break  # salir del bucle de operaciones → sesión perdida
                else:
                    monto_operacion = unidad_base
                           
                monto_operacion = min(monto_operacion, MONTO_MAXIMO_OPERACION)
                estadofind = False 

            balance = await client.get_balance()
            profit_total = sum(op["profit"] for op in registro_operaciones)
            print(f"\n?? Balance actualizado: {balance:.2f}")
            print(f"?? Profit acumulado: {profit_total:.2f}")
            print(f"?? Saldo sesión: {saldo_sesion:.2f}")
            totales = stats["ganadas"] + stats["perdidas"]
            rendimiento = stats["ganadas"] /totales if totales > 0 else 0.5
            
            if profit_total >= TAKE_PROFIT_TOTAL:
                print(f"\n✅ Objetivo global alcanzado: Profit total {profit_total:.2f} ≥ {TAKE_PROFIT_TOTAL:.2f}. Deteniendo bot.")
                enviar_nota_telegram(f"Objetivo global alcanzado: Profit total {profit_total:.2f} ≥ {TAKE_PROFIT_TOTAL:.2f}. Bot detenido.")
                ganancia_total = sum(op["profit"] for op in registro_operaciones if op["resultado"] == "Win")
                perdida_total = sum(op["monto"] for op in registro_operaciones if op["resultado"] == "Loss")
                recuperacion_neta = ganancia_total - perdida_total
                print("\n📋 RESUMEN FINAL DE LA SESIÓN")
                print(f"📌 Sesiones realizadas: {stats['sesiones_realizadas']}")
                print(f"✅ Ganadas: {stats['ganadas']} | ❌ Perdidas: {stats['perdidas']} | Doji: {stats['doji']}")
                print(f"Profit total: ${profit_total:.2f}")
                print(f"📈 Ganancia total: ${ganancia_total:.2f} | Pérdida total: ${perdida_total:.2f}")
                print(f"💰 Recuperación neta: ${recuperacion_neta:.2f}")
                print(f"📈 Balance final: ${balance:.2f}")
                return {
                "estado": "finalizado",
                "balance_final": balance,
                "ganancia_total": ganancia_total,
                "perdida_total": perdida_total,
                "recuperacion_neta": recuperacion_neta,
                "stats": stats
                }

            if profit_total <= STOP_LOSS_TOTAL:
                print(f"\n❌ Stop Loss global alcanzado: Profit total {profit_total:.2f} ≤ {STOP_LOSS_TOTAL:.2f}. Deteniendo bot.")
                enviar_nota_telegram(f"Stop Loss global alcanzado: Profit total {profit_total:.2f} ≤ {STOP_LOSS_TOTAL:.2f}. Bot detenido.")
                ganancia_total = sum(op["profit"] for op in registro_operaciones if op["resultado"] == "Win")
                perdida_total = sum(op["monto"] for op in registro_operaciones if op["resultado"] == "Loss")
                recuperacion_neta = ganancia_total - perdida_total
                print("\n📋 RESUMEN FINAL DE LA SESIÓN")
                print(f"📌 Sesiones realizadas: {stats['sesiones_realizadas']}")
                print(f"✅ Ganadas: {stats['ganadas']} | ❌ Perdidas: {stats['perdidas']} | Doji: {stats['doji']}")
                print(f"Profit total: ${profit_total:.2f}")
                print(f"📈 Ganancia total: ${ganancia_total:.2f} | Pérdida total: ${perdida_total:.2f}")
                print(f"💰 Recuperación neta: ${recuperacion_neta:.2f}")
                print(f"📈 Balance final: ${balance:.2f}")              
                return {
                "estado": "finalizado",
                "balance_final": balance,
                "ganancia_total": ganancia_total,
                "perdida_total": perdida_total,
                "recuperacion_neta": recuperacion_neta,
                "stats": stats
                }


            if DETENER_EN_POSITIVO and profit_total >= -unidad_base:
                print(f"\n❌ Bandera DETENER_EN_POSITIVO activada y sesión cerrada en ganancia. Bot detenido de forma segura.")
                enviar_nota_telegram("Bandera DETENER_EN_POSITIVO activada y sesión cerrada en ganancia. Bot detenido de forma segura.")

                # 1. Ejecutar systemctl stop
                try:
                    resultado = subprocess.run(
                        ["sudo", "systemctl", "stop", "kaizer"],
                        capture_output=True,
                        text=True
                    )
                    print("🔧 Servicio detenido con systemctl:", resultado.stdout)
                except Exception as e:
                    print("⚠️ Error al detener servicio con systemctl:", e)

                # 2. Reescribir config.env para resetear la bandera
                try:
                    with open("config.env") as f:
                        lineas = f.readlines()
                    with open("config.env", "w") as f:
                        for linea in lineas:
                            if linea.startswith("DETENER_EN_POSITIVO="):
                                f.write("DETENER_EN_POSITIVO=false\n")
                            else:
                                f.write(linea)
                    print("📄 Configuración actualizada: DETENER_EN_POSITIVO=false")
                    enviar_nota_telegram("DETENER_EN_POSITIVO reiniciado a FALSE en config.env")
                except Exception as e:
                    print("⚠️ Error al actualizar config.env:", e)

                # 3. Calcular totales antes de salir
                ganancia_total = sum(op["profit"] for op in registro_operaciones if op["resultado"] == "Win")
                perdida_total = sum(op["monto"] for op in registro_operaciones if op["resultado"] == "Loss")
                recuperacion_neta = ganancia_total - perdida_total

                return {
                    "estado": "finalizado",
                    "balance_final": balance,
                    "ganancia_total": ganancia_total,
                    "perdida_total": perdida_total,
                    "recuperacion_neta": recuperacion_neta,
                    "stats": stats
                }
                
            if saldo_sesion >= take_profit_sesion:
                print(f"\n?? Take Profit alcanzado en sesión {sesion_actual} (+${saldo_sesion:.2f}).")
                if len(SECUENCIA_SESIONES) > 1:
                    SECUENCIA_SESIONES = SECUENCIA_SESIONES[1:-1]
                else:
                    SECUENCIA_SESIONES = []
                break

            if saldo_sesion <= stop_loss_sesion:
                print(f"\n?? Stop Loss alcanzado en sesión {sesion_actual} (–${abs(saldo_sesion):.2f}).")
                SECUENCIA_SESIONES.append(int(take_profit_sesion / COEFICIENTE_ESCALA))
                break

        stats["sesiones_realizadas"] += 1
        print(f"\n? Sesión {sesion_actual} finalizada | Resultado: {'G' if saldo_sesion >= 0 else 'P'} | Saldo neto: ${saldo_sesion:.2f}")

        notaabot = (
            f"\n🎯 Sesión {sesion_actual} finalizada | Resultado: {'G' if saldo_sesion >= 0 else 'P'} | Saldo neto: ${saldo_sesion:.2f}"
            f"📈 Profit acumulado: {profit_total:.2f}\n"
        )
        enviar_nota_telegram(notaabot)

        # ?? Control de sesiones perdidas consecutivas
        if saldo_sesion < 0:
            sesiones_perdidas_consecutivas += 1
            perdida_acumulada_sesion += abs(saldo_sesion)

        else:
            sesiones_perdidas_consecutivas = 0
            perdida_acumulada_sesion = max(perdida_acumulada_sesion - saldo_sesion, 0)
        
        with open("config.env") as f:
            for line in f:
                if line.startswith("DETENER_EN_POSITIVO="):
                     valor = line.strip().split("=")[1].lower()
                     DETENER_EN_POSITIVO = True if valor == "true" else False

        # ?? Escalón superior: dos sesiones perdidas consecutivas
        if sesiones_perdidas_consecutivas >= 2:
            nume_escalamientos +=1
            if nume_escalamientos > 2:
                MULTIPLICADOR_CIERRE *=1.5
                COEFICIENTE_ESCALA = MULTIPLICADOR_CIERRE
                nume_escalamientos = 1
                incremento_base += 0.05  # ejemplo: sube de 0.15 → 0.20 → 0.25

            SECUENCIA_SESIONES = [0.6, 1, 0.6, 1]  # reinicia secuencia
            COEFICIENTE_ESCALA *= (1+ nume_escalamientos * incremento_base)  
            margenganancia = abs(recuperacion_neta)*2/9
            peso_coef = 0.8
            peso_margen = 0.2
            COEFICIENTE_ESCALA = (
                COEFICIENTE_ESCALA 
                if COEFICIENTE_ESCALA * 0.8 > margenganancia  
                else (COEFICIENTE_ESCALA * peso_coef + margenganancia * peso_margen)
            )
            COEFICIENTE_ESCALA = max(ESCALADO_FACTOR, COEFICIENTE_ESCALA)            
            sesiones_perdidas_consecutivas = 0
            sesion_actual += 1
            
            print("\n?? Se han perdido dos sesiones consecutivas. Reiniciando secuencia con coeficiente aumentado.")
            notaabot = (
                f"Estrategia: LABOUCHERE POR SESIÓN + OSCAR'S GRIND ADAPTATIVO | PATRÓN RESULTADOS: {resultados}\n"
                f"\n Se han perdido dos sesiones consecutivas. Reiniciando secuencia con coeficiente aumentado. Nuevo coeficiente: {COEFICIENTE_ESCALA:.2f}\n"
                f" Estrategia: LABOUCHERE POR SESIÓN + OSCAR'S GRIND ADAPTATIVO | Secuencia inicial: {SECUENCIA_SESIONES}\n"
                
            )
            enviar_nota_telegram(notaabot)
            continue
        sesion_actual += 1
        # ?? Normalización progresiva del coeficiente (reduce 40%) SOLO al finalizar toda la secuencia
        if len(SECUENCIA_SESIONES) == 0 and COEFICIENTE_ESCALA > ESCALADO_FACTOR:
            temp = COEFICIENTE_ESCALA
            COEFICIENTE_ESCALA = max(ESCALADO_FACTOR, COEFICIENTE_ESCALA * 0.9) if perdida_acumulada_sesion > 0 else ESCALADO_FACTOR
            margenganancia = abs(recuperacion_neta)*2/11
            peso_coef = 0.8
            peso_margen = 0.2
            COEFICIENTE_ESCALA = COEFICIENTE_ESCALA if COEFICIENTE_ESCALA  <  margenganancia  else COEFICIENTE_ESCALA * peso_coef + margenganancia * peso_margen
            COEFICIENTE_ESCALA = max(ESCALADO_FACTOR, COEFICIENTE_ESCALA)            
            SECUENCIA_SESIONES = [0.6, 1, 0.6, 1]
            MULTIPLICADOR_CIERRE =max(ESCALADO_FACTOR, COEFICIENTE_ESCALA / ESCALADO_FACTOR)
            temp = temp / COEFICIENTE_ESCALA           
            nume_escalamientos = int(max(0, nume_escalamientos / temp))
            incremento_base = max(0.15, incremento_base / temp)
            print(f"\n Secuencia ganadora: reduciendo coeficiente a {COEFICIENTE_ESCALA:.2f}")
            enviar_nota_telegram(f"\n Secuencia ganadora: reduciendo coeficiente a {COEFICIENTE_ESCALA:.2f}") 
            
    stats["sesiones_finalizadas"] = sesion_actual - 1

    ganancia_total = sum(op["profit"] for op in registro_operaciones if op["resultado"] == "Win")
    perdida_total = sum(op["monto"] for op in registro_operaciones if op["resultado"] == "Loss")
    recuperacion_neta = ganancia_total - perdida_total

    print("\n📋 RESUMEN FINAL DEL DÍA")
    print(f"📌 Sesiones realizadas: {stats['sesiones_realizadas']}")
    print(f"✅ Ganadas: {stats['ganadas']} | ❌ Perdidas: {stats['perdidas']} | Doji: {stats['doji']}")
    print(f"Profit total: ${profit_total:.2f}")
    print(f"📈 Ganancia total: ${ganancia_total:.2f} | Pérdida total: ${perdida_total:.2f}")
    print(f"💰 Recuperación neta: ${recuperacion_neta:.2f}")
    print(f"📈 Balance final: ${balance:.2f}")

    enviar_resumen_telegram(stats, balance, ganancia_total, perdida_total, recuperacion_neta)

    return {
        "estado": "finalizado",
        "balance_final": balance,
        "ganancia_total": ganancia_total,
        "perdida_total": perdida_total,
        "recuperacion_neta": recuperacion_neta,
        "stats": stats
    }
# ?? Entrada principal
async def main():
    resultado = {
        "estado": "error",
        "balance_final": 0.0,
        "ganancia_total": 0.0,
        "perdida_total": 0.0,
        "recuperacion_neta": 0.0,
        "stats": {
            "ganadas": 0,
            "perdidas": 0,
            "doji": 0,
            "errores": 0
        }
    }

    try:
        resultado = await trade_loop()
        await client.close()
    except Exception as e:
        error_msg = f"⚠️ Error en main: {e}\n{traceback.format_exc()}"
        enviar_nota_telegram(error_msg)
        
        
    print("\n📋 RESUMEN FINAL DE EJECUCIÓN")
    print("────────────────────────────────────────────")
    print(f"📌 Estado: {resultado['estado'].upper()}")
    print(f"💰 Saldo final: {resultado['balance_final']:.2f}")
    print(f"📈 Ganancia total acumulada: {resultado['ganancia_total']:.2f}")
    print(f"📉 Pérdida total acumulada: {resultado['perdida_total']:.2f}")
    print(f"🔁 Recuperación neta: {resultado['recuperacion_neta']:.2f}")
    print("────────────────────────────────────────────")
    print(f"✅ Operaciones ganadas: {resultado['stats']['ganadas']}")
    print(f"❌ Operaciones perdidas: {resultado['stats']['perdidas']}")
    print(f"⚪ Doji: {resultado['stats']['doji']}")
    print(f"💥 Errores: {resultado['stats']['errores']}")
    print("────────────────────────────────────────────")

    input("\nPresiona Enter para cerrar la consola...")

if __name__ == "__main__":
    asyncio.run(main())