import streamlit as st
import time
from utils import get_selic_atual_db, verificar_login, criar_usuario

# Importação das Abas (que criaremos a seguir)
from abas import comparativo, calculadora, metas, compras, investimentos, despesas

# ==================================================
# CONFIGURAÇÃO GERAL E ESTADO
# ==================================================
st.set_page_config(page_title="Finanças Família", page_icon="💰", layout="wide")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'usuario_atual' not in st.session_state:
    st.session_state['usuario_atual'] = None

# Inicializa estados globais se necessário
keys_globais = ['res_comp', 'res_calc', 'res_meta', 'res_compra']
for k in keys_globais:
    if k not in st.session_state: st.session_state[k] = None

# ==================================================
# LOGIN (ÁREA RESTRITA)
# ==================================================
def mostrar_tela_login(chave):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.warning("🔒 Área restrita. Faça login.")
        t_ent, t_cri = st.tabs(["Entrar", "Criar Conta"])
        with t_ent:
            with st.form(f"login_{chave}"):
                u = st.text_input("Usuário")
                s = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", type="primary"):
                    if verificar_login(u, s):
                        st.session_state['logado'] = True
                        st.session_state['usuario_atual'] = u
                        st.success("Sucesso!"); time.sleep(0.5); st.rerun()
                    else: st.error("Erro no login.")
        with t_cri:
            with st.form(f"cad_{chave}"):
                nu = st.text_input("Novo Usuário"); ns = st.text_input("Nova Senha", type="password")
                if st.form_submit_button("Criar"):
                    if nu and ns: 
                        ok, msg = criar_usuario(nu, ns)
                        if ok: st.success(msg)
                        else: st.error(msg)
                    else: st.warning("Preencha tudo.")

# ==================================================
# INTERFACE PRINCIPAL
# ==================================================
titulo = "💰 Controle Financeiro"
if st.session_state.get('logado', False):
    titulo += f" de {st.session_state.get('usuario_atual', '')}"
    with st.sidebar:
        st.write(f"Logado como: **{st.session_state.get('usuario_atual', '')}**")
        if st.button("Sair / Logout", type="primary"):
            st.session_state['logado'] = False
            st.session_state['usuario_atual'] = None
            st.rerun()

st.title(titulo)

val_selic_inicial = get_selic_atual_db()

with st.container():
    col1, col2, col3 = st.columns(3)
    with col1: selic_atual = st.number_input("Taxa Selic (%)", value=val_selic_inicial, step=0.25, format="%.2f", key="global_selic") 
    with col2: cdi_estimado = selic_atual - 0.10; st.metric("CDI Estimado (%)", f"{cdi_estimado:.2f}%")
    with col3: ipca_estimado = st.number_input("IPCA Projetado (%)", value=4.50, step=0.5, format="%.2f", key="global_ipca")

st.divider()

aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "⚖️ Comparativo", "📈 Simulador", "🎯 Metas", "🛒 Compras", "💰 Meus Investimentos 🔒", "💸 Extrato Despesas 🔒"
])

# Chamada dos Módulos
with aba1: comparativo.render(cdi_estimado, ipca_estimado)
with aba2: calculadora.render(cdi_estimado, ipca_estimado)
with aba3: metas.render(cdi_estimado, ipca_estimado)
with aba4: compras.render(selic_atual, cdi_estimado)

with aba5:
    if not st.session_state.get('logado', False): mostrar_tela_login("inv")
    else: investimentos.render(selic_atual, cdi_estimado, ipca_estimado)

with aba6:
    if not st.session_state.get('logado', False): mostrar_tela_login("ext")
    else: despesas.render()