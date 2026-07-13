import streamlit as st

from core.auth import eh_admin
from core.queries import lista_clubes, lista_jogadores_da_liga, criar_jogador, editar_jogador, buscar_jogador
from core.state import selecionar_liga_ativa

liga_id, liga_nome = selecionar_liga_ativa()
st.header(f"\U0001F464 Jogadores \u2014 {liga_nome}")
clubes = lista_clubes(liga_id)

if eh_admin():
    with st.expander("\u2795 Registrar novo jogador"):
        with st.form("form_jogador"):
            nome = st.text_input("Nome do jogador")
            posicao = st.selectbox("Posi\u00e7\u00e3o", ["GOL", "ZAG", "LAT", "VOL", "MEI", "ATA"])
            overall = st.slider("Overall", 40, 99, 70)
            valor_mercado = st.number_input("Valor de mercado", min_value=0.0, step=50000.0)
            salario = st.number_input("Sal\u00e1rio", min_value=0.0, step=1000.0)
            clube_opcoes = ["(Sem clube / Free agent)"] + (clubes["nome"].tolist() if not clubes.empty else [])
            clube_sel = st.selectbox("Clube atual", clube_opcoes)
            enviado = st.form_submit_button("Registrar")
            if enviado:
                if not nome.strip():
                    st.error("Informe o nome do jogador.")
                else:
                    clube_id = None
                    if clube_sel != "(Sem clube / Free agent)":
                        clube_id = int(clubes.loc[clubes["nome"] == clube_sel, "id"].iloc[0])
                    criar_jogador(nome, posicao, overall, valor_mercado, salario, clube_id, liga_id)
                    st.success(f"Jogador '{nome}' registrado em {liga_nome}!")
                    st.rerun()
else:
    st.info("Modo visualiza\u00e7\u00e3o: escolha um clube abaixo para ver o elenco dele.")

st.subheader("Elenco")
filtro_clube = st.selectbox(
    "Filtrar por clube", ["Todos"] + (clubes["nome"].tolist() if not clubes.empty else [])
)
jogadores = lista_jogadores_da_liga(liga_id)
if filtro_clube != "Todos" and not jogadores.empty:
    jogadores = jogadores[jogadores["Clube"] == filtro_clube]
st.dataframe(jogadores, use_container_width=True)

if eh_admin():
    st.divider()
    todos_jogadores = lista_jogadores_da_liga(liga_id)
    with st.expander("\u270F\uFE0F Editar jogador"):
        if todos_jogadores.empty:
            st.caption("Nenhum jogador cadastrado.")
        else:
            jogador_edit_nome = st.selectbox("Escolha o jogador", todos_jogadores["Nome"], key="edit_jogador_sel")
            jogador_edit_id = int(todos_jogadores.loc[todos_jogadores["Nome"] == jogador_edit_nome, "ID"].iloc[0])
            atual = buscar_jogador(jogador_edit_id)

            with st.form("form_editar_jogador"):
                novo_nome = st.text_input("Nome", value=atual[1])
                posicoes = ["GOL", "ZAG", "LAT", "VOL", "MEI", "ATA"]
                nova_posicao = st.selectbox("Posi\u00e7\u00e3o", posicoes, index=posicoes.index(atual[2]) if atual[2] in posicoes else 0)
                novo_overall = st.slider("Overall", 40, 99, int(atual[3] or 70))
                novo_valor_mercado = st.number_input("Valor de mercado", min_value=0.0, step=50000.0, value=float(atual[4] or 0))
                novo_salario = st.number_input("Sal\u00e1rio", min_value=0.0, step=1000.0, value=float(atual[5] or 0))

                clube_opcoes = ["(Sem clube / Free agent)"] + (clubes["nome"].tolist() if not clubes.empty else [])
                clube_atual_nome = "(Sem clube / Free agent)"
                if atual[6] is not None:
                    match = clubes[clubes["id"] == atual[6]]
                    if not match.empty:
                        clube_atual_nome = match.iloc[0]["nome"]
                novo_clube_sel = st.selectbox(
                    "Clube atual", clube_opcoes, index=clube_opcoes.index(clube_atual_nome) if clube_atual_nome in clube_opcoes else 0
                )

                salvar = st.form_submit_button("Salvar altera\u00e7\u00f5es")
                if salvar:
                    if not novo_nome.strip():
                        st.error("Informe o nome do jogador.")
                    else:
                        novo_clube_id = None
                        if novo_clube_sel != "(Sem clube / Free agent)":
                            novo_clube_id = int(clubes.loc[clubes["nome"] == novo_clube_sel, "id"].iloc[0])
                        editar_jogador(jogador_edit_id, novo_nome, nova_posicao, novo_overall, novo_valor_mercado, novo_salario, novo_clube_id)
                        st.success("Jogador atualizado!")
                        st.rerun()