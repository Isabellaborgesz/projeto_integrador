import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
import plotly.express as px
import os

# 1. CONFIGURAÇÃO DA PÁGINA (Precisa obrigatoriamente ser o primeiro comando Streamlit do código)
st.set_page_config(page_title="Motor de Oportunidades B2B", layout="wide")

# 2. CONFIGURAÇÕES DE USUÁRIO
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

# 3. RENDERIZA A TELA DE LOGIN
authenticator.login(fields=['username', 'password'])

# 4. VALIDAÇÕES DE SEGURANÇA
if st.session_state["authentication_status"] == False:
    st.error('Usuário ou senha incorretos.')

elif st.session_state["authentication_status"] == None:
    st.warning('Por favor, insira seu usuário e senha.')

elif st.session_state["authentication_status"]:
    # ⚠️ SE O LOGIN FOR BEM-SUCEDIDO, EXECUTA TUDO DAQUI PARA BAIXO (COM RECUO/TAB)
    
    authenticator.logout('Sair do Sistema', 'sidebar')
    nome_usuario = st.session_state["name"]
    
    # Título do Dashboard principal
    st.title("🎯 Dashboard de Oportunidades de Vendas B2B")
    st.markdown(f"Bem-vindo, {nome_usuario}! Identificação automática de Cross-Sell e Up-Sell baseada em chamados de suporte técnico.")

    # 5. FUNÇÃO PARA CARREGAR OS DADOS (LENDO EXCEL .XLSX)
    @st.cache_data
    def load_data():
        # Descobre automaticamente a pasta raiz do projeto de forma dinâmica
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # AJUSTE AQUI: Monta o caminho exato apontando para os seus arquivos .xlsx originais na raiz
        caminho_clientes = os.path.join(BASE_DIR, "Clientes CTI.xlsx")
        caminho_tickets = os.path.join(BASE_DIR, "Result_28.xlsx")
        
        # Se você gerou um arquivo consolidado na pasta output em formato Excel, aponte assim:
        caminho_oportunidades = os.path.join(BASE_DIR, "output", "oportunidades.xlsx")
        
        try:
            # Se o seu pipeline gera o arquivo final na pasta output, usamos ele:
            if os.path.exists(caminho_oportunidades):
                return pd.read_excel(caminho_oportunidades)
            
            # Caso contrário, se o seu app lê direto a planilha original de resultados:
            elif os.path.exists(caminho_tickets):
                return pd.read_excel(caminho_tickets)
                
            return None
        except Exception as e:
            st.error(f"Erro ao ler as planilhas: {e}")
            return None

    df = load_data()

    if df is None or df.empty:
        st.warning("Nenhum dado encontrado. Verifique se os arquivos '.xlsx' existem na pasta raiz ou na pasta 'output'.")
    else:
        # --- KPIs Superiores ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Registros Analisados", len(df))
        
        # Condicionais de segurança caso as colunas de prioridade comercial/tickets existam na sua planilha final
        if 'prioridade_comercial' in df.columns:
            col2.metric("Alta Prioridade (Hot Leads)", len(df[df['prioridade_comercial'] == 'ALTA']))
            top_servico = df['servico_sugerido'].mode()[0] if 'servico_sugerido' in df.columns and not df.empty else "N/A"
            col4.metric("Top Serviço Recomendado", top_servico)
        else:
            col2.metric("Alta Prioridade", "N/A")
            col4.metric("Top Serviço Recomendado", "N/A")
            
        if 'qtd_tickets' in df.columns:
            col3.metric("Tickets Analisados", df['qtd_tickets'].sum())
        elif 'id_ticket' in df.columns:
            col3.metric("Total de Tickets", df['id_ticket'].nunique())
        else:
            col3.metric("Tickets Analisados", "N/A")

        st.divider()

        # --- Gráficos ---
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Análise por Status ou Categoria")
            # Tenta plotar pela coluna 'categoria' ou 'status_cliente' dependendo do seu arquivo original
            coluna_grafico_1 = 'categoria' if 'categoria' in df.columns else ('status_cliente' if 'status_cliente' in df.columns else df.columns[0])
            fig_cat = px.bar(df[coluna_grafico_1].value_counts().reset_index(), 
                            x=coluna_grafico_1, y='count', color=coluna_grafico_1)
            st.plotly_chart(fig_cat, use_container_width=True)

        with c2:
            st.subheader("Distribuição por Serviços ou Classificação")
            coluna_grafico_2 = 'servico' if 'servico' in df.columns else ('classificacao' if 'classificacao' in df.columns else df.columns[1])
            fig_prio = px.pie(df, names=coluna_grafico_2, hole=0.4)
            st.plotly_chart(fig_prio, use_container_width=True)

        # --- Tabela de Dados ---
        st.subheader("Lista de Clientes Extraída das Planilhas")
        
        # Exibe colunas identificadas nas suas planilhas para o professor ver
        colunas_exibicao = [c for c in ['codcli', 'servico', 'status_cliente', 'consultor', 'prioridade_comercial'] if c in df.columns]
        if not colunas_exibicao:
            colunas_exibicao = df.columns[:5].tolist() # Pega as primeiras 5 colunas se não achar as específicas
            
        st.dataframe(df[colunas_exibicao])

        # Se houver os scripts gerados no seu pipeline final, ele os mostra aqui
        if 'script_vendas' in df.columns:
            st.subheader("Scripts Gerados (Clique para expandir)")
            for index, row in df.iterrows():
                identificador = row['codcli'] if 'codcli' in df.columns else index
                st.text(row['script_vendas'])
                