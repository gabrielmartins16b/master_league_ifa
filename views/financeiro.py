import streamlit as st

from core.queries import lista_clubes, historico_financeiro
from core.state import selecionar_liga_ativa

liga_id, liga_nome = selecionar_liga_ativa()
st.header(f"\U0001F4D2 Hist\u00f3rico Financeiro \u2014 {liga_nome}")
clubes = lista_clubes(liga_id)

filtro = st.selectbox("Filtrar por clube", ["Todos"] + (clubes["nome"].tolist() if not clubes.empty else []))

hist = historico_financeiro(liga_id)
if filtro != "Todos" and not hist.empty:
    hist = hist[hist["Clube"] == filtro]

st.dataframe(hist.style.format({"Valor": "R$ {:.2f}"}), use_container_width=True)

if not hist.empty:
    csv = hist.to_csv(index=False).encode("utf-8")
    st.download_button("\u2B07\uFE0F Baixar extrato (CSV)", csv, f"extrato_{liga_nome}.csv", "text/csv")