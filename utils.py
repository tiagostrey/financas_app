import pandas as pd
from datetime import datetime
from conexao import conectar
import streamlit as st

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