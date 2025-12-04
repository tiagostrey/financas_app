import telebot
from conexao import conectar
import pandas as pd
from datetime import datetime
import uuid # Necessário para gerar o ID

# ==================================================
# CONFIGURAÇÕES
# ==================================================
TOKEN = "8468850047:AAHNhy7O9XzODin2biNV1DGeUrEBZw982OM"

bot = telebot.TeleBot(TOKEN)

# Listas de palavras-chave (Smart Parser)
CAT_MAP = {
    'alimentacao': 'Alimentação', 'alimentação': 'Alimentação', 'comida': 'Alimentação', 'mercado': 'Alimentação', 'lanche': 'Alimentação',
    'transporte': 'Transporte', 'uber': 'Transporte', 'gasolina': 'Transporte', 'combustivel': 'Transporte', '99': 'Transporte',
    'lazer': 'Lazer', 'cinema': 'Lazer', 'restaurante': 'Lazer',
    'casa': 'Casa', 'aluguel': 'Casa', 'luz': 'Casa', 'internet': 'Casa', 'condominio': 'Casa',
    'saude': 'Saúde', 'saúde': 'Saúde', 'farmacia': 'Saúde', 'medico': 'Saúde', 'remedio': 'Saúde',
    'educacao': 'Educação', 'educação': 'Educação', 'escola': 'Educação',
    'outros': 'Outros'
}

PGTO_MAP = {
    'credito': 'Crédito', 'crédito': 'Crédito', 'cc': 'Crédito',
    'debito': 'Débito', 'débito': 'Débito',
    'pix': 'Pix',
    'dinheiro': 'Dinheiro'
}

# ==================================================
# GESTÃO DE USUÁRIO
# ==================================================

def buscar_usuario_por_telegram(telegram_id):
    p = conectar()
    if not p: return None
    try:
        dados = p.worksheet("usuarios").get_all_records()
        for u in dados:
            if str(u.get('telegram_id', '')).strip() == str(telegram_id):
                return u['nome']
        return None
    except Exception as e:
        print(f"Erro busca: {e}")
        return None

def vincular_usuario(telegram_id, nome_informado):
    p = conectar()
    if not p: return False, "Erro de conexão."
    try:
        aba = p.worksheet("usuarios")
        cell = aba.find(nome_informado)
        if not cell: return False, f"Usuário '{nome_informado}' não encontrado."
        
        header = aba.row_values(1)
        try: col_idx = header.index("telegram_id") + 1
        except: return False, "Coluna telegram_id não existe."
            
        aba.update_cell(cell.row, col_idx, str(telegram_id))
        return True, f"Vínculo realizado! Agora você é **{nome_informado}**."
    except Exception as e:
        return False, f"Erro: {e}"

# ==================================================
# SMART PARSER
# ==================================================

def interpretar_mensagem(texto):
    partes = texto.split()
    valor = 0.0
    categoria = "Outros"
    pagamento = "Outros"
    palavras_item = []

    for palavra in partes:
        p_lower = palavra.lower()
        
        if any(c.isdigit() for c in palavra) and valor == 0.0:
            try:
                clean = palavra.lower().replace('r$', '').replace(',', '.')
                valor = float(clean)
                continue
            except: pass
        
        if p_lower in CAT_MAP:
            categoria = CAT_MAP[p_lower]
            continue
            
        if p_lower in PGTO_MAP:
            pagamento = PGTO_MAP[p_lower]
            continue
            
        palavras_item.append(palavra)
        
    return " ".join(palavras_item), valor, categoria, pagamento

# ==================================================
# HANDLERS
# ==================================================

@bot.message_handler(func=lambda m: True)
def processar(message):
    chat_id = message.chat.id
    texto = message.text.strip()
    
    print(f"📩 Msg {chat_id}: {texto}")
    
    usuario = buscar_usuario_por_telegram(chat_id)
    
    # --- CADASTRO ---
    if not usuario:
        if len(texto.split()) > 1 or any(c.isdigit() for c in texto):
            bot.reply_to(message, "⛔ É novo por aqui?\nPor favor, informe o nome de usuário cadastrado no App 'Controle Financeiro' para eu vincular a tua conta.")
            return
        
        ok, msg = vincular_usuario(chat_id, texto)
        bot.reply_to(message, msg)
        return

    # --- DESPESA ---
    item, valor, categoria, pgto = interpretar_mensagem(texto)
    
    if valor <= 0:
        bot.reply_to(message, "❌ Valor não identificado.")
        return

    try:
        p = conectar()
        # Gera ID único para essa despesa
        novo_id = str(uuid.uuid4())
        
        # Grava 8 Colunas (A=ID, B=Data, etc...)
        p.worksheet("registros").append_row([
            novo_id,                             # A: ID
            datetime.now().strftime("%d/%m/%Y"), # B: Data
            item,                                # C: Item
            valor,                               # D: Valor
            pgto,                                # E: Pagto
            "Bot Telegram",                      # F: Origem
            categoria,                           # G: Categoria
            usuario                              # H: Usuario
        ])
        bot.reply_to(message, f"✅ **Lançado!**\nItem: {item}\nValor: R$ {valor:.2f}\nCat: {categoria}\nPgto: {pgto}")
    except Exception as e:
        bot.reply_to(message, f"Erro ao salvar: {e}")

print("🤖 Bot com ID Rodando...")
bot.infinity_polling()