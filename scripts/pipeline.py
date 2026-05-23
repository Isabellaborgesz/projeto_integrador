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
    # ETAPA 3 - MODELAGEM DE OPORTUNIDADES (ALTERADA)
    # ==========================================
    def model_opportunities(self):
        print("--- ETAPA 3: Cruzamento Tickets x Serviços Contratados (Filtrando Poucos Serviços) ---")
        
        # Checar se a coluna 'codcli' existe (cliente ID)
        if 'codcli' not in self.df_clients.columns or 'codcli' not in self.df_tickets.columns:
            print("Erro: A coluna 'codcli' (ID do cliente) não foi encontrada nas planilhas.")
            self.df_opps = pd.DataFrame()
            return

        servicos_por_cliente = self.df_clients.groupby('codcli')['servico'].apply(
            lambda x: ', '.join(x.dropna().astype(str).str.upper())
        ).reset_index()
        servicos_por_cliente.rename(columns={'servico': 'servicos_contratados'}, inplace=True)

        recorrencia_tickets = self.df_tickets.groupby(['codcli', 'categoria_nlp']).agg(
            qtd_tickets=('id_ticket', 'count')
        ).reset_index()

        df_cruzamento = pd.merge(recorrencia_tickets, servicos_por_cliente, on='codcli', how='left')
        df_cruzamento['servicos_contratados'] = df_cruzamento['servicos_contratados'].fillna('')

        oportunidades = []
        for _, row in df_cruzamento.iterrows():
            cliente = row['codcli']
            categoria = row['categoria_nlp']
            qtd = row['qtd_tickets']
            servicos = row['servicos_contratados']

            # --- NOVA LÓGICA: Contar quantos serviços o cliente tem ativo atualmente ---
            # Como seus serviços estão separados por vírgula (Ex: "FIBRA, ANTIVIRUS"), 
            # contamos quantas vírgulas existem + 1. Se estiver vazio, o total é 0.
            if servicos.strip() == "":
                total_servicos = 0
            else:
                total_servicos = len(servicos.split(','))

            gap_encontrado = False
            servico_sugerido = ""

            if categoria == "BACKUP" and "BACKUP" not in servicos:
                gap_encontrado = True
                servico_sugerido = "Backup Gerenciado"
            elif categoria == "SEGURANÇA" and ("FIREWALL" not in servicos and "ANTIVIRUS" not in servicos):
                gap_encontrado = True
                servico_sugerido = "Pacote de Cibersegurança / Firewall"
            elif categoria == "INTERNET/REDE" and "ACESSO DEDICADO" not in servicos:
                gap_encontrado = True
                servico_sugerido = "Acesso Dedicado Link Corporativo"

            # --- FILTRO RESTRITIVO ALTERADO ---
            # O cliente precisa ter o GAP técnico, ter mais de 20 tickets E possuir POUCOS serviços contratados (ex: no máximo 2)
            MAX_SERVICOS_PERMITIDOS = 2 
            
            if gap_encontrado and qtd >= 20 and total_servicos <= MAX_SERVICOS_PERMITIDOS: 
                oportunidades.append({
                    'codcli': cliente,
                    'categoria_problema': categoria,
                    'qtd_tickets': qtd,
                    'servicos_contratados': servicos,
                    'servico_sugerido': servico_sugerido
                })
        
        self.df_opps = pd.DataFrame(oportunidades)
        print(f"Oportunidades filtradas geradas: {self.df_opps.shape[0]} registros.")

    # ==========================================
    # ETAPA 4 - SCORE DE OPORTUNIDADE
    # ==========================================
    def score_opportunities(self):
        print("--- ETAPA 4: Calculando Score de Lead ---")
        if self.df_opps.empty:
            print("Nenhuma oportunidade encontrada.")
            return

        peso_categoria = {"BACKUP": 3, "SEGURANÇA": 3, "INTERNET/REDE": 2, "HOSPEDAGEM/CLOUD": 1, "OUTROS": 1}
        self.df_opps['peso'] = self.df_opps['categoria_problema'].map(peso_categoria)
        self.df_opps['score_bruto'] = self.df_opps['qtd_tickets'] * self.df_opps['peso']

        def classificar_score(score):
            if score >= 15: return "ALTA"
            elif score >= 6: return "MÉDIA"
            else: return "BAIXA"

        self.df_opps['prioridade_comercial'] = self.df_opps['score_bruto'].apply(classificar_score)

    # ==========================================
    # ETAPAS 5 E 6 - RECOMENDAÇÃO E SCRIPT COMERCIAL
    # ==========================================
    def generate_sales_script(self):
        print("--- ETAPAS 5 e 6: Gerando Recomendações e Scripts ---")
        if self.df_opps.empty: return

        scripts = []
        for _, row in self.df_opps.iterrows():
            script = f"""
Cliente (ID): {row['codcli']}
Problema Recorrente: {row['categoria_problema']} ({row['qtd_tickets']} tickets abertos)
Serviços Atuais: {row['servicos_contratados']}
Serviço Sugerido: {row['servico_sugerido']}
Prioridade: {row['prioridade_comercial']}

SCRIPT DE ABORDAGEM:
"Olá, notei que sua equipe tem aberto chamados técnicos relacionados a {row['categoria_problema']}. 
Como vocês ainda não possuem nosso serviço de {row['servico_sugerido']}, gostaria de agendar uma reunião de 15 minutos para apresentar como essa solução eliminaria esses incidentes. Que tal amanhã à tarde?"
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
    