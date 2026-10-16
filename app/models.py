from .config import VAZAO_PLANTA_LH
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, UniqueConstraint, LargeBinary
from .db import Base
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(300), nullable=False)
    active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
class DailyRecord(Base):
    __tablename__ = "daily_records"
    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False, unique=True, index=True)
    arquivo_estacao = Column(String, nullable=False)
    estadio = Column(String, nullable=False)
    kc = Column(Float, nullable=False)
    eto_mm = Column(Float, nullable=False)
    etc_mm = Column(Float, nullable=False)

    # Resultados de irrigação com e sem Kl
    etc_com_kl_mm = Column(Float, nullable=True)
    etc_sem_kl_mm = Column(Float, nullable=True)

    lamina_bruta_com_kl_mm = Column(Float, nullable=True)
    lamina_bruta_sem_kl_mm = Column(Float, nullable=True)

    volume_planta_com_kl_l = Column(Float, nullable=True)
    volume_planta_sem_kl_l = Column(Float, nullable=True)

    tempo_irrigacao_com_kl_min = Column(Float, nullable=True)
    tempo_irrigacao_sem_kl_min = Column(Float, nullable=True)
    @property
    def tempo_irrigacao_campo_min(self):
        """Tempo sem Kl calculado com 0,50 m² por planta."""
        if self.lamina_bruta_sem_kl_mm is None:
            return None

        area_campo_m2 = 0.50
        vazao_planta_l_h = VAZAO_PLANTA_LH

        return (
            self.lamina_bruta_sem_kl_mm
            * area_campo_m2
            / vazao_planta_l_h
            * 60
        )

    temperatura_media_c = Column(Float)
    temperatura_max_c = Column(Float)
    temperatura_min_c = Column(Float)
    rh_max = Column(Float)
    rh_min = Column(Float)
    vento_ms = Column(Float)
    chuva_mm = Column(Float)
    chuva_efetiva_mm = Column(Float)
    rn_mj_m2_dia = Column(Float)
    necessidade_liquida_mm = Column(Float)
    lamina_bruta_mm = Column(Float)
    volume_planta_l = Column(Float)
    tempo_irrigacao_min = Column(Float)
    cobertura_dados = Column(Float)
    status_dados = Column(String, default="OK")
    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    atualizado_por_id = Column(Integer, ForeignKey("users.id"), nullable=True)
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    data_registro = Column(Date, nullable=False, index=True)
    acao = Column(String(30), nullable=False)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    usuario_nome = Column(String(80), nullable=False)
    arquivo = Column(String, nullable=False)
    alterado_em = Column(DateTime, nullable=False, default=datetime.utcnow)
    antes_json = Column(Text, nullable=True)
    depois_json = Column(Text, nullable=False)
class PendingImport(Base):
    __tablename__ = "pending_imports"
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_content = Column(LargeBinary, nullable=False)
    estadio = Column(String, nullable=False)
    conflicts_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    drenagem_data = Column(Date, nullable=True)
    drenagem_leitura_percentual = Column(Float, nullable=True)
class DrainageRecord(Base):
    __tablename__ = "drainage_records"

    id = Column(Integer, primary_key=True)
    data = Column(Date, nullable=False, index=True)
    leitura_percentual = Column(Float, nullable=False)
    umidade_volumetrica = Column(Float, nullable=False)
    arquivo_origem = Column(String, nullable=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    criado_em = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
