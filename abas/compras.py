import streamlit as st
import pandas as pd
from utils import calcular_aliquota_ir, formatar_real

def render(selic_atual, cdi_estimado):
    st.subheader("🛒 Calculadora: À Vista ou A Prazo?")
    
    with st.form("form_compras"):
        c1, c2, c3 = st.columns(3)
        
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

        with c2:
            st.markdown("#### 2. Oportunidade")
            tipo_liquidez = st.selectbox("Onde o dinheiro ficará investido?", ["CDB / Conta Digital (% do CDI)", "Poupança", "Não invisto"], key="compra_tipo_liq")
            percentual_cdi = st.number_input("Taxa", value=0.0, min_value=0.0, step=0.5, format="%.2f", key="compra_cdi_val")
            st.markdown("---")
            compra_cashback = st.number_input("Cashback Cartão (%)", value=0.0, step=0.25, format="%.2f")

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

            if sv > sp:
                perdedor = "A PRAZO"
                saldo_perdedor = sp
            else:
                perdedor = "À VISTA"
                saldo_perdedor = sv

            st.info(
                f"Vantagem: {formatar_real(dif)}\n\n"
                f"Saldo no cenário {perdedor}: {formatar_real(saldo_perdedor)}\n\n"
                f"Desconto considerado: {c['perc']:.2f}%"
            )
        with cg:
            cor_v, cor_p = ("#00FF00", "#FF4B4B") if sv > sp else ("#FF4B4B", "#00FF00")
            st.line_chart(pd.DataFrame({"Mês": m, "À Vista": lv, "A Prazo": lp}).set_index("Mês"), color=[cor_v, cor_p])