import streamlit as st
import pandas as pd
from datetime import datetime
import time
import uuid
from conexao import conectar
from utils import (
    formatar_real, 
    calcular_aliquota_ir, 
    get_historico_selic_df, 
    calcular_valor_futuro_dinamico, 
    calcular_taxa_anual_bruta_simples
)

def render(selic_atual, cdi_estimado, ipca_estimado):
    # --- CABEÇALHO ---
    c_topo1, c_topo2 = st.columns([3, 1])
    with c_topo1:
        st.subheader("💰 Controle de Patrimônio")
        st.caption("Resumo atualizado da sua carteira de investimentos.")
    with c_topo2:
        if st.button("🔄 Atualizar", key="btn_up_invest"):
            st.cache_data.clear()
            st.rerun()

    # ==============================================================================
    # 1. LEITURA DE DADOS E CÁLCULOS
    # ==============================================================================
    res = [] 
    df_full = pd.DataFrame()
    df_user = pd.DataFrame()
    df_hist = get_historico_selic_df() 
    
    try:
        p = conectar()
        if p:
            aba_inv = p.worksheet("investimentos")
            todos_dados = aba_inv.get_all_records()
            df_full = pd.DataFrame(todos_dados)
            
            # Filtra usuário atual
            if not df_full.empty and "usuario" in df_full.columns:
                df_user = df_full[df_full["usuario"].astype(str).str.lower() == st.session_state['usuario_atual'].lower()].copy()
            
            if not df_user.empty:
                ti = 0; ta = 0
                
                for idx, r in df_user.iterrows():
                    try: dt = datetime.strptime(str(r['data_compra']), "%d/%m/%Y")
                    except: continue
                    
                    # Limpeza e conversão
                    vi = float(str(r['valor_inicial']).replace("R$","").replace(".","").replace(",","."))
                    tc = float(str(r['taxa']).replace(",", "."))
                    
                    # ID e Vencimento
                    item_id = str(r.get('id_invest', ''))
                    if not item_id: item_id = f"temp_{idx}"
                    data_venc_str = str(r.get('data_venc', ''))

                    # Cálculo do Valor Bruto (VA)
                    if r['indexador'] == "% do CDI": 
                        va = calcular_valor_futuro_dinamico(vi, dt, tc, df_hist, selic_atual)
                    else:
                        dias = (datetime.now() - dt).days
                        txa = calcular_taxa_anual_bruta_simples(r['indexador'], tc, cdi_estimado, ipca_estimado)
                        va = vi * ((1 + txa)**(dias/365))
                    
                    # Cálculo do Líquido e IR
                    dias_corridos = (datetime.now() - dt).days
                    lucro_bruto = va - vi
                    
                    if "Isento" in str(r.get("tributacao", "")): imposto = 0.0
                    else: imposto = lucro_bruto * calcular_aliquota_ir(dias_corridos)
                    
                    lucro_liq = lucro_bruto - imposto
                    
                    res.append({
                        "Nome": r['nome'], 
                        "Instituição": r.get('instituicao', ''), 
                        "Data": r['data_compra'],
                        "Vencimento": data_venc_str,
                        "Valor Investido": vi, 
                        "Valor Hoje": va - imposto, 
                        "Lucro Líquido": lucro_liq, 
                        "IR Pago": imposto, 
                        "Rent. Líquida": f"{(lucro_liq/vi)*100:.2f}%",
                        "ID_OCULTO": item_id
                    })
                    ti += vi; ta += (va - imposto)

                # --- EXIBIÇÃO DO RESUMO ---
                k1, k2, k3 = st.columns(3)
                k1.metric("Patrimônio Líquido Estimado", formatar_real(ta))
                k2.metric("Total Investido", formatar_real(ti))
                k3.metric("Lucro Líquido Acumulado", formatar_real(ta-ti), delta=f"{((ta/ti)-1)*100:.1f}%" if ti>0 else "0%")
                
                df_exibir = pd.DataFrame(res).drop(columns=["ID_OCULTO"])
                
                st.dataframe(
                    df_exibir, 
                    column_config={
                        "Valor Investido": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Valor Hoje": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Lucro Líquido": st.column_config.NumberColumn(format="R$ %.2f"),
                        "IR Pago": st.column_config.NumberColumn(format="R$ %.2f"),
                        "Vencimento": st.column_config.TextColumn("Vencimento"),
                        "Rent. Líquida": st.column_config.TextColumn("Rent. Líquida")
                    },
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("Nenhum investimento cadastrado. Utilize o formulário abaixo para começar.")

    except Exception as e: st.warning(f"Aguardando conexão... ({e})")

    st.divider()

    # ==============================================================================
    # 2. ADICIONAR NOVO INVESTIMENTO
    # ==============================================================================
    with st.expander("➕ Adicionar Novo Investimento", expanded=False):
        with st.form("form_investimentos"):
            c1, c2 = st.columns(2)
            with c1: nom = st.text_input("Nome do investimento", key="inv_nome")
            with c2: inst = st.text_input("Banco / Corretora", key="inv_inst")
            
            ce1, ce2, ce3 = st.columns(3)
            with ce1:
                dat = st.date_input("Data da aplicação", format="DD/MM/YYYY", key="inv_data")
                trib = st.selectbox("Tributação", ["Tributado (CDB, RDB, LC, Tesouro)", "Isento (LCI, LCA, CRI, CRA)"], key="inv_trib")
            with ce2:
                prazo = st.number_input("Prazo (meses)", 0, step=1, key="inv_prazo")
                idx = st.selectbox("Indexador", ["% do CDI", "IPCA +", "Taxa Fixa"], key="inv_idx")
            with ce3:
                val = st.number_input("Valor aplicado (R$)", 0.0, step=100.0, format="%.2f", key="inv_val")
                tx = st.number_input("Taxa", 0.0, step=0.5, key="inv_tx")

            c_vazio1, c_salvar, c_cancelar, c_vazio2 = st.columns(4)
            with c_salvar: salvar = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
            with c_cancelar: cancelar = st.form_submit_button("Cancelar", use_container_width=True, on_click=lambda: st.session_state.update({"inv_nome": "", "inv_inst": "", "inv_val": 0.0, "inv_tx": 0.0, "inv_prazo": 0}))

            if salvar:
                if val > 0:
                    try:
                        novo_id = str(uuid.uuid4())
                        # Calcula Vencimento
                        data_vencimento = (pd.to_datetime(dat) + pd.DateOffset(months=int(prazo))).strftime("%d/%m/%Y") if prazo > 0 else ""
                        
                        conectar().worksheet("investimentos").append_row([
                            novo_id,
                            dat.strftime("%d/%m/%Y"),
                            int(prazo),
                            data_vencimento,
                            nom,
                            inst,
                            val,
                            idx,
                            tx,
                            trib,
                            st.session_state['usuario_atual']
                        ])
                        st.success("Cadastrado!")
                        for k in ["inv_nome", "inv_inst", "inv_val", "inv_tx", "inv_prazo"]:
                            if k in st.session_state: del st.session_state[k]
                        st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro no salvamento: {e}")
                else: st.warning("Valor zerado.")
            
            if cancelar: st.rerun()

    # ==============================================================================
    # 3. GERENCIAR INVESTIMENTOS
    # ==============================================================================
    with st.expander("📝 Gerenciar Investimentos Cadastrados", expanded=False):
        opcoes_investimentos = {}
        if res:
            for r in res:
                # CORREÇÃO APLICADA: Nome - Data (Valor Formatado)
                opcoes_investimentos[r['ID_OCULTO']] = f"{r['Nome']} - {r['Data']} ({formatar_real(r['Valor Investido'])})"
        
        inv_selecionado_id = st.selectbox("Selecione:", options=["Selecione..."] + list(opcoes_investimentos.keys()), format_func=lambda x: opcoes_investimentos.get(x, "Selecione..."))
        
        c_vazio1, c_edit, c_del, c_vazio2 = st.columns(4)
        with c_edit:
            if st.button("✏️ Editar", use_container_width=True):
                if inv_selecionado_id != "Selecione...":
                    st.session_state['editando_id'] = inv_selecionado_id
                    st.rerun()
                else: st.warning("Selecione um item!")
        
        with c_del:
            with st.popover("🗑️ Excluir", use_container_width=True):
                st.write("Confirma exclusão?")
                if st.button("Sim, excluir", type="primary"):
                    if inv_selecionado_id != "Selecione...":
                        try:
                            df_nova = df_full[df_full['id_invest'].astype(str) != inv_selecionado_id]
                            aba_inv.clear()
                            aba_inv.update([df_nova.columns.values.tolist()] + df_nova.astype(str).values.tolist())
                            st.success("Excluído!"); time.sleep(1); st.rerun()
                        except Exception as ex: st.error(f"Erro: {ex}")

        # FORMULÁRIO DE EDIÇÃO
        if st.session_state.get('editando_id') == inv_selecionado_id and inv_selecionado_id != "Selecione...":
            st.divider()
            try:
                item_dados = df_user[df_user['id_invest'].astype(str) == inv_selecionado_id].iloc[0]
                st.markdown(f"**Editando:** {item_dados['nome']}")
                
                with st.form("form_editar_investimento"):
                    ce1, ce2 = st.columns(2)
                    with ce1: ennome = st.text_input("Nome", value=item_dados['nome'])
                    with ce2: eninst = st.text_input("Instituição", value=item_dados.get('instituicao', ''))
                    
                    col_e1, col_e2, col_e3 = st.columns(3)
                    with col_e1:
                        try: d_obj = datetime.strptime(str(item_dados['data_compra']), "%d/%m/%Y")
                        except: d_obj = datetime.now()
                        endata = st.date_input("Data", value=d_obj, format="DD/MM/YYYY")
                        
                        lista_trib = ["Tributado (CDB, RDB, LC, Tesouro)", "Isento (LCI, LCA, CRI, CRA)"]
                        curr_trib = item_dados.get('tributacao', '')
                        idx_trib = 1 if "Isento" in curr_trib else 0
                        entrib = st.selectbox("Tributação", lista_trib, index=idx_trib)
                    
                    with col_e2:
                        try: prazo_atual = int(item_dados.get('prazo', 0))
                        except: prazo_atual = 0
                        enprazo = st.number_input("Prazo (meses)", value=prazo_atual, step=1)

                        lista_idx = ["% do CDI", "IPCA +", "Taxa Fixa"]
                        curr_idx = item_dados['indexador']
                        idx_pos = lista_idx.index(curr_idx) if curr_idx in lista_idx else 0
                        enidx = st.selectbox("Indexador", lista_idx, index=idx_pos)
                    
                    with col_e3:
                        val_str = str(item_dados['valor_inicial']).replace("R$","").replace(".","").replace(",",".")
                        try: val_float = float(val_str)
                        except: val_float = 0.0
                        enval = st.number_input("Valor", value=val_float, step=100.0, format="%.2f")

                        try: tx_float = float(str(item_dados['taxa']).replace(",", "."))
                        except: tx_float = 0.0
                        entx = st.number_input("Taxa", value=tx_float, step=0.5, format="%.2f")

                    c_v1, c_save, c_canc, c_v2 = st.columns(4)
                    with c_save: salvar_ed = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
                    with c_canc: 
                        cancel_ed = st.form_submit_button("Cancelar", use_container_width=True, 
                            on_click=lambda: st.session_state.update({'editando_id': None}))

                    if salvar_ed:
                        try:
                            idx_geral = df_full[df_full['id_invest'].astype(str) == inv_selecionado_id].index[0]
                            
                            nova_venc = (pd.to_datetime(endata) + pd.DateOffset(months=int(enprazo))).strftime("%d/%m/%Y") if enprazo > 0 else ""

                            df_full.at[idx_geral, 'nome'] = ennome
                            df_full.at[idx_geral, 'instituicao'] = eninst
                            df_full.at[idx_geral, 'data_compra'] = endata.strftime("%d/%m/%Y")
                            df_full.at[idx_geral, 'prazo'] = int(enprazo)
                            df_full.at[idx_geral, 'data_venc'] = nova_venc
                            df_full.at[idx_geral, 'valor_inicial'] = enval
                            df_full.at[idx_geral, 'indexador'] = enidx
                            df_full.at[idx_geral, 'taxa'] = entx
                            df_full.at[idx_geral, 'tributacao'] = entrib
                            
                            aba_inv.clear()
                            aba_inv.update([df_full.columns.values.tolist()] + df_full.astype(str).values.tolist())
                            st.success("Atualizado!"); st.session_state['editando_id'] = None; time.sleep(1); st.rerun()
                        except Exception as ex: st.error(f"Erro: {ex}")
                    
                    if cancel_ed: st.rerun()

            except Exception as e: st.error(f"Erro na edição: {e}")

    # ==============================================================================
    # 4. GERENCIAR HISTÓRICO SELIC
    # ==============================================================================
    with st.expander("⚙️ Gerenciar Histórico Selic", expanded=False):
        c_h1, c_h2 = st.columns([2, 1])
        def_data = datetime.now(); def_tx = 11.25
        if not df_hist.empty:
            ult = df_hist.sort_values('data_inicio', ascending=False).iloc[0]
            def_data = ult['data_inicio']; def_tx = float(ult['taxa_anual'])
        with c_h1:
            st.info("Cadastre aqui as taxas Selic.")
            data_selic = st.date_input("Data da Mudança", value=def_data, key="hist_data")
            taxa_selic_hist = st.number_input("Nova Taxa Selic Anual (%)", value=def_tx, step=0.25, format="%.2f", key="hist_taxa")
            if st.button("💾 Salvar no Histórico"):
                try:
                    p = conectar()
                    p.worksheet("historico_selic").append_row([data_selic.strftime("%d/%m/%Y"), taxa_selic_hist])
                    st.success("Salvo!"); st.cache_data.clear(); st.rerun()
                except Exception as e:
                    st.error("Erro ao salvar: {e}")
        with c_h2:
            if not df_hist.empty:
                df_hist['Data'] = df_hist['data_inicio'].dt.strftime("%d/%m/%Y")
                df_exibicao = df_hist.sort_values('data_inicio', ascending=False)[['Data', 'taxa_anual']]
                st.dataframe(df_exibicao.style.format({"taxa_anual": "{:.2f}"}), height=200, hide_index=True, use_container_width=True)