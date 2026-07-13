import streamlit as st

from core.auth import eh_admin
from core.queries import (
    lista_clubes,
    lancar_patrocinio,
    historico_patrocinios,
    buscar_patrocinio,
    editar_patrocinio,
    deletar_patrocinio,
)
from core.state import selecionar_liga_ativa

liga_id, liga_nome = selecionar_liga_ativa()
st.header(f"\U0001F91D Patroc\u00ednios \u2014 {liga_nome}")
clubes = lista_clubes(liga_id)

TIPOS_PATROCINIO = ["Contrato fixo (mensal)", "B\u00f4nus por vit\u00f3ria", "B\u00f4nus \u00fanico", "Outro"]

if not eh_admin():
    st.info("Modo visualiza\u00e7\u00e3o: apenas administradores podem lan\u00e7ar, editar ou apagar patroc\u00ednios.")
    st.stop()
elif clubes.empty:
    st.info("Cadastre um clube nesta liga primeiro.")
else:
    with st.form("form_patrocinio"):
        clube_nome = st.selectbox("Clube", clubes["nome"])
        patrocinador = st.text_input("Nome do patrocinador")
        tipo = st.selectbox("Tipo", TIPOS_PATROCINIO)
        valor = st.number_input("Valor", min_value=0.0, step=10000.0)
        enviado = st.form_submit_button("Lan\u00e7ar patroc\u00ednio")

        if enviado:
            if not patrocinador.strip():
                st.error("Informe o nome do patrocinador.")
            else:
                clube_id = int(clubes.loc[clubes["nome"] == clube_nome, "id"].iloc[0])
                lancar_patrocinio(clube_id, patrocinador, valor, tipo)
                st.success("Patroc\u00ednio lan\u00e7ado!")
                st.rerun()

st.subheader("Patroc\u00ednios lan\u00e7ados nesta liga")
hist = historico_patrocinios(liga_id)
st.dataframe(hist, use_container_width=True)

if not hist.empty:
    st.divider()
    hist["rotulo"] = hist["Patrocinador"] + " \u2014 " + hist["Clube"] + " (" + hist["Data"] + ")"

    with st.expander("\u270F\uFE0F Editar patroc\u00ednio"):
        rotulo_edit = st.selectbox("Escolha o patroc\u00ednio", hist["rotulo"], key="edit_patro_sel")
        patro_edit_id = int(hist.loc[hist["rotulo"] == rotulo_edit, "ID"].iloc[0])
        atual = buscar_patrocinio(patro_edit_id)

        with st.form("form_editar_patrocinio"):
            novo_patrocinador = st.text_input("Patrocinador", value=atual[2])
            novo_tipo = st.selectbox("Tipo", TIPOS_PATROCINIO, index=TIPOS_PATROCINIO.index(atual[4]) if atual[4] in TIPOS_PATROCINIO else 0)
            novo_valor = st.number_input("Valor", min_value=0.0, step=10000.0, value=float(atual[3]))
            salvar = st.form_submit_button("Salvar altera\u00e7\u00f5es")
            if salvar:
                if not novo_patrocinador.strip():
                    st.error("Informe o nome do patrocinador.")
                else:
                    editar_patrocinio(patro_edit_id, novo_patrocinador, novo_valor, novo_tipo)
                    st.success("Patroc\u00ednio atualizado!")
                    st.rerun()

    with st.expander("\U0001F5D1\uFE0F Apagar patroc\u00ednio"):
        rotulo_del = st.selectbox("Escolha o patroc\u00ednio a apagar", hist["rotulo"], key="del_patro_sel")
        patro_del_id = int(hist.loc[hist["rotulo"] == rotulo_del, "ID"].iloc[0])
        st.warning("O valor lan\u00e7ado ser\u00e1 estornado do saldo do clube. Essa a\u00e7\u00e3o n\u00e3o pode ser desfeita.")
        confirmar = st.checkbox("Sim, tenho certeza que quero apagar esse patroc\u00ednio", key="del_patro_confirma")
        if st.button("Apagar patroc\u00ednio definitivamente", disabled=not confirmar):
            deletar_patrocinio(patro_del_id)
            st.success("Patroc\u00ednio apagado.")
            st.rerun()