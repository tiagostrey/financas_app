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
    # Alimentação
    'alimentacao': 'Alimentação', 'alimentação': 'Alimentação',
    'comida': 'Alimentação', 'mercado': 'Alimentação', 'mercadinho': 'Alimentação',
    'lanche': 'Alimentação', 'lancheria': 'Alimentação',
    'xis': 'Alimentação',
    'pizza': 'Alimentação', 'pizzaria': 'Alimentação',
    'churrasco': 'Alimentação', 'churras': 'Alimentação',
    'bebida': 'Alimentação', 'refri': 'Alimentação', 'refrigerante': 'Alimentação',
    'doce': 'Alimentação', 'salgado': 'Alimentação', 'salgadinho': 'Alimentação',

    # Transporte
    'transporte': 'Transporte', 'uber': 'Transporte', 'gasolina': 'Transporte',
    'combustivel': 'Transporte', 'combustível': 'Transporte',
    'onibus': 'Transporte', 'ônibus': 'Transporte',

    # Saúde
    'saude': 'Saúde', 'saúde': 'Saúde', 'farmacia': 'Saúde', 'farmácia': 'Saúde',
    'medico': 'Saúde', 'médico': 'Saúde',
    'dentista': 'Saúde',

    # Casa
    'casa': 'Casa', 'aluguel': 'Casa', 'aluguel': 'Casa',
    'luz': 'Casa', 'energia': 'Casa',
    'agua': 'Casa', 'água': 'Casa',
    'internet': 'Casa',
    'condominio': 'Casa', 'condomínio': 'Casa',
    'limpeza': 'Casa',

    # Lazer
    'lazer': 'Lazer', 'cinema': 'Lazer', 'show': 'Lazer', 'bar': 'Lazer',
    'parque': 'Lazer',

    # Educação
    'educacao': 'Educação', 'educação': 'Educação',
    'curso': 'Educação', 'faculdade': 'Educação', 'livro': 'Educação',

    # Tecnologia (Nova)
    'celular': 'Tecnologia', 'iphone': 'Tecnologia', 'android': 'Tecnologia',
    'notebook': 'Tecnologia', 'laptop': 'Tecnologia',
    'fone': 'Tecnologia', 'fonebluetooth': 'Tecnologia', 'fones': 'Tecnologia',
    'mouse': 'Tecnologia', 'teclado': 'Tecnologia',
    'carregador': 'Tecnologia', 'cabo': 'Tecnologia', 'adaptador': 'Tecnologia',

    # Outros
    'outros': 'Outros', 'diverso': 'Outros'
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
    partes = texto.split()
    
    valor = 0.0
    categoria_detectada = None
    pagamento = "Outros"
    palavras_do_item = []

    for palavra in partes:
        p_lower = palavra.lower()

        # 1. Valor
        if any(c.isdigit() for c in palavra) and valor == 0.0:
            val = normalizar_valor(palavra)
            if val is not None:
                valor = val
                continue

        # 2. Categoria (mapeamento inteligente)
        if p_lower in CAT_MAP:
            if categoria_detectada is None:
                categoria_detectada = CAT_MAP[p_lower]
            # Mesmo sendo categoria, faz parte do item
            palavras_do_item.append(palavra)
            continue

        # 3. Forma de Pagamento
        if p_lower in PGTO_MAP:
            pagamento = PGTO_MAP[p_lower]
            continue

        # 4. Resto vira o item
        palavras_do_item.append(palavra)

    item_final = " ".join(palavras_do_item).strip()
    if not item_final:
        item_final = "Gasto Geral"

    if categoria_detectada is None:
        categoria_detectada = "Outros"

    return item_final, valor, categoria_detectada, pagamento

# ==============================================================================
# HANDLERS (O CÉREBRO DO BOT)
# ==============================================================================

@bot.message_handler(commands=['desfazer'])
def desfazer(message):
    chat_id = message.chat.id
    usuario = buscar_usuario_por_telegram(chat_id)

    if not usuario:
        bot.reply_to(message, "❗ Não encontrei seu cadastro. Envie seu nome de usuário primeiro.")
        return

    try:
        p = conectar()
        aba = p.worksheet("registros")
        linhas = aba.get_all_values()

        # Se só tem cabeçalho → nada a apagar
        if len(linhas) <= 1:
            bot.reply_to(message, "A planilha está vazia.")
            return

        ultima_linha = linhas[-1]   # Última linha com dados
        num_linha = len(linhas)    # Número real da linha
        usuario_ultimo = ultima_linha[6]  # Coluna G

        if usuario_ultimo != usuario:
            bot.reply_to(message, f"⛔ Não foi possível excluir o seu último registro. Por favor, utilize o app.")
            return

        item = ultima_linha[1]
        valor = ultima_linha[2]

        # Apaga a linha (SEM deixar buracos!)
        aba.delete_rows(num_linha)

        bot.reply_to(
            message,
            f"🗑️ Registro apagado!\nItem: **{item}**\nValor: **R$ {valor}**"
        )

    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao apagar: {e}")

# COMANDOS /start E /ajuda
@bot.message_handler(commands=['start'])
def iniciar(message):
    bot.reply_to(
        message,
        "👋 *Bem-vindo ao Controle Financeiro!*\n\n"
        "Envie mensagens como:\n"
        "• `mercado 50`\n"
        "• `uber 20 crédito`\n"
        "• `pizza 40`\n\n"
        "O bot identifica automaticamente o *item*, *valor*, *categoria* e *forma de pagamento*.\n\n"
        "Se for seu primeiro acesso, informe o seu *nome de usuário* cadastrado no App.\n\n"
        "Use `/ajuda` para ver mais comandos.",
        parse_mode="Markdown"
    )


@bot.message_handler(commands=['help', 'ajuda'])
def ajuda(message):
    bot.reply_to(
        message,
        "📘 *Comandos disponíveis:*\n\n"
        "• `/desfazer` — Remove o *último lançamento* registrado na planilha, "
        "desde que ele tenha sido feito por você *e* seja realmente o último da lista.\n\n"
        "• Para registrar despesas, basta enviar frases como:\n"
        "  `mercado 50`, `uber 20 crédito`, `pizza 40`, `gasolina 100 debito`.\n\n"
        "• O bot identifica automaticamente o valor, categoria, item e forma de pagamento.\n\n"
        "• Se estiver usando o bot pela primeira vez, informe seu *nome de usuário* cadastrado no app.\n\n"
        "❤️ Obrigado por usar o Controle Financeiro!",
        parse_mode="Markdown"
    )

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
        
        bot.reply_to(
            message,
            f"✅ **Lançado!**\n"
            f"Item: {item}\n"
            f"Valor: R$ {valor:.2f}\n"
            f"Categoria: {categoria}\n"
            f"Pagamento: {pgto}\n\n"
            f"↩️ Não está certo? Envie /desfazer."
        )
        
    except Exception as e:
        bot.reply_to(message, f"Erro ao salvar: {e}")

print("🤖 Bot Inteligente Rodando...")
bot.infinity_polling()
