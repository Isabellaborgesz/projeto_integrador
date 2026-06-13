from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse  # Adicione FileResponse aqui também
from pydantic import BaseModel
import pandas as pd
import plotly.express as px
import plotly.io as pio  # Cuidado: você escreveu "pi" mas é "pio"
import os
import json as _json

app = FastAPI()

@app.get("/logo-cti.png")
async def get_logo():
    return FileResponse("logo-cti.png") 

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

# --- TEMPLATE HTML DO DASHBOARD COMPLETO ---
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
        
        .card-top5 {
            transition: all 0.2s;
            cursor: pointer;
        }
        .card-top5:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.08);
        }
        .heatmap-cell {
            transition: transform 0.2s;
        }
        .heatmap-cell:hover {
            transform: scale(1.02);
        }

        /* ── CHATBOT FLUTUANTE ── */
        #chatbot-fab {
            position: fixed; bottom: 28px; right: 28px; z-index: 9999;
            width: 52px; height: 52px; border-radius: 50%;
            background: #2563eb; border: none; cursor: pointer;
            display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 20px rgba(37,99,235,0.45);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        #chatbot-fab:hover { transform: scale(1.08); box-shadow: 0 6px 28px rgba(37,99,235,0.55); }
        #chatbot-window {
            position: fixed; bottom: 92px; right: 28px; z-index: 9998;
            width: 360px; border-radius: 20px;
            display: flex; flex-direction: column;
            background: white; border: 1px solid #e2e8f0;
            box-shadow: 0 16px 48px rgba(0,0,0,0.14);
            transform: scale(0.92) translateY(12px); opacity: 0;
            pointer-events: none; transition: all 0.22s cubic-bezier(0.34,1.56,0.64,1);
        }
        .dark #chatbot-window { background: #0f172a; border-color: #1e293b; }
        #chatbot-window.open { transform: scale(1) translateY(0); opacity: 1; pointer-events: all; }
        #chatbot-messages {
            overflow-y: auto; padding: 16px;
            display: flex; flex-direction: column; gap: 10px;
            min-height: 280px; max-height: 360px;
        }
        .chat-msg {
            max-width: 82%; padding: 9px 13px; border-radius: 14px;
            font-size: 12px; line-height: 1.5; word-break: break-word;
        }
        .chat-msg.user { align-self: flex-end; background: #2563eb; color: white; border-bottom-right-radius: 4px; }
        .chat-msg.bot { align-self: flex-start; background: #f1f5f9; color: #1e293b; border-bottom-left-radius: 4px; }
        .dark .chat-msg.bot { background: #1e293b; color: #e2e8f0; }
        .chat-msg.typing { align-self: flex-start; background: #f1f5f9; color: #94a3b8; font-style: italic; }
        .dark .chat-msg.typing { background: #1e293b; }
    </style>
</head>
<body class="bg-slate-50 dark:bg-slate-950 min-h-screen text-slate-800 dark:text-slate-100 antialiased font-sans transition-colors duration-300">
    
    <div class="min-h-screen flex flex-col">
        
        <header class="border-b border-slate-200 dark:border-slate-900 bg-white/50 dark:bg-slate-950/50 backdrop-blur-md sticky top-0 z-50">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                <div class="flex items-center gap-8">
                    <div class="flex items-center gap-3">
                        <div class="h-8 w-8 rounded-lg bg-white flex items-center justify-center shadow-md shadow-blue-600/20 overflow-hidden p-1">
                            <img src="/logo-cti.png" alt="Logo CTI" class="w-full h-full object-contain">                        </div>
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
                        <p class="text-xs font-semibold text-slate-800 dark:text-slate-200">Leonardo</p>
                        <p class="text-[10px] text-slate-500 font-medium">Ecossistema CTI</p>
                    </div>
                    <a href="/" class="border border-slate-300 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-900/60 text-slate-600 dark:text-slate-400 hover:text-rose-500 dark:hover:text-rose-400 px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
                        Sair
                    </a>
                </div>
            </div>
        </header>

        <!-- TAB 1: PAINEL COMERCIAL -->
        <main id="tab-content-comercial" class="flex-grow w-full overflow-hidden" style="height: calc(100vh - 64px);">
            <div class="flex h-full">

                <!-- SIDEBAR -->
                <div class="w-80 flex-shrink-0 border-r border-slate-200 dark:border-slate-900 bg-white dark:bg-slate-950 flex flex-col h-full">
                    <div class="p-4 border-b border-slate-200 dark:border-slate-900 space-y-2">
                        <div class="relative">
                            <span class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-slate-400">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                            </span>
                            <input id="rec-search" type="text" placeholder="Buscar cliente ou servico..." oninput="recFiltrar()" class="w-full pl-8 pr-3 py-2 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg text-xs text-slate-700 dark:text-slate-300 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition">
                        </div>
                        <div class="flex gap-2">
                            <select id="rec-nivel" onchange="recFiltrar()" class="flex-1 border border-slate-200 dark:border-slate-800 rounded-lg px-2 py-1.5 bg-slate-50 dark:bg-slate-900 text-xs text-slate-600 dark:text-slate-400 focus:outline-none focus:border-blue-500">
                                <option value="">Todos os niveis</option>
                                <option value="A">Nivel A</option>
                                <option value="B">Nivel B</option>
                                <option value="C">Nivel C</option>
                            </select>
                            <select id="rec-seg" onchange="recFiltrar()" class="w-full mr-2 border border-slate-200 dark:border-slate-800 rounded-lg px-2 py-1.5 bg-slate-50 dark:bg-slate-900 text-xs text-slate-600 dark:text-slate-400 focus:outline-none focus:border-blue-500">
                                <option value="">Todos segmentos</option>
                            </select>
                        </div>
                        <div>
                            <select id="rec-consultor" onchange="recFiltrar()" class="w-full border border-slate-200 dark:border-slate-800 rounded-lg px-2 py-1.5 bg-slate-50 dark:bg-slate-900 text-xs text-slate-600 dark:text-slate-400 focus:outline-none focus:border-blue-500">
                                <option value="">Todos os consultores</option>
                                {{CONSULTOR_OPTIONS}}
                            </select>
                        </div>
                    </div>
                    <div id="rec-lista" class="flex-grow overflow-y-auto divide-y divide-slate-100 dark:divide-slate-900/60"></div>
                    <div class="flex items-center justify-between px-4 py-2 border-t border-slate-200 dark:border-slate-900 bg-slate-50 dark:bg-slate-950">
                        <button onclick="recPaginar(-1)" class="text-xs text-slate-500 hover:text-blue-500 font-medium transition">&#8592; Anterior</button>
                        <span class="text-[11px] text-slate-400 font-mono" id="rec-pag-info"></span>
                        <button onclick="recPaginar(1)" class="text-xs text-slate-500 hover:text-blue-500 font-medium transition">Proxima &#8594;</button>
                    </div>
                </div>

                <!-- PAINEL DIREITO -->
                <div class="flex-grow overflow-y-auto bg-slate-50 dark:bg-slate-950/60 p-6">

                    <!-- Estado vazio -->
                    <div id="rec-vazio" class="flex flex-col items-center justify-center h-full text-center text-slate-400 dark:text-slate-600 gap-3">
                        <svg class="w-10 h-10 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
                        <p class="text-sm font-medium">Selecione um cliente na lista para ver as recomendacoes</p>
                    </div>

                    <!-- Detalhamento do cliente -->
                    <div id="rec-detalhe" class="hidden space-y-5 max-w-4xl mx-auto">

                        <!-- Header -->
                        <div class="flex items-start justify-between">
                            <div>
                                <h2 class="text-xl font-bold text-slate-900 dark:text-white" id="rec-nome">Cliente #0000</h2>
                                <p class="text-sm text-slate-500 mt-0.5" id="rec-sub">Segmento | Nivel</p>
                            </div>
                            <div class="flex gap-2">
                                <a id="rec-email-btn" href="#" class="flex items-center gap-1.5 border border-slate-200 dark:border-slate-800 hover:border-blue-400 text-slate-600 dark:text-slate-400 hover:text-blue-500 px-3 py-1.5 rounded-lg text-xs font-medium transition">
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                                    Email
                                </a>
                                <a id="rec-whats-btn" href="#" target="_blank" class="flex items-center gap-1.5 border border-slate-200 dark:border-slate-800 hover:border-emerald-400 text-slate-600 dark:text-slate-400 hover:text-emerald-500 px-3 py-1.5 rounded-lg text-xs font-medium transition">
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path></svg>
                                    WhatsApp
                                </a>
                            </div>
                        </div>

                        <!-- Servicos ativos -->
                        <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 rounded-xl p-5">
                            <p class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-3">&#x1F4CB; Servicos ativos contratados</p>
                            <div id="rec-servicos" class="flex flex-wrap gap-2"></div>
                        </div>

                        <!-- Oportunidade -->
                        <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 rounded-xl p-5">
                            <div class="flex items-center justify-between">
                                <div>
                                    <p class="text-base font-bold text-blue-600 dark:text-blue-400">&#x1F680; Oportunidade detectada</p>
                                    <p class="text-sm text-slate-600 dark:text-slate-400 mt-1">O algoritmo recomenda a oferta de <strong id="rec-servico-rec" class="text-slate-900 dark:text-white"></strong></p>
                                </div>
                                <span id="rec-score-badge" class="flex-shrink-0 ml-4 text-sm font-bold px-4 py-2 rounded-xl bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20">Score 0</span>
                            </div>
                        </div>

                        <!-- Justificativas -->
                        <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 rounded-xl p-5">
                            <div class="flex items-center justify-between mb-4">
                                <p class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider" id="rec-just-titulo">Justificativas</p>
                                <button onclick="recToggleJust()" id="rec-just-btn" class="text-xs text-blue-500 hover:text-blue-400 font-medium transition">Ver todas</button>
                            </div>
                            <div id="rec-justificativas" class="space-y-3"></div>
                        </div>

                    </div>
                </div>
            </div>
        </main>
        <!-- TAB 2: KANBAN -->
        <main id="tab-content-novo-modulo" class="hidden flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-900 pb-6">
                <div>
                    <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-3xl">Painel de Chamados & Negocios</h1>
                    <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Gerencie a evolucao das propostas comerciais arrastando os cards atraves das etapas do funil.</p>
                </div>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 items-start min-h-[550px]">
                
                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] shadow-sm">
                    <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-3">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-blue-600 dark:text-blue-400">A Fazer Proposta</h3>
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
                        <h3 class="text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">Aguardando Respostas</h3>
                        <span class="bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/20 text-amber-600 dark:text-amber-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-aguardando">0</span>
                    </div>
                    <div id="col-aguardando" data-status="aguardando" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        {{KANBAN_AGUARDANDO}}
                    </div>
                </div>

                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] shadow-sm">
                    <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400">Recusado</h3>
                        <span class="bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-600 dark:text-rose-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-recusado">0</span>
                    </div>
                    <div id="col-recusado" data-status="recusado" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        {{KANBAN_RECUSADO}}
                    </div>
                </div>

                <div class="bg-white dark:bg-slate-900/40 border border-slate-200 dark:border-slate-900 rounded-xl p-4 flex flex-col h-full min-h-[500px] shadow-sm">
                    <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3 mb-4">
                        <h3 class="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Aceito</h3>
                        <span class="bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-[11px] font-bold px-2 py-0.5 rounded-full" id="count-aceito">0</span>
                    </div>
                    <div id="col-aceito" data-status="aceito" class="kanban-zone flex-grow space-y-2 overflow-y-auto max-h-[500px] pb-6">
                        {{KANBAN_ACEITO}}
                    </div>
                </div>
            </div>
        </main>

        <!-- TAB 3: CHURN - LAYOUT REORGANIZADO -->
        <main id="tab-content-churn" class="hidden flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
            
            <div class="border-b border-slate-200 dark:border-slate-900 pb-6 mb-6">
                <h1 class="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-3xl">Análise de Risco de Churn</h1>
                <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Score calculado por nível do cliente, portfólio de serviços e oportunidades não aproveitadas.</p>
            </div>

            <!-- LINHA 1: TOP 5 CARDS (HORIZONTAL) -->
            <div class="mb-8">
                <h2 class="text-sm font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-4">Top 5 Segmentos em Risco</h2>
                <div id="top5-cards" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                    <div class="text-center text-slate-400 py-8 col-span-full">Carregando dados...</div>
                </div>
            </div>

            <!-- LINHA 2: GRAFICO BARRAS (ESQUERDA) + GRAFICO ROSCA (DIREITA) -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                
                <!-- Grafico de Barras Horizontal -->
                <div class="bg-white dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
                    <h3 class="text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-3">Score Medio por Segmento</h3>
                    <p class="text-[10px] text-slate-400 dark:text-slate-500 mb-3">Top 10 segmentos com maior risco medio</p>
                    <div id="churn-bar-chart" style="height: 360px;"></div>
                </div>

                <!-- Grafico de Rosca -->
                <div class="bg-white dark:bg-slate-900/30 border border-slate-200 dark:border-slate-800 rounded-xl p-4">
                    <h3 class="text-xs font-bold text-slate-600 dark:text-slate-400 uppercase tracking-wider mb-3">Top Oportunidades por Servico</h3>
                    <p class="text-[10px] text-slate-400 dark:text-slate-500 mb-3">Servicos mais recomendados na base de clientes</p>
                    <div id="churn-donut-chart" style="height: 280px;"></div>
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
            if (churnLoaded) {
                renderBarChart();
                renderDonutChart();
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

        // ── PAINEL COMERCIAL (Recomendacoes) ─────────────────────────────────────
        var recTodos = [], recFiltrados = [], recPagAtual = 1, recTamPag = 25;
        var recClienteAtivo = null, recJustExpandido = false;

        function recInit() {
            fetch('/api/recomendacoes')
                .then(function(r){ return r.json(); })
                .then(function(dados){
                    recTodos = dados;
                    recFiltrados = dados.slice();
                    // Popular segmentos
                    var segs = [...new Set(dados.map(function(r){ return r.segmento; }))].sort();
                    var sel = document.getElementById('rec-seg');
                    if (sel) segs.forEach(function(s){ var o = document.createElement('option'); o.value=s; o.textContent=s; sel.appendChild(o); });
                    recRenderLista();
                })
                .catch(function(e){ console.error('Erro ao carregar recomendacoes:', e); });
        }

        var recConsultorAtivo = '';
        function recFiltrar() {
            var q = (document.getElementById('rec-search').value||'').toLowerCase();
            var nivel = document.getElementById('rec-nivel').value;
            var seg = document.getElementById('rec-seg').value;
            var consultor = document.getElementById('rec-consultor').value;

            // Se o consultor mudou, recarrega dados da API com o novo consultor
            if (consultor !== recConsultorAtivo) {
                recConsultorAtivo = consultor;
                var url = consultor ? '/api/recomendacoes?consultor=' + encodeURIComponent(consultor) : '/api/recomendacoes';
                fetch(url)
                    .then(function(r){ return r.json(); })
                    .then(function(dados){
                        recTodos = dados;
                        recFiltrados = dados.filter(function(r){
                            var mq = !q || String(r.codcli).includes(q) || r.servico_recomendado.toLowerCase().includes(q) || r.segmento.toLowerCase().includes(q);
                            var mn = !nivel || r.nivel_cliente === nivel;
                            var ms = !seg || r.segmento === seg;
                            return mq && mn && ms;
                        });
                        recPagAtual = 1;
                        recRenderLista();
                    });
                return;
            }

            recFiltrados = recTodos.filter(function(r){
                var mq = !q || String(r.codcli).includes(q) || r.servico_recomendado.toLowerCase().includes(q) || r.segmento.toLowerCase().includes(q);
                var mn = !nivel || r.nivel_cliente === nivel;
                var ms = !seg || r.segmento === seg;
                return mq && mn && ms;
            });
            recPagAtual = 1;
            recRenderLista();
        }

        function recPaginar(dir) {
            var total = Math.ceil(recFiltrados.length / recTamPag);
            recPagAtual = Math.max(1, Math.min(recPagAtual + dir, total));
            recRenderLista();
        }

        function recRenderLista() {
            var start = (recPagAtual - 1) * recTamPag;
            var pagina = recFiltrados.slice(start, start + recTamPag);
            var totalPag = Math.ceil(recFiltrados.length / recTamPag) || 1;
            var lista = document.getElementById('rec-lista');
            if (!lista) return;
    
            var nivelCls = {
                'A': 'text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border-emerald-200 dark:border-emerald-500/20',
                'B': 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20',
                'C': 'text-rose-500 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/20'
            };

            lista.innerHTML = pagina.map(function(r) {
                var isAtivo = recClienteAtivo && recClienteAtivo.codcli === r.codcli && recClienteAtivo.servico_recomendado === r.servico_recomendado;
                var activeCls = isAtivo ? 'bg-blue-50 dark:bg-blue-500/10 border-l-2 border-l-blue-500' : 'hover:bg-slate-50 dark:hover:bg-slate-900/40';
                var nc = nivelCls[r.nivel_cliente] || 'text-slate-500 bg-slate-100 border-slate-200';
                
                // CORREÇÃO: usar uma função separada em vez de inline onclick
                var id = r.codcli;
                
                return '<div data-codcli="' + id + '" data-servico="' + r.servico_recomendado + '" class="rec-item px-4 py-3 cursor-pointer transition ' + activeCls + '">'
                    + '<div class="flex justify-between items-center">'
                    + '<span class="text-sm font-bold text-slate-800 dark:text-white">Cliente #' + r.codcli + '</span>'
                    + '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full border ' + nc + '">Nivel ' + r.nivel_cliente + '</span>'
                    + '</div>'
                    + '<p class="text-[11px] text-amber-600 dark:text-amber-400 font-semibold mt-0.5">&#x1F4A1; ' + r.servico_recomendado + ' <span class="text-slate-400 font-mono">' + Math.round(r.score) + '</span></p>'
                    + '</div>';
            }).join('');

            // Adicionar event listeners para os itens
            document.querySelectorAll('.rec-item').forEach(function(item) {
                item.addEventListener('click', function() {
                    var codcli = parseInt(this.dataset.codcli);
                    var servico = this.dataset.servico;
                    var cliente = recTodos.find(function(r) { return r.codcli === codcli && r.servico_recomendado === servico; });
                    if (!cliente) cliente = recTodos.find(function(r) { return r.codcli === codcli; });
                    if (cliente) recSelecionar(cliente);
                });
            });

            document.getElementById('rec-pag-info').textContent = recPagAtual + ' / ' + totalPag;
        }

        function recSelecionar(r) {
            // Não faça JSON.parse! r já é o objeto
            recClienteAtivo = r;
            recJustExpandido = false;

            document.getElementById('rec-vazio').classList.add('hidden');
            document.getElementById('rec-detalhe').classList.remove('hidden');

            document.getElementById('rec-nome').textContent = 'Cliente #' + r.codcli;
            document.getElementById('rec-sub').textContent = 'Segmento: ' + r.segmento + ' | Nivel ' + r.nivel_cliente;
            document.getElementById('rec-email-btn').href = 'mailto:cliente' + r.codcli + '@cti.com.br';
            document.getElementById('rec-whats-btn').href = 'https://wa.me/5511999999999?text=' + encodeURIComponent('Ola, cliente CTI #' + r.codcli + ' - recomendamos: ' + r.servico_recomendado);

            // Servicos
            var srvs = r.servicos_atuais || [];
            document.getElementById('rec-servicos').innerHTML = srvs.map(function(s){
                return '<span class="text-[11px] font-semibold px-3 py-1 rounded-full border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-400">' + s + '</span>';
            }).join('');

            // Oportunidade
            document.getElementById('rec-servico-rec').textContent = r.servico_recomendado;
            document.getElementById('rec-score-badge').textContent = 'Score ' + Math.round(r.score);

            // Justificativas (top 3)
            recRenderJust(r, false);

            // Atualizar contexto do chatbot
            window.recClienteAtivoGlobal = r;

            recRenderLista();
        }

        function recRenderJust(r, todas) {
            var justs = r.justificativas || [];
            var lista = todas ? justs : justs.slice(0, 3);
            var total = justs.length;
            // DEBUG: inspecionar os dados que chegam
            if (lista.length > 0) {
                console.log('[DEBUG] justificativa[0]:', JSON.stringify(lista[0]));
                console.log('[DEBUG] percentual_base:', lista[0].percentual_base, typeof lista[0].percentual_base);
            }
            document.getElementById('rec-just-btn').textContent = todas ? 'Ver menos' : 'Ver todas';
            document.getElementById('rec-just-titulo').textContent = todas
                ? 'Justificativas (todas as ' + total + ')'
                : 'Justificativas';
            document.getElementById('rec-justificativas').innerHTML = lista.map(function(j){
                var origens = j.tipo_regra === 'dupla'
                    ? '<strong>' + (j.origem||'') + '</strong>'
                    : '<strong>' + (j.origem_1||'') + '</strong> e <strong>' + (j.origem_2||'') + '</strong>';
                var pb = parseFloat(j.percentual_base);
                var pbTexto = (!isNaN(pb) && pb > 0) ? pb.toFixed(2) + '%' : 'N/A';
                return '<div class="p-3.5 bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 rounded-xl">'
                    + '<p class="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">'
                    + j.percentual_relacao.toFixed(1) + '% dos clientes que possuem ' + origens
                    + ' tambem possuem <strong class="text-slate-800 dark:text-white">' + j.destino + '</strong>.'
                    + '</p>'
                    + '<div class="flex gap-2 mt-2 flex-wrap">'
                    + '<span class="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-500/20">&#x1F4C8; Lift: ' + j.lift.toFixed(2) + '</span>'
                    + '<span class="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-violet-50 dark:bg-violet-500/10 text-violet-600 dark:text-violet-400 border border-violet-100 dark:border-violet-500/20">&#x1F517; Relacao: ' + j.percentual_relacao.toFixed(2) + '%</span>'
                    + '<span class="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-amber-50 dark:bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-100 dark:border-amber-500/20">&#x1F4CA; Media da carteira: ' + pbTexto + '</span>'
                    + '</div></div>';
            }).join('');
        }

        function recToggleJust() {
            if (!recClienteAtivo) return;
            recJustExpandido = !recJustExpandido;
            recRenderJust(recClienteAtivo, recJustExpandido);
        }

        function filterKanbanAFazer() {
            const search = document.getElementById('kanbanSearchInput').value.toLowerCase();
            document.querySelectorAll('#col-afazer > div').forEach(card => {
                const id = (card.dataset.id || '').toLowerCase();
                card.style.display = !search || id.includes(search) ? '' : 'none';
            });
        }

        function calculateCounters() {
            document.getElementById('count-afazer').textContent = document.querySelectorAll('#col-afazer > div').length;
            document.getElementById('count-aguardando').textContent = document.querySelectorAll('#col-aguardando > div').length;
            document.getElementById('count-recusado').textContent = document.querySelectorAll('#col-recusado > div').length;
            document.getElementById('count-aceito').textContent = document.querySelectorAll('#col-aceito > div').length;
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
            if (tabId === 'churn' && !churnLoaded) initChurnVisual();
        }

        // ======================================================================
        // CHURN
        // ======================================================================

        let churnLoaded = false;
        let churnSegmentos = [];
        let churnServicosPorSegmento = {};
        let churnServicoRecPorSegmento = {};
        let churnDataGlobal = null;

        function initChurnVisual() {
            churnLoaded = true;
            
            const jsonEl = document.getElementById('churn-json-data');
            if (!jsonEl) return;
            
            try {
                const data = JSON.parse(jsonEl.textContent);
                if (data && data.segmentos) {
                    churnSegmentos = data.segmentos;
                    churnServicosPorSegmento = data.servicos_por_segmento || {};
                    churnServicoRecPorSegmento = data.servico_rec_por_segmento || {};
                    churnDataGlobal = data;
                    
                    renderTop5Cards();
                    renderBarChart();
                    renderDonutChart();
                } else {
                    showChurnFallback();
                }
            } catch(e) {
                console.error('Erro ao carregar churn:', e);
                showChurnFallback();
            }
        }

        function getRiscoInfo(taxa) {
            if (taxa >= 60) return { bg: 'bg-rose-500', text: 'text-rose-500', label: 'Alto', cor: '#ef4444' };
            if (taxa >= 35) return { bg: 'bg-amber-500', text: 'text-amber-500', label: 'Medio', cor: '#f59e0b' };
            return { bg: 'bg-emerald-500', text: 'text-emerald-500', label: 'Baixo', cor: '#10b981' };
        }

        function renderTop5Cards() {
            const container = document.getElementById('top5-cards');
            const top5 = [...churnSegmentos].sort((a,b) => b.taxa_churn - a.taxa_churn).slice(0, 5);
            
            if (top5.length === 0) {
                container.innerHTML = '<div class="text-center text-slate-400 py-8 col-span-full">Nenhum dado disponivel</div>';
                return;
            }
            
            container.innerHTML = top5.map((seg, idx) => {
                const risco = seg.taxa_churn;
                const cor = getRiscoInfo(risco);
                const posicao = idx + 1;
                const label = risco >= 80 ? 'CRITICO' : risco >= 60 ? 'ALTO' : 'MEDIO';
                const badgeCl = risco >= 60
                    ? 'bg-rose-50 dark:bg-rose-500/10 text-rose-500 border-rose-200 dark:border-rose-500/20'
                    : 'bg-amber-50 dark:bg-amber-500/10 text-amber-600 border-amber-200 dark:border-amber-500/20';
                const barCor = risco >= 60 ? '#ef4444' : '#f59e0b';

                const servicosReais = churnServicosPorSegmento[seg.segmento] || [];
                const servicoRec = churnServicoRecPorSegmento[seg.segmento] || null;

                // Tags dos serviços que já tem
                const tagsTem = servicosReais.map(s =>
                    `<span class="inline-flex items-center text-[10px] px-2 py-0.5 rounded-md border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-500 dark:text-slate-400 mb-1">${s.length > 28 ? s.substring(0,26)+'..' : s}</span>`
                ).join('');

                // Tag do serviço recomendado (em vermelho)
                const tagRec = servicoRec
                    ? `<span class="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md border border-rose-200 dark:border-rose-500/30 bg-rose-50 dark:bg-rose-500/10 text-rose-600 dark:text-rose-400 mb-1 font-semibold"><span style="font-size:9px">&#x2605;</span>${servicoRec.length > 28 ? servicoRec.substring(0,26)+'..' : servicoRec}</span>`
                    : '';

                return `
                    <div class="bg-white dark:bg-slate-900/50 border-l-4 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm" style="border-left-color:${barCor}">
                        <div class="flex justify-between items-start mb-2">
                            <div class="flex items-center gap-1.5 min-w-0">
                                <span class="text-sm font-bold text-slate-400 flex-shrink-0">#${posicao}</span>
                                <h3 class="font-bold text-slate-800 dark:text-white text-sm leading-tight" title="${seg.segmento}">${seg.segmento.length > 30 ? seg.segmento.substring(0,28)+'...' : seg.segmento}</h3>
                            </div>
                            <span class="text-[10px] font-bold px-2 py-0.5 rounded-full border flex-shrink-0 ml-1 ${badgeCl}">${label}</span>
                        </div>
                        <div class="text-[10px] text-slate-400 mb-2">${seg.nivel_c} de ${seg.total} clientes Nivel C</div>
                        <div class="flex items-center gap-2 mb-3">
                            <div class="flex-1 h-1.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                <div style="width:${risco}%;background:${barCor}" class="h-full rounded-full"></div>
                            </div>
                            <span class="text-xs font-bold font-mono flex-shrink-0" style="color:${barCor}">${risco}%</span>
                        </div>
                        <div class="text-[9px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">Portfolio de servicos</div>
                        <div class="flex flex-wrap gap-1">${tagsTem}${tagRec}</div>
                        ${servicoRec ? '<p class="text-[9px] text-rose-400 mt-1.5">&#x2605; vermelho = oportunidade recomendada</p>' : ''}
                    </div>
                `;
            }).join('');
        }

        function renderHeatmapResumido() {
            const container = document.getElementById('heatmap-resumido');
            if (!container) return;
            const filtered = churnSegmentos.filter(s => s.taxa_churn >= 35);
            const sorted = [...filtered].sort((a,b) => b.taxa_churn - a.taxa_churn);
            
            if (sorted.length === 0) {
                container.innerHTML = '<div class="col-span-full text-center text-slate-400 py-6 text-xs">Nenhum segmento em alto ou medio risco</div>';
                return;
            }
            
            container.innerHTML = sorted.map(seg => {
                const risco = seg.taxa_churn;
                const cor = getRiscoInfo(risco);
                return `
                    <div class="heatmap-cell ${cor.bg} bg-opacity-20 dark:bg-opacity-30 rounded-md p-2 text-center">
                        <div class="text-[9px] font-medium text-slate-700 dark:text-slate-300 truncate" title="${seg.segmento}">${seg.segmento.length > 18 ? seg.segmento.substring(0,15)+'...' : seg.segmento}</div>
                        <div class="text-xs font-bold ${cor.text} mt-0.5">${risco}%</div>
                    </div>
                `;
            }).join('');
        }

        function renderBarChart() {
            // Inverter: maior risco em cima no gráfico horizontal (Plotly inverte eixo Y)
            const top10 = [...churnSegmentos].sort((a,b) => a.taxa_churn - b.taxa_churn).slice(-10);
            const isDark = document.documentElement.classList.contains('dark');
            const gridColor = isDark ? '#1e293b' : '#e2e8f0';
            const textColor = isDark ? '#94a3b8' : '#64748b';
            
            const barColors = top10.map(s => s.taxa_churn >= 60 ? '#ef4444' : (s.taxa_churn >= 35 ? '#f59e0b' : '#10b981'));
            
            const data = [{
                type: 'bar',
                orientation: 'h',
                x: top10.map(s => s.taxa_churn),
                y: top10.map(s => s.segmento.length > 28 ? s.segmento.substring(0,25) + '...' : s.segmento),
                text: top10.map(s => s.taxa_churn + '%'),
                textposition: 'outside',
                marker: { color: barColors, line: { width: 0 } },
                hovertemplate: '<b>%{y}</b><br>Taxa de Churn: %{x}%<br>Clientes Nivel C: %{customdata}<extra></extra>',
                customdata: top10.map(s => s.nivel_c + ' de ' + s.total)
            }];
            
            const layout = {
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)',
                font: { color: textColor, family: 'Inter', size: 10 },
                margin: { l: 145, r: 45, t: 10, b: 20 },
                xaxis: { 
                    showgrid: true, 
                    gridcolor: gridColor, 
                    title: { text: 'Clientes Nivel C (%)', font: { size: 9 } },
                    range: [0, 105]
                },
                yaxis: { showgrid: false, title: '' },
                height: 340
            };
            
            Plotly.newPlot('churn-bar-chart', data, layout, { displayModeBar: false, responsive: true });
        }

        function renderDonutChart() {
            if (!churnDataGlobal || !churnServicoRecPorSegmento) return;
            const isDark = document.documentElement.classList.contains('dark');

            // Contar quantas vezes cada servico aparece como recomendado
            const contagem = {};
            Object.values(churnServicoRecPorSegmento).forEach(function(sv) {
                contagem[sv] = (contagem[sv] || 0) + 1;
            });

            // Ordenar e pegar top 8
            const sorted = Object.entries(contagem).sort((a,b) => b[1]-a[1]).slice(0, 8);
            const labels = sorted.map(e => e[0].length > 30 ? e[0].substring(0,28)+'..' : e[0]);
            const values = sorted.map(e => e[1]);

            const cores = ['#3b82f6','#8b5cf6','#06b6d4','#10b981','#f59e0b','#ef4444','#ec4899','#64748b'];

            const plotData = [{
                type: 'pie',
                hole: 0.58,
                labels: labels,
                values: values,
                marker: {
                    colors: cores,
                    line: { color: isDark ? '#0f172a' : '#f8fafc', width: 2 }
                },
                textinfo: 'percent',
                textposition: 'inside',
                insidetextorientation: 'radial',
                hovertemplate: '<b>%{label}</b><br>Recomendado em %{value} segmento(s)<br>%{percent}<extra></extra>'
            }];

            const layout = {
                plot_bgcolor: 'rgba(0,0,0,0)',
                paper_bgcolor: 'rgba(0,0,0,0)',
                font: { color: isDark ? '#94a3b8' : '#64748b', family: 'Inter', size: 10 },
                margin: { l: 10, r: 10, t: 10, b: 80 },
                showlegend: true,
                legend: { orientation: 'h', yanchor: 'top', y: -0.18, xanchor: 'center', x: 0.5, font: { size: 9 }, tracegroupgap: 6 }
            };

            Plotly.newPlot('churn-donut-chart', plotData, layout, { displayModeBar: false, responsive: true });
        }

        function showChurnFallback() {
            document.getElementById('top5-cards').innerHTML = '<div class="text-center text-slate-400 py-8 col-span-full">Dados nao disponiveis</div>';
            const _hm = document.getElementById('heatmap-resumido'); if (_hm) _hm.innerHTML = '<div class="col-span-full text-center text-slate-400 py-6 text-xs">Dados nao disponiveis</div>';
        }

        document.addEventListener('DOMContentLoaded', function() {
            recInit();
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

    <!-- ── CHATBOT FLUTUANTE ── -->
    <button id="chatbot-fab" title="Assistente CTI">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
    </button>

    <div id="chatbot-window">
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/60 rounded-t-[20px]">
            <div class="flex items-center gap-2.5">
                <div class="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center flex-shrink-0">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><path d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
                </div>
                <div>
                    <p class="text-xs font-bold text-slate-800 dark:text-white leading-none">Assistente CTI</p>
                    <p class="text-[10px] text-slate-400 mt-0.5">Motor de Oportunidades B2B</p>
                </div>
            </div>
            <button id="chatbot-close" class="p-1.5 rounded-lg hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>
        </div>
        <!-- Mensagens -->
        <div id="chatbot-messages">
            <div class="chat-msg bot">Ola! Sou o assistente do Motor de Oportunidades CTI. Posso responder duvidas sobre clientes, sugerir acoes comerciais e gerar scripts de abordagem. Como posso ajudar?</div>
        </div>
        <!-- Input -->
        <div class="flex items-center gap-2 px-3 py-3 border-t border-slate-200 dark:border-slate-800">
            <input id="chatbot-input" type="text" placeholder="Digite sua mensagem..." class="flex-1 text-xs px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 text-slate-800 dark:text-slate-200 placeholder-slate-400 focus:outline-none focus:border-blue-500 transition">
            <button id="chatbot-send" class="w-8 h-8 flex-shrink-0 rounded-xl bg-blue-600 hover:bg-blue-500 flex items-center justify-center transition shadow-sm">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
        </div>
    </div>

    <script>
        // ── CHATBOT ──────────────────────────────────────────────
        const WEBHOOK_URL = 'https://cti12dias.app.n8n.cloud/webhook/cti12dias';
        const chatFab     = document.getElementById('chatbot-fab');
        const chatWindow  = document.getElementById('chatbot-window');
        const chatClose   = document.getElementById('chatbot-close');
        const chatMsgs    = document.getElementById('chatbot-messages');
        const chatInput   = document.getElementById('chatbot-input');
        const chatSend    = document.getElementById('chatbot-send');

        chatFab.addEventListener('click', function() {
            chatWindow.classList.toggle('open');
            if (chatWindow.classList.contains('open')) chatInput.focus();
        });
        chatClose.addEventListener('click', function() { chatWindow.classList.remove('open'); });

        function chatAddMsg(texto, tipo) {
            var div = document.createElement('div');
            div.className = 'chat-msg ' + tipo;
            div.textContent = texto;
            chatMsgs.appendChild(div);
            chatMsgs.scrollTop = chatMsgs.scrollHeight;
            return div;
        }

        function chatGetContexto() {
            var abaAtiva = 'comercial';
            ['comercial','novo-modulo','churn'].forEach(function(id) {
                var el = document.getElementById('tab-content-' + id);
                if (el && !el.classList.contains('hidden')) abaAtiva = id;
            });

            if (window.recClienteAtivoGlobal) {
                var r = window.recClienteAtivoGlobal;
                return {
                    codigo: r.codcli,
                    segmento: r.segmento,
                    nivel: r.nivel_cliente,
                    score: r.score,
                    servico_recomendado: r.servico_recomendado,
                    servicos_atuais: r.servicos_atuais,
                    total_justificativas: (r.justificativas||[]).length,
                    justificativas: (r.justificativas||[]).slice(0,5).map(function(j){
                        return {
                            tipo: j.tipo_regra,
                            origem: j.origem || ((j.origem_1||'') + ' + ' + (j.origem_2||'')),
                            destino: j.destino,
                            lift: j.lift.toFixed(2),
                            percentual_relacao: j.percentual_relacao + '%',
                            confianca: j.score_regra || null
                        };
                    })
                };
            }
            return { aba: abaAtiva, cliente: null };
        }

                async function chatEnviar() {
            var msg = chatInput.value.trim();
            if (!msg) return;
            chatInput.value = '';
            chatAddMsg(msg, 'user');

            var typing = chatAddMsg('Digitando...', 'typing');

            try {
                var resp = await fetch(WEBHOOK_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ pergunta: msg, contexto: chatGetContexto() })
                });
                var texto = await resp.text();
                typing.remove();
                try {
                    var data = JSON.parse(texto);
                    var resposta = data.output || data.resposta || data.text || data.message || (Array.isArray(data) && data[0] && data[0].output) || JSON.stringify(data);
                    chatAddMsg(resposta, 'bot');
                } catch(e) {
                    chatAddMsg(texto, 'bot');
                }
            } catch(err) {
                typing.remove();
                chatAddMsg('Erro ao conectar com o assistente. Tente novamente.', 'bot');
            }
        }

        chatSend.addEventListener('click', chatEnviar);
        chatInput.addEventListener('keypress', function(e) { if (e.key === 'Enter') chatEnviar(); });
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
        erro_msg = "<div class='bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-600 dark:text-rose-400 p-3 rounded-xl mb-5 text-center text-xs font-semibold shadow-sm'>As credenciais informadas nao coincidem.</div>"
        return LOGIN_HTML.replace("", erro_msg)
    
    # --- CARREGAR OPORTUNIDADES ---
    caminhos_oportunidades = [
        os.path.join("output", "oportunidades.xlsx"),
        "oportunidades.xlsx",
    ]
    
    df = None
    for p in caminhos_oportunidades:
        if os.path.exists(p):
            df = pd.read_excel(p)
            break
    
    if df is None or df.empty:
        df = pd.DataFrame({'codcli': [], 'segmento': [], 'categoria_problema': [], 'qtd_tickets': [], 'servico_sugerido': [], 'prioridade_comercial': []})
    
    kpi_total = str(len(df))
    kpi_alta = str(len(df[df['prioridade_comercial'] == 'ALTA'])) if 'prioridade_comercial' in df.columns else "0"
    kpi_tickets = str(df['qtd_tickets'].sum()) if 'qtd_tickets' in df.columns else "0"
    kpi_top = str(df['servico_sugerido'].mode()[0]) if not df.empty and 'servico_sugerido' in df.columns else "N/A"
    
    # --- GRAFICOS ---
    if not df.empty and 'categoria_problema' in df.columns:
        fig_cat = px.bar(df['categoria_problema'].value_counts().reset_index(), x='categoria_problema', y='count')
        fig_cat.update_traces(marker_color='#2563eb')
        fig_cat.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8', margin=dict(l=0, r=0, t=10, b=0), height=240)
        html_g1 = pio.to_html(fig_cat, full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})
    else:
        html_g1 = "<p class='text-center text-slate-400'>Dados nao disponiveis</p>"
    
    if not df.empty and 'prioridade_comercial' in df.columns:
        fig_prio = px.pie(df, names='prioridade_comercial', hole=0.7, color='prioridade_comercial', color_discrete_map={'ALTA':'#f43f5e', 'MEDIA':'#3b82f6', 'BAIXA':'#64748b'})
        fig_prio.update_traces(textinfo='none')
        fig_prio.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color='#94a3b8', margin=dict(l=0, r=0, t=10, b=0), height=240, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
        html_g2 = pio.to_html(fig_prio, full_html=False, include_plotlyjs='cdn', config={'displayModeBar': False})
    else:
        html_g2 = "<p class='text-center text-slate-400'>Dados nao disponiveis</p>"
    
    # --- KANBAN ---
    for _, row in df.iterrows():
        cid = str(row.get('codcli', ''))
        if cid and cid not in KANBAN_STATE:
            KANBAN_STATE[cid] = "afazer"
    
    table_rows = ""
    kanban_buffers = {"afazer": "", "aguardando": "", "recusado": "", "aceito": ""}
    
    for _, row in df.iterrows():
        cid = str(row.get('codcli', ''))
        segmento = str(row.get('segmento', 'Nao Informado'))
        categoria = str(row.get('categoria_problema', ''))
        solucao = str(row.get('servico_sugerido', ''))
        prioridade = str(row.get('prioridade_comercial', 'MEDIA'))
        tickets = str(row.get('qtd_tickets', '0'))
        
        servico_atual = str(row.get('servicos_contratados', 'Nenhum'))
        script_texto = str(row.get('script_vendas', f"Ola, identificamos chamados sobre {categoria} e sugerimos a solucao {solucao}.")).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        cor_prio = "text-rose-500" if prioridade == "ALTA" else ("text-blue-500" if prioridade == "MEDIA" else "text-slate-500")
        
        table_rows += f"""
        <tr data-id="{cid}" data-segmento="{segmento}" data-priority="{prioridade}" data-cat="{categoria}" data-sug="{solucao}" data-servico="{servico_atual}" onclick="loadLeadScript(this)" class="hover:bg-slate-100 dark:hover:bg-slate-900/40 cursor-pointer border-b border-slate-200 dark:border-slate-900/60">
            <td class="px-5 py-3 font-semibold">#{cid}</td>
            <td class="px-5 py-3">{segmento}</td>
            <td class="px-5 py-3 text-amber-600">{servico_atual}</td>
            <td class="px-5 py-3 text-blue-600">{categoria}</td>
            <td class="px-5 py-3 text-emerald-600">{solucao}</td>
            <td class="px-5 py-3 text-right font-bold {cor_prio}">{prioridade}
                <div class="hidden hidden-script-source">{script_texto}</div>
            </td>
          </table>
        """
        
        status_atual = KANBAN_STATE.get(cid, "afazer")
        card_html = f"""
        <div data-id="{cid}" class="bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800 p-3 rounded-xl space-y-1 cursor-grab shadow-sm">
            <div class="flex justify-between"><span class="text-[11px] font-bold">#{cid}</span><span class="text-[9px] px-2 py-0.5 rounded-full bg-slate-100">{tickets} Tickets</span></div>
            <p class="text-[11px] truncate">{segmento}</p>
            <div class="text-[10px] text-emerald-600 bg-emerald-50 px-2 py-1 rounded truncate">{solucao}</div>
        </div>
        """
        if status_atual in kanban_buffers:
            kanban_buffers[status_atual] += card_html
    
    # --- CHURN DATA ---
    churn_json_str = "{}"
    # Clientes CTI.xlsx tem codcli + segmento + nivel_cliente + servico
    caminhos_clientes = [
        os.path.join("data", "raw", "Clientes CTI.xlsx"),
        os.path.join("data", "raw", "schurn.xlsx"),
        "Clientes CTI.xlsx",
    ]

    df_clientes = None
    for p in caminhos_clientes:
        if os.path.exists(p):
            try:
                _df_test = pd.read_excel(p)
                if 'segmento' in _df_test.columns and any(c in _df_test.columns for c in ['nivel_cliente','nivel_relacionamento']):
                    df_clientes = _df_test
                    print(f"Churn: usando {p} com {len(df_clientes)} linhas, colunas: {list(df_clientes.columns)}")
                    break
                else:
                    print(f"Churn: {p} sem colunas necessarias: {list(_df_test.columns)}")
            except Exception as _e:
                print(f"Churn: erro ao ler {p}: {_e}")
    
    if df_clientes is not None and not df_clientes.empty:
        try:
            nivel_col = 'nivel_cliente' if 'nivel_cliente' in df_clientes.columns else 'nivel_relacionamento'
            
            # Desduplicar por codcli para contar clientes únicos
            # (Clientes CTI.xlsx tem múltiplas linhas por cliente, uma por serviço)
            df_sem_nan = df_clientes.dropna(subset=['segmento'])
            if 'codcli' in df_sem_nan.columns:
                df_uniq = df_sem_nan.drop_duplicates(subset=['codcli'])
            else:
                df_uniq = df_sem_nan.drop_duplicates(subset=['segmento', nivel_col])

            total_seg   = df_uniq.groupby("segmento").size()
            clientes_c  = df_uniq[df_uniq[nivel_col] == "C"].groupby("segmento").size()
            clientes_a  = df_uniq[df_uniq[nivel_col] == "A"].groupby("segmento").size()
            clientes_b  = df_uniq[df_uniq[nivel_col] == "B"].groupby("segmento").size()
            
            analise = pd.DataFrame({"total": total_seg, "nivel_c": clientes_c, "nivel_a": clientes_a, "nivel_b": clientes_b}).fillna(0).astype(int)
            analise["taxa_churn"] = (analise["nivel_c"] / analise["total"] * 100).round(1)
            analise = analise[analise["total"] > 0]
            
            servicos_por_segmento = {}
            servico_rec_por_segmento = {}
            if 'servico' in df_clientes.columns:    
                df_srvs = df_clientes.dropna(subset=['segmento'])
                for seg in df_srvs['segmento'].unique():
                    servicos = df_srvs[df_srvs['segmento'] == seg]['servico'].dropna().value_counts().head(8).index.tolist()
                    servicos_por_segmento[str(seg)] = servicos if servicos else ['Acesso Dedicado - Fisico']
            # Top servico recomendado por segmento (via recomendacoes.json)
            for _p in [os.path.join("output","recomendacoes.json"), os.path.join("data","raw","recomendacoes.json"), "recomendacoes.json"]:
                if os.path.exists(_p):
                    try:
                        with open(_p, "r", encoding="utf-8", errors="replace") as _f:
                            _rec = _json.load(_f)
                        _recs = _rec.get("recomendacoes", _rec) if isinstance(_rec, dict) else _rec
                        from collections import Counter
                        _seg_rec = {}
                        for _r in _recs:
                            _s = _r.get("segmento",""); _sv = _r.get("servico_recomendado",""); _sc = _r.get("score",0)
                            if _s and _sv:
                                if _s not in _seg_rec or _sc > _seg_rec[_s][1]:
                                    _seg_rec[_s] = (_sv, _sc)
                        servico_rec_por_segmento = {k: v[0] for k,v in _seg_rec.items()}
                    except Exception: pass
                    break
            
            churn_list = []
            for seg, row in analise.iterrows():
                if pd.isna(seg) or seg == "": continue
                churn_list.append({
                    "segmento": str(seg), "total": int(row["total"]), "nivel_c": int(row["nivel_c"]),
                    "nivel_a": int(row["nivel_a"]), "nivel_b": int(row["nivel_b"]), "taxa_churn": float(row["taxa_churn"]),
                })
            churn_list.sort(key=lambda x: -x["taxa_churn"])
            
            churn_json_str = _json.dumps({
                "segmentos": churn_list,
                "servicos_por_segmento": servicos_por_segmento,
                "servico_rec_por_segmento": servico_rec_por_segmento,
                "taxa_global": round(float(clientes_c.sum() / total_seg.sum() * 100), 1),
                "total_clientes": int(total_seg.sum()),
                "nivel_a": int(clientes_a.sum()),
                "nivel_b": int(clientes_b.sum()),
                "nivel_c": int(clientes_c.sum()),
            }, ensure_ascii=True)
        except Exception as e:
            print(f"Erro churn: {e}")
    
    # Gerar options de consultor a partir do JSON
    consultor_options = ''
    for _p in [
        'recomendacoes.json',
        os.path.join('output', 'recomendacoes.json'),
        os.path.join('data', 'raw', 'recomendacoes.json'),
    ]:
        if os.path.exists(_p):
            print(f'[CONSULTOR] Usando arquivo: {_p}')
            try:
                with open(_p, 'r', encoding='utf-8', errors='replace') as _f:
                    _rec = _json.load(_f)
                _recs = _rec.get('recomendacoes', _rec) if isinstance(_rec, dict) else _rec
                _consultores = sorted(set(
                    (r.get('consultor') or '').strip()
                    for r in _recs
                    if r.get('consultor')
                ), key=lambda x: x.lower())
                consultor_options = ''.join(
                    f'<option value="{c}">{c}</option>' for c in _consultores
                )
                print(f'[CONSULTOR] {len(_consultores)} consultores gerados: {_consultores}')
            except Exception as e:
                print(f'Erro ao gerar consultor_options: {e}')
            break

    html = DASHBOARD_HTML.replace("{{CHURN_DATA}}", churn_json_str)
    html = html.replace("{{KPI_TOTAL}}", kpi_total).replace("{{KPI_ALTA}}", kpi_alta)
    html = html.replace("{{KPI_TICKETS}}", kpi_tickets).replace("{{KPI_TOP}}", kpi_top)
    html = html.replace("{{GRAFICO_1}}", html_g1).replace("{{GRAFICO_2}}", html_g2)
    html = html.replace("{{TABLE_ROWS}}", table_rows)
    html = html.replace("{{KANBAN_AFAZER}}", kanban_buffers["afazer"])
    html = html.replace("{{KANBAN_AGUARDANDO}}", kanban_buffers["aguardando"])
    html = html.replace("{{KANBAN_RECUSADO}}", kanban_buffers["recusado"])
    html = html.replace("{{KANBAN_ACEITO}}", kanban_buffers["aceito"])
    html = html.replace("{{CONSULTOR_OPTIONS}}", consultor_options)
    
    return HTMLResponse(content=html)

@app.get("/api/recomendacoes")
def get_recomendacoes(consultor: str = ""):
    for _p in [
        "recomendacoes.json",
        os.path.join("output", "recomendacoes.json"),
        os.path.join("data", "raw", "recomendacoes.json"),
    ]:
        if os.path.exists(_p):
            try:
                with open(_p, "r", encoding="utf-8", errors="replace") as _f:
                    _rec = _json.load(_f)
                _recs = _rec.get("recomendacoes", _rec) if isinstance(_rec, dict) else _rec
                
                if consultor:
                    # Filtrar pelo consultor específico, sem restrição de score
                    _recs = [r for r in _recs if (r.get("consultor") or "").strip() == consultor.strip()]
                else:
                    # Sem consultor selecionado: ordena do maior para o menor score e pega os top 1000
                    _recs.sort(key=lambda x: x.get("score", 0), reverse=True)
                    _recs = _recs[:1000]
                    
                return JSONResponse(content=_recs)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    return JSONResponse(content=[])

@app.post("/api/kanban/save")
def save_kanban(data: KanbanUpdate):
    global KANBAN_STATE
    KANBAN_STATE[data.codcli] = data.nova_coluna
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)