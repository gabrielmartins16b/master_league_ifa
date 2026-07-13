"""
Conexao com o banco (Postgres / Supabase), criacao de tabelas e migracao leve.
 
A connection string vem de st.secrets["DATABASE_URL"] (arquivo
.streamlit/secrets.toml) ou da variavel de ambiente DATABASE_URL.
 
_PGConn e um adaptador fino em volta da conexao psycopg2 que imita o jeito
de usar do sqlite3 (conn.execute(...).fetchone()), traduzindo os
placeholders '?' (estilo sqlite, usados em todo o queries.py) para '%s'
(estilo psycopg2/Postgres). Assim quase nada em queries.py precisou mudar.
"""
 
import hashlib
import os
from datetime import date
 
import bcrypt
import psycopg2
import streamlit as st
 
 
def _connection_string():
    try:
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass  # sem secrets.toml configurado ainda
 
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL não configurada. Crie o arquivo .streamlit/secrets.toml "
            "com a chave DATABASE_URL = \"postgresql://...\" (connection string do Supabase) "
            "ou defina a variável de ambiente DATABASE_URL."
        )
    return url
 
 
class _PGConn:
    """Adaptador: conn.execute(query_com_?, params) -> cursor psycopg2."""
 
    def __init__(self, raw):
        self.raw = raw  # conexão psycopg2 "de verdade", usada pelo pandas
 
    def execute(self, query, params=()):
        cur = self.raw.cursor()
        cur.execute(query.replace("?", "%s"), params)
        return cur
 
    def cursor(self):
        return self.raw.cursor()
 
    def commit(self):
        self.raw.commit()
 
    def rollback(self):
        self.raw.rollback()
 
    def close(self):
        self.raw.close()
 
 
def get_conn():
    raw = psycopg2.connect(_connection_string())
    return _PGConn(raw)
 
 
def _hash_senha(senha):
    """Gera um hash bcrypt (com salt aleatório embutido) a partir da senha em texto puro."""
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
 
 
def _verificar_senha(senha, hash_salvo):
    """Confere se a senha em texto puro bate com o hash bcrypt salvo no banco.
    Também aceita hashes antigos em SHA-256 (de antes da migração para bcrypt),
    só para não travar contas já existentes — eles nunca são gerados de novo."""
    try:
        return bcrypt.checkpw(senha.encode("utf-8"), hash_salvo.encode("utf-8"))
    except ValueError:
        # hash_salvo não é um hash bcrypt válido -> provavelmente é um SHA-256 antigo
        return hashlib.sha256(senha.encode("utf-8")).hexdigest() == hash_salvo
 
 
def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ligas (
            id BIGSERIAL PRIMARY KEY,
            nome TEXT NOT NULL UNIQUE,
            descricao TEXT
        );
 
        CREATE TABLE IF NOT EXISTS clubes (
            id BIGSERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            tecnico TEXT,
            saldo DOUBLE PRECISION NOT NULL DEFAULT 0,
            liga_id BIGINT REFERENCES ligas(id),
            UNIQUE(nome, liga_id)
        );
 
        CREATE TABLE IF NOT EXISTS jogadores (
            id BIGSERIAL PRIMARY KEY,
            nome TEXT NOT NULL,
            posicao TEXT,
            overall INTEGER,
            valor_mercado DOUBLE PRECISION DEFAULT 0,
            salario DOUBLE PRECISION DEFAULT 0,
            clube_id BIGINT REFERENCES clubes(id),
            liga_id BIGINT REFERENCES ligas(id)
        );
 
        CREATE TABLE IF NOT EXISTS transferencias (
            id BIGSERIAL PRIMARY KEY,
            jogador_id BIGINT REFERENCES jogadores(id),
            clube_origem_id BIGINT,
            clube_destino_id BIGINT,
            valor DOUBLE PRECISION NOT NULL,
            data TEXT NOT NULL
        );
 
        CREATE TABLE IF NOT EXISTS patrocinios (
            id BIGSERIAL PRIMARY KEY,
            clube_id BIGINT REFERENCES clubes(id),
            patrocinador TEXT NOT NULL,
            valor DOUBLE PRECISION NOT NULL,
            tipo TEXT,
            data TEXT NOT NULL
        );
 
        CREATE TABLE IF NOT EXISTS financeiro (
            id BIGSERIAL PRIMARY KEY,
            clube_id BIGINT REFERENCES clubes(id),
            descricao TEXT,
            valor DOUBLE PRECISION NOT NULL,
            categoria TEXT,
            data TEXT NOT NULL
        );
 
        CREATE TABLE IF NOT EXISTS usuarios (
            id BIGSERIAL PRIMARY KEY,
            usuario TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            papel TEXT NOT NULL CHECK (papel IN ('admin', 'visualizador')),
            clube_id BIGINT REFERENCES clubes(id)
        );
        """
    )
    conn.commit()
 
    # Migração leve: Postgres suporta "ADD COLUMN IF NOT EXISTS" nativamente,
    # então não precisamos mais checar PRAGMA table_info como no sqlite.
    cur.execute("ALTER TABLE clubes ADD COLUMN IF NOT EXISTS liga_id BIGINT REFERENCES ligas(id)")
    cur.execute("ALTER TABLE jogadores ADD COLUMN IF NOT EXISTS liga_id BIGINT REFERENCES ligas(id)")
    cur.execute("ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS clube_id BIGINT REFERENCES clubes(id)")
    conn.commit()
 
    # Se existem clubes órfãos (liga_id nulo) de uma versão antiga sem ligas,
    # cria uma liga padrão e associa tudo a ela — nenhum dado é perdido.
    tem_liga = conn.execute("SELECT COUNT(*) FROM ligas").fetchone()[0]
    tem_clube_orfao = conn.execute("SELECT COUNT(*) FROM clubes WHERE liga_id IS NULL").fetchone()[0]
    if tem_clube_orfao > 0:
        if tem_liga == 0:
            conn.execute(
                "INSERT INTO ligas (nome, descricao) VALUES (?,?)",
                ("Liga Padrão", "Criada automaticamente na migração"),
            )
            conn.commit()
        liga_padrao_id = conn.execute("SELECT id FROM ligas ORDER BY id LIMIT 1").fetchone()[0]
        conn.execute("UPDATE clubes SET liga_id = ? WHERE liga_id IS NULL", (liga_padrao_id,))
        conn.execute("UPDATE jogadores SET liga_id = ? WHERE liga_id IS NULL", (liga_padrao_id,))
        conn.commit()
 
    conn.close()
    _seed_usuarios_padrao()
 
 
def _seed_usuarios_padrao():
    """Cria os usuários padrão na primeira vez que o app roda, para não
    deixar o sistema sem acesso nenhum. TROQUE ESSAS SENHAS depois do primeiro
    login (veja instruções no README)."""
    conn = get_conn()
    tem_usuario = conn.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if tem_usuario == 0:
        conn.execute(
            "INSERT INTO usuarios (usuario, senha_hash, papel) VALUES (?,?,?)",
            ("admin", _hash_senha("admin123"), "admin"),
        )
        conn.execute(
            "INSERT INTO usuarios (usuario, senha_hash, papel) VALUES (?,?,?)",
            ("visualizador", _hash_senha("visualizador123"), "visualizador"),
        )
        conn.commit()
    conn.close()
 
 
def registrar_lancamento(conn, clube_id, descricao, valor, categoria):
    """Lança uma movimentação no livro financeiro e ajusta o saldo do clube."""
    conn.execute(
        "INSERT INTO financeiro (clube_id, descricao, valor, categoria, data) VALUES (?,?,?,?,?)",
        (clube_id, descricao, valor, categoria, date.today().isoformat()),
    )
    conn.execute("UPDATE clubes SET saldo = saldo + ? WHERE id = ?", (valor, clube_id))
 