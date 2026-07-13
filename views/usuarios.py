import sqlite3

import streamlit as st

from core.auth import eh_admin
from core.queries import lista_usuarios, criar_usuario, redefinir_senha_usuario, deletar_usuario

if not eh_admin():
    st.header("\U0001F465 Usu\u00e1rios")
    st.info("Apenas administradores podem gerenciar usu\u00e1rios.")
    st.stop()

st.header("\U0001F465 Usu\u00e1rios")
st.caption(
    "Admin tem acesso total (cadastra, edita, apaga). Visualizador consulta "
    "qualquer clube da liga, mas n\u00e3o v\u00ea nenhum formul\u00e1rio de edi\u00e7\u00e3o."
)

with st.expander("\u2795 Criar novo usu\u00e1rio"):
    with st.form("form_usuario"):
        novo_usuario = st.text_input("Nome de usu\u00e1rio (login)")
        nova_senha = st.text_input("Senha", type="password")
        papel = st.selectbox("Papel", ["visualizador", "admin"])
        enviado = st.form_submit_button("Criar usu\u00e1rio")
        if enviado:
            if not novo_usuario.strip() or not nova_senha:
                st.error("Preencha usu\u00e1rio e senha.")
            else:
                try:
                    criar_usuario(novo_usuario, nova_senha, papel, None)
                    st.success(f"Usu\u00e1rio '{novo_usuario}' criado!")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("J\u00e1 existe um usu\u00e1rio com esse nome.")

st.subheader("Usu\u00e1rios cadastrados")
usuarios = lista_usuarios()
st.dataframe(usuarios[["ID", "Usu\u00e1rio", "Papel"]], use_container_width=True)

if not usuarios.empty:
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        with st.expander("\U0001F511 Redefinir senha"):
            user_sel_senha = st.selectbox("Usu\u00e1rio", usuarios["Usu\u00e1rio"], key="redef_senha_user")
            nova_senha_redef = st.text_input("Nova senha", type="password", key="redef_senha_valor")
            if st.button("Redefinir senha"):
                if not nova_senha_redef:
                    st.error("Digite a nova senha.")
                else:
                    usuario_id = int(usuarios.loc[usuarios["Usu\u00e1rio"] == user_sel_senha, "ID"].iloc[0])
                    redefinir_senha_usuario(usuario_id, nova_senha_redef)
                    st.success("Senha redefinida.")

    with col2:
        with st.expander("\U0001F5D1\uFE0F Apagar usu\u00e1rio"):
            user_sel_del = st.selectbox("Usu\u00e1rio", usuarios["Usu\u00e1rio"], key="del_user_sel")
            usuario_logado_atual = st.session_state.get("usuario")
            if user_sel_del == usuario_logado_atual:
                st.warning("Voc\u00ea n\u00e3o pode apagar o pr\u00f3prio usu\u00e1rio logado.")
            else:
                confirmar = st.checkbox("Sim, tenho certeza que quero apagar esse usu\u00e1rio", key="del_user_confirma")
                if st.button("Apagar usu\u00e1rio definitivamente", disabled=not confirmar):
                    usuario_id = int(usuarios.loc[usuarios["Usu\u00e1rio"] == user_sel_del, "ID"].iloc[0])
                    deletar_usuario(usuario_id)
                    st.success("Usu\u00e1rio apagado.")
                    st.rerun()