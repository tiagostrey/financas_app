import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Escopos necessários para acessar planilhas e drive
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def conectar():
    """
    Conecta ao Google Sheets usando Conta de Serviço (Robô).
    - Prioridade 1: Lê do st.secrets (Nuvem)
    - Prioridade 2: Lê do arquivo credentials.json (Local)
    """
    creds = None
    
    # 1. TENTATIVA VIA SECRETS (Para o Streamlit Cloud)
    # Verifica se existe a seção [gcp_service_account] nos segredos
    if "gcp_service_account" in st.secrets:
        try:
            # Cria credenciais a partir do dicionário dos secrets
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
        except Exception as e:
            st.error(f"Erro ao ler Secrets da nuvem: {e}")
            return None

    # 2. TENTATIVA VIA ARQUIVO LOCAL (Para seu computador)
    else:
        try:
            # Tenta ler o arquivo físico
            creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        except FileNotFoundError:
            st.error("⚠️ Erro de Autenticação: Arquivo 'credentials.json' não encontrado e Secrets não configurados.")
            return None

    # 3. CONEXÃO FINAL
    try:
        client = gspread.authorize(creds)
        # Abre a planilha pelo nome exato
        planilha = client.open("Controle_Financeiro")
        return planilha
    except Exception as e:
        st.error(f"❌ Erro ao abrir planilha: {e}")
        return None

if __name__ == "__main__":
    # Teste rápido se rodar este arquivo direto
    p = conectar()
    if p:
        print(f"✅ Conexão OK com a planilha: {p.title}")