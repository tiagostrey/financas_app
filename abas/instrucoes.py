import streamlit as st

def render():
    st.subheader("📘 Guia de Uso do Sistema")
    
    with st.expander("⚖️ Comparativo de Rentabilidade", expanded=True):
        st.write("""
        **Objetivo:** Comparar dois produtos de investimento para decidir qual rende mais.
        - **Produto Atual:** O que você já tem ou está analisando (ex: uma LCI de 90% do CDI).
        - **Comparar com:** O benchmark (ex: um CDB de 110% do CDI).
        - **Resultado:** O sistema calcula o IR regressivo automaticamente e mostra qual produto ganha no prazo estipulado.
        """)

    with st.expander("📈 Simulador de Juros Compostos"):
        st.write("""
        **Objetivo:** Projetar o crescimento do seu patrimônio ao longo do tempo.
        - Preencha o valor inicial, o aporte mensal e a taxa anual estimada.
        - O gráfico mostra a curva exponencial dos juros sobre juros.
        """)

    with st.expander("🎯 Planejador de Metas"):
        st.write("""
        **Objetivo:** Descobrir quanto você precisa investir por mês para realizar um sonho.
        - Defina quanto quer ter (ex: R$ 50.000) e em quanto tempo (ex: 5 anos).
        - O sistema calcula o aporte mensal necessário considerando a rentabilidade escolhida.
        """)

    with st.expander("🛒 Calculadora: À Vista ou A Prazo?"):
        st.write("""
        **Objetivo:** Decidir matematicamente se vale a pena pegar o desconto à vista ou parcelar.
        - O sistema considera que, se você parcelar, o dinheiro fica rendendo no CDI.
        - Ele compara o **Desconto à Vista** vs **Rendimento do dinheiro aplicado** durante as parcelas.
        """)

    with st.expander("💰 Meus Investimentos (Área Restrita)"):
        st.write("""
        **Objetivo:** Controlar sua carteira real.
        - **Adicionar:** Cadastre novos aportes.
        - **Gerenciar:** Edite ou exclua lançamentos.
        - **Cálculos:** O sistema busca o histórico real da Selic/CDI para calcular quanto seu dinheiro rendeu até hoje.
        - **Tributação:** Se for "Tributado", ele desconta o IR automaticamente conforme o tempo (tabela regressiva).
        """)

    with st.expander("💸 Extrato de Despesas (Área Restrita)"):
        st.write("""
        **Objetivo:** Visualizar os gastos lançados via Bot do Telegram.
        - O gráfico de donut mostra onde você está gastando mais.
        - Caso precise, o tutorial de configuração do Bot está dentro da aba de Despesas.
        """)