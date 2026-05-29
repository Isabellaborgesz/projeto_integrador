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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
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
                    Entrar no Panel
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
    <title>Dashboard | Motor de Oportunidades B2B</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js"></script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #334155; }
    </style>
</head>
<body class="bg-slate-950 min-h-screen text-slate-100 antialiased font-sans">
    
    <div class="min-h-screen flex flex-col">
        
        <header class="border-b border-slate-900 bg-slate-950/50 backdrop-blur-md sticky top-0 z-50">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                <div class="flex items-center gap-8">
                    <div class="flex items-center gap-3">
                        <div class="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-md shadow-blue-600/20">
                            <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        </div>
                        <div>
                            <span class="text-sm font-bold tracking-tight text-white">Motor de Vendas B2B</span>
                        </div>
                    </div>
                    
                    <nav class="hidden md:flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-900">
                        <button onclick="switchTab('comercial')" id="btn-comercial" class="px-4 py-1.5 rounded-lg text-xs font-semibold transition bg-blue-600 text-white shadow-sm">
                            Painel Comercial
                        </button>
                        <button onclick="switchTab('novo-modulo')" id="btn-novo-modulo" class="px-4 py-1.5 rounded-lg text-xs font-semibold transition text-slate-400 hover:text-slate-200">
                            Kanbam 
                        </button>
                    </nav>
                </div>
                
                <div class="flex items-center gap-4">
                    <div class="text-right hidden sm:block">
                        <p class="text-xs font-semibold text-slate-200">Rodrigo</p>
                        <p class="text-[10px] text-slate-500 font-medium">Ecossistema CTI</p>
                    </div>
                    <a href="/" class="border border-slate-800 hover:bg-slate-900/60 text-slate-400 hover:text-rose-400 px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
                        Sair
                    </a>
                </div>
            </div>
        </header>

        <main id="tab-content-comercial" class="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
            
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900 pb-6">
                <div>
                    <h1 class="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">Geração Estratégica de Leads</h1>
                    <p class="text-sm text-slate-400 mt-1">Cruzamento de chamados de suporte técnico ativos com gaps contratuais comerciais.</p>
                </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Oportunidades Filtradas</p>
                    <p class="text-3xl font-bold text-white tracking-tight mt-2">"{{KPI_TOTAL}}"</p>
                </div>
                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Prioridade Máxima (Hot)</p>
                    <div class="flex justify-between items-baseline mt-2">
                        <p class="text-3xl font-bold text-rose-500 tracking-tight">"{{KPI_ALTA}}"</p>
                        <span class="text-[10px] font-bold bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded-full border border-rose-500/20">Ação Comercial</span>
                    </div>
                </div>
                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Total Histórico Analisado</p>
                    <p class="text-3xl font-bold text-slate-300 tracking-tight mt-2">"{{KPI_TICKETS}}"</p>
                </div>
                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Maior Demanda Comercial</p>
                    <p class="text-base font-bold text-blue-400 mt-3 truncate tracking-tight">"{{KPI_TOP}}"</p>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl flex flex-col">
                    <div class="mb-4">
                        <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Frequência por Categoria do Problema</h3>
                        <p class="text-xs text-slate-500 mt-0.5">Distribuição baseada no diagnóstico NLP dos chamados</p>
                    </div>
                    <div class="w-full flex-grow">"{{GRAFICO_1}}"</div>
                </div>
                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl flex flex-col">
                    <div class="mb-4">
                        <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Distribuição por Score de Urgência</h3>
                        <p class="text-xs text-slate-500 mt-0.5">Fatias geradas a partir da fórmula de multiplicação peso x volumetria</p>
                    </div>
                    <div class="w-full flex-grow">"{{GRAFICO_2}}"</div>
                </div>
            </div>

            <div class="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
                <div class="xl:col-span-2 bg-slate-900/30 border border-slate-900 rounded-xl overflow-hidden shadow-xl flex flex-col">
                    <div class="p-5 border-b border-slate-900 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/20">
                        <div>
                            <h3 class="text-sm font-bold text-slate-200 uppercase tracking-wider">Painel de Leads Qualificados</h3>
                            <p class="text-xs text-slate-500 mt-0.5">Selecione uma linha para carregar o playbook ao lado</p>
                        </div>
                        
                        <div class="flex items-center gap-3 w-full sm:w-auto">
                            <div class="relative w-full sm:w-64">
                                <span class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-slate-500">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                                    </svg>
                                </span>
                                <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="Buscar ID ou Segmento..." class="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-semibold text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500 transition">
                            </div>
                            
                            <select id="priorityFilter" onchange="filterTable()" class="border border-slate-800 rounded-lg px-3 py-2 bg-slate-950 text-xs font-semibold focus:outline-none focus:border-blue-500 text-slate-300 transition">
                                <option value="TODOS">Todos os Níveis</option>
                                <option value="ALTA">🚨 Apenas ALTA</option>
                                <option value="MÉDIA">⚠️ Apenas MÉDIA</option>
                                <option value="BAIXA">🟢 Apenas BAIXA</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="overflow-y-auto max-h-[465px] relative">
                        <table class="min-w-full divide-y divide-slate-900 text-left sticky" id="leadsTable">
                            <thead class="bg-slate-950/80 text-[11px] font-bold tracking-wider text-slate-500 uppercase sticky top-0 backdrop-blur-md z-10 border-b border-slate-900">
                                <tr>
                                    <th class="px-5 py-3.5">Cód. Cliente</th>
                                    <th class="px-5 py-3.5">Segmento</th>
                                    <th class="px-5 py-3.5">Categoria Vinculada</th>
                                    <th class="px-5 py-3.5">Solução Alvo</th>
                                    <th class="px-5 py-3.5 text-right">Urgência</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-900 text-xs text-slate-300 bg-slate-950/10">
                                "{{TABLE_ROWS}}"
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-xl space-y-4 min-h-[538px] flex flex-col justify-between">
                    <div class="space-y-4 flex-grow">
                        <div>
                            <h3 class="text-sm font-bold text-slate-200 uppercase tracking-wider">Playbook Comercial</h3>
                            <p class="text-xs text-slate-500 mt-0.5">Geração de abordagem automatizada baseada no gap do cliente</p>
                        </div>
                        
                        <div id="scriptPlaceholder" class="bg-slate-950/50 border border-slate-900/80 rounded-xl p-5 text-center py-24 text-slate-600 border-dashed flex flex-col justify-center items-center h-[380px]">
                            <svg class="w-8 h-8 mx-auto mb-2 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"></path></svg>
                            <p class="text-xs font-medium px-4">Selecione qualquer cliente na tabela ao lado para extrair o script pronto de vendas da IA.</p>
                        </div>
                        
                        <div id="scriptContentBox" class="hidden space-y-4">
                            <div class="p-4 bg-slate-950 border border-slate-900 rounded-xl space-y-2 text-xs">
                                <div class="flex justify-between"><span class="text-slate-500">Alvo Comercial:</span> <span id="viewId" class="font-bold text-white"></span></div>
                                <div class="flex justify-between"><span class="text-slate-500">Segmento Setorial:</span> <span id="viewSegm" class="font-bold text-yellow-500"></span></div>
                                <div class="flex justify-between"><span class="text-slate-500">Categoria Vinculada:</span> <span id="viewCat" class="font-semibold text-blue-400"></span></div>
                                <div class="flex justify-between"><span class="text-slate-500">Oferta Recomendada:</span> <span id="viewSug" class="font-bold text-emerald-400"></span></div>
                            </div>
                            <div class="relative group">
                                <textarea id="scriptBodyText" readonly class="w-full h-[210px] p-3.5 bg-slate-950 border border-slate-900 rounded-xl text-xs font-mono text-slate-300 focus:outline-none resize-none leading-relaxed"></textarea>
                                <button onclick="copyToClipboard()" class="absolute bottom-3 right-3 bg-blue-600 hover:bg-blue-500 text-white font-bold px-3 py-1.5 rounded-lg text-[10px] transition shadow-md">
                                    Copiar Texto
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div id="copyAlert" class="hidden text-center text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 py-2 rounded-lg mt-2">
                        ✓ Copiado para a área de transferência!
                    </div>
                </div>
            </div>
        </main>

        <main id="tab-content-novo-modulo" class="hidden flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900 pb-6">
                <div>
                    <h1 class="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">Painel de Chamados & Negócios</h1>
                    <p class="text-sm text-slate-400 mt-1">Gerencie a evolução das propostas comerciais arrastando os cards através das etapas do funil.</p>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-start min-h-[550px]">
                
                <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px]">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-blue-400">📋 A Fazer Proposta</h3>
                        <span class="bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-afazer">0</span>
                    </div>
                    
                    <div class="relative mb-4">
                        <span class="absolute inset-y-0 left-0 flex items-center pl-2.5 pointer-events-none text-slate-500">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                            </svg>
                        </span>
                        <input type="text" id="kanbanSearchInput" onkeyup="filterKanbanAFazer()" placeholder="Buscar ID nesta coluna..." class="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500 transition">
                    </div>

                    <div id="col-afazer" data-status="afazer" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[440px] pb-6">
                        "{{KANBAN_AFAZER}}"
                    </div>
                </div>

                <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px]">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-amber-400">⏳ Aguardando Respostas</h3>
                        <span class="bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-aguardando">0</span>
                    </div>
                    <div id="col-aguardando" data-status="aguardando" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        "{{KANBAN_AGUARDANDO}}"
                    </div>
                </div>

                <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px]">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-rose-400">❌ Recusado</h3>
                        <span class="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-recusado">0</span>
                    </div>
                    <div id="col-recusado" data-status="recusado" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        "{{KANBAN_RECUSADO}}"
                    </div>
                </div>

                <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px]">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-400">✅ Aceito</h3>
                        <span class="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-aceito">0</span>
                    </div>
                    <div id="col-aceito" data-status="aceito" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        "{{KANBAN_ACEITO}}"
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        function switchTab(tabId) {
            const contentComercial = document.getElementById('tab-content-comercial');
            const contentNovoModulo = document.getElementById('tab-content-novo-modulo');
            const btnComercial = document.getElementById('btn-comercial');
            const btnNovoModulo = document.getElementById('btn-novo-modulo');

            if (tabId === 'comercial') {
                contentComercial.classList.remove('hidden');
                contentNovoModulo.classList.add('hidden');
                btnComercial.className = "px-4 py-1.5 rounded-lg text-xs font-semibold transition bg-blue-600 text-white shadow-sm";
                btnNovoModulo.className = "px-4 py-1.5 rounded-lg text-xs font-semibold transition text-slate-400 hover:text-slate-200";
            } else if (tabId === 'novo-modulo') {
                contentComercial.classList.add('hidden');
                contentNovoModulo.classList.remove('hidden');
                btnNovoModulo.className = "px-4 py-1.5 rounded-lg text-xs font-semibold transition bg-blue-600 text-white shadow-sm";
                btnComercial.className = "px-4 py-1.5 rounded-lg text-xs font-semibold transition text-slate-400 hover:text-slate-200";
                calculateCounters();
            }
        }

        // Filtro da Tabela Principal
        function filterTable() {
            const searchVal = document.getElementById('searchInput').value.toLowerCase().trim();
            const filterVal = document.getElementById('priorityFilter').value;
            const rows = document.querySelectorAll('#leadsTable tbody tr');
            
            rows.forEach(row => {
                const id = row.getAttribute('data-id').toLowerCase();
                const segmento = row.getAttribute('data-segmento').toLowerCase();
                const priority = row.getAttribute('data-priority');
                
                const matchesSearch = id.includes(searchVal) || segmento.includes(searchVal);
                const matchesPriority = (filterVal === 'TODOS' || priority === filterVal);
                
                if (matchesSearch && matchesPriority) { row.style.display = ''; } 
                else { row.style.display = 'none'; }
            });
        }

        // FILTRO CIRÚRGICO DA COLUNA "A FAZER PROPOSTA"
        function filterKanbanAFazer() {
            const searchVal = document.getElementById('kanbanSearchInput').value.toLowerCase().trim();
            const cards = document.querySelectorAll('#col-afazer > div');
            
            cards.forEach(card => {
                const id = card.getAttribute('data-id').toLowerCase();
                // Também pesquisa opcionalmente pelo segmento guardado no texto interno do card
                const innerText = card.textContent.toLowerCase();
                
                if (id.includes(searchVal) || innerText.includes(searchVal)) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
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
            const copyText = document.getElementById("scriptBodyText");
            copyText.select();
            copyText.setSelectionRange(0, 99999);
            navigator.clipboard.writeText(copyText.value);
            
            const alertBox = document.getElementById('copyAlert');
            alertBox.classList.remove('hidden');
            setTimeout(() => { alertBox.classList.add('hidden'); }, 3000);
        }

        // --- SCRIPTS DO KANBAN ---
        document.addEventListener('DOMContentLoaded', function() {
            const zones = document.querySelectorAll('.kanban-zone');
            zones.forEach(zone => {
                new Sortable(zone, {
                    group: 'kanban-crm',
                    animation: 150,
                    ghostClass: 'bg-slate-800/50',
                    onEnd: function (evt) {
                        const itemEl = evt.item;
                        const clientCode = itemEl.getAttribute('data-id');
                        const destination = evt.to.getAttribute('data-status');
                        
                        fetch('/api/kanban/save', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ codcli: clientCode, nova_coluna: destination })
                        })
                        .then(res => res.json())
                        .then(() => { calculateCounters(); })
                        .catch(err => console.error("Falha ao salvar:", err));
                    }
                });
            });
            calculateCounters();
        });

        function calculateCounters() {
            document.getElementById('count-afazer').textContent = document.querySelectorAll('#col-afazer > div').length;
            document.getElementById('count-aguardando').textContent = document.querySelectorAll('#col-aguardando > div').length;
            document.getElementById('count-recusado').textContent = document.querySelectorAll('#col-recusado > div').length;
            document.getElementById('count-aceito').textContent = document.querySelectorAll('#col-aceito > div').length;
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
    global KANBAN_STATE
    if username != USER_EMAIL or password != USER_PASSWORD:
        erro_msg = "<div class='bg-rose-500/10 border border-rose-500/20 text-rose-400 p-3 rounded-xl mb-5 text-center text-xs font-semibold shadow-sm'>As credenciais informadas não coincidem.</div>"
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

    # --- GRAFICO 1 ---
    fig_cat = px.bar(df['categoria_problema'].value_counts().reset_index(), x='categoria_problema', y='count')
    fig_cat.update_traces(marker_color='#2563eb', marker_line_color='#1e40af', marker_line_width=1, opacity=0.85)
    fig_cat.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8', font_family='Inter',
        margin=dict(l=0, r=0, t=10, b=0), height=240, xaxis=dict(showgrid=False, title=""), yaxis=dict(showgrid=True, gridcolor='#1e293b', title="")
    )
    html_g1 = pio.to_html(fig_cat, full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

    # --- GRAFICO 2 ---
    fig_prio = px.pie(df, names='prioridade_comercial', hole=0.7, color='prioridade_comercial', color_discrete_map={'ALTA':'#f43f5e', 'MÉDIA':'#3b82f6', 'BAIXA':'#64748b'})
    fig_prio.update_traces(textposition='inside', textinfo='none')
    fig_prio.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8', font_family='Inter',
        margin=dict(l=0, r=0, t=10, b=0), height=240, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    )
    html_g2 = pio.to_html(fig_prio, full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})

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
        
        card_html = f"""
        <div data-id="{cid}" class="bg-slate-950 border border-slate-800 hover:border-slate-700 p-3.5 rounded-xl shadow-md cursor-grab active:cursor-grabbing transition space-y-2">
            <div class="flex justify-between items-center">
                <span class="text-xs font-bold text-white">Cliente #{cid}</span>
                <span class="text-[10px] font-bold px-2 py-0.5 rounded {badge_style}">{prio}</span>
            </div>
            <p class="text-[11px] text-yellow-500 font-medium tracking-tight">🏢 Segmento: {segmento_txt}</p>
            <div class="border-t border-slate-900 pt-2">
                <p class="text-[10px] text-slate-500 uppercase font-semibold">Solução Alvo:</p>
                <p class="text-xs text-slate-200 font-medium truncate">{row['servico_sugerido']}</p>
            </div>
        </div>
        """
        status_do_lead = KANBAN_STATE.get(cid, "afazer")
        kanban_buffers[status_do_lead] += card_html

    page = DASHBOARD_HTML
    page = page.replace('""{{KPI_TOTAL}}""', kpi_total).replace('"{{KPI_TOTAL}}"', kpi_total)
    page = page.replace('""{{KPI_ALTA}}""', kpi_alta).replace('"{{KPI_ALTA}}"', kpi_alta)
    page = page.replace('""{{KPI_TICKETS}}""', kpi_tickets).replace('"{{KPI_TICKETS}}"', kpi_tickets)
    page = page.replace('""{{KPI_TOP}}""', kpi_top).replace('"{{KPI_TOP}}"', kpi_top)
    page = page.replace('""{{GRAFICO_1}}""', html_g1).replace('"{{GRAFICO_1}}"', html_g1)
    page = page.replace('""{{GRAFICO_2}}""', html_g2).replace('"{{GRAFICO_2}}"', html_g2)
    page = page.replace('""{{TABLE_ROWS}}""', table_rows).replace('"{{TABLE_ROWS}}"', table_rows)
    
    page = page.replace('""{{KANBAN_AFAZER}}""', kanban_buffers["afazer"]).replace('"{{KANBAN_AFAZER}}"', kanban_buffers["afazer"])
    page = page.replace('""{{KANBAN_AGUARDANDO}}""', kanban_buffers["aguardando"]).replace('"{{KANBAN_AGUARDANDO}}"', kanban_buffers["aguardando"])
    page = page.replace('""{{KANBAN_RECUSADO}}""', kanban_buffers["recusado"]).replace('"{{KANBAN_RECUSADO}}"', kanban_buffers["recusado"])
    page = page.replace('""{{KANBAN_ACEITO}}""', kanban_buffers["aceito"]).replace('"{{KANBAN_ACEITO}}"', kanban_buffers["aceito"])

    return page

@app.post("/api/kanban/save")
def save_kanban_position(data: KanbanUpdate):
    if data.nova_coluna not in ["afazer", "aguardando", "recusado", "aceito"]:
        raise HTTPException(status_code=400, detail="Etapa do funil inválida")
    KANBAN_STATE[data.codcli] = data.nova_coluna
    return JSONResponse(content={"status": "success"})