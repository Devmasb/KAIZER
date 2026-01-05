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
    

async def find_best_asset(client, metodo_estructura="combinado", estado=True):
    codes_asset = await client.get_all_assets()
    activos_ordenados = []

    # Filtrar por payout y apertura
    for asset_name in codes_asset.keys():
        try:
            asset_name, asset_data = await client.get_available_asset(asset_name, force_open=True)
            if not asset_data[2]:
                continue
            payout = client.get_payout_by_asset(asset_name)
            if payout and isinstance(payout, (int, float)) and payout >= 91:
                activos_ordenados.append((asset_name, payout))
        except:
            continue

    activos_ordenados.sort(key=lambda x: x[1], reverse=True)

    for asset_name, payout in activos_ordenados:
        candles = await client.get_candles(asset_name, int(time.time()), 30 * 20, 60)
        closes = [c['close'] for c in candles]  
        highs  = [c["high"] for c in candles]
        lows   = [c["low"] for c in candles]
       
        candle_prev = candles[-2]
        candle_actual = candles[-1]
        apertura = candle_actual["open"]
        cierre   = candle_actual["close"]

        if estado:
                    analyzer = TrendVolumeAnalyzer()
                    direccion_macd = await analyzer.get_macd_signal(client, asset_name, None, 60)                    
                    if direccion_macd not in ["call", "put"]:
                        continue
                        
                    sma_direction = analyzer.determine_sma_structure(closes)
                    if direccion_macd != sma_direction:
                       continue
                        
                    return asset_name, direccion_macd 
      
        else:   
            estocastico = TechnicalIndicators.calculate_stochastic(closes, highs, lows, k_period=8, d_period=3)
            # Últimos valores de las listas
            k_prev = estocastico["k"][-2]
            d_prev = estocastico["d"][-2]

            k_actual = estocastico["k"][-1]
            d_actual = estocastico["d"][-1]
            
            if es_envolvente_de_continuidad(candle_prev, candle_actual, "call") and  k_actual>=30  and k_actual<=70 and k_actual>=d_actual:
                    return asset_name, "call"

            elif es_envolvente_de_continuidad(candle_prev, candle_actual, "put") and k_actual>=30  and k_actual<=70 and k_actual<=d_actual:

                       return asset_name, "put"

    print(f"?? Ningún activo cumple condiciones con método {metodo_estructura}.")
    return None, None      
