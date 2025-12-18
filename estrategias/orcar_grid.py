from capital import find_best_asset
import asyncio

async def estrategia_orcar_grid(client, base_amount, duration, balance,registro_operaciones, execute_trade):
    monto = round(base_amount * 1.25)
    perdida_acumulada = 0.0
    ganancia_acumulada = 0.0
    intento = 1

    print(f"\n📊 Iniciando estrategia Orcar Grid adaptativa")
    print(f"🔁 Monto inicial: {monto:.2f}")

    while True:
        asset_name, direction = await find_best_asset(client,metodo_estructura="combinado")
        if not asset_name or not direction:
            print("⏳ Esperando activo válido...")
            await asyncio.sleep(10)
            continue

        print(f"\n📉 Orcar Grid intento {intento} | Monto: {monto:.2f}")
        balance, result, profit = await execute_trade(monto, asset_name, direction, duration)
        
        registro_operaciones.append({
            "resultado": result,
            "monto": monto,
            "profit": profit
        })

        if result == "Win":
            ganancia_acumulada += profit
            print(f"✅ Ganancia: {profit:.2f} | Ganancia acumulada: {ganancia_acumulada:.2f}")

            if ganancia_acumulada >= perdida_acumulada and ganancia_acumulada >= base_amount:
                print("🎯 Recuperación completa. Reiniciando al monto base.")
                return balance, True
            elif profit > 0:
                monto = max(base_amount, monto * 0.85)
                print(f"↘️ Reducción parcial del monto: {monto:.2f}")
            else:
                print(f"↘️ Operación neutra. Se mantiene el mismo monto: {monto:.2f}")

        elif result == "Loss":
            perdida_acumulada += monto
            print(f"❌ Pérdida: {monto:.2f} | Pérdida acumulada: {perdida_acumulada:.2f}")
            monto *= 1.25
            print(f"🔺 Aumento del monto: {monto:.2f}")

        elif result in ["Doji", "Failed", "Error"]:
            print(f"⚠️ Resultado no concluyente ({result}). Reintentando con mismo monto.")
        
        intento += 1
        await asyncio.sleep(5)

        # Límite de seguridad
        if monto > 11000:
            print("⛔ Monto máximo alcanzado sin recuperación. Estrategia fallida.")
            return balance, False
            
            
            