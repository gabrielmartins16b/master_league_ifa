import streamlit as st

from core.auth import eh_admin
from core.queries import (
    lista_clubes,
    lista_clubes_todas_ligas,
    lista_jogadores_por_clube,
    registrar_negociacao,
    historico_negociacoes,
    detalhes_negociacao,
    historico_transferencias as historico_transferencias_legado,
)
from core.state import selecionar_liga_ativa

liga_id, liga_nome = selecionar_liga_ativa()
st.header(f"\U0001F504 Transfer\u00eancias \u2014 {liga_nome}")


def _opcoes_clube(entre_ligas):
    """Retorna (lista_de_rotulos, dict rotulo->id, dict rotulo->liga_id)."""
    if entre_ligas:
        todos = lista_clubes_todas_ligas()
        if todos.empty:
            return [], {}, {}
        rotulos = [f"{row['nome']} ({row['liga_nome']})" for _, row in todos.iterrows()]
        rotulo_para_id = {f"{row['nome']} ({row['liga_nome']})": int(row["id"]) for _, row in todos.iterrows()}
        return rotulos, rotulo_para_id, todos
    else:
        clubes_liga = lista_clubes(liga_id)
        if clubes_liga.empty:
            return [], {}, clubes_liga
        rotulos = clubes_liga["nome"].tolist()
        rotulo_para_id = {row["nome"]: int(row["id"]) for _, row in clubes_liga.iterrows()}
        return rotulos, rotulo_para_id, clubes_liga


if not eh_admin():
    st.info("Modo visualiza\u00e7\u00e3o: transfer\u00eancias s\u00f3 podem ser registradas por um administrador.")
else:
    entre_ligas = st.checkbox(
        "\U0001F310 Incluir clubes de outras ligas nesta negocia\u00e7\u00e3o",
        help="Marque para negociar com um clube que est\u00e1 em outra liga. O jogador muda de clube E de liga.",
    )
    rotulos, rotulo_para_id, _ = _opcoes_clube(entre_ligas)

    if len(rotulos) < 2:
        st.warning("Cadastre pelo menos 2 clubes" + (" (em qualquer liga)" if entre_ligas else " nesta liga") + " para negociar.")
    else:
        tipo = st.radio("Tipo de negocia\u00e7\u00e3o", ["Compra", "Troca"], horizontal=True)

        st.caption(f"Limite: cada clube pode participar de no m\u00e1ximo 2 negocia\u00e7\u00f5es por dia.")

        if tipo == "Compra":
            col1, col2 = st.columns(2)
            with col1:
                rotulo_vendedor = st.selectbox("Clube vendedor", rotulos, key="compra_vendedor")
            with col2:
                opcoes_comprador = [r for r in rotulos if r != rotulo_vendedor]
                rotulo_comprador = st.selectbox("Clube comprador", opcoes_comprador, key="compra_comprador")

            vendedor_id = rotulo_para_id[rotulo_vendedor]
            comprador_id = rotulo_para_id[rotulo_comprador]

            jogadores_vendedor = lista_jogadores_por_clube(vendedor_id)
            if jogadores_vendedor.empty:
                st.info(f"{rotulo_vendedor} n\u00e3o tem jogadores para vender.")
            else:
                nomes_para_id = {row["nome"]: int(row["id"]) for _, row in jogadores_vendedor.iterrows()}
                jogadores_sel = st.multiselect("Jogador(es) vendido(s)", list(nomes_para_id.keys()), key="compra_jogadores")
                valor = st.number_input("Valor total da compra", min_value=0.0, step=50000.0, key="compra_valor")

                if st.button("Confirmar compra"):
                    if not jogadores_sel:
                        st.error("Selecione ao menos um jogador.")
                    else:
                        movimentos = [(nomes_para_id[nome], vendedor_id, comprador_id) for nome in jogadores_sel]
                        try:
                            registrar_negociacao(
                                "compra", vendedor_id, comprador_id, movimentos,
                                valor_compensacao=valor, clube_pagador_id=comprador_id, clube_recebedor_id=vendedor_id,
                            )
                            st.success(f"{len(jogadores_sel)} jogador(es) comprado(s) por {rotulo_comprador}!")
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

        else:  # Troca
            col1, col2 = st.columns(2)
            with col1:
                rotulo_a = st.selectbox("Clube A", rotulos, key="troca_a")
            with col2:
                opcoes_b = [r for r in rotulos if r != rotulo_a]
                rotulo_b = st.selectbox("Clube B", opcoes_b, key="troca_b")

            clube_a_id = rotulo_para_id[rotulo_a]
            clube_b_id = rotulo_para_id[rotulo_b]

            jogadores_a = lista_jogadores_por_clube(clube_a_id)
            jogadores_b = lista_jogadores_por_clube(clube_b_id)
            nomes_a_para_id = {row["nome"]: int(row["id"]) for _, row in jogadores_a.iterrows()}
            nomes_b_para_id = {row["nome"]: int(row["id"]) for _, row in jogadores_b.iterrows()}

            col3, col4 = st.columns(2)
            with col3:
                st.markdown(f"**Jogadores de {rotulo_a} indo para {rotulo_b}**")
                sel_a_para_b = st.multiselect("Jogadores", list(nomes_a_para_id.keys()), key="troca_sel_a")
            with col4:
                st.markdown(f"**Jogadores de {rotulo_b} indo para {rotulo_a}**")
                sel_b_para_a = st.multiselect("Jogadores", list(nomes_b_para_id.keys()), key="troca_sel_b")

            valor_compensacao = st.number_input(
                "Valor de compensa\u00e7\u00e3o (opcional \u2014 deixe 0 se for troca sem dinheiro)",
                min_value=0.0, step=50000.0, key="troca_valor",
            )
            quem_paga = None
            if valor_compensacao > 0:
                quem_paga = st.radio("Quem paga a compensa\u00e7\u00e3o?", [rotulo_a, rotulo_b], horizontal=True, key="troca_quem_paga")

            if st.button("Confirmar troca"):
                if not sel_a_para_b and not sel_b_para_a:
                    st.error("Selecione ao menos um jogador de algum dos lados.")
                else:
                    movimentos = (
                        [(nomes_a_para_id[nome], clube_a_id, clube_b_id) for nome in sel_a_para_b]
                        + [(nomes_b_para_id[nome], clube_b_id, clube_a_id) for nome in sel_b_para_a]
                    )
                    if valor_compensacao > 0:
                        if quem_paga == rotulo_a:
                            pagador_id, recebedor_id = clube_a_id, clube_b_id
                        else:
                            pagador_id, recebedor_id = clube_b_id, clube_a_id
                    else:
                        pagador_id, recebedor_id = None, None

                    try:
                        registrar_negociacao(
                            "troca", clube_a_id, clube_b_id, movimentos,
                            valor_compensacao=valor_compensacao, clube_pagador_id=pagador_id, clube_recebedor_id=recebedor_id,
                        )
                        st.success(f"Troca entre {rotulo_a} e {rotulo_b} registrada!")
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))

st.subheader("Hist\u00f3rico de negocia\u00e7\u00f5es")
hist = historico_negociacoes(liga_id)
if hist.empty:
    st.caption("Nenhuma negocia\u00e7\u00e3o (compra/troca) registrada ainda nesta liga.")
else:
    st.dataframe(hist, use_container_width=True)

    with st.expander("\U0001F50D Ver jogadores de uma negocia\u00e7\u00e3o"):
        hist_rotulo = hist.copy()
        hist_rotulo["rotulo"] = (
            "#" + hist_rotulo["ID"].astype(str) + " \u2014 " + hist_rotulo["Tipo"] + " \u2014 "
            + hist_rotulo["Clube A"] + " x " + hist_rotulo["Clube B"] + " (" + hist_rotulo["Data"] + ")"
        )
        rotulo_sel = st.selectbox("Escolha a negocia\u00e7\u00e3o", hist_rotulo["rotulo"])
        negociacao_id = int(hist_rotulo.loc[hist_rotulo["rotulo"] == rotulo_sel, "ID"].iloc[0])
        st.dataframe(detalhes_negociacao(negociacao_id), use_container_width=True)

hist_legado = historico_transferencias_legado(liga_id)
if not hist_legado.empty:
    with st.expander("\U0001F4DC Hist\u00f3rico antigo (transfer\u00eancias simples, antes desta atualiza\u00e7\u00e3o)"):
        st.dataframe(hist_legado, use_container_width=True)