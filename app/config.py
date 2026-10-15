import os
from dotenv import load_dotenv
load_dotenv()
APP_NAME = os.getenv("APP_NAME", "Agente de Irrigação")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./instance/irrigacao.db")
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE-ME-BEFORE-DEPLOYMENT-USE-A-LONG-RANDOM-SECRET")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
ALTITUDE_M = float(os.getenv("ALTITUDE_M", "220"))
ALTURA_VENTO_M = float(os.getenv("ALTURA_VENTO_M", "2"))
EFICIENCIA_SISTEMA = float(os.getenv("EFICIENCIA_SISTEMA", "0.90"))
VAZAO_EMISSOR_LH = float(os.getenv("VAZAO_EMISSOR_LH", "0.98"))
EMISSORES_POR_PLANTA = int(os.getenv("EMISSORES_POR_PLANTA", "3"))
ESPACAMENTO_LINHAS_M = float(os.getenv("ESPACAMENTO_LINHAS_M", "1.00"))
ESPACAMENTO_PLANTAS_M = float(os.getenv("ESPACAMENTO_PLANTAS_M", "0.50"))
VAZAO_PLANTA_LH = VAZAO_EMISSOR_LH * EMISSORES_POR_PLANTA
AREA_POR_PLANTA_M2 = float(os.getenv("AREA_EFETIVA_POR_PLANTA_M2", "0.16"))
KC_ESTADIOS = {"Inicial": 0.45, "Vegetativo": 0.75, "Floração/frutificação": 1.05, "Maturação/final": 0.85}
