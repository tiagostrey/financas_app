import streamlit as st
import pandas as pd
import altair as alt
from conexao import conectar
from utils import formatar_real
import time
from datetime import datetime
import uuid

def render():
    c1, c2 = st.columns([3,1])
    with c1: st.subheader("💸 Extrato de Despesas")
    with c2: 
        if st.button("🔄 Atualizar", key="btn_ext_up"): st.cache_data.clear(); st.rerun()
    
    # ==============================================================================
    # 0. CARGA DE DADOS E FUNÇÕES
    # ==============================================================================
    df_full = pd.DataFrame()
    df_user = pd.DataFrame()
    df_f = pd.DataFrame()
    
    def normalizar_valor(v):
        if isinstance(v, (int, float)): return float(v)
        s = str(v).replace("R$", "").replace("£", "").strip()
        s = s.replace(",", "") 
        try: return float(s)
        except: return 0.0

    try:
        p = conectar()
        if p:
            aba_reg = p.worksheet("registros")
            dados = aba_reg.get_all_records()
            df_full = pd.DataFrame(dados)
            if not df_full.empty and "usuario" in df_full.columns:
                df_user = df_full[df_full["usuario"].astype(str).str.lower() == st.session_state['usuario_atual'].lower()].copy()
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")

    # ==============================================================================
    # 1. DADOS LANÇADOS (Visualização)
    # ==============================================================================
    if not df_user.empty:
        df_user["dt"] = pd.to_datetime(df_user["data"], format="%d/%m/%Y", errors="coerce")
        df_user["mes"] = df_user["dt"].dt.strftime("%m/%Y")
        meses = sorted(df_user["mes"].dropna().unique().tolist(), reverse=True)
        
        c_filtro, c_vazio = st.columns([1, 2])
        with c_filtro:
            f_mes = st.selectbox("Mês", ["Todos"] + meses, key="fil_mes")
        
        df_f = df_user.copy()
        if f_mes != "Todos": df_f = df_f[df_f["mes"] == f_mes]
        
        if not df_f.empty:
            df_f["v"] = df_f["valor"].apply(normalizar_valor)
            df_f["valor"] = df_f["v"] 

            st.metric("Total Gasto", formatar_real(df_f["v"].sum()))
            
            g1, g2 = st.columns([1, 2])
            with g1:
                cat_s = df_f.groupby("categoria")["v"].sum().reset_index().sort_values("v", ascending=False)
                colors = {"Alimentação": "#FFB3BA", "Transporte": "#FFDFBA", "Lazer": "#FFFFBA", "Casa": "#BAFFC9", "Saúde": "#BAE1FF", "Educação": "#E2C4FF", "Outros": "#D3D3D3"}
                def get_c(c): return colors.get(c, "#A0C4FF")
                
                base = alt.Chart(cat_s).encode(theta=alt.Theta("v", stack=True), color=alt.Color("categoria", scale=alt.Scale(domain=cat_s["categoria"].tolist(), range=[get_c(c) for c in cat_s["categoria"]]), legend=None), tooltip=["categoria", "v"])
                st.altair_chart(base.mark_arc(innerRadius=70, outerRadius=90), use_container_width=True)
            
            with g2:
                cols_view = [c for c in ["data", "item", "valor", "categoria", "forma_pagamento"] if c in df_f.columns]
                st.dataframe(
                    df_f[cols_view].style.format({"valor": "R$ {:.2f}"}), 
                    use_container_width=True, 
                    hide_index=True
                )
        else:
            st.info("Nenhum dado neste mês.")
    else:
        st.info("Sem dados de despesas ainda.")

    st.divider()

    # ==============================================================================
    # 2. LANÇAR NOVO (Formulário Manual)
    # ==============================================================================
    with st.expander("➕ Nova Despesa (Manual)", expanded=False):
        with st.form("form_nova_despesa_app"):
            c_input1, c_input2, c_input3 = st.columns(3)
            with c_input1:
                novo_item = st.text_input("Descrição", placeholder="Ex: Mercado")
                nova_data = st.date_input("Data", value=datetime.now(), format="DD/MM/YYYY")
            with c_input2:
                novo_valor = st.number_input("Valor (R$)", min_value=0.0, step=10.0, format="%.2f")
                nova_cat = st.selectbox("Categoria", ["Alimentação", "Transporte", "Casa", "Lazer", "Saúde", "Educação", "Outros"])
            with c_input3:
                novo_pgto = st.selectbox("Forma Pagto", ["Crédito", "Débito", "Pix", "Dinheiro", "Outros"])
            
            if st.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                if novo_item and novo_valor > 0:
                    try:
                        p = conectar()
                        if p:
                            aba = p.worksheet("registros")
                            novo_id = str(uuid.uuid4())
                            nova_linha = [
                                novo_id,
                                nova_data.strftime("%d/%m/%Y"),
                                novo_item,
                                novo_valor,
                                novo_pgto,
                                "Web App",
                                nova_cat,
                                st.session_state.get('usuario_atual', 'Desconhecido')
                            ]
                            aba.append_row(nova_linha)
                            st.success("Salvo!"); time.sleep(1); st.cache_data.clear(); st.rerun()
                    except Exception as e: st.error(f"Erro: {e}")
                else: st.warning("Preencha item e valor.")

    # ==============================================================================
    # 3. GERENCIAR LANÇAMENTOS (Editar/Excluir)
    # ==============================================================================
    if not df_f.empty:
        with st.expander("📝 Gerenciar Lançamentos (Editar / Excluir)", expanded=False):
            opcoes_despesas = {}
            for idx, r in df_f.iterrows():
                item_id = str(r.get('id_despesa', ''))
                if item_id:
                    opcoes_despesas[item_id] = f"{r['data']} - {r['item']} (R$ {r['v']:.2f})"
            
            sel_id = st.selectbox("Selecione o gasto:", ["Selecione..."] + list(opcoes_despesas.keys()), format_func=lambda x: opcoes_despesas.get(x, "Selecione..."))

            c_v1, c_edit, c_del, c_v2 = st.columns(4)
            
            with c_edit:
                if st.button("✏️ Editar", key="btn_edit_desp", use_container_width=True):
                    if sel_id != "Selecione...":
                        st.session_state['editando_desp_id'] = sel_id
                        st.rerun()

            with c_del:
                with st.popover("🗑️ Excluir", use_container_width=True):
                    st.write("Confirma?")
                    if st.button("Sim, excluir", type="primary", key="btn_del_desp"):
                        if sel_id != "Selecione...":
                            try:
                                df_nova = df_full[df_full['id_despesa'].astype(str) != sel_id]
                                p = conectar(); aba_reg = p.worksheet("registros")
                                aba_reg.clear()
                                aba_reg.update([df_nova.columns.values.tolist()] + df_nova.astype(str).values.tolist())
                                st.success("Excluído!"); time.sleep(1); st.rerun()
                            except Exception as ex: st.error(f"Erro: {ex}")

            # --- FORMULÁRIO DE EDIÇÃO ---
            if st.session_state.get('editando_desp_id') == sel_id and sel_id != "Selecione...":
                st.divider()
                try:
                    item_dados = df_full[df_full['id_despesa'].astype(str) == sel_id].iloc[0]
                    with st.form("form_edit_despesa"):
                        ce1, ce2, ce3 = st.columns(3)
                        with ce1:
                            en_item = st.text_input("Item", value=item_dados['item'])
                            try: d_obj = datetime.strptime(str(item_dados['data']), "%d/%m/%Y")
                            except: d_obj = datetime.now()
                            en_data = st.date_input("Data", value=d_obj, format="DD/MM/YYYY")
                        with ce2:
                            val_ini = normalizar_valor(item_dados['valor'])
                            en_valor = st.number_input("Valor", value=val_ini, step=10.0, format="%.2f")
                            lista_cat = ["Alimentação", "Transporte", "Casa", "Lazer", "Saúde", "Educação", "Outros"]
                            cat_atual = item_dados.get('categoria', 'Outros')
                            en_cat = st.selectbox("Categoria", lista_cat, index=lista_cat.index(cat_atual) if cat_atual in lista_cat else 6)
                        with ce3:
                            lista_pgto = ["Crédito", "Débito", "Pix", "Dinheiro", "Outros"]
                            pgto_atual = item_dados.get('forma_pagamento', 'Outros')
                            en_pgto = st.selectbox("Pagto", lista_pgto, index=lista_pgto.index(pgto_atual) if pgto_atual in lista_pgto else 4)
                        
                        st.divider()
                        
                        c_vazia1, c_salvar, c_cancelar, c_vazia2 = st.columns(4)
                        
                        with c_salvar: 
                            if st.form_submit_button("💾 Salvar", type="primary", use_container_width=True):
                                idx_geral = df_full[df_full['id_despesa'].astype(str) == sel_id].index[0]
                                df_full.at[idx_geral, 'item'] = en_item
                                df_full.at[idx_geral, 'data'] = en_data.strftime("%d/%m/%Y")
                                df_full.at[idx_geral, 'valor'] = en_valor
                                df_full.at[idx_geral, 'categoria'] = en_cat
                                df_full.at[idx_geral, 'forma_pagamento'] = en_pgto
                                p = conectar(); aba_reg = p.worksheet("registros")
                                aba_reg.clear()
                                aba_reg.update([df_full.columns.values.tolist()] + df_full.astype(str).values.tolist())
                                st.session_state['editando_desp_id'] = None
                                st.success("Salvo!"); time.sleep(1); st.rerun()
                        
                        with c_cancelar: 
                            if st.form_submit_button("Cancelar", use_container_width=True):
                                st.session_state['editando_desp_id'] = None; st.rerun()

                except Exception as e: st.error(f"Erro edição: {e}")

    # ==============================================================================
    # 4. TUTORIAL: COMO USAR O BOT (Rodapé Atualizado v0.08)
    # ==============================================================================
    with st.expander("🤖 Como ativar e usar o Bot do Telegram"):
        c_texto, c_info = st.columns([2, 1])
        
        with c_texto:
            st.markdown("""
            **Passo 1 - Inicie a conversa:** Clique no link ao lado para abrir o **Controle Financeiro Bot** no Telegram e envie um **"Oi"**.
            
            **Passo 2 - Identifique-se:** O Bot vai avisar que não te conhece e pedirá seu nome de usuário.
            
            **Passo 3 - Digite seu usuário:** Responda para o bot exatamente o nome que aparece na caixa azul ao lado (copie e cole para garantir).
            
            **Passo 4 - Pronto!** O Bot confirmará o vínculo. A partir daí, é só mandar os gastos (ex: `50 padaria crédito`).
            """)

        with c_info:
            usuario_logado = st.session_state.get('usuario_atual', 'Desconhecido')
            
            # Voltamos ao padrão st.info (Nativo)
            st.info(f"👤 Seu usuário é:\n\n**{usuario_logado}**")
            
            # Link oficial do novo bot
            st.link_button("💬 Abrir Bot no Telegram", "https://t.me/GranaSegura_Bot", use_container_width=True)