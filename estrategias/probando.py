import math
import random

# Simulador de operaciones con resultados predefinidos
class SimuladorOperaciones:
    def __init__(self, resultados):
        self.resultados = resultados
        self.indice = 0

    async def execute_trade(self, client, monto, duration):
        if self.indice >= len(self.resultados):
            return "fin"
        resultado = self.resultados[self.indice]
        self.indice += 1
        return "win" if resultado == 1 else "loss"

# Función principal kaizer_risk
async def kaizer_risk(client, base_amount, duration, balance, registro_operaciones, execute_trade):
    monto = base_amount
    monto_basico = 0
    profit = 0
    num_op = 0
    ganadas = 0
    perdidas = 0
    payout = 0.93
    pila_perd = 0
    acumula_temp = 0
    take_profit = 70
    stop_lost = -70
    profit_total = 0

    while True:
        result = await execute_trade(client, monto, duration)
       
        if result == "fin":
                print("✅ Fin de la secuencia simulada. Terminando estrategia.")
                return balance, False

        if result in ["false", "doji"]:
            registro_operaciones.append({
                "n": num_op + 1,
                "monto": monto,
                "resultado": result,
                "profit": profit,
                "esperado": num_op * base_amount * payout,
                "balance": balance
            })
            continue
        num_op += 1
        esperado = round(num_op * base_amount * payout, 2)
       
        registro_operaciones.append({
            "n": num_op,
            "monto": monto,
            "resultado": result,
            "profit": round(profit, 2),
            "esperado": esperado,
            "ganadas": ganadas,
            "perdidas": perdidas,
            "monto_basico": round(monto_basico, 2),
            "acumula_temp": round(acumula_temp, 2),
            "balance": balance
        })
        
        profit_total = 0
        for i, op in enumerate(registro_operaciones, 1):
            profit_total += op["profit"]        
            
        if profit >= take_profit:
                print("✅ Fin de la secuencia simulada. TAKE PROFIT !!.")
                return balance, True   
                
        if profit <= stop_lost:
                print("✅ Fin de la secuencia simulada. STOP LOSS !!.")
                return balance, True   
                
                
        if result == "win":
            ganadas += 1
            ganancia_op = round(monto * payout, 2)
            profit += ganancia_op
        elif result == "loss":
            perdidas += 1
            profit -= monto

        # Calcular próximo_monto
        if perdidas > 0:
            diferencia = esperado - profit
            ajuste = acumula_temp *- 0.45
            proximo_monto = round(monto + ajuste, 2)
        else:
            proximo_monto = base_amount

        # Calcular acumula_temp
        if monto_basico + profit < 0:
            acumula_temp = monto_basico + profit
            pila_perd +=1
        else:
            acumula_temp = 0
            pila_perd = 0

        # Actualizar monto_basico si corresponde
        if acumula_temp >= 0:
            if profit >= 0:
                monto_basico = profit
                monto = base_amount
            else:
                monto = proximo_monto
        else:
            if result == "loss":
                monto = base_amount
            elif result == "win":
                monto = proximo_monto



# Secuencia de resultados simulados
resultados_simulados = [
    1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1]

random.seed(12)
resultados_aleatorios = [random.choice([0, 1]) for _ in range(15)]

# Ejecutar simulación
import asyncio

async def main():
    registro = []
    simulador = SimuladorOperaciones(resultados_simulados)
    resultadoscorrida = True
    
    while resultadoscorrida:
       balance , resultadoscorrida = await kaizer_risk(
            client=None,
            base_amount=50,
            duration=60,
            balance=1000,
            registro_operaciones=registro,
            execute_trade=simulador.execute_trade
        )

    # Mostrar resultados
    for op in registro:
        print(f"Op {op['n']:02d} | Resultado: {op['resultado']:>4} | Monto: {op['monto']:>7.2f} | Profit: {op['profit']:>8.2f} | Esperado: {op['esperado']:>8.2f} | Perdidas: {op['perdidas']:>2} | Ganadas: {op['ganadas']:>2}")

asyncio.run(main())