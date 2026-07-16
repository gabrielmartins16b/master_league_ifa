import psycopg2

import streamlit as st

from core.auth import eh_admin
from core.queries import lista_clubes_completo, lista_clubes_por_folha_salarial, criar_clube, ajustar_saldo_clube, editar_clube, deletar_clube, cobrar_salarios
from core.state import selecionar_liga_ativa

liga_id, liga_nome = selecionar_liga_ativa()
st.header(f"\U0001F3DF\uFE0F Clubes \u2014 {liga_nome}")

if eh_admin():
    with st.expander("\u2795 Cadastrar novo clube nesta liga"):
        with st.form("form_clube"):
            nome = st.text_input("Nome do clube")
            tecnico = st.text_input("T\u00e9cnico / Dono")
            saldo_inicial = st.number_input("Saldo inicial", min_value=0.0, step=100000.0, value=0.0)
            enviado = st.form_submit_button("Cadastrar")
            if enviado:
                if not nome.strip():
                    st.error("Informe o nome do clube.")
                else:
                    try:
                        criar_clube(nome, tecnico, saldo_inicial, liga_id)
                        st.success(f"Clube '{nome}' cadastrado em {liga_nome}!")
                        st.rerun()
                    except psycopg2.IntegrityError:
                        st.error("J\u00e1 existe um clube com esse nome nesta liga.")
else:
    st.info("Modo visualiza\u00e7\u00e3o: apenas administradores podem cadastrar, editar ou apagar clubes.")

st.subheader("Clubes cadastrados nesta liga")
clubes = lista_clubes_completo(liga_id)
st.dataframe(clubes.style.format({"Saldo": "R$ {:.2f}"}), use_container_width=True)

if eh_admin() and not clubes.empty:
    with st.expander("\U0001F4B0 Ajustar saldo manualmente (corre\u00e7\u00e3o/ajuste)"):
        clube_sel = st.selectbox("Clube", clubes["Nome"], key="ajuste_clube")
        valor_ajuste = st.number_input("Valor (positivo soma, negativo subtrai)", step=10000.0, value=0.0, key="ajuste_valor")
        motivo = st.text_input("Motivo do ajuste", key="ajuste_motivo")
        if st.button("Aplicar ajuste"):
            clube_id = int(clubes.loc[clubes["Nome"] == clube_sel, "ID"].iloc[0])
            ajustar_saldo_clube(clube_id, valor_ajuste, motivo)
            st.success("Ajuste aplicado.")
            st.rerun()

    st.divider()
    with st.expander("\u270F\uFE0F Editar clube"):
        clube_edit_nome = st.selectbox("Escolha o clube a editar", clubes["Nome"], key="edit_clube_sel")
        clube_edit_row = clubes[clubes["Nome"] == clube_edit_nome].iloc[0]
        with st.form("form_editar_clube"):
            novo_nome = st.text_input("Nome", value=clube_edit_row["Nome"])
            novo_tecnico = st.text_input("T\u00e9cnico / Dono", value=clube_edit_row["T\u00e9cnico"] or "")
            novo_saldo = st.number_input("Saldo", step=10000.0, value=float(clube_edit_row["Saldo"]))
            salvar = st.form_submit_button("Salvar altera\u00e7\u00f5es")
            if salvar:
                if not novo_nome.strip():
                    st.error("Informe o nome do clube.")
                else:
                    try:
                        editar_clube(int(clube_edit_row["ID"]), novo_nome, novo_tecnico, novo_saldo)
                        st.success("Clube atualizado!")
                        st.rerun()
                    except psycopg2.IntegrityError:
                        st.error("J\u00e1 existe um clube com esse nome nesta liga.")

    st.divider()
    with st.expander("\U0001F5D1\uFE0F Apagar clube"):
        clube_del_nome = st.selectbox("Escolha o clube a apagar", clubes["Nome"], key="del_clube_sel")
        st.warning(
            f"Isso vai apagar o clube **{clube_del_nome}**, seu hist\u00f3rico financeiro, patroc\u00ednios e "
            "transfer\u00eancias ligados a ele. Os jogadores dele ficam 'Sem clube' (n\u00e3o s\u00e3o apagados). "
            "Essa a\u00e7\u00e3o n\u00e3o pode ser desfeita."
        )
        confirmar_clube = st.checkbox("Sim, tenho certeza que quero apagar esse clube", key="del_clube_confirma")
        if st.button("Apagar clube definitivamente", disabled=not confirmar_clube):
            clube_del_id = int(clubes.loc[clubes["Nome"] == clube_del_nome, "ID"].iloc[0])
            deletar_clube(clube_del_id)
            st.success(f"Clube '{clube_del_nome}' apagado.")
            st.rerun()

    st.divider()
    st.subheader("\U0001F4B8 Folha salarial")
    folha = lista_clubes_por_folha_salarial(liga_id)
    st.caption("Soma dos sal\u00e1rios do elenco atual de cada clube.")
    st.dataframe(folha.style.format({"Folha Salarial": "R$ {:.2f}"}), use_container_width=True)

    with st.expander("\U0001F4B0 Cobrar sal\u00e1rios (desconta do saldo de todos os clubes)"):
        total_folha = float(folha["Folha Salarial"].sum()) if not folha.empty else 0.0
        st.write(
            f"Isso vai descontar do saldo de **cada clube** a soma dos sal\u00e1rios do elenco atual dele, "
            f"e lan\u00e7ar no hist\u00f3rico financeiro como 'Pagamento de sal\u00e1rios'. "
            f"Total que sai da liga inteira: **R$ {total_folha:,.2f}**."
        )
        st.warning("Essa a\u00e7\u00e3o n\u00e3o pode ser desfeita automaticamente (mas pode ser ajustada manualmente depois, clube por clube).")
        confirmar_salario = st.checkbox("Sim, quero cobrar os sal\u00e1rios agora", key="confirma_cobranca_salario")
        if st.button("Cobrar sal\u00e1rios de todos os clubes", disabled=not confirmar_salario):
            qtd = cobrar_salarios(liga_id)
            if qtd == 0:
                st.info("Nenhum clube tem jogadores com sal\u00e1rio cadastrado.")
            else:
                st.success(f"Sal\u00e1rios cobrados de {qtd} clube(s)!")
            st.rerun()