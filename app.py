import streamlit as st
import pandas as pd
from datetime import datetime
from conexao import conectar
import time

# ==================================================
# 1. CONFIGURAÇÃO GERAL E ESTADO
# ==================================================
st.set_page_config(page_title="Finanças Família", page_icon="💰", layout="wide")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'usuario_atual' not in st.session_state:
    st.session_state['usuario_atual'] = None

# Estados dos botões e resultados
if 'res_comp' not in st.session_state: st.session_state['res_comp'] = None
if 'res_calc' not in st.session_state: st.session_state['res_calc'] = None
if 'res_meta' not in st.session_state: st.session_state['res_meta'] = None
if 'res_compra' not in st.session_state: st.session_state['res_compra'] = None

# ==================================================
# 2. FUNÇÕES AUXILIARES
# ==================================================

def formatar_real(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calcular_aliquota_ir(dias):
    if dias <= 180: return 0.225
    elif dias <= 360: return 0.20
    elif dias <= 720: return 0.175
    else: return 0.15

def get_historico_selic_df():
    try:
        p = conectar()
        if not p: return pd.DataFrame()
        aba = p.worksheet("historico_selic")
        dados = aba.get_all_records()
        df = pd.DataFrame(dados)
        df['data_inicio'] = pd.to_datetime(df['data_inicio'], format="%d/%m/%Y")
        df['taxa_anual'] = df['taxa_anual'].astype(str).str.replace(',', '.').astype(float)
        return df.sort_values('data_inicio')
    except:
        return pd.DataFrame()

def get_selic_atual_db():
    df = get_historico_selic_df()
    if not df.empty:
        return float(df.iloc[-1]['taxa_anual'])
    return 11.25

def calcular_valor_futuro_dinamico(valor_inicial, data_compra, pct_cdi, df_selic, selic_atual_manual):
    hoje = datetime.now()
    if data_compra >= hoje: return valor_inicial

    if df_selic.empty:
        dias_totais = (hoje - data_compra).days
        anos = dias_totais / 365
        taxa_anual = (pct_cdi/100) * ((selic_atual_manual - 0.10)/100)
        return valor_inicial * ((1 + taxa_anual) ** anos)

    montante = valor_inicial
    data_atual_cursor = data_compra
    taxas_relevantes = df_selic[df_selic['data_inicio'] <= hoje].copy()
    
    while data_atual_cursor < hoje:
        taxa_vigente_row = taxas_relevantes[taxas_relevantes['data_inicio'] <= data_atual_cursor].iloc[-1]
        taxa_selic_momento = taxa_vigente_row['taxa_anual']
        proximas_mudancas = taxas_relevantes[taxas_relevantes['data_inicio'] > data_atual_cursor]
        
        if proximas_mudancas.empty: data_fim_periodo = hoje
        else:
            data_fim_periodo = proximas_mudancas.iloc[0]['data_inicio']
            if data_fim_periodo > hoje: data_fim_periodo = hoje

        dias_no_periodo = (data_fim_periodo - data_atual_cursor).days
        if dias_no_periodo > 0:
            cdi_momento = max(0, taxa_selic_momento - 0.10)
            taxa_anual_aplicada = (pct_cdi / 100) * (cdi_momento / 100)
            fator = (1 + taxa_anual_aplicada) ** (dias_no_periodo / 365)
            montante *= fator
        data_atual_cursor = data_fim_periodo
    return montante

def calcular_taxa_anual_bruta(tipo_indexador, taxa_input, cdi_atual, ipca_atual):
    if tipo_indexador == "% do CDI": return (taxa_input / 100) * (cdi_atual / 100)
    elif tipo_indexador == "IPCA +": return ((1 + ipca_atual/100) * (1 + taxa_input/100)) - 1
    else: return taxa_input / 100

def calcular_taxa_anual_bruta_simples(tipo_indexador, taxa_input, cdi_atual, ipca_atual):
    if tipo_indexador == "% do CDI": return (taxa_input / 100) * (cdi_atual / 100)
    elif tipo_indexador == "IPCA +": return ((1 + ipca_atual/100) * (1 + taxa_input/100)) - 1
    else: return taxa_input / 100

# --- LOGIN ---
def verificar_login(usuario, senha):
    try:
        p = conectar()
        if not p: return False
        aba = p.worksheet("usuarios")
        usuarios_db = aba.get_all_records()
        for u in usuarios_db:
            if str(u['nome']).strip().lower() == usuario.strip().lower() and str(u['senha']).strip() == str(senha).strip():
                return True
        return False
    except: return False

def criar_usuario(usuario, senha):
    try:
        p = conectar()
        if not p: return False, "Erro conexão."
        aba = p.worksheet("usuarios")
        usuarios_db = aba.get_all_records()
        for u in usuarios_db:
            if str(u['nome']).strip().lower() == usuario.strip().lower(): return False, "Usuário já existe!"
        aba.append_row([usuario, senha, ""])
        return True, "Criado com sucesso!"
    except Exception as e: return False, f"Erro: {e}"

# ==================================================
# 3. INTERFACE PRINCIPAL
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
    with col1: selic_atual = st.number_input("Taxa Selic (%)", value=val_selic_inicial, step=0.5, format="%.2f", key="global_selic") 
    with col2: cdi_estimado = selic_atual - 0.10; st.metric("CDI Estimado (%)", f"{cdi_estimado:.2f}%")
    with col3: ipca_estimado = st.number_input("IPCA Projetado (%)", value=4.50, step=0.5, format="%.2f", key="global_ipca")

st.divider()

aba_comparativo, aba_calculadora, aba_meta, aba_compras, aba_patrimonio, aba_despesas = st.tabs([
    "⚖️ Comparativo", "📈 Simulador", "🎯 Metas", "🛒 Compras", "💰 Meus Investimentos 🔒", "💸 Extrato Despesas 🔒"
])

# ==================================================
# ABAS PÚBLICAS
# ==================================================

# --- ABA 1: COMPARATIVO ---
with aba_comparativo:
    st.subheader("⚖️ Comparatiovo de Rentabilidade")
    
    with st.form("form_comparativo"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 1. Produto Atual")
            tipo_produto = st.selectbox("Produto", ["Tributado (CDB, RDB, LC, Tesouro)", "Isento (LCI, LCA, CRI, CRA)"], key="comp_prod")
            # CORREÇÃO AQUI: value=0, min_value=0
            prazo_meses = st.number_input("Prazo (meses)", value=0, step=1, min_value=0, key="comp_prazo")
        with c2:
            st.markdown("#### 2. Comparar com")
            indexador = st.selectbox("Indexador", ["% do CDI", "IPCA +", "Taxa Fixa (Pré)"], key="comp_idx")
            # CORREÇÃO AQUI
            taxa_usuario = st.number_input("Taxa", value=0.0, min_value=0.0, step=0.5, format="%.2f", key="comp_taxa")
        with c3:
            st.write(""); st.write(""); st.write(""); st.write(""); st.write("")
            submit_comp = st.form_submit_button("Calcular Comparativo", type="primary", use_container_width=True)

    if submit_comp:
        if prazo_meses > 0 and taxa_usuario > 0:
            st.session_state['res_comp'] = {'prazo': prazo_meses, 'taxa': taxa_usuario, 'tipo': tipo_produto, 'idx': indexador}
        else:
            st.warning("Preencha prazo e taxa.")

    if st.session_state['res_comp']:
        d = st.session_state['res_comp']
        st.divider()
        dias_est = int(d['prazo'] * (365 / 12))
        aliq = calcular_aliquota_ir(dias_est)
        fator_ir = (1 - aliq) if "Tributado" in d['tipo'] else 1.0
        tx_bruta = calcular_taxa_anual_bruta(d['idx'], d['taxa'], cdi_estimado, ipca_estimado)
        tx_liq = tx_bruta * fator_ir
        
        equiv = (tx_liq / (cdi_estimado/100)) * 100 if "Tributado" in d['tipo'] else (tx_liq / ((1 - aliq) * (cdi_estimado/100))) * 100
        lbl = "Equivalência em LCI/LCA" if "Tributado" in d['tipo'] else "Equivalência em CDB/RDB"

        st.caption(f"Prazo: **{dias_est} dias** | IR: **{aliq*100:.1f}%**")
        r1, r2 = st.columns(2)
        r1.metric("Rentabilidade Líquida Real", f"{tx_liq*100:.2f}% a.a.")
        r2.metric(lbl, f"{equiv:.2f}% do CDI", delta="Ponto de equilíbrio", delta_color="off")

# --- ABA 2: CALCULADORA ---
with aba_calculadora:
    st.subheader("📈 Simulador de Juros Compostos")
    
    with st.form("form_calculadora"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 1. Aportes")
            valor_inicial = st.number_input("Valor Inicial (R$)", value=0.0, step=1000.0, format="%.2f", key="calc_ini")
            aporte_mensal = st.number_input("Aporte Mensal (R$)", value=0.0, step=100.0, format="%.2f", key="calc_aporte")
            # CORREÇÃO AQUI
            meses_input = st.number_input("Prazo (Meses)", value=0, step=1, min_value=0, key="calc_meses")
        with c2:
            st.markdown("#### 2. Rentabilidade")
            tipo_trib = st.selectbox("Produto", ["Tributado", "Isento"], key="calc_prod_type")
            tipo_rent = st.selectbox("Indexador", ["% do CDI", "IPCA +", "Taxa Fixa (Pré)"], key="calc_rent_type")
            
            # CORREÇÃO AQUI (value explícito)
            if tipo_rent == "% do CDI": 
                taxa_calc = st.number_input("Taxa", value=0.0, min_value=0.0, step=0.5, format="%.2f", key="calc_taxa_cdi")
            elif tipo_rent == "IPCA +": 
                taxa_calc = st.number_input("Taxa", value=0.0, min_value=0.0, step=0.5, format="%.2f", key="calc_taxa_ipca")
            else: 
                taxa_calc = st.number_input("Taxa", value=0.0, min_value=0.0, step=0.5, format="%.2f", key="calc_taxa_fixa")
            
        with c3:
            st.write(""); st.write(""); st.write(""); st.write(""); st.write("")
            submit_calc = st.form_submit_button("Calcular Futuro", type="primary", use_container_width=True)

    if submit_calc:
        if months_input := meses_input:
            taxa_efetiva = calcular_taxa_anual_bruta(tipo_rent, taxa_calc, cdi_estimado, ipca_estimado)
            st.session_state['res_calc'] = {'vi': valor_inicial, 'pm': aporte_mensal, 'm': meses_input, 'tx': taxa_efetiva, 'trib': tipo_trib}
        else:
            st.warning("O prazo deve ser maior que zero.")

    if st.session_state['res_calc']:
        d = st.session_state['res_calc']
        st.divider()
        i_mensal = ((1 + d['tx']) ** (1/12)) - 1
        dados = []
        montante = d['vi']
        investido = d['vi']
        for m in range(1, d['m'] + 1):
            montante = montante * (1 + i_mensal) + d['pm']
            investido += d['pm']
            dados.append({"Mês": m, "Total Bruto": montante, "Investido": investido})
        
        df_calc = pd.DataFrame(dados)
        if not df_calc.empty:
            final_bruto = df_calc.iloc[-1]["Total Bruto"]
            lucro = final_bruto - df_calc.iloc[-1]["Investido"]
            ir = 0 if d['trib'] == "Isento" else lucro * calcular_aliquota_ir(d['m']*30)
            
            final_liquido = final_bruto - ir
            investido_total = investido

            # Linha 1: Bruto / IR / Líquido
            k1, k2, k3 = st.columns(3)
            k1.metric("💰 Valor Bruto Final", formatar_real(final_bruto))
            k2.metric("IR a Pagar", formatar_real(ir))
            k3.metric("Valor Líquido Final", formatar_real(final_liquido))

            # Linha 2: Investido / Lucro / Vazio
            k4, k5, k6 = st.columns(3)
            k4.metric("Total Investido", formatar_real(investido_total))
            k5.metric("Lucro Líquido", formatar_real(lucro - ir))
            k6.write("")  # Espaço vazio para manter a simetria

            st.line_chart(df_calc, x="Mês", y=["Total Bruto"], color=["#00FF00"])

# --- ABA 3: METAS ---
with aba_meta:
    st.subheader("🎯 Planejador de Metas")
    with st.form("form_meta"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 1. Objetivo")
            meta_ini = st.number_input("Tenho hoje (R$)", value=0.0, step=1000.0, format="%.2f", key="meta_ini_val")
            meta_obj = st.number_input("Quero ter (R$)", value=0.0, step=100000.0, format="%.2f", key="meta_obj_val")
            # CORREÇÃO AQUI: value=0
            meta_anos = st.number_input("Em quantos anos?", value=0, step=1, min_value=0, key="meta_anos_val")
        with c2:
            st.markdown("#### 2. Onde investir?")
            meta_trib = st.selectbox("Produto", ["Tributado", "Isento"], key="meta_trib_sel")
            meta_idx = st.selectbox("Indexador", ["% do CDI", "IPCA +", "Taxa Fixa"], key="meta_idx_sel")
            
            # CORREÇÃO AQUI: value=0.0
            if meta_idx == "% do CDI": 
                meta_taxa = st.number_input("Taxa", value=0.0, min_value=0.0, step=0.5, format="%.2f", key="meta_rate_cdi")
            elif meta_idx == "IPCA +": 
                meta_taxa = st.number_input("Taxa", value=0.0, min_value=0.0, step=0.5, format="%.2f", key="meta_rate_ipca")
            else: 
                meta_taxa = st.number_input("Taxa", value=0.0, min_value=0.0, step=0.5, format="%.2f", key="meta_rate_fixa")
        with c3:
            st.write(""); st.write(""); st.write(""); st.write(""); st.write("")
            submit_meta = st.form_submit_button("Calcular Aporte Necessário", type="primary", use_container_width=True)

    if submit_meta:
        if meta_obj > meta_ini and meta_anos > 0:
            st.session_state['res_meta'] = True
        else:
            st.warning("Defina um objetivo maior que o valor atual e prazo maior que zero.")

    if st.session_state['res_meta']:
        st.divider()
        if meta_obj > meta_ini and meta_anos > 0:
            taxa_b = calcular_taxa_anual_bruta(meta_idx, meta_taxa, cdi_estimado, ipca_estimado)
            ir = 0 if meta_trib == "Isento" else calcular_aliquota_ir(meta_anos*360)
            taxa_liq = taxa_b * (1 - ir)
            i_mes = ((1 + taxa_liq) ** (1/12)) - 1
            
            if i_mes == 0: aporte = (meta_obj - meta_ini) / (meta_anos*12)
            else: aporte = (meta_obj - (meta_ini * ((1+i_mes)**(meta_anos*12)))) / ((((1+i_mes)**(meta_anos*12)) - 1) / i_mes)
            
            c_res1, c_res2 = st.columns(2)
            c_res1.metric("Você precisa guardar por mês:", formatar_real(aporte))
            c_res2.info(f"Taxa Líquida considerada: {taxa_liq*100:.2f}% a.a.")
        else:
            st.warning("Defina um objetivo maior que o valor atual e prazo maior que zero.")

# --- ABA 4: COMPRAS ---
with aba_compras:
    st.subheader("🛒 Calculadora: À Vista ou A Prazo?")
    
    with st.form("form_compras"):
        c1, c2, c3 = st.columns(3)
        
        # --- COLUNA 1 ---
        with c1:
            st.markdown("#### 1. A Compra")
            compra_valor = st.number_input("Valor parcelado, sem desconto (R$)", value=0.0, step=50.0, format="%.2f", key="c1_valor")
            compra_parcelas = st.number_input("Nº Parcelas", value=0, step=1, min_value=0)
            
            st.markdown("---")
            
            tipo_desc_anterior = st.session_state.get("tipo_desc_radio", "Valor à Vista (R$)")
            lbl = "Valor (R$) / Desconto (%)" if tipo_desc_anterior == "Valor à Vista (R$)" else "Desconto (%)"
            step_beneficio = 50.0 if tipo_desc_anterior == "Valor à Vista (R$)" else 0.5
            
            input_beneficio = st.number_input(lbl, value=0.0, step=step_beneficio, format="%.2f", key="c2_input1")
            tipo_desconto = st.radio("Tipo de desconto", ["Valor à Vista (R$)", "Porcentagem (%)"], horizontal=True, label_visibility="collapsed", key="tipo_desc_radio")

        # --- COLUNA 2 ---
        with c2:
            st.markdown("#### 2. Oportunidade")
            
            tipo_liquidez = st.selectbox("Onde o dinheiro ficará investido?", ["CDB / Conta Digital (% do CDI)", "Poupança", "Não invisto"], key="compra_tipo_liq")
            
            percentual_cdi = st.number_input("Taxa", value=0.0, min_value=0.0, step=0.5, format="%.2f", key="compra_cdi_val")
            
            st.markdown("---")
            compra_cashback = st.number_input("Cashback Cartão (%)", value=0.0, step=0.25, format="%.2f")

        # --- COLUNA 3 ---
        with c3:
            st.write(""); st.write(""); st.write(""); st.write(""); st.write("")
            submit_compra = st.form_submit_button("Calcular Decisão", type="primary", use_container_width=True)

    if submit_compra:
        if compra_parcelas > 0 and compra_valor > 0:
            if tipo_desconto == "Porcentagem (%)":
                val_vista = compra_valor * (1 - (input_beneficio/100))
                perc_real = input_beneficio
            else:
                val_vista = input_beneficio
                perc_real = (1 - (val_vista / compra_valor)) * 100 if compra_valor > 0 else 0.0

            if tipo_liquidez == "Não invisto": taxa_mensal = 0.0
            elif tipo_liquidez == "Poupança":
                taxa_mensal = 0.005 if selic_atual > 8.5 else ((1 + (selic_atual*0.7/100))**(1/12)) - 1
            else:
                dias = int(compra_parcelas * 30) if compra_parcelas > 0 else 30
                ir = calcular_aliquota_ir(dias)
                tx_anual = (percentual_cdi/100) * (cdi_estimado/100)
                taxa_mensal = ((1 + (tx_anual*(1-ir)))**(1/12)) - 1

            st.session_state['res_compra'] = {
                'cv': compra_valor, 'parc': compra_parcelas, 'vv': val_vista, 'tx': taxa_mensal, 
                'cash': compra_cashback, 'perc': perc_real
            }
        else:
            st.warning("Preencha o valor da compra.")

    if st.session_state['res_compra']:
        c = st.session_state['res_compra']
        st.divider()
        sobra = c['cv'] - c['vv']
        vp = c['cv'] / c['parc']
        vcash = c['cv'] * (c['cash']/100)
        lv, lp, m = [sobra], [c['cv']], [0]
        sv, sp = sobra, c['cv']
        
        for i in range(1, int(c['parc'])+1):
            sv *= (1 + c['tx'])
            sp = (sp * (1 + c['tx'])) - vp
            if i == 1: sp += vcash
            lv.append(sv); lp.append(sp); m.append(i)
            
        dif = abs(sv - sp)
        cres, cg = st.columns([1, 2])
        with cres:
            win = "À VISTA" if sv > sp else "A PRAZO"
            st.success(f"🏆 VENCEDOR: **{win}**")
            st.markdown(f"### Saldo: :green[{formatar_real(max(sv, sp))}]")

            # Identificar perdedor
            if sv > sp:
                perdedor = "A PRAZO"
                saldo_perdedor = sp
            else:
                perdedor = "À VISTA"
                saldo_perdedor = sv

            # Quadro azul CLEAN (três blocos, linha em branco entre eles)
            st.info(
                f"Vantagem: {formatar_real(dif)}\n\n"
                f"Saldo no cenário {perdedor}: {formatar_real(saldo_perdedor)}\n\n"
                f"Desconto considerado: {c['perc']:.2f}%"
            )
        with cg:
            cor_v, cor_p = ("#00FF00", "#FF4B4B") if sv > sp else ("#FF4B4B", "#00FF00")
            st.line_chart(pd.DataFrame({"Mês": m, "À Vista": lv, "A Prazo": lp}).set_index("Mês"), color=[cor_v, cor_p])
    else: st.info("👆 Preencha os valores acima para simular.")

# ==================================================
# ÁREA RESTRITA
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

# --- ABA 5: INVESTIMENTOS ---
with aba_patrimonio:
    if not st.session_state.get('logado', False): mostrar_tela_login("inv")
    else:
        c_topo1, c_topo2 = st.columns([3, 1])
        with c_topo1:
            st.subheader("💰 Controle de Patrimônio")
            st.caption("Cadastre seus investimentos e veja quanto eles valem HOJE (Estimativa).")
        with c_topo2:
            if st.button("🔄 Atualizar", key="btn_up_invest"):
                st.cache_data.clear()
                st.rerun()
        
        with st.expander("➕ Adicionar Novo Investimento", expanded=False):
            with st.form("form_investimentos"):
    
                c1, c2, c3 = st.columns(3)

                with c1:
                    nom = st.text_input("Nome do investimento")
                    dat = st.date_input("Data da aplicação", format="DD/MM/YYYY")

                with c2:
                    inst = st.text_input("Banco / Corretora")
                    val = st.number_input("Valor aplicado (R$)", 0.0, step=100.0, format="%.2f")
                    st.text_input("Dono", st.session_state['usuario_atual'], disabled=True)

                with c3:
                    idx = st.selectbox("Indexador", ["% do CDI", "IPCA +", "Taxa Fixa"])
                    tx = st.number_input("Taxa", 0.0, step=0.5)
                    trib = st.selectbox("Tributação", ["Tributado", "Isento"])

                salvar = st.form_submit_button("Salvar")

                if salvar:
                    if val > 0:
                        try:
                            conectar().worksheet("investimentos").append_row([
                                dat.strftime("%d/%m/%Y"),
                                nom,
                                inst,
                                val,
                                idx,
                                tx,
                                trib,
                                st.session_state['usuario_atual']
                            ])
                            st.success("Cadastrado!")
                            st.cache_data.clear()
                            st.rerun()
                        except:
                            st.error("Erro no salvamento.")
                    else:
                        st.warning("Valor zerado.")
        with st.expander("⚙️ Gerenciar Histórico Selic", expanded=False):
            c_h1, c_h2 = st.columns([2, 1])
            df_hist = get_historico_selic_df()
            def_data = datetime.now(); def_tx = 11.25
            if not df_hist.empty:
                ult = df_hist.sort_values('data_inicio', ascending=False).iloc[0]
                def_data = ult['data_inicio']; def_tx = float(ult['taxa_anual'])
            with c_h1:
                st.info("Cadastre aqui as taxas Selic que ainda não estão no histórico.")
                data_selic = st.date_input("Data da Mudança da Taxa", value=def_data, key="hist_data")
                taxa_selic_hist = st.number_input("Nova Taxa Selic Anual (%)", value=def_tx, step=0.25, format="%.2f", key="hist_taxa")
                if st.button("💾 Salvar no Histórico"):
                    try:
                        p = conectar()
                        p.worksheet("historico_selic").append_row([data_selic.strftime("%d/%m/%Y"), taxa_selic_hist])
                        st.success("Salvo!")
                        st.cache_data.clear()
                        st.rerun()
                    except: st.error("Erro.")
            with c_h2:
                if not df_hist.empty:
                    df_hist['Data'] = df_hist['data_inicio'].dt.strftime("%d/%m/%Y")
                    df_hist_sorted = df_hist.sort_values('data_inicio', ascending=False)
                    st.dataframe(
                        df_hist_sorted[['Data', 'taxa_anual']].style.format({"taxa_anual": "{:.2f}"}),
                        height=200,
                        hide_index=True,
                        use_container_width=True
                    )
        
        try:
            p = conectar()
            if p:
                df_i = pd.DataFrame(p.worksheet("investimentos").get_all_records())
                if not df_i.empty and "usuario" in df_i.columns:
                    df_i = df_i[df_i["usuario"].astype(str).str.lower() == st.session_state['usuario_atual'].lower()]
                
                if not df_i.empty:
                    df_s = get_historico_selic_df()
                    res = []
                    ti = 0                # total investido
                    total_bruto = 0       # valor antes do IR
                    total_liquido = 0     # valor após IR
                    total_ir = 0          # IR total

                    for _, r in df_i.iterrows():
                        try: dt = datetime.strptime(str(r['data_compra']), "%d/%m/%Y")
                        except: continue
                        vi = float(str(r['valor_inicial']).replace("R$","").replace(".","").replace(",","."))
                        tc = float(str(r['taxa']).replace(",", "."))
                        
                        if r['indexador'] == "% do CDI": va = calcular_valor_futuro_dinamico(vi, dt, tc, df_s, selic_atual)
                        else:
                            dias = (datetime.now() - dt).days
                            txa = calcular_taxa_anual_bruta_simples(r['indexador'], tc, cdi_estimado, ipca_estimado)
                            va = vi * ((1 + txa)**(dias/365))
                        
                        dias = (datetime.now() - dt).days

                        lucro_bruto = va - vi

                        # IR
                        if str(r.get("tributacao", "Tributado")).lower() == "tributado":
                            # tabela regressiva
                            if dias <= 180:
                                ir = 0.225
                            elif dias <= 360:
                                ir = 0.20
                            elif dias <= 720:
                                ir = 0.175
                            else:
                                ir = 0.15
                            imposto = lucro_bruto * ir
                        else:
                            imposto = 0

                        lucro_liquido = lucro_bruto - imposto

                        # ACUMULADORES ATUALIZADOS
                        ti += vi
                        total_bruto += va
                        total_liquido += (va - imposto)
                        total_ir += imposto

                        res.append({
                            "Nome": r['nome'],
                            "Instituição": r['instituicao'],
                            "Data": r['data_compra'],
                            "Valor Investido": vi,
                            "Valor Hoje": va - imposto,  # valor líquido
                            "Lucro Líquido": lucro_liquido,
                            "IR Pago": imposto,
                            "Rent. Líquida": f"{(lucro_liquido/vi)*100:.2f}%"
                        })

                    k1, k2, k3 = st.columns(3)
                    k1.metric("Patrimônio bruto aproximado", formatar_real(total_bruto))
                    k2.metric("IR a Pagar", formatar_real(total_ir))
                    k3.metric("Patrimônio líquido aproximado", formatar_real(total_liquido))

                    k4, k5, k6 = st.columns(3)
                    k4.metric("Investido", formatar_real(ti))
                    k5.metric("Lucro aproximado", formatar_real(total_liquido - ti),
                              delta=f"{((total_liquido/ti)-1)*100:.1f}%" if ti>0 else "0%")
                    k6.write("")

                    st.dataframe(
                        pd.DataFrame(res).style
                        .format({
                            "Valor Investido": "R$ {:,.2f}", 
                            "Valor Hoje": "R$ {:,.2f}", 
                            "Lucro Líquido": "R$ {:,.2f}", # Nova formatação
                            "IR Pago": "R$ {:,.2f}"        # Nova formatação
                        })
                        .set_properties(**{'text-align': 'center'}) # Centraliza Células
                        .set_table_styles([dict(selector='th', props=[('text-align', 'center')])]), # Centraliza Cabeçalho
                        use_container_width=True, 
                        hide_index=True
                    )
                    
                else: st.info("Nenhum investimento seu.")
        except: st.warning("Sem dados.")

# --- ABA 6: DESPESAS ---
with aba_despesas:
    if not st.session_state.get('logado', False): mostrar_tela_login("ext")
    else:
        c1, c2 = st.columns([3,1])
        with c1: st.subheader("💸 Extrato de Despesas")
        with c2: 
            if st.button("🔄 Atualizar", key="btn_ext_up"): st.cache_data.clear(); st.rerun()
        
        @st.cache_data(ttl=60)
        def load_g(): return pd.DataFrame(conectar().worksheet("registros").get_all_records()) if conectar() else pd.DataFrame()
        
        df = load_g()
        if not df.empty:
            if "usuario" in df.columns: df = df[df["usuario"].astype(str).str.lower() == st.session_state['usuario_atual'].lower()]
            
            c1, c2 = st.columns([2,1])
            with c1:
                df["dt"] = pd.to_datetime(df["data"], format="%d/%m/%Y", errors="coerce")
                df["mes"] = df["dt"].dt.strftime("%m/%Y")
                meses = sorted(df["mes"].dropna().unique().tolist(), reverse=True)
                f_mes = st.selectbox("Mês", ["Todos"] + meses, key="fil_mes")
            
            df_f = df.copy()
            if f_mes != "Todos": df_f = df_f[df_f["mes"] == f_mes]
            
            if not df_f.empty:
                def clean(v):
                    s = str(v).replace("R$", "").strip()
                    if "," in s: s = s.replace(".", "").replace(",", ".")
                    try: return float(s)
                    except: return 0.0
                
                df_f["v"] = df_f["valor"].apply(clean)
                st.metric("Total Gasto", formatar_real(df_f["v"].sum()))
                
                g1, g2 = st.columns([1, 2])
                with g1:
                    st.markdown("##### Categorias")
                    cat_s = df_f.groupby("categoria")["v"].sum().reset_index().sort_values("v", ascending=False)
                    colors = {"Alimentação": "#FFB3BA", "Transporte": "#FFDFBA", "Lazer": "#FFFFBA", "Casa": "#BAFFC9", "Saúde": "#BAE1FF", "Educação": "#E2C4FF", "Outros": "#D3D3D3"}
                    def get_c(c): return colors.get(c, "#A0C4FF")
                    
                    import altair as alt
                    base = alt.Chart(cat_s).encode(theta=alt.Theta("v", stack=True), color=alt.Color("categoria", scale=alt.Scale(domain=cat_s["categoria"].tolist(), range=[get_c(c) for c in cat_s["categoria"]]), legend=None), tooltip=["categoria", "v"])
                    st.altair_chart(base.mark_arc(innerRadius=70, outerRadius=90), use_container_width=True)
                    for _, r in cat_s.iterrows(): st.markdown(f"<div style='display: flex; align-items: center; margin-bottom: 5px;'><span style='height: 12px; width: 12px; background-color: {get_c(r['categoria'])}; border-radius: 50%; display: inline-block; margin-right: 8px;'></span><span style='font-size: 14px;'><b>{r['categoria']}:</b> {formatar_real(r['v'])}</span></div>", unsafe_allow_html=True)
                
                with g2:
                    cols = [c for c in ["data", "item", "valor", "categoria", "forma_pagamento"] if c in df_f.columns]
                    st.dataframe(df_f[cols].style.format({"valor": "R$ {}"}), use_container_width=True, hide_index=True)
            else: st.info("Sem dados.")