import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import re
from segredos import TELEGRAM_TOKEN
from conexao import conectar

# 1. Iniciar o Bot
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# 2. Memória Temporária
memoria_temporaria = {}

# 3. Categorias
CATEGORIAS = ["Alimentação", "Transporte", "Lazer", "Casa", "Saúde", "Outros"]

def obter_usuarios_permitidos():
    """Busca usuários autorizados na planilha"""
    planilha = conectar()
    if planilha:
        aba_usuarios = planilha.worksheet("usuarios")
        dados = aba_usuarios.get_all_records()
        ids = [int(u['telegram_id']) for u in dados if str(u['telegram_id']).strip()]
        return ids, planilha
    return [], None

def analisar_mensagem(texto):
    """O DETETIVE: Separa Valor, Data, Pagamento e Item"""
    # A. Valor
    match_valor = re.search(r'\b\d+[,.]?\d*\b', texto)
    if match_valor:
        valor_str = match_valor.group().replace(',', '.')
        valor = float(valor_str)
        texto = texto.replace(match_valor.group(), "", 1).strip()
    else:
        return None

    # B. Pagamento
    mapa_pagamentos = {
        "credito": "Crédito", "crédito": "Crédito", "cred": "Crédito", "cc": "Crédito",
        "debito": "Débito", "débito": "Débito", "deb": "Débito",
        "pix": "Pix",
        "dinheiro": "Dinheiro", "cash": "Dinheiro",
        "boleto": "Boleto"
    }
    forma_pagamento = "Carteira/Outros"
    palavras = texto.split()
    novas_palavras = []
    for palavra in palavras:
        p_limpa = palavra.lower().strip(".,")
        if p_limpa in mapa_pagamentos:
            forma_pagamento = mapa_pagamentos[p_limpa]
        else:
            novas_palavras.append(palavra)
    texto = " ".join(novas_palavras)

    # C. Data
    data_hoje = datetime.now()
    data_formatada = data_hoje.strftime("%d/%m/%Y")
    if "ontem" in texto.lower():
        data_ontem = data_hoje - timedelta(days=1)
        data_formatada = data_ontem.strftime("%d/%m/%Y")
        texto = re.sub(r'\bontem\b', '', texto, flags=re.IGNORECASE).strip()
    elif "anteontem" in texto.lower():
        data_ante = data_hoje - timedelta(days=2)
        data_formatada = data_ante.strftime("%d/%m/%Y")
        texto = re.sub(r'\banteontem\b', '', texto, flags=re.IGNORECASE).strip()
    
    # D. Item
    item = texto.strip().capitalize()
    if not item: item = "Despesa Diversa"

    return {"valor": valor, "item": item, "data": data_formatada, "pagamento": forma_pagamento}

# --- COMANDO DESFAZER (NOVIDADE) ---

@bot.message_handler(commands=['desfazer'])
def comando_desfazer(message):
    chat_id = message.chat.id
    nome_usuario = message.from_user.first_name
    
    # Verifica permissão
    ids, planilha = obter_usuarios_permitidos()
    if chat_id not in ids: return

    try:
        aba = planilha.worksheet("registros")
        todas_linhas = aba.get_all_values()
        
        # Se só tem o cabeçalho (linha 1), não tem o que apagar
        if len(todas_linhas) <= 1:
            bot.reply_to(message, "📭 A planilha já está vazia.")
            return

        # Pega a última linha
        ultima_linha = todas_linhas[-1]
        numero_da_linha = len(todas_linhas)
        
        # Estrutura da planilha: 
        # A:data, B:item, C:valor, D:pagto, E:origem, F:cat, G:usuario
        # O índice 6 é a Coluna G (Usuário)
        dono_do_registro = ultima_linha[6]
        item_apagado = ultima_linha[1]
        valor_apagado = ultima_linha[2]

        # Verifica se foi você mesmo
        # (Comparação simples de nome. Idealmente usaríamos ID, mas na planilha está o nome)
        if dono_do_registro == nome_usuario:
            aba.delete_rows(numero_da_linha)
            bot.reply_to(message, f"🗑️ **Apagado:** {item_apagado} (R$ {valor_apagado})\nPode enviar novamente.")
        else:
            bot.reply_to(message, f"⛔ **Não posso apagar.**\nO último registro é de *{dono_do_registro}*, não seu.")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao desfazer: {e}")

# --- OUVINTE DE MENSAGENS ---

@bot.message_handler(func=lambda message: True)
def receber_mensagem(message):
    chat_id = message.chat.id
    ids_permitidos, planilha = obter_usuarios_permitidos()
    
    if chat_id not in ids_permitidos:
        bot.reply_to(message, f"⛔ Acesso Negado (ID: {chat_id})")
        return

    dados = analisar_mensagem(message.text)
    if not dados:
        bot.reply_to(message, "🤷‍♂️ Não entendi o valor. Tente: 'Mercado 50'")
        return

    memoria_temporaria[chat_id] = dados
    
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    botoes = [InlineKeyboardButton(cat, callback_data=cat) for cat in CATEGORIAS]
    markup.add(*botoes)
    
    resumo = (f"📝 **Confirmação:**\n\n🛒 {dados['item']}\n💰 R$ {dados['valor']:.2f}\n"
              f"💳 {dados['pagamento']}\n📅 {dados['data']}\n\n**Categoria:**")
    bot.reply_to(message, resumo, reply_markup=markup, parse_mode="Markdown")

# --- OUVINTE DOS BOTÕES ---

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    chat_id = call.message.chat.id
    categoria = call.data
    
    if chat_id in memoria_temporaria:
        dados = memoria_temporaria[chat_id]
        try:
            planilha = conectar()
            aba = planilha.worksheet("registros")
            nova_linha = [
                dados['data'], dados['item'], dados['valor'], dados['pagamento'],
                "Telegram", categoria, call.from_user.first_name
            ]
            aba.append_row(nova_linha)
            
            # Resposta com dica do comando desfazer
            bot.edit_message_text(
                f"✅ **Salvo!**\n{dados['item']} (R$ {dados['valor']:.2f})\n\n_Errou? Use /desfazer_", 
                chat_id, call.message.message_id, parse_mode="Markdown"
            )
            del memoria_temporaria[chat_id]
        except Exception as e:
            bot.send_message(chat_id, f"❌ Erro: {e}")
    else:
        bot.send_message(chat_id, "⚠️ Expirou.")

print("🤖 Bot Financeiro V2.1 (Com Undo) Iniciado!")
bot.infinity_polling()