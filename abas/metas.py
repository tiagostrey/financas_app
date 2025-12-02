import streamlit as st
from utils import calcular_taxa_anual_bruta, calcular_aliquota_ir, formatar_real

def render(cdi_estimado, ipca_estimado):
    st.subheader("🎯 Planejador de Metas")
    with st.form("form_meta"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 1. Objetivo")
            meta_ini = st.number_input("Tenho hoje (R$)", value=0.0, step=1000.0, format="%.2f", key="meta_ini_val")
            meta_obj = st.number_input("Quero ter (R$)", value=0.0, step=100000.0, format="%.2f", key="meta_obj_val")
            meta_anos = st.number_input("Em quantos anos?", value=0, step=1, min_value=0, key="meta_anos_val")
        with c2:
            st.markdown("#### 2. Onde investir?")
            meta_trib = st.selectbox("Produto", ["Tributado (CDB, RDB, LC, Tesouro)", "Isento (LCI, LCA, CRI, CRA)"], key="meta_trib_sel")
            meta_idx = st.selectbox("Indexador", ["% do CDI", "IPCA +", "Taxa Fixa"], key="meta_idx_sel")
            
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
            
            # Correção lógica Isento
            ir = 0 if "Isento" in meta_trib else calcular_aliquota_ir(meta_anos*360)
            
            taxa_liq = taxa_b * (1 - ir)
            i_mes = ((1 + taxa_liq) ** (1/12)) - 1
            
            if i_mes == 0: aporte = (meta_obj - meta_ini) / (meta_anos*12)
            else: aporte = (meta_obj - (meta_ini * ((1+i_mes)**(meta_anos*12)))) / ((((1+i_mes)**(meta_anos*12)) - 1) / i_mes)
            
            c_res1, c_res2 = st.columns(2)
            c_res1.metric("Você precisa guardar por mês:", formatar_real(aporte))
            c_res2.info(f"Taxa Líquida considerada: {taxa_liq*100:.2f}% a.a.")
        else:
            st.warning("Defina um objetivo maior que o valor atual e prazo maior que zero.")