import os
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# CONFIGURAÇÕES GERAIS DA APLICAÇÃO
# ============================================================

APP_NAME = os.getenv("APP_NAME", "Agente de Irrigação")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./instance/irrigacao.db"
)

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "CHANGE-ME-BEFORE-DEPLOYMENT-USE-A-LONG-RANDOM-SECRET"
)

COOKIE_SECURE = (
    os.getenv("COOKIE_SECURE", "false").lower() == "true"
)

# ============================================================
# CONFIGURAÇÕES METEOROLÓGICAS
# ============================================================

ALTITUDE_M = float(os.getenv("ALTITUDE_M", "220"))
ALTURA_VENTO_M = float(os.getenv("ALTURA_VENTO_M", "6"))

# ============================================================
# PARÂMETROS DO SISTEMA DE IRRIGAÇÃO
# ============================================================

EFICIENCIA_SISTEMA = float(
    os.getenv("EFICIENCIA_SISTEMA", "0.96")
)

VAZAO_EMISSOR_LH = float(
    os.getenv("VAZAO_EMISSOR_LH", "1.335")
)

EMISSORES_POR_PLANTA = int(
    os.getenv("EMISSORES_POR_PLANTA", "3")
)

VAZAO_PLANTA_LH = (
    VAZAO_EMISSOR_LH * EMISSORES_POR_PLANTA
)

ESPACAMENTO_LINHAS_M = float(
    os.getenv("ESPACAMENTO_LINHAS_M", "1.00")
)

ESPACAMENTO_PLANTAS_M = float(
    os.getenv("ESPACAMENTO_PLANTAS_M", "0.50")
)

# ============================================================
# PARÂMETROS DAS REGRAS DE CÁLCULO
# ============================================================

# Método 1: ETc ajustada pelo fator de área molhada.
FATOR_AREA_MOLHADA = float(
    os.getenv("FATOR_AREA_MOLHADA", "0.32")
)

# Métodos 1 e 2: área efetiva considerada por planta.
AREA_POR_PLANTA_M2 = float(
    os.getenv("AREA_EFETIVA_POR_PLANTA_M2", "0.16")
)

# Método 3: área de campo considerada por planta.
AREA_CAMPO_POR_PLANTA_M2 = float(
    os.getenv("AREA_CAMPO_POR_PLANTA_M2", "0.50")
)

# ============================================================
# COEFICIENTES DE CULTURA (Kc) — QUIABO
# ============================================================

KC_ESTADIOS = {
    "Inicial": 0.45,
    "Vegetativo": 0.80,
    "Floração/frutificação": 1.05,
    "Maturação/final": 0.85,
}
