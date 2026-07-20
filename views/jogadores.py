import pandas as pd
import streamlit as st

from core.auth import eh_admin
from core.queries import lista_clubes, lista_jogadores_da_liga, criar_jogador, editar_jogador, buscar_jogador
from core.state import selecionar_liga_ativa

liga_id, liga_nome = selecionar_liga_ativa()
st.header(f"\U0001F464 Jogadores \u2014 {liga_nome}")
clubes = lista_clubes(liga_id)

POSICOES = ["GOL", "ZAG", "LAT", "VOL", "MEI", "ATA"]

if eh_admin():
    with st.expander("\u2795 Registrar novo jogador"):
        with st.form("form_jogador"):
            nome = st.text_input("Nome do jogador")
            posicao = st.selectbox("Posi\u00e7\u00e3o", POSICOES)
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

    with st.expander("\U0001F4CB Cadastrar v\u00e1rios jogadores de uma vez"):
        st.caption(
            "Preencha a tabela abaixo (clique em '+' pra adicionar linhas) ou **cole direto de uma "
            "planilha do Excel/Google Sheets** — selecione as células lá, copie (Ctrl+C), clique numa "
            "célula aqui e cole (Ctrl+V). Depois clique em 'Salvar todos'."
        )
        clube_opcoes_lote = ["(Sem clube / Free agent)"] + (clubes["nome"].tolist() if not clubes.empty else [])

        modelo = pd.DataFrame(
            [{"Nome": "", "Posição": "MEI", "Overall": 70, "Valor de Mercado": 0.0, "Salário": 0.0, "Clube": clube_opcoes_lote[0]}]
        )
        tabela = st.data_editor(
            modelo,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_lote_jogadores",
            column_config={
                "Posição": st.column_config.SelectboxColumn("Posição", options=POSICOES),
                "Overall": st.column_config.NumberColumn("Overall", min_value=40, max_value=99, step=1),
                "Valor de Mercado": st.column_config.NumberColumn("Valor de Mercado", min_value=0.0, step=50000.0, format="R$ %.2f"),
                "Salário": st.column_config.NumberColumn("Salário", min_value=0.0, step=1000.0, format="R$ %.2f"),
                "Clube": st.column_config.SelectboxColumn("Clube", options=clube_opcoes_lote),
            },
        )

        if st.button("Salvar todos"):
            linhas_validas = tabela[tabela["Nome"].fillna("").str.strip() != ""]
            if linhas_validas.empty:
                st.warning("Nenhuma linha com nome preenchido pra salvar.")
            else:
                criados = 0
                for _, linha in linhas_validas.iterrows():
                    clube_id = None
                    clube_nome_linha = linha.get("Clube")
                    if clube_nome_linha and clube_nome_linha != "(Sem clube / Free agent)":
                        match = clubes[clubes["nome"] == clube_nome_linha]
                        if not match.empty:
                            clube_id = int(match.iloc[0]["id"])
                    criar_jogador(
                        str(linha["Nome"]).strip(),
                        linha.get("Posição") or "MEI",
                        int(linha.get("Overall") or 70),
                        float(linha.get("Valor de Mercado") or 0),
                        float(linha.get("Salário") or 0),
                        clube_id,
                        liga_id,
                    )
                    criados += 1
                st.success(f"{criados} jogador(es) cadastrado(s)!")
                st.rerun()
else:
    st.info("Modo visualização: escolha um clube abaixo para ver o elenco dele.")

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