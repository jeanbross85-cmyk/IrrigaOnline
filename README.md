# Agente de Irrigação Web — versão multiusuário (base para implantação)

## O que esta versão prepara
- Login individual por usuário; nenhuma conta ou senha padrão embutida.
- PostgreSQL configurável por `DATABASE_URL` e compartilhamento do mesmo histórico oficial entre usuários.
- Uma linha oficial por data (`daily_records.data` tem restrição `UNIQUE`), portanto os gráficos consultam um histórico diário único.
- Se a importação contiver datas já registradas, o sistema pausa e solicita confirmação explícita antes de substituir.
- Auditoria registra usuário, data afetada, arquivo, ação e snapshots anterior/novo para cada criação ou atualização.
- Importações pendentes ficam associadas ao usuário que as iniciou; outro usuário não pode confirmar/cancelar essa importação.
- Sessão assinada, expiração em 8 horas, token CSRF nos formulários e cookie seguro configurável para HTTPS.

## Importante antes de colocar online
Este projeto é uma base de desenvolvimento e precisa ser implantado e testado no ambiente real antes de receber dados operacionais. Configure PostgreSQL gerenciado, HTTPS, `SECRET_KEY` forte, backups e monitoramento. Defina `COOKIE_SECURE=true` somente atrás de HTTPS. Restrinja acesso de rede ao banco; ele não deve ficar público. Faça revisão de segurança e validação agronômica dos cálculos. Os quatro usuários não são criados automaticamente.

## Configuração local para desenvolvimento
1. Instale Python 3.11 ou 3.12.
2. Crie ambiente virtual e instale dependências:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

3. Para testar localmente, pode configurar temporariamente `DATABASE_URL=sqlite:///./instance/irrigacao.db` no `.env`. Para uso remoto multiusuário, configure PostgreSQL compartilhado, por exemplo `postgresql+psycopg://usuario:senha@host:5432/irrigacao`.
4. Gere uma chave secreta forte e defina `SECRET_KEY` no `.env`.
5. Crie as contas, uma por pessoa:

```powershell
python scripts/create_user.py usuario1
python scripts/create_user.py usuario2
python scripts/create_user.py usuario3
python scripts/create_user.py usuario4
```

O script solicita a senha sem exibi-la e exige pelo menos 12 caracteres.
6. Inicie para desenvolvimento local:

```powershell
python -m uvicorn app.main:app --reload
```

Abra `http://127.0.0.1:8000`. O `--reload` é somente para desenvolvimento; não o use em produção. Para o acesso remoto, publique a aplicação em um serviço de hospedagem com HTTPS e configure o banco PostgreSQL centralizado. Não basta executar o app no computador de um usuário se ele estiver desligado ou desconectado.

## Importação de dados
- Nome: `Dados_meteorologicos_aaaa-mm-dd.xlsx`, por exemplo `Dados_meteorologicos_2026-10-09.xlsx`.
- Lê a primeira aba, com cabeçalhos na primeira linha e coluna de data/hora `TIMESTAMP` (ou alias reconhecido pelo importador).
- O estádio selecionado aplica o Kc a todos os dias da planilha.
- Se houver datas já existentes, uma página de confirmação lista as datas conflitantes. Confirmar substitui os valores e cria snapshots de auditoria; cancelar preserva os dados oficiais atuais.
- A chave única da data protege contra duplicação. Em uma corrida simultânea de inserção da mesma data, a transação concorrente pode ser recusada com mensagem para repetir a importação; revise o conflito antes de tentar novamente.

## Arquitetura
- `app/main.py`: rotas, autenticação de sessão, importação e auditoria.
- `app/models.py`: usuários, histórico diário, auditoria e importações pendentes.
- `app/security.py`: hash de senha PBKDF2, validação de senha e sessão de usuário.
- `app/db.py`: SQLAlchemy e conexão configurável.
- `app/calculations.py`: cálculos de irrigação herdados do protótipo.
- `scripts/create_user.py`: criação manual de usuários.

## Limitações agronômicas que continuam exigindo validação
- A cobertura é estimada como registros/144, assumindo intervalo de 10 minutos.
- `Chuva_Tot` é somada como total por intervalo; confirme que não é um acumulado repetido.
- A chuva efetiva usa aproximação `min(chuva, ETc)`, não um balanço hídrico do solo.
- Os Kc são valores herdados do protótipo e precisam de validação para quiabo e para as condições locais.
- A recomendação não deve ser usada como comando automático de irrigação sem validação dos dados e do método.
