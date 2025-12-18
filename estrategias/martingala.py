from capital import find_best_asset
import asyncio

async def estrategia_martingala(client, base_amount, duration, balance,registro_operaciones, execute_trade):
    intento = 1
    monto = base_amount * 2.10

    while intento <= 50:
        asset_name, direction = await find_best_asset(client,metodo_estructura="combinado")
        if not asset_name or not direction:
            print("⏳ Esperando activo válido...")
            await asyncio.sleep(10)
            continue

        print(f"📉 Martingala intento {intento} con monto: {monto:.2f}")
        balance, result, profit = await execute_trade(monto, asset_name, direction, duration)
        
        registro_operaciones.append({
            "resultado": result,
            "monto": monto,
            "profit": profit
        })


        if result == "Win":
            return balance, True

        monto *= 2.10
        intento += 1
        await asyncio.sleep(5)

    print("⛔ Martingala alcanzó el límite sin éxito.")
    return balance, False