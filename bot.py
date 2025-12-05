import telebot
from telebot import types # Necessário para os botões
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

# Dicionários de fallback
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
    global CAT_MAP, PGTO_MAP
    print("📥 Carregando configurações da planilha...")
    p = obter_planilha()
    
    CAT_MAP = DEFAULT_CAT.copy()
    PGTO_MAP = DEFAULT_PGTO.copy()
    
    if not p:
        print("⚠️ Sem conexão. Usando dicionários padrão.")
        return

    try:
        aba_config = p.worksheet("config_bot")
        dados = aba_config.get_all_records()
        for linha in dados:
            termo = str(linha.get('termo', '')).strip().lower()
            vinculo = str(linha.get('vinculo', '')).strip()
            tipo = str(linha.get('tipo', '')).strip().lower()
            if termo and vinculo:
                if tipo == 'categoria': CAT_MAP[termo] = vinculo
                elif tipo == 'pgto': PGTO_MAP[termo] = vinculo
        print(f"✅ Configurações carregadas! {len(CAT_MAP)} regras.")
    except Exception as e:
        print(f"⚠️ Erro config: {e}. Usando padrões.")

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
    except: return None

def vincular_usuario(telegram_id, nome_informado):
    p = obter_planilha()
    if not p: return False, "Erro conexão."
    try:
        aba = p.worksheet("usuarios")
        cell = aba.find(nome_informado)
        if not cell: return False, f"Usuário '{nome_informado}' não encontrado."
        
        header = aba.row_values(1)
        try: col_idx = header.index("telegram_id") + 1
        except: return False, "Coluna telegram_id não existe."
            
        aba.update_cell(cell.row, col_idx, str(telegram_id))
        return True, f"Vínculo realizado! Agora você é **{nome_informado}**."
    except Exception as e: return False, f"Erro: {e}"

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
        
        if p_lower in PGTO_MAP:
            pagamento = PGTO_MAP[p_lower]
            continue
        
        if p_lower in CAT_MAP:
            categoria = CAT_MAP[p_lower]
            # Mantém a palavra no item (Opção 1)
            
        palavras_item.append(palavra)
        
    nome_final = " ".join(palavras_item)
    if not nome_final:
        nome_final = categoria if categoria != "Outros" else "Despesa Avulsa"

    return nome_final, valor, categoria, pagamento

# ==================================================
# COMANDOS E HANDLERS
# ==================================================

@bot.message_handler(commands=['refresh', 'atualizar'])
def atualizar_config(message):
    carregar_dicionarios()
    bot.reply_to(message, "🔄 Regras atualizadas!")

# --- COMANDO DESFAZER (NOVO v0.03) ---
@bot.message_handler(commands=['desfazer', 'undo'])
def comando_desfazer(message):
    chat_id = message.chat.id
    usuario = buscar_usuario_por_telegram(chat_id)
    if not usuario:
        bot.reply_to(message, "Usuário não identificado.")
        return

    p = obter_planilha()
    if not p:
        bot.reply_to(message, "Erro de conexão.")
        return

    try:
        # Busca últimos registros para encontrar o do usuário
        aba = p.worksheet("registros")
        # Pega todas as linhas (lista de listas) para ser mais rápido
        todas_linhas = aba.get_all_values()
        
        # Procura de trás para frente
        linha_alvo = None
        idx_alvo = -1
        
        # Assume que as colunas são fixas, mas vamos tentar achar o index pelo cabeçalho
        header = todas_linhas[0]
        try:
            col_user = header.index("usuario")
            col_item = header.index("item")
            col_valor = header.index("valor")
            col_id = header.index("id_despesa")
        except:
            bot.reply_to(message, "Erro: Colunas da planilha mudaram?")
            return

        # Loop reverso (ignora cabeçalho)
        for i in range(len(todas_linhas) - 1, 0, -1):
            row = todas_linhas[i]
            if len(row) > col_user and row[col_user] == usuario:
                linha_alvo = row
                idx_alvo = i # Índice na lista (na planilha é i+1)
                break
        
        if not linha_alvo:
            bot.reply_to(message, "🤷‍♂️ Não encontrei nenhum lançamento recente seu.")
            return

        # Prepara dados para confirmação
        item_nome = linha_alvo[col_item]
        valor_txt = linha_alvo[col_valor]
        uuid_reg = linha_alvo[col_id]

        # Cria botões Inline
        markup = types.InlineKeyboardMarkup()
        # Passamos o UUID no callback para ter certeza absoluta do que apagar
        btn_sim = types.InlineKeyboardButton("🗑️ Sim, apagar", callback_data=f"del_{uuid_reg}")
        btn_nao = types.InlineKeyboardButton("Cancelar", callback_data="cancel_del")
        markup.add(btn_sim, btn_nao)

        bot.reply_to(message, 
                     f"⚠️ **Confirmação**\n\nDeseja apagar seu último lançamento?\n\n🛒 **{item_nome}**\n💰 R$ {valor_txt}", 
                     parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        bot.reply_to(message, f"Erro ao buscar: {e}")

# --- CALLBACK DOS BOTÕES (NOVO v0.03) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_botoes(call):
    if call.data == "cancel_del":
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❌ Operação cancelada.")
        return

    if call.data.startswith("del_"):
        uuid_para_apagar = call.data.split("_")[1]
        
        p = obter_planilha()
        try:
            aba = p.worksheet("registros")
            # Busca a célula que contém o UUID exato
            cell = aba.find(uuid_para_apagar)
            
            if cell:
                aba.delete_rows(cell.row)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="✅ **Apagado!** O registro foi removido da planilha.", parse_mode="Markdown")
            else:
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="⚠️ Erro: Não encontrei esse registro. Talvez já tenha sido apagado.")
                
        except Exception as e:
            bot.answer_callback_query(call.id, "Erro ao apagar.")

# --- PROCESSADOR DE MENSAGENS ---
@bot.message_handler(func=lambda m: True)
def processar(message):
    chat_id = message.chat.id
    texto = message.text.strip()
    
    usuario = buscar_usuario_por_telegram(chat_id)
    
    if not usuario:
        if len(texto.split()) > 1 or any(c.isdigit() for c in texto):
            bot.reply_to(message, "⛔ É novo por aqui?\nInforme seu usuário do App.")
            return
        ok, msg = vincular_usuario(chat_id, texto)
        bot.reply_to(message, msg)
        return

    item, valor, categoria, pgto = interpretar_mensagem(texto)
    
    if valor <= 0:
        bot.reply_to(message, "❌ Valor não identificado.")
        return

    try:
        p = obter_planilha()
        novo_id = str(uuid.uuid4())
        
        # V0.03 - Padrão US/UK (Envia float puro)
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
        
        # Mensagem com link para desfazer
        msg_sucesso = (f"✅ **Lançado!**\n"
                       f"Item: {item}\n"
                       f"Valor: R$ {valor:.2f}\n"
                       f"Cat: {categoria}\n"
                       f"Pgto: {pgto}\n\n"
                       f"↩️ _Errou?_ /desfazer")
                       
        bot.reply_to(message, msg_sucesso, parse_mode="Markdown")
        
    except Exception as e:
        global PLANILHA_CACHE
        PLANILHA_CACHE = None
        bot.reply_to(message, f"Erro ao salvar: {e}")

# ==================================================
# INICIALIZAÇÃO
# ==================================================
print("🤖 Iniciando Bot v0.03...")
carregar_dicionarios()
print("🤖 Bot Rodando!")
bot.infinity_polling()