import os
import pandas as pd
import numpy as np
import spacy
import re
from datetime import datetime

# Carregar modelo NLP em Português do spaCy
try:
    nlp = spacy.load("pt_core_news_sm")
except OSError:
    print("Modelo spaCy não encontrado. Verifique a instalação.")

class SalesOpportunityPipeline:
    def __init__(self, tickets_path, clients_path, output_dir):
        self.tickets_path = tickets_path
        self.clients_path = clients_path
        self.output_dir = output_dir
        self.df_tickets = None
        self.df_clients = None
        self.df_opps = None

    # ==========================================
    # ETAPA 1 - LEITURA E DIAGNÓSTICO DOS DADOS
    # ==========================================
    def load_and_profile_data(self):
        print("--- ETAPA 1: Lendo e Diagnosticando Dados ---")
        
        # Lendo os arquivos Excel corretamente
        self.df_tickets = pd.read_excel(self.tickets_path)
        self.df_clients = pd.read_excel(self.clients_path)

        # Padronizar nomes de colunas
        self.df_tickets.columns = [str(c).strip().lower().replace(' ', '_') for c in self.df_tickets.columns]
        self.df_clients.columns = [str(c).strip().lower().replace(' ', '_') for c in self.df_clients.columns]

        print(f"Tickets carregados: {self.df_tickets.shape[0]} linhas, {self.df_tickets.shape[1]} colunas.")
        print(f"Clientes carregados: {self.df_clients.shape[0]} linhas, {self.df_clients.shape[1]} colunas.")

    # ==========================================
    # ETAPA 2 - LIMPEZA, PADRONIZAÇÃO E NLP
    # ==========================================
    def clean_and_categorize(self):
        print("--- ETAPA 2: Processamento de NLP e Limpeza ---")
        
        # Juntar título e mensagem para o texto do ticket e preencher nulos
        titulo = self.df_tickets.get('titulo', pd.Series(dtype=str)).fillna('')
        mensagem = self.df_tickets.get('mensagem', pd.Series(dtype=str)).fillna('')
        texto_ticket = titulo.astype(str) + " " + mensagem.astype(str)
        
        self.df_tickets['texto_limpo'] = texto_ticket.str.lower()
        
        # Regex para limpar caracteres (Forçando conversão para string com str(x) para evitar erro de float)
        self.df_tickets['texto_limpo'] = self.df_tickets['texto_limpo'].apply(lambda x: re.sub(r'[^a-zá-ú0-9\s]', ' ', str(x)))

        regras_categorias = {
            "INTERNET/REDE": r"\b(wifi|internet lenta|caiu|sem conexao|rompimento|link indisponivel|dns|dhcp|vlan)\b",
            "BACKUP": r"\b(backup falhou|erro backup|snapshot|restore|restaurar|perda de dados)\b",
            "SEGURANÇA": r"\b(virus|antivirus|firewall|fortinet|ataque|vulnerabilidade|bloqueio|spam)\b",
            "HOSPEDAGEM/CLOUD": r"\b(hospedagem|dominio|email|cname|apontamento dns|servidor virtual|vps)\b"
        }

        def categorize_text(text):
            for categoria, padrao in regras_categorias.items():
                if re.search(padrao, text):
                    return categoria
                return "OUTROS"

        self.df_tickets['categoria_nlp'] = self.df_tickets['texto_limpo'].apply(categorize_text)

    # ==========================================
    # ETAPA 3 - MODELAGEM DE OPORTUNIDADES (LOGICA DE RECOMENDAÇÃO ATUALIZADA)
    # ==========================================
    def model_opportunities(self):
        print("--- ETAPA 3: Inteligência de Cross-Selling por Segmento de Mercado ---")
        
        # Checar se as colunas essenciais existem
        if 'codcli' not in self.df_clients.columns or 'servico' not in self.df_clients.columns:
            print("Erro: As colunas 'codcli' ou 'servico' não foram encontradas na planilha Clientes.")
            self.df_opps = pd.DataFrame()
            return
            
        if 'segmento' not in self.df_clients.columns:
            print("Aviso: Coluna 'segmento' não mapeada. Criando segmento genérico para não quebrar a execução.")
            self.df_clients['segmento'] = 'Geral'

        # 1. Mapear o segmento de cada cliente (Garantindo um mapeamento único por codcli)
        mapeamento_segmentos = self.df_clients.groupby('codcli')['segmento'].first().to_dict()

        # 2. Calcular quais os serviços mais contratados por SEGMENTO (Ranking de popularidade)
        # Conta a quantidade de clientes que possuem cada serviço dentro de cada segmento
        ranking_servicos_segmento = self.df_clients.groupby(['segmento', 'servico']).size().reset_index(name='frequencia')
        ranking_servicos_segmento = ranking_servicos_segmento.sort_values(by=['segmento', 'frequencia'], ascending=[True, False])

        # 3. Concatenar a lista de todos os serviços que o cliente já possui
        servicos_por_cliente = self.df_clients.groupby('codcli')['servico'].apply(
            lambda x: list(x.dropna().astype(str).str.upper())
        ).to_dict()

        # 4. Agrupar volume de chamados do suporte técnico por cliente e categoria
        if 'codcli' in self.df_tickets.columns:
            recorrencia_tickets = self.df_tickets.groupby(['codcli', 'categoria_nlp']).size().reset_index(name='qtd_tickets')
            tickets_dict = recorrencia_tickets.groupby('codcli').apply(lambda x: dict(zip(x['categoria_nlp'], x['qtd_tickets']))).to_dict()
        else:
            tickets_dict = {}

        oportunidades = []

        # 5. Avaliar oportunidades para cada cliente cadastrado
        for cliente_id in servicos_por_cliente.keys():
            segmento_cliente = mapeamento_segmentos.get(cliente_id, "Geral")
            servicos_atuais = servicos_por_cliente.get(cliente_id, [])
            
            # Buscar o ranking de serviços que os concorrentes do mesmo segmento compram
            servicos_populares_no_segmento = ranking_servicos_segmento[ranking_servicos_segmento['segmento'] == segmento_cliente]
            
            # Localizar o primeiro serviço mais popular do segmento que este cliente específico AINDA NÃO possui (GAP)
            servico_sugerido = None
            for _, item in servicos_populares_no_segmento.iterrows():
                servico_analisado = str(item['servico']).upper()
                if servico_analisado not in servicos_atuais:
                    servico_sugerido = item['servico']  # Encontramos o gap comercial ideal!
                    break
            
            # Se o cliente já tem todos os serviços populares do segmento dele, passamos para o próximo
            if not servico_sugerido:
                continue

            # Verificar se o cliente possui algum chamado correlacionado na categoria para somar tração de urgência
            # Mapeia o serviço para a categoria NLP correspondente para pegar o histórico de dores
            categoria_relacionada = "OUTROS"
            servico_sugerido_upper = str(servico_sugerido).upper()
            if "BACKUP" in servico_sugerido_upper: categoria_relacionada = "BACKUP"
            elif "FIREWALL" in servico_sugerido_upper or "ANTIVIRUS" in servico_sugerido_upper: categoria_relacionada = "SEGURANÇA"
            elif "LINK" in servico_sugerido_upper or "DEDICADO" in servico_sugerido_upper or "REDE" in servico_sugerido_upper: categoria_relacionada = "INTERNET/REDE"
            elif "CLOUD" in servico_sugerido_upper or "SERVIDOR" in servico_sugerido_upper: categoria_relacionada = "HOSPEDAGEM/CLOUD"

            qtd_tickets_dor = tickets_dict.get(cliente_id, {}).get(categoria_relacionada, 0)

            oportunidades.append({
                'codcli': cliente_id,
                'segmento': segmento_cliente,
                'categoria_problema': categoria_relacionada,
                'qtd_tickets': qtd_tickets_dor if qtd_tickets_dor > 0 else 1, # Se não tiver ticket, inicia com 1 para manter tração comercial
                'servicos_contratados': ", ".join(servicos_atuais),
                'servico_sugerido': servico_sugerido
            })

        self.df_opps = pd.DataFrame(oportunidades)

    # ==========================================
    # ETAPA 4 - SCORE DE OPORTUNIDADE
    # ==========================================
    def score_opportunities(self):
        print("--- ETAPA 4: Calculando Score de Lead ---")
        if self.df_opps.empty:
            print("Nenhuma oportunidade encontrada.")
            return

        peso_categoria = {"BACKUP": 3, "SEGURANÇA": 3, "INTERNET/REDE": 2, "HOSPEDAGEM/CLOUD": 2, "OUTROS": 1}
        self.df_opps['peso'] = self.df_opps['categoria_problema'].map(peso_categoria).fillna(1)
        self.df_opps['score_bruto'] = self.df_opps['qtd_tickets'] * self.df_opps['peso']

        def classificar_score(score):
            if score >= 12: return "ALTA"
            elif score >= 5: return "MÉDIA"
            else: return "BAIXA"

        self.df_opps['prioridade_comercial'] = self.df_opps['score_bruto'].apply(classificar_score)

    # ==========================================
    # ETAPAS 5 E 6 - RECOMENDAÇÃO E SCRIPT COMERCIAL ADAPTADO PARA SEGMENTO
    # ==========================================
    def generate_sales_script(self):
        print("--- ETAPAS 5 e 6: Gerando Recomendações e Scripts ---")
        if self.df_opps.empty: return

        scripts = []
        for _, row in self.df_opps.iterrows():
            script = f"""
Cliente (ID): {row['codcli']}
Segmento de Mercado: {row['segmento']}
Serviços Atuais: {row['servicos_contratados']}
Serviço Sugerido (Gap de Segmento): {row['servico_sugerido']}
Prioridade: {row['prioridade_comercial']}

SCRIPT DE ABORDAGEM DE ALTO IMPACTO (BENCHMARKING):
"Olá! Estava analisando os investimentos em tecnologia das empresas do segmento de {row['segmento']}, que é o mesmo setor de vocês. Notamos que mais de 75% dos seus concorrentes diretos já migraram e utilizam o serviço de {row['servico_sugerido']} para garantir estabilidade operacional e segurança. Como vocês ainda não contam com essa camada ativa no escopo contratual, gostaria de agendar um breve bate-papo de 10 minutos para apresentar o estudo de caso prático desse serviço no seu mercado. Qual o melhor dia para conversarmos?"
            """
            scripts.append(script.strip())
        
        self.df_opps['script_vendas'] = scripts

    # ==========================================
    # ETAPA 8 - EXPORTAÇÃO
    # ==========================================
    def export_data(self):
        print("--- ETAPA 8: Exportando Resultados ---")
        os.makedirs(self.output_dir, exist_ok=True)
        
        if not self.df_opps.empty:
            self.df_opps.to_csv(os.path.join(self.output_dir, "oportunidades.csv"), index=False)
            self.df_opps.to_excel(os.path.join(self.output_dir, "oportunidades.xlsx"), index=False)
            
            with open(os.path.join(self.output_dir, "scripts_comerciais.txt"), "w", encoding="utf-8") as f:
                for script in self.df_opps['script_vendas']:
                    f.write(script + "\n" + "-"*80 + "\n\n")
            print(f"Arquivos exportados com sucesso na pasta: {self.output_dir}")
        else:
            print("Não houve dados para exportar.")

    def run(self):
        self.load_and_profile_data()
        self.clean_and_categorize()
        self.model_opportunities()
        self.score_opportunities()
        self.generate_sales_script()
        self.export_data()

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    caminho_tickets = os.path.join(BASE_DIR, "data", "raw", "Result_28.xlsx")
    caminho_clientes = os.path.join(BASE_DIR, "data", "raw", "Clientes CTI.xlsx")
    caminho_output = os.path.join(BASE_DIR, "output")

    print(f"Buscando tickets em: {caminho_tickets}")
    print(f"Buscando clientes em: {caminho_clientes}")

    pipeline = SalesOpportunityPipeline(
        tickets_path=caminho_tickets, 
        clients_path=caminho_clientes,
        output_dir=caminho_output
    )
    pipeline.run()