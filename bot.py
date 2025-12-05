import telebot
from conexao import conectar
import pandas as pd
from datetime import datetime
import uuid
import time
from segredos import TELEGRAM_TOKEN

# ==================================================
# CONFIGURAÇÕES GLOBAIS
# ==================================================
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Variável global para manter a conexão aberta
PLANILHA_CACHE = None

# Dicionários que serão populados dinamicamente
CAT_MAP = {}
PGTO_MAP = {}

# Dicionários de fallback (Padrão caso a planilha falhe)
DEFAULT_CAT = {
    'alimentacao': 'Alimentação', 'mercado': 'Alimentação', 'lanche': 'Alimentação',
    'transporte': 'Transporte', 'uber': 'Transporte', 'posto': 'Transporte',
    'lazer': 'Lazer', 'cinema': 'Lazer', 'restaurante': 'Lazer',
    'saude': 'Saúde', 'farmacia': 'Saúde',
    'casa': 'Casa', 'luz': 'Casa', 'internet': 'Casa'
}
DEFAULT_PGTO = {
    'credito': 'Crédito', 'cc': 'Crédito',
    'debito': 'Débito',
    'pix': 'Pix', 'dinheiro': 'Dinheiro'
}

# ==================================================
# GERENCIADOR DE CONEXÃO E CONFIGURAÇÃO
# ==================================================
def obter_planilha():
    global PLANILHA_CACHE
    try:
        if PLANILHA_CACHE:
            PLANILHA_CACHE.title 
            return PLANILHA_CACHE
    except:
        print("🔄 Conexão perdida. Reconectando...")
    
    PLANILHA_CACHE = conectar()
    return PLANILHA_CACHE

def carregar_dicionarios():
    """
    Lê a aba 'config_bot' da planilha para atualizar os sinônimos.
    """
    global CAT_MAP, PGTO_MAP
    
    print("📥 Carregando configurações da planilha...")
    p = obter_planilha()
    
    # Começa com os padrões para garantir funcionamento
    CAT_MAP = DEFAULT_CAT.copy()
    PGTO_MAP = DEFAULT_PGTO.copy()
    
    if not p:
        print("⚠️ Sem conexão. Usando dicionários padrão.")
        return

    try:
        # Tenta ler a aba de configurações
        aba_config = p.worksheet("config_bot")
        dados = aba_config.get_all_records()
        
        for linha in dados:
            termo = str(linha.get('termo', '')).strip().lower()
            vinculo = str(linha.get('vinculo', '')).strip()
            tipo = str(linha.get('tipo', '')).strip().lower()
            
            if termo and vinculo:
                if tipo == 'categoria':
                    CAT_MAP[termo] = vinculo
                elif tipo == 'pgto':
                    PGTO_MAP[termo] = vinculo
                    
        print(f"✅ Configurações carregadas! {len(CAT_MAP)} regras de Categoria e {len(PGTO_MAP)} de Pagamento.")
        
    except Exception as e:
        print(f"⚠️ Aba 'config_bot' não encontrada ou erro de leitura: {e}")
        print("➡️ Mantendo dicionários padrão.")

# ==================================================
# GESTÃO DE USUÁRIO
# ==================================================

def buscar_usuario_por_telegram(telegram_id):
    p = obter_planilha()
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
    p = obter_planilha()
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
        
        # --- 1. VALOR (Remove do item) ---
        if any(c.isdigit() for c in palavra) and valor == 0.0:
            try:
                clean = palavra.lower().replace('r$', '').replace(',', '.')
                valor = float(clean)
                continue # Pula a palavra (não entra no nome do item)
            except: pass
        
        # --- 2. PAGAMENTO (Remove do item) ---
        # "Crédito", "Pix", etc. geralmente não fazem parte do nome do produto.
        if p_lower in PGTO_MAP:
            pagamento = PGTO_MAP[p_lower]
            continue # Pula a palavra
        
        # --- 3. CATEGORIA (MANTÉM no item - Mudança Opção 1) ---
        if p_lower in CAT_MAP:
            categoria = CAT_MAP[p_lower]
            # REMOVEMOS O 'continue' aqui. 
            # Assim, "mac" define a categoria Alimentação, mas continua no fluxo para ser adicionado ao nome.
            
        palavras_item.append(palavra)
        
    # Se, mesmo assim, o item ficou vazio (ex: só mandou valor), define um padrão
    nome_final = " ".join(palavras_item)
    if not nome_final:
        nome_final = categoria if categoria != "Outros" else "Despesa Avulsa"

    return nome_final, valor, categoria, pagamento

# ==================================================
# HANDLERS
# ==================================================

@bot.message_handler(commands=['refresh', 'atualizar'])
def atualizar_config(message):
    """Comando secreto para forçar atualização das categorias sem reiniciar o bot"""
    carregar_dicionarios()
    bot.reply_to(message, "🔄 Regras de categorias e pagamentos atualizadas da planilha!")

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
        p = obter_planilha()
        novo_id = str(uuid.uuid4())
        
        p.worksheet("registros").append_row([
            novo_id,
            datetime.now().strftime("%d/%m/%Y"),
            item,
            valor,
            pgto,
            "Bot Telegram",
            categoria,
            usuario
        ])
        bot.reply_to(message, f"✅ **Lançado!**\nItem: {item}\nValor: R$ {valor:.2f}\nCat: {categoria}\nPgto: {pgto}")
    except Exception as e:
        # Se der erro de conexão, limpa cache para reconectar na próxima
        global PLANILHA_CACHE
        PLANILHA_CACHE = None
        bot.reply_to(message, f"Erro ao salvar: {e}")

# ==================================================
# INICIALIZAÇÃO
# ==================================================
print("🤖 Iniciando Bot...")
carregar_dicionarios() # Carrega regras ao iniciar
print("🤖 Bot Rodando!")
bot.infinity_polling()