import sqlite3

import streamlit as st

from core.auth import eh_admin
from core.queries import lista_ligas_com_totais, criar_liga, editar_liga, lista_ligas
from core.state import selecionar_liga_ativa

liga_id, liga_nome = selecionar_liga_ativa()
st.header("\U0001F3C6 Ligas")

if not eh_admin():
    st.info("Modo visualiza\u00e7\u00e3o: apenas administradores podem cadastrar ou editar ligas.")
    st.stop()

with st.expander("\u2795 Cadastrar nova liga"):
    with st.form("form_liga"):
        nome = st.text_input("Nome da liga")
        descricao = st.text_area("Descri\u00e7\u00e3o (opcional)", placeholder="Ex: Temporada 2026, divis\u00e3o principal...")
        enviado = st.form_submit_button("Cadastrar")
        if enviado:
            if not nome.strip():
                st.error("Informe o nome da liga.")
            else:
                try:
                    criar_liga(nome, descricao)
                    st.success(f"Liga '{nome}' criada! Selecione ela na barra lateral para come\u00e7ar a usar.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("J\u00e1 existe uma liga com esse nome.")

st.subheader("Ligas cadastradas")
st.dataframe(lista_ligas_com_totais(), use_container_width=True)

st.divider()
with st.expander("\u270F\uFE0F Editar liga"):
    ligas = lista_ligas()
    if ligas.empty:
        st.caption("Nenhuma liga cadastrada.")
    else:
        liga_edit_nome = st.selectbox("Escolha a liga a editar", ligas["nome"], key="edit_liga_sel")
        liga_edit_id = int(ligas.loc[ligas["nome"] == liga_edit_nome, "id"].iloc[0])
        with st.form("form_editar_liga"):
            novo_nome = st.text_input("Nome", value=liga_edit_nome)
            nova_descricao = st.text_area("Descri\u00e7\u00e3o")
            salvar = st.form_submit_button("Salvar altera\u00e7\u00f5es")
            if salvar:
                if not novo_nome.strip():
                    st.error("Informe o nome da liga.")
                else:
                    try:
                        editar_liga(liga_edit_id, novo_nome, nova_descricao)
                        if st.session_state.get("liga_ativa_nome") == liga_edit_nome:
                            st.session_state["liga_ativa_nome"] = novo_nome.strip()
                        st.success("Liga atualizada!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("J\u00e1 existe uma liga com esse nome.")