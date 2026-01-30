import time
import random
import asyncio
from pyquotex.config import credentials
from pyquotex.stable_api import Quotex
from indicators import TrendVolumeAnalyzer
from pyquotex.utils.indicators import TechnicalIndicators

# 🔍 Detectar pivotes clásicos
def detectar_pivotes(candles, profundidad=2):
    resistencias = []
    soportes = []
    for i in range(profundidad, len(candles) - profundidad):
        h = candles[i]['high']
        l = candles[i]['low']
        if all(h > candles[i - j]['high'] and h > candles[i + j]['high'] for j in range(1, profundidad + 1)):
            resistencias.append(h)
        if all(l < candles[i - j]['low'] and l < candles[i + j]['low'] for j in range(1, profundidad + 1)):
            soportes.append(l)
    return resistencias, soportes

# 🔍 Detectar fractales (estructura de 5 velas)
def detectar_fractales(candles):
    fractales_alcistas = []
    fractales_bajistas = []
    for i in range(2, len(candles) - 2):
        lows = [candles[i - j]['low'] for j in range(1, 3)] + [candles[i + j]['low'] for j in range(1, 3)]
        highs = [candles[i - j]['high'] for j in range(1, 3)] + [candles[i + j]['high'] for j in range(1, 3)]
        centro_low = candles[i]['low']
        centro_high = candles[i]['high']
        if all(centro_low < l for l in lows):
            fractales_alcistas.append(centro_low)
        if all(centro_high > h for h in highs):
            fractales_bajistas.append(centro_high)
    return fractales_alcistas, fractales_bajistas

# 🔗 Intersección de niveles con tolerancia
def intersectar_niveles(niveles_a, niveles_b, tolerancia=0.0003):
    combinados = []
    for nivel_a in niveles_a:
        for nivel_b in niveles_b:
            if abs(nivel_a - nivel_b) == 0: # sustituir el 0 por tolerancia para permitir mas niveles
                combinados.append((nivel_a + nivel_b) / 2)
    return combinados

# 📐 Margen dinámico adaptado al activo
def calcular_margen_dinamico(candles, factor=0.1):
    rangos = [abs(c['high'] - c['low']) for c in candles[-10:]]
    return sum(rangos) / len(rangos) * factor

# ✅ Confirmar ruptura de nivel
def confirmar_ruptura(cierre_actual, niveles, direccion, margen):
    if direccion == "call":
        return any(cierre_actual > nivel + margen for nivel in niveles)
    elif direccion == "put":
        return any(cierre_actual < nivel - margen for nivel in niveles)
    return False
    
def confirmar_rupturacruce(candle, niveles, direccion, margen):
    """
    candle: diccionario con 'open', 'close', 'high', 'low'
    niveles: lista de niveles clave
    direccion: 'call' o 'put'
    margen: tolerancia para evitar falsos rompimientos
    
    """
    for nivel in niveles:
        if direccion == "call":
            # Apertura o mínimo debajo del nivel, cierre arriba
            if (candle['open'] < nivel) and candle['close'] > nivel:
                return True
        elif direccion == "put":
            # Apertura o máximo encima del nivel, cierre abajo
            if (candle['open'] > nivel) and candle['close'] < nivel:
                return True
    return False



def filtrar_niveles_relevantes(cierre_actual, niveles, direccion, margen, tolerancia=1): # aumentar o disminuir la toleranci apara determinar la ruptura mas cercana al precio
    """
    Devuelve solo los niveles que están cerca del precio actual.
    - tolerancia: cuántos márgenes de distancia se permiten
    """
    if direccion == "call":
        return [nivel for nivel in niveles if cierre_actual - nivel < margen * tolerancia]
    elif direccion == "put":
        return [nivel for nivel in niveles if nivel - cierre_actual < margen * tolerancia]
    return []
# 🔍 Validación de patrón de vela cerca del nivel
def es_envolvente(candle_prev, candle_actual):
    cuerpo_prev = abs(candle_prev['close'] - candle_prev['open'])
    cuerpo_actual = abs(candle_actual['close'] - candle_actual['open'])
    return (
        cuerpo_actual > cuerpo_prev and
        candle_actual['open'] < candle_prev['close'] and
        candle_actual['close'] > candle_prev['open']
    ) or (
        cuerpo_actual > cuerpo_prev and
        candle_actual['open'] > candle_prev['close'] and
        candle_actual['close'] < candle_prev['open']
    )

def es_envolvente_de_continuidad(candle_prev, candle_actual, sma_direction):
    cuerpo_prev = abs(candle_prev['close'] - candle_prev['open'])
    cuerpo_actual = abs(candle_actual['close'] - candle_actual['open'])

    envolvente_alcista = (
        cuerpo_actual > cuerpo_prev and
        candle_actual['open'] < candle_prev['close'] and
        candle_actual['close'] > candle_prev['open']
    )

    envolvente_bajista = (
        cuerpo_actual > cuerpo_prev and
        candle_actual['open'] > candle_prev['close'] and
        candle_actual['close'] < candle_prev['open']
    )

    if sma_direction == "call" and envolvente_alcista:
        print("envolvente_alcista")
        return True
    elif sma_direction == "put" and envolvente_bajista:
        print("envolvente_alcista")
        return True
    else:
        return False
        
        
def es_martillo(candle):
    cuerpo = abs(candle['close'] - candle['open'])
    mecha_inferior = candle['open'] - candle['low'] if candle['open'] < candle['close'] else candle['close'] - candle['low']
    mecha_superior = candle['high'] - candle['close'] if candle['close'] > candle['open'] else candle['high'] - candle['open']
    return cuerpo < (candle['high'] - candle['low']) * 0.3 and mecha_inferior > cuerpo * 2 and mecha_superior < cuerpo
    
def detectar_martillo_de_continuidad(candle, sma_direction):
    """
    Detecta si una vela es un martillo de continuidad y clasifica su tipo.
    
    Retorna:
        - "alcista" si es martillo en tendencia alcista
        - "bajista" si es martillo invertido en tendencia bajista
        - None si no aplica
    """
    cuerpo = abs(candle['close'] - candle['open'])
    rango_total = candle['high'] - candle['low']
    mecha_inferior = min(candle['close'], candle['open']) - candle['low']
    mecha_superior = candle['high'] - max(candle['close'], candle['open'])

    # Martillo clásico (alcista)
    es_martillo_alcista = (
        cuerpo < rango_total * 0.3 and
        mecha_inferior > cuerpo * 2 and
        mecha_superior < cuerpo
    )

    # Martillo invertido (bajista)
    es_martillo_bajista = (
        cuerpo < rango_total * 0.3 and
        mecha_superior > cuerpo * 2 and
        mecha_inferior < cuerpo
    )

    if es_martillo_alcista and sma_direction == "call":
        print("es_martillo_alcista")
        return True
    elif es_martillo_bajista and sma_direction == "put":
        print("es_martillo_alcista")
        return True
    else:
        return False
        
        
def es_pinbar(candle):
    cuerpo = abs(candle['close'] - candle['open'])
    rango_total = candle['high'] - candle['low']
    mecha_superior = candle['high'] - max(candle['close'], candle['open'])
    mecha_inferior = min(candle['close'], candle['open']) - candle['low']
    return cuerpo < rango_total * 0.3 and (mecha_superior > cuerpo * 2 or mecha_inferior > cuerpo * 2)
    
def detectar_pinbar_de_continuidad(candle, sma_direction):
    cuerpo = abs(candle['close'] - candle['open'])
    rango_total = candle['high'] - candle['low']
    mecha_superior = candle['high'] - max(candle['close'], candle['open'])
    mecha_inferior = min(candle['close'], candle['open']) - candle['low']

    es_pinbar = cuerpo < rango_total * 0.3 and (mecha_superior > cuerpo * 2 or mecha_inferior > cuerpo * 2)

    if not es_pinbar:
        return None

    if sma_direction == "call" and mecha_inferior > mecha_superior:
        return True
    elif sma_direction == "put" and mecha_superior > mecha_inferior:
        return True
    else:
        return False

def es_inside_bar(prev, actual, sma_direction):
    rango_prev = prev['high'] - prev['low']
    return (
        actual['high'] < prev['high'] and
        actual['low'] > prev['low'] and
        rango_prev > (actual['high'] - actual['low']) and
        ((sma_direction == "call" and actual['close'] > actual['open']) or
         (sma_direction == "put" and actual['close'] < actual['open']))
    )        

def es_retroceso_controlado(prev, actual, sma_direction):
    cuerpo_prev = abs(prev['close'] - prev['open'])
    cuerpo_actual = abs(actual['close'] - actual['open'])
    mitad_prev = prev['open'] + cuerpo_prev * 0.5 if prev['close'] > prev['open'] else prev['open'] - cuerpo_prev * 0.5

    if sma_direction == "call":
        return actual['close'] > mitad_prev and cuerpo_actual < cuerpo_prev * 0.6 and actual['close'] < actual['open']
    elif sma_direction == "put":
        return actual['close'] < mitad_prev and cuerpo_actual < cuerpo_prev * 0.6 and actual['close'] > actual['open']
    return False

def es_marubozu_pausa(prev, actual, sma_direction):
    cuerpo_prev = abs(prev['close'] - prev['open'])
    rango_prev = prev['high'] - prev['low']
    sin_mechas = (
        abs(prev['high'] - max(prev['close'], prev['open'])) < rango_prev * 0.1 and
        abs(min(prev['close'], prev['open']) - prev['low']) < rango_prev * 0.1
    )
    cuerpo_actual = abs(actual['close'] - actual['open'])
    rango_actual = actual['high'] - actual['low']

    pausa = cuerpo_actual < cuerpo_prev * 0.5 and rango_actual < rango_prev

    if sma_direction == "call":
        return prev['close'] > prev['open'] and sin_mechas and pausa
    elif sma_direction == "put":
        return prev['close'] < prev['open'] and sin_mechas and pausa
    return False

def validar_patron_de_ruptura(candles, nivel, direccion, margen=0.0003):
    relevantes = candles[-2:]
    for i in range(1, len(relevantes)):
        c_prev = relevantes[i - 1]
        c = relevantes[i]
        cerca_del_nivel = abs(c['close'] - nivel) < margen or abs(c['open'] - nivel) < margen
        # if not cerca_del_nivel:
            # continue
        #if detectar_martillo_de_continuidad(c,direccion):
        if es_retroceso_controlado(c_prev, c, direccion) or es_envolvente_de_continuidad(c_prev, c,direccion) or detectar_martillo_de_continuidad(c,direccion):
            return True
    return False


def validar_patron_de_ruptura_retroceso(candles, nivel, direccion, margen=0.0003):
    relevantes = candles[-5:]
    for i in range(1, len(relevantes)):
        c_prev = relevantes[i - 1]
        c = relevantes[i]
        cerca_del_nivel = abs(c['close'] - nivel) < margen or abs(c['open'] - nivel) < margen
        # if not cerca_del_nivel:
            # continue
        if es_retroceso_controlado(c_prev, c, direccion):
      #  if es_envolvente_de_continuidad(c_prev, c,direccion) or detectar_martillo_de_continuidad(c,direccion):
            return True
    return False


def validar_patron_de_rupturav2(candles, nivel, sma_direction, margen=0.0003):
    relevantes = candles[-3:]
    for i in range(1, len(relevantes)):
        c_prev = relevantes[i - 1]
        c = relevantes[i]

        # Validar proximidad al nivel
        # cerca_del_nivel = (
            # abs(c['close'] - nivel) < margen or
            # abs(c['open'] - nivel) < margen or
            # (c['high'] >= nivel and c['low'] <= nivel)
        # )
        # if not cerca_del_nivel:
            # continue

        # Validar patrones clásicos
        patron_detectado = (
            es_envolvente_de_continuidad(c_prev, c, sma_direction) or
            detectar_martillo_de_continuidad(c, sma_direction) or
            detectar_pinbar_de_continuidad(c, sma_direction) or
            #es_inside_bar(c_prev, c, sma_direction) or
            es_retroceso_controlado(c_prev, c, sma_direction) or
            es_marubozu_pausa(c_prev, c, sma_direction)
        )

        # Validar fuerza de la vela actual
        cuerpo = abs(c['close'] - c['open'])
        rango = c['high'] - c['low']
        cuerpo_significativo = cuerpo > rango * 0.5
        cierre_fuerte = (
            sma_direction == "call" and c['close'] > c['high'] - rango * 0.2 or
            sma_direction == "put" and c['close'] < c['low'] + rango * 0.2
        )

        if patron_detectado and cuerpo_significativo and cierre_fuerte:
            print(f"📍 Ruptura válida con patrón de continuidad en vela {i} cerca de nivel {nivel}")
            return True

    return False

# 🔁 Función principal con selector de método estructural
async def find_best_asset_v0(client, metodo_estructura="combinado",estado=True):
    codes_asset = await client.get_all_assets()
    asset_names = list(codes_asset.keys())
    activos_ordenados = []

    # Filtrar y ordenar por payout
    for asset_name in asset_names:
        try:
            asset_name, asset_data = await client.get_available_asset(asset_name, force_open=True)
            is_open = asset_data[2]
            if not is_open:
                continue
            payout = client.get_payout_by_asset(asset_name)
            if payout is None or not isinstance(payout, (int, float)) or payout < 91:
                continue
            activos_ordenados.append((asset_name, payout))
        except:
            continue

    activos_ordenados.sort(key=lambda x: x[1], reverse=True)

    for asset_name, payout in activos_ordenados:
        now = int(time.time())
        period = 60
        offset = 60 * 30
        candles = await client.get_candles(asset_name, now, offset, period)
        if not candles or len(candles) < 20:
            continue

        closes = [c['close'] for c in candles]
        volumes = [c['ticks'] for c in candles]
        cierre_actual = candles[-1]['close']
        margen = calcular_margen_dinamico(candles)
        analyzer = TrendVolumeAnalyzer()
        sma_direction = analyzer.determine_sma_structure(closes)
        #sma_direction = await analyzer.determine_ema_structure(client, asset_name, closes)
        volume_oscillator = analyzer.calculate_volume_oscillator(volumes)
        macd_signal = await analyzer.get_macd_signal(client, asset_name,margen)

        fractales_alcistas, fractales_bajistas = detectar_fractales(candles)
        pivotes_resistencias, pivotes_soportes = detectar_pivotes(candles)

        if metodo_estructura == "fractales":
            soportes = fractales_alcistas
            resistencias = fractales_bajistas
        elif metodo_estructura == "pivote":
            soportes = pivotes_soportes
            resistencias = pivotes_resistencias
        elif metodo_estructura == "combinado":
            soportes = intersectar_niveles(fractales_alcistas, pivotes_soportes)
            resistencias = intersectar_niveles(fractales_bajistas, pivotes_resistencias)
        else:
            print(f"⚠️ Método de estructura desconocido: {metodo_estructura}")
            continue

      #  margen = calcular_margen_dinamico(candles,1)
        if estado:
             if sma_direction == "call" and macd_signal == "call":
                  # niveles_filtrados = filtrar_niveles_relevantes(cierre_actual, resistencias, "call", margen)
                # # if confirmar_ruptura(cierre_actual, niveles_filtrados, "call", margen):
                  # if any(validar_patron_de_ruptura(candles, nivel, "call", margen*50) for nivel in niveles_filtrados):
                        # # print(f"✅ {metodo_estructura.upper()} | {asset_name} | CALL | Payout: {payout}% | Margen: {margen:.5f}")
                        return asset_name, "call"

             elif sma_direction == "put" and macd_signal == "put":
                   # niveles_filtrados = filtrar_niveles_relevantes(cierre_actual, soportes, "put", margen)
                # # if confirmar_ruptura(cierre_actual, niveles_filtrados, "put", margen):
                   # if any(validar_patron_de_ruptura(candles, nivel, "put", margen*50) for nivel in niveles_filtrados):
                        # print(f"✅ {metodo_estructura.upper()} | {asset_name} | PUT | Payout: {payout}% | Margen: {margen:.5f}")
                        return asset_name, "put"
                    
                   
        else:
        
             if sma_direction == "call" and macd_signal == "call":
                  niveles_filtrados = filtrar_niveles_relevantes(cierre_actual, resistencias, "call", margen)
                # if confirmar_ruptura(cierre_actual, niveles_filtrados, "call", margen):
                  if validar_patron_de_rupturav2(candles, cierre_actual, "call", margen*50):
                        # print(f"✅ {metodo_estructura.upper()} | {asset_name} | CALL | Payout: {payout}% | Margen: {margen:.5f}")
                        return asset_name, "call"

             elif sma_direction == "put" and macd_signal == "put":
                   niveles_filtrados = filtrar_niveles_relevantes(cierre_actual, soportes, "put", margen)
                # if confirmar_ruptura(cierre_actual, niveles_filtrados, "put", margen):
                   if validar_patron_de_rupturav2(candles, cierre_actual, "put", margen*50):
                        print(f"✅ {metodo_estructura.upper()} | {asset_name} | PUT | Payout: {payout}% | Margen: {margen:.5f}")
                        return asset_name, "put"
                 


    print(f"⚠️ Ningún activo cumple condiciones con método {metodo_estructura}.")
    return None, None

def validar_cruce_con_fractal_dinamico(closes, candles, direccion, periodo_sma=20):
    if len(closes) < periodo_sma + 5:
        return False

    # Calcular SMA histórica para las últimas 5 velas
    sma_series = [
        sum(closes[i - periodo_sma:i]) / periodo_sma
        for i in range(len(closes) - 5, len(closes))
    ]

    # Evaluar las últimas 3 velas como candidatas
    for i in range(2, 5):  # índices relativos: vela[-3], vela[-2], vela[-1]
        idx = -5 + i
        c0 = candles[idx]
        c1 = candles[idx - 1]
        c2 = candles[idx - 2]
        sma = sma_series[i]

        if direccion == "call":
            cruce_valido = c0['low'] < sma and c0['close'] > sma
            fractal_potencial = c1['high'] < c0['high'] and c2['high'] < c0['high']
        elif direccion == "put":
            cruce_valido = c0['high'] > sma and c0['close'] < sma
            fractal_potencial = c1['high'] > c0['high'] and c2['high'] > c0['high']
        else:
            continue

        if cruce_valido and fractal_potencial:
            print(f"📍 Cruce + fractal detectado en vela {idx} con SMA{periodo_sma}")
            return True

    return False

def chequear_patron_tres_velas(candles):
    """
    Recibe una lista de velas (diccionarios con open, high, low, close).
    Verifica si las últimas tres forman un patrón alcista o bajista.
    """

    if len(candles) < 3:
        return "No hay suficientes velas"

    # Tomar las últimas tres
    v1, v2, v3 = candles[-3:]

    # Patrón alcista
    alcista = (
        v1["close"] > v1["open"] and
        v2["close"] > v2["open"] and
        v3["close"] > v3["open"] and
        v2["high"] > v1["high"] and
        v3["high"] > v2["high"] and
        v2["close"] > v1["close"] and
        v3["close"] > v2["close"]
    )

    # Patrón bajista
    bajista = (
        v1["close"] < v1["open"] and
        v2["close"] < v2["open"] and
        v3["close"] < v3["open"] and
        v2["low"] < v1["low"] and
        v3["low"] < v2["low"] and
        v2["close"] < v1["close"] and
        v3["close"] < v2["close"]
    )

    if alcista:
        return "call"
    elif bajista:
        return "put"
    else:
        return None
        
async def find_best_asset(client, metodo_estructura="combinado", estado=True):
    try:
        codes_asset = await client.get_all_assets()
        activos_ordenados = []

        # Filtrar por payout y apertura
        for asset_name in codes_asset.keys():
            try:
                asset_name, asset_data = await client.get_available_asset(asset_name, force_open=True)
                if not asset_data or not asset_data[2]:
                    continue
                payout = client.get_payout_by_asset(asset_name)
                if payout and isinstance(payout, (int, float)) and payout >= 91:
                    activos_ordenados.append((asset_name, payout))
            except Exception as e:
                print(f"⚠️ Error en asset {asset_name}: {e}")
                continue

        activos_ordenados.sort(key=lambda x: x[1], reverse=True)

        for asset_name, payout in activos_ordenados:
            try:
                candles = await client.get_candles(asset_name, int(time.time()), 50 * 60, 60)
                if not candles or len(candles) < 2:
                    continue

                closes = [c['close'] for c in candles]
                highs  = [c["high"] for c in candles]
                lows   = [c["low"] for c in candles]
                fractales_alcistas, fractales_bajistas = detectar_fractales(candles)
                pivotes_resistencias, pivotes_soportes = detectar_pivotes(candles)           

                candle_prev = candles[-2]
                candle_prev3 = candles[-3]
                candle_actual = candles[-1]
                apertura = candle_actual["open"]
                cierre   = candle_actual["close"]

                analyzer = TrendVolumeAnalyzer()
                direccion_macd = await analyzer.get_macd_signal(client, asset_name, None, 60)
                if direccion_macd not in ["call", "put"]:
                    continue

                estocastico = TechnicalIndicators.calculate_stochastic(closes, highs, lows, k_period=8, d_period=3)
                if len(estocastico["k"]) < 2 or len(estocastico["d"]) < 2:
                    continue
 
                k_prev, d_prev = estocastico["k"][-2], estocastico["d"][-2]
                k_actual, d_actual = estocastico["k"][-1], estocastico["d"][-1]
                
                direccionconteovelas = chequear_patron_tres_velas(candles[:-2])

           
                if k_actual>=20 and k_prev<=20 and k_actual > d_actual and direccion_macd == "call" :
                               return asset_name, "call" 
                               

                elif k_actual<=80 and k_prev>=80 and k_actual < d_actual and direccion_macd == "put" :
                               return asset_name, "put" 
                               

                if k_actual>=80  and k_prev>=80 and candle_prev['high'] > candle_prev3['high'] and  candle_prev['close'] <candle_prev3['high'] and es_envolvente_de_continuidad(candle_prev, candle_actual, "put"):
                               return asset_name, "put" 


                elif  k_actual<=20  and k_prev<=20 and candle_prev['low'] < candle_prev3['low'] and  candle_prev['close'] > candle_prev3['low'] and es_envolvente_de_continuidad(candle_prev, candle_actual, "call"):
                             return asset_name, "call"  
                
                if k_actual>k_prev and direccion_macd == "call" and direccionconteovelas== "call" and candle_prev['high'] > candle_prev3['high'] and es_envolvente_de_continuidad(candle_prev, candle_actual, "call") and  candle_prev['close'] <= candle_prev3['close'] and  candle_prev['open'] <= candle_prev3['close']:
                               return asset_name, "call" 


                elif  k_actual<k_prev  and direccion_macd == "put" and direccionconteovelas== "put" and candle_prev['low'] < candle_prev3['low'] and es_envolvente_de_continuidad(candle_prev, candle_actual, "put") and  candle_prev['close'] >= candle_prev3['close'] and  candle_prev['open'] >= candle_prev3['close']:
                             return asset_name, "put"  
                          
                   
                if k_actual>=80  and k_prev>=80 and k_actual < d_actual and es_envolvente_de_continuidad(candle_prev, candle_actual, "put"):
                                return asset_name, "put" 


                elif  k_actual<=20  and k_prev<=20 and k_actual > d_actual and es_envolvente_de_continuidad(candle_prev, candle_actual, "call"):
                              return asset_name, "call"  

                if direccion_macd == "call" and es_envolvente_de_continuidad(candle_prev, candle_actual, "call") and  es_retroceso_controlado(candle_prev3, candle_prev, "call") and not detectar_martillo_de_continuidad(candle_prev, "put")  :
                               return asset_name, "call" 


                elif direccion_macd == "put" and es_envolvente_de_continuidad(candle_prev, candle_actual, "put") and  es_retroceso_controlado(candle_prev3, candle_prev, "put") and not detectar_martillo_de_continuidad(candle_prev, "call")  :
                               return asset_name, "put" 


                if detectar_harami_alcista(candles) == "call":
                               return asset_name, "put" 

                elif detectar_harami_bajista(candles) == "put":
                               return asset_name, "call" 

                if direccionconteovelas== "call" and  es_retroceso_controlado(candle_prev3, candle_prev, "call") and es_envolvente_de_continuidad(candle_prev, candle_actual, "call"):
                               return asset_name, "call" 


                elif  direccionconteovelas== "put" and  es_retroceso_controlado(candle_prev3, candle_prev, "put") and es_envolvente_de_continuidad(candle_prev, candle_actual, "put"):
                             return asset_name, "put"  
                             
                if  k_actual>=90  and d_actual>=80 and k_actual > d_actual and detectar_martillo_de_continuidad(candle_actual, direccion_macd) and es_retroceso_controlado(candle_prev, candle_actual, direccion_macd) :
                               
                                return asset_name, "call" 
                                                                             

                elif  k_actual<=10  and d_actual<=20 and k_actual < d_actual and detectar_martillo_de_continuidad(candle_actual, direccion_macd) and es_retroceso_controlado(candle_prev, candle_actual, direccion_macd):
                             
                                return asset_name, "put"     


                if  k_actual > d_actual and k_prev < d_prev and direccion_macd=="call" and  es_retroceso_controlado(candle_prev3, candle_prev, "call") and es_envolvente_de_continuidad(candle_prev, candle_actual, "call"):
                                           return asset_name, "call" 


                elif   k_actual < d_actual and k_prev > d_prev and  direccion_macd=="put" and  es_retroceso_controlado(candle_prev3, candle_prev, "put") and  es_envolvente_de_continuidad(candle_prev, candle_actual, "put"):
                                         return asset_name, "put"  

                if direccion_macd == "call":
                               if confirmar_rupturacruce(candle_actual, fractales_alcistas, "call", 0):
                                   return asset_name, "call"

                elif direccion_macd == "put":

                               if confirmar_rupturacruce(candle_actual, fractales_bajistas, "put", 0):
                                   return asset_name, "put"
                if estado:

                                      
                    return asset_name, direccion_macd
                    
            except Exception as e:
                print(f"⚠️ Error analizando {asset_name}: {e}")
                continue

        print(f"❌ Ningún activo cumple condiciones con método {metodo_estructura}.")
        return None, None

    except Exception as e:
        print(f"⚠️ Error general en find_best_asset: {e}")
        return None, None

         
async def especialfind_best_asset(client, metodo_estructura="combinado", estado=True):
    try:
        codes_asset = await client.get_all_assets()
        activos_ordenados = []

        # Filtrar por payout y apertura
        for asset_name in codes_asset.keys():
            try:
                asset_name, asset_data = await client.get_available_asset(asset_name, force_open=True)
                if not asset_data or not asset_data[2]:
                    continue
                payout = client.get_payout_by_asset(asset_name)
                if payout and isinstance(payout, (int, float)) and payout >= 91:
                    activos_ordenados.append((asset_name, payout))
            except Exception as e:
                print(f"⚠️ Error en asset {asset_name}: {e}")
                continue

        activos_ordenados.sort(key=lambda x: x[1], reverse=True)

        for asset_name, payout in activos_ordenados:
            try:
                candles = await client.get_candles(asset_name, int(time.time()), 50 * 60, 60)
                if not candles or len(candles) < 2:
                    continue

                closes = [c['close'] for c in candles]
                highs  = [c["high"] for c in candles]
                lows   = [c["low"] for c in candles]
                fractales_alcistas, fractales_bajistas = detectar_fractales(candles)
                pivotes_resistencias, pivotes_soportes = detectar_pivotes(candles)           

                candle_prev = candles[-2]
                candle_prev3 = candles[-3]
                candle_actual = candles[-1]
                apertura = candle_actual["open"]
                cierre   = candle_actual["close"]

                analyzer = TrendVolumeAnalyzer()
                direccion_macd = await analyzer.get_macd_signal(client, asset_name, None, 60)
                if direccion_macd not in ["call", "put"]:
                    continue

                estocastico = TechnicalIndicators.calculate_stochastic(closes, highs, lows, k_period=8, d_period=3)
                if len(estocastico["k"]) < 2 or len(estocastico["d"]) < 2:
                    continue
 
                k_prev, d_prev = estocastico["k"][-2], estocastico["d"][-2]
                k_actual, d_actual = estocastico["k"][-1], estocastico["d"][-1]
                
                direccionconteovelas = chequear_patron_tres_velas(candles[:-2])

             
                ##0.6 - 0.8 9 -12 operaciones            
                if k_actual>k_prev and direccion_macd == "call" and direccionconteovelas== "call" and candle_prev['high'] > candle_prev3['high'] and es_envolvente_de_continuidad(candle_prev, candle_actual, "call") and  candle_prev['close'] <= candle_prev3['close'] and  candle_prev['open'] <= candle_prev3['close']:
                                           return asset_name, "call" 


                elif  k_actual<k_prev  and direccion_macd == "put" and direccionconteovelas== "put" and candle_prev['low'] < candle_prev3['low'] and es_envolvente_de_continuidad(candle_prev, candle_actual, "put") and  candle_prev['close'] >= candle_prev3['close'] and  candle_prev['open'] >= candle_prev3['close']:
                                         return asset_name, "put"                         
                  
                ##0.8 5 -8 operaciones
                if k_actual>=80  and k_prev>=80 and candle_prev['high'] > candle_prev3['high'] and  candle_prev['close'] <candle_prev3['high'] and es_envolvente_de_continuidad(candle_prev, candle_actual, "put"):
                                           return asset_name, "put" 

                elif  k_actual<=20  and k_prev<=20 and candle_prev['low'] < candle_prev3['low'] and  candle_prev['close'] > candle_prev3['low'] and es_envolvente_de_continuidad(candle_prev, candle_actual, "call"):
                                         return asset_name, "call"      
                ##0.7 3 -5 operaciones
                if k_actual>=20 and k_prev<=20 and k_actual > d_actual and direccion_macd == "call" :
                                           return asset_name, "call" 
                                           

                elif k_actual<=80 and k_prev>=80 and k_actual < d_actual and direccion_macd == "put" :
                                           return asset_name, "put" 


                # ##0.6 - 0.6 13-26 operaciones 
                # if  k_actual>=90  and d_actual>=80 and k_actual > d_actual and detectar_martillo_de_continuidad(candle_actual, direccion_macd) and es_retroceso_controlado(candle_prev, candle_actual, direccion_macd) :
                               
                                # return asset_name, "call" 
                                                               
                # elif  k_actual<=10  and d_actual<=20 and k_actual < d_actual and detectar_martillo_de_continuidad(candle_actual, direccion_macd) and es_retroceso_controlado(candle_prev, candle_actual, direccion_macd):                 
                                # return asset_name, "put" 
                          
             
                # ##0.5 - 0.6 51 operaciones  /////super buena, muchas operaciones
                # if direccion_macd == "call" and es_envolvente_de_continuidad(candle_prev, candle_actual, "call") and  es_retroceso_controlado(candle_prev3, candle_prev, "call") and not detectar_martillo_de_continuidad(candle_prev, "put")  :
                               # return asset_name, "call" 


                # elif direccion_macd == "put" and es_envolvente_de_continuidad(candle_prev, candle_actual, "put") and  es_retroceso_controlado(candle_prev3, candle_prev, "put") and not detectar_martillo_de_continuidad(candle_prev, "call")  :
                               # return asset_name, "put" 

                                           
                # ##0.5 - 0.6 23-27 operaciones             
                # if k_actual>=80  and k_prev>=80 and k_actual < d_actual and es_envolvente_de_continuidad(candle_prev, candle_actual, "put"):
                                            # return asset_name, "put" 


                # elif  k_actual<=20  and k_prev<=20 and k_actual > d_actual and es_envolvente_de_continuidad(candle_prev, candle_actual, "call"):
                                          # return asset_name, "call"  


                              
            except Exception as e:
                    print(f"⚠️ Error analizando {asset_name}: {e}")
                    continue

        print(f"❌ Ningún activo cumple condiciones con método {metodo_estructura}.")
        return None, None

    except Exception as e:
        print(f"⚠️ Error general en find_best_asset: {e}")
        return None, None

    
def detectar_harami_alcista(candles):
    """
    Detecta patrón Harami alcista en las últimas 3 velas.
    Retorna 'call' si se confirma, None si no hay patrón.
    """

    if len(candles) < 3:
        return None

    v1, v2, v3 = candles[-3], candles[-2], candles[-1]

    # 1. Primera vela bajista larga
    cuerpo_v1 = abs(v1["close"] - v1["open"])
    rango_v1 = v1["high"] - v1["low"]
    es_bajista_larga = v1["close"] < v1["open"] and cuerpo_v1 > rango_v1 * 0.5

    # 2. Segunda vela alcista pequeña dentro del cuerpo de la primera
    cuerpo_v2 = abs(v2["close"] - v2["open"])
    es_alcista_pequena = v2["close"] > v2["open"] and cuerpo_v2 < cuerpo_v1 * 0.6
    dentro_del_cuerpo = v2["open"] > v1["close"] and v2["close"] < v1["open"]

    # 3. Confirmación: tercera vela cierra por encima del máximo de la segunda
    confirmacion = v3["close"] > v2["high"]

    if es_bajista_larga and es_alcista_pequena and dentro_del_cuerpo and confirmacion:
        return "call"

    return None
    
def detectar_harami_bajista(candles):
    """
    Detecta patrón Harami bajista en las últimas 3 velas.
    Retorna 'put' si se confirma, None si no hay patrón.
    """

    if len(candles) < 3:
        return None

    v1, v2, v3 = candles[-3], candles[-2], candles[-1]

    # 1. Primera vela alcista larga
    cuerpo_v1 = abs(v1["close"] - v1["open"])
    rango_v1 = v1["high"] - v1["low"]
    es_alcista_larga = v1["close"] > v1["open"] and cuerpo_v1 > rango_v1 * 0.5

    # 2. Segunda vela bajista pequeña dentro del cuerpo de la primera
    cuerpo_v2 = abs(v2["close"] - v2["open"])
    es_bajista_pequena = v2["close"] < v2["open"] and cuerpo_v2 < cuerpo_v1 * 0.6
    dentro_del_cuerpo = v2["open"] < v1["close"] and v2["close"] > v1["open"]

    # 3. Confirmación: tercera vela cierra por debajo del mínimo de la segunda
    confirmacion = v3["close"] < v2["low"]

    if es_alcista_larga and es_bajista_pequena and dentro_del_cuerpo and confirmacion:
        return "put"

    return None    
            