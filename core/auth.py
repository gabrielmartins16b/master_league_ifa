"""
Autenticacao: uma UNICA tela de login antes do app. Enquanto o usuario nao
loga, nenhum menu/pagina do app e mostrado - so a tela de login. Depois de
logar, o Home.py monta a navegacao de acordo com o papel do usuario.

Dois papeis:
- admin: acesso total (cadastra, edita, apaga qualquer dado).
- visualizador: vinculado a UM clube_id especifico, ve so aquele clube.
"""

import streamlit as st

from core.database import _verificar_senha, get_conn


def verificar_login(usuario, senha):
    """Retorna (papel, clube_id) se as credenciais forem validas, senao None."""
    conn = get_conn()
    row = conn.execute(
        "SELECT papel, senha_hash, clube_id FROM usuarios WHERE usuario = ?", (usuario,)
    ).fetchone()
    conn.close()
    if row and _verificar_senha(senha, row[1]):
        return row[0], row[2]
    return None


def usuario_logado():
    return st.session_state.get("usuario")


def papel_logado():
    return st.session_state.get("papel")


def clube_logado_id():
    """clube_id do usuario logado, se for visualizador vinculado a um clube."""
    return st.session_state.get("clube_id")


def eh_admin():
    return papel_logado() == "admin"


def tela_login():
    """Renderiza a UNICA tela de login do app. Chamada apenas pelo Home.py,
    antes de qualquer menu ou pagina existir."""
    st.title("\u26bd Master League")
    st.subheader("Login")
    st.caption(
        "Administradores tem acesso total. Visualizadores enxergam apenas "
        "o clube ao qual foram vinculados."
    )

    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        with st.form("form_login"):
            usuario = st.text_input("Usu\u00e1rio")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar", use_container_width=True)
            if entrar:
                resultado = verificar_login(usuario.strip(), senha)
                if resultado:
                    papel, clube_id = resultado
                    st.session_state["usuario"] = usuario.strip()
                    st.session_state["papel"] = papel
                    st.session_state["clube_id"] = clube_id
                    st.rerun()
                else:
                    st.error("Usu\u00e1rio ou senha inv\u00e1lidos.")


def fazer_logout():
    for chave in ("usuario", "papel", "clube_id"):
        st.session_state.pop(chave, None)
    st.rerun()