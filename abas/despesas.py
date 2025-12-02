import streamlit as st
import pandas as pd
import altair as alt
from conexao import conectar
from utils import formatar_real

def render():
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
                
                base = alt.Chart(cat_s).encode(theta=alt.Theta("v", stack=True), color=alt.Color("categoria", scale=alt.Scale(domain=cat_s["categoria"].tolist(), range=[get_c(c) for c in cat_s["categoria"]]), legend=None), tooltip=["categoria", "v"])
                st.altair_chart(base.mark_arc(innerRadius=70, outerRadius=90), use_container_width=True)
                for _, r in cat_s.iterrows(): st.markdown(f"<div style='display: flex; align-items: center; margin-bottom: 5px;'><span style='height: 12px; width: 12px; background-color: {get_c(r['categoria'])}; border-radius: 50%; display: inline-block; margin-right: 8px;'></span><span style='font-size: 14px;'><b>{r['categoria']}:</b> {formatar_real(r['v'])}</span></div>", unsafe_allow_html=True)
            
            with g2:
                cols = [c for c in ["data", "item", "valor", "categoria", "forma_pagamento"] if c in df_f.columns]
                st.dataframe(df_f[cols].style.format({"valor": "R$ {}"}), use_container_width=True, hide_index=True)
        else: st.info("Sem dados.")