import streamlit as st
import pandas as pd
import altair as alt
from conexao import conectar
from utils import formatar_real
import time
from datetime import datetime

def render():
    c1, c2 = st.columns([3,1])
    with c1: st.subheader("💸 Extrato de Despesas")
    with c2: 
        if st.button("🔄 Atualizar", key="btn_ext_up"): st.cache_data.clear(); st.rerun()
    
    # --- TUTORIAL CONTEXTUAL ---
    with st.expander("🤖 Tutorial: Criar e Configurar Bot do Telegram"):
        st.markdown("""
        Se você deseja configurar um novo bot para lançar despesas, siga este passo a passo:
        1. Abra o Telegram e busque por **@BotFather**.
        2. Envie `/newbot` e siga as instruções.
        3. Copie o TOKEN e envie ao administrador.
        4. Busque seu ID no **@userinfobot** e envie ao administrador.
        """)

    # Carrega dados
    df_full = pd.DataFrame()
    df_user = pd.DataFrame()
    
    try:
        p = conectar()
        if p:
            aba_reg = p.worksheet("registros")
            dados = aba_reg.get_all_records()
            df_full = pd.DataFrame(dados)
            
            # Filtra usuário logado
            if not df_full.empty and "usuario" in df_full.columns:
                df_user = df_full[df_full["usuario"].astype(str).str.lower() == st.session_state['usuario_atual'].lower()].copy()
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")

    # --- FUNÇÃO DE NORMALIZAÇÃO (V0.02) ---
    def normalizar_valor(v):
        """
        Converte qualquer entrada (texto ou número) para float padrão Python.
        Compatível com Google Sheets configurado para Reino Unido/EUA.
        """
        if isinstance(v, (int, float)):
            return float(v)
        
        # Se for texto, remove símbolos de moeda e separadores de milhar (vírgula)
        s = str(v).replace("R$", "").replace("£", "").strip()
        s = s.replace(",", "") # Remove vírgula de milhar (Ex: 1,200.50 -> 1200.50)
        # O ponto (.) é mantido pois é o separador decimal correto
        try: 
            return float(s)
        except: 
            return 0.0

    # --- VISUALIZAÇÃO ---
    if not df_user.empty:
        c1, c2 = st.columns([2,1])
        with c1:
            df_user["dt"] = pd.to_datetime(df_user["data"], format="%d/%m/%Y", errors="coerce")
            df_user["mes"] = df_user["dt"].dt.strftime("%m/%Y")
            # Ordena meses
            meses = sorted(df_user["mes"].dropna().unique().tolist(), reverse=True)
            f_mes = st.selectbox("Mês", ["Todos"] + meses, key="fil_mes")
        
        df_f = df_user.copy()
        if f_mes != "Todos": df_f = df_f[df_f["mes"] == f_mes]
        
        if not df_f.empty:
            # Aplica normalização na coluna de valor para cálculos e exibição
            # Cria coluna 'v' (float puro) para contas
            df_f["v"] = df_f["valor"].apply(normalizar_valor)
            
            # Atualiza a coluna original 'valor' com o número limpo para exibir na tabela sem lixo de texto
            df_f["valor"] = df_f["v"] 

            st.metric("Total Gasto", formatar_real(df_f["v"].sum()))
            
            # Gráficos
            g1, g2 = st.columns([1, 2])
            with g1:
                cat_s = df_f.groupby("categoria")["v"].sum().reset_index().sort_values("v", ascending=False)
                # Paleta de cores suave
                colors = {"Alimentação": "#FFB3BA", "Transporte": "#FFDFBA", "Lazer": "#FFFFBA", "Casa": "#BAFFC9", "Saúde": "#BAE1FF", "Educação": "#E2C4FF", "Outros": "#D3D3D3"}
                def get_c(c): return colors.get(c, "#A0C4FF")
                
                base = alt.Chart(cat_s).encode(theta=alt.Theta("v", stack=True), color=alt.Color("categoria", scale=alt.Scale(domain=cat_s["categoria"].tolist(), range=[get_c(c) for c in cat_s["categoria"]]), legend=None), tooltip=["categoria", "v"])
                st.altair_chart(base.mark_arc(innerRadius=70, outerRadius=90), use_container_width=True)
            
            with g2:
                # Mostra tabela
                cols_view = [c for c in ["data", "item", "valor", "categoria", "forma_pagamento"] if c in df_f.columns]
                # Aqui usamos {:.2f} para forçar duas casas decimais (30.1 vira 30.10)
                st.dataframe(
                    df_f[cols_view].style.format({"valor": "R$ {:.2f}"}), 
                    use_container_width=True, 
                    hide_index=True
                )

            st.divider()

            # ==============================================================================
            # GERENCIAR LANÇAMENTOS (EDITAR/EXCLUIR)
            # ==============================================================================
            with st.expander("📝 Gerenciar Lançamentos", expanded=False):
                opcoes_despesas = {}
                for idx, r in df_f.iterrows():
                    item_id = str(r.get('id_despesa', ''))
                    if item_id:
                        # Usa formatar_real ou formatação direta
                        opcoes_despesas[item_id] = f"{r['data']} - {r['item']} (R$ {r['v']:.2f})"
                
                sel_id = st.selectbox("Selecione o gasto:", ["Selecione..."] + list(opcoes_despesas.keys()), format_func=lambda x: opcoes_despesas.get(x, "Selecione..."))

                c_v1, c_edit, c_del, c_v2 = st.columns(4)
                
                with c_edit:
                    if st.button("✏️ Editar", key="btn_edit_desp", use_container_width=True):
                        if sel_id != "Selecione...":
                            st.session_state['editando_desp_id'] = sel_id
                            st.rerun()
                        else: st.warning("Selecione um item.")

                with c_del:
                    with st.popover("🗑️ Excluir", use_container_width=True):
                        st.write("Confirma exclusão?")
                        if st.button("Sim, excluir", type="primary", key="btn_del_desp"):
                            if sel_id != "Selecione...":
                                try:
                                    df_nova = df_full[df_full['id_despesa'].astype(str) != sel_id]
                                    aba_reg.clear()
                                    # Atualiza mantendo compatibilidade
                                    aba_reg.update([df_nova.columns.values.tolist()] + df_nova.astype(str).values.tolist())
                                    st.success("Excluído!"); time.sleep(1); st.rerun()
                                except Exception as ex: st.error(f"Erro: {ex}")

                # --- FORMULÁRIO DE EDIÇÃO ---
                if st.session_state.get('editando_desp_id') == sel_id and sel_id != "Selecione...":
                    st.divider()
                    try:
                        item_dados = df_full[df_full['id_despesa'].astype(str) == sel_id].iloc[0]
                        st.markdown(f"**Editando:** {item_dados['item']}")
                        
                        with st.form("form_edit_despesa"):
                            ce1, ce2, ce3 = st.columns(3)
                            
                            with ce1:
                                en_item = st.text_input("Item", value=item_dados['item'])
                                try: d_obj = datetime.strptime(str(item_dados['data']), "%d/%m/%Y")
                                except: d_obj = datetime.now()
                                en_data = st.date_input("Data", value=d_obj, format="DD/MM/YYYY")
                            
                            with ce2:
                                # Usa a nova função normalizar_valor para preencher o campo corretamente
                                val_ini = normalizar_valor(item_dados['valor'])
                                en_valor = st.number_input("Valor", value=val_ini, step=10.0, format="%.2f")
                                
                                lista_cat = ["Alimentação", "Transporte", "Casa", "Lazer", "Saúde", "Educação", "Outros"]
                                cat_atual = item_dados.get('categoria', 'Outros')
                                idx_cat = lista_cat.index(cat_atual) if cat_atual in lista_cat else 6
                                en_cat = st.selectbox("Categoria", lista_cat, index=idx_cat)

                            with ce3:
                                lista_pgto = ["Crédito", "Débito", "Pix", "Dinheiro", "Outros"]
                                pgto_atual = item_dados.get('forma_pagamento', 'Outros')
                                idx_pgto = lista_pgto.index(pgto_atual) if pgto_atual in lista_pgto else 4
                                en_pgto = st.selectbox("Forma Pagto", lista_pgto, index=idx_pgto)
                            
                            c_btn1, c_save, c_canc, c_btn2 = st.columns(4)
                            with c_save: submit = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
                            with c_canc: cancel = st.form_submit_button("Cancelar", use_container_width=True)

                            if submit:
                                idx_geral = df_full[df_full['id_despesa'].astype(str) == sel_id].index[0]
                                df_full.at[idx_geral, 'item'] = en_item
                                df_full.at[idx_geral, 'data'] = en_data.strftime("%d/%m/%Y")
                                df_full.at[idx_geral, 'valor'] = en_valor # Salva como float puro
                                df_full.at[idx_geral, 'categoria'] = en_cat
                                df_full.at[idx_geral, 'forma_pagamento'] = en_pgto
                                
                                aba_reg.clear()
                                aba_reg.update([df_full.columns.values.tolist()] + df_full.astype(str).values.tolist())
                                
                                st.success("Salvo!")
                                st.session_state['editando_desp_id'] = None
                                time.sleep(1); st.rerun()
                            
                            if cancel:
                                st.session_state['editando_desp_id'] = None
                                st.rerun()

                    except Exception as e: st.error(f"Erro ao editar: {e}")

        else: st.info("Nenhuma despesa encontrada neste filtro.")
    else: st.info("Sem dados de despesas. Use o Bot do Telegram para lançar!")