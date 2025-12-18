from capital import find_best_asset
import asyncio

async def estrategia_hibrida(client, base_amount, duration, balance,registro_operaciones, execute_trade):
    monto = base_amount * 2.25
    perdida_acumulada = 0.0
    ganancia_acumulada = 0.0
    contador_perdidas = 1
    intento = 1

    print("\n📊 Iniciando estrategia híbrida: Martingala (3) + Orcar Grid adaptativa")
    print(f"🔁 Monto inicial: {monto:.2f}")

    while True:
        asset_name, direction = await find_best_asset(client)
        if not asset_name or not direction:
            print("⏳ Esperando activo válido...")
            await asyncio.sleep(10)
            continue

        print(f"\n📌 Intento {intento} | Monto: {monto:.2f} | Estrategia: {'Martingala' if contador_perdidas < 4 else 'Orcar Grid'}")
        balance, result, profit = await execute_trade(monto, asset_name, direction, duration)
        registro_operaciones.append({
            "resultado": result,
            "monto": monto,
            "profit": profit
        })


        if result == "Win":
            ganancia_acumulada += profit
            recuperacion_neta = ganancia_acumulada - perdida_acumulada

            print(f"✅ Ganancia obtenida: {profit:.2f}")
            print(f"📈 Ganancia acumulada: {ganancia_acumulada:.2f} | 📉 Pérdida acumulada: {perdida_acumulada:.2f}")
            print(f"🔁 Recuperación neta: {recuperacion_neta:.2f}")

            if ganancia_acumulada >= perdida_acumulada and ganancia_acumulada >= base_amount:
                print("🎯 Recuperación completa. Reiniciando al monto base.")
                return balance, True
            elif profit > 0:
                monto = max(base_amount, monto * 0.75)
                print(f"↘️ Reducción parcial del monto: {monto:.2f}")
            else:
                print(f"↘️ Operación neutra. Se mantiene el mismo monto: {monto:.2f}")
                
                
        elif result == "Loss":
            print(f"❌ Pérdida registrada: {monto:.2f}")
            contador_perdidas += 1

            if contador_perdidas <= 3:
                perdida_acumulada += monto
                monto = base_amount * (2 ** contador_perdidas)
                print(f"📉 Martingala activa (intento {contador_perdidas}) | Nuevo monto: {monto:.2f}")
            else:
                perdida_acumulada += monto
                monto *= 1.25
                print(f"📉 Orcar Grid activa | Pérdida acumulada: {perdida_acumulada:.2f} | Nuevo monto: {monto:.2f}")

        elif result in ["Doji", "Failed", "Error"]:
            print(f"⚠️ Resultado no concluyente ({result}). Reintentando con mismo monto.")

        intento += 1
        await asyncio.sleep(5)

        if monto > 500:
            print("⛔ Monto máximo alcanzado sin recuperación. Estrategia fallida.")
            return balance, False