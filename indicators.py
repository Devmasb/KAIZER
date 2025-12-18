import numpy as np
from scipy.stats import linregress

class TrendVolumeAnalyzer:
    def __init__(self):
        self.sma_periods = [5, 10, 20]

    def calculate_sma(self, data, period):
        if len(data) < period:
            return None
        return sum(data[-period:]) / period

    def get_sma_values(self, closes):
        sma_values = {}
        for p in self.sma_periods:
            sma = self.calculate_sma(closes, p)
            if sma is None:
                return None
            sma_values[p] = sma
        return sma_values

    def determine_sma_structure(self, closes):
        sma = self.get_sma_values(closes)
        if not sma:
            return "hold"

        sma5, sma10, sma20 = sma[5], sma[10], sma[20]

        if sma5 < sma10 < sma20  and closes[-1] < closes[-2]:
            return "put"
        elif sma5 > sma10 > sma20  and closes[-1] > closes[-2]:
            return "call"
        else:
            return "hold"


    def determine_sma_structure_v0(self, closes):
        sma = self.get_sma_values(closes)
        if not sma or len(closes) < 30:
            return "hold"

        sma5, sma10, sma20 = sma[5], sma[10], sma[20]

        # Calcular pendiente lineal de SMA20 en las últimas 10 velas
        sma20_series = [
            self.calculate_sma(closes[i - 20:i])
            for i in range(len(closes) - 10, len(closes))
        ]
        x = np.arange(len(sma20_series))
        y = np.array(sma20_series)
        pendiente_sma20, _ = np.polyfit(x, y, 1)

        # Validar estructura + pendiente
        if sma5 < sma10 < sma20 and closes[-1] < closes[-2] and pendiente_sma20 < 0:
            return "put"
        elif sma5 > sma10 > sma20 and closes[-1] > closes[-2] and pendiente_sma20 > 0:
            return "call"
        else:
            return "hold"
        
    async def determine_ema_structure(self, client, asset_name, closes, timeframe_ema=60, timeframe_atr=60):
        try:
            if len(closes) < 60:
                return "hold"

            # Calcular EMAs
            ema5_data = await client.calculate_indicator(
                asset=asset_name,
                indicator="EMA",
                params={"period": 5},
                timeframe=timeframe_ema
            )
            ema10_data = await client.calculate_indicator(
                asset=asset_name,
                indicator="EMA",
                params={"period": 10},
                timeframe=timeframe_ema
            )
            ema20_data = await client.calculate_indicator(
                asset=asset_name,
                indicator="EMA",
                params={"period": 20},
                timeframe=timeframe_ema
            )

            # Validar datos EMA
            if not ema5_data or not ema10_data or not ema20_data:
                return "hold"

            e5 = ema5_data.get("current")
            e10 = ema10_data.get("current")
            e20 = ema20_data.get("current")

            if e5 is None or e10 is None or e20 is None:
                return "hold"

            # Calcular ATR
            atr_data = await client.calculate_indicator(
                asset=asset_name,
                indicator="ATR",
                params={"period": 14},
                timeframe=timeframe_atr
            )

            atr_actual = atr_data.get("current")
            if atr_actual is None or atr_actual == 0:
                return "hold"

            # Separaciones absolutas
            sep_corta = abs(e5 - e10)
            sep_larga = abs(e10 - e20)

            # Validar si la separación es significativa respecto al ATR
            if sep_corta < atr_actual * 0.1 or sep_larga < atr_actual * 0.1:
                print(f"🔍 EMAs demasiado juntas para {sep_corta} | ATR: {atr_actual:.5f}")
                return "hold"

            # Confirmar dirección del precio
            if closes[-1] > closes[-2] and e5 > e10 > e20:
                return "call"
            elif closes[-1] < closes[-2] and e5 < e10 < e20:
                return "put"
            else:
                return "hold"

        except Exception as e:
            print(f"⛔ Error en determine_ema_structure para {asset_name}: {e}")
            return "hold"
            

    def calculate_volume_oscillator(self, volumes, short_period=5, long_period=14):
        if len(volumes) < long_period:
            return 0
        short_sma = self.calculate_sma(volumes, short_period)
        long_sma = self.calculate_sma(volumes, long_period)
        if not short_sma or not long_sma or long_sma == 0:
            return 0
        return ((short_sma - long_sma) / long_sma) * 100

    # async def get_macd_signal(self, client, asset_name,margen, timeframe=60):
        # try:
            # macd_data = await client.calculate_indicator(
                # asset=asset_name,
                # indicator="MACD",
                # params={
                    # "fast_period": 25,
                    # "slow_period": 50,
                    # "signal_period": 9
                # },
                # timeframe=timeframe
            # )

            # current = macd_data.get("current", {})
            # histogram = current.get("histogram")

            # if histogram is None or abs(histogram) < margen:
                # return "neutral"

            # if histogram > 0:
                # return "call"
            # elif histogram < 0:
                # return "put"
            # else:
                # return "neutral"

        # except Exception as e:
            # print(f"Error al calcular MACD para {asset_name}: {e}")
            # return "neutral"



    async def get_macd_signal(self, client, asset_name, margen=None, timeframe=60):
        try:
            macd_data = await client.calculate_indicator(
                asset=asset_name,
                indicator="MACD",
                params={
                    "fast_period": 25,
                    "slow_period": 50,
                    "signal_period": 9
                },
                timeframe=timeframe
            )

            # Extraer series completas
            histograma = macd_data.get("histogram", [])
            macd_line = macd_data.get("macd", [])
            signal_line = macd_data.get("signal", [])
            current = macd_data.get("current", {})
            h_actual = current.get("histogram")
            m_actual = current.get("macd")
            s_actual = current.get("signal")

            # Validacion basica
            if not histograma or h_actual is None or m_actual is None or s_actual is None:
                #print(f"?? Datos incompletos para {asset_name}")
                return "neutral"

            # Calcular desviacion estandar adaptativa
            std_histograma = np.std(histograma[-20:])
            umbral_adaptativo = margen if margen is not None else std_histograma * 0.5

            # Filtrar lateralizacion
            if abs(h_actual) < umbral_adaptativo:
               # print(f"?? Histograma pequeno ({h_actual:.4f}) < umbral ({umbral_adaptativo:.4f}) ? lateral")
                return "neutral"

            # Calcular pendiente lineal del histograma
            n_pendiente = min(5, len(histograma))
            x = list(range(n_pendiente))
            y = histograma[-n_pendiente:]
            pendiente, _, _, _, _ = linregress(x, y)

            # Validar coherencia entre signo y pendiente
            if h_actual > 0 and pendiente <= 0:
              #  print(f"?? Histograma positivo pero pendiente negativa ({pendiente:.4f}) ? sin impulso real")
                return "neutral"
            elif h_actual < 0 and pendiente >= 0:
              #  print(f"?? Histograma negativo pero pendiente positiva ({pendiente:.4f}) ? sin impulso real")
                return "neutral"

            # Senal valida
            if h_actual > 0:
              #  print(f"?? Senal CALL | Histograma: {h_actual:.4f} | Pendiente: {pendiente:.4f}")
                return "call"
            elif h_actual < 0:
               # print(f"?? Senal PUT | Histograma: {h_actual:.4f} | Pendiente: {pendiente:.4f}")
                return "put"
            else:
                return "neutral"

        except Exception as e:
            print(f"? Error al calcular MACD para {asset_name}: {e}")
            return "neutral"            
                

    async def get_macd_signalcorto(self, client, asset_name, margen=None, timeframe=60):
        try:
            macd_data = await client.calculate_indicator(
                asset=asset_name,
                indicator="MACD",
                params={
                    "fast_period": 1,
                    "slow_period": 4,
                    "signal_period": 4
                },
                timeframe=timeframe
            )

            # Extraer series completas
            histograma = macd_data.get("histogram", [])
            macd_line = macd_data.get("macd", [])
            signal_line = macd_data.get("signal", [])
            current = macd_data.get("current", {})
            h_actual = current.get("histogram")
            m_actual = current.get("macd")
            s_actual = current.get("signal")

            # Validacion basica
            if not histograma or h_actual is None or m_actual is None or s_actual is None:
                #print(f"?? Datos incompletos para {asset_name}")
                return "neutral"

            # Calcular desviacion estandar adaptativa
            std_histograma = np.std(histograma[-20:])
            umbral_adaptativo = margen if margen is not None else std_histograma * 0.5

            # Filtrar lateralizacion
            if abs(h_actual) < umbral_adaptativo:
               # print(f"?? Histograma pequeno ({h_actual:.4f}) < umbral ({umbral_adaptativo:.4f}) ? lateral")
                return "neutral"

            # Calcular pendiente lineal del histograma
            n_pendiente = min(5, len(histograma))
            x = list(range(n_pendiente))
            y = histograma[-n_pendiente:]
            pendiente, _, _, _, _ = linregress(x, y)

            # Validar coherencia entre signo y pendiente
            if h_actual > 0 and pendiente <= 0:
              #  print(f"?? Histograma positivo pero pendiente negativa ({pendiente:.4f}) ? sin impulso real")
                return "neutral"
            elif h_actual < 0 and pendiente >= 0:
              #  print(f"?? Histograma negativo pero pendiente positiva ({pendiente:.4f}) ? sin impulso real")
                return "neutral"

            # Senal valida
            if h_actual > 0:
              #  print(f"?? Senal CALL | Histograma: {h_actual:.4f} | Pendiente: {pendiente:.4f}")
                return "call"
            elif h_actual < 0:
               # print(f"?? Senal PUT | Histograma: {h_actual:.4f} | Pendiente: {pendiente:.4f}")
                return "put"
            else:
                return "neutral"

        except Exception as e:
            print(f"? Error al calcular MACD para {asset_name}: {e}")
            return "neutral"            
                