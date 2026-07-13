import pandas as pd
import streamlit as st

from core.auth import eh_admin
from core.queries import lista_clubes, lista_jogadores_simples, registrar_transferencia, historico_transferencias, cancelar_transferencia, editar_valor_transferencia
from core.state import selecionar_liga_ativa

liga_id, liga_nome = selecionar_liga_ativa()
st.header(f"\U0001F504 Transfer\u00eancias \u2014 {liga_nome}")
clubes = lista_clubes(liga_id)
jogadores = lista_jogadores_simples(liga_id)

if not eh_admin():
    st.info("Modo visualiza\u00e7\u00e3o: transfer\u00eancias s\u00f3 podem ser registradas por um administrador.")
elif jogadores.empty:
    st.info("Cadastre jogadores primeiro na aba 'Jogadores'.")
else:
    with st.form("form_transferencia"):
        jogador_nome = st.selectbox("Jogador", jogadores["nome"])
        jogador_row = jogadores[jogadores["nome"] == jogador_nome].iloc[0]
        clube_origem_id = jogador_row["clube_id"]

        clube_origem_nome = "Sem clube"
        if pd.notna(clube_origem_id):
            match = clubes[clubes["id"] == clube_origem_id]
            if not match.empty:
                clube_origem_nome = match.iloc[0]["nome"]
        st.caption(f"Clube atual: **{clube_origem_nome}**")

        opcoes_destino = clubes[clubes["nome"] != clube_origem_nome]["nome"].tolist()
        if not opcoes_destino:
            st.warning("Cadastre outro clube nesta liga para transferir este jogador.")
            st.form_submit_button("Confirmar transfer\u00eancia", disabled=True)
        else:
            clube_destino_nome = st.selectbox("Clube de destino", opcoes_destino)
            valor = st.number_input("Valor da transfer\u00eancia", min_value=0.0, step=50000.0)
            confirmar = st.form_submit_button("Confirmar transfer\u00eancia")

            if confirmar:
                destino_id = int(clubes.loc[clubes["nome"] == clube_destino_nome, "id"].iloc[0])
                try:
                    registrar_transferencia(
                        int(jogador_row["id"]), jogador_nome, clube_origem_id, destino_id, clube_destino_nome, valor
                    )
                    st.success(f"{jogador_nome} transferido para {clube_destino_nome}!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

st.subheader("Hist\u00f3rico de transfer\u00eancias")
hist = historico_transferencias(liga_id)
st.dataframe(hist, use_container_width=True)

if eh_admin():
    st.divider()
    with st.expander("\u270F\uFE0F Editar valor ou anular uma transfer\u00eancia"):
        if hist.empty:
            st.caption("Nenhuma transfer\u00eancia registrada nesta liga.")
        else:
            hist["rotulo"] = hist["Jogador"] + " \u2014 " + hist["Origem"] + " \u2192 " + hist["Destino"] + " (" + hist["Data"] + ")"
            rotulo_sel = st.selectbox("Escolha a transfer\u00eancia", hist["rotulo"], key="transf_sel")
            transf_id = int(hist.loc[hist["rotulo"] == rotulo_sel, "ID"].iloc[0])
            valor_atual = float(hist.loc[hist["rotulo"] == rotulo_sel, "Valor"].iloc[0])

            col_edit, col_cancel = st.columns(2)

            with col_edit:
                st.markdown("**Corrigir valor**")
                novo_valor = st.number_input("Novo valor", min_value=0.0, step=50000.0, value=valor_atual, key="transf_novo_valor")
                if st.button("Salvar novo valor"):
                    try:
                        editar_valor_transferencia(transf_id, novo_valor)
                        st.success("Valor da transfer\u00eancia atualizado.")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

            with col_cancel:
                st.markdown("**Anular transfer\u00eancia**")
                st.caption("O jogador volta para o clube de origem e os saldos s\u00e3o estornados.")
                if st.button("Anular esta transfer\u00eancia"):
                    cancelar_transferencia(transf_id)
                    st.success("Transfer\u00eancia anulada.")
                    st.rerun()