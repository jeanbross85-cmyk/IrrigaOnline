"""Cria usuário de acesso: python scripts/create_user.py nome_usuario"""
import getpass, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import init_db, SessionLocal
from app.models import User
from app.security import hash_password
from sqlalchemy import select

def main():
    if len(sys.argv) != 2:
        print("Uso: python scripts/create_user.py nome_usuario"); raise SystemExit(2)
    username=sys.argv[1].strip()
    if not username or len(username)>80:
        print("Nome de usuário inválido (1 a 80 caracteres)."); raise SystemExit(2)
    password=getpass.getpass("Nova senha (mínimo 12 caracteres): ")
    confirm=getpass.getpass("Repita a senha: ")
    if password != confirm or len(password)<12:
        print("As senhas devem coincidir e ter pelo menos 12 caracteres."); raise SystemExit(2)
    init_db()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username==username)):
            print("Esse usuário já existe."); raise SystemExit(2)
        db.add(User(username=username,password_hash=hash_password(password),active=1)); db.commit()
    print(f"Usuário '{username}' criado.")
if __name__ == "__main__": main()
