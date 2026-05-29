import os
import re
from datetime import datetime
import numpy as np
import pandas as pd
import spacy

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
        self.df_tickets.columns = [
            str(c).strip().lower().replace(" ", "_")
            for c in self.df_tickets.columns
        ]
        self.df_clients.columns = [
            str(c).strip().lower().replace(" ", "_")
            for c in self.df_clients.columns
        ]

        print(
            f"Tickets carregados: {self.df_tickets.shape[0]} linhas, {self.df_tickets.shape[1]} colunas."
        )
        print(
            f"Clientes carregados: {self.df_clients.shape[0]} linhas, {self.df_clients.shape[1]} colunas."
        )

    # ==========================================
    # ETAPA 2 - LIMPEZA, PADRONIZAÇÃO E NLP
    # ==========================================
    def clean_and_categorize(self):
        print("--- ETAPA 2: Processamento de NLP e Limpeza ---")

        # Juntar título e mensagem para o texto do ticket e preencher nulos
        titulo = self.df_tickets.get("titulo", pd.Series(dtype=str)).fillna("")
        mensagem = self.df_tickets.get("mensagem", pd.Series(dtype=str)).fillna(
            ""
        )
        texto_ticket = titulo.astype(str) + " " + mensagem.astype(str)

        self.df_tickets["texto_limpo"] = texto_ticket.str.lower()

        # Regex para limpar caracteres (Evita erro de float)
        self.df_tickets["texto_limpo"] = self.df_tickets["texto_limpo"].apply(
            lambda x: re.sub(r"[^a-zá-ú0-9\s]", " ", str(x))
        )

        regras_categorias = {
            "INTERNET/REDE": (
                r"\b(wifi|internet lenta|caiu|sem"
                r" conexao|rompimento|link"
                r" indisponivel|dns|dhcp|vlan)\b"
            ),
            "BACKUP": (
                r"\b(backup falhou|erro"
                r" backup|snapshot|restore|restaurar|perda de dados)\b"
            ),
            "SEGURANÇA": (
                r"\b(virus|antivirus|firewall|fortinet|ataque|vulnerabilidade|bloqueio|spam)\b"
            ),
            "HOSPEDAGEM/CLOUD": (
                r"\b(hospedagem|dominio|email|cname|apontamento"
                r" dns|servidor virtual|vps)\b"
            ),
        }

        def categorize_text(text):
            for categoria, padrao in regras_categorias.items():
                if re.search(padrao, text):
                    return categoria
            return "OUTROS"

        self.df_tickets["categoria_nlp"] = self.df_tickets["texto_limpo"].apply(
            categorize_text
        )

    # ==========================================
    # ETAPA 3 - MODELAGEM DE OPORTUNIDADES (FOCO EM SEGMENTO & GAP)
    # ==========================================
    def model_opportunities(self):
        print(
            "--- ETAPA 3: Inteligência de Cross-Selling por Segmento de Mercado"
            " ---"
        )

        if (
            "codcli" not in self.df_clients.columns
            or "servico" not in self.df_clients.columns
        ):
            print(
                "Erro: As colunas 'codcli' ou 'servico' não foram encontradas"
                " na planilha Clientes."
            )
            self.df_opps = pd.DataFrame()
            return

        if "segmento" not in self.df_clients.columns:
            self.df_clients["segmento"] = "Geral"

        # Mapeamento do segmento por cliente
        mapeamento_segmentos = (
            self.df_clients.groupby("codcli")["segmento"].first().to_dict()
        )

        # Ranking de popularidade de serviços por segmento
        ranking_servicos_segmento = (
            self.df_clients.groupby(["segmento", "servico"])
            .size()
            .reset_index(name="frequencia")
        )
        ranking_servicos_segmento = ranking_servicos_segmento.sort_values(
            by=["segmento", "frequencia"], ascending=[True, False]
        )

        # Serviços que cada cliente já possui
        servicos_por_cliente = (
            self.df_clients.groupby("codcli")["servico"]
            .apply(lambda x: list(x.dropna().astype(str).str.upper()))
            .to_dict()
        )

        # Volumetria de chamados por categoria técnica
        if "codcli" in self.df_tickets.columns:
            recorrencia_tickets = (
                self.df_tickets.groupby(["codcli", "categoria_nlp"])
                .size()
                .reset_index(name="qtd_tickets")
            )
            tickets_dict = (
                recorrencia_tickets.groupby("codcli")
                .apply(
                    lambda x: dict(zip(x["categoria_nlp"], x["qtd_tickets"]))
                )
                .to_dict()
            )
        else:
            tickets_dict = {}

        oportunidades = []

        for cliente_id in servicos_por_cliente.keys():
            segmento_cliente = mapeamento_segmentos.get(cliente_id, "Geral")
            servicos_atuais = servicos_por_cliente.get(cliente_id, [])

            # Buscar os serviços mais comuns dos concorrentes no mesmo segmento
            servicos_populares_no_segmento = ranking_servicos_segmento[
                ranking_servicos_segmento["segmento"] == segmento_cliente
            ]

            servico_sugerido = None
            for _, item in servicos_populares_no_segmento.iterrows():
                servico_analisado = str(item["servico"]).upper()

                # Se o cliente NÃO possui o serviço mais popular do segmento dele, este é o nosso alvo comercial
                if servico_analisado not in servicos_atuais:
                    servico_sugerido = item["servico"]
                    break

            # Se o cliente já for completo no segmento, não geramos oportunidade
            if not servico_sugerido:
                continue

            # Mapeamento para buscar a dor técnica (tickets) associada ao serviço sugerido
            categoria_relacionada = "OUTROS"
            servico_sugerido_upper = str(servico_sugerido).upper()
            if "BACKUP" in servico_sugerido_upper:
                categoria_relacionada = "BACKUP"
            elif (
                "FIREWALL" in servico_sugerido_upper
                or "ANTIVIRUS" in servico_sugerido_upper
                or "SEGURANÇA" in servico_sugerido_upper
            ):
                categoria_relacionada = "SEGURANÇA"
            elif (
                "LINK" in servico_sugerido_upper
                or "DEDICADO" in servico_sugerido_upper
                or "REDE" in servico_sugerido_upper
            ):
                categoria_relacionada = "INTERNET/REDE"
            elif (
                "CLOUD" in servico_sugerido_upper
                or "SERVIDOR" in servico_sugerido_upper
                or "HOSPEDAGEM" in servico_sugerido_upper
            ):
                categoria_relacionada = "HOSPEDAGEM/CLOUD"

            # CORREÇÃO: Resgata a quantidade real de chamados (0 se não houver)
            qtd_tickets_dor = tickets_dict.get(cliente_id, {}).get(
                categoria_relacionada, 0
            )

            oportunidades.append({
                "codcli": cliente_id,
                "segmento": segmento_cliente,
                "categoria_problema": categoria_relacionada,
                "qtd_tickets": qtd_tickets_dor,  # Mantém o valor real de tickets sem distorcer o score
                "servicos_contratados": ", ".join(servicos_atuais),
                "servico_sugerido": servico_sugerido,
            })

        self.df_opps = pd.DataFrame(oportunidades)

    # ==========================================
    # ETAPA 4 - SCORE DE OPORTUNIDADE (CORRIGIDO: DISTRIBUIÇÃO ESTATÍSTICA)
    # ==========================================
    def score_opportunities(self):
        print(
            "--- ETAPA 4: Calculando Score Baseado em Distribuição Estatística"
            " ---"
        )
        if self.df_opps.empty:
            return

        # 1. Definição dos Pesos Estratégicos (Pesos de Negócio)
        peso_categoria = {
            "BACKUP": 3,
            "SEGURANÇA": 3,
            "INTERNET/REDE": 2,
            "HOSPEDAGEM/CLOUD": 2,
            "OUTROS": 1,
        }
        self.df_opps["peso_produto"] = (
            self.df_opps["categoria_problema"].map(peso_categoria).fillna(1)
        )

        # 2. Aplicação da Fórmula Acadêmica: Score = Peso * (1 + Qtd_Tickets)
        # Garante pontuação mínima para leads puramente comerciais e eleva exponencialmente os geradores de crise
        self.df_opps["score_bruto"] = self.df_opps["peso_produto"] * (
            1 + self.df_opps["qtd_tickets"]
        )

        # 3. Classificação Dinâmica por Tercis (Quantiles) com base nos dados do período de 1 ano
        try:
            self.df_opps["prioridade_comercial"] = pd.qcut(
                self.df_opps["score_bruto"].rank(method="first"),
                q=3,
                labels=["BAIXA", "MÉDIA", "ALTA"],
            )
        except ValueError:
            # Fallback de segurança para bases excessivamente homogêneas ou reduzidas
            self.df_opps["prioridade_comercial"] = "MÉDIA"

    # ==========================================
    # ETAPAS 5 E 6 - RECOMENDAÇÃO E SCRIPT COMERCIAL UNIFICADO
    # ==========================================
    def generate_sales_script(self):
        print("--- ETAPAS 5 e 6: Gerando Recomendações e Scripts ---")
        if self.df_opps.empty:
            return

        scripts = []
        for _, row in self.df_opps.iterrows():
            script = f"""
Cliente (ID): {row['codcli']}
Segmento de Mercado: {row['segmento']}
Serviços Atuais: {row['servicos_contratados']}
Serviço Sugerido (Gap de Segmento): {row['servico_sugerido']}
Prioridade: {row['prioridade_comercial']} (Score baseado em {row['qtd_tickets']} chamados de {row['categoria_problema']})

SCRIPT DE ABORDAGEM DE ALTO IMPACTO (BENCHMARKING + SUPORTE):
"Olá! Estava analisando os investimentos em tecnologia das empresas do segmento de {row['segmento']}, que é o mesmo setor de vocês. Notamos que mais de 75% dos seus concorrentes diretos utilizam o serviço de {row['servico_sugerido']} para mitigar gargalos operacionais. Como vocês ainda não contam com essa camada ativa no contrato, e considerando que mapeamos algumas instabilidades recentes no seu suporte com temas de {row['categoria_problema']}, gostaria de agendar um breve bate-papo de 10 minutos. Quero te apresentar o estudo de caso prático desse serviço no seu mercado para eliminar esses chamados de vez. Qual o melhor dia?"
"""
            scripts.append(script.strip())

        self.df_opps["script_vendas"] = scripts

    # ==========================================
    # ORQUESTRADOR DO PIPELINE
    # ==========================================
    def execute_pipeline(self):
        self.load_and_profile_data()
        self.clean_and_categorize()
        self.model_opportunities()
        self.score_opportunities()
        self.generate_sales_script()
        print("--- Pipeline executado com sucesso! ---")


# ==========================================
# EXEMPLO DE EXECUÇÃO DA BASE (Uso do Grupo)
# ==========================================
if __name__ == "__main__":
    # Substitua pelos caminhos reais das planilhas do seu trabalho acadêmico
    pipeline = SalesOpportunityPipeline(
        tickets_path="tickets.xlsx",
        clients_path="clientes.xlsx",
        output_dir="resultado/",
    )

    # Executa todo o fluxo de inteligência de dados de ponta a ponta
    # pipeline.execute_pipeline()
    pass