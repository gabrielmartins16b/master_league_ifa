import streamlit as st

from core.auth import eh_admin
from core.queries import lista_clubes_dashboard, historico_financeiro
from core.state import selecionar_liga_ativa

liga_id, liga_nome = selecionar_liga_ativa()
st.header(f"\U0001F4CA Dashboard \u2014 {liga_nome}")

clubes = lista_clubes_dashboard(liga_id)

if clubes.empty:
    st.info("Nenhum clube cadastrado nesta liga ainda." + (" V\u00e1 em 'Clubes' para come\u00e7ar." if eh_admin() else ""))
else:
    col1, col2, col3 = st.columns(3)
    col1.metric("Clubes cadastrados", len(clubes))
    col2.metric("Saldo total da liga", f"R$ {clubes['Saldo'].sum():,.2f}")
    col3.metric("Clube mais rico", clubes.iloc[0]["Clube"])

    st.subheader("Saldo por clube")
    st.dataframe(clubes.style.format({"Saldo": "R$ {:.2f}"}), use_container_width=True)
    st.bar_chart(clubes.set_index("Clube")["Saldo"])

    st.subheader("\u00daltimas movimenta\u00e7\u00f5es")
    hist = historico_financeiro(liga_id, limite=10)
    st.dataframe(hist, use_container_width=True)