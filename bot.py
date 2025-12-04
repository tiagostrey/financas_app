import telebot
from conexao import conectar
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
# Cole seu TOKEN aqui (O mesmo que já estava funcionando)
TOKEN = "8468850047:AAHNhy7O9XzODin2biNV1DGeUrEBZw982OM"

bot = telebot.TeleBot(TOKEN)

# Listas de palavras-chave para a inteligência
CAT_MAP = {
    'alimentacao': 'Alimentação', 'alimentação': 'Alimentação', 'comida': 'Alimentação', 'mercado': 'Alimentação', 'lanche': 'Alimentação',
    'transporte': 'Transporte', 'uber': 'Transporte', 'gasolina': 'Transporte', 'combustivel': 'Transporte',
    'lazer': 'Lazer', 'cinema': 'Lazer',
    'casa': 'Casa', 'aluguel': 'Casa', 'luz': 'Casa', 'internet': 'Casa',
    'saude': 'Saúde', 'saúde': 'Saúde', 'farmacia': 'Saúde',
    'educacao': 'Educação', 'educação': 'Educação',
    'outros': 'Outros'
}

PGTO_MAP = {
    'credito': 'Crédito', 'crédito': 'Crédito', 'cc': 'Crédito',
    'debito': 'Débito', 'débito': 'Débito',
    'pix': 'Pix',
    'dinheiro': 'Dinheiro'
}

def normalizar_valor(valor_str):
    """
    Converte valores como:
    '76,05', '1.234,56', '100', '100,5'
    em float correto.
    """
    if not isinstance(valor_str, str):
        valor_str = str(valor_str)

    valor_str = valor_str.strip()

    # remove separadores de milhar
    valor_str = valor_str.replace(".", "")

    # troca vírgula decimal por ponto
    valor_str = valor_str.replace(",", ".")

    try:
        return float(valor_str)
    except:
        return None

# ==============================================================================
# FUNÇÕES DE GESTÃO DE USUÁRIO
# ==============================================================================

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
        
        # Acha a coluna telegram_id dinamicamente
        header = aba.row_values(1)
        try: col_idx = header.index("telegram_id") + 1
        except: return False, "Coluna telegram_id não existe na planilha."
            
        aba.update_cell(cell.row, col_idx, str(telegram_id))
        return True, f"Vínculo realizado! Agora você é **{nome_informado}**."
    except Exception as e:
        return False, f"Erro: {e}"

# ==============================================================================
# LÓGICA INTELIGENTE (SMART PARSER)
# ==============================================================================

def interpretar_mensagem(texto):
    """Separa Valor, Item, Categoria e Pagamento da frase."""
    partes = texto.split()
    
    valor = 0.0
    categoria = "Outros"
    pagamento = "Outros" # Padrão se não achar
    palavras_do_item = []

    for palavra in partes:
        p_lower = palavra.lower()
        
        # 1. Valor (tem números dentro da palavra?)
        if any(c.isdigit() for c in palavra) and valor == 0.0:
            clean_val = palavra.lower().replace("r$", "").replace("r", "").replace("$", "")

            valor_normalizado = normalizar_valor(clean_val)

            if valor_normalizado is not None:
                valor = valor_normalizado
                continue


        # 2. Categoria
        if p_lower in CAT_MAP:
            categoria = CAT_MAP[p_lower]
            continue

        # 3. Pagamento
        if p_lower in PGTO_MAP:
            pagamento = PGTO_MAP[p_lower]
            continue

        # 4. Resto é Item
        palavras_do_item.append(palavra)

    item_final = " ".join(palavras_do_item)
    if not item_final: item_final = "Gasto Geral"

    return item_final, valor, categoria, pagamento

# ==============================================================================
# HANDLERS (O CÉREBRO DO BOT)
# ==============================================================================

@bot.message_handler(func=lambda m: True)
def processar(message):
    chat_id = message.chat.id
    texto = message.text.strip()
    
    print(f"📩 Msg {chat_id}: {texto}")
    
    # 1. Verifica Usuário
    usuario = buscar_usuario_por_telegram(chat_id)
    
    # --- FLUXO DE CADASTRO (Se não conhece o usuário) ---
    if not usuario:
        # Se for /start ou uma frase longa (despesa), avisa e pede o nome
        # A lógica aqui é: Só tenta cadastrar se for uma palavra única (o login)
        if texto == "/start" or len(texto.split()) > 1 or any(c.isdigit() for c in texto):
            bot.reply_to(message, "⛔ É novo por aqui?\nPor favor, informe o nome de usuário cadastrado no App 'Controle Financeiro' para eu vincular a tua conta.")
            return
        
        # Se chegou aqui, é uma mensagem curta (provável tentativa de login)
        ok, msg = vincular_usuario(chat_id, texto)
        bot.reply_to(message, msg)
        return

    # --- FLUXO DE DESPESA (Se já conhece) ---
    item, valor, categoria, pgto = interpretar_mensagem(texto)
    
    if valor <= 0:
        bot.reply_to(message, "❌ Não entendi o valor.\nExemplo: `Padaria 20` ou `20 credito almoço`")
        return

    # Salva na Planilha (ORDEM CORRETA: 7 COLUNAS)
    try:
        p = conectar()
        # [Data, Item, Valor, Forma Pgto, Origem, Categoria, Usuario]
        p.worksheet("registros").append_row([
            datetime.now().strftime("%d/%m/%Y"),
            item,
            valor,
            pgto,
            "Telegram",
            categoria,
            usuario
        ])
        
        bot.reply_to(message, f"✅ **Lançado!**\nItem: {item}\nValor: R$ {valor:.2f}\nCat: {categoria}\nPgto: {pgto}")
        
    except Exception as e:
        bot.reply_to(message, f"Erro ao salvar: {e}")

print("🤖 Bot Inteligente Rodando...")
bot.infinity_polling()