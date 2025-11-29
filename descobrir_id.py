import requests
import time
from segredos import TELEGRAM_TOKEN

def pegar_atualizacoes():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        resposta = requests.get(url)
        return resposta.json()
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return None

print("🤖 O Espião de ID está rodando...")
print("1. Certifique-se que você clicou em COMEÇAR no seu bot.")
print("2. Mande um 'Oi' para ele agora.")
print("3. Aguardando...\n")

ultimo_id = 0

while True:
    dados = pegar_atualizacoes()
    
    if dados and "result" in dados:
        for mensagem in dados["result"]:
            update_id = mensagem["update_id"]
            
            if update_id > ultimo_id:
                try:
                    # Tenta pegar dados da mensagem
                    chat_id = mensagem["message"]["chat"]["id"]
                    nome = mensagem["message"]["chat"].get("first_name", "Usuário")
                    texto = mensagem["message"].get("text", "(Sem texto)")
                    
                    print(f"--------------------------------------------------")
                    print(f"👤 Nome encontrado: {nome}")
                    print(f"🔑 SEU ID É: {chat_id}")
                    print(f"--------------------------------------------------")
                    print("Copie o número acima e cole na coluna 'telegram_id' da sua planilha!")
                    
                    ultimo_id = update_id
                except KeyError:
                    pass
    
    time.sleep(2)