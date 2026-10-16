import math
import pandas as pd
from .config import (
    ALTITUDE_M,
    ALTURA_VENTO_M,
    EFICIENCIA_SISTEMA,
    VAZAO_PLANTA_LH,
    AREA_POR_PLANTA_M2,
    AREA_CAMPO_POR_PLANTA_M2,
    FATOR_AREA_MOLHADA,
)

def saturation_vapor_pressure(temp_c: float) -> float:
    return 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))

def calculate_eto(tmean, tmax, tmin, rhmax, rhmin, wind, rn_mj_m2_day,
                  altitude=ALTITUDE_M, wind_height=ALTURA_VENTO_M):
    # FAO-56 Penman–Monteith diário. Entradas precisam ser verificadas quanto a qualidade.
    pressure = 101.3 * (((293 - 0.0065 * altitude) / 293) ** 5.26)
    gamma = 0.000665 * pressure
    delta = 4098 * saturation_vapor_pressure(tmean) / ((tmean + 237.3) ** 2)
    es_max, es_min = saturation_vapor_pressure(tmax), saturation_vapor_pressure(tmin)
    es = (es_max + es_min) / 2
    ea = (es_min * rhmax / 100 + es_max * rhmin / 100) / 2
    vpd = max(0.0, es - ea)
    u2 = wind if wind_height == 2 else wind * 4.87 / math.log(67.8 * wind_height - 5.42)
    eto = (0.408 * delta * rn_mj_m2_day + gamma * (900 / (tmean + 273)) * u2 * vpd) / (
        delta + gamma * (1 + 0.34 * u2)
    )
    return max(0.0, eto)

def daily_summary(day_df: pd.DataFrame):
    coverage = min(1.0, day_df["TIMESTAMP"].dt.hour.size / 144.0)
    tmax, tmin = day_df["AirTC_Max"].max(), day_df["AirTC_Min"].min()
    tmean = day_df["AirTC_Avg"].mean()
    if pd.isna(tmean):
        tmean = (tmax + tmin) / 2
    rhmax, rhmin = day_df["RH_Max"].max(), day_df["RH_Min"].min()
    wind = day_df["Vento_Avg"].mean()
    # Confirme que Chuva_Tot é total de cada intervalo, não um acumulado repetido.
    rain = day_df["Chuva_Tot"].sum(min_count=1)
    # Rn_Avg em W/m²; média de 10 minutos × 600 s / 1e6 = MJ/m².
    rn = day_df["Rn_Avg"].sum(min_count=1) * 0.0006
    eto = calculate_eto(float(tmean), float(tmax), float(tmin), float(rhmax),
                        float(rhmin), float(wind), float(rn))
    return {
        "cobertura": coverage, "temperatura_media": float(tmean),
        "temperatura_max": float(tmax), "temperatura_min": float(tmin),
        "rh_max": float(rhmax), "rh_min": float(rhmin), "vento": float(wind),
        "chuva": float(rain if pd.notna(rain) else 0),
        "rn": float(rn), "eto": float(eto),
    }
def irrigation(
    eto,
    kc,
    rain,
    efficiency=EFICIENCIA_SISTEMA,
    kl=FATOR_AREA_MOLHADA,
):
    """
    Calcula três métodos de irrigação.

    Método 1:
        ETc = ETo * Kc * fator de área molhada
        Área por planta = área efetiva configurada.

    Método 2:
        ETc = ETo * Kc
        Área por planta = área efetiva configurada.

    Método 3:
        ETc = ETo * Kc
        Área por planta = área de campo configurada.

    A lâmina bruta considera a eficiência do sistema.
    A chuva efetiva é limitada à ETc.
    """

    if eto < 0:
        raise ValueError("ETo não pode ser negativa.")

    if kc < 0:
        raise ValueError("Kc não pode ser negativo.")

    if not 0 < efficiency <= 1:
        raise ValueError("A eficiência deve ser maior que 0 e menor ou igual a 1.")

    if not 0 <= kl <= 1:
        raise ValueError("O fator de área molhada deve estar entre 0 e 1.")

    if VAZAO_PLANTA_LH <= 0:
        raise ValueError("A vazão por planta deve ser maior que zero.")

    if AREA_POR_PLANTA_M2 <= 0 or AREA_CAMPO_POR_PLANTA_M2 <= 0:
        raise ValueError("As áreas por planta devem ser maiores que zero.")

    def calcular_cenario(fator_etc, area_planta):
        etc = eto * kc * fator_etc

        chuva_efetiva = min(max(rain, 0), etc)
        necessidade_liquida = max(0.0, etc - chuva_efetiva)

        lamina_bruta_mm = necessidade_liquida / efficiency

        volume_planta_l = (
            lamina_bruta_mm * area_planta
        )

        tempo_irrigacao_min = (
            volume_planta_l / VAZAO_PLANTA_LH * 60
        )

        return {
            "etc": etc,
            "chuva_efetiva": chuva_efetiva,
            "necessidade_liquida": necessidade_liquida,
            "lamina_bruta": lamina_bruta_mm,
            "volume_planta": volume_planta_l,
            "tempo_irrigacao": tempo_irrigacao_min,
        }

    # Método 1: ETc ajustada pela área molhada.
    metodo1 = calcular_cenario(
    kl,
    AREA_POR_PLANTA_M2,
    )

    # Método 2: ETc integral e área efetiva por planta.
    metodo2 = calcular_cenario(
        1.0,
        AREA_POR_PLANTA_M2,
    )

    # Método 3: ETc integral e área de campo por planta.
    metodo3 = calcular_cenario(
        1.0,
        AREA_CAMPO_POR_PLANTA_M2,
    )

    return {
        # Campos legados: preservam a compatibilidade.
        **metodo1,

        # Métodos 1 e 2: campos já utilizados pelo histórico.
        "etc_com_kl_mm": metodo1["etc"],
        "etc_sem_kl_mm": metodo2["etc"],

        "lamina_bruta_com_kl_mm": metodo1["lamina_bruta"],
        "lamina_bruta_sem_kl_mm": metodo2["lamina_bruta"],

        "volume_planta_com_kl_l": metodo1["volume_planta"],
        "volume_planta_sem_kl_l": metodo2["volume_planta"],

        "tempo_irrigacao_com_kl_min": metodo1["tempo_irrigacao"],
        "tempo_irrigacao_sem_kl_min": metodo2["tempo_irrigacao"],

        # Método 3: área de campo de 0,50 m² por planta.
        "etc_metodo3_mm": metodo3["etc"],
        "lamina_bruta_metodo3_mm": metodo3["lamina_bruta"],
        "volume_planta_campo_l": metodo3["volume_planta"],
        "tempo_irrigacao_campo_min": metodo3["tempo_irrigacao"],
    }

def coverage_status(coverage):
    if coverage >= 0.90:
        return "OK"
    if coverage >= 0.80:
        return "ATENÇÃO"
    return "INSUFICIENTE"
