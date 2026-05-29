from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import pandas as pd
import plotly.express as px
import plotly.io as pio
import os

app = FastAPI()

# Credenciais de acesso
USER_EMAIL = "rodrigo.cti@senai.com"
USER_PASSWORD = "cti134"

# Estado em memória para o Kanban persistir durante a sessão
KANBAN_STATE = {}

class KanbanUpdate(BaseModel):
    codcli: str
    nova_coluna: str

# --- TEMPLATE HTML DA TELA DE LOGIN ---
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Entrar | Motor de Oportunidades B2B</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght=300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>body { font-family: 'Inter', sans-serif; }</style>
</head>
<body class="bg-slate-950 flex items-center justify-center min-h-screen bg-gradient-to-tr from-slate-950 via-slate-900 to-blue-950 text-slate-100 antialiased">
    <div class="w-full max-w-md p-4">
        <div class="bg-slate-900/80 border border-slate-800 backdrop-blur-xl p-8 rounded-2xl shadow-2xl relative overflow-hidden">
            <div class="absolute -top-24 -right-24 w-48 h-48 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>
            
            <div class="mb-8">
                <div class="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center mb-4 shadow-lg shadow-blue-600/30">
                    <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                </div>
                <h2 class="text-2xl font-bold tracking-tight text-white">Acesse a plataforma</h2>
                <p class="text-sm text-slate-400 mt-1">Insira suas credenciais do ecossistema CTI</p>
            </div>

            <form action="/login" method="POST" class="space-y-5">
                <div>
                    <label class="block text-slate-300 text-xs font-semibold tracking-wider uppercase mb-1.5">E-mail Corporativo</label>
                    <input type="email" name="username" placeholder="seu.nome@senai.com" required class="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm transition text-slate-200 placeholder-slate-600">
                </div>
                <div>
                    <div class="flex justify-between items-center mb-1.5">
                        <label class="block text-slate-300 text-xs font-semibold tracking-wider uppercase">Senha de Acesso</label>
                    </div>
                    <input type="password" name="password" placeholder="••••••••" required class="w-full px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm transition text-slate-200 placeholder-slate-600">
                </div>
                <button type="submit" class="w-full bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-white font-semibold py-3 px-4 rounded-xl transition duration-150 text-sm shadow-xl shadow-blue-600/10 mt-2">
                    Entrar no Painel
                </button>
            </form>
        </div>
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard | Motor de Oportunidades</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        .kanban-zone::-webkit-scrollbar { width: 4px; }
        .kanban-zone::-webkit-scrollbar-thumb { background-color: #1e293b; border-radius: 4px; }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col antialiased">
    
    <header class="border-b border-slate-900 bg-slate-900/20 backdrop-blur-md sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <div class="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-md shadow-blue-600/20">
                    <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                </div>
                <span class="font-bold tracking-tight text-white text-sm">CTI Motor B2B</span>
            </div>
            <div class="flex items-center gap-4">
                <button onclick="switchTab('analytics')" class="text-xs font-semibold px-3 py-2 rounded-lg bg-slate-900 text-blue-400 border border-slate-800" id="btn-tab-analytics">Dados & Insights</button>
                <button onclick="switchTab('kanban')" class="text-xs font-semibold px-3 py-2 rounded-lg text-slate-400 hover:text-white" id="btn-tab-kanban">Funil Kanban</button>
                <a href="/" class="text-xs text-slate-500 hover:text-rose-400 transition">Sair</a>
            </div>
        </div>
    </header>

    <main id="tab-content-analytics" class="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200">
                <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Oportunidades Filtradas</p>
                <p class="text-3xl font-bold text-white tracking-tight mt-2">{{KPI_TOTAL}}</p>
            </div>
            <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200">
                <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Prioridade Máxima (Hot)</p>
                <div class="flex justify-between items-baseline mt-2">
                    <p class="text-3xl font-bold text-rose-500 tracking-tight">{{KPI_ALTA}}</p>
                    <span class="text-[10px] font-bold bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded-full border border-rose-500/20">Ação Comercial</span>
                </div>
            </div>
            <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200">
                <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Total Histórico Analisado</p>
                <p class="text-3xl font-bold text-slate-300 tracking-tight mt-2">{{KPI_TICKETS}}</p>
            </div>
            <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200">
                <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Maior Demanda Comercial</p>
                <p class="text-base font-bold text-blue-400 mt-3 truncate tracking-tight">{{KPI_TOP}}</p>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl flex flex-col">
                <div class="mb-4">
                    <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Frequência por Categoria do Problema</h3>
                    <p class="text-xs text-slate-500 mt-0.5">Distribuição baseada no diagnóstico NLP dos chamados</p>
                </div>
                <div class="w-full flex-grow">{{GRAFICO_1}}</div>
            </div>
            <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl flex flex-col">
                <div class="mb-4">
                    <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Distribuição por Score de Urgência</h3>
                    <p class="text-xs text-slate-500 mt-0.5">Fatias geradas a partir da fórmula de multiplicação peso x volumetria</p>
                </div>
                <div class="w-full flex-grow">{{GRAFICO_2}}</div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            <div class="lg:col-span-2 bg-slate-900/20 border border-slate-900 rounded-xl overflow-hidden">
                <div class="p-4 border-b border-slate-900 flex flex-col sm:flex-row gap-3 justify-between items-center">
                    <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="Buscar por ID ou segmento..." class="bg-slate-950 border border-slate-800 text-xs px-3 py-2 rounded-lg w-full sm:max-w-xs focus:outline-none focus:border-blue-500 text-slate-300">
                    <select id="priorityFilter" onchange="filterTable()" class="bg-slate-950 border border-slate-800 text-xs px-3 py-2 rounded-lg focus:outline-none focus:border-blue-500 text-slate-400 w-full sm:w-auto">
                        <option value="">Todas as Prioridades</option>
                        <option value="ALTA">ALTA</option>
                        <option value="MÉDIA">MÉDIA</option>
                        <option value="BAIXA">BAIXA</option>
                    </select>
                </div>
                <div class="overflow-x-auto max-h-[400px]">
                    <table id="leadsTable" class="w-full text-left border-collapse">
                        <thead>
                            <tr class="border-b border-slate-900 bg-slate-900/40 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                                <th class="px-5 py-3">CodCli</th>
                                <th class="px-5 py-3">Segmento</th>
                                <th class="px-5 py-3">Categoria</th>
                                <th class="px-5 py-3">Serviço Sugerido</th>
                                <th class="px-5 py-3 text-right">Prioridade</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-900 text-xs text-slate-300 bg-slate-950/10">
                            {{TABLE_ROWS}}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="bg-slate-900/30 border border-slate-900 rounded-xl p-5 sticky top-24">
                <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Script de Vendas Personalizado</h3>
                
                <div id="scriptPlaceholder" class="bg-slate-950/50 border border-slate-900/80 rounded-xl p-5 text-center py-24 text-slate-600 border-dashed flex flex-col justify-center items-center h-[320px]">
                    <svg class="w-8 h-8 mx-auto mb-2 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"></path></svg>
                    <p class="text-xs font-medium px-4">Selecione qualquer cliente na tabela ao lado para extrair o script pronto de vendas da IA.</p>
                </div>
                
                <div id="scriptContentBox" class="hidden space-y-4">
                    <div class="flex flex-wrap gap-2 justify-between items-center bg-slate-950 p-3 rounded-lg border border-slate-900">
                        <div>
                            <p class="text-[10px] text-slate-500 font-bold uppercase" id="viewId">Lead #</p>
                            <p class="text-xs font-medium text-yellow-500" id="viewSegm">-</p>
                        </div>
                        <div class="text-right">
                            <p class="text-[10px] text-slate-500 font-bold uppercase" id="viewCat">Categoria</p>
                            <p class="text-xs font-medium text-blue-400 truncate max-w-[150px]" id="viewSug">-</p>
                        </div>
                    </div>
                    <textarea id="scriptBodyText" readonly class="w-full h-48 bg-slate-950 border border-slate-900 rounded-xl p-3 text-xs text-slate-300 font-mono focus:outline-none resize-none"></textarea>
                    <button onclick="copyToClipboard()" class="w-full bg-slate-900 hover:bg-slate-800 text-slate-200 text-xs font-medium py-2.5 px-4 rounded-lg border border-slate-800 transition">
                        Copiar Script
                    </button>
                    <p id="copyAlert" class="text-[11px] text-emerald-400 text-center hidden">✓ Copiado para a área de transferência!</p>
                </div>
            </div>
        </div>
    </main>

    <main id="tab-content-kanban" class="hidden flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-900 pb-4">
            <div>
                <h1 class="text-xl font-extrabold tracking-tight text-white">Painel de Chamados & Negócios</h1>
                <p class="text-xs text-slate-400 mt-0.5">Gerencie o pipeline comercial arrastando os cards entre as etapas do funil.</p>
            </div>
            <input type="text" id="kanbanSearchInput" onkeyup="filterKanban()" placeholder="Filtrar por ID ou serviço..." class="bg-slate-950 border border-slate-800 text-xs px-3 py-2 rounded-lg focus:outline-none focus:border-blue-500 text-slate-300 w-full sm:max-w-xs">
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-start">
            
            <div class="bg-slate-900/20 border border-slate-900 rounded-xl p-4 flex flex-col h-[580px]">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-blue-500"></span> A Fazer Proposta
                    </h3>
                    <span class="bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-bold px-2 py-0.5 rounded-full" id="count-afazer">0</span>
                </div>
                <div id="col-afazer" data-status="afazer" class="kanban-zone flex-grow space-y-3 overflow-y-auto pb-4">
                    {{KANBAN_AFAZER}}
                </div>
            </div>

            <div class="bg-slate-900/20 border border-slate-900 rounded-xl p-4 flex flex-col h-[580px]">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-amber-500"></span> Em Negociação
                    </h3>
                    <span class="bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-bold px-2 py-0.5 rounded-full" id="count-aguardando">0</span>
                </div>
                <div id="col-aguardando" data-status="aguardando" class="kanban-zone flex-grow space-y-3 overflow-y-auto pb-4">
                    {{KANBAN_AGUARDANDO}}
                </div>
            </div>

            <div class="bg-slate-900/20 border border-slate-900 rounded-xl p-4 flex flex-col h-[580px]">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-rose-500"></span> Proposta Recusada
                    </h3>
                    <span class="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[10px] font-bold px-2 py-0.5 rounded-full" id="count-recusado">0</span>
                </div>
                <div id="col-recusado" data-status="recusado" class="kanban-zone flex-grow space-y-3 overflow-y-auto pb-4">
                    {{KANBAN_RECUSADO}}
                </div>
            </div>

            <div class="bg-slate-900/20 border border-slate-900 rounded-xl p-4 flex flex-col h-[580px]">
                <div class="flex justify-between items-center mb-3">
                    <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-500"></span> Ganho / Fechado
                    </h3>
                    <span class="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded-full" id="count-aceito">0</span>
                </div>
                <div id="col-aceito" data-status="aceito" class="kanban-zone flex-grow space-y-3 overflow-y-auto pb-4">
                    {{KANBAN_ACEITO}}
                </div>
            </div>

        </div>
    </main>

    <script>
        function switchTab(tab) {
            if (tab === 'analytics') {
                document.getElementById('tab-content-analytics').classList.remove('hidden');
                document.getElementById('tab-content-kanban').classList.add('hidden');
                document.getElementById('btn-tab-analytics').className = "text-xs font-semibold px-3 py-2 rounded-lg bg-slate-900 text-blue-400 border border-slate-800";
                document.getElementById('btn-tab-kanban').className = "text-xs font-semibold px-3 py-2 rounded-lg text-slate-400 hover:text-white";
            } else {
                document.getElementById('tab-content-analytics').classList.add('hidden');
                document.getElementById('tab-content-kanban').classList.remove('hidden');
                document.getElementById('btn-tab-kanban').className = "text-xs font-semibold px-3 py-2 rounded-lg bg-slate-900 text-blue-400 border border-slate-800";
                document.getElementById('btn-tab-analytics').className = "text-xs font-semibold px-3 py-2 rounded-lg text-slate-400 hover:text-white";
                updateKanbanCounters();
            }
        }

        function filterTable() {
            const searchVal = document.getElementById('searchInput').value.toLowerCase().trim();
            const filterVal = document.getElementById('priorityFilter').value;
            const rows = document.querySelectorAll('#leadsTable tbody tr');

            rows.forEach(row => {
                const id = row.getAttribute('data-id').toLowerCase();
                const seg = row.getAttribute('data-segmento').toLowerCase();
                const prio = row.getAttribute('data-priority');
                
                const matchesSearch = id.includes(searchVal) || seg.includes(searchVal);
                const matchesPrio = filterVal === "" || prio === filterVal;

                if (matchesSearch && matchesPrio) {
                    row.classList.remove('hidden');
                } else {
                    row.classList.add('hidden');
                }
            });
        }

        function filterKanban() {
            const searchVal = document.getElementById('kanbanSearchInput').value.toLowerCase().trim();
            const cards = document.querySelectorAll('.kanban-zone > div');
            
            cards.forEach(card => {
                const text = card.textContent.toLowerCase();
                if (text.includes(searchVal)) {
                    card.classList.remove('hidden');
                } else {
                    card.classList.add('hidden');
                }
            });
            updateKanbanCounters();
        }

        function loadLeadScript(row) {
            document.querySelectorAll('#leadsTable tbody tr').forEach(r => r.classList.remove('bg-blue-600/10', 'border-l-2', 'border-blue-500'));
            row.classList.add('bg-blue-600/10', 'border-l-2', 'border-blue-500');

            const id = row.getAttribute('data-id');
            const segmento = row.getAttribute('data-segmento');
            const cat = row.getAttribute('data-cat');
            const sug = row.getAttribute('data-sug');
            const rawScript = row.querySelector('.hidden-script-source').textContent;

            document.getElementById('scriptPlaceholder').classList.add('hidden');
            document.getElementById('scriptContentBox').classList.remove('hidden');
            document.getElementById('copyAlert').classList.add('hidden');

            document.getElementById('viewId').textContent = "Lead #" + id;
            document.getElementById('viewSegm').textContent = segmento;
            document.getElementById('viewCat').textContent = cat;
            document.getElementById('viewSug').textContent = sug;
            document.getElementById('scriptBodyText').value = rawScript;
        }

        function copyToClipboard() {
            const txt = document.getElementById('scriptBodyText');
            txt.select();
            document.execCommand('copy');
            document.getElementById('copyAlert').classList.remove('hidden');
        }

        function updateKanbanCounters() {
            ['afazer', 'aguardando', 'recusado', 'aceito'].forEach(status => {
                const count = document.querySelectorAll(`#col-${status} > div:not(.hidden)`).length;
                document.getElementById(`count-${status}`).textContent = count;
            });
        }

        // --- SISTEMA DRAG AND DROP ---
        document.addEventListener('DOMContentLoaded', () => {
            const cards = document.querySelectorAll('.kanban-zone > div');
            const zones = document.querySelectorAll('.kanban-zone');

            cards.forEach(card => {
                card.addEventListener('dragstart', () => {
                    card.classList.add('opacity-50');
                    card.id = "dragging-card";
                });
                card.addEventListener('dragend', () => {
                    card.classList.remove('opacity-50');
                    card.removeAttribute('id');
                    updateKanbanCounters();
                });
            });

            zones.forEach(zone => {
                zone.addEventListener('dragover', (e) => {
                    e.preventDefault();
                });

                zone.addEventListener('drop', async (e) => {
                    e.preventDefault();
                    const card = document.getElementById('dragging-card');
                    if (card) {
                        zone.appendChild(card);
                        const codcli = card.getAttribute('data-id');
                        const nova_coluna = zone.getAttribute('data-status');
                        
                        // Sincroniza com a API do FastAPI
                        await fetch('/api/kanban/save', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ codcli, nova_coluna })
                        });
                    }
                });
            });
            updateKanbanCounters();
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def index():
    return LOGIN_HTML

@app.post("/login", response_class=HTMLResponse)
def login(username: str = Form(...), password: str = Form(...)):
    global KANBAN_STATE
    
    if username != USER_EMAIL or password != USER_PASSWORD:
        return "<h1 style='font-family:sans-serif; text-align:center; margin-top:50px; color:#ef4444;'>Credenciais Inválidas!</h1>"

    # Define o caminho padrão do arquivo ou fallback
    caminho_csv = os.path.join("output", "consolidado.csv")
    df = None
    if os.path.exists(caminho_csv):
        df = pd.read_csv(caminho_csv)
    else:
        # Criando dados mockados idênticos para não quebrar caso rode sem o arquivo físico inicial
        df = pd.DataFrame([
            {"codcli": "1001", "segmento": "Metalmecânico", "categoria_problema": "Manutenção Preventiva", "servico_sugerido": "Consultoria Lean", "prioridade_comercial": "ALTA", "script_vendas": "Olá, vimos sua necessidade em manutenção..."},
            {"codcli": "1002", "segmento": "Alimentos", "categoria_problema": "Automação", "servico_sugerido": "Eficiência Energética", "prioridade_comercial": "MÉDIA", "script_vendas": "Olá, reduzimos custos de energia em indústrias de alimentos..."}
        ])

    kpi_total = str(len(df))
    kpi_alta = str(len(df[df['prioridade_comercial'] == 'ALTA']))
    kpi_tickets = str(len(df))  # Modifique se houver coluna específica para volumetria
    kpi_top = str(df['servico_sugerido'].mode()[0]) if not df.empty else "Nenhum"

    # --- CRIAÇÃO DOS GRÁFICOS PLOTLY ---
    # Gráfico 1: Frequência de Categorias
    df_cat = df['categoria_problema'].value_counts().reset_index()
    df_cat.columns = ['categoria', 'quantidade']
    fig_freq = px.bar(df_cat, x='quantidade', y='categoria', orientation='h', template='plotly_dark')
    fig_freq.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10), height=220)
    html_g1 = pio.to_html(fig_freq, full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

    # Gráfico 2: Distribuição por Urgência (Prioridade)
    df_prio = df['prioridade_comercial'].value_counts().reset_index()
    df_prio.columns = ['prioridade', 'quantidade']
    fig_prio = px.pie(df_prio, values='quantidade', names='prioridade', hole=0.4, template='plotly_dark', color_discrete_sequence=px.colors.qualitative.Pastel)
    fig_prio.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', margin=dict(l=10, r=10, t=10, b=10), height=220)
    html_g2 = pio.to_html(fig_prio, full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

    # Alimentação dos estados padrão do Kanban
    for _, row in df.iterrows():
        cid = str(row['codcli'])
        if cid not in KANBAN_STATE:
            KANBAN_STATE[cid] = "afazer"

    table_rows = ""
    kanban_buffers = {"afazer": "", "aguardando": "", "recusado": "", "aceito": ""}
    
    for _, row in df.iterrows():
        cid = str(row['codcli'])
        prio = row['prioridade_comercial']
        segmento_txt = str(row['segmento']) if 'segmento' in df.columns and pd.notna(row['segmento']) else "Não Informado"
        
        badge_style = "bg-rose-500/10 text-rose-400 border border-rose-500/20" if prio == 'ALTA' else "bg-blue-500/10 text-blue-400 border border-blue-500/20" if prio == 'MÉDIA' else "bg-slate-500/10 text-slate-400 border border-slate-500/20"
        dot_color = "bg-rose-500" if prio == 'ALTA' else "bg-blue-500" if prio == 'MÉDIA' else "bg-slate-500"
        
        # Montagem da tabela
        table_rows += f"""
        <tr class="hover:bg-slate-900/40 cursor-pointer transition border-b border-slate-900" 
            data-priority="{prio}" data-id="{cid}" data-segmento="{segmento_txt}" data-cat="{row['categoria_problema']}" data-sug="{row['servico_sugerido']}"
            onclick="loadLeadScript(this)">
            <td class="px-5 py-3.5 font-bold text-white tracking-tight">{cid}</td>
            <td class="px-5 py-3.5 text-yellow-500 font-medium">{segmento_txt}</td>
            <td class="px-5 py-3.5 text-slate-400">{row['categoria_problema']}</td>
            <td class="px-5 py-3.5 text-slate-200 font-medium">{row['servico_sugerido']}</td>
            <td class="px-5 py-3.5 text-right">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-bold rounded-md {badge_style}">
                    <span class="w-1.5 h-1.5 rounded-full {dot_color}"></span>
                    {prio}
                </span>
                <div class="hidden hidden-script-source">{row['script_vendas']}</div>
            </td>
        </tr>
        """

        # Montagem dos cards Kanban
        card_html = f"""
        <div data-id="{cid}" draggable="true" class="bg-slate-950 border border-slate-800 hover:border-slate-700 p-3.5 rounded-xl shadow-md cursor-grab active:cursor-grabbing transition space-y-2">
            <div class="flex justify-between items-center">
                <span class="text-xs font-bold text-white">Cliente #{cid}</span>
                <span class="text-[10px] font-bold px-2 py-0.5 rounded {badge_style}">{prio}</span>
            </div>
            <p class="text-[11px] text-yellow-500 font-medium tracking-tight">🏢 {segmento_txt}</p>
            <div class="border-t border-slate-900 pt-2">
                <p class="text-[9px] text-slate-500 uppercase font-semibold">Solução Alvo:</p>
                <p class="text-xs text-slate-200 font-medium truncate">{row['servico_sugerido']}</p>
            </div>
        </div>
        """
        status_do_lead = KANBAN_STATE.get(cid, "afazer")
        kanban_buffers[status_do_lead] += card_html

    # Injeção dos dados no template final
    page = DASHBOARD_HTML
    page = page.replace('{{KPI_TOTAL}}', kpi_total)
    page = page.replace('{{KPI_ALTA}}', kpi_alta)
    page = page.replace('{{KPI_TICKETS}}', kpi_tickets)
    page = page.replace('{{KPI_TOP}}', kpi_top)
    page = page.replace('{{GRAFICO_1}}', html_g1)
    page = page.replace('{{GRAFICO_2}}', html_g2)
    page = page.replace('{{TABLE_ROWS}}', table_rows)
    
    page = page.replace('{{KANBAN_AFAZER}}', kanban_buffers["afazer"])
    page = page.replace('{{KANBAN_AGUARDANDO}}', kanban_buffers["aguardando"])
    page = page.replace('{{KANBAN_RECUSADO}}', kanban_buffers["recusado"])
    page = page.replace('{{KANBAN_ACEITO}}', kanban_buffers["aceito"])

    return page

@app.post("/api/kanban/save")
def save_kanban_position(data: KanbanUpdate):
    if data.nova_coluna not in ["afazer", "aguardando", "recusado", "aceito"]:
        raise HTTPException(status_code=400, detail="Etapa do funil inválida")
    KANBAN_STATE[data.codcli] = data.nova_coluna
    return JSONResponse(content={"status": "success"})