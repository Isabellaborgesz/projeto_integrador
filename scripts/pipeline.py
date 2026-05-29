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

        titulo = self.df_tickets.get('titulo', pd.Series(dtype=str)).fillna('')
        mensagem = self.df_tickets.get('mensagem', pd.Series(dtype=str)).fillna('')
        texto_ticket = titulo.astype(str) + " " + mensagem.astype(str)

        self.df_tickets['texto_limpo'] = texto_ticket.str.lower()
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
    # ETAPA 3 - MODELAGEM SIMPLIFICADA E ROBUSTA
    # ==========================================
    def model_opportunities(self):
        print("--- ETAPA 3: Modelagem de Oportunidades Simplificada ---")

        if 'codcli' not in self.df_clients.columns or 'codcli' not in self.df_tickets.columns:
            print("Erro: A coluna 'codcli' não foi encontrada nas planilhas.")
            self.df_opps = pd.DataFrame()
            return

        # 1. Identificar quais categorias de problemas cada cliente teve (e quantos tickets)
        recorrencia = self.df_tickets.groupby(['codcli', 'categoria_nlp']).size().reset_index(name='qtd_tickets')
        
        # Filtrar o saco de gatos: não faz sentido vender produto para a categoria "OUTROS"
        recorrencia = recorrencia[recorrencia['categoria_nlp'] != 'OUTROS']

        # 2. Criar um dicionário rápido para saber o que cada cliente JÁ TEM contratado
        # Isso evita fazer merges complexos que mudam os nomes das colunas
        servicos_por_cliente = self.df_clients.groupby('codcli')['servico'].apply(
            lambda x: list(x.dropna().astype(str).str.upper())
        ).to_dict()

        # Pegar os segmentos dos clientes
        segmentos = {}
        if 'segmento' in self.df_clients.columns:
            segmentos = self.df_clients.set_index('codcli')['segmento'].to_dict()

        oportunidades = []

        # 3. Varrer a lista de dores e checar se há o GAP no contrato
        for _, row in recorrencia.iterrows():
            cliente = row['codcli']
            categoria = row['categoria_nlp']
            qtd = row['qtd_tickets']
            
            # Buscar o que esse cliente específico já tem em contrato (lista vazia se não achar)
            contratos_cliente = servicos_por_cliente.get(cliente, [])
            
            # Unificar todos os contratos em uma string única para facilitar a busca por palavra-chave
            texto_contratos = " ".join(contratos_cliente)

            gap_encontrado = False
            servico_sugerido = ""

            # Regras diretas baseadas na dor do chamado vs o que falta no contrato
            if categoria == "BACKUP" and "BACKUP" not in texto_contratos:
                gap_encontrado = True
                servico_sugerido = "Backup Gerenciado"
                
            elif categoria == "SEGURANÇA" and not any(w in texto_contratos for w in ["FIREWALL", "ANTIVIRUS", "SEGURANÇA"]):
                gap_encontrado = True
                servico_sugerido = "Pacote de Cibersegurança / Firewall"
                
            elif categoria == "INTERNET/REDE" and not any(w in texto_contratos for w in ["DEDICADO", "LINK", "REDE"]):
                gap_encontrado = True
                servico_sugerido = "Acesso Dedicado Link Corporativo"
                
            elif categoria == "HOSPEDAGEM/CLOUD" and not any(w in texto_contratos for w in ["CLOUD", "HOSPEDAGEM", "VIRTUAL"]):
                gap_encontrado = True
                servico_sugerido = "Migração para Nuvem / Cloud Dedicado"

            # Se encontrou a dor e o cliente não paga por esse serviço: temos uma oportunidade!
            if gap_encontrado:
                oportunidades.append({
                    'codcli': cliente,
                    'segmento': segmentos.get(cliente, "Não Informado"),
                    'categoria_problema': categoria,
                    'qtd_tickets': qtd,
                    'servicos_contratados': ", ".join(contratos_cliente) if contratos_cliente else "Nenhum Serviço Ativo",
                    'servico_sugerido': servico_sugerido
                })

        self.df_opps = pd.DataFrame(oportunidades)
        print(f"Processamento concluído. Oportunidades reais geradas: {self.df_opps.shape[0]}")

    # ==========================================
    # ETAPA 4 - SCORE COMERCIAL SIMPLIFICADO
    # ==========================================
    def score_opportunities(self):
        print("--- ETAPA 4: Calculando Score Simplificado ---")
        if self.df_opps.empty:
            return

        # Regra comercial baseada no volume de dor (recorrência de chamados)
        def definir_prioridade(qtd):
            if qtd >= 5: return "ALTA"
            elif qtd >= 2: return "MÉDIA"
            else: return "BAIXA"

        self.df_opps['prioridade_comercial'] = self.df_opps['qtd_tickets'].apply(definir_prioridade)

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
    # Caminho do script atual
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Sobe um nível para a raiz do projeto (C:\Users\Cliente\Documents\GitHub\DASHBOARD)
    BASE_DIR = os.path.dirname(SCRIPT_DIR)

    # Agora os caminhos vão apontar corretamente para a raiz do projeto
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
    # Executa o processo completo
    pipeline.run()