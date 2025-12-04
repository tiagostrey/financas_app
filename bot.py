import telebot
from conexao import conectar
import pandas as pd
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES
# ==============================================================================
# Cole seu TOKEN do BotFather aqui (ou use arquivo .env se souber configurar)
TOKEN = "8468850047:AAHNhy7O9XzODin2biNV1DGeUrEBZw982OM" 

bot = telebot.TeleBot(TOKEN)

# ==============================================================================
# FUNÇÕES DE GESTÃO DE USUÁRIO (VIA SHEET)
# ==============================================================================

def buscar_usuario_por_telegram(telegram_id):
    """
    Verifica se o ID do Telegram já existe na aba 'usuarios' da planilha.
    Retorna o 'nome' do usuário se encontrar, ou None se não encontrar.
    """
    planilha = conectar()
    if not planilha: return None
    
    try:
        aba_user = planilha.worksheet("usuarios")
        # Pega todos os registros (lista de dicionários)
        usuarios = aba_user.get_all_records()
        
        # Procura o ID (converte para string para garantir comparação)
        for u in usuarios:
            if str(u.get('telegram_id', '')).strip() == str(telegram_id):
                return u['nome'] # Retorna o login do sistema (ex: tiagostrey)
        return None
    except Exception as e:
        print(f"Erro ao buscar usuário: {e}")
        return None

def vincular_usuario(telegram_id, nome_informado):
    """
    Tenta vincular um ID de Telegram a um usuário existente na planilha.
    """
    planilha = conectar()
    if not planilha: return False, "Erro de conexão."
    
    try:
        aba_user = planilha.worksheet("usuarios")
        # get_all_records é bom, mas para editar precisamos achar a linha exata (célula)
        # Vamos usar find para achar o nome
        cell = aba_user.find(nome_informado)
        
        if not cell:
            return False, "Usuário não encontrado no sistema. Peça ao administrador para criar sua conta primeiro."
        
        # Verifica se já tem ID vinculado nessa linha (Coluna 3 assumindo ordem: Nome, Senha, ID)
        # O ideal é buscar pelo cabeçalho, mas vamos assumir que 'telegram_id' é a coluna C (3) ou D (4)
        # Vamos ler a linha inteira para ser seguro
        linha_dados = aba_user.row_values(cell.row)
        
        # Cabeçalhos: nome, senha, telegram_id
        # Se a lista da linha for curta, não tem ID ainda.
        # Ajuste o índice conforme sua planilha. Se telegram_id for a 3ª coluna, índice é 2.
        
        # Maneira mais segura: Atualizar a coluna 'telegram_id' (cabeçalho) na linha encontrada
        # Acha a coluna do telegram_id
        header = aba_user.row_values(1)
        try:
            col_index = header.index("telegram_id") + 1 # +1 porque gspread usa base 1
        except:
            return False, "Erro na Planilha: Coluna 'telegram_id' não existe na aba usuarios."

        val_atual = aba_user.cell(cell.row, col_index).value
        
        if val_atual and str(val_atual).strip() != "":
            return False, "Este usuário já possui um Telegram vinculado."
            
        # Realiza o vínculo
        aba_user.update_cell(cell.row, col_index, str(telegram_id))
        return True, f"Sucesso! Telegram vinculado ao usuário **{nome_informado}**."
        
    except Exception as e:
        return False, f"Erro ao vincular: {e}"

# ==============================================================================
# LÓGICA DO BOT
# ==============================================================================

@bot.message_handler(func=lambda message: True)
def receber_mensagem(message):
    chat_id = message.chat.id
    texto = message.text.strip()
    
    print(f"📩 Msg de {chat_id}: {texto}")

    # 1. IDENTIFICAÇÃO: Quem é esse Telegram ID?
    usuario_planilha = buscar_usuario_por_telegram(chat_id)

    # --- CENÁRIO A: USUÁRIO DESCONHECIDO (Tenta Vincular) ---
    if not usuario_planilha:
        # Se o usuário mandou o comando /start, damos as boas vindas
        if texto == "/start":
            bot.reply_to(message, "👋 Olá! Não encontrei seu Telegram no sistema.\n\nPara vincular, responda com seu **Nome de Usuário** do App (ex: tiagostrey).")
            return

        # Tenta usar o texto enviado como "Nome de Usuário" para fazer o vínculo
        sucesso, resposta = vincular_usuario(chat_id, texto)
        
        if sucesso:
            bot.reply_to(message, f"✅ {resposta}\n\nAgora você pode enviar seus gastos! Tente enviar: `Padaria 20`")
        else:
            bot.reply_to(message, f"🚫 {resposta}\n\nTente novamente enviar apenas seu usuário correto ou contate o administrador.")
        return

    # --- CENÁRIO B: USUÁRIO AUTORIZADO (Processa Despesa) ---
    
    # Validação básica de formato (ex: Padaria 20.00)
    partes = texto.split()
    if len(partes) < 2:
        bot.reply_to(message, f"Oi, {usuario_planilha}! 👋\nPara lançar, envie: `Item Valor`\nEx: `Padaria 15.90`")
        return

    # Tenta descobrir o valor (assumindo que pode estar no início ou fim)
    item = ""
    valor = 0.0
    categoria = "Outros" # Categoria padrão se não detectar

    # Lógica simples: Tenta achar o número na mensagem
    try:
        # Pega o último elemento como valor (ex: Padaria 20)
        valor_str = partes[-1].replace(",", ".")
        valor = float(valor_str)
        item = " ".join(partes[:-1]) # O resto é o nome
    except:
        try:
            # Tenta pegar o primeiro elemento como valor (ex: 20 Padaria)
            valor_str = partes[0].replace(",", ".")
            valor = float(valor_str)
            item = " ".join(partes[1:])
        except:
            bot.reply_to(message, "❌ Não entendi o valor. Use ponto ou vírgula.\nEx: `Almoço 25.50`")
            return

    # Tenta adivinhar categoria (Bem básico, pode melhorar depois com IA ou lista)
    item_lower = item.lower()
    if any(x in item_lower for x in ['uber', 'gasolina', 'posto', 'bus']): categoria = "Transporte"
    elif any(x in item_lower for x in ['mercado', 'padaria', 'ifood', 'lanche', 'pizza']): categoria = "Alimentação"
    elif any(x in item_lower for x in ['luz', 'internet', 'aluguel', 'condominio']): categoria = "Casa"
    elif any(x in item_lower for x in ['farmacia', 'medico', 'remedio']): categoria = "Saúde"

    # --- SALVAR NA PLANILHA ---
    try:
        planilha = conectar()
        aba_registros = planilha.worksheet("registros")
        
        data_hoje = datetime.now().strftime("%d/%m/%Y")
        
        # Colunas: Data, Item, Valor, Categoria, FormaPagto, Usuario
        aba_registros.append_row([
            data_hoje,
            item,
            valor,
            categoria,
            "Bot Telegram", # Forma de pagamento padrão
            usuario_planilha # O nome que pegamos do mapa (ex: tiagostrey)
        ])
        
        bot.reply_to(message, f"✅ **Lançado!**\nItem: {item}\nValor: R$ {valor:.2f}\nCat: {categoria}\nUsuário: {usuario_planilha}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Erro ao salvar na planilha: {e}")

# Inicia o Bot
print("🤖 Bot Financeiro (Multi-usuário) Iniciado!")
bot.infinity_polling()