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
    ea = (es_min * rhmin / 100 + es_max * rhmax / 100) / 2
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

def irrigation(eto, kc, rain, efficiency=EFICIENCIA_SISTEMA):
    etc = eto * kc
    effective_rain = min(max(rain, 0), etc)
    net_need = max(0, etc - effective_rain)
    gross_depth = net_need / efficiency
    volume_plant = gross_depth * AREA_POR_PLANTA_M2
    time_min = volume_plant / VAZAO_PLANTA_LH * 60
    return {"etc": etc, "chuva_efetiva": effective_rain, "necessidade_liquida": net_need,
            "lamina_bruta": gross_depth, "volume_planta": volume_plant,
            "tempo_irrigacao": time_min}

def coverage_status(coverage):
    if coverage >= 0.90:
        return "OK"
    if coverage >= 0.80:
        return "ATENÇÃO"
    return "INSUFICIENTE"
