import math
import pandas as pd
from .config import ALTITUDE_M, ALTURA_VENTO_M, EFICIENCIA_SISTEMA, VAZAO_PLANTA_LH, AREA_POR_PLANTA_M2

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


def irrigation(eto, kc, rain, efficiency=EFICIENCIA_SISTEMA, kl=0.32):
    """
    Calcula dois cenários de irrigação:
    - com Kl: ETc = ETo * Kc * Kl
    - sem Kl: ETc = ETo * Kc

    As lâminas são expressas em mm; o volume, em L/planta;
    e o tempo, em minutos.
    """
    if eto < 0:
        raise ValueError("ETo não pode ser negativa.")
    if kc < 0:
        raise ValueError("Kc não pode ser negativo.")
    if not 0 < efficiency <= 1:
        raise ValueError("A eficiência deve estar entre 0 e 1.")
    if not 0 <= kl <= 1:
        raise ValueError("Kl deve estar entre 0 e 1.")

    def calcular_cenario(fator_kl):
        etc = eto * kc * fator_kl

        # A chuva efetiva é limitada à ETc considerada em cada cenário.
        chuva_efetiva = min(max(rain, 0), etc)
        necessidade_liquida = max(0, etc - chuva_efetiva)

        # Lâmina bruta em mm, corrigida pela eficiência do sistema.
        lamina_bruta_mm = necessidade_liquida / efficiency

        # mm × m² = litros por planta.
        volume_planta_l = lamina_bruta_mm * AREA_POR_PLANTA_M2

        # Vazão em L/h convertida para tempo em minutos.
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

    com_kl = calcular_cenario(kl)
    sem_kl = calcular_cenario(1.0)

    return {
        **com_kl,
        "etc_com_kl_mm": com_kl["etc"],
        "etc_sem_kl_mm": sem_kl["etc"],
        "lamina_bruta_com_kl_mm": com_kl["lamina_bruta"],
        "lamina_bruta_sem_kl_mm": sem_kl["lamina_bruta"],
        "volume_planta_com_kl_l": com_kl["volume_planta"],
        "volume_planta_sem_kl_l": sem_kl["volume_planta"],
        "tempo_irrigacao_com_kl_min": com_kl["tempo_irrigacao"],
        "tempo_irrigacao_sem_kl_min": sem_kl["tempo_irrigacao"],
    }


def coverage_status(coverage):
    if coverage >= 0.90:
        return "OK"
    if coverage >= 0.80:
        return "ATENÇÃO"
    return "INSUFICIENTE"
