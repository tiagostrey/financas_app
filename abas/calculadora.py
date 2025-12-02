import streamlit as st
import pandas as pd
from utils import calcular_taxa_anual_bruta, calcular_aliquota_ir, formatar_real

def render(cdi_estimado, ipca_estimado):
    st.subheader("📈 Simulador de Juros Compostos")
    
    with st.form("form_calculadora"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 1. Aportes")
            valor_inicial = st.number_input("Valor Inicial (R$)", value=0.0, step=1000.0, format="%.2f", key="calc_ini")
            aporte_mensal = st.number_input("Aporte Mensal (R$)", value=0.0, step=100.0, format="%.2f", key="calc_aporte")
            meses_input = st.number_input("Prazo (Meses)", value=0, step=1, min_value=0, key="calc_meses")
        with c2:
            st.markdown("#### 2. Rentabilidade")
            tipo_trib = st.selectbox("Produto", ["Tributado (CDB, RDB, LC, Tesouro)", "Isento (LCI, LCA, CRI, CRA)"], key="calc_prod_type")
            tipo_rent = st.selectbox("Indexador", ["% do CDI", "IPCA +", "Taxa Fixa (Pré)"], key="calc_rent_type")
            
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
        if meses_input > 0:
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
            
            # Correção da lógica de Isento (usando 'in')
            ir = 0 if "Isento" in d['trib'] else lucro * calcular_aliquota_ir(d['m']*30)
            
            final_liquido = final_bruto - ir
            investido_total = investido

            k1, k2, k3 = st.columns(3)
            k1.metric("💰 Valor Bruto Final", formatar_real(final_bruto))
            k2.metric("IR a Pagar", formatar_real(ir))
            k3.metric("Valor Líquido Final", formatar_real(final_liquido))

            k4, k5, k6 = st.columns(3)
            k4.metric("Total Investido", formatar_real(investido_total))
            k5.metric("Lucro Líquido", formatar_real(lucro - ir))
            k6.write("")

            st.line_chart(df_calc, x="Mês", y=["Total Bruto"], color=["#00FF00"])