from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import pandas as pd
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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght=300;400;500;600;700;800&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js"></script>
    <style>
        body { font-family: 'Inter', sans-serif; transition: background-color 0.3s, color 0.3s; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #334155; }
    </style>
</head>
<body id="body-layout" class="bg-slate-950 min-h-screen text-slate-100 antialiased font-sans">
    
    <div class="min-h-screen flex flex-col">
        
        <header class="border-b border-slate-900 bg-slate-950/50 backdrop-blur-md sticky top-0 z-50 id-header">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                <div class="flex items-center gap-8">
                    <div class="flex items-center gap-3">
                        <div class="h-8 w-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-md shadow-blue-600/20">
                            <svg class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                        </div>
                        <div>
                            <span class="text-sm font-bold tracking-tight text-white id-title-app">Motor de Vendas B2B</span>
                        </div>
                    </div>
                    
                    <nav class="hidden md:flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-900 navbar-bg">
                        <button onclick="switchTab('comercial')" id="btn-comercial" class="px-4 py-1.5 rounded-lg text-xs font-semibold transition bg-blue-600 text-white shadow-sm">
                            Painel Comercial
                        </button>
                        <button onclick="switchTab('novo-modulo')" id="btn-novo-modulo" class="px-4 py-1.5 rounded-lg text-xs font-semibold transition text-slate-400 hover:text-slate-200">
                            Kanban
                        </button>
                    </nav>
                </div>
                
                <div class="flex items-center gap-4">
                    <button onclick="toggleTheme()" class="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm">
                        ☀️/🌙 Alterar Tema
                    </button>
                    <div class="text-right hidden sm:block">
                        <p class="text-xs font-semibold text-slate-200 id-user-name">Rodrigo</p>
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
            
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900 pb-6 div-border">
                <div>
                    <h1 class="text-2xl font-extrabold tracking-tight text-white sm:text-3xl text-main-heading">Geração Estratégica de Leads</h1>
                    <p class="text-sm text-slate-400 mt-1 subtitle-text">Cruzamento de chamados de suporte técnico ativos com gaps contratuais comerciais.</p>
                </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200 card-bg border-style">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider label-text">Oportunidades Filtradas</p>
                    <p class="text-3xl font-bold text-white tracking-tight mt-2 val-text">{{KPI_TOTAL}}</p>
                </div>
                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200 card-bg border-style">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider label-text">Prioridade Máxima (Hot)</p>
                    <div class="flex justify-between items-baseline mt-2">
                        <p class="text-3xl font-bold text-rose-500 tracking-tight">{{KPI_ALTA}}</p>
                        <span class="text-[10px] font-bold bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded-full border border-rose-500/20">Ação Comercial</span>
                    </div>
                </div>
                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200 card-bg border-style">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider label-text">Total Histórico Analisado</p>
                    <p class="text-3xl font-bold text-slate-300 tracking-tight mt-2 val-text">{{KPI_TICKETS}}</p>
                </div>
                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-sm relative overflow-hidden group hover:border-slate-800 transition duration-200 card-bg border-style">
                    <p class="text-xs text-slate-500 font-semibold uppercase tracking-wider label-text">Maior Demanda Comercial</p>
                    <p class="text-base font-bold text-blue-400 mt-3 truncate tracking-tight">{{KPI_TOP}}</p>
                </div>
            </div>

            <div class="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
                <div class="xl:col-span-2 bg-slate-900/30 border border-slate-900 rounded-xl overflow-hidden shadow-xl flex flex-col card-bg border-style">
                    <div class="p-5 border-b border-slate-900 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/20 div-border header-table-bg">
                        <div>
                            <h3 class="text-sm font-bold text-slate-200 uppercase tracking-wider text-main-heading">Painel de Leads Qualificados</h3>
                            <p class="text-xs text-slate-500 mt-0.5 subtitle-text">Selecione uma linha para carregar o playbook ao lado</p>
                        </div>
                        
                        <div class="flex items-center gap-3 w-full sm:w-auto">
                            <div class="relative w-full sm:w-64">
                                <span class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-slate-500">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                                    </svg>
                                </span>
                                <input type="text" id="searchInput" onkeyup="filterTable()" placeholder="Buscar ID ou Segmento..." class="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-semibold text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500 transition input-box">
                            </div>
                            
                            <select id="priorityFilter" onchange="filterTable()" class="border border-slate-800 rounded-lg px-3 py-2 bg-slate-950 text-xs font-semibold focus:outline-none focus:border-blue-500 text-slate-300 transition input-box">
                                <option value="TODOS">Todos os Níveis</option>
                                <option value="ALTA">🚨 Apenas ALTA</option>
                                <option value="MÉDIA">⚠️ Apenas MÉDIA</option>
                                <option value="BAIXA">🟢 Apenas BAIXA</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="overflow-y-auto max-h-[465px] relative">
                        <table class="min-w-full divide-y divide-slate-900 text-left sticky border-style" id="leadsTable">
                            <thead class="bg-slate-950/80 text-[11px] font-bold tracking-wider text-slate-500 uppercase sticky top-0 backdrop-blur-md z-10 border-b border-slate-900 div-border header-table-bg">
                                <tr>
                                    <th class="px-5 py-3.5">Cód. Cliente</th>
                                    <th class="px-5 py-3.5">Segmento</th>
                                    <th class="px-5 py-3.5">Categoria Vinculada</th>
                                    <th class="px-5 py-3.5">Solução Alvo</th>
                                    <th class="px-5 py-3.5 text-right">Urgência</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-900 text-xs text-slate-300 bg-slate-950/10 table-body">
                                {{TABLE_ROWS}}
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="bg-slate-900/40 border border-slate-900 p-5 rounded-xl shadow-xl space-y-4 min-h-[538px] flex flex-col justify-between card-bg border-style">
                    <div class="space-y-4 flex-grow">
                        <div>
                            <h3 class="text-sm font-bold text-slate-200 uppercase tracking-wider text-main-heading">Playbook Comercial</h3>
                            <p class="text-xs text-slate-500 mt-0.5 subtitle-text">Geração de abordagem automatizada baseada no gap do cliente</p>
                        </div>
                        
                        <div id="scriptPlaceholder" class="bg-slate-950/50 border border-slate-900/80 rounded-xl p-5 text-center py-24 text-slate-600 border-dashed flex flex-col justify-center items-center h-[380px] placeholder-box">
                            <svg class="w-8 h-8 mx-auto mb-2 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"></path></svg>
                            <p class="text-xs font-medium px-4">Selecione qualquer cliente na tabela ao lado para extrair o script pronto de vendas da IA.</p>
                        </div>
                        
                        <div id="scriptContentBox" class="hidden space-y-4">
                            <div class="p-4 bg-slate-950 border border-slate-900 rounded-xl space-y-2 text-xs table-body border-style">
                                <div class="flex justify-between"><span class="text-slate-500">Alvo Comercial:</span> <span id="viewId" class="font-bold text-white val-text"></span></div>
                                <div class="flex justify-between"><span class="text-slate-500">Segmento Setorial:</span> <span id="viewSegm" class="font-bold text-yellow-500"></span></div>
                                <div class="flex justify-between"><span class="text-slate-500">Categoria Vinculada:</span> <span id="viewCat" class="font-semibold text-blue-400"></span></div>
                                <div class="flex justify-between"><span class="text-slate-500">Oferta Recomendada:</span> <span id="viewSug" class="font-bold text-emerald-400"></span></div>
                            </div>
                            <div class="relative group">
                                <textarea id="scriptBodyText" readonly class="w-full h-[210px] p-3.5 bg-slate-950 border border-slate-900 rounded-xl text-xs font-mono text-slate-300 focus:outline-none resize-none leading-relaxed textarea-box"></textarea>
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
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-900 pb-6 div-border">
                <div>
                    <h1 class="text-2xl font-extrabold tracking-tight text-white sm:text-3xl text-main-heading">Painel de Chamados & Negócios</h1>
                    <p class="text-sm text-slate-400 mt-1 subtitle-text">Gerencie a evolução das propostas comerciais arrastando os cards através das etapas do funil.</p>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-start min-h-[550px]">
                <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] card-bg border-style">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-3 div-border">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-blue-400">📋 A Fazer Proposta</h3>
                        <span class="bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-afazer">0</span>
                    </div>
                    <div class="relative mb-4">
                        <span class="absolute inset-y-0 left-0 flex items-center pl-2.5 pointer-events-none text-slate-500">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                            </svg>
                        </span>
                        <input type="text" id="kanbanSearchInput" onkeyup="filterKanbanAFazer()" placeholder="Buscar ID nesta coluna..." class="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500 transition input-box">
                    </div>
                    <div id="col-afazer" data-status="afazer" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[440px] pb-6">
                        {{KANBAN_AFAZER}}
                    </div>
                </div>

                <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] card-bg border-style">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-4 div-border">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-amber-400">⏳ Aguardando Respostas</h3>
                        <span class="bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-aguardando">0</span>
                    </div>
                    <div id="col-aguardando" data-status="aguardando" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        {{KANBAN_AGUARDANDO}}
                    </div>
                </div>

                <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] card-bg border-style">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-4 div-border">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-rose-400">❌ Recusado</h3>
                        <span class="bg-rose-500/10 border border-rose-500/20 text-rose-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-recusado">0</span>
                    </div>
                    <div id="col-recusado" data-status="recusado" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        {{KANBAN_RECUSADO}}
                    </div>
                </div>

                <div class="bg-slate-900/40 border border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] card-bg border-style">
                    <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-4 div-border">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-400">✅ Aceito</h3>
                        <span class="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-aceito">0</span>
                    </div>
                    <div id="col-aceito" data-status="aceito" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        {{KANBAN_ACEITO}}
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        // --- SCRIPT DE ALTERNÂNCIA DE TEMA (DARK/LIGHT) ---
        function toggleTheme() {
            const body = document.getElementById('body-layout');
            const isDark = body.classList.contains('bg-slate-950');

            if (isDark) {
                // Mudar para o Modo Branco (Light)
                body.className = "bg-slate-50 min-h-screen text-slate-800 antialiased font-sans";
                document.querySelectorAll('.card-bg').forEach(el => el.className = el.className.replace('bg-slate-900/40', 'bg-white shadow-md').replace('bg-slate-900/30', 'bg-white shadow-md'));
                document.querySelectorAll('.border-style').forEach(el => el.className = el.className.replace('border-slate-900', 'border-slate-200'));
                document.querySelectorAll('.div-border').forEach(el => el.className = el.className.replace('border-slate-900', 'border-slate-200').replace('border-slate-800', 'border-slate-200'));
                document.querySelectorAll('.input-box, .textarea-box').forEach(el => el.className = el.className.replace('bg-slate-950', 'bg-slate-100').replace('border-slate-800', 'border-slate-300').replace('text-slate-300', 'text-slate-800'));
                document.querySelectorAll('.text-main-heading, .val-text').forEach(el => el.className = el.className.replace('text-white', 'text-slate-900').replace('text-slate-200', 'text-slate-900'));
                document.querySelectorAll('.subtitle-text, .label-text').forEach(el => el.className = el.className.replace('text-slate-400', 'text-slate-600').replace('text-slate-500', 'text-slate-600'));
                document.querySelectorAll('.header-table-bg').forEach(el => el.className = el.className.replace('bg-slate-900/20', 'bg-slate-100').replace('bg-slate-950/80', 'bg-slate-100'));
                document.querySelectorAll('.table-body').forEach(el => el.className = el.className.replace('bg-slate-950/10', 'bg-white').replace('text-slate-300', 'text-slate-700'));
                document.querySelectorAll('.placeholder-box').forEach(el => el.className = el.className.replace('bg-slate-950/50', 'bg-slate-100').replace('border-slate-900/80', 'border-slate-300'));
                document.querySelectorAll('.kanban-card').forEach(el => el.className = el.className.replace('bg-slate-950', 'bg-slate-100').replace('border-slate-800', 'border-slate-200').replace('text-slate-200', 'text-slate-800'));
                document.querySelector('.id-header').className = "border-b border-slate-200 bg-white sticky top-0 z-50 id-header shadow-sm";
                document.querySelector('.id-title-app').className = "text-sm font-bold tracking-tight text-slate-800 id-title-app";
                document.querySelector('.id-user-name').className = "text-xs font-semibold text-slate-800 id-user-name";
                document.querySelector('.navbar-bg').className = "hidden md:flex items-center gap-1 bg-slate-200 p-1 rounded-xl border border-slate-300 navbar-bg";
            } else {
                // Retornar para o Modo Escuro (Dark)
                body.className = "bg-slate-950 min-h-screen text-slate-100 antialiased font-sans";
                document.querySelectorAll('.card-bg').forEach(el => el.className = el.className.replace('bg-white shadow-md', 'bg-slate-900/40').replace('bg-white shadow-md', 'bg-slate-900/30'));
                document.querySelectorAll('.border-style').forEach(el => el.className = el.className.replace('border-slate-200', 'border-slate-900'));
                document.querySelectorAll('.div-border').forEach(el => el.className = el.className.replace('border-slate-200', 'border-slate-900').replace('border-slate-200', 'border-slate-800'));
                document.querySelectorAll('.input-box, .textarea-box').forEach(el => el.className = el.className.replace('bg-slate-100', 'bg-slate-950').replace('border-slate-300', 'border-slate-800').replace('text-slate-800', 'text-slate-300'));
                document.querySelectorAll('.text-main-heading, .val-text').forEach(el => el.className = el.className.replace('text-slate-900', 'text-white').replace('text-slate-900', 'text-slate-200'));
                document.querySelectorAll('.subtitle-text, .label-text').forEach(el => el.className = el.className.replace('text-slate-600', 'text-slate-400').replace('text-slate-600', 'text-slate-500'));
                document.querySelectorAll('.header-table-bg').forEach(el => el.className = el.className.replace('bg-slate-100', 'bg-slate-900/20').replace('bg-slate-100', 'bg-slate-950/80'));
                document.querySelectorAll('.table-body').forEach(el => el.className = el.className.replace('bg-white', 'bg-slate-950/10').replace('text-slate-700', 'text-slate-300'));
                document.querySelectorAll('.placeholder-box').forEach(el => el.className = el.className.replace('bg-slate-100', 'bg-slate-950/50').replace('border-slate-300', 'border-slate-900/80'));
                document.querySelectorAll('.kanban-card').forEach(el => el.className = el.className.replace('bg-slate-100', 'bg-slate-950').replace('border-slate-200', 'border-slate-800').replace('text-slate-800', 'text-slate-200'));
                document.querySelector('.id-header').className = "border-b border-slate-900 bg-slate-950/50 backdrop-blur-md sticky top-0 z-50 id-header";
                document.querySelector('.id-title-app').className = "text-sm font-bold tracking-tight text-white id-title-app";
                document.querySelector('.id-user-name').className = "text-xs font-semibold text-slate-200 id-user-name";
                document.querySelector('.navbar-bg').className = "hidden md:flex items-center gap-1 bg-slate-900/60 p-1 rounded-xl border border-slate-900 navbar-bg";
            }
        }

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

        function filterKanbanAFazer() {
            const searchVal = document.getElementById('kanbanSearchInput').value.toLowerCase().trim();
            const cards = document.querySelectorAll('#col-afazer > div');
            
            cards.forEach(card => {
                const id = card.getAttribute('data-id').toLowerCase();
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

    # Toda a lógica redundante de plotagem do Plotly foi eliminada daqui para acelerar a API

    for _, row in df.iterrows():
        cid = str(row['codcli'])
        if cid not in KANBAN_STATE:
            KANBAN_STATE[cid] = "afazer"

    table_rows = ""
    kanban_buffers = {"afazer": "", "aguardando": "", "recusado": "", "aceito": ""}
    
    for _, row in df.iterrows():
        cid = str(row['codcli'])
        segmento = str(row.get('segmento', 'Não Informado'))
        categoria = str(row['categoria_problema'])
        solucao = str(row['servico_sugerido'])
        prioridade = str(row['prioridade_comercial'])
        tickets = str(row['qtd_tickets'])
        script_texto = str(row.get('script_abordagem', 'Script não gerado.'))

        cor_prio = "text-rose-500" if prioridade == "ALTA" else ("text-blue-400" if prioridade == "MÉDIA" else "text-slate-400")
        
        # Injeção das Linhas da Tabela
        table_rows += f"""
        <tr data-id="{cid}" data-segmento="{segmento}" data-priority="{prioridade}" data-cat="{categoria}" data-sug="{solucao}" onclick="loadLeadScript(this)" class="hover:bg-slate-900/40 cursor-pointer border-b border-slate-900/60 transition duration-150 group">
            <td class="px-5 py-3 font-semibold text-white val-text">#{cid}</td>
            <td class="px-5 py-3 text-slate-400 font-medium subtitle-text">{segmento}</td>
            <td class="px-5 py-3 text-blue-400 font-semibold">{categoria}</td>
            <td class="px-5 py-3 text-emerald-400 font-medium">{solucao}</td>
            <td class="px-5 py-3 text-right font-bold {cor_prio}">{prioridade} ({tickets})
                <div class="hidden hidden-script-source">{script_texto}</div>
            </td>
        </tr>
        """

        # Injeção dos Cards do Kanban
        status_atual = KANBAN_STATE.get(cid, "afazer")
        card_html = f"""
        <div data-id="{cid}" class="bg-slate-950 border border-slate-800 p-3.5 rounded-xl space-y-2 cursor-grab active:cursor-grabbing shadow-sm hover:border-slate-700 transition duration-150 kanban-card border-style">
            <div class="flex justify-between items-center"><span class="text-[11px] font-bold text-white val-text">#{cid}</span><span class="text-[9px] font-bold px-2 py-0.5 rounded-full bg-slate-900 text-slate-400 border border-slate-800 border-style">{tickets} Tickets</span></div>
            <p class="text-[11px] font-medium text-slate-400 truncate subtitle-text">{segmento}</p>
            <div class="text-[10px] font-semibold text-emerald-400 bg-emerald-500/5 px-2 py-1 rounded-md border border-emerald-500/10 truncate">{solucao}</div>
        </div>
        """
        if status_atual in kanban_buffers:
            kanban_buffers[status_atual] += card_html

    # Renderiza o HTML final substituindo as chaves criadas
    html_customizado = DASHBOARD_HTML\
        .replace("{{KPI_TOTAL}}", kpi_total)\
        .replace("{{KPI_ALTA}}", kpi_alta)\
        .replace("{{KPI_TICKETS}}", kpi_tickets)\
        .replace("{{KPI_TOP}}", kpi_top)\
        .replace("{{TABLE_ROWS}}", table_rows)\
        .replace("{{KANBAN_AFAZER}}", kanban_buffers["afazer"])\
        .replace("{{KANBAN_AGUARDANDO}}", kanban_buffers["aguardando"])\
        .replace("{{KANBAN_RECUSADO}}", kanban_buffers["recusado"])\
        .replace("{{KANBAN_ACEITO}}", kanban_buffers["aceito"])

    return html_customizado

@app.post("/api/kanban/save")
def save_kanban(data: KanbanUpdate):
    global KANBAN_STATE
    KANBAN_STATE[data.codcli] = data.nova_coluna
    return {"status": "success", "message": f"Cliente {data.codcli} movido para {data.nova_coluna}"}