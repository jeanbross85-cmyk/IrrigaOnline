from pathlib import Path
import re
import pandas as pd

REQUIRED_COLUMNS = [
    "TIMESTAMP", "AirTC_Avg", "AirTC_Max", "AirTC_Min",
    "RH_Max", "RH_Min", "Vento_Avg", "Chuva_Tot", "Rn_Avg"
]

COLUMN_ALIASES = {
    "timestamp": "TIMESTAMP",
    "data_hora": "TIMESTAMP",
    "datahora": "TIMESTAMP",
    "data_e_hora": "TIMESTAMP",
    "datetime": "TIMESTAMP",
    "data": "TIMESTAMP",
    "airtc_avg": "AirTC_Avg",
    "temperatura_media": "AirTC_Avg",
    "temp_media": "AirTC_Avg",
    "temperatura_do_ar_c": "AirTC_Avg",
    "airtc_max": "AirTC_Max",
    "temperatura_maxima": "AirTC_Max",
    "temp_max": "AirTC_Max",
    "airtc_min": "AirTC_Min",
    "temperatura_minima": "AirTC_Min",
    "temp_min": "AirTC_Min",
    "rh_max": "RH_Max",
    "umidade_maxima": "RH_Max",
    "ur_max": "RH_Max",
    "umidade_relativa": "RH_Avg",
    "rh_min": "RH_Min",
    "umidade_minima": "RH_Min",
    "ur_min": "RH_Min",
    "vento_avg": "Vento_Avg",
    "vento": "Vento_Avg",
    "vento_m_s": "Vento_Avg",
    "velocidade_vento": "Vento_Avg",
    "chuva_tot": "Chuva_Tot",
    "chuva": "Chuva_Tot",
    "precipitacao": "Chuva_Tot",
    "rn_avg": "Rn_Avg",
    "radiacao_liquida": "Rn_Avg",
    "rn": "Rn_Avg",
    "rn_w_m": "Rn_Avg",
}

def _normalize_header(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")

def read_meteorological_xlsx(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if path.suffix.lower() != ".xlsx":
        raise ValueError("O arquivo deve ter extensão .xlsx.")

    # Use the first worksheet by default. Headers are expected in the first row.
    df = pd.read_excel(path, sheet_name=0, engine="openpyxl")
    if df.empty:
        raise ValueError("A planilha está vazia.")

    rename = {}
    for col in df.columns:
        normalized = _normalize_header(col)
        if normalized in COLUMN_ALIASES:
            rename[col] = COLUMN_ALIASES[normalized]
    df = df.rename(columns=rename)

    if "AirTC_Max" not in df.columns and "AirTC_Avg" in df.columns:
        df["AirTC_Max"] = df["AirTC_Avg"]

    if "AirTC_Min" not in df.columns and "AirTC_Avg" in df.columns:
        df["AirTC_Min"] = df["AirTC_Avg"]

    if "RH_Max" not in df.columns and "RH_Avg" in df.columns:
        df["RH_Max"] = df["RH_Avg"]

    if "RH_Min" not in df.columns and "RH_Avg" in df.columns:
        df["RH_Min"] = df["RH_Avg"]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "A planilha não contém todas as colunas necessárias. "
            "Faltam: " + ", ".join(missing) +
            ". Colunas esperadas: TIMESTAMP, AirTC_Avg, AirTC_Max, AirTC_Min, "
            "RH_Max, RH_Min, Vento_Avg, Chuva_Tot e Rn_Avg."
        )

    df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], errors="coerce", dayfirst=True)
    for col in REQUIRED_COLUMNS:
        if col != "TIMESTAMP":
                valores = df[col].astype(str).str.strip()
                df[col] = pd.to_numeric(
                valores.str.replace(",", ".", regex=False),
                errors="coerce"
        )

    df = df.dropna(subset=["TIMESTAMP"]).copy()
    if df.empty:
        raise ValueError("Não foram encontradas datas/horários válidos na coluna TIMESTAMP.")
    df["DATA"] = df["TIMESTAMP"].dt.date
    return df.sort_values("TIMESTAMP")
