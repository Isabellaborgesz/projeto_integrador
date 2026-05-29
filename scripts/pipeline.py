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
    # ETAPA 3 - MODELAGEM SIMPLIFICADA (MATRIZ DE GAPS)
    # ==========================================
    def model_opportunities(self):
        print("--- ETAPA 3: Modelagem de Oportunidades Simplificada ---")
        
        # 1. Mapear o perfil de consumo de cada cliente (Tabela de 0 e 1)
        # Cria colunas para cada serviço dizendo se o cliente tem (1) ou não (0)
        self.df_clients['servico_clean'] = self.df_clients['servico'].astype(str).str.upper()
        matriz_contratos = pd.crosstab(self.df_clients['codcli'], self.df_clients['servico_clean'])
        
        # Garantir que as colunas principais existam na matriz para evitar erros
        for col in ['BACKUP', 'FIREWALL', 'ANTIVIRUS', 'ACESSO DEDICADO']:
            if col not in matriz_contratos.columns:
                matriz_contratos[col] = 0

        # 2. Consolidar a dor do cliente (Total de tickets por categoria)
        matriz_dores = pd.crosstab(self.df_tickets['codcli'], self.df_tickets['categoria_nlp'])

        # 3. Unificar as duas matrizes em um único painel de controle
        painel = pd.merge(matriz_dores, matriz_contratos, on='codcli', how='inner').reset_index()

        # 4. Extrair oportunidades usando filtros simples e diretos
        oportunidades = []
        
        # Buscar os segmentos se existirem
        segmentos = {}
        if 'segmento' in self.df_clients.columns:
            segmentos = self.df_clients.set_index('codcli')['segmento'].to_dict()

        for _, row in painel.iterrows():
            cliente = row['codcli']
            seg = segmentos.get(cliente, "Não Informado")
            
            # FILTRO 1: Reclamou de Backup mas NÃO tem Backup contratado
            if row.get('BACKUP', 0) > 0 and row.get('BACKUP_y', 0) == 0: # _y ou nome exato se cruzar
                # Para garantir que pegamos a coluna certa independente do nome:
                tem_chamado = row.get('BACKUP', 0)
                tem_contrato = row.get('BACKUP', 0) if 'BACKUP' in matriz_contratos.columns else 0
                
            # Vamos usar uma lógica mais limpa e direta aproveitando as variáveis da linha
            # Cenário A: Dor em BACKUP + Falta de Produto BACKUP
            if 'BACKUP' in matriz_dores.columns and row['BACKUP'] > 0:
                # Se não tem a palavra BACKUP nos serviços dele
                if row.get('BACKUP', 0) > 0 and not any('BACKUP' in str(c) for c in matriz_contratos.columns if row[c] > 0):
                    oportunidades.append({
                        'codcli': cliente, 'segmento': seg, 'categoria_problema': 'BACKUP',
                        'qtd_tickets': row['BACKUP'], 'servico_sugerido': 'Backup Gerenciado'
                    })

            # Cenário B: Dor em SEGURANÇA + Falta de Firewall/Antivirus
            if 'SEGURANÇA' in matriz_dores.columns and row['SEGURANÇA'] > 0:
                tem_firewall = row.get('FIREWALL', 0) > 0 if 'FIREWALL' in matriz_contratos.columns else False
                tem_antivirus = row.get('ANTIVIRUS', 0) > 0 if 'ANTIVIRUS' in matriz_contratos.columns else False
                if not (tem_firewall or tem_antivirus):
                    oportunidades.append({
                        'codcli': cliente, 'segmento': seg, 'categoria_problema': 'SEGURANÇA',
                        'qtd_tickets': row['SEGURANÇA'], 'servico_sugerido': 'Pacote de Cibersegurança / Firewall'
                    })

            # Cenário C: Dor em INTERNET/REDE + Falta de Link Dedicado
            if 'INTERNET/REDE' in matriz_dores.columns and row['INTERNET/REDE'] > 0:
                tem_link = row.get('ACESSO DEDICADO', 0) > 0 if 'ACESSO DEDICADO' in matriz_contratos.columns else False
                if not tem_link:
                    oportunidades.append({
                        'codcli': cliente, 'segmento': seg, 'categoria_problema': 'INTERNET/REDE',
                        'qtd_tickets': row['INTERNET/REDE'], 'servico_sugerido': 'Acesso Dedicado Link Corporativo'
                    })

        self.df_opps = pd.DataFrame(oportunidades)

    # ==========================================
    # ETAPA 4 - SCORE COMERCIAL SIMPLIFICADO (MÉDIA SIMPLES)
    # ==========================================
    def score_opportunities(self):
        print("--- ETAPA 4: Calculando Score Simplificado ---")
        if self.df_opps.empty:
            print("Nenhuma oportunidade para pontuar.")
            return

        # Multiplicação simples: Qtd de chamados determina o tamanho do problema
        # Se abriu 1 ou 2 chamados = Baixa prioridade (Problema esporádico)
        # Se abriu de 3 a 5 chamados = Média prioridade (Problema recorrente)
        # Se abriu mais de 5 chamados = Alta prioridade (Crise / Lead Quente)
        def definir_prioridade(qtd):
            if qtd > 5: return "ALTA"
            elif qtd >= 3: return "MÉDIA"
            else: return "BAIXA"

        self.df_opps['prioridade_comercial'] = self.df_opps['qtd_tickets'].apply(definir_prioridade)
        
        # Manter compatibilidade com a etapa de script criando as colunas fictícias de apoio
        self.df_opps['servicos_contratados'] = "Verificado na Matriz"

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