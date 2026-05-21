import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import plotly.express as px

# 1. Suas configurações de usuário (Mantenha como está)
config = {                                      
     "credentials": {                                     
         "usernames": {
             "rodrigo.cti@senai.com": {
                 "email": "rodrigo.cti@senai.com",
                 "name": "Rodrigo",
                 "password": "$2b$12$GRZMw4/K0nC4bs.LD7pSXujdsathd4Hu9Wk7iGR4EJnSr/XSroxuW" 
             }
         }
     },         
     "cookie": {           
         "expiry_days": 30,                    
         "key": "assinatura_secreta_do_cookie",
         "name": "dashboard_cookie"
     }
}

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

# 2. Renderiza a tela de login
authenticator.login(fields=['username', 'password'])

# 3. Validações de segurança
if st.session_state["authentication_status"] == False:
    st.error('Usuário ou senha incorretos.')

elif st.session_state["authentication_status"] == None:
    st.warning('Por favor, insira seu usuário e senha.')

elif st.session_state["authentication_status"]:
    # ⚠️ TUDO DAQUI PARA BAIXO PRECISA DE 4 ESPAÇOS (OU 1 TAB) NO COMEÇO DA LINHA
    
    authenticator.logout('Sair do Sistema', 'sidebar')
    nome_usuario = st.session_state["name"]
    st.title(f"Bem-vindo ao Dashboard, {nome_usuario}!")
    
    # ⬇️ Cole o seu código antigo aqui dentro (repare no espaço no começo de cada linha):
    df_clientes = pd.read_csv("Clientes CTI.xlsx - Clientes CTI.csv")
    df_tickets = pd.read_csv("Result_28.xlsx - Result 1.csv")
    
    st.subheader("Análise de Chamados e Clientes")
    
    # Exemplo de gráfico (coloque os seus gráficos reais aqui com o recuo):
    fig = px.histogram(df_tickets, x="status_cliente", title="Status dos Chamados")
    st.plotly_chart(fig)
    
    # Se você tiver mais tabelas ou funções, todas ficam com o recuo aqui dentro!
    # --- O RESTANTE DO SEU CÓDIGO (Gráficos, pandas, etc.) CONTINUA AQUI ---
    
   #_______________________________________________________________#


    import streamlit as st
    import pandas as pd
    import plotly.express as px
    import os

    # Configuração da Página
    st.set_page_config(page_title="Motor de Oportunidades B2B", layout="wide")

    st.title("🎯 Dashboard de Oportunidades de Vendas B2B")
    st.markdown("Identificação automática de Cross-Sell e Up-Sell baseada em chamados de suporte técnico.")

    # Carregar dados
    @st.cache_data
    def load_data():
        # Descobre automaticamente a pasta raiz do projeto e aponta para a pasta output
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        caminho_csv = os.path.join(BASE_DIR, "output", "oportunidades.csv")
        
        try:
            return pd.read_csv(caminho_csv)
        except FileNotFoundError:
            return None

    df = load_data()

    if df is None or df.empty:
        st.warning("Nenhum dado encontrado. Verifique se o arquivo 'oportunidades.csv' existe na pasta 'output'. Se não, execute o pipeline.py primeiro.")
    else:
        # --- KPIs Superiores ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Oportunidades", len(df))
        col2.metric("Alta Prioridade (Hot Leads)", len(df[df['prioridade_comercial'] == 'ALTA']))
        col3.metric("Tickets Analisados (Oportunidades)", df['qtd_tickets'].sum())
        top_servico = df['servico_sugerido'].mode()[0] if not df.empty else "N/A"
        col4.metric("Top Serviço Recomendado", top_servico)

        st.divider()

        # --- Gráficos ---
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Oportunidades por Categoria de Problema")
            fig_cat = px.bar(df['categoria_problema'].value_counts().reset_index(), 
                            x='categoria_problema', y='count', color='categoria_problema')
            st.plotly_chart(fig_cat, use_container_width=True)

        with c2:
            st.subheader("Distribuição de Prioridade Comercial")
            fig_prio = px.pie(df, names='prioridade_comercial', hole=0.4, 
                            color='prioridade_comercial',
                            color_discrete_map={'ALTA':'red', 'MÉDIA':'orange', 'BAIXA':'green'})
            st.plotly_chart(fig_prio, use_container_width=True)

        # --- Tabela de Dados e Scripts ---
        st.subheader("Lista de Clientes para Abordagem Comercial")
        
        # Filtro de Prioridade
        prioridade_filtro = st.multiselect("Filtrar por Prioridade", options=["ALTA", "MÉDIA", "BAIXA"], default=["ALTA", "MÉDIA"])
        df_filtrado = df[df['prioridade_comercial'].isin(prioridade_filtro)]

        st.dataframe(df_filtrado[['codcli', 'categoria_problema', 'qtd_tickets', 'servico_sugerido', 'prioridade_comercial']])

        st.subheader("Scripts Gerados (Clique para expandir)")
        for index, row in df_filtrado.iterrows():
            with st.expander(f"Lead ID: {row['codcli']} - {row['servico_sugerido']} (Prioridade: {row['prioridade_comercial']})"):
                st.text(row['script_vendas'])