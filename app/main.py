from pathlib import Path
from datetime import datetime
import json, re, shutil, secrets, uuid
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import select, desc
from sqlalchemy.exc import IntegrityError
from .config import APP_NAME, KC_ESTADIOS, SECRET_KEY, COOKIE_SECURE
from .db import SessionLocal, init_db
from .models import DailyRecord, User, AuditLog, PendingImport
from .security import current_user, require_user, verify_password, ensure_csrf
from .importer import read_meteorological_xlsx
from .calculations import daily_summary, irrigation, coverage_status
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
PENDING_DIR = PROJECT_DIR / "instance" / "pending"
DATA_DIR.mkdir(exist_ok=True); PENDING_DIR.mkdir(parents=True, exist_ok=True)
app = FastAPI(title=APP_NAME)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax", https_only=COOKIE_SECURE, max_age=60*60*8)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
@app.on_event("startup")
def startup(): init_db()
def template(name, request, **kwargs):
    if "csrf_token" not in request.session: request.session["csrf_token"] = secrets.token_urlsafe(32)
    return templates.TemplateResponse(name, {"request": request, "app_name": APP_NAME, "user": current_user(request), "csrf_token": request.session["csrf_token"], **kwargs})
def auth_redirect(request):
    if not current_user(request): return RedirectResponse("/login", status_code=303)
    return None
@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    if current_user(request): return RedirectResponse("/", status_code=303)
    return template("login.html", request, error=None)
@app.post("/login", response_class=HTMLResponse)
def login_post(request: Request, username: str = Form(...), password: str = Form(...), csrf_token: str = Form(...)):
    ensure_csrf(request, csrf_token)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == username.strip()))
        if not user or not user.active or not verify_password(password, user.password_hash):
            return template("login.html", request, error="Usuário ou senha inválidos.")
        request.session.clear(); request.session["user_id"] = user.id; request.session["csrf_token"] = secrets.token_urlsafe(32)
    return RedirectResponse("/", status_code=303)
@app.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    ensure_csrf(request, csrf_token); request.session.clear()
    return RedirectResponse("/login", status_code=303)
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if auth_redirect(request): return auth_redirect(request)
    with SessionLocal() as db: records = list(db.scalars(select(DailyRecord).order_by(desc(DailyRecord.data)).limit(30)))
    return template("dashboard.html", request, records=records, latest=records[0] if records else None)
@app.get("/historico", response_class=HTMLResponse)
def historico(request: Request):
    if auth_redirect(request): return auth_redirect(request)
    with SessionLocal() as db: records = list(db.scalars(select(DailyRecord).order_by(desc(DailyRecord.data))))
    return template("historico.html", request, records=records)
def records_as_json(records):
    result=[]
    for r in records:
        result.append({"data":r.data.isoformat(),"eto":r.eto_mm,"etc":r.etc_mm,"temperatura":r.temperatura_media_c,"chuva":r.chuva_mm,"lamina":r.lamina_bruta_mm,"tempo":r.tempo_irrigacao_min,"cobertura":r.cobertura_dados,"status":r.status_dados})
    return result
@app.get("/api/historico")
def api_historico(request: Request):
    if auth_redirect(request): return auth_redirect(request)
    with SessionLocal() as db: records=list(db.scalars(select(DailyRecord).order_by(DailyRecord.data)))
    return records_as_json(records)
@app.get("/importar", response_class=HTMLResponse)
def importar_get(request: Request):
    if auth_redirect(request): return auth_redirect(request)
    return template("importar.html", request, message=None, error=None, conflicts=None, pending_id=None)
def parse_filename(filename):
    return bool(re.fullmatch(r"Dados_meteorologicos_\d{4}-\d{2}-\d{2}\.xlsx", filename, flags=re.IGNORECASE))
def build_day_values(day, day_df, estadio, filename, user_id):
    s=daily_summary(day_df); kc=KC_ESTADIOS[estadio]; irr=irrigation(s["eto"],kc,s["chuva"])
    return {"data":day,"arquivo_estacao":filename,"estadio":estadio,"kc":kc,"eto_mm":s["eto"],"etc_mm":irr["etc"],"temperatura_media_c":s["temperatura_media"],"temperatura_max_c":s["temperatura_max"],"temperatura_min_c":s["temperatura_min"],"rh_max":s["rh_max"],"rh_min":s["rh_min"],"vento_ms":s["vento"],"chuva_mm":s["chuva"],"chuva_efetiva_mm":irr["chuva_efetiva"],"rn_mj_m2_dia":s["rn"],"necessidade_liquida_mm":irr["necessidade_liquida"],"lamina_bruta_mm":irr["lamina_bruta"],"volume_planta_l":irr["volume_planta"],"tempo_irrigacao_min":irr["tempo_irrigacao"],"cobertura_dados":s["cobertura"],"status_dados":coverage_status(s["cobertura"]),"atualizado_por_id":user_id}
def snapshot(record):
    if not record: return None
    return {c.name:(getattr(record,c.name).isoformat() if hasattr(getattr(record,c.name),"isoformat") else getattr(record,c.name)) for c in DailyRecord.__table__.columns}
def apply_import(path, filename, estadio, user):
    df=read_meteorological_xlsx(path)
    if df.empty: raise ValueError("O arquivo não contém registros com data/hora válida.")
    days=[]
    with SessionLocal() as db:
        try:
            # Unique date key is the final guard against duplicate official days.
            for day, day_df in df.groupby("DATA"):
                values=build_day_values(day,day_df,estadio,filename,user["id"])
                rec=db.scalar(select(DailyRecord).where(DailyRecord.data==day).with_for_update())
                before=snapshot(rec)
                action="ATUALIZACAO" if rec else "CRIACAO"
                if rec is None:
                    rec=DailyRecord(**values); db.add(rec)
                else:
                    for k,v in values.items(): setattr(rec,k,v)
                db.flush()
                db.add(AuditLog(data_registro=day,acao=action,usuario_id=user["id"],usuario_nome=user["username"],arquivo=filename,antes_json=json.dumps(before,ensure_ascii=False,default=str) if before else None,depois_json=json.dumps(snapshot(rec),ensure_ascii=False,default=str)))
                days.append(day)
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise ValueError("Outra pessoa atualizou uma das datas ao mesmo tempo. O banco protegeu o histórico contra duplicação; atualize a página e repita a importação, confirmando novamente as datas existentes.") from exc
    return len(days), days
@app.post("/importar", response_class=HTMLResponse)
async def importar_post(request: Request, arquivo: UploadFile = File(...), estadio: str = Form("Vegetativo"), csrf_token: str = Form(...)):
    redirect=auth_redirect(request)
    if redirect: return redirect
    ensure_csrf(request,csrf_token); user=current_user(request)
    if not arquivo.filename or not arquivo.filename.lower().endswith(".xlsx"):
        return template("importar.html",request,message=None,error="Selecione um arquivo Excel .xlsx.",conflicts=None,pending_id=None)
    safe_name=Path(arquivo.filename).name
    if not parse_filename(safe_name):
        return template("importar.html",request,message=None,error="O nome deve seguir o padrão Dados_meteorologicos_aaaa-mm-dd.xlsx, por exemplo Dados_meteorologicos_2026-10-09.xlsx.",conflicts=None,pending_id=None)
    if estadio not in KC_ESTADIOS: raise HTTPException(400,"Estádio inválido")
    file_bytes=await arquivo.read()
    if len(file_bytes) > 25 * 1024 * 1024:
        return template("importar.html",request,message=None,error="O arquivo excede o limite de 25 MB.",conflicts=None,pending_id=None)
    pending_path=PENDING_DIR/f"{uuid.uuid4()}.xlsx"
    pending_path.write_bytes(file_bytes)
    pending_id=None
    try:
        df=read_meteorological_xlsx(pending_path)
        if df.empty: raise ValueError("O arquivo não contém registros com data/hora válida.")
        dates=sorted(set(df["DATA"].tolist()))
        with SessionLocal() as db:
            existing=list(db.scalars(select(DailyRecord.data).where(DailyRecord.data.in_(dates))))
            if existing:
                pending_id=str(uuid.uuid4())
                db.add(PendingImport(id=pending_id,user_id=user["id"],filename=safe_name,file_content=file_bytes,estadio=estadio,conflicts_json=json.dumps([d.isoformat() for d in sorted(existing)]))); db.commit()
                return template("importar.html",request,message=None,error=None,conflicts=[d.strftime("%d/%m/%Y") for d in sorted(existing)],pending_id=pending_id)
        count,days=apply_import(pending_path,safe_name,estadio,user)
        return template("importar.html",request,message=f"Importação concluída: {count} dia(s) gravado(s) no histórico compartilhado.",error=None,conflicts=None,pending_id=None)
    except Exception as exc:
        return template("importar.html",request,message=None,error=f"Não foi possível processar o arquivo: {exc}",conflicts=None,pending_id=None)
    finally:
        # Keep file only if saved as a pending import for explicit confirmation.
        with SessionLocal() as db: keep=(pending_id is not None and db.get(PendingImport,pending_id) is not None)
        if not keep: pending_path.unlink(missing_ok=True)
@app.post("/importar/confirmar", response_class=HTMLResponse)
def confirmar_importacao(request: Request, pending_id: str = Form(...), csrf_token: str = Form(...)):
    redirect=auth_redirect(request)
    if redirect: return redirect
    ensure_csrf(request,csrf_token); user=current_user(request)
    with SessionLocal() as db:
        pending=db.get(PendingImport,pending_id)
        if not pending or pending.user_id != user["id"]: raise HTTPException(404,"Importação pendente não encontrada ou não pertence a este usuário.")
        filename=pending.filename; estadio=pending.estadio; file_bytes=bytes(pending.file_content)
        previously_shown=set(json.loads(pending.conflicts_json or "[]"))
    path=PENDING_DIR/f"confirm-{uuid.uuid4()}.xlsx"
    path.write_bytes(file_bytes)
    try:
        df=read_meteorological_xlsx(path)
        dates=sorted(set(df["DATA"].tolist()))
        with SessionLocal() as db:
            now_existing=list(db.scalars(select(DailyRecord.data).where(DailyRecord.data.in_(dates))))
            newly_conflicting=[d for d in now_existing if d.isoformat() not in previously_shown]
            if newly_conflicting:
                with SessionLocal() as update_db:
                    staged=update_db.get(PendingImport,pending_id)
                    if staged:
                        staged.conflicts_json=json.dumps([d.isoformat() for d in sorted(now_existing)])
                        update_db.commit()
                return template("importar.html",request,message=None,error=None,conflicts=[d.strftime("%d/%m/%Y") for d in sorted(now_existing)],pending_id=pending_id)
        # Explicit confirmation permits replacement; before/after snapshots are audited.
        count,days=apply_import(path,filename,estadio,user)
        with SessionLocal() as db:
            pending=db.get(PendingImport,pending_id)
            if pending: db.delete(pending); db.commit()
        return template("importar.html",request,message=f"Atualização confirmada: {count} dia(s) inserido(s) ou substituído(s). O histórico de alterações foi registrado.",error=None,conflicts=None,pending_id=None)
    except Exception as exc:
        return template("importar.html",request,message=None,error=f"Não foi possível confirmar a atualização: {exc}",conflicts=None,pending_id=pending_id)
    finally:
        path.unlink(missing_ok=True)
@app.post("/importar/cancelar", response_class=HTMLResponse)
def cancelar_importacao(request: Request,pending_id: str=Form(...),csrf_token: str=Form(...)):
    redirect=auth_redirect(request)
    if redirect:return redirect
    ensure_csrf(request,csrf_token); user=current_user(request)
    with SessionLocal() as db:
        pending=db.get(PendingImport,pending_id)
        if pending and pending.user_id==user["id"]:
            db.delete(pending); db.commit()
    return template("importar.html",request,message="Importação cancelada; o histórico oficial não foi alterado.",error=None,conflicts=None,pending_id=None)
@app.get("/configuracoes", response_class=HTMLResponse)
def configuracoes(request: Request):
    redirect=auth_redirect(request)
    if redirect:return redirect
    return template("configuracoes.html",request,kc=KC_ESTADIOS)
@app.get("/auditoria", response_class=HTMLResponse)
def auditoria(request: Request):
    redirect=auth_redirect(request)
    if redirect:return redirect
    with SessionLocal() as db: logs=list(db.scalars(select(AuditLog).order_by(desc(AuditLog.alterado_em)).limit(300)))
    return template("auditoria.html",request,logs=logs)
