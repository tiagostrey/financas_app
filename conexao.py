import os.path
import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# Escopos necessários
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

def conectar():
    creds = None
    # Verifica login salvo
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # Login novo se necessário
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                if os.path.exists("token.json"):
                    os.remove("token.json")
                return conectar() # Tenta de novo do zero
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Salva o token novo
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        # Conecta no GSpread
        client = gspread.authorize(creds)
        
        # Abre a planilha (Apenas abre, NÃO grava nada)
        planilha = client.open("Controle_Financeiro")
        return planilha

    except Exception as e:
        print(f"❌ ERRO de Conexão: {e}")
        return None

if __name__ == "__main__":
    # Teste rápido apenas se rodar este arquivo direto (manual)
    p = conectar()
    if p:
        print(f"✅ Conexão OK com a planilha: {p.title}")