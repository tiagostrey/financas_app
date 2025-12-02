import streamlit as st
from utils import calcular_aliquota_ir, calcular_taxa_anual_bruta

def render(cdi_estimado, ipca_estimado):
    st.subheader("⚖️ Comparativo de Rentabilidade")
    
    with st.form("form_comparativo"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("#### 1. Produto Atual")
            tipo_produto = st.selectbox("Produto", ["Tributado (CDB, RDB, LC, Tesouro)", "Isento (LCI, LCA, CRI, CRA)"], key="comp_prod")
            prazo_meses = st.number_input("Prazo (meses)", value=0, step=1, min_value=0, key="comp_prazo")
        with c2:
            st.markdown("#### 2. Comparar com")
            indexador = st.selectbox("Indexador", ["% do CDI", "IPCA +", "Taxa Fixa (Pré)"], key="comp_idx")
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
        
        # Correção da lógica de Isento (usando 'in')
        fator_ir = (1 - aliq) if "Tributado" in d['tipo'] else 1.0
        
        tx_bruta = calcular_taxa_anual_bruta(d['idx'], d['taxa'], cdi_estimado, ipca_estimado)
        tx_liq = tx_bruta * fator_ir
        
        # Cálculo de equivalência
        if "Tributado" in d['tipo']:
            equiv = (tx_liq / (cdi_estimado/100)) * 100 
            lbl = "Equivalência em LCI/LCA"
        else:
            equiv = (tx_liq / ((1 - aliq) * (cdi_estimado/100))) * 100
            lbl = "Equivalência em CDB/RDB"

        st.caption(f"Prazo: **{dias_est} dias** | IR: **{aliq*100:.1f}%**")
        r1, r2 = st.columns(2)
        r1.metric("Rentabilidade Líquida Real", f"{tx_liq*100:.2f}% a.a.")
        r2.metric(lbl, f"{equiv:.2f}% do CDI", delta="Ponto de equilíbrio", delta_color="off")