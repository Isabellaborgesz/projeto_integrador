from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os

app = FastAPI()

# Credenciais diretas para máxima compatibilidade na nuvem da Vercel
USER_EMAIL = "rodrigo.cti@senai.com"
USER_PASSWORD = "cti134"

# --- TEMPLATE HTML DA TELA DE LOGIN ---
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Login - Motor de Oportunidades</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 flex items-center justify-center h-screen">
    <div class="bg-white p-8 rounded-lg shadow-md w-96">
        <h2 class="text-2xl font-bold mb-6 text-center text-gray-800">🎯 Sistema B2B</h2>
        <form action="/login" method="POST">
            <div class="mb-4">
                <label class="block text-gray-700 text-sm font-bold mb-2">E-mail</label>
                <input type="email" name="username" required class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <div class="mb-6">
                <label class="block text-gray-700 text-sm font-bold mb-2">Senha</label>
                <input type="password" name="password" required class="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500">
            </div>
            <button type="submit" class="w-full bg-blue-600 text-white font-bold py-2 px-4 rounded-lg hover:bg-blue-700 transition duration-200">Entrar</button>
        </form>
    </div>
</body>
</html>
"""

# --- TEMPLATE HTML DO DASHBOARD ---
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Dashboard de Oportunidades B2B</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 p-6 font-sans">
    <div class="max-w-7xl mx-auto">
        <div class="flex justify-between items-center mb-8 bg-white p-6 rounded-xl shadow-sm">
            <div>
                <h1 class="text-3xl font-bold text-gray-900">🎯 Dashboard de Oportunidades de Vendas B2B</h1>
                <p class="text-gray-600">Identificação automática de Cross-Sell e Up-Sell baseada em chamados de suporte técnico.</p>
            </div>
            <a href="/" class="bg-red-500 text-white px-4 py-2 rounded-lg font-bold hover:bg-red-600 transition">Sair</a>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-blue-500">
                <p class="text-sm text-gray-500 font-semibold uppercase">Total de Oportunidades</p>
                <p class="text-2xl font-bold text-gray-800">{{KPI_TOTAL}}</p>
            </div>
            <div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-red-500">
                <p class="text-sm text-gray-500 font-semibold uppercase">Alta Prioridade</p>
                <p class="text-2xl font-bold text-gray-800">{{KPI_ALTA}}</p>
            </div>
            <div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-green-500">
                <p class="text-sm text-gray-500 font-semibold uppercase">Tickets Analisados</p>
                <p class="text-2xl font-bold text-gray-800">{{KPI_TICKETS}}</p>
            </div>
            <div class="bg-white p-6 rounded-xl shadow-sm border-l-4 border-purple-500">
                <p class="text-sm text-gray-500 font-semibold uppercase">Top Serviço Recomendado</p>
                <p class="text-xl font-bold text-gray-800">{{KPI_TOP}}</p>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            <div class="bg-white p-4 rounded-xl shadow-sm">{{GRAFICO_1}}</div>
            <div class="bg-white p-4 rounded-xl shadow-sm">{{GRAFICO_2}}</div>
        </div>

        <div class="bg-white p-6 rounded-xl shadow-sm mb-8">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-xl font-bold text-gray-800">Lista de Clientes para Abordagem Comercial</h3>
                <div>
                    <label class="text-sm font-semibold text-gray-600 mr-2">Filtrar por Prioridade:</label>
                    <select id="priorityFilter" onchange="filterTable()" class="border rounded-lg p-2 bg-gray-50 focus:outline-none">
                        <option value="TODOS">TODOS</option>
                        <option value="ALTA">ALTA</option>
                        <option value="MÉDIA">MÉDIA</option>
                        <option value="BAIXA">BAIXA</option>
                    </select>
                </div>
            </div>
            <div class="overflow-x-auto rounded-lg border border-gray-200">
                <table class="min-w-full divide-y divide-gray-200" id="leadsTable">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase">CodCli</th>
                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase">Categoria Problema</th>
                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase">Qtd Tickets</th>
                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase">Serviço Sugerido</th>
                            <th class="px-6 py-3 text-left text-xs font-bold text-gray-500 uppercase">Prioridade</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        {{TABLE_ROWS}}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="bg-white p-6 rounded-xl shadow-sm">
            <h3 class="text-xl font-bold text-gray-800 mb-4">Scripts Gerados para Abordagem</h3>
            <div class="space-y-4">
                {{SCRIPTS_EXPANDERS}}
            </div>
        </div>
    </div>

    <script>
        function filterTable() {
            const val = document.getElementById('priorityFilter').value;
            const rows = document.querySelectorAll('#leadsTable tbody tr');
            rows.forEach(row => {
                const priority = row.getAttribute('data-priority');
                if(val === 'TODOS' || priority === val) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return LOGIN_HTML

@app.post("/login", response_class=HTMLResponse)
def login(username: str = Form(...), password: str = Form(...)):
    if username != USER_EMAIL or password != USER_PASSWORD:
        erro_msg = "<div class='bg-red-100 text-red-700 p-3 rounded-lg mb-4 text-center text-sm font-semibold'>Usuário ou senha incorretos.</div>"
        return LOGIN_HTML.replace("", erro_msg)
    
    # --- CARREGAMENTO DE DADOS DOS EXCEL/CSV ---
    caminho_xlsx = os.path.join("output", "oportunidades.xlsx")
    caminho_csv = os.path.join("output", "oportunidades.csv")
    
    df = None
    if os.path.exists(caminho_xlsx):
        df = pd.read_excel(caminho_xlsx)
    elif os.path.exists(caminho_csv):
        df = pd.read_csv(caminho_csv)
        
    if df is None or df.empty:
        return "<h1>Erro: Arquivo 'oportunidades' não encontrado na pasta 'output'. Execute o pipeline primeiro!</h1>"
        
    # --- CÁLCULO DOS KPIS ---
    kpi_total = str(len(df))
    kpi_alta = str(len(df[df['prioridade_comercial'] == 'ALTA']))
    kpi_tickets = str(df['qtd_tickets'].sum())
    kpi_top = str(df['servico_sugerido'].mode()[0]) if not df.empty else "N/A"

    # --- GERAÇÃO DOS GRÁFICOS DO PLOTLY PARA HTML ---
    fig_cat = px.bar(df['categoria_problema'].value_counts().reset_index(), 
                     x='categoria_problema', y='count', color='categoria_problema',
                     title="Oportunidades por Categoria de Problema")
    fig_cat.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    html_g1 = pio.to_html(fig_cat, full_html=False, include_plotlyjs='cdn')

    fig_prio = px.pie(df, names='prioridade_comercial', hole=0.4, title="Distribuição de Prioridade Comercial",
                      color='prioridade_comercial',
                      color_discrete_map={'ALTA':'#EF4444', 'MÉDIA':'#F59E0B', 'BAIXA':'#10B981'})
    fig_prio.update_layout(margin=dict(l=20, r=20, t=40, b=20))
    html_g2 = pio.to_html(fig_prio, full_html=False, include_plotlyjs='cdn')

    # --- CONSTRUÇÃO DAS LINHAS DA TABELA ---
    table_rows = ""
    for _, row in df.iterrows():
        table_rows += f"""
        <tr class="hover:bg-gray-50 data-row" data-priority="{row['prioridade_comercial']}">
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">{row['codcli']}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row['categoria_problema']}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row['qtd_tickets']}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{row['servico_sugerido']}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm">
                <span class="px-2.5 py-1 text-xs font-bold rounded-full 
                    {'bg-red-100 text-red-800' if row['prioridade_comercial'] == 'ALTA' else 'bg-amber-100 text-amber-800' if row['prioridade_comercial'] == 'MÉDIA' else 'bg-green-100 text-green-800'}">
                    {row['prioridade_comercial']}
                </span>
            </td>
        </tr>
        """

    # --- CONSTRUÇÃO DOS EXPANDERS NATIVOS (HTML DETAILS/SUMMARY) ---
    expanders = ""
    for _, row in df.iterrows():
        expanders += f"""
        <details class="bg-gray-50 border border-gray-200 rounded-lg p-4 hover:bg-gray-100 transition duration-150 group">
            <summary class="font-bold text-gray-700 cursor-pointer list-none flex justify-between items-center select-none">
                <span>Lead ID: {row['codcli']} - <span class="text-blue-600">{row['servico_sugerido']}</span> (Prioridade: {row['prioridade_comercial']})</span>
                <span class="text-gray-400 group-open:rotate-180 transition-transform">▼</span>
            </summary>
            <div class="mt-4 p-4 bg-white border border-gray-100 rounded-lg text-gray-600 font-mono text-sm whitespace-pre-wrap">
                {row['script_vendas']}
            </div>
        </details>
        """

    # --- INJEÇÃO DE DADOS NO TEMPLATE DO DASHBOARD ---
    page = DASHBOARD_HTML
    page = page.replace("{{KPI_TOTAL}}", kpi_total)
    page = page.replace("{{KPI_ALTA}}", kpi_alta)
    page = page.replace("{{KPI_TICKETS}}", kpi_tickets)
    page = page.replace("{{KPI_TOP}}", kpi_top)
    page = page.replace("{{GRAFICO_1}}", html_g1)
    page = page.replace("{{GRAFICO_2}}", html_g2)
    page = page.replace("{{TABLE_ROWS}}", table_rows)
    page = page.replace("{{SCRIPTS_EXPANDERS}}", expanders)

    return page