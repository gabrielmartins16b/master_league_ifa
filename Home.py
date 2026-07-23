"""
Gestao Financeira - Master League eFootball
Ponto de entrada UNICO do app (streamlit run Home.py).

Antes do login: so a tela de login aparece, sem sidebar/menu.
Depois do login: monta a navegacao (st.navigation) de acordo com o papel
do usuario - admin ve todas as paginas, visualizador ve um menu reduzido.
"""

import streamlit as st

from core.auth import usuario_logado, papel_logado, eh_admin, tela_login, fazer_logout
from core.database import init_db

st.set_page_config(page_title="Master League - Gest\u00e3o Financeira", page_icon="\u26bd", layout="wide")
init_db()

# CSS global: em telas estreitas (celular), as colunas do Streamlit (st.columns)
# empilham (uma embaixo da outra, 100% de largura) em vez de ficarem espremidas
# lado a lado com scroll horizontal. So aplica abaixo de 640px de largura.
st.markdown(
    """
    <style>
    @media (max-width: 640px) {
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }
    }

    /* Esconde o menu "⋮" padrão do Streamlit e o rodapé "Made with Streamlit".
       Não esconde o <header> inteiro de propósito: ele contém o botão ☰ que
       abre a sidebar no celular — escondê-lo quebraria a navegação mobile. */
    footer {visibility: hidden;}
    [data-testid="stDecoration"] {visibility: hidden !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Gate de login: enquanto nao autenticado, so isso existe na tela ---
if not usuario_logado() or not papel_logado():
    tela_login()
    st.stop()

# --- A partir daqui o usuario ja esta autenticado ---
dashboard = st.Page("views/dashboard.py", title="Dashboard", icon="\U0001F4CA", default=True)
ligas = st.Page("views/ligas.py", title="Ligas", icon="\U0001F3C6")
clubes = st.Page("views/clubes.py", title="Clubes", icon="\U0001F3DF\uFE0F")
jogadores = st.Page("views/jogadores.py", title="Jogadores", icon="\U0001F464")
transferencias = st.Page("views/transferencias.py", title="Transfer\u00eancias", icon="\U0001F504")
patrocinios = st.Page("views/patrocinios.py", title="Patroc\u00ednios", icon="\U0001F91D")
financeiro = st.Page("views/financeiro.py", title="Financeiro", icon="\U0001F4D2")
usuarios = st.Page("views/usuarios.py", title="Usu\u00e1rios", icon="\U0001F465")

if eh_admin():
    paginas = [dashboard, ligas, clubes, jogadores, transferencias, patrocinios, financeiro, usuarios]
else:
    paginas = [dashboard, clubes, jogadores, transferencias, financeiro]

st.sidebar.title("\u26bd Master League")
with st.sidebar:
    rotulo_papel = "Administrador" if eh_admin() else "Visualizador"
    st.caption(f"\U0001F464 **{usuario_logado()}** \u00b7 {rotulo_papel}")
    if st.button("Sair", use_container_width=True):
        fazer_logout()
    st.divider()

pg = st.navigation(paginas)
pg.run()