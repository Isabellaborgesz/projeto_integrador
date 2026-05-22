from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os

app = FastAPI()

# Credenciais de acesso
USER_EMAIL = "rodrigo.cti@senai.com"
USER_PASSWORD = "cti134"

# 🏢 INSIRA A URL DA SUA LOGO AQUI (Pode ser um link do Imgur, GitHub ou link direto da imagem)
LOGO_URL = "https://ibb.co/xKvML26Q" 

# --- TEMPLATE HTML DA TELA DE LOGIN ---
LOGIN_HTML = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Login - Motor de Oportunidades</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 flex items-center justify-center h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900">
    <div class="bg-white/95 backdrop-blur-md p-8 rounded-2xl shadow-2xl w-96 border border-slate-800/20">
        <div class="flex flex-col items-center mb-6">
            <img src="{LOGO_URL}" alt="Logo" class="w-16 h-16 object-cover rounded-xl mb-3 shadow-md">
            <h2 class="text-2xl font-extrabold text-slate-800 tracking-tight">Motor de Vendas B2B</h2>
            <p class="text-xs text-slate-500 mt-1">Insira suas credenciais corporativas</p>
        </div>
        <form action="/login" method="POST" class="space-y-4">
            <div>
                <label class="block text-slate-700 text-xs font-bold uppercase tracking-wider mb-1">E-mail Corporativo</label>
                <input type="email" name="username" required class="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-800 transition text-sm">
            </div>
            <div class="mb-2">
                <label class="block text-slate-700 text-xs font-bold uppercase tracking-wider mb-1">Senha de Acesso</label>
                <input type="password" name="password" required class="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-800 transition text-sm">
            </div>
            <button type="submit" class="w-full bg-blue-800 text-white font-bold py-3 px-4 rounded-xl hover:bg-blue-900 active:scale-[0.99] transition duration-150 text-sm shadow-lg shadow-blue-900/20">Entrar no Sistema</button>
        </form>
    </div>
</body>
</html>
"""

# --- TEMPLATE HTML DO DASHBOARD ---
DASHBOARD_HTML = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>Dashboard de Oportunidades B2B</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 min-h-screen p-4 md:p-6 font-sans antialiased text-slate-800">
    <div class="max-w-7xl mx-auto space-y-6">
        
        <div class="flex flex-col md:flex-row justify-between items-center bg-blue-900 text-white p-6 rounded-2xl shadow-xl shadow-blue-900/10 gap-4 bg-gradient-to-r from-blue-900 via-indigo-950 to-blue-900">
            <div class="flex items-center gap-4 text-center md:text-left">
                <img src="{LOGO_URL}" alt="Logo" class="w-14 h-14 object-cover rounded-xl border-2 border-white/20 bg-white shadow-inner">
                <div>
                    <h1 class="text-2xl md:text-3xl font-black tracking-tight">Motor de Oportunidades B2B</h1>
                    <p class="text-blue-200 text-xs md:text-sm font-medium mt-0.5">Identificação de Cross-Sell e Up-Sell baseada em chamados técnicos</p>
                </div>
            </div>
            <div class="flex items-center gap-4">
                <span class="text-xs font-semibold bg-white/10 px-3 py-1.5 rounded-full border border-white/10">Olá, Rodrigo</span>
                <a href="/" class="bg-red-500 hover:bg-red-600 px-4 py-2 rounded-xl text-xs font-bold transition shadow-md">Sair</a>
            </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
                <p class="text-xs text-slate-400 font-bold uppercase tracking-wider">Total de Oportunidades</p>
                <p class="text-3xl font-black text-blue-900 mt-2">"{{KPI_TOTAL}}"</p>
            </div>
            <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
                <p class="text-xs text-slate-400 font-bold uppercase tracking-wider">Alta Prioridade (Hot)</p>
                <div class="flex justify-between items-end mt-2">
                    <p class="text-3xl font-black text-rose-600">"{{KPI_ALTA}}"</p>
                    <span class="text-[10px] font-bold bg-rose-50 text-rose-700 px-2 py-0.5 rounded-full mb-1">Ação Imediata</span>
                </div>
            </div>
            <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
                <p class="text-xs text-slate-400 font-bold uppercase tracking-wider">Tickets Analisados</p>
                <p class="text-3xl font-black text-slate-700 mt-2">"{{KPI_TICKETS}}"</p>
            </div>
            <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
                <p class="text-xs text-slate-400 font-bold uppercase tracking-wider">Top Serviço Sugerido</p>
                <p class="text-lg font-black text-indigo-950 mt-2 truncate">"{{KPI_TOP}}"</p>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-100">
                <h3 class="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">Volume por Categoria de Chamado</h3>
                <div class="w-full">"{{GRAFICO_1}}"</div>
            </div>
            <div class="bg-white p-5 rounded-2xl shadow-sm border border-slate-100">
                <h3 class="text-sm font-bold text-slate-500 uppercase tracking-wider mb-4">Urgência Comercial dos Leads</h3>
                <div class="w-full">"{{GRAFICO_2}}"</div>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            <div class="p-6 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-50/50">
                <div>
                    <h3 class="text-lg font-bold text-slate-800">Lista de Clientes para Prospecção</h3>
                    <p class="text-xs text-slate-500">Ordene ou filtre os leads identificados pelo motor</p>
                </div>
                <div class="flex items-center gap-2">
                    <label class="text-xs font-bold text-slate-500 uppercase tracking-wide">Filtro:</label>
                    <select id="priorityFilter" onchange="filterTable()" class="border border-slate-200 rounded-xl p-2.5 bg-white text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-blue-800 transition">
                        <option value="TODOS">Mostrar Todos</option>
                        <option value="ALTA">Apenas ALTA</option>
                        <option value="MÉDIA">Apenas MÉDIA</option>
                        <option value="BAIXA">Apenas BAIXA</option>
                    </select>
                </div>
            </div>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-slate-200" id="leadsTable">
                    <thead class="bg-slate-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Cód. Cliente</th>
                            <th class="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Origem do Problema</th>
                            <th class="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Tickets</th>
                            <th class="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Solução Recomendada</th>
                            <th class="px-6 py-3 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Prioridade</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-slate-100 text-sm">
                        "{{TABLE_ROWS}}"
                    </tbody>
                </table>
            </div>
        </div>

        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
            <div class="mb-4">
                <h3 class="text-lg font-bold text-slate-800">Scripts Comerciais customizados por IA</h3>
                <p class="text-xs text-slate-500">Abordagens sob medida prontas para o time de vendas utilizar</p>
            </div>
            <div class="space-y-3">
                "{{SCRIPTS_EXPANDERS}}"
            </div>
        </div>
    </div>

    <script>
        function filterTable() {{
            const val = document.getElementById('priorityFilter').value;
            const rows = document.querySelectorAll('#leadsTable tbody tr');
            rows.forEach(row => {{
                const priority = row.getAttribute('data-priority');
                if(val === 'TODOS' || priority === val) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }});
        }}
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
        erro_msg = "<div class='bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl mb-4 text-center text-xs font-semibold shadow-sm'>E-mail corporativo ou senha inválidos.</div>"
        return LOGIN_HTML.replace("", erro_msg)
    
    caminho_xlsx = os.path.join("output", "oportunidades.xlsx")
    caminho_csv = os.path.join("output", "oportunidades.csv")
    
    df = None
    if os.path.exists(caminho_xlsx):
        df = pd.read_excel(caminho_xlsx)
    elif os.path.exists(caminho_csv):
        df = pd.read_csv(caminho_csv)
        
    if df is None or df.empty:
        return "<h1 style='font-family:sans-serif; text-align:center; margin-top:50px;'>Erro: O arquivo consolidado não foi localizado na pasta 'output'.</h1>"
        
    kpi_total = str(len(df))
    kpi_alta = str(len(df[df['prioridade_comercial'] == 'ALTA']))
    kpi_tickets = str(df['qtd_tickets'].sum())
    kpi_top = str(df['servico_sugerido'].mode()[0]) if not df.empty else "N/A"

    # --- GRAFICO 1: Customizado com Tons Azuis de Marca ---
    fig_cat = px.bar(df['categoria_problema'].value_counts().reset_index(), 
                     x='categoria_problema', y='count',
                     labels={'categoria_problema': 'Categoria', 'count': 'Chamados'})
    
    # Customizando as cores do gráfico para combinar com tons de azul escuro e slate
    fig_cat.update_traces(marker_color='#1E3A8A', marker_line_color='#1E293B', marker_line_width=1, opacity=0.9)
    fig_cat.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=300,
        xaxis=dict(showgrid=False, title=""), yaxis=dict(showgrid=True, gridcolor='#F1F5F9', title="")
    )
    html_g1 = pio.to_html(fig_cat, full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

    # --- GRAFICO 2: Pizza Customizada ---
    fig_prio = px.pie(df, names='prioridade_comercial', hole=0.55,
                      color='prioridade_comercial',
                      color_discrete_map={'ALTA':'#E11D48', 'MÉDIA':'#1E3A8A', 'BAIXA':'#475569'})
    fig_prio.update_traces(textposition='inside', textinfo='percent+label')
    fig_prio.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=10, b=0), height=300, showlegend=False
    )
    html_g2 = pio.to_html(fig_prio, full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

    # --- LINHAS DA TABELA COM FORMATAÇÃO CLEAN ---
    table_rows = ""
    for _, row in df.iterrows():
        prio = row['prioridade_comercial']
        badge_style = "bg-rose-50 text-rose-700 border border-rose-200" if prio == 'ALTA' else "bg-blue-50 text-blue-800 border border-blue-200" if prio == 'MÉDIA' else "bg-slate-50 text-slate-600 border border-slate-200"
        
        table_rows += f"""
        <tr class="hover:bg-slate-50/80 transition" data-priority="{prio}">
            <td class="px-6 py-4 whitespace-nowrap text-slate-900 font-bold tracking-tight">{row['codcli']}</td>
            <td class="px-6 py-4 whitespace-nowrap text-slate-600">{row['categoria_problema']}</td>
            <td class="px-6 py-4 whitespace-nowrap text-slate-700 font-semibold">{row['qtd_tickets']}</td>
            <td class="px-6 py-4 whitespace-nowrap text-slate-900 font-medium">{row['servico_sugerido']}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2.5 py-1 text-xs font-bold rounded-lg {badge_style}">
                    {prio}
                </span>
            </td>
        </tr>
        """

    # --- ACORDEONS RETRÁTEIS CORPORATIVOS ---
    expanders = ""
    for _, row in df.iterrows():
        prio = row['prioridade_comercial']
        dot_color = "bg-rose-500" if prio == 'ALTA' else "bg-blue-700" if prio == 'MÉDIA' else "bg-slate-400"
        
        expanders += f"""
        <details class="bg-white border border-slate-200/80 rounded-xl overflow-hidden shadow-sm group">
            <summary class="font-bold text-slate-700 p-4 cursor-pointer list-none flex justify-between items-center select-none bg-slate-50/50 hover:bg-slate-50 transition">
                <div class="flex items-center gap-2.5 text-sm md:text-base">
                    <span class="w-2 h-2 rounded-full {dot_color}"></span>
                    <span>Lead {row['codcli']} <span class="text-slate-400 font-normal">|</span> Sugestão: <span class="text-blue-950 font-extrabold">{row['servico_sugerido']}</span></span>
                </div>
                <span class="text-slate-400 group-open:rotate-180 transition duration-200 text-xs">▼</span>
            </summary>
            <div class="p-5 bg-white border-t border-slate-100 text-slate-600 text-sm leading-relaxed whitespace-pre-wrap font-mono bg-slate-50/30">
                {row['script_vendas']}
            </div>
        </details>
        """

    page = DASHBOARD_HTML
    page = page.replace('""{{KPI_TOTAL}}""', kpi_total).replace('"{{KPI_TOTAL}}"', kpi_total)
    page = page.replace('""{{KPI_ALTA}}""', kpi_alta).replace('"{{KPI_ALTA}}"', kpi_alta)
    page = page.replace('""{{KPI_TICKETS}}""', kpi_tickets).replace('"{{KPI_TICKETS}}"', kpi_tickets)
    page = page.replace('""{{KPI_TOP}}""', kpi_top).replace('"{{KPI_TOP}}"', kpi_top)
    page = page.replace('""{{GRAFICO_1}}""', html_g1).replace('"{{GRAFICO_1}}"', html_g1)
    page = page.replace('""{{GRAFICO_2}}""', html_g2).replace('"{{GRAFICO_2}}"', html_g2)
    page = page.replace('""{{TABLE_ROWS}}""', table_rows).replace('"{{TABLE_ROWS}}"', table_rows)
    page = page.replace('""{{SCRIPTS_EXPANDERS}}""', expanders).replace('"{{SCRIPTS_EXPANDERS}}"', expanders)

    return page