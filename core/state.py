"""
Estado compartilhado entre páginas: seletor de "liga ativa" na sidebar.
"""

import streamlit as st

from core.database import get_conn
from core.queries import lista_ligas


def selecionar_liga_ativa():
    """Mostra o seletor de liga ativa na sidebar e retorna (liga_id, liga_nome).

    Deve ser chamado no topo de toda página que precisa da liga ativa.
    """
    st.sidebar.markdown("### 🏆 Liga ativa")
    ligas = lista_ligas()

    if ligas.empty:
        st.sidebar.info("Nenhuma liga cadastrada ainda.")
        with st.sidebar.form("form_primeira_liga"):
            nome = st.text_input("Nome da primeira liga")
            criar = st.form_submit_button("Criar liga")
            if criar and nome.strip():
                conn = get_conn()
                conn.execute("INSERT INTO ligas (nome) VALUES (?)", (nome.strip(),))
                conn.commit()
                conn.close()
                st.rerun()
        st.stop()

    nomes = ligas["nome"].tolist()
    if "liga_ativa_nome" not in st.session_state or st.session_state["liga_ativa_nome"] not in nomes:
        st.session_state["liga_ativa_nome"] = nomes[0]

    escolha = st.sidebar.selectbox(
        "Escolha a liga",
        nomes,
        index=nomes.index(st.session_state["liga_ativa_nome"]),
    )
    st.session_state["liga_ativa_nome"] = escolha
    liga_id = int(ligas.loc[ligas["nome"] == escolha, "id"].iloc[0])
    return liga_id, escolha
