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
<html lang="pt-br" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Entrar | Motor de Oportunidades B2B</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>body { font-family: 'Inter', sans-serif; }</style>
    <script>
        tailwind.config = { darkMode: 'class' };
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    </script>
</head>
<body class="bg-slate-50 dark:bg-slate-950 flex items-center justify-center min-h-screen bg-gradient-to-tr from-slate-100 via-slate-50 to-blue-50 dark:from-slate-950 dark:via-slate-900 dark:to-blue-950 text-slate-800 dark:text-slate-100 antialiased transition-colors duration-300">
    <div class="w-full max-w-md p-4">
        <div class="bg-white/80 dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 backdrop-blur-xl p-8 rounded-2xl shadow-2xl relative overflow-hidden">
            <div class="absolute -top-24 -right-24 w-48 h-48 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>
            
            <div class="mb-8">
                <div class="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center mb-4 shadow-lg shadow-blue-600/30">
                    <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                </div>
                <h2 class="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">Acesse a plataforma</h2>
                <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Insira suas credenciais do ecossistema CTI</p>
            </div>

            <form action="/login" method="POST" class="space-y-5">
                <div>
                    <label class="block text-slate-600 dark:text-slate-300 text-xs font-semibold tracking-wider uppercase mb-1.5">E-mail Corporativo</label>
                    <input type="email" name="username" placeholder="seu.nome@senai.com" required class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm transition text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-600">
                </div>
                <div>
                    <div class="flex justify-between items-center mb-1.5">
                        <label class="block text-slate-600 dark:text-slate-300 text-xs font-semibold tracking-wider uppercase">Senha de Acesso</label>
                    </div>
                    <input type="password" name="password" placeholder="••••••••" required class="w-full px-4 py-3 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm transition text-slate-800 dark:text-slate-200 placeholder-slate-400 dark:placeholder-slate-600">
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
<html lang="pt-br" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard | Motor de Oportunidades B2B</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.27.0/plotly.min.js"></script>
    <script>
        tailwind.config = { darkMode: 'class' };
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    </script>
    <style>
        body { font-family: 'Inter', sans-serif; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        .dark ::-webkit-scrollbar-thumb { background: #1e293b; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
        .dark ::-webkit-scrollbar-thumb:hover { background: #334155; }
    </style>
</head>
<body class="bg-slate-50 dark:bg-slate-950 min-h-screen text-slate-800 dark:text-slate-100 antialiased font-sans transition-colors duration-300">
    
    <div class="min-h-screen flex flex-col">
        
        <header class="border-b border-slate-200 dark:border-slate-900 bg-white/50 dark:bg-slate-950/50 backdrop-blur-md sticky top-0 z-50">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                <div class="flex items-center gap-8">
                    <div class="flex items-center gap-3">
                        <div class="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-md shadow-blue-600/20">
                            <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        </div>
                        <div>
                            <span class="text-sm font-bold tracking-tight text-slate-900 dark:text-white">Motor de Vendas B2B</span>
                        </div>
                    </div>
                    
                    <nav class="hidden md:flex items-center gap-1 bg-slate-100 dark:bg-slate-900/60 p-1 rounded-xl border border-slate-200 dark:border-slate-900">
                        <button onclick="switchTab('comercial')" id="btn-comercial" class="px-4 py-1.5 rounded-lg text-xs font-semibold transition bg-blue-600 text-white shadow-sm">
                            Painel Comercial
                        </button>
                        <button onclick="switchTab('novo-modulo')" id="btn-novo-modulo" class="px-4 py-1.5 rounded-lg text-xs font-semibold transition text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200">
                            Kanban
                        </button>
                        <button onclick="switchTab('churn')" id="btn-churn" class="px-4 py-1.5 rounded-lg text-xs font-semibold transition text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200">
                            Churn
                        </button>
                    </nav>
                </div>
                
                <div class="flex items-center gap-4">
                    <button onclick="toggleTheme()" class="p-2 rounded-lg bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-300 dark:hover:bg-slate-700 transition" title="Alternar Tema">
                        <svg class="w-4 h-4 hidden dark:block" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
                        <svg class="w-4 h-4 block dark:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"></path></svg>
                    </button>

                    <div class="text-right hidden sm:block">
                        <p class="text-xs font-semibold text-slate-800 dark:text-slate-200">Rodrigo</p>
                        <p class="text-[10px] text-slate-500 font-medium">Ecossistema CTI</p>
                    </div>
                    <a href="/" class="border border-slate-300 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-900/60 text-slate-600 dark:text-slate-400 hover:text-rose-500 dark:hover:text-rose-400 px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
                        Sair
                    </a>
                </div>
            </div>
        </header>

        <main id="tab-content-comercial" class="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
            
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-900 pb-6">
                <div>
                    <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-3xl">Geração Estratégica de Leads</h1>
                    <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Cruzamento de chamados de suporte técnico ativos com gaps contratuais comerciais.</p>
                </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-300 dark:hover:border-slate-800 transition duration-200">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Oportunidades Filtradas</p>
                    <p class="text-3xl font-bold text-slate-900 dark:text-white tracking-tight mt-2">{{KPI_TOTAL}}</p>
                </div>
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-300 dark:hover:border-slate-800 transition duration-200">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Prioridade Máxima (Hot)</p>
                    <div class="flex justify-between items-baseline mt-2">
                        <p class="text-3xl font-bold text-rose-500 tracking-tight">{{KPI_ALTA}}</p>
                        <span class="text-[10px] font-bold bg-rose-50 dark:bg-rose-500/10 text-rose-500 dark:text-rose-400 px-2 py-0.5 rounded-full border border-rose-200 dark:border-rose-500/20">Ação Comercial</span>
                    </div>
                </div>
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-300 dark:hover:border-slate-800 transition duration-200">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Total Histórico Analisado</p>
                    <p class="text-3xl font-bold text-slate-700 dark:text-slate-300 tracking-tight mt-2">{{KPI_TICKETS}}</p>
                </div>
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-300 dark:hover:border-slate-800 transition duration-200">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Maior Demanda Comercial</p>
                    <p class="text-base font-bold text-blue-500 dark:text-blue-400 mt-3 truncate tracking-tight">{{KPI_TOP}}</p>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl flex flex-col shadow-sm">
                    <div class="mb-4">
                        <h3 class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Frequência por Categoria do Problema</h3>
                        <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Distribuição baseada no diagnóstico dos chamados</p>
                    </div>
                    <div class="w-full flex-grow">{{GRAFICO_1}}</div>
                </div>
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl flex flex-col shadow-sm">
                    <div class="mb-4">
                        <h3 class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Distribuição por Score de Urgência</h3>
                        <p class="text-xs text-slate-400 dark:text-slate-500 mt-0.5">Fatias geradas a partir da fórmula de multiplicação peso x volumetria</p>
                    </div>
                    <div class="w-full flex-grow">{{GRAFICO_2}}</div>
                </div>
            </div>

            <div class="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
                <div class="xl:col-span-2 bg-white dark:bg-slate-900/30 border border-slate-200 dark:border-slate-900 rounded-xl overflow-hidden shadow-xl flex flex-col">
                    <div class="p-5 border-b border-slate-200 dark:border-slate-900 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-50 dark:bg-slate-900/20">
                        <div>
                            <h3 class="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">Painel de Leads Qualificados</h3>
                            <p class="text-xs text-slate-500 mt-0.5">Selecione uma linha para carregar o playbook ao lado</p>
                        </div>
                        
                        <div class="flex items-center gap-3 w-full sm:w-auto">
                            <div class="relative w-full sm:w-64">
                                <span class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-slate-400 dark:text-slate-500">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                                    </svg>
                                </span>
                                <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="Buscar ID ou Segmento..." class="w-full pl-9 pr-4 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none focus:border-blue-500 transition">
                            </div>
                            
                            <select id="priorityFilter" onchange="filterTable()" class="border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 bg-slate-50 dark:bg-slate-950 text-xs font-semibold focus:outline-none focus:border-blue-500 text-slate-700 dark:text-slate-300 transition">
                                <option value="TODOS">Todos os Níveis</option>
                                <option value="ALTA">🚨 Apenas ALTA</option>
                                <option value="MÉDIA">⚠️ Apenas MÉDIA</option>
                                <option value="BAIXA">🟢 Apenas BAIXA</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="overflow-y-auto max-h-[465px] relative">
                        <table class="min-w-full divide-y divide-slate-200 dark:divide-slate-900 text-left sticky" id="leadsTable">
                            <thead class="bg-slate-100/90 dark:bg-slate-950/80 text-[11px] font-bold tracking-wider text-slate-500 uppercase sticky top-0 backdrop-blur-md z-10 border-b border-slate-200 dark:border-slate-900">
                                <tr>
                                    <th class="px-5 py-3.5">Cód. Cliente</th>
                                    <th class="px-5 py-3.5">Segmento</th>
                                    <th class="px-5 py-3.5">Serviço Contratado</th>
                                    <th class="px-5 py-3.5">Categoria Vinculada</th>
                                    <th class="px-5 py-3.5">Solução Alvo</th>
                                    <th class="px-5 py-3.5 text-right">Urgência</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-200 dark:divide-slate-900 text-xs text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950/10">
                                {{TABLE_ROWS}}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-xl space-y-4 min-h-[538px] flex flex-col justify-between">
                    <div class="space-y-4 flex-grow">
                        <div>
                            <h3 class="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">Playbook Comercial</h3>
                            <p class="text-xs text-slate-500 mt-0.5">Geração de abordagem automatizada baseada no gap do cliente</p>
                        </div>
                        
                        <div id="scriptPlaceholder" class="bg-slate-50 dark:bg-slate-950/50 border border-slate-300 dark:border-slate-900/80 rounded-xl p-5 text-center py-24 text-slate-500 dark:text-slate-600 border-dashed flex flex-col justify-center items-center h-[380px]">
                            <svg class="w-8 h-8 mx-auto mb-2 text-slate-400 dark:text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"></path></svg>
                            <p class="text-xs font-medium px-4">Selecione qualquer cliente na tabela ao lado para extrair o script pronto de vendas da IA.</p>
                        </div>
                        
                        <div id="scriptContentBox" class="hidden space-y-4">
                            <div class="p-4 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-900 rounded-xl space-y-2 text-xs shadow-sm">
                                <div class="flex justify-between"><span class="text-slate-500">Alvo Comercial:</span> <span id="viewId" class="font-bold text-slate-800 dark:text-white"></span></div>
                                <div class="flex justify-between"><span class="text-slate-500">Segmento Setorial:</span> <span id="viewSegm" class="font-bold text-yellow-600 dark:text-yellow-500"></span></div>
                                <div class="flex justify-between"><span class="text-slate-500">Serviços Contratados:</span> <span id="viewServico" class="font-bold text-amber-600 dark:text-amber-400"></span></div>
                                <div class="flex justify-between"><span class="text-slate-500">Categoria Vinculada:</span> <span id="viewCat" class="font-semibold text-blue-600 dark:text-blue-400"></span></div>
                                <div class="flex justify-between"><span class="text-slate-500">Oferta Recomendada:</span> <span id="viewSug" class="font-bold text-emerald-600 dark:text-emerald-400"></span></div>
                            </div>
                            <div class="relative group">
                                <textarea id="scriptBodyText" readonly class="w-full h-[210px] p-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-900 rounded-xl text-xs font-mono text-slate-700 dark:text-slate-300 focus:outline-none resize-none leading-relaxed"></textarea>
                                <button onclick="copyToClipboard()" class="absolute bottom-3 right-3 bg-blue-600 hover:bg-blue-500 text-white font-bold px-3 py-1.5 rounded-lg text-[10px] transition shadow-md">
                                    Copiar Texto
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <div id="copyAlert" class="hidden text-center text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 py-2 rounded-lg mt-2">
                        ✓ Copiado para a área de transferência!
                    </div>
                </div>
            </div>
        </main>

        <main id="tab-content-novo-modulo" class="hidden flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-900 pb-6">
                <div>
                    <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-3xl">Painel de Chamados & Negócios</h1>
                    <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Gerencie a evolução das propostas comerciais arrastando os cards através das etapas do funil.</p>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-start min-h-[550px]">
                
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] shadow-sm">
                    <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-3">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">📋 A Fazer Proposta</h3>
                        <span class="bg-blue-50 dark:bg-blue-500/10 border border-blue-200 dark:border-blue-500/20 text-blue-600 dark:text-blue-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-afazer">0</span>
                    </div>
                    
                    <div class="relative mb-4">
                        <span class="absolute inset-y-0 left-0 flex items-center pl-2.5 pointer-events-none text-slate-400 dark:text-slate-500">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                            </svg>
                        </span>
                        <input type="text" id="kanbanSearchInput" onkeyup="filterKanbanAFazer()" placeholder="Buscar ID nesta coluna..." class="w-full pl-8 pr-3 py-1.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-[11px] text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none focus:border-blue-500 transition">
                    </div>

                    <div id="col-afazer" data-status="afazer" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[440px] pb-6">
                        {{KANBAN_AFAZER}}
                    </div>
                </div>

                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] shadow-sm">
                    <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">⏳ Aguardando Respostas</h3>
                        <span class="bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 text-amber-600 dark:text-amber-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-aguardando">0</span>
                    </div>
                    <div id="col-aguardando" data-status="aguardando" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        {{KANBAN_AGUARDANDO}}
                    </div>
                </div>

                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] shadow-sm">
                    <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400">❌ Recusado</h3>
                        <span class="bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-600 dark:text-rose-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-recusado">0</span>
                    </div>
                    <div id="col-recusado" data-status="recusado" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        {{KANBAN_RECUSADO}}
                    </div>
                </div>

                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] shadow-sm">
                    <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">✅ Aceito</h3>
                        <span class="bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-aceito">0</span>
                    </div>
                    <div id="col-aceito" data-status="aceito" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        {{KANBAN_ACEITO}}
                    </div>
                </div>
            </div>
        </main>

        <main id="tab-content-churn" class="hidden flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-900 pb-6">
                <div>
                    <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-3xl">Análise de Risco de Churn</h1>
                    <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Score calculado por nível do cliente, portfólio de serviços e oportunidades não aproveitadas.</p>
                </div>
            </div>

            <!-- KPIs Churn -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden">
                    <div class="absolute top-0 left-0 right-0 h-0.5 bg-rose-500"></div>
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Risco Alto</p>
                    <p class="text-3xl font-bold text-rose-500 tracking-tight mt-2" id="churn-kpi-alto">—</p>
                    <p class="text-xs text-slate-400 mt-1">segmentos com taxa ≥ 60%</p>
                </div>
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden">
                    <div class="absolute top-0 left-0 right-0 h-0.5 bg-amber-500"></div>
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Risco Médio</p>
                    <p class="text-3xl font-bold text-amber-500 tracking-tight mt-2" id="churn-kpi-medio">—</p>
                    <p class="text-xs text-slate-400 mt-1">segmentos com taxa 35–60%</p>
                </div>
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden">
                    <div class="absolute top-0 left-0 right-0 h-0.5 bg-emerald-500"></div>
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Risco Baixo</p>
                    <p class="text-3xl font-bold text-emerald-500 tracking-tight mt-2" id="churn-kpi-baixo">—</p>
                    <p class="text-xs text-slate-400 mt-1">segmentos com taxa &lt; 35%</p>
                </div>
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden">
                    <div class="absolute top-0 left-0 right-0 h-0.5 bg-blue-500"></div>
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Taxa Global de Churn</p>
                    <p class="text-3xl font-bold text-blue-500 tracking-tight mt-2" id="churn-kpi-avg">—</p>
                    <p class="text-xs text-slate-400 mt-1">% clientes nível C na base</p>
                </div>
            </div>

            <!-- Gráficos Churn -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-sm">
                    <h3 class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Score Médio por Segmento</h3>
                    <p class="text-xs text-slate-400 dark:text-slate-500 mb-4">Top 10 segmentos com maior risco médio</p>
                    <div id="churn-chart-seg" style="height:260px"></div>
                </div>
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-sm">
                    <h3 class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">Distribuição por Classificação</h3>
                    <p class="text-xs text-slate-400 dark:text-slate-500 mb-4">Proporção de clientes por faixa de risco</p>
                    <div id="churn-chart-donut" style="height:260px"></div>
                </div>
            </div>

            <!-- Tabela + Detalhe Churn -->
            <div class="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
                <div class="xl:col-span-2 bg-white dark:bg-slate-900/30 border border-slate-200 dark:border-slate-900 rounded-xl overflow-hidden shadow-xl flex flex-col">
                    <div class="p-5 border-b border-slate-200 dark:border-slate-900 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-50 dark:bg-slate-900/20">
                        <div>
                            <h3 class="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">Clientes por Risco de Churn</h3>
                            <p class="text-xs text-slate-500 mt-0.5">Clique em uma linha para ver o detalhamento</p>
                        </div>
                        <div class="flex items-center gap-2 flex-wrap">
                            <input type="text" id="churnSearch" onkeyup="filterChurnTable()" placeholder="🔍 Buscar cliente ou segmento..." class="pl-3 pr-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-semibold text-slate-700 dark:text-slate-300 placeholder-slate-400 dark:placeholder-slate-600 focus:outline-none focus:border-blue-500 transition w-52">
                            <select id="churnFilterRisco" onchange="filterChurnTable()" class="border border-slate-200 dark:border-slate-800 rounded-lg px-3 py-2 bg-slate-50 dark:bg-slate-950 text-xs font-semibold focus:outline-none focus:border-blue-500 text-slate-700 dark:text-slate-300 transition">
                                <option value="">Todos os Riscos</option>
                                <option value="ALTO">🔴 Alto (≥60%)</option>
                                <option value="MEDIO">🟡 Médio (35–60%)</option>
                                <option value="BAIXO">🟢 Baixo (&lt;35%)</option>
                            </select>
                        </div>
                    </div>
                    <div class="overflow-y-auto max-h-[465px]">
                        <table class="min-w-full divide-y divide-slate-200 dark:divide-slate-900 text-left" id="churnTable">
                            <thead class="bg-slate-100/90 dark:bg-slate-950/80 text-[11px] font-bold tracking-wider text-slate-500 uppercase sticky top-0 backdrop-blur-md z-10 border-b border-slate-200 dark:border-slate-900">
                                <tr>
                                    <th class="px-5 py-3.5">Segmento</th>
                                    <th class="px-5 py-3.5">Total Clientes</th>
                                    <th class="px-5 py-3.5">Nível C</th>
                                    <th class="px-5 py-3.5">Taxa de Churn</th>
                                    <th class="px-5 py-3.5">Classificação</th>
                                </tr>
                            </thead>
                            <tbody id="churnTableBody" class="divide-y divide-slate-200 dark:divide-slate-900 text-xs text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-950/10">
                                <tr><td colspan="5" class="px-5 py-8 text-center text-slate-400">Carregando dados...</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="flex items-center justify-center gap-3 py-3 border-t border-slate-200 dark:border-slate-900">
                        <button onclick="churnChangePage(-1)" class="border border-slate-200 dark:border-slate-800 hover:border-blue-500 text-slate-600 dark:text-slate-400 hover:text-blue-500 px-3 py-1 rounded-lg text-xs font-medium transition" id="churnBtnPrev">← Anterior</button>
                        <span class="text-xs text-slate-500 font-mono" id="churnPageInfo"></span>
                        <button onclick="churnChangePage(1)" class="border border-slate-200 dark:border-slate-800 hover:border-blue-500 text-slate-600 dark:text-slate-400 hover:text-blue-500 px-3 py-1 rounded-lg text-xs font-medium transition" id="churnBtnNext">Próxima →</button>
                    </div>
                </div>

                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 p-5 rounded-xl shadow-xl min-h-[538px] flex flex-col">
                    <h3 class="text-sm font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider mb-1">Detalhamento do Cliente</h3>
                    <p class="text-xs text-slate-500 mb-4">Selecione uma linha para carregar</p>
                    <div id="churnDetailEmpty" class="flex-grow flex flex-col items-center justify-center text-center text-slate-400 dark:text-slate-600 gap-3 py-16">
                        <svg class="w-8 h-8 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                        <p class="text-xs font-medium px-4">Selecione um cliente na tabela para ver o detalhamento do risco de churn.</p>
                    </div>
                    <div id="churnDetailBody" class="hidden space-y-3 flex-grow"></div>
                </div>
            </div>
        </main>
    </div>

    <script>
        function toggleTheme() {
            document.documentElement.classList.toggle('dark');
            if (document.documentElement.classList.contains('dark')) {
                localStorage.theme = 'dark';
            } else {
                localStorage.theme = 'light';
            }
        }

        function loadLeadScript(row) {
            const id = row.dataset.id;
            const segmento = row.dataset.segmento;
            const cat = row.dataset.cat;
            const sug = row.dataset.sug;
            const servico = row.dataset.servico;
            const scriptEl = row.querySelector('.hidden-script-source');
            const script = scriptEl ? scriptEl.textContent.trim() : '';

            document.getElementById('scriptPlaceholder').classList.add('hidden');
            document.getElementById('scriptContentBox').classList.remove('hidden');
            document.getElementById('viewId').textContent = 'Lead #' + id;
            document.getElementById('viewSegm').textContent = segmento;
            document.getElementById('viewServico').textContent = servico;
            document.getElementById('viewCat').textContent = cat;
            document.getElementById('viewSug').textContent = sug;
            document.getElementById('scriptBodyText').value = script;
        }

        function copyToClipboard() {
            const text = document.getElementById('scriptBodyText').value;
            navigator.clipboard.writeText(text).then(() => {
                const alert = document.getElementById('copyAlert');
                alert.classList.remove('hidden');
                setTimeout(() => alert.classList.add('hidden'), 2500);
            });
        }

        function filterTable() {
            const search = document.getElementById('searchInput').value.toLowerCase();
            const priority = document.getElementById('priorityFilter').value;
            const rows = document.querySelectorAll('#leadsTable tbody tr');
            rows.forEach(row => {
                const id = (row.dataset.id || '').toLowerCase();
                const seg = (row.dataset.segmento || '').toLowerCase();
                const prio = (row.dataset.priority || '');
                const matchSearch = !search || id.includes(search) || seg.includes(search);
                const matchPrio = priority === 'TODOS' || !priority || prio === priority;
                row.style.display = matchSearch && matchPrio ? '' : 'none';
            });
        }

        function filterKanbanAFazer() {
            const search = document.getElementById('kanbanSearchInput').value.toLowerCase();
            document.querySelectorAll('#col-afazer > div').forEach(card => {
                const id = (card.dataset.id || '').toLowerCase();
                card.style.display = !search || id.includes(search) ? '' : 'none';
            });
        }

        function switchTab(tabId) {
            const tabs = ['comercial', 'novo-modulo', 'churn'];
            const inactiveClass = "px-4 py-1.5 rounded-lg text-xs font-semibold transition text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200";
            const activeClass = "px-4 py-1.5 rounded-lg text-xs font-semibold transition bg-blue-600 text-white shadow-sm";

            tabs.forEach(t => {
                document.getElementById('tab-content-' + t).classList.add('hidden');
                document.getElementById('btn-' + t).className = inactiveClass;
            });

            document.getElementById('tab-content-' + tabId).classList.remove('hidden');
            document.getElementById('btn-' + tabId).className = activeClass;

            if (tabId === 'novo-modulo') calculateCounters();
            if (tabId === 'churn' && !churnLoaded) initChurn();
        }

        // ── CHURN MODULE ──────────────────────────────────────────────────────
        let churnData = [], churnFiltered = [], churnPage = 1, churnLoaded = false;
        const CHURN_PAGE_SIZE = 15;

        function seededRand(seed) {
            let s = seed;
            return () => { s = (s * 1664525 + 1013904223) & 0xffffffff; return (s >>> 0) / 0xffffffff; };
        }

        function initChurn() {
            churnLoaded = true;
            const data = JSON.parse(document.getElementById('churn-json-data').textContent);
            if (!data || !data.segmentos) return;

            churnData = data.segmentos;
            churnFiltered = [...churnData];

            document.getElementById('churn-kpi-alto').textContent = data.segmentos.filter(function(s){ return s.taxa_churn >= 60; }).length;
            document.getElementById('churn-kpi-medio').textContent = data.segmentos.filter(function(s){ return s.taxa_churn >= 35 && s.taxa_churn < 60; }).length;
            document.getElementById('churn-kpi-baixo').textContent = data.segmentos.filter(function(s){ return s.taxa_churn < 35; }).length;
            document.getElementById('churn-kpi-avg').textContent = data.taxa_global.toFixed(1) + '%';

            renderChurnTable();

            // Espera o Plotly carregar antes de renderizar os gráficos
            if (typeof Plotly !== 'undefined') {
                renderChurnCharts(data);
            } else {
                const interval = setInterval(function() {
                    if (typeof Plotly !== 'undefined') {
                        clearInterval(interval);
                        renderChurnCharts(data);
                    }
                }, 100);
            }
        }

        function updateChurnKPIs() { /* substituido por initChurn */ }


        function renderChurnCharts(data) {
            const isDark = document.documentElement.classList.contains('dark');
            const gridColor = isDark ? '#1e293b' : '#e2e8f0';
            const textColor = isDark ? '#94a3b8' : '#64748b';

            // Gráfico de barras: top 10 segmentos por taxa de churn (% nível C)
            const top10 = [...data.segmentos].sort((a,b) => b.taxa_churn - a.taxa_churn).slice(0, 10).reverse();
            const barColors = top10.map(s => s.taxa_churn >= 60 ? '#f43f5e' : s.taxa_churn >= 35 ? '#f59e0b' : '#10b981');

            Plotly.newPlot('churn-chart-seg', [{
                type: 'bar', orientation: 'h',
                x: top10.map(s => s.taxa_churn),
                y: top10.map(s => s.segmento.length > 22 ? s.segmento.slice(0, 22) + '…' : s.segmento),
                text: top10.map(s => s.taxa_churn + '%'),
                textposition: 'outside',
                marker: { color: barColors, line: { width: 0 } }
            }], {
                plot_bgcolor: 'rgba(0,0,0,0)', paper_bgcolor: 'rgba(0,0,0,0)',
                font: { color: textColor, family: 'Inter', size: 11 },
                margin: { l: 145, r: 50, t: 10, b: 30 },
                xaxis: { showgrid: true, gridcolor: gridColor, title: '% clientes nível C', range: [0, 115] },
                yaxis: { showgrid: false, title: '' }
            }, { displayModeBar: false, responsive: true });

            // Donut: distribuição A/B/C
            Plotly.newPlot('churn-chart-donut', [{
                type: 'pie', hole: 0.65,
                labels: ['Nível A (saudável)', 'Nível B (atenção)', 'Nível C (risco)'],
                values: [data.nivel_a, data.nivel_b, data.nivel_c],
                marker: { colors: ['#10b981', '#f59e0b', '#f43f5e'], line: { color: isDark ? '#0f172a' : '#f8fafc', width: 2 } },
                textinfo: 'none'
            }], {
                plot_bgcolor: 'rgba(0,0,0,0)', paper_bgcolor: 'rgba(0,0,0,0)',
                font: { color: textColor, family: 'Inter', size: 11 },
                margin: { l: 10, r: 10, t: 10, b: 10 },
                showlegend: true,
                legend: { orientation: 'h', yanchor: 'bottom', y: -0.2, xanchor: 'center', x: 0.5 }
            }, { displayModeBar: false, responsive: true });
        }

        function filterChurnTable() {
            const search = document.getElementById('churnSearch').value.toLowerCase();
            const risco = document.getElementById('churnFilterRisco').value;
            churnFiltered = churnData.filter(s => {
                const ms = !search || s.segmento.toLowerCase().includes(search);
                const mr = !risco || s.classificacao === risco;
                return ms && mr;
            });
            churnPage = 1;
            renderChurnTable();
        }

        function renderChurnTable() {
            const start = (churnPage - 1) * CHURN_PAGE_SIZE;
            const page = churnFiltered.slice(start, start + CHURN_PAGE_SIZE);
            const total = churnFiltered.length;
            const totalPages = Math.ceil(total / CHURN_PAGE_SIZE);
            const tbody = document.getElementById('churnTableBody');

            if (page.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="px-5 py-8 text-center text-slate-400">Nenhum segmento encontrado.</td></tr>';
            } else {
                tbody.innerHTML = page.map(s => {
                    const barColor = s.taxa_churn >= 60 ? '#f43f5e' : s.taxa_churn >= 35 ? '#f59e0b' : '#10b981';
                    const badgeCl = s.taxa_churn >= 60
                        ? 'bg-rose-50 dark:bg-rose-500/10 text-rose-500 border-rose-200 dark:border-rose-500/20'
                        : s.taxa_churn >= 35
                        ? 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 border-amber-200 dark:border-amber-500/20'
                        : 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 border-emerald-200 dark:border-emerald-500/20';
                    const label = s.taxa_churn >= 60 ? 'ALTO' : s.taxa_churn >= 35 ? 'MÉDIO' : 'BAIXO';
                    const tr = '<tr onclick="selectChurnSegmento(' + JSON.stringify(s.segmento) + ')" class="hover:bg-slate-100 dark:hover:bg-slate-900/40 cursor-pointer border-b border-slate-200 dark:border-slate-900/60 transition duration-150">' +
                        '<td class="px-5 py-3 font-semibold text-slate-800 dark:text-white">' + s.segmento + '</td>' +
                        '<td class="px-5 py-3 text-slate-500 font-mono text-xs">' + s.total + '</td>' +
                        '<td class="px-5 py-3 text-rose-500 font-semibold">' + s.nivel_c + '</td>' +
                        '<td class="px-5 py-3"><div class="flex items-center gap-2"><div class="flex-1 h-1.5 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden"><div style="width:' + s.taxa_churn + '%;background:' + barColor + '" class="h-full rounded-full"></div></div><span class="text-xs font-mono text-slate-600 dark:text-slate-400 w-10 text-right">' + s.taxa_churn + '%</span></div></td>' +
                        '<td class="px-5 py-3"><span class="text-[10px] font-bold px-2 py-0.5 rounded-full border ' + badgeCl + '">' + label + '</span></td>' +
                        '</tr>';
                    return tr;
                }).join('');
            }
            document.getElementById('churnPageInfo').textContent = (start + 1) + '\u2013' + Math.min(start + CHURN_PAGE_SIZE, total) + ' de ' + total;
            document.getElementById('churnBtnPrev').disabled = churnPage === 1;
            document.getElementById('churnBtnNext').disabled = churnPage >= totalPages;
        }

        function churnChangePage(dir) { churnPage += dir; renderChurnTable(); }

        function selectChurnSegmento(segmento) {
            const s = churnData.find(x => x.segmento === segmento);
            if (!s) return;
            const scoreColor = s.taxa_churn >= 60 ? '#f43f5e' : s.taxa_churn >= 35 ? '#f59e0b' : '#10b981';
            const label = s.taxa_churn >= 60 ? 'ALTO' : s.taxa_churn >= 35 ? 'MÉDIO' : 'BAIXO';
            const badgeCl = s.taxa_churn >= 60 ? 'bg-rose-50 dark:bg-rose-500/10 text-rose-500 border-rose-200' : s.taxa_churn >= 35 ? 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 border-amber-200' : 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 border-emerald-200';
            const acao = s.taxa_churn >= 60 ? 'Segmento crítico. Mais de 60% dos clientes em nível C. Ação imediata de retenção recomendada.' : s.taxa_churn >= 35 ? 'Atenção moderada. Monitore e acione clientes nível C com proposta de upsell.' : 'Segmento saudável. Foco em expansão de portfólio.';
            document.getElementById('churnDetailEmpty').classList.add('hidden');
            const body = document.getElementById('churnDetailBody');
            body.classList.remove('hidden');
            body.innerHTML =
                '<div class="space-y-2 text-xs">' +
                    '<div class="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800"><span class="text-slate-500">Segmento</span><span class="font-bold text-yellow-600 dark:text-yellow-500">' + s.segmento + '</span></div>' +
                    '<div class="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800"><span class="text-slate-500">Total de clientes</span><span class="font-bold font-mono">' + s.total + '</span></div>' +
                    '<div class="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800"><span class="text-slate-500">N\u00edvel A (saud\u00e1vel)</span><span class="font-bold text-emerald-600">' + s.nivel_a + '</span></div>' +
                    '<div class="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800"><span class="text-slate-500">N\u00edvel B (aten\u00e7\u00e3o)</span><span class="font-bold text-amber-600">' + s.nivel_b + '</span></div>' +
                    '<div class="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800"><span class="text-slate-500">N\u00edvel C (risco)</span><span class="font-bold text-rose-500">' + s.nivel_c + '</span></div>' +
                '</div>' +
                '<div class="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-900 rounded-xl p-4 mt-3">' +
                    '<p class="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Taxa de Churn (% n\u00edvel C)</p>' +
                    '<div class="h-2 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden mb-2"><div style="width:' + s.taxa_churn + '%;background:' + scoreColor + '" class="h-full rounded-full transition-all duration-500"></div></div>' +
                    '<div class="flex justify-between items-center">' +
                        '<span class="text-2xl font-bold font-mono" style="color:' + scoreColor + '">' + s.taxa_churn + '<span class=\"text-xs text-slate-400 font-sans\">%</span></span>' +
                        '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full border ' + badgeCl + '">' + label + '</span>' +
                    '</div>' +
                '</div>' +
                '<div class="mt-3 p-3 bg-blue-50 dark:bg-blue-500/5 border border-blue-200 dark:border-blue-500/20 rounded-xl text-xs text-slate-600 dark:text-slate-400 leading-relaxed">' +
                    '&#x1F4A1; <strong class=\"text-slate-800 dark:text-slate-200\">A\u00e7\u00e3o Recomendada:</strong> ' + acao +
                '</div>';
        }



        function calculateCounters() {
            document.getElementById('count-afazer').textContent = document.querySelectorAll('#col-afazer > div').length;
            document.getElementById('count-aguardando').textContent = document.querySelectorAll('#col-aguardando > div').length;
            document.getElementById('count-recusado').textContent = document.querySelectorAll('#col-recusado > div').length;
            document.getElementById('count-aceito').textContent = document.querySelectorAll('#col-aceito > div').length;
        }

        document.addEventListener('DOMContentLoaded', function() {
            const zones = document.querySelectorAll('.kanban-zone');
            zones.forEach(zone => {
                Sortable.create(zone, {
                    group: 'kanban',
                    animation: 150,
                    ghostClass: 'opacity-30',
                    onEnd: function(evt) {
                        const cardId = evt.item.dataset.id;
                        const novaColuna = evt.to.dataset.status;
                        fetch('/api/kanban/save', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ codcli: cardId, nova_coluna: novaColuna })
                        }).then(() => { calculateCounters(); });
                        calculateCounters();
                    }
                });
            });
            calculateCounters();
        });
    </script>
    <script id="churn-json-data" type="application/json">{{CHURN_DATA}}</script>
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
        erro_msg = "<div class='bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-600 dark:text-rose-400 p-3 rounded-xl mb-5 text-center text-xs font-semibold shadow-sm'>As credenciais informadas não coincidem.</div>"
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
        margin=dict(l=0, r=0, t=10, b=0), height=240, xaxis=dict(showgrid=False, title=""), yaxis=dict(showgrid=True, gridcolor='#cbd5e1', title="")
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
    
    # --- RENDERIZAÇÃO DAS LINHAS E DOS CARDS DO KANBAN ---
    for _, row in df.iterrows():
        cid = str(row['codcli'])
        segmento = str(row.get('segmento', 'Não Informado'))
        categoria = str(row['categoria_problema'])
        solucao = str(row['servico_sugerido'])
        prioridade = str(row['prioridade_comercial'])
        tickets = str(row['qtd_tickets'])
        
    
        # 1. PEGA O SERVIÇO QUE O CLIENTE JÁ CONTRATA
        # ATENÇÃO: O texto abaixo deve ser EXATAMENTE igual ao cabeçalho da coluna no seu arquivo
        coluna_servico = 'servicos_contratados' 
        
        if coluna_servico in row.index:
            val = row[coluna_servico]
            # Trata células vazias do Pandas (NaN), nulas ou strings em branco
            if pd.isna(val) or str(val).strip().lower() in ["nan", "none", "", "null"]:
                servico_atual = "Nenhum"
            else:
                servico_atual = str(val).strip()
        else:
            servico_atual = "Nenhum"
        # Tratamento do script antigo (mantendo o fallback dinâmico)
        script_texto = str(row.get('script_abordagem', '')).strip()
        if script_texto in ["", "nan", "None", "Script não gerado."]:
            script_texto = f"Olá, identificamos chamados sobre {categoria} e sugerimos a solução {solucao}."
        # Sanitiza caracteres que quebram o HTML
        script_texto = script_texto.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

        cor_prio = "text-rose-500" if prioridade == "ALTA" else ("text-blue-500 dark:text-blue-400" if prioridade == "MÉDIA" else "text-slate-500 dark:text-slate-400")
        
        # 2. LINHA DA TABELA OPERACIONAL
        table_rows += f"""
        <tr data-id="{cid}" data-segmento="{segmento}" data-priority="{prioridade}" data-cat="{categoria}" data-sug="{solucao}" data-servico="{servico_atual}" onclick="loadLeadScript(this)" class="hover:bg-slate-100 dark:hover:bg-slate-900/40 cursor-pointer border-b border-slate-200 dark:border-slate-900/60 transition duration-150 group">
            <td class="px-5 py-3 font-semibold text-slate-800 dark:text-white">#{cid}</td>
            <td class="px-5 py-3 text-slate-600 dark:text-slate-400 font-medium">{segmento}</td>
            <td class="px-5 py-3 text-amber-600 dark:text-amber-400 font-medium">{servico_atual}</td> 
            <td class="px-5 py-3 text-blue-600 dark:text-blue-400 font-semibold">{categoria}</td>
            <td class="px-5 py-3 text-emerald-600 dark:text-emerald-400 font-medium">{solucao}</td>
            <td class="px-5 py-3 text-right font-bold {cor_prio}">{prioridade}
                <div class="hidden hidden-script-source">{script_texto}</div>
            </td>
        </tr>
        """

        # Card do Funil Kanban
        status_atual = KANBAN_STATE.get(cid, "afazer")
        card_html = f"""
        <div data-id="{cid}" class="bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-3.5 rounded-xl space-y-2 cursor-grab active:cursor-grabbing shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition duration-150">
            <div class="flex justify-between items-center"><span class="text-[11px] font-bold text-slate-800 dark:text-white">#{cid}</span><span class="text-[9px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800">{tickets} Tickets</span></div>
            <p class="text-[11px] font-medium text-slate-500 dark:text-slate-400 truncate">{segmento}</p>
            <div class="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/5 px-2 py-1 rounded-md border border-emerald-200 dark:border-emerald-500/10 truncate">{solucao}</div>
        </div>
        """
        if status_atual in kanban_buffers:
            kanban_buffers[status_atual] += card_html

    # Substituição final de placeholders no template HTML
    html_customizado = DASHBOARD_HTML\
        .replace("{{KPI_TOTAL}}", kpi_total)\
        .replace("{{KPI_ALTA}}", kpi_alta)\
        .replace("{{KPI_TICKETS}}", kpi_tickets)\
        .replace("{{KPI_TOP}}", kpi_top)\
        .replace("{{GRAFICO_1}}", html_g1)\
        .replace("{{GRAFICO_2}}", html_g2)\
        .replace("{{TABLE_ROWS}}", table_rows)\
        .replace("{{KANBAN_AFAZER}}", kanban_buffers["afazer"])\
        .replace("{{KANBAN_AGUARDANDO}}", kanban_buffers["aguardando"])\
        .replace("{{KANBAN_RECUSADO}}", kanban_buffers["recusado"])\
        .replace("{{KANBAN_ACEITO}}", kanban_buffers["aceito"])

    # --- CHURN DATA (baseado no schurn.xlsx, lógica do notebook de análise) ---
    import json as _json
    churn_json_str = "{}"
    caminhos_schurn = [
        os.path.join("data", "raw", "schurn (1).xlsx"),
        os.path.join("data", "raw", "schurn.xlsx"),
        os.path.join("output", "schurn.xlsx"),
        "schurn.xlsx",
    ]
    df_schurn = None
    for _p in caminhos_schurn:
        if os.path.exists(_p):
            df_schurn = pd.read_excel(_p)
            break

    if df_schurn is not None and not df_schurn.empty:
        try:
            total_seg = df_schurn.groupby("segmento").size()
            clientes_c = df_schurn[df_schurn["nivel_cliente"] == "C"].groupby("segmento").size()
            analise = pd.DataFrame({"total": total_seg, "nivel_c": clientes_c}).fillna(0).astype(int)
            analise["taxa_churn"] = (analise["nivel_c"] / analise["total"] * 100).round(1)

            def classifica(t):
                return "ALTO" if t >= 60 else ("MEDIO" if t >= 35 else "BAIXO")

            total_srv = df_schurn.groupby("servico").size()
            c_srv = df_schurn[df_schurn["nivel_cliente"] == "C"].groupby("servico").size()
            analise_srv = pd.DataFrame({"total": total_srv, "nivel_c": c_srv}).fillna(0).astype(int)
            analise_srv["taxa_churn"] = (analise_srv["nivel_c"] / analise_srv["total"] * 100).round(1)

            churn_list = []
            for seg, row in analise.iterrows():
                churn_list.append({
                    "segmento": seg,
                    "total": int(row["total"]),
                    "nivel_c": int(row["nivel_c"]),
                    "nivel_a": int(df_schurn[(df_schurn["segmento"] == seg) & (df_schurn["nivel_cliente"] == "A")].shape[0]),
                    "nivel_b": int(df_schurn[(df_schurn["segmento"] == seg) & (df_schurn["nivel_cliente"] == "B")].shape[0]),
                    "taxa_churn": float(row["taxa_churn"]),
                    "classificacao": classifica(float(row["taxa_churn"])),
                })
            churn_list.sort(key=lambda x: -x["taxa_churn"])

            srv_list = []
            for srv, row in analise_srv.sort_values("taxa_churn", ascending=False).head(15).iterrows():
                srv_list.append({
                    "servico": srv,
                    "total": int(row["total"]),
                    "nivel_c": int(row["nivel_c"]),
                    "taxa_churn": float(row["taxa_churn"]),
                })

            churn_json_str = _json.dumps({
                "segmentos": churn_list,
                "servicos": srv_list,
                "taxa_global": round(float((df_schurn["nivel_cliente"] == "C").mean() * 100), 1),
                "total_clientes": int(len(df_schurn)),
                "nivel_a": int((df_schurn["nivel_cliente"] == "A").sum()),
                "nivel_b": int((df_schurn["nivel_cliente"] == "B").sum()),
                "nivel_c": int((df_schurn["nivel_cliente"] == "C").sum()),
            }, ensure_ascii=True)
        except Exception as e:
            churn_json_str = "{}"

    html_customizado = html_customizado.replace("{{CHURN_DATA}}", churn_json_str)

    # Limpa surrogates e caracteres inválidos
    html_customizado = html_customizado.encode('utf-8', errors='replace').decode('utf-8')

    return HTMLResponse(content=html_customizado)

@app.post("/api/kanban/save")
def save_kanban(data: KanbanUpdate):
    global KANBAN_STATE
    KANBAN_STATE[data.codcli] = data.nova_coluna
    return {"status": "success", "message": f"Cliente {data.codcli} movido para {data.nova_coluna}"}