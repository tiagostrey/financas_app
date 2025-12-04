import telebot
from conexao import conectar
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
TOKEN = "8468850047:AAHNhy7O9XzODin2biNV1DGeUrEBZw982OM" 

bot = telebot.TeleBot(TOKEN)

# Listas de palavras-chave para inteligência
CAT_MAP = {
    'alimentacao': 'Alimentação', 'alimentação': 'Alimentação', 'comida': 'Alimentação', 'mercado': 'Alimentação',
    'transporte': 'Transporte', 'uber': 'Transporte', 'gasolina': 'Transporte', 'combustivel': 'Transporte',
    'lazer': 'Lazer', 'cinema': 'Lazer', 'restaurante': 'Lazer',
    'casa': 'Casa', 'aluguel': 'Casa', 'internet': 'Casa', 'luz': 'Casa',
    'saude': 'Saúde', 'saúde': 'Saúde', 'farmacia': 'Saúde', 'medico': 'Saúde',
    'educacao': 'Educação', 'educação': 'Educação', 'escola': 'Educação',
    'outros': 'Outros'
}

PGTO_MAP = {
    'credito': 'Crédito', 'crédito': 'Crédito', 'cc': 'Crédito',
    'debito': 'Débito', 'débito': 'Débito',
    'pix': 'Pix',
    'dinheiro': 'Dinheiro'
}

# ==============================================================================
# FUNÇÕES DE GESTÃO DE USUÁRIO
# ==============================================================================

def buscar_usuario_por_telegram(telegram_id):
    p = conectar()
    if not p: return None
    try:
        # Busca usuário na aba 'usuarios'
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
        if not cell: return False, "Usuário não encontrado."
        
        # Acha a coluna telegram_id dinamicamente
        header = aba.row_values(1)
        try: col_idx = header.index("telegram_id") + 1
        except: return False, "Coluna telegram_id não existe."
            
        aba.update_cell(cell.row, col_idx, str(telegram_id))
        return True, f"Vínculo feito com **{nome_informado}**!"
    except Exception as e:
        return False, f"Erro: {e}"

# ==============================================================================
# LÓGICA INTELIGENTE
# ==============================================================================

def interpretar_mensagem(texto):
    """
    Separa o texto em Valor, Item, Categoria e Pagamento.
    """
    partes = texto.split()
    
    valor = 0.0
    categoria = "Outros"
    pagamento = "Outros" # Padrão se não achar
    palavras_do_item = []

    for palavra in partes:
        p_lower = palavra.lower()
        
        # 1. Tenta achar Valor (tem numero?)
        if any(c.isdigit() for c in palavra) and valor == 0.0:
            try:
                # Trata R$ e virgulas
                clean_val = palavra.lower().replace('r$', '').replace(',', '.')
                valor = float(clean_val)
                continue # Já achamos o valor, pula pro proximo
            except:
                pass # Se falhar, talvez seja nome de item com numero (ex: 99taxi)

        # 2. Tenta achar Categoria (está na lista?)
        if p_lower in CAT_MAP:
            categoria = CAT_MAP[p_lower]
            continue

        # 3. Tenta achar Pagamento (está na lista?)
        if p_lower in PGTO_MAP:
            pagamento = PGTO_MAP[p_lower]
            continue

        # 4. Se não for nada disso, é parte do Nome do Item
        palavras_do_item.append(palavra)

    item_final = " ".join(palavras_do_item)
    if not item_final: item_final = "Gasto Geral" # Se sobrar nada

    return item_final, valor, categoria, pagamento

# ==============================================================================
# HANDLERS
# ==============================================================================

@bot.message_handler(func=lambda m: True)
def processar(message):
    chat_id = message.chat.id
    texto = message.text.strip()
    
    print(f"📩 Msg de {chat_id}: {texto}")
    
    # 1. Verifica Usuário
    usuario = buscar_usuario_por_telegram(chat_id)
    
    if not usuario:
        if texto == "/start":
            bot.reply_to(message, "👋 Olá! Responda com seu **Usuário do App** para vincular.")
            return
        ok, msg = vincular_usuario(chat_id, texto)
        bot.reply_to(message, msg)
        return

    # 2. Processa Gasto (Com Inteligência)
    item, valor, categoria, pgto = interpretar_mensagem(texto)
    
    if valor <= 0:
        bot.reply_to(message, "❌ Não encontrei um valor válido.\nEx: `Padaria 20` ou `20 credito almoço`")
        return

    # 3. Salva na Planilha (ORDEM CORRETA: A->G)
    try:
        p = conectar()
        # [Data, Item, Valor, Forma_Pgto, Origem, Categoria, Usuario]
        p.worksheet("registros").append_row([
            datetime.now().strftime("%d/%m/%Y"), # A: Data
            item,                                # B: Item (Limpo)
            valor,                               # C: Valor
            pgto,                                # D: Forma Pgto (Detectada)
            "Telegram",                          # E: Origem (Fixo)
            categoria,                           # F: Categoria (Detectada)
            usuario                              # G: Usuario (Do vínculo)
        ])
        
        bot.reply_to(message, f"✅ **Lançado!**\nItem: {item}\nValor: R$ {valor:.2f}\nCat: {categoria}\nPgto: {pgto}")
        
    except Exception as e:
        bot.reply_to(message, f"Erro ao salvar: {e}")

print("🤖 Bot Inteligente Rodando...")
bot.infinity_polling()