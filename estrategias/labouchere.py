from capital import find_best_asset
import asyncio

async def estrategia_labouchere(client, base_amount, duration, balance, execute_trade):
    secuencia = [1, 2, 3]
    intento = 1

    while sum(secuencia) * base_amount <= 50 and len(secuencia) > 0:
        if len(secuencia) == 1:
            monto = secuencia[0] * base_amount
        else:
            monto = (secuencia[0] + secuencia[-1]) * base_amount

        asset_name, direction = await find_best_asset(client)
        if not asset_name or not direction:
            await asyncio.sleep(10)
            continue

        print(f"📉 Labouchere intento {intento} con monto: {monto:.2f} | Secuencia: {secuencia}")
        balance, result, _ = await execute_trade(monto, asset_name, direction, duration)

        if result == "Win":
            if len(secuencia) > 1:
                secuencia = secuencia[1:-1]
            else:
                secuencia = []
            return balance, True
        else:
            secuencia.append(secuencia[0] + secuencia[-1])
            intento += 1
            await asyncio.sleep(5)

    print("⛔ Labouchere agotado sin éxito.")
    return balance, False