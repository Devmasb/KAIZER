import asyncio
import random

# Simulador de activos y direcciones
async def find_best_asset(client, modo, filtro):
    return "EURUSD", "CALL"

# Simulador de operaciones con resultados predefinidos
class SimuladorTrade:
    def __init__(self, resultados):
        self.resultados = resultados
        self.indice = 0

    async def execute_trade(self, monto, asset_name, direction, duration):
        if self.indice >= len(self.resultados):
            return 1000, "Fin", 0.0
        resultado = self.resultados[self.indice]
        self.indice += 1

        if resultado == "Win":
            profit = round(monto * 0.93, 2)
        elif resultado == "Loss":
            profit = -monto
        else:
            profit = 0.0

        return 1000, resultado, profit

# Estrategia OrcarGrid adaptativa
async def estrategia_orcar_grid(client, base_amount, duration, balance, registro_operaciones, espacios, execute_trade):
    monto = base_amount
    monto_perdidaconsecutiva = base_amount
    perdida_acumulada = monto
    ganancia_acumulada = 0.0
    intento = 0
    take_profit = duration
    stop_lost = balance
    profit_total = 0
    ganaparcial=0
    countduos = 0
    contandoespacioentreduos = espacios
    


    #print(f"\n📊 Iniciando estrategia Orcar Grid adaptativa")
    #print(f"🔁 Monto inicial: {monto:.2f}")

    while True:
        intento += 1
        asset_name, direction = await find_best_asset(client, "combinado", False)
        #print(f"\n📉 Orcar Grid intento {intento} | Monto: {monto:.2f}")
        balance, result, profit = await execute_trade(monto, asset_name, direction, duration)

        if result == "Fin":
            print("✅ Fin de la secuencia simulada. Terminando OrcarGrid.")
            return contandoespacioentreduos,False, False

        registro_operaciones.append({
            "estrategia": "orcar_grid",
            "intento": intento,
            "monto": monto,
            "resultado": result,
            "profit": profit,
            "countduos": countduos
            
        })
        
        profit_total = 0
        for i, op in enumerate(registro_operaciones, 1):
             profit_total += op["profit"]
             
        # if profit_total >= take_profit:
           # # print(f"✅ Fin de la secuencia simulada. TAKE PROFIT !!. | Ganancia acumulada: {profit_total:.2f}")
            # return contandoespacioentreduos,True, True 
        
        # if profit_total <= stop_lost:
           # # print(f"✅ Fin de la secuencia simulada. STOP LOSS !!. | Ganancia acumulada: {profit_total:.2f}")
            # return contandoespacioentreduos,False, True 
        
        
        if result == "Win":
            contandoespacioentreduos+=1
            ganaparcial+=1
            ganancia_acumulada += profit
            stop_lost += profit
            #print(f"✅ Ganancia: {profit:.2f} | Ganancia acumulada: {ganancia_acumulada:.2f}")
            # if ganancia_acumulada >= perdida_acumulada and ganancia_acumulada >= base_amount:
                # #print("🎯 Recuperación completa. Reiniciando al monto base.")
                # return True, True
            if ganaparcial < 2:
                if contandoespacioentreduos > 10:
                    #monto *= 1.50
                    # monto = base_amount
                   if  stop_lost < 0:
                      print(f"Perdida acum: {stop_lost:.2f}")
                      monto = stop_lost * -1.93
                   else:
                     monto *= 1.93
                else:
                    
                    monto = base_amount
                    
            else:
               monto = base_amount
               #intento = 0 
               ganaparcial =0
               contandoespacioentreduos=0
               countduos+=1
                #return True, True
                
                
        elif result == "Loss":
            #intento += 1
            perdida_acumulada += monto
            stop_lost -= monto
            contandoespacioentreduos+=1
            # monto_perdidaconsecutiva *= 1.55
            # monto = monto_perdidaconsecutiva
            ganaparcial=0
            monto = base_amount
          
           # print(f"❌ Pérdida: {monto:.2f} | Pérdida acumulada: {perdida_acumulada:.2f}")
        elif result in ["Doji", "Failed", "Error"]:
            print(f"⚠️ Resultado no concluyente ({result}). Reintentando con mismo monto.")

        # if result == "Win":
            # ganancia_acumulada += profit
            # ganaparcial+=1
          # #  print(f"✅ Ganancia: {profit:.2f} | Ganancia acumulada: {ganancia_acumulada:.2f}")

            # # if ganancia_acumulada >= perdida_acumulada and ganancia_acumulada >= base_amount:
                # # print("🎯 Recuperación completa. Reiniciando al monto base.")
                # # return balance, True
            # if profit > 0:
                # monto = max(base_amount, monto * 0.85)
               # # print(f"↘️ Reducción parcial del monto: {monto:.2f}")
            # if ganaparcial == 2:
                # countduos+=1
                
        # elif result == "Loss":
            # perdida_acumulada += monto
            # ganaparcial=0
            # #print(f"❌ Pérdida: {monto:.2f} | Pérdida acumulada: {perdida_acumulada:.2f}")
            # monto *= 1.15
            # #print(f"🔺 Aumento del monto: {monto:.2f}")

        
        
        if intento > client:
            #print(f"📉 Intentos máximo alcanzados sin recuperación. Estrategia fallida con monto: {profit_total:.2f}")
           # print("⛔ Intentos máximo alcanzados sin recuperación. Estrategia fallida.")
            return contandoespacioentreduos,balance, True
            
        if monto > 200000:
           # print(f"⛔ Monto máximo alcanzado sin recuperación. Estrategia fallida. con monto: {profit_total:.2f}")
            return contandoespacioentreduos,balance, True


# Estrategia Martingala con fallback a OrcarGrid
async def estrategia_martingala(client, base_amount, duration, balance, registro_operaciones,espacios, execute_trade):
    monto_base = base_amount / 2.30
    monto = monto_base
    intento = 1
    perdidas_acumuladas = 0
    take_profit = duration
    stop_lost = balance
    profit_total = 0
    contandoespacioentreduos = espacios

    while True:
        # while intento <= 2:
            # asset_name, direction = await find_best_asset(client, "combinado", False)
            # monto *= 2.30
            # #print(f"📉 Martingala intento {intento} con monto: {monto:.2f}")
            # balance, result, profit = await execute_trade(monto, asset_name, direction, duration)
            # profit_total = 0
            # for i, op in enumerate(registro_operaciones, 1):
               # profit_total += op["profit"]

            # if result == "Fin":
               # # print("✅ Fin de la secuencia simulada. Terminando estrategia.")
                # return balance, False
             
            # if profit_total >= take_profit:
               # # print(f"✅ Fin de la secuencia simulada. TAKE PROFIT !!. | Ganancia acumulada: {profit_total:.2f}")
                # return balance, True      
                          
            # if profit_total <= stop_lost:
               # # print(f"✅ Fin de la secuencia simulada. STOP LOSS !!. | Ganancia acumulada: {profit_total:.2f}")
                # return balance, True      
                
            # registro_operaciones.append({
                # "estrategia": "martingala",
                # "intento": intento,
                # "monto": monto,
                # "resultado": result,
                # "profit": profit
            # })

            # if result == "Win":
                # if profit > 0:
                    # #print("✅ Martingala exitosa, reiniciando ciclo.")
                    # monto_base = base_amount / 2.30
                    # monto = monto_base
                    # intento = 1
                    # perdidas_acumuladas = 0
                
                # else:
                    # #print(f"↘️ Operación neutra. Se mantiene el mismo monto: {monto:.2f}")
                    # perdidas_acumuladas += monto
                    # monto /= 2
                    # continue
            # elif result in ["Doji", "Failed", "Error"]:
                # #print(f"⚠️ Resultado no concluyente ({result}). Reintentando con mismo monto.")
                # perdidas_acumuladas += monto
                # monto /= 2
                # continue

            # perdidas_acumuladas += monto
            # intento += 1
                   
        #print(f"📉 Activando OrcarGrid para recuperar ${perdidas_acumuladas:.2f}...")
        losduos,balance, success = await estrategia_orcar_grid(
            client, base_amount, duration, balance, registro_operaciones, espacios, execute_trade
        )
        contandoespacioentreduos = losduos
        if success:
            #print("🔁 OrcarGrid logró recuperar, reiniciando Martingala.")
 
            return contandoespacioentreduos,balance, True
            
        else:
           # print("⛔ OrcarGrid no logró recuperar, finalizando estrategia.")
            return contandoespacioentreduos,balance, False

# Ejecutar prueba
async def main():
    resultados_simulados = [
  1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1,
  1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1,
  1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1,
  1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1,
  1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1,
  1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1,
  1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1,
  1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1,
  1, 1, 0, 0, 1, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    
    #random.seed(20)
    resultados_aleatorios = [random.choice([0, 1]) for _ in range(3000)]
    resultados = ["Win" if r == 1 else "Loss" for r in resultados_aleatorios]
    simulador = SimuladorTrade(resultados)
    registro = []
    sesiones=0
    ganadas=0
    perdidas=0
    profit_general=0
    salida = True
    saldocuenta=-100
    
    base_amountt=1
    takeprofit=400
    stoploss=0
    countduosgeneral = 0
    
    resultadoscorrida = True
    contandoespacioentreduos = 0
    
   # print("\n📋 CORRIDA GENERAL:")
   # print(f"PROBABILIDAD: {resultados}")
    while resultadoscorrida:
        registro = []         
        sesiones+=1
        print(f"\n📋 NUEVA SESION: {sesiones:.2f}")
        parametros = {
            "client": 9,
            "base_amount": base_amountt,
            "duration": takeprofit,
            "balance": stoploss,
            "registro_operaciones": registro,
            "espacios": contandoespacioentreduos,
            "execute_trade": simulador.execute_trade
        }

        losduos,salida, resultadoscorrida = await estrategia_martingala(**parametros)

        contandoespacioentreduos = losduos

       # 📊 Tabla resumen
        
        
        print(f"{'Op':>3} {'Estrategia':>12} {'Intento':>7} {'Monto':>8} {'Resultado':>10} {'Profit':>9} {'Acumulado':>10} {'Contadorseguidas':>10}")
        profit_total = 0
        duosseguidos = 0
        for i, op in enumerate(registro, 1):
            profit_total += op["profit"]
            duosseguidos += op['countduos']
            print(f"{i:>3} {op['estrategia']:>12} {op['intento']:>7} {op['monto']:>8.2f} {op['resultado']:>10} {op['profit']:>9.2f} {profit_total:>10.2f} {op['countduos']:10.2f}")
            
        profit_general += profit_total
        if duosseguidos > 0:
          countduosgeneral+=1 
        if profit_total >= 0:
            ganadas +=1
            
        if profit_total <= 0:
            perdidas += 1
        stoploss = profit_total
        # if salida == False:
           # base_amountt *= 1.20
           # takeprofit *= 1.20
           # stoploss *= 3
            # # print("\n📋 RESULTADOS:-----------*******************************************************************************************************************---------")
        # else:
            # if profit_general > 0:
                # base_amountt = 1
                # takeprofit=4
                # stoploss=-3
            # else: 
               # if profit_total > base_amountt:
                   # base_amountt = profit_total * 0.25
                   # takeprofit = profit_total * 0.8
                   # stoploss =  profit_total* -1
        print(f"📋 profit_general: {profit_general:.2f}")
        
        # if profit_general < saldocuenta:
            # print("\n📋 SE QUEMÓ LA CUENTA:--------------------")
            # break
        # if profit_general > saldocuenta * -0.15:
            # print("\n📋 Mes cumplido a hotel:--------------------")
            # break    
    
    print("\n📋 RESULTADOS:--------------------")
    print(f"📋 sesiones: {sesiones:.2f} | Profit: {profit_general:.2f} | ✅ Sesiones con ganadas seguidas:  {countduosgeneral:.2f} |  ✅ Sesiones exitosas:  {ganadas:.2f} | ❌ Sesiones Perdidas: {perdidas:.2f}")
   
           
           # print(f"{i:>3} {op['estrategia']:>12} {op['intento']:>7} {op['monto']:>8.2f} {op['resultado']:>10} {op['profit']:>9.2f} {profit_total:>10.2f}")

asyncio.run(main())