import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ==================================================
# CONFIGURAÇÃO
# ==================================================
# Cole abaixo o ID da planilha da nova conta (dev.tiagostrey)
# Ele fica na URL: docs.google.com/spreadsheets/d/SEU_ID_AQUI/edit
SHEET_ID = "1A9p9on85dh8dNo3azWd5DyrIj_7KayzzKMnzQtoeJLs"

# Escopos de permissão obrigatórios
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def conectar():
    """
    Conecta ao Google Sheets usando Conta de Serviço (Robô).
    - Prioridade 1: Tenta ler st.secrets (Nuvem).
    - Prioridade 2: Tenta ler arquivo credentials.json (Local).
    - Conexão: Usa o ID da planilha para evitar erros de nomes duplicados.
    """
    creds = None
    
    # 1. TENTATIVA VIA SECRETS (NUVEM)
    # Envolvido em try/except genérico para não travar se rodar localmente sem .streamlit/secrets.toml
    try:
        # Só tenta acessar se o objeto secrets existir e tiver a chave
        # (O acesso direto a st.secrets fora do try causaria erro no PC)
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
    except Exception:
        # Se der qualquer erro (ex: secrets não encontrado), segue o baile
        pass

    # 2. TENTATIVA VIA ARQUIVO LOCAL (PC)
    # Se a etapa anterior falhou (creds continua None), tenta o arquivo físico
    if not creds:
        try:
            creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        except FileNotFoundError:
            print("⚠️ Erro Crítico: 'credentials.json' não encontrado e Secrets indisponíveis.")
            return None

    # 3. EFETUAR CONEXÃO
    try:
        client = gspread.authorize(creds)
        
        # Abre especificamente pelo ID (Mais seguro que pelo nome)
        if SHEET_ID == "COLE_SEU_ID_AQUI_DENTRO_DAS_ASPAS":
            print("⚠️ AVISO: Você esqueceu de configurar o ID da planilha no arquivo conexao.py!")
            return None
            
        planilha = client.open_by_key(SHEET_ID)
        return planilha

    except Exception as e:
        print(f"❌ Erro ao conectar na planilha: {e}")
        return None

if __name__ == "__main__":
    # Bloco de teste rápido (só roda se executar este arquivo direto)
    p = conectar()
    if p:
        print(f"✅ Conexão BEM SUCEDIDA com a planilha: {p.title}")