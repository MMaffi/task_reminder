import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, colorchooser
import json
import os
import sys
import threading
import webbrowser
import winsound
import subprocess
from datetime import datetime, timedelta
import time
from pathlib import Path
import traceback
import re
import csv
from collections import defaultdict
import calendar
from enum import Enum
import pyperclip
import queue

# Tente importar bibliotecas opcionais com fallback
try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

try:
    import pystray
    from pystray import MenuItem as item
    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False

try:
    import winshell
    from win32com.client import Dispatch
    WINSHELL_AVAILABLE = True
except ImportError:
    WINSHELL_AVAILABLE = False

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

class Priority(Enum):
    LOW = "Baixa"
    MEDIUM = "Média"
    HIGH = "Alta"
    URGENT = "Urgente"

class TaskCategory(Enum):
    WORK = "Trabalho"
    PERSONAL = "Pessoal"
    STUDY = "Estudo"
    HEALTH = "Saúde"
    FINANCE = "Finanças"
    HOME = "Casa"
    SOCIAL = "Social"
    SHOPPING = "Compras"
    OTHER = "Outro"

class NotificationWindow:
    """Janela de notificação personalizada com mais opções"""
    def __init__(self, parent_app, task_text, reminder_text=None, task_data=None):
        self.parent_app = parent_app  # Referência ao aplicativo principal
        self.task_data = task_data
        self.window = tk.Toplevel()
        self.window.title("🔔 Task Reminder - Notificação")
        self.window.geometry("600x400")
        self.window.configure(bg='#1e1e1e')
        
        # Tornar a janela sempre no topo
        self.window.attributes('-topmost', True)
        self.window.attributes('-toolwindow', True)
        
        # Remover botões de minimizar/maximizar
        self.window.overrideredirect(True)
        
        # Posicionar no canto superior direito
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        self.window.geometry(f"600x400+{screen_width-620}+20")
        
        # Frame principal
        main_frame = tk.Frame(self.window, bg='#1e1e1e', padx=25, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Cabeçalho colorido baseado na prioridade
        header_color = '#3498db'  # Default blue
        if task_data and 'priority' in task_data:
            if task_data['priority'] == Priority.HIGH.value:
                header_color = '#e74c3c'
            elif task_data['priority'] == Priority.MEDIUM.value:
                header_color = '#f39c12'
            elif task_data['priority'] == Priority.URGENT.value:
                header_color = '#c0392b'
        
        header_frame = tk.Frame(main_frame, bg=header_color, height=60)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        header_frame.pack_propagate(False)
        
        # Ícone e título
        icon_label = tk.Label(header_frame, text="⏰", font=('Arial', 24), 
                            bg=header_color, fg='white')
        icon_label.pack(side=tk.LEFT, padx=(20, 10), pady=10)
        
        title_text = "⏰ Lembrete" if reminder_text else "🚨 Tarefa Agora!"
        title_label = tk.Label(header_frame, text=title_text, 
                             font=('Arial', 18, 'bold'), 
                             bg=header_color, fg='white')
        title_label.pack(side=tk.LEFT, padx=(10, 0), pady=10)
        
        # Botão fechar
        close_btn = tk.Label(header_frame, text="×", font=('Arial', 24, 'bold'),
                           bg=header_color, fg='white', cursor='hand2')
        close_btn.pack(side=tk.RIGHT, padx=20)
        close_btn.bind('<Button-1>', lambda e: self.on_close())
        
        # Conteúdo da notificação
        content_frame = tk.Frame(main_frame, bg='#2c3e50')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Se tiver dados da tarefa, mostrar informações detalhadas
        if task_data:
            details = f"""
📋 Tarefa: {task_data.get('task', '')}
📅 Data: {task_data.get('formatted_datetime', '')}
🎯 Prioridade: {task_data.get('priority', 'Normal')}
🏷️ Categoria: {task_data.get('category', 'Geral')}
📝 Notas: {task_data.get('notes', 'Nenhuma')}
"""
            message = details
        else:
            message = f"🔔 {reminder_text}\n\n📋 {task_text}" if reminder_text else f"🚨 É hora de realizar a tarefa:\n\n📋 {task_text}"
        
        message_label = tk.Label(content_frame, text=message, 
                               font=('Segoe UI', 11), 
                               bg='#2c3e50', fg='#ecf0f1',
                               justify=tk.LEFT, wraplength=550)
        message_label.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        
        # Botões de ação
        button_frame = tk.Frame(main_frame, bg='#1e1e1e')
        button_frame.pack(fill=tk.X)
        
        btn_style = {'font': ('Segoe UI', 10, 'bold'), 'padx': 15, 'pady': 8, 'cursor': 'hand2'}
        
        # Botão Snooze (adiar)
        if not reminder_text:  # Só adiar para notificações principais
            snooze_btn = tk.Button(button_frame, text="⏸️ Adiar (10 min)", 
                                 bg='#f39c12', fg='white',
                                 command=lambda: self.snooze_task(10),
                                 **btn_style)
            snooze_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botão Concluir (AGORA SEM MENSAGEM DE CONFIRMAÇÃO)
        complete_btn = tk.Button(button_frame, text="✅ Concluir", 
                               bg='#27ae60', fg='white',
                               command=self.mark_as_completed,  # Remove a mensagem de confirmação
                               **btn_style)
        complete_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botão Adiar para amanhã
        tomorrow_btn = tk.Button(button_frame, text="⏭️ Amanhã", 
                               bg='#3498db', fg='white',
                               command=lambda: self.snooze_task(1440),  # 24 horas
                               **btn_style)
        tomorrow_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botão Ver Detalhes
        details_btn = tk.Button(button_frame, text="🔍 Detalhes", 
                              bg='#9b59b6', fg='white',
                              command=self.show_details,
                              **btn_style)
        details_btn.pack(side=tk.LEFT)
        
        # Configurar teclas de atalho
        self.window.bind('<Escape>', lambda e: self.on_close())
        self.window.bind('<Return>', lambda e: self.mark_as_completed())
        self.window.bind('<s>', lambda e: self.snooze_task(10) if not reminder_text else None)
        
        # Focar na janela
        self.window.focus_force()
        
        # Reproduzir som se configurado
        self.play_notification_sound()
        
    def play_notification_sound(self):
        """Reproduz som de notificação"""
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except:
            pass
    
    def snooze_task(self, minutes):
        """Adia a tarefa por X minutos"""
        if self.task_data:
            try:
                # Buscar a tarefa na lista principal
                for task in self.parent_app.tasks:
                    if task['id'] == self.task_data['id']:
                        # Adiar a tarefa
                        original_datetime = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
                        new_datetime = original_datetime + timedelta(minutes=minutes)
                        
                        task['datetime'] = new_datetime.strftime("%Y-%m-%d %H:%M:%S")
                        task['formatted_datetime'] = new_datetime.strftime("%d/%m/%Y %H:%M")
                        task['status'] = 'Pendente'
                        task['is_overdue'] = False
                        
                        # Salvar alterações
                        self.parent_app.save_tasks()
                        
                        # Reagendar notificações
                        if SCHEDULE_AVAILABLE:
                            self.parent_app.reschedule_all_tasks()
                        
                        # Atualizar interface
                        self.parent_app.root.after(0, self.parent_app.load_tasks_to_table)
                        self.parent_app.root.after(0, self.parent_app.update_task_count)

                        # Atualizar estatísticas da sidebar
                        self.parent_app.update_sidebar_stats()
                        
                        break
            except Exception as e:
                print(f"Erro ao adiar tarefa: {e}")
        
        self.on_close()
    
    def mark_as_completed(self):
        """Marca a tarefa como concluída SEM MENSAGEM DE CONFIRMAÇÃO"""
        if self.task_data:
            try:
                # Buscar a tarefa na lista principal
                task_found = False
                for task in self.parent_app.tasks:
                    if task['id'] == self.task_data['id']:
                        task['status'] = 'Concluída'
                        task['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        task['is_overdue'] = False
                        task_found = True
                        break
                
                if task_found:
                    # Salvar alterações
                    self.parent_app.save_tasks()
                    
                    # Reagendar notificações (remover as pendentes)
                    if SCHEDULE_AVAILABLE:
                        self.parent_app.reschedule_all_tasks()
                    
                    # Atualizar interface
                    self.parent_app.root.after(0, self.parent_app.load_tasks_to_table)
                    self.parent_app.root.after(0, self.parent_app.update_task_count)

                    # Atualizar estatísticas da sidebar
                    self.parent_app.update_sidebar_stats()
                    
                    # Status do aplicativo
                    self.parent_app.status_var.set(f"✅ Tarefa '{self.task_data.get('task', '')[:30]}...' concluída")
                    
                    # Tocar som de confirmação
                    if self.parent_app.config.get("notification_sound", True):
                        try:
                            winsound.MessageBeep(winsound.MB_ICONASTERISK)
                        except:
                            pass
                
            except Exception as e:
                print(f"Erro ao marcar tarefa como concluída: {e}")
        
        # Fechar a janela de notificação SEM mensagem de confirmação
        self.on_close()
    
    def show_details(self):
        """Mostra detalhes da tarefa"""
        if self.task_data:
            details = f"""
📋 Tarefa: {self.task_data.get('task', '')}
📅 Data/Hora: {self.task_data.get('formatted_datetime', '')}
🎯 Prioridade: {self.task_data.get('priority', 'Normal')}
🏷️ Categoria: {self.task_data.get('category', 'Geral')}
📝 Notas: {self.task_data.get('notes', 'Nenhuma')}
"""
            messagebox.showinfo("Detalhes da Tarefa", details)
    
    def on_close(self):
        """Fecha a janela de notificação"""
        # Remover esta janela da lista de notificações ativas
        if self in self.parent_app.notification_windows:
            self.parent_app.notification_windows.remove(self)
        self.window.destroy()

class StatisticsWindow:
    """Janela de estatísticas e relatórios"""
    def __init__(self, parent, tasks):
        self.parent = parent
        self.tasks = tasks
        self.window = tk.Toplevel(parent)
        self.window.title("📊 Estatísticas e Relatórios")
        self.window.geometry("1000x700")
        self.window.configure(bg='#f8f9fa')
        
        # Notebook para diferentes tipos de estatísticas
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Aba de Visão Geral
        self.setup_overview_tab(notebook)
        
        # Aba de Análise Temporal
        self.setup_temporal_analysis_tab(notebook)
        
        # Aba de Categorias
        self.setup_category_analysis_tab(notebook)
        
        # Aba de Produtividade
        self.setup_productivity_tab(notebook)
        
        # Aba de Relatórios
        self.setup_reports_tab(notebook)
        
    def setup_overview_tab(self, notebook):
        """Configura aba de visão geral"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="📈 Visão Geral")
        
        # Estatísticas principais
        stats_frame = ttk.LabelFrame(frame, text="Estatísticas Principais", padding="20")
        stats_frame.pack(fill=tk.X, padx=10, pady=10)
        
        total_tasks = len(self.tasks)
        completed_tasks = len([t for t in self.tasks if t.get('status') == 'Concluída'])
        pending_tasks = len([t for t in self.tasks if t.get('status') == 'Pendente'])
        overdue_tasks = len([t for t in self.tasks if t.get('status') == 'Atrasada'])
        
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Cards de estatísticas
        cards_frame = ttk.Frame(stats_frame)
        cards_frame.pack(fill=tk.X)
        
        stats_data = [
            ("📋 Total", total_tasks, "#3498db"),
            ("✅ Concluídas", completed_tasks, "#27ae60"),
            ("⏳ Pendentes", pending_tasks, "#f39c12"),
            ("⚠️ Atrasadas", overdue_tasks, "#e74c3c"),
            ("📊 Taxa Conclusão", f"{completion_rate:.1f}%", "#9b59b6")
        ]
        
        for i, (title, value, color) in enumerate(stats_data):
            card = tk.Frame(cards_frame, bg=color, relief=tk.RAISED, bd=2)
            card.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.BOTH, expand=True)
            
            tk.Label(card, text=title, font=('Segoe UI', 10, 'bold'), 
                    bg=color, fg='white').pack(pady=(10, 5))
            tk.Label(card, text=str(value), font=('Segoe UI', 24, 'bold'), 
                    bg=color, fg='white').pack(pady=(5, 10))
        
        # Gráfico de pizza simples (simulado)
        chart_frame = ttk.LabelFrame(frame, text="Distribuição por Status", padding="20")
        chart_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Simulação de gráfico
        canvas = tk.Canvas(chart_frame, bg='white', height=200)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Legendas
        legend_frame = ttk.Frame(chart_frame)
        legend_frame.pack(fill=tk.X, pady=10)
        
        colors = ['#27ae60', '#f39c12', '#e74c3c', '#3498db']
        labels = ['Concluídas', 'Pendentes', 'Atrasadas', 'Outros']
        
        for i, (color, label) in enumerate(zip(colors, labels)):
            tk.Label(legend_frame, text="⬤", fg=color, 
                    font=('Arial', 16)).grid(row=0, column=i*2, padx=5)
            tk.Label(legend_frame, text=label).grid(row=0, column=i*2+1, padx=(0, 20))
    
    def setup_temporal_analysis_tab(self, notebook):
        """Configura aba de análise temporal"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="📅 Análise Temporal")
        
        # Análise por período
        period_frame = ttk.LabelFrame(frame, text="Tendências por Período", padding="20")
        period_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Filtros de período
        filter_frame = ttk.Frame(period_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(filter_frame, text="Período:").pack(side=tk.LEFT, padx=(0, 10))
        period_var = tk.StringVar(value="Últimos 7 dias")
        period_combo = ttk.Combobox(filter_frame, textvariable=period_var,
                                  values=["Hoje", "Últimos 7 dias", "Este mês", "Este ano", "Todo o período"])
        period_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # Tabela de tendências
        columns = ("Período", "Criadas", "Concluídas", "Taxa %", "Tempo Médio")
        tree = ttk.Treeview(period_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        vsb = ttk.Scrollbar(period_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Dados de exemplo
        data = [
            ("Jan 2024", 15, 12, "80%", "2h 30m"),
            ("Fev 2024", 18, 15, "83%", "2h 15m"),
            ("Mar 2024", 22, 19, "86%", "2h 45m"),
            ("Abr 2024", 20, 17, "85%", "2h 20m"),
        ]
        
        for item in data:
            tree.insert("", tk.END, values=item)
    
    def setup_category_analysis_tab(self, notebook):
        """Configura aba de análise por categoria"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🏷️ Análise por Categoria")
        
        # Coletar estatísticas por categoria
        category_stats = defaultdict(lambda: {"total": 0, "completed": 0})
        
        for task in self.tasks:
            category = task.get('category', 'Outro')
            category_stats[category]["total"] += 1
            if task.get('status') == 'Concluída':
                category_stats[category]["completed"] += 1
        
        # Tabela de categorias
        table_frame = ttk.LabelFrame(frame, text="Desempenho por Categoria", padding="20")
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        columns = ("Categoria", "Total", "Concluídas", "Taxa %")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        # Adicionar dados
        for category, stats in category_stats.items():
            total = stats["total"]
            completed = stats["completed"]
            rate = (completed / total * 100) if total > 0 else 0
            tree.insert("", tk.END, values=(category, total, completed, f"{rate:.1f}%"))
        
        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
    
    def setup_productivity_tab(self, notebook):
        """Configura aba de análise de produtividade"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🚀 Produtividade")
        
        # Métricas de produtividade
        metrics_frame = ttk.LabelFrame(frame, text="Métricas de Produtividade", padding="20")
        metrics_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Calcular métricas
        tasks_today = len([t for t in self.tasks if 
                          datetime.strptime(t.get('created_at', '2000-01-01'), "%Y-%m-%d %H:%M:%S").date() == datetime.now().date()])
        
        avg_completion_time = "2h 30m"  # Simulado
        peak_hours = "09:00-11:00, 14:00-16:00"  # Simulado
        
        metrics = [
            ("🎯 Tarefas Hoje", tasks_today),
            ("⏱️ Tempo Médio por Tarefa", avg_completion_time),
            ("📈 Pico de Produtividade", peak_hours),
            ("⭐ Melhor Dia", "Segunda-feira"),
            ("📅 Tarefas/Semana", "15.3"),
            ("🏆 Taxa de Conclusão Semanal", "82%")
        ]
        
        for i, (label, value) in enumerate(metrics):
            row = i // 2
            col = (i % 2) * 2
            
            tk.Label(metrics_frame, text=label, font=('Segoe UI', 10, 'bold')).grid(
                row=row, column=col, sticky=tk.W, padx=10, pady=10)
            tk.Label(metrics_frame, text=str(value), font=('Segoe UI', 12)).grid(
                row=row, column=col+1, sticky=tk.W, padx=(0, 20), pady=10)
    
    def setup_reports_tab(self, notebook):
        """Configura aba de relatórios"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="📄 Relatórios")
        
        # Opções de relatório
        options_frame = ttk.LabelFrame(frame, text="Gerar Relatório", padding="20")
        options_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Tipo de relatório
        ttk.Label(options_frame, text="Tipo de Relatório:").grid(row=0, column=0, sticky=tk.W, pady=5)
        report_type = tk.StringVar(value="Resumo Semanal")
        ttk.Combobox(options_frame, textvariable=report_type,
                    values=["Resumo Diário", "Resumo Semanal", "Resumo Mensal", 
                           "Análise Detalhada", "Relatório de Performance"]).grid(
                    row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Período
        ttk.Label(options_frame, text="Período:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        period_frame = ttk.Frame(options_frame)
        period_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        start_date = ttk.Entry(period_frame, width=12)
        start_date.grid(row=0, column=0, padx=(0, 5))
        start_date.insert(0, datetime.now().strftime("%d/%m/%Y"))
        
        ttk.Label(period_frame, text="até").grid(row=0, column=1, padx=5)
        
        end_date = ttk.Entry(period_frame, width=12)
        end_date.grid(row=0, column=2)
        end_date.insert(0, datetime.now().strftime("%d/%m/%Y"))
        
        # Formato
        ttk.Label(options_frame, text="Formato:").grid(row=2, column=0, sticky=tk.W, pady=5)
        format_var = tk.StringVar(value="TXT")
        ttk.Combobox(options_frame, textvariable=format_var,
                    values=["TXT", "CSV", "HTML", "JSON"]).grid(
                    row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Botões
        button_frame = ttk.Frame(options_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="📄 Visualizar", 
                  command=self.preview_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="💾 Exportar", 
                  command=self.export_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🖨️ Imprimir", 
                  command=self.print_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📧 Enviar por Email", 
                  command=self.email_report).pack(side=tk.LEFT, padx=5)
    
    def preview_report(self):
        """Previsualiza o relatório"""
        preview_window = tk.Toplevel(self.window)
        preview_window.title("Visualização do Relatório")
        preview_window.geometry("800x600")
        
        text_widget = scrolledtext.ScrolledText(preview_window, wrap=tk.WORD, font=('Consolas', 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Gerar relatório de exemplo
        report = self.generate_sample_report()
        text_widget.insert(tk.END, report)
        text_widget.configure(state='disabled')
    
    def generate_sample_report(self):
        """Gera um relatório de exemplo"""
        report = f"""
{'='*60}
RELATÓRIO DE PRODUTIVIDADE - TASK REMINDER
{'='*60}
Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
Período: Últimos 7 dias
{'='*60}

📊 ESTATÍSTICAS GERAIS
{'─'*60}
Total de Tarefas: {len(self.tasks)}
Tarefas Concluídas: {len([t for t in self.tasks if t.get('status') == 'Concluída'])}
Tarefas Pendentes: {len([t for t in self.tasks if t.get('status') == 'Pendente'])}
Taxa de Conclusão: {(len([t for t in self.tasks if t.get('status') == 'Concluída']) / len(self.tasks) * 100):.1f}%

🏷️ ANÁLISE POR CATEGORIA
{'─'*60}
"""
        # Estatísticas por categoria
        category_stats = defaultdict(int)
        for task in self.tasks:
            category = task.get('category', 'Outro')
            category_stats[category] += 1
        
        for category, count in category_stats.items():
            report += f"{category}: {count} tarefas\n"
        
        report += f"""
⏰ ANÁLISE TEMPORAL
{'─'*60}
Pico de Produtividade: 09:00-11:00
Melhor Dia da Semana: Segunda-feira
Tarefas por Dia (Média): 5.2

🎯 RECOMENDAÇÕES
{'─'*60}
1. Concentre tarefas importantes entre 09:00-11:00
2. Distribua tarefas grandes em subtarefas menores
3. Revise tarefas pendentes diariamente
4. Utilize categorias para melhor organização

{'='*60}
Fim do Relatório
{'='*60}
"""
        return report
    
    def export_report(self):
        """Exporta o relatório"""
        try:
            filename = f"relatorio_tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.generate_sample_report())
            messagebox.showinfo("Sucesso", f"Relatório exportado como {filename}")
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao exportar: {e}")
    
    def print_report(self):
        """Imprime o relatório"""
        messagebox.showinfo("Imprimir", "Funcionalidade de impressão em desenvolvimento")
    
    def email_report(self):
        """Envia relatório por email"""
        messagebox.showinfo("Email", "Funcionalidade de email em desenvolvimento")

class QuickTaskWindow:
    """Janela para adição rápida de tarefas"""
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        self.window = tk.Toplevel(parent)
        self.window.title("⚡ Tarefa Rápida")
        self.window.geometry("400x400")  # Aumentado para caber data/hora
        self.window.configure(bg='#f8f9fa')
        
        # Posicionar no centro
        self.window.transient(parent)
        self.window.grab_set()
        
        # Tornar sempre no topo
        self.window.attributes('-topmost', True)
        
        # Frame principal
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        ttk.Label(main_frame, text="➕ Adicionar Tarefa Rápida", 
                 font=('Segoe UI', 14, 'bold')).pack(pady=(0, 20))
        
        # Campo de descrição
        ttk.Label(main_frame, text="Descrição:").pack(anchor=tk.W)
        self.task_entry = ttk.Entry(main_frame, font=('Segoe UI', 11))
        self.task_entry.pack(fill=tk.X, pady=(5, 15))
        self.task_entry.focus()
        
        # Data e Hora (adicionado)
        ttk.Label(main_frame, text="Data/Hora:").pack(anchor=tk.W)
        
        datetime_frame = ttk.Frame(main_frame)
        datetime_frame.pack(fill=tk.X, pady=(5, 15))
        
        self.date_entry = ttk.Entry(datetime_frame, width=12, font=('Segoe UI', 10))
        self.date_entry.grid(row=0, column=0, padx=(0, 5))
        self.date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        
        self.time_entry = ttk.Entry(datetime_frame, width=8, font=('Segoe UI', 10))
        self.time_entry.grid(row=0, column=1, padx=(0, 5))
        self.time_entry.insert(0, (datetime.now() + timedelta(hours=1)).strftime("%H:%M"))
        
        ttk.Button(datetime_frame, text="Agora", 
                  command=self.set_current_time).grid(row=0, column=2, padx=(10, 0))
        
        # Prioridade
        priority_frame = ttk.Frame(main_frame)
        priority_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(priority_frame, text="Prioridade:").pack(side=tk.LEFT)
        
        self.priority_var = tk.StringVar(value=Priority.MEDIUM.value)
        for priority in Priority:
            ttk.Radiobutton(priority_frame, text=priority.value, 
                          value=priority.value, variable=self.priority_var).pack(side=tk.LEFT, padx=10)
        
        # Categoria
        category_frame = ttk.Frame(main_frame)
        category_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(category_frame, text="Categoria:").pack(side=tk.LEFT)
        
        self.category_var = tk.StringVar(value=TaskCategory.WORK.value)
        category_combo = ttk.Combobox(category_frame, textvariable=self.category_var,
                                    values=[cat.value for cat in TaskCategory], width=15)
        category_combo.pack(side=tk.LEFT, padx=(10, 0))
        
        # Botões
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(button_frame, text="➕ Adicionar", 
                  command=self.add_task,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="➕ & Sair", 
                  command=self.add_and_close).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="Cancelar", 
                  command=self.window.destroy).pack(side=tk.LEFT)
        
        # Configurar atalhos
        self.task_entry.bind('<Return>', lambda e: self.add_task())
        self.window.bind('<Escape>', lambda e: self.window.destroy())
        
    def set_current_time(self):
        """Define a data e hora atuais"""
        now = datetime.now()
        self.date_entry.delete(0, tk.END)
        self.time_entry.delete(0, tk.END)
        self.date_entry.insert(0, now.strftime("%d/%m/%Y"))
        self.time_entry.insert(0, now.strftime("%H:%M"))
    
    def add_task(self):
        """Adiciona a tarefa"""
        task_text = self.task_entry.get().strip()
        if task_text:
            try:
                date_text = self.date_entry.get().strip()
                time_text = self.time_entry.get().strip()
                task_datetime = datetime.strptime(f"{date_text} {time_text}", "%d/%m/%Y %H:%M")
                
                task_data = {
                    'task': task_text,
                    'datetime': task_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    'formatted_datetime': task_datetime.strftime("%d/%m/%Y %H:%M"),
                    'priority': self.priority_var.get(),
                    'category': self.category_var.get(),
                    'status': 'Pendente'
                }
                self.callback(task_data)
                self.task_entry.delete(0, tk.END)
                self.set_current_time()  # Reset para hora atual
                self.task_entry.focus()

                # Atualizar estatísticas da sidebar
                self.update_sidebar_stats()

            except ValueError:
                messagebox.showerror("Erro", "Formato de data/hora inválido!\nUse: DD/MM/AAAA HH:MM")
    
    def add_and_close(self):
        """Adiciona tarefa e fecha janela"""
        self.add_task()
        self.window.destroy()

class PomodoroTimer:
    """Temporizador Pomodoro simplificado"""
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("🍅 Pomodoro Timer")
        self.window.geometry("350x430")
        self.window.configure(bg='#2c3e50')
        self.window.resizable(False, False)
        
        # Variáveis
        self.is_running = False
        self.time_left = 25 * 60  # 25 minutos em segundos (padrão)
        self.original_time = 25 * 60
        
        # Configurar interface
        self.setup_ui()
    
    def setup_ui(self):
        """Configura a interface do Pomodoro simplificada"""
        # Frame principal
        main_frame = tk.Frame(self.window, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_label = tk.Label(main_frame, text="🍅 Pomodoro Timer", 
                             font=('Segoe UI', 20, 'bold'), 
                             bg='#2c3e50', fg='white')
        title_label.pack(pady=(0, 15))
        
        # Frame para configuração de tempo
        config_frame = tk.LabelFrame(main_frame, text="Configurar Tempo", 
                                    bg='#34495e', fg='white',
                                    font=('Segoe UI', 11, 'bold'),
                                    padx=15, pady=15)
        config_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Label e entrada
        tk.Label(config_frame, text="Minutos:", 
                bg='#34495e', fg='white',
                font=('Segoe UI', 10)).grid(row=0, column=0, padx=(0, 10))
        
        self.time_entry = tk.Entry(config_frame, font=('Segoe UI', 12), 
                                 width=10, justify='center', bg='white')
        self.time_entry.grid(row=0, column=1, padx=(0, 10))
        self.time_entry.insert(0, "25")
        
        # Botão para aplicar o tempo
        apply_btn = tk.Button(config_frame, text="Aplicar", 
                            bg='#3498db', fg='white', 
                            font=('Segoe UI', 10, 'bold'),
                            padx=15, command=self.apply_time,
                            cursor='hand2')
        apply_btn.grid(row=0, column=2)
        
        # Display do tempo
        self.time_label = tk.Label(main_frame, text="25:00", 
                                  font=('Digital-7', 56, 'bold'), 
                                  bg='#1a1a2e', fg='#0ef',
                                  relief=tk.RIDGE, bd=5,
                                  padx=30, pady=15)
        self.time_label.pack(pady=15)
        
        # Frame para botões de controle
        control_frame = tk.Frame(main_frame, bg='#2c3e50')
        control_frame.pack(pady=10)
        
        # Botão Iniciar
        self.start_btn = tk.Button(control_frame, text="▶ Iniciar", 
                                  bg='#27ae60', fg='white', 
                                  font=('Segoe UI', 11, 'bold'),
                                  width=8, height=2, 
                                  command=self.start_timer,
                                  cursor='hand2')
        self.start_btn.grid(row=0, column=0, padx=5)
        
        # Botão Pausar
        self.pause_btn = tk.Button(control_frame, text="⏸ Pausar", 
                                  bg='#f39c12', fg='white', 
                                  font=('Segoe UI', 11, 'bold'),
                                  width=8, height=2, 
                                  command=self.pause_timer,
                                  cursor='hand2')
        self.pause_btn.grid(row=0, column=1, padx=5)
        
        # Botão Reiniciar
        self.reset_btn = tk.Button(control_frame, text="⏹ Reiniciar", 
                                  bg='#e74c3c', fg='white', 
                                  font=('Segoe UI', 11, 'bold'),
                                  width=8, height=2, 
                                  command=self.reset_timer,
                                  cursor='hand2')
        self.reset_btn.grid(row=0, column=2, padx=5)
        
        # Status
        self.status_label = tk.Label(main_frame, text="Pronto para iniciar", 
                                    bg='#2c3e50', fg='#95a5a6',
                                    font=('Segoe UI', 10))
        self.status_label.pack(pady=(15, 5))
        
        # Configurar teclas de atalho
        self.window.bind('<Return>', lambda e: self.start_timer())
        self.window.bind('<space>', lambda e: self.pause_timer())
        self.window.bind('<Escape>', lambda e: self.reset_timer())
        self.time_entry.bind('<Return>', lambda e: self.apply_time())
        
        # Focar no campo de tempo
        self.time_entry.focus()
        self.time_entry.select_range(0, tk.END)
    
    def apply_time(self):
        """Aplica o tempo digitado pelo usuário"""
        if self.is_running:
            self.status_label.config(text="Pare o temporizador para alterar o tempo", fg='#e74c3c')
            return
        
        try:
            # Obter minutos do campo
            minutes_text = self.time_entry.get().strip()
            
            # Verificar se está vazio
            if not minutes_text:
                self.status_label.config(text="Digite um tempo", fg='#e74c3c')
                self.time_entry.focus()
                return
            
            minutes = float(minutes_text)  # Permitir decimais também
            
            # Validar entrada
            if minutes <= 0:
                self.status_label.config(text="Digite um tempo maior que 0", fg='#e74c3c')
                self.time_entry.focus()
                self.time_entry.select_range(0, tk.END)
                return
            
            if minutes > 240:  # 4 horas máximo
                minutes = 240
                self.time_entry.delete(0, tk.END)
                self.time_entry.insert(0, "240")
                self.status_label.config(text="Tempo máximo: 240 minutos", fg='#f39c12')
            
            # Converter para segundos
            total_seconds = int(minutes * 60)
            self.time_left = total_seconds
            self.original_time = total_seconds
            
            # Atualizar display
            self.update_display()
            
            # Feedback positivo
            self.status_label.config(text=f"Tempo definido: {minutes} minutos ({total_seconds//60}:{total_seconds%60:02d})", 
                                   fg='#27ae60')
            
            # Tocar som de confirmação
            try:
                winsound.Beep(800, 100)
            except:
                pass
            
            print(f"DEBUG: Tempo aplicado - {minutes} minutos ({self.time_left} segundos)")  # Debug
            
        except ValueError as e:
            self.status_label.config(text=f"Erro: Digite um número válido", fg='#e74c3c')
            self.time_entry.delete(0, tk.END)
            self.time_entry.insert(0, "25")
            self.time_entry.focus()
            self.time_entry.select_range(0, tk.END)
            print(f"DEBUG: Erro ao aplicar tempo - {e}")  # Debug
    
    def start_timer(self):
        """Inicia o temporizador"""
        if not self.is_running:
            self.is_running = True
            self.start_btn.config(text="⏸ Pausar", bg='#f39c12')
            self.pause_btn.config(state='normal')
            self.status_label.config(text="Em execução...", fg='#27ae60')
            self.update_timer()
            
            # Tocar som de início
            try:
                winsound.Beep(600, 100)
            except:
                pass
    
    def pause_timer(self):
        """Pausa o temporizador"""
        if self.is_running:
            self.is_running = False
            self.start_btn.config(text="▶ Continuar", bg='#27ae60')
            self.status_label.config(text="Pausado", fg='#f39c12')
            
            # Tocar som de pausa
            try:
                winsound.Beep(500, 100)
            except:
                pass
    
    def reset_timer(self):
        """Reinicia o temporizador"""
        self.is_running = False
        self.time_left = self.original_time
        self.update_display()
        self.start_btn.config(text="▶ Iniciar", bg='#27ae60')
        self.pause_btn.config(state='normal')
        self.status_label.config(text="Pronto para iniciar", fg='#95a5a6')
        
        # Tocar som de reset
        try:
            winsound.Beep(400, 200)
            time.sleep(0.1)
            winsound.Beep(300, 200)
        except:
            pass
    
    def update_timer(self):
        """Atualiza o temporizador"""
        if self.is_running and self.time_left > 0:
            self.time_left -= 1
            self.update_display()
            
            # Verificar se o tempo acabou
            if self.time_left == 0:
                self.timer_complete()
            else:
                self.window.after(1000, self.update_timer)
    
    def update_display(self):
        """Atualiza o display do tempo"""
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.time_label.config(text=f"{minutes:02d}:{seconds:02d}")
        
        # Mudar cor baseada no tempo restante
        if self.time_left <= 30:  # Menos de 30 segundos
            self.time_label.config(fg='#ff3838', bg='#1a1a2e')
        elif self.time_left <= 300:  # Menos de 5 minutos
            self.time_label.config(fg='#ff9f1a', bg='#1a1a2e')
        else:
            self.time_label.config(fg='#0ef', bg='#1a1a2e')
    
    def timer_complete(self):
        """Ação quando o temporizador completa"""
        self.is_running = False
        self.start_btn.config(text="▶ Iniciar", command=self.start_timer, bg='#27ae60')
        self.status_label.config(text="Tempo esgotado! 🎉", fg='#9b59b6')
        
        # Tocar som de conclusão
        try:
            for i in range(3):
                winsound.Beep(800 + (i * 100), 300)
                time.sleep(0.1)
        except:
            pass
        
        # Mostrar notificação
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title="🍅 Pomodoro Completo!",
                    message="Tempo do Pomodoro terminou!",
                    timeout=5,
                    app_name="Pomodoro Timer"
                )
            except:
                pass
        
        # Piscar o display
        self.blink_display()
        
        # Focar na janela
        self.window.lift()
        self.window.focus_force()
    
    def blink_display(self):
        """Faz o display piscar quando o tempo termina"""
        if hasattr(self, 'blink_count'):
            self.blink_count += 1
        else:
            self.blink_count = 0
        
        if self.blink_count < 10:  # Piscar por 10 ciclos
            current_bg = self.time_label.cget('bg')
            current_fg = self.time_label.cget('fg')
            
            # Alternar entre cores
            if self.blink_count % 2 == 0:
                self.time_label.config(bg='#ff3838', fg='#ffffff')
            else:
                self.time_label.config(bg='#1a1a2e', fg='#ff3838')
            
            self.window.after(300, self.blink_display)
        else:
            # Restaurar cor normal
            self.time_label.config(bg='#1a1a2e', fg='#ff3838')
            delattr(self, 'blink_count')

class TaskReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Reminder")
        self.root.geometry("1380x920")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Ocultar console
        self.hide_console()
        
        # Configurar caminhos dos arquivos
        if getattr(sys, 'frozen', False):
            self.exe_dir = Path(sys.executable).parent.absolute()
        else:
            self.exe_dir = Path(__file__).parent.absolute()

        # Criar pastas necessárias
        self.data_path = self.exe_dir / "data"
        self.images_path = self.exe_dir / "images"
        self.backup_path = self.exe_dir / "backups"
        self.reports_path = self.exe_dir / "reports"
        
        for path in [self.data_path, self.images_path, self.backup_path, self.reports_path]:
            path.mkdir(exist_ok=True)

        # Caminhos dos arquivos
        self.tasks_file = self.data_path / "tasks.json"
        self.config_file = self.data_path / "config.json"
        self.backup_file = self.backup_path / f"backup_{datetime.now().strftime('%Y%m%d')}.json"
        self.icon_file = self.images_path / "icon.ico"
        
        # Carregar configurações
        self.config = self.load_config()
        
        # Inicializar variáveis
        self.tasks = []
        self.scheduler_running = True
        self.tray_icon = None
        self.editing_task_id = None
        self.notification_windows = []
        self.is_quitting = False
        self.pomodoro_timer = None
        self.quick_task_queue = queue.Queue()
        self.hotkey_enabled = False
        
        # Configurar cores
        self.setup_colors()
        
        # Configurar ícone do aplicativo
        if PILLOW_AVAILABLE:
            self.setup_app_icon()
        
        # Configurar interface
        self.setup_ui()
        
        # Carregar tarefas
        self.tasks = self.load_tasks()
        self.load_tasks_to_table()
        
        # Configurar autostart se necessário
        if self.config.get("start_with_windows", True) and WINSHELL_AVAILABLE:
            self.setup_autostart()
        
        # Iniciar scheduler em thread separada
        if SCHEDULE_AVAILABLE:
            self.start_scheduler()
        
        # Configurar ícone na bandeja do sistema
        if self.config.get("show_tray_icon", True) and PYSTRAY_AVAILABLE and PILLOW_AVAILABLE:
            self.setup_tray_icon()
        
        # Configurar hotkey global se disponível
        if KEYBOARD_AVAILABLE and self.config.get("enable_global_hotkey", True):
            self.setup_global_hotkey()
        
        # Verificar tarefas imediatamente
        threading.Thread(target=self.check_pending_tasks, daemon=True).start()
        
        # Processar fila de tarefas rápidas
        threading.Thread(target=self.process_quick_task_queue, daemon=True).start()
        
        # Iniciar backup automático
        self.start_auto_backup()
        
        # Verificar dependências
        self.check_dependencies()

    def remove_autostart(self):
        """Remove o atalho de inicialização do Windows"""
        if not WINSHELL_AVAILABLE:
            print("AVISO: Biblioteca winshell não disponível - não é possível remover autostart")
            return False
        
        try:
            startup_path = winshell.startup()
            shortcut_path = os.path.join(startup_path, "TaskReminderPro.lnk")
            
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                # print(f"✅ Autostart removido: {shortcut_path}")
                
                # Também verificar e remover do registro do Windows
                self.remove_from_registry()
                
                return True
            else:
                print("ℹ️  Atalho de autostart não encontrado")
                return True  # Considera como sucesso pois já não existe
                
        except Exception as e:
            print(f"❌ Erro ao remover autostart: {e}")
            return False

    def remove_from_registry(self):
        """Remove do registro do Windows também (se existir)"""
        try:
            import winreg
            
            # Chaves do registro para verificar
            registry_keys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")
            ]
            
            app_name = "TaskReminderPro"
            
            for hive, key_path in registry_keys:
                try:
                    key = winreg.OpenKey(hive, key_path, 0, winreg.KEY_ALL_ACCESS)
                    try:
                        winreg.DeleteValue(key, app_name)
                        # print(f"✅ Removido do registro: {key_path}\\{app_name}")
                    except WindowsError:
                        pass  # Valor não existe
                    finally:
                        winreg.CloseKey(key)
                except WindowsError:
                    pass  # Chave não existe ou sem permissão
                    
        except ImportError:
            print("AVISO: Módulo winreg não disponível")
        except Exception as e:
            print(f"❌ Erro ao remover do registro: {e}")

    def hide_console(self):
        """Oculta o console do Windows"""
        try:
            import ctypes
            whnd = ctypes.windll.kernel32.GetConsoleWindow()
            if whnd != 0:
                ctypes.windll.user32.ShowWindow(whnd, 0)
                ctypes.windll.kernel32.CloseHandle(whnd)
        except:
            pass

    def check_dependencies(self):
        """Verifica e informa sobre dependências faltantes"""
        missing = []
        if not PLYER_AVAILABLE:
            missing.append("plyer (para notificações do sistema)")
        if not SCHEDULE_AVAILABLE:
            missing.append("schedule (para agendamentos)")
        if not PILLOW_AVAILABLE:
            missing.append("Pillow (para ícones)")
        if not PYSTRAY_AVAILABLE:
            missing.append("pystray (para ícone na bandeja)")
        if not WINSHELL_AVAILABLE:
            missing.append("winshell/pywin32 (para autostart)")
        if not KEYBOARD_AVAILABLE:
            missing.append("keyboard (para hotkeys globais)")
        
        if missing and self.config.get("show_warnings", True):
            self.status_var.set("⚠️ Algumas funcionalidades podem estar limitadas")

    def setup_colors(self):
        """Configura as cores do aplicativo"""
        self.colors = {
            'bg': '#f8f9fa',
            'fg': '#212529',
            'accent': '#007bff',
            'success': '#28a745',
            'warning': '#ffc107',
            'danger': '#dc3545',
            'overdue': '#dc3545',
            'pending': '#6c757d',
            'completed': '#28a745',
            'border': '#dee2e6',
            'header': '#343a40',
            'sidebar': '#2c3e50',
            'card_bg': '#ffffff'
        }

    def load_config(self):
        """Carrega as configurações do arquivo config.json"""
        default_config = {
            "start_with_windows": True,
            "minimize_to_tray": True,
            "show_tray_icon": True,
            "notification_sound": True,
            "notification_duration": 15,
            "check_interval": 60,
            "theme": "dark",
            "show_notification_on_minimize": True,
            "auto_backup": True,
            "backup_interval_hours": 24,
            "enable_global_hotkey": True,
            "global_hotkey": "ctrl+shift+t",
            "default_priority": Priority.MEDIUM.value,
            "default_category": TaskCategory.WORK.value,
            "show_warnings": True,
            "auto_complete_overdue": False,
            "pomodoro_enabled": True,
            "voice_reminders": False,
            "dark_mode": True
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
                    return default_config
            except Exception as e:
                print(f"Erro ao carregar configurações: {e}")
                return default_config
        else:
            self.save_config(default_config)
            return default_config

    def save_config(self, config=None):
        """Salva as configurações"""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")
            return False

    def setup_app_icon(self):
        """Configura o ícone do aplicativo"""
        try:
            if os.path.exists(self.icon_file):
                self.root.iconbitmap(default=str(self.icon_file))
            else:
                self.create_default_icon()
                if os.path.exists(self.icon_file):
                    self.root.iconbitmap(default=str(self.icon_file))
        except:
            pass

    def create_default_icon(self):
        """Cria um ícone padrão"""
        if not PILLOW_AVAILABLE:
            return
            
        try:
            image = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            # Desenhar fundo circular
            draw.ellipse([(20, 20), (236, 236)], fill='#007bff')
            
            # Desenhar check
            draw.line([(80, 140), (120, 180), (180, 100)], 
                     fill='white', width=20)
            
            # Desenhar relógio
            draw.ellipse([(150, 50), (206, 106)], fill='white', outline='#007bff', width=3)
            
            # Ponteiros do relógio
            draw.line([(178, 78), (178, 95)], fill='#007bff', width=4)  # Ponteiro hora
            draw.line([(178, 78), (195, 78)], fill='#007bff', width=4)  # Ponteiro minuto
            
            image.save(self.icon_file, format='ICO')
        except Exception as e:
            print(f"Erro ao criar ícone padrão: {e}")

    def setup_autostart(self):
        """Configura o aplicativo para iniciar com o Windows"""
        if not WINSHELL_AVAILABLE:
            print("AVISO: Biblioteca winshell não disponível - não é possível configurar autostart")
            return False
        
        try:
            startup_path = winshell.startup()
            shortcut_path = os.path.join(startup_path, "TaskReminderPro.lnk")
            
            # Se já existir, remover primeiro
            if os.path.exists(shortcut_path):
                try:
                    os.remove(shortcut_path)
                except:
                    pass
            
            # Criar atalho
            target = sys.executable
            script = os.path.abspath(__file__)
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target
            
            # Adicionar argumento para iniciar minimizado
            shortcut.Arguments = f'"{script}" --minimized'
            shortcut.WorkingDirectory = os.path.dirname(script)
            
            if os.path.exists(self.icon_file):
                shortcut.IconLocation = str(self.icon_file)
            
            shortcut.WindowStyle = 7  # Minimizado
            shortcut.save()
            
            # print(f"✅ Autostart configurado: {shortcut_path}")
            
            # Também adicionar ao registro (backup)
            self.add_to_registry()
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao configurar autostart: {e}")
            return False

    def add_to_registry(self):
        """Adiciona ao registro do Windows também (como backup)"""
        try:
            import winreg
            
            app_name = "TaskReminderPro"
            target = sys.executable
            script = os.path.abspath(__file__)
            arguments = f'"{script}" --minimized'
            
            # Adicionar apenas ao registro do usuário atual (não requer admin)
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            except WindowsError:
                # Se a chave não existir, criar
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            
            full_command = f'"{target}" {arguments}'
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, full_command)
            winreg.CloseKey(key)
            
            # print(f"✅ Adicionado ao registro: {key_path}\\{app_name}")
            
        except ImportError:
            print("AVISO: Módulo winreg não disponível")
        except Exception as e:
            print(f"❌ Erro ao adicionar ao registro: {e}")

    def setup_global_hotkey(self):
        """Configura hotkey global para abrir tarefa rápida"""
        if not KEYBOARD_AVAILABLE:
            return
            
        try:
            hotkey = self.config.get("global_hotkey", "ctrl+shift+t")
            keyboard.add_hotkey(hotkey, self.open_quick_task_window)
            self.hotkey_enabled = True
        except Exception as e:
            print(f"Erro ao configurar hotkey: {e}")

    def setup_tray_icon(self):
        """Configura o ícone na bandeja do sistema"""
        if not PYSTRAY_AVAILABLE or not PILLOW_AVAILABLE:
            return
            
        try:
            if os.path.exists(self.icon_file):
                image = Image.open(self.icon_file)
            else:
                image = Image.new('RGB', (64, 64), color='#007bff')
            
            # Menu da bandeja
            menu = (
                item('🚀 Mostrar', self.show_window),
                item('⚡ Tarefa Rápida', self.open_quick_task_window),
                item('🍅 Pomodoro', self.open_pomodoro_timer),
                item('📊 Estatísticas', self.open_statistics),
                item('🔧 Configurações', self.open_settings),
                item('💾 Backup Agora', self.create_backup_now),
                item('---', None),
                item('🚪 Sair', self.quit_app_silent)
            )
            
            self.tray_icon = pystray.Icon(
                "task_reminder",
                image,
                "Task Reminder",
                menu
            )
            
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            
        except Exception as e:
            print(f"Erro ao configurar ícone da bandeja: {e}")

    def setup_ui(self):
        """Configura a interface do usuário aprimorada"""
        # Configurar tema escuro
        if self.config.get("dark_mode", True):
            self.root.configure(bg='#1e1e1e')
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Barra de ferramentas superior
        self.setup_toolbar()
        
        # Frame principal
        main_frame = ttk.Frame(self.root)
        main_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Sidebar esquerda
        self.setup_sidebar(main_frame)
        
        # Área principal com notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        # Aba de Tarefas (aprimorada)
        self.setup_tasks_tab()
        
        # Aba de Calendário
        self.setup_calendar_tab()
        
        # Aba de Painel
        self.setup_dashboard_tab()
        
        # Aba de Configurações
        self.setup_settings_tab()
        
        # Barra de status
        self.setup_status_bar()

    def setup_toolbar(self):
        """Configura a barra de ferramentas superior"""
        toolbar = tk.Frame(self.root, bg='#2c3e50', height=50)
        toolbar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        toolbar.grid_propagate(False)
        
        # Logo e título
        logo_frame = tk.Frame(toolbar, bg='#2c3e50')
        logo_frame.pack(side=tk.LEFT, padx=15)
        
        tk.Label(logo_frame, text="🚀", font=('Arial', 20), 
                bg='#2c3e50', fg='white').pack(side=tk.LEFT)
        tk.Label(logo_frame, text="Task Reminder", font=('Segoe UI', 16, 'bold'), 
                bg='#2c3e50', fg='white').pack(side=tk.LEFT, padx=(10, 0))
        
        # Botões rápidos
        quick_buttons_frame = tk.Frame(toolbar, bg='#2c3e50')
        quick_buttons_frame.pack(side=tk.RIGHT, padx=15)
        
        buttons = [
            ("⚡ Rápida", self.open_quick_task_window, '#f39c12'),
            ("🍅 Pomodoro", self.open_pomodoro_timer, '#e74c3c'),
            ("📊 Relatórios", self.open_statistics, '#27ae60'),
            ("💾 Backup", self.create_backup_now, '#3498db'),
            ("🔍 Pesquisar", self.open_search_window, '#9b59b6'),
            ("📤 Exportar", self.export_all_tasks, '#1abc9c')
        ]
        
        for text, command, color in buttons:
            btn = tk.Button(quick_buttons_frame, text=text, 
                          bg=color, fg='white', font=('Segoe UI', 10, 'bold'),
                          padx=10, pady=5, command=command, cursor='hand2',
                          relief=tk.FLAT)
            btn.pack(side=tk.LEFT, padx=2)

    def setup_sidebar(self, parent):
        """Configura a barra lateral esquerda"""
        sidebar = tk.Frame(parent, bg='#2c3e50', width=200)
        sidebar.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        sidebar.grid_propagate(False)
        
        # Menu de navegação
        nav_frame = tk.Frame(sidebar, bg='#2c3e50')
        nav_frame.pack(fill=tk.X, padx=10, pady=20)
        
        nav_items = [
            ("📋 Tarefas", lambda: self.notebook.select(0)),
            ("📅 Calendário", lambda: self.notebook.select(1)),
            ("🏠 Painel", lambda: self.notebook.select(2)),
            ("⚙️ Configurações", lambda: self.notebook.select(3)),
            ("---", None),
            ("⭐ Importantes", self.show_important_tasks),
            ("⏰ Hoje", self.show_today_tasks),
            ("📅 Esta Semana", self.show_week_tasks),
            ("⚠️ Atrasadas", self.show_overdue_tasks),
            ("---", None),
            ("🏷️ Categorias", self.show_categories)
        ]
        
        for text, command in nav_items:
            if text == "---":
                tk.Frame(nav_frame, bg='#34495e', height=2).pack(fill=tk.X, pady=10)
            else:
                btn = tk.Button(nav_frame, text=text, 
                            bg='#2c3e50', fg='#ecf0f1', font=('Segoe UI', 11),
                            anchor=tk.W, padx=15, pady=8, command=command,
                            cursor='hand2', relief=tk.FLAT)
                btn.pack(fill=tk.X, pady=2)
                btn.bind('<Enter>', lambda e, b=btn: b.configure(bg='#34495e'))
                btn.bind('<Leave>', lambda e, b=btn: b.configure(bg='#2c3e50'))
        
        # Estatísticas rápidas (Frame para atualizar dinamicamente)
        self.stats_frame = tk.Frame(sidebar, bg='#34495e')
        self.stats_frame.pack(fill=tk.X, padx=10, pady=20)
        
        # Inicializar estatísticas
        self.update_sidebar_stats()

    def update_sidebar_stats(self):
        """Atualiza as estatísticas rápidas na sidebar"""
        # Limpar estatísticas antigas
        for widget in self.stats_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.stats_frame, text="📈 Estatísticas Rápidas", 
                bg='#34495e', fg='white', font=('Segoe UI', 12, 'bold')).pack(pady=(10, 15))
        
        # Contar tarefas por status
        completed = len([t for t in self.tasks if t.get('status') == 'Concluída'])
        pending = len([t for t in self.tasks if t.get('status') == 'Pendente'])
        overdue = len([t for t in self.tasks if t.get('status') == 'Atrasada'])
        total = len(self.tasks)
        
        # Calcular tarefas de hoje (baseado na data do campo datetime)
        today = datetime.now().date()
        today_tasks = 0
        for task in self.tasks:
            try:
                task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date()
                if task_date == today:
                    today_tasks += 1
            except (ValueError, KeyError):
                continue
        
        # Calcular taxa de conclusão
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        stats = [
            (f"📅 Hoje: {today_tasks}", '#3498db'),
            (f"📋 Total: {total}", '#95a5a6'),
            (f"⏳ Pendentes: {pending}", '#f39c12'),
            (f"⚠️ Atrasadas: {overdue}", '#e74c3c'),
            (f"✅ Concluídas: {completed}", '#27ae60'),
            (f"📊 Conclusão: {completion_rate:.1f}%", '#9b59b6')
        ]
        
        for text, color in stats:
            frame = tk.Frame(self.stats_frame, bg='#34495e')
            frame.pack(fill=tk.X, pady=3)
            
            tk.Label(frame, text=text, bg='#34495e', fg=color,
                    font=('Segoe UI', 10), anchor=tk.W).pack(side=tk.LEFT, padx=10, pady=2)

    def setup_tasks_tab(self):
        """Configura aba de tarefas simplificada (sem detalhes)"""
        tasks_frame = ttk.Frame(self.notebook)
        self.notebook.add(tasks_frame, text="📋 Tarefas")
        
        # Frame principal para o grid
        main_frame = ttk.Frame(tasks_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tabela de tarefas (ocupa toda a área)
        columns = ("Sel", "ID", "Tarefa", "Data/Hora", "Prioridade", "Categoria", "Status")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings", 
                            selectmode='extended', height=20)
        
        # Configurar colunas com larguras proporcionais
        col_configs = [
            ("Sel", "✓", 50, tk.CENTER),
            ("ID", "ID", 60, tk.CENTER),
            ("Tarefa", "Tarefa", 400, tk.W),
            ("Data/Hora", "Data/Hora", 150, tk.CENTER),
            ("Prioridade", "Prioridade", 120, tk.CENTER),
            ("Categoria", "Categoria", 140, tk.CENTER),
            ("Status", "Status", 100, tk.CENTER)
        ]
        
        for col_id, heading, width, anchor in col_configs:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, anchor=anchor, minwidth=width)
        
        # Scrollbars
        vsb = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(main_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        # Layout da tabela usando grid
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Configurar expansão
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Frame de entrada de nova tarefa
        input_frame = ttk.LabelFrame(tasks_frame, text="➕ Nova Tarefa", padding="15")
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.setup_detailed_task_input(input_frame)
        
        # Frame para botões de ação em massa
        action_frame = ttk.Frame(tasks_frame)
        action_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Frame centralizado para os botões
        center_frame = ttk.Frame(action_frame)
        center_frame.pack(expand=True)
        
        # Botões de ação em massa
        action_buttons = [
            ("✅ Concluir Selecionadas", self.mark_selected_completed),
            ("🗑️ Excluir Selecionadas", self.delete_selected_tasks),
            ("📤 Exportar Selecionadas", self.export_selected_tasks),
            ("✏️ Editar Selecionada", self.edit_selected_task),
            ("🔄 Atualizar", self.load_tasks_to_table)
        ]
        
        for text, command in action_buttons:
            ttk.Button(center_frame, text=text,
                    command=command,
                    width=18).pack(side=tk.LEFT, padx=3, pady=5)
        
        # Bind de seleção na tabela (removemos o on_task_select já que não temos mais detalhes)
        self.tree.bind('<Double-Button-1>', lambda e: self.edit_selected_task())

    def setup_detailed_task_input(self, parent):
        """Configura entrada detalhada de tarefa"""
        # Grid de 2 colunas
        parent.columnconfigure(1, weight=1)
        
        row = 0
        
        # Descrição
        ttk.Label(parent, text="Descrição:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.task_entry = ttk.Entry(parent, font=('Segoe UI', 11))
        self.task_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        self.task_entry.focus()
        row += 1
        
        # Data e Hora
        ttk.Label(parent, text="Data/Hora:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        datetime_frame = ttk.Frame(parent)
        datetime_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        self.date_entry = ttk.Entry(datetime_frame, width=12, font=('Segoe UI', 10))
        self.date_entry.grid(row=0, column=0, padx=(0, 5))
        self.date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        
        self.time_entry = ttk.Entry(datetime_frame, width=8, font=('Segoe UI', 10))
        self.time_entry.grid(row=0, column=1, padx=(0, 5))
        self.time_entry.insert(0, (datetime.now() + timedelta(hours=1)).strftime("%H:%M"))
        
        ttk.Button(datetime_frame, text="Agora", 
                  command=self.set_current_time).grid(row=0, column=2, padx=(10, 0))
        
        ttk.Button(datetime_frame, text="Hoje 09:00", 
                  command=lambda: self.set_time_today(9, 0)).grid(row=0, column=3, padx=(5, 0))
        
        ttk.Button(datetime_frame, text="Amanhã 08:00", 
                  command=lambda: self.set_time_tomorrow(8, 0)).grid(row=0, column=4, padx=(5, 0))
        row += 1
        
        # Prioridade e Categoria
        ttk.Label(parent, text="Prioridade:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        priority_frame = ttk.Frame(parent)
        priority_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        self.priority_var = tk.StringVar(value=self.config.get("default_priority", Priority.MEDIUM.value))
        for priority in Priority:
            ttk.Radiobutton(priority_frame, text=priority.value, 
                          value=priority.value, variable=self.priority_var).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(parent, text="Categoria:").grid(row=row, column=2, sticky=tk.W, pady=5, padx=(20, 0))
        
        self.category_var = tk.StringVar(value=self.config.get("default_category", TaskCategory.WORK.value))
        category_combo = ttk.Combobox(parent, textvariable=self.category_var,
                                     values=[cat.value for cat in TaskCategory], width=15)
        category_combo.grid(row=row, column=3, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1
        
        # Notas
        ttk.Label(parent, text="Notas:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notes_text = scrolledtext.ScrolledText(parent, height=4, font=('Segoe UI', 10))
        self.notes_text.grid(row=row, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        row += 1
        
        # Lembretes
        ttk.Label(parent, text="Lembretes:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        reminders_frame = ttk.Frame(parent)
        reminders_frame.grid(row=row, column=1, columnspan=3, sticky=tk.W, pady=5, padx=(10, 0))
        
        self.reminder_vars = {}
        reminders = [
            ("5 min antes", 5),
            ("10 min antes", 10),
            ("30 min antes", 30),
            ("1 hora antes", 60),
            ("1 dia antes", 1440)
        ]
        
        for i, (text, minutes) in enumerate(reminders):
            var = tk.BooleanVar()
            self.reminder_vars[minutes] = var
            ttk.Checkbutton(reminders_frame, text=text, variable=var).grid(
                row=0, column=i, padx=(0, 10) if i < len(reminders)-1 else 0)
        row += 1
        
        # Botões de ação
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=4, pady=(15, 0))
        
        ttk.Button(button_frame, text="➕ Adicionar Tarefa", 
                  command=self.add_task,
                  style='Accent.TButton',
                  width=20).grid(row=0, column=0, padx=2)
        
        ttk.Button(button_frame, text="➕ Várias Tarefas", 
                  command=self.add_multiple_tasks,
                  width=20).grid(row=0, column=1, padx=2)
        
        ttk.Button(button_frame, text="📅 Agendar para Semana", 
                  command=self.schedule_for_week,
                  width=20).grid(row=0, column=2, padx=2)
        
        ttk.Button(button_frame, text="🗑️ Limpar", 
                  command=self.clear_task_form,
                  width=20).grid(row=0, column=3, padx=2)

    def setup_calendar_tab(self):
        """Configura aba de calendário"""
        calendar_frame = ttk.Frame(self.notebook)
        self.notebook.add(calendar_frame, text="📅 Calendário")
        
        # Cabeçalho do calendário
        header_frame = ttk.Frame(calendar_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.calendar_month = tk.StringVar(value=datetime.now().strftime("%B %Y"))
        ttk.Label(header_frame, textvariable=self.calendar_month, 
                 font=('Segoe UI', 16, 'bold')).pack(side=tk.LEFT)
        
        nav_frame = ttk.Frame(header_frame)
        nav_frame.pack(side=tk.RIGHT)
        
        ttk.Button(nav_frame, text="◀", width=3,
                  command=self.prev_month).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="Hoje",
                  command=self.show_current_month).pack(side=tk.LEFT, padx=2)
        ttk.Button(nav_frame, text="▶", width=3,
                  command=self.next_month).pack(side=tk.LEFT, padx=2)
        
        # Grade do calendário
        self.calendar_canvas = tk.Canvas(calendar_frame, bg='white')
        self.calendar_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Configurar calendário
        self.current_date = datetime.now()
        self.draw_calendar()

    def setup_dashboard_tab(self):
        """Configura aba de painel/dashboard"""
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="🏠 Painel")
        
        # Dashboard com múltiplos widgets
        notebook = ttk.Notebook(dashboard_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Visão Geral
        overview_frame = ttk.Frame(notebook)
        notebook.add(overview_frame, text="Visão Geral")
        
        # Estatísticas em tempo real
        self.setup_dashboard_widgets(overview_frame)
        
        # Tarefas do Dia
        today_frame = ttk.Frame(notebook)
        notebook.add(today_frame, text="Hoje")
        
        # Próximas Tarefas
        upcoming_frame = ttk.Frame(notebook)
        notebook.add(upcoming_frame, text="Próximas")

    def setup_settings_tab(self):
        """Configura aba de configurações aprimorada"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ Configurações")
        
        # Notebook para categorias de configurações
        settings_notebook = ttk.Notebook(settings_frame)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Geral
        self.setup_general_settings(settings_notebook)
        
        # Notificações
        self.setup_notification_settings(settings_notebook)
        
        # Backup
        self.setup_backup_settings(settings_notebook)
        
        # Sobre
        self.setup_about_tab(settings_notebook)

    def setup_general_settings(self, notebook):
        """Configura aba de configurações gerais"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Geral")
        
        # Frame com scroll
        canvas = tk.Canvas(frame)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Conteúdo das configurações
        content_frame = ttk.LabelFrame(scrollable_frame, text="Configurações Gerais", padding="20")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        row = 0
        
        # Iniciar com Windows
        if WINSHELL_AVAILABLE:
            self.start_with_windows_var = tk.BooleanVar(value=self.config.get("start_with_windows", True))
            ttk.Checkbutton(content_frame, text="Iniciar automaticamente com o Windows",
                          variable=self.start_with_windows_var).grid(row=row, column=0, sticky=tk.W, pady=5)
            row += 1
        
        # Minimizar para bandeja
        self.minimize_to_tray_var = tk.BooleanVar(value=self.config.get("minimize_to_tray", True))
        ttk.Checkbutton(content_frame, text="Minimizar para bandeja do sistema ao fechar",
                      variable=self.minimize_to_tray_var).grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        # Mostrar ícone na bandeja
        if PYSTRAY_AVAILABLE and PILLOW_AVAILABLE:
            self.show_tray_icon_var = tk.BooleanVar(value=self.config.get("show_tray_icon", True))
            ttk.Checkbutton(content_frame, text="Mostrar ícone na bandeja do sistema",
                          variable=self.show_tray_icon_var).grid(row=row, column=0, sticky=tk.W, pady=5)
            row += 1
        
        # Hotkey global
        if KEYBOARD_AVAILABLE:
            self.enable_hotkey_var = tk.BooleanVar(value=self.config.get("enable_global_hotkey", True))
            ttk.Checkbutton(content_frame, text="Ativar hotkey global (Ctrl+Shift+T)",
                          variable=self.enable_hotkey_var).grid(row=row, column=0, sticky=tk.W, pady=5)
            row += 1
            
            ttk.Label(content_frame, text="Hotkey personalizado:").grid(row=row, column=0, sticky=tk.W, pady=5)
            self.hotkey_entry = ttk.Entry(content_frame, width=20)
            self.hotkey_entry.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
            self.hotkey_entry.insert(0, self.config.get("global_hotkey", "ctrl+shift+t"))
            row += 1
        
        # Auto-backup
        self.auto_backup_var = tk.BooleanVar(value=self.config.get("auto_backup", True))
        ttk.Checkbutton(content_frame, text="Backup automático",
                      variable=self.auto_backup_var).grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        ttk.Label(content_frame, text="Intervalo de backup (horas):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.backup_interval_var = tk.IntVar(value=self.config.get("backup_interval_hours", 24))
        ttk.Spinbox(content_frame, from_=1, to=168, textvariable=self.backup_interval_var,
                   width=10).grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1
        
        # Auto-completar tarefas atrasadas
        self.auto_complete_var = tk.BooleanVar(value=self.config.get("auto_complete_overdue", False))
        ttk.Checkbutton(content_frame, text="Marcar automaticamente tarefas muito atrasadas",
                      variable=self.auto_complete_var).grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        # Lembretes por voz
        if TTS_AVAILABLE:
            self.voice_reminders_var = tk.BooleanVar(value=self.config.get("voice_reminders", False))
            ttk.Checkbutton(content_frame, text="Lembretes por voz",
                          variable=self.voice_reminders_var).grid(row=row, column=0, sticky=tk.W, pady=5)
            row += 1
        
        # Padrões
        ttk.Label(content_frame, text="Prioridade padrão:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.default_priority_var = tk.StringVar(value=self.config.get("default_priority", Priority.MEDIUM.value))
        ttk.Combobox(content_frame, textvariable=self.default_priority_var,
                    values=[p.value for p in Priority], width=15).grid(
                    row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1
        
        ttk.Label(content_frame, text="Categoria padrão:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.default_category_var = tk.StringVar(value=self.config.get("default_category", TaskCategory.WORK.value))
        ttk.Combobox(content_frame, textvariable=self.default_category_var,
                    values=[cat.value for cat in TaskCategory], width=15).grid(
                    row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1
        
        # Botões
        button_frame = ttk.Frame(content_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="💾 Salvar", 
                  command=self.save_all_settings,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="🔄 Restaurar Padrões", 
                  command=self.restore_default_settings).pack(side=tk.LEFT, padx=5)

    def setup_notification_settings(self, notebook):
        """Configura aba de notificações"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="🔔 Notificações")
        
        content = ttk.LabelFrame(frame, text="Configurações de Notificação", padding="20")
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        row = 0
        
        # Som de notificação
        if PLYER_AVAILABLE:
            self.notification_sound_var = tk.BooleanVar(value=self.config.get("notification_sound", True))
            ttk.Checkbutton(content, text="Tocar som nas notificações",
                          variable=self.notification_sound_var).grid(row=row, column=0, sticky=tk.W, pady=5)
            row += 1
        
        # Notificação ao minimizar
        if PLYER_AVAILABLE:
            self.show_notification_var = tk.BooleanVar(value=self.config.get("show_notification_on_minimize", True))
            ttk.Checkbutton(content, text="Mostrar notificação ao minimizar para bandeja",
                          variable=self.show_notification_var).grid(row=row, column=0, sticky=tk.W, pady=5)
            row += 1
        
        # Duração
        if PLYER_AVAILABLE:
            ttk.Label(content, text="Duração da notificação (segundos):").grid(row=row, column=0, sticky=tk.W, pady=5)
            self.notification_duration_var = tk.IntVar(value=self.config.get("notification_duration", 15))
            ttk.Spinbox(content, from_=5, to=60, increment=5,
                       textvariable=self.notification_duration_var, width=10).grid(
                       row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
            row += 1
        
        # Tipo de notificação
        ttk.Label(content, text="Tipo de notificação:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.notification_type_var = tk.StringVar(value=self.config.get("notification_type", "ambos"))
        ttk.Combobox(content, textvariable=self.notification_type_var,
                    values=["Somente janela", "Somente sistema", "Ambos"], width=15).grid(
                    row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1

    def setup_backup_settings(self, notebook):
        """Configura aba de backup"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="💾 Backup")
        
        content = ttk.LabelFrame(frame, text="Backup e Restauração", padding="20")
        content.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Lista de backups
        ttk.Label(content, text="Backups disponíveis:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        backup_list_frame = ttk.Frame(content)
        backup_list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.backup_listbox = tk.Listbox(backup_list_frame, height=8, width=50)
        self.backup_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(backup_list_frame, orient="vertical", command=self.backup_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.backup_listbox.config(yscrollcommand=scrollbar.set)
        
        # Atualizar lista de backups
        self.update_backup_list()
        
        # Botões de backup
        button_frame = ttk.Frame(content)
        button_frame.grid(row=2, column=0, columnspan=2, pady=15)
        
        ttk.Button(button_frame, text="💾 Criar Backup", 
                  command=self.create_backup_now).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="↩️ Restaurar", 
                  command=self.restore_backup).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="🗑️ Excluir Backup", 
                  command=self.delete_backup).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="📤 Exportar Tudo", 
                  command=self.export_all_data).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="📥 Importar", 
                  command=self.import_data).pack(side=tk.LEFT, padx=5)

    def setup_about_tab(self, notebook):
        """Configura aba 'Sobre'"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="ℹ️ Sobre")
        
        content = tk.Frame(frame, bg='#f8f9fa')
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Logo
        logo_label = tk.Label(content, text="🚀", font=('Arial', 48), bg='#f8f9fa')
        logo_label.pack(pady=(20, 10))
        
        # Título
        title_label = tk.Label(content, text="Task Reminder", 
                              font=('Segoe UI', 24, 'bold'), bg='#f8f9fa')
        title_label.pack(pady=(0, 10))
        
        # Versão
        version_label = tk.Label(content, text="Versão 3.0.0 Professional", 
                                font=('Segoe UI', 12), bg='#f8f9fa', fg='#6c757d')
        version_label.pack(pady=(0, 20))
        
        # Descrição
        desc_text = """Um gerenciador de tarefas profissional e completo com múltiplas funcionalidades:

• Agendamento inteligente de tarefas
• Sistema Pomodoro integrado
• Estatísticas e relatórios detalhados
• Backup automático e seguro
• Notificações personalizáveis
• Hotkeys globais
• E muito mais!"""
        
        desc_label = tk.Label(content, text=desc_text, 
                             font=('Segoe UI', 11), bg='#f8f9fa', justify=tk.LEFT)
        desc_label.pack(pady=(0, 30))
        
        # Informações
        info_frame = tk.Frame(content, bg='#f8f9fa')
        info_frame.pack(fill=tk.X, pady=10)
        
        infos = [
            ("👨‍💻 Desenvolvedor:", "Seu Nome"),
            ("📧 Contato:", "seu.email@exemplo.com"),
            ("🌐 Website:", "www.seusite.com"),
            ("📄 Licença:", "MIT License")
        ]
        
        for label, value in infos:
            frame = tk.Frame(info_frame, bg='#f8f9fa')
            frame.pack(fill=tk.X, pady=5)
            
            tk.Label(frame, text=label, font=('Segoe UI', 10, 'bold'), 
                    bg='#f8f9fa', width=15, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(frame, text=value, font=('Segoe UI', 10), 
                    bg='#f8f9fa', anchor=tk.W).pack(side=tk.LEFT)
        
        # Botões
        button_frame = tk.Frame(content, bg='#f8f9fa')
        button_frame.pack(pady=30)
        
        tk.Button(button_frame, text="🌐 Visitar Website", 
                 command=lambda: webbrowser.open("https://www.seusite.com"),
                 bg='#007bff', fg='white', padx=15, pady=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="📚 Documentação", 
                 command=lambda: webbrowser.open("https://docs.seusite.com"),
                 bg='#6c757d', fg='white', padx=15, pady=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="🐛 Reportar Bug", 
                 command=self.report_bug,
                 bg='#dc3545', fg='white', padx=15, pady=8).pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="🔄 Verificar Atualizações", 
                 command=self.check_for_updates,
                 bg='#28a745', fg='white', padx=15, pady=8).pack(side=tk.LEFT, padx=5)

    def setup_status_bar(self):
        """Configura a barra de status aprimorada"""
        status_frame = tk.Frame(self.root, bg='#2c3e50', height=30)
        status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
        status_frame.grid_propagate(False)
        
        # Status do aplicativo
        self.status_var = tk.StringVar(value="👌 Pronto")
        status_label = tk.Label(status_frame, textvariable=self.status_var,
                               bg='#2c3e50', fg='white', font=('Segoe UI', 9))
        status_label.pack(side=tk.LEFT, padx=10)
        
        # Contador de tarefas
        self.task_count_var = tk.StringVar(value="Tarefas: 0")
        count_label = tk.Label(status_frame, textvariable=self.task_count_var,
                              bg='#2c3e50', fg='#95a5a6', font=('Segoe UI', 9))
        count_label.pack(side=tk.RIGHT, padx=10)
        
        # Atualizar contador
        self.update_task_count()

    def update_task_count(self):
        """Atualiza o contador de tarefas na barra de status"""
        total = len(self.tasks)
        pending = len([t for t in self.tasks if t.get('status') == 'Pendente'])
        overdue = len([t for t in self.tasks if t.get('status') == 'Atrasada'])
        today = datetime.now().date()
        today_count = len([t for t in self.tasks 
                        if datetime.strptime(t['datetime'], "%Y-%m-%d %H:%M:%S").date() == today])
        
        self.task_count_var.set(f"📋 Total: {total} | 📅 Hoje: {today_count} | ⏳ Pendentes: {pending} | ⚠️ Atrasadas: {overdue}")

    def draw_calendar(self):
        """Desenha o calendário na tela"""
        self.calendar_canvas.delete("all")
        
        year = self.current_date.year
        month = self.current_date.month
        
        # Configurar dimensões
        canvas_width = self.calendar_canvas.winfo_width()
        canvas_height = self.calendar_canvas.winfo_height()
        
        if canvas_width < 10 or canvas_height < 10:
            canvas_width = 800
            canvas_height = 600
        
        cell_width = canvas_width // 7
        cell_height = canvas_height // 8
        
        # Desenhar cabeçalho
        days = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
        for i, day in enumerate(days):
            x = i * cell_width
            self.calendar_canvas.create_rectangle(
                x, 0, x + cell_width, cell_height,
                fill='#3498db', outline='#2980b9'
            )
            self.calendar_canvas.create_text(
                x + cell_width // 2, cell_height // 2,
                text=day, fill='white', font=('Segoe UI', 10, 'bold')
            )
        
        # Primeiro dia do mês
        first_day = datetime(year, month, 1)
        start_weekday = first_day.weekday()  # 0 = segunda, 6 = domingo
        
        # Último dia do mês
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        
        last_day = next_month - timedelta(days=1)
        total_days = last_day.day
        
        # Desenhar dias
        current_day = 1
        for week in range(6):
            for weekday in range(7):
                if week == 0 and weekday < start_weekday:
                    continue
                
                if current_day > total_days:
                    break
                
                x = weekday * cell_width
                y = (week + 1) * cell_height
                
                # Verificar se é hoje
                is_today = (current_day == datetime.now().day and 
                           month == datetime.now().month and 
                           year == datetime.now().year)
                
                # Verificar se há tarefas neste dia
                has_tasks = self.has_tasks_on_date(year, month, current_day)
                
                # Cor do fundo
                fill_color = '#f0f8ff' if is_today else '#ffffff'
                if weekday in [5, 6]:  # Fim de semana
                    fill_color = '#f8f9fa'
                
                self.calendar_canvas.create_rectangle(
                    x, y, x + cell_width, y + cell_height,
                    fill=fill_color, outline='#e0e0e0', width=1
                )
                
                # Texto do dia
                day_color = '#e74c3c' if weekday == 6 else '#000000'  # Domingos em vermelho
                if is_today:
                    day_color = '#3498db'
                
                self.calendar_canvas.create_text(
                    x + cell_width - 10, y + 10,
                    text=str(current_day), anchor=tk.NE,
                    fill=day_color, font=('Segoe UI', 11, 'bold')
                )
                
                # Indicador de tarefas
                if has_tasks:
                    task_count = self.count_tasks_on_date(year, month, current_day)
                    indicator_color = '#e74c3c' if any(t['is_overdue'] for t in 
                                                      self.get_tasks_on_date(year, month, current_day)) else '#3498db'
                    
                    self.calendar_canvas.create_oval(
                        x + 10, y + 15, x + 25, y + 30,
                        fill=indicator_color, outline=indicator_color
                    )
                    
                    self.calendar_canvas.create_text(
                        x + 17.5, y + 22.5,
                        text=str(task_count), fill='white',
                        font=('Segoe UI', 8, 'bold')
                    )
                
                current_day += 1
    
    def has_tasks_on_date(self, year, month, day):
        """Verifica se há tarefas em uma data específica"""
        target_date = datetime(year, month, day).date()
        for task in self.tasks:
            task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date()
            if task_date == target_date:
                return True
        return False
    
    def count_tasks_on_date(self, year, month, day):
        """Conta tarefas em uma data específica"""
        target_date = datetime(year, month, day).date()
        count = 0
        for task in self.tasks:
            task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date()
            if task_date == target_date:
                count += 1
        return count
    
    def get_tasks_on_date(self, year, month, day):
        """Obtém tarefas em uma data específica"""
        target_date = datetime(year, month, day).date()
        tasks = []
        for task in self.tasks:
            task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date()
            if task_date == target_date:
                tasks.append(task)
        return tasks
    
    def prev_month(self):
        """Navega para o mês anterior"""
        self.current_date = self.current_date.replace(day=1)
        self.current_date = self.current_date - timedelta(days=1)
        self.current_date = self.current_date.replace(day=1)
        self.calendar_month.set(self.current_date.strftime("%B %Y"))
        self.draw_calendar()
    
    def next_month(self):
        """Navega para o próximo mês"""
        self.current_date = self.current_date.replace(day=28)
        self.current_date = self.current_date + timedelta(days=7)
        self.current_date = self.current_date.replace(day=1)
        self.calendar_month.set(self.current_date.strftime("%B %Y"))
        self.draw_calendar()
    
    def show_current_month(self):
        """Mostra o mês atual"""
        self.current_date = datetime.now()
        self.calendar_month.set(self.current_date.strftime("%B %Y"))
        self.draw_calendar()
    
    def setup_dashboard_widgets(self, parent):
        """Configura widgets do dashboard"""
        # Widgets em grid 2x2
        widgets = [
            ("📊 Produtividade Hoje", self.create_progress_widget, 0, 0),
            ("📈 Estatísticas da Semana", self.create_stats_widget, 0, 1),
            ("🎯 Tarefas Prioritárias", self.create_priority_widget, 1, 0),
            ("⏰ Próximos Prazos", self.create_deadline_widget, 1, 1)
        ]
        
        for title, creator_func, row, col in widgets:
            frame = ttk.LabelFrame(parent, text=title, padding="10")
            frame.grid(row=row, column=col, padx=5, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))
            parent.columnconfigure(col, weight=1)
            parent.rowconfigure(row, weight=1)
            creator_func(frame)
    
    def create_progress_widget(self, parent):
        """Cria widget de progresso"""
        # Calcular progresso do dia
        tasks_today = [t for t in self.tasks if 
                      datetime.strptime(t['datetime'], "%Y-%m-%d %H:%M:%S").date() == datetime.now().date()]
        
        completed_today = len([t for t in tasks_today if t.get('status') == 'Concluída'])
        total_today = len(tasks_today)
        
        progress = (completed_today / total_today * 100) if total_today > 0 else 0
        
        # Canvas para progresso circular
        canvas = tk.Canvas(parent, width=150, height=150, bg='white', highlightthickness=0)
        canvas.pack(pady=10)
        
        # Desenhar círculo de progresso
        center_x, center_y = 75, 75
        radius = 60
        
        # Fundo
        canvas.create_oval(center_x - radius, center_y - radius,
                          center_x + radius, center_y + radius,
                          fill='#f0f0f0', outline='#e0e0e0')
        
        # Progresso
        angle = 360 * progress / 100
        canvas.create_arc(center_x - radius, center_y - radius,
                         center_x + radius, center_y + radius,
                         start=90, extent=-angle,
                         fill='#3498db', outline='#2980b9', width=3)
        
        # Texto do progresso
        canvas.create_text(center_x, center_y, 
                          text=f"{progress:.0f}%", 
                          font=('Segoe UI', 16, 'bold'), fill='#2c3e50')
        
        # Estatísticas
        stats_text = f"Concluídas: {completed_today}/{total_today}"
        tk.Label(parent, text=stats_text, font=('Segoe UI', 10)).pack()
    
    def create_stats_widget(self, parent):
        """Cria widget de estatísticas da semana"""
        # Coletar estatísticas da semana
        week_tasks = []
        for task in self.tasks:
            task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
            if task_date.isocalendar()[1] == datetime.now().isocalendar()[1]:
                week_tasks.append(task)
        
        stats = {
            "Total": len(week_tasks),
            "Concluídas": len([t for t in week_tasks if t.get('status') == 'Concluída']),
            "Pendentes": len([t for t in week_tasks if t.get('status') == 'Pendente']),
            "Atrasadas": len([t for t in week_tasks if t.get('status') == 'Atrasada']),
            "Taxa": f"{(len([t for t in week_tasks if t.get('status') == 'Concluída']) / len(week_tasks) * 100 if week_tasks else 0):.1f}%"
        }
        
        for key, value in stats.items():
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=2)
            
            tk.Label(frame, text=f"{key}:", width=10, anchor=tk.W,
                    font=('Segoe UI', 10)).pack(side=tk.LEFT)
            tk.Label(frame, text=str(value), anchor=tk.W,
                    font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT)
    
    def create_priority_widget(self, parent):
        """Cria widget de tarefas prioritárias"""
        # Buscar tarefas de alta prioridade
        high_priority = [t for t in self.tasks 
                        if t.get('priority') in [Priority.HIGH.value, Priority.URGENT.value]
                        and t.get('status') == 'Pendente']
        
        if not high_priority:
            tk.Label(parent, text="Nenhuma tarefa prioritária pendente",
                    font=('Segoe UI', 10), fg='#7f8c8d').pack(pady=20)
            return
        
        for i, task in enumerate(high_priority[:5]):  # Mostrar até 5
            task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=2)
            
            # Prioridade colorida
            priority_color = '#e74c3c' if task.get('priority') == Priority.URGENT.value else '#f39c12'
            tk.Label(frame, text="●", fg=priority_color,
                    font=('Arial', 12)).pack(side=tk.LEFT, padx=(0, 5))
            
            # Texto da tarefa
            text = f"{task['task'][:30]}..." if len(task['task']) > 30 else task['task']
            tk.Label(frame, text=text, anchor=tk.W,
                    font=('Segoe UI', 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Data
            tk.Label(frame, text=task_date.strftime("%d/%m %H:%M"),
                    font=('Segoe UI', 8), fg='#7f8c8d').pack(side=tk.RIGHT)
    
    def create_deadline_widget(self, parent):
        """Cria widget de próximos prazos"""
        # Buscar próximas tarefas
        now = datetime.now()
        upcoming_tasks = []
        
        for task in self.tasks:
            if task.get('status') != 'Pendente':
                continue
                
            task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
            if task_date > now:
                time_diff = task_date - now
                upcoming_tasks.append((task, time_diff))
        
        # Ordenar por proximidade
        upcoming_tasks.sort(key=lambda x: x[1])
        
        if not upcoming_tasks:
            tk.Label(parent, text="Nenhum prazo próximo",
                    font=('Segoe UI', 10), fg='#7f8c8d').pack(pady=20)
            return
        
        for i, (task, time_diff) in enumerate(upcoming_tasks[:5]):  # Mostrar até 5
            frame = tk.Frame(parent)
            frame.pack(fill=tk.X, pady=2)
            
            # Tempo restante
            if time_diff.days > 0:
                time_text = f"{time_diff.days}d {time_diff.seconds//3600}h"
            elif time_diff.seconds >= 3600:
                time_text = f"{time_diff.seconds//3600}h {(time_diff.seconds%3600)//60}m"
            else:
                time_text = f"{time_diff.seconds//60}m"
            
            tk.Label(frame, text=time_text, width=8,
                    font=('Segoe UI', 9, 'bold'), fg='#3498db').pack(side=tk.LEFT)
            
            # Texto da tarefa
            text = f"{task['task'][:25]}..." if len(task['task']) > 25 else task['task']
            tk.Label(frame, text=text, anchor=tk.W,
                    font=('Segoe UI', 9)).pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def set_time_today(self, hour, minute):
        """Define a hora para hoje com horário específico"""
        today = datetime.now()
        self.date_entry.delete(0, tk.END)
        self.time_entry.delete(0, tk.END)
        self.date_entry.insert(0, today.strftime("%d/%m/%Y"))
        self.time_entry.insert(0, f"{hour:02d}:{minute:02d}")
    
    def set_time_tomorrow(self, hour, minute):
        """Define a hora para amanhã com horário específico"""
        tomorrow = datetime.now() + timedelta(days=1)
        self.date_entry.delete(0, tk.END)
        self.time_entry.delete(0, tk.END)
        self.date_entry.insert(0, tomorrow.strftime("%d/%m/%Y"))
        self.time_entry.insert(0, f"{hour:02d}:{minute:02d}")
    
    def filter_tasks(self, event=None):
        """Filtra tarefas baseado nos critérios selecionados"""
        # Implementação do filtro
        pass
    
    def on_task_select(self, event=None):
        """Atualiza detalhes da tarefa selecionada"""
        selected = self.tree.selection()
        if not selected:
            self.detail_text.config(state='normal')
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(tk.END, "Selecione uma tarefa para ver detalhes")
            self.detail_text.config(state='disabled')
            return
        
        item = self.tree.item(selected[0])
        task_id = item['values'][1]  # ID está na coluna 1
        
        for task in self.tasks:
            if task['id'] == task_id:
                self.show_task_details(task)
                break
    
    def add_task(self):
        """Adiciona uma nova tarefa com todos os detalhes"""
        # Obter dados do formulário
        task_text = self.task_entry.get().strip()
        date_text = self.date_entry.get().strip()
        time_text = self.time_entry.get().strip()
        
        # Validação básica
        if not task_text:
            messagebox.showwarning("Aviso", "Por favor, insira uma descrição para a tarefa!")
            self.task_entry.focus()
            return
        
        if not self.validate_datetime(date_text, time_text):
            messagebox.showerror("Erro", "Formato de data/hora inválido!\nUse: DD/MM/AAAA HH:MM")
            return
        
        # Preparar dados da tarefa
        task_datetime = datetime.strptime(f"{date_text} {time_text}", "%d/%m/%Y %H:%M")
        now = datetime.now()
        
        # Coletar lembretes
        reminders = {}
        for minutes, var in self.reminder_vars.items():
            reminders[f"reminder_{minutes}min"] = var.get()
        
        task = {
            "id": max([t['id'] for t in self.tasks], default=0) + 1,
            "task": task_text,
            "datetime": task_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "formatted_datetime": task_datetime.strftime("%d/%m/%Y %H:%M"),
            "priority": self.priority_var.get(),
            "category": self.category_var.get(),
            "status": "Pendente",
            "notes": self.notes_text.get(1.0, tk.END).strip(),
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "is_overdue": task_datetime < now,
            **reminders
        }
        
        # Adicionar à lista
        self.tasks.append(task)
        
        # Salvar
        self.save_tasks()
        
        # Atualizar interface
        self.load_tasks_to_table()
        self.update_task_count()
        
        # Agendar notificações
        if SCHEDULE_AVAILABLE:
            self.schedule_task_notifications(task)
        
        # Limpar formulário
        self.clear_task_form()
        
        # Feedback
        self.status_var.set(f"✅ Tarefa '{task_text[:30]}...' adicionada")
        
        # Tocar som de confirmação
        if self.config.get("notification_sound", True):
            try:
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except:
                pass
    
    def clear_task_form(self):
        """Limpa o formulário de tarefa"""
        self.task_entry.delete(0, tk.END)
        self.set_current_time()
        self.priority_var.set(self.config.get("default_priority", Priority.MEDIUM.value))
        self.category_var.set(self.config.get("default_category", TaskCategory.WORK.value))
        self.notes_text.delete(1.0, tk.END)
        
        for var in self.reminder_vars.values():
            var.set(False)
        
        self.task_entry.focus()
    
    def add_multiple_tasks(self):
        """Abre janela para adicionar múltiplas tarefas"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Adicionar Múltiplas Tarefas")
        dialog.geometry("600x400")
        
        # Text area para múltiplas tarefas
        tk.Label(dialog, text="Digite uma tarefa por linha (formato: Tarefa;Data;Hora;Prioridade)",
                font=('Segoe UI', 10)).pack(pady=10)
        
        text_area = scrolledtext.ScrolledText(dialog, height=15, width=70,
                                            font=('Consolas', 10))
        text_area.pack(padx=10, pady=5)
        
        # Exemplo
        example = """Reunião com equipe;01/01/2024;14:00;Alta
Enviar relatório;01/01/2024;16:30;Média
Ligar para cliente;02/01/2024;10:00;Urgente"""
        text_area.insert(tk.END, example)
        
        def process_tasks():
            content = text_area.get(1.0, tk.END).strip()
            lines = content.split('\n')
            
            added = 0
            errors = []
            
            for i, line in enumerate(lines, 1):
                parts = line.split(';')
                if len(parts) >= 3:
                    try:
                        task_text = parts[0].strip()
                        date_text = parts[1].strip()
                        time_text = parts[2].strip()
                        priority = parts[3].strip() if len(parts) > 3 else self.priority_var.get()
                        
                        if task_text and date_text and time_text:
                            # Adicionar tarefa
                            task_datetime = datetime.strptime(f"{date_text} {time_text}", "%d/%m/%Y %H:%M")
                            
                            task = {
                                "id": max([t['id'] for t in self.tasks], default=0) + 1,
                                "task": task_text,
                                "datetime": task_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                                "formatted_datetime": task_datetime.strftime("%d/%m/%Y %H:%M"),
                                "priority": priority,
                                "category": self.category_var.get(),
                                "status": "Pendente",
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "is_overdue": task_datetime < datetime.now()
                            }
                            
                            self.tasks.append(task)
                            added += 1
                            
                    except Exception as e:
                        errors.append(f"Linha {i}: {str(e)}")
            
            if added > 0:
                self.save_tasks()
                self.load_tasks_to_table()
                self.update_task_count()
                
                if SCHEDULE_AVAILABLE:
                    self.reschedule_all_tasks()
            
            dialog.destroy()
            
            if errors:
                messagebox.showwarning("Aviso", 
                    f"Adicionadas {added} tarefas. Erros:\n\n" + "\n".join(errors))
            else:
                messagebox.showinfo("Sucesso", f"Adicionadas {added} tarefas com sucesso!")
        
        # Botões
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        tk.Button(button_frame, text="Processar", command=process_tasks,
                 bg='#28a745', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancelar", command=dialog.destroy,
                 bg='#dc3545', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
    
    def schedule_for_week(self):
        """Agenda tarefas para a semana"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Agendar para Semana")
        dialog.geometry("500x300")
        
        tk.Label(dialog, text="Agendar tarefa repetida para os próximos 7 dias",
                font=('Segoe UI', 12)).pack(pady=10)
        
        # Formulário
        form_frame = tk.Frame(dialog)
        form_frame.pack(pady=10)
        
        tk.Label(form_frame, text="Tarefa:").grid(row=0, column=0, sticky=tk.W, pady=5)
        task_entry = tk.Entry(form_frame, width=40)
        task_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        
        tk.Label(form_frame, text="Horário:").grid(row=1, column=0, sticky=tk.W, pady=5)
        time_entry = tk.Entry(form_frame, width=10)
        time_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        time_entry.insert(0, "09:00")
        
        tk.Label(form_frame, text="Prioridade:").grid(row=2, column=0, sticky=tk.W, pady=5)
        priority_var = tk.StringVar(value=Priority.MEDIUM.value)
        for i, priority in enumerate(Priority):
            tk.Radiobutton(form_frame, text=priority.value, 
                          value=priority.value, variable=priority_var).grid(
                          row=2, column=1+i, sticky=tk.W, padx=(10 if i==0 else 5, 0))
        
        def schedule_tasks():
            task_text = task_entry.get().strip()
            time_text = time_entry.get().strip()
            
            if not task_text:
                messagebox.showwarning("Aviso", "Digite uma tarefa!")
                return
            
            added = 0
            today = datetime.now().date()
            
            for i in range(7):
                task_date = today + timedelta(days=i)
                task_datetime = datetime.combine(task_date, 
                                                datetime.strptime(time_text, "%H:%M").time())
                
                task = {
                    "id": max([t['id'] for t in self.tasks], default=0) + 1,
                    "task": f"{task_text} ({task_date.strftime('%A')})",
                    "datetime": task_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    "formatted_datetime": task_datetime.strftime("%d/%m/%Y %H:%M"),
                    "priority": priority_var.get(),
                    "category": self.category_var.get(),
                    "status": "Pendente",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "is_overdue": False
                }
                
                self.tasks.append(task)
                added += 1
            
            self.save_tasks()
            self.load_tasks_to_table()
            self.update_task_count()
            
            if SCHEDULE_AVAILABLE:
                self.reschedule_all_tasks()
            
            dialog.destroy()
            messagebox.showinfo("Sucesso", f"Agendadas {added} tarefas para a semana!")
        
        # Botões
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Agendar", command=schedule_tasks,
                 bg='#3498db', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancelar", command=dialog.destroy,
                 bg='#6c757d', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
    
    def mark_selected_completed(self):
        """Marca tarefas selecionadas como concluídas"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione tarefas para marcar como concluídas!")
            return
        
        count = 0
        for item_id in selected:
            item = self.tree.item(item_id)
            task_id = item['values'][1]
            
            for task in self.tasks:
                if task['id'] == task_id and task.get('status') != 'Concluída':
                    task['status'] = 'Concluída'
                    task['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    count += 1
                    break
        
        if count > 0:
            self.save_tasks()
            self.load_tasks_to_table()
            self.update_task_count()
            self.status_var.set(f"✅ {count} tarefa(s) marcada(s) como concluída(s)")

        # Atualizar estatísticas da sidebar
        self.update_sidebar_stats()
    
    def delete_selected_tasks(self):
        """Exclui tarefas selecionadas"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione tarefas para excluir!")
            return
        
        if not messagebox.askyesno("Confirmar", 
                                  f"Excluir {len(selected)} tarefa(s) selecionada(s)?"):
            return
        
        deleted_ids = []
        for item_id in selected:
            item = self.tree.item(item_id)
            task_id = item['values'][1]
            deleted_ids.append(task_id)
        
        # Remover da lista
        self.tasks = [t for t in self.tasks if t['id'] not in deleted_ids]
        
        self.save_tasks()
        self.load_tasks_to_table()
        self.update_task_count()
        
        if SCHEDULE_AVAILABLE:
            self.reschedule_all_tasks()
        
        self.status_var.set(f"🗑️ {len(selected)} tarefa(s) excluída(s)")

        # Atualizar estatísticas da sidebar
        self.update_sidebar_stats()
    
    def export_selected_tasks(self):
        """Exporta tarefas selecionadas"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione tarefas para exportar!")
            return
        
        tasks_to_export = []
        for item_id in selected:
            item = self.tree.item(item_id)
            task_id = item['values'][1]
            
            for task in self.tasks:
                if task['id'] == task_id:
                    tasks_to_export.append(task)
                    break
        
        # Escolher formato
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), 
                      ("CSV files", "*.csv"),
                      ("Text files", "*.txt"),
                      ("All files", "*.*")]
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(tasks_to_export, f, ensure_ascii=False, indent=2)
                
                elif filename.endswith('.csv'):
                    import csv
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['ID', 'Tarefa', 'Data/Hora', 'Prioridade', 'Categoria', 'Status'])
                        for task in tasks_to_export:
                            writer.writerow([
                                task['id'],
                                task['task'],
                                task.get('formatted_datetime', task['datetime']),
                                task.get('priority', ''),
                                task.get('category', ''),
                                task.get('status', '')
                            ])
                
                else:  # TXT
                    with open(filename, 'w', encoding='utf-8') as f:
                        for task in tasks_to_export:
                            f.write(f"ID: {task['id']}\n")
                            f.write(f"Tarefa: {task['task']}\n")
                            f.write(f"Data/Hora: {task.get('formatted_datetime', task['datetime'])}\n")
                            f.write(f"Prioridade: {task.get('priority', '')}\n")
                            f.write(f"Categoria: {task.get('category', '')}\n")
                            f.write(f"Status: {task.get('status', '')}\n")
                            f.write("-" * 40 + "\n\n")
                
                messagebox.showinfo("Sucesso", f"Tarefas exportadas para: {filename}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {e}")
    
    def edit_selected_task(self):
        """Edita a tarefa selecionada"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Selecione uma tarefa para editar!")
            return
        
        item = self.tree.item(selected[0])
        task_id = item['values'][1]
        
        for task in self.tasks:
            if task['id'] == task_id:
                self.edit_task(task)
                break
    
    def edit_task(self, task):
        """Abre janela para editar tarefa"""
        dialog = tk.Toplevel(self.root)
        dialog.title("✏️ Editar Tarefa")
        dialog.geometry("500x500")
        
        tk.Label(dialog, text="Editar Tarefa",
                font=('Segoe UI', 14, 'bold')).pack(pady=10)
        
        # Formulário
        form_frame = tk.Frame(dialog, padx=20)
        form_frame.pack(fill=tk.BOTH, expand=True)
        
        # Descrição
        tk.Label(form_frame, text="Descrição:").grid(row=0, column=0, sticky=tk.W, pady=5)
        task_entry = tk.Entry(form_frame, font=('Segoe UI', 11))
        task_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        task_entry.insert(0, task['task'])
        
        # Data e Hora
        tk.Label(form_frame, text="Data/Hora:").grid(row=1, column=0, sticky=tk.W, pady=5)
        task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
        
        datetime_frame = tk.Frame(form_frame)
        datetime_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        date_entry = tk.Entry(datetime_frame, width=12, font=('Segoe UI', 10))
        date_entry.grid(row=0, column=0, padx=(0, 5))
        date_entry.insert(0, task_date.strftime("%d/%m/%Y"))
        
        time_entry = tk.Entry(datetime_frame, width=8, font=('Segoe UI', 10))
        time_entry.grid(row=0, column=1)
        time_entry.insert(0, task_date.strftime("%H:%M"))
        
        # Prioridade
        tk.Label(form_frame, text="Prioridade:").grid(row=2, column=0, sticky=tk.W, pady=5)
        priority_var = tk.StringVar(value=task.get('priority', Priority.MEDIUM.value))
        for i, priority in enumerate(Priority):
            tk.Radiobutton(form_frame, text=priority.value, 
                          value=priority.value, variable=priority_var).grid(
                          row=2, column=1+i, sticky=tk.W, padx=(10 if i==0 else 5, 0))
        
        # Categoria
        tk.Label(form_frame, text="Categoria:").grid(row=3, column=0, sticky=tk.W, pady=5)
        category_var = tk.StringVar(value=task.get('category', TaskCategory.WORK.value))
        category_combo = ttk.Combobox(form_frame, textvariable=category_var,
                                     values=[cat.value for cat in TaskCategory], width=15)
        category_combo.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Status
        tk.Label(form_frame, text="Status:").grid(row=4, column=0, sticky=tk.W, pady=5)
        status_var = tk.StringVar(value=task.get('status', 'Pendente'))
        status_combo = ttk.Combobox(form_frame, textvariable=status_var,
                                   values=['Pendente', 'Concluída', 'Atrasada'], width=15)
        status_combo.grid(row=4, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Notas
        tk.Label(form_frame, text="Notas:").grid(row=5, column=0, sticky=tk.W, pady=5)
        notes_text = scrolledtext.ScrolledText(form_frame, height=4, font=('Segoe UI', 10))
        notes_text.grid(row=5, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        notes_text.insert(1.0, task.get('notes', ''))
        
        def save_changes():
            # Atualizar tarefa
            task['task'] = task_entry.get().strip()
            task_date_str = f"{date_entry.get().strip()} {time_entry.get().strip()}"
            try:
                new_datetime = datetime.strptime(task_date_str, "%d/%m/%Y %H:%M")
                task['datetime'] = new_datetime.strftime("%Y-%m-%d %H:%M:%S")
                task['formatted_datetime'] = new_datetime.strftime("%d/%m/%Y %H:%M")
            except:
                pass
            
            task['priority'] = priority_var.get()
            task['category'] = category_var.get()
            task['status'] = status_var.get()
            task['notes'] = notes_text.get(1.0, tk.END).strip()
            
            if task['status'] == 'Concluída' and 'completed_at' not in task:
                task['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.save_tasks()
            self.load_tasks_to_table()
            
            if SCHEDULE_AVAILABLE:
                self.reschedule_all_tasks()
            
            dialog.destroy()
            messagebox.showinfo("Sucesso", "Tarefa atualizada!")
        
        # Botões
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="💾 Salvar", command=save_changes,
                 bg='#28a745', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancelar", command=dialog.destroy,
                 bg='#6c757d', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
    
    def show_important_tasks(self):
        """Mostra tarefas importantes"""
        # Filtrar por prioridade alta e urgente
        filtered_tasks = [t for t in self.tasks 
                         if t.get('priority') in [Priority.HIGH.value, Priority.URGENT.value]]
        self.load_filtered_tasks(filtered_tasks)
        self.status_var.set(f"⭐ Mostrando tarefas importantes: {len(filtered_tasks)} encontradas")
    
    def show_today_tasks(self):
        """Mostra tarefas de hoje"""
        today = datetime.now().date()
        filtered_tasks = []
        
        for task in self.tasks:
            task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date()
            if task_date == today:
                filtered_tasks.append(task)
        
        self.load_filtered_tasks(filtered_tasks)
        self.status_var.set(f"📅 Mostrando tarefas de hoje: {len(filtered_tasks)} encontradas")
    
    def show_week_tasks(self):
        """Mostra tarefas desta semana"""
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        filtered_tasks = []
        for task in self.tasks:
            task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date()
            if week_start <= task_date <= week_end:
                filtered_tasks.append(task)
        
        self.load_filtered_tasks(filtered_tasks)
        self.status_var.set(f"📅 Mostrando tarefas desta semana: {len(filtered_tasks)} encontradas")
    
    def show_overdue_tasks(self):
        """Mostra tarefas atrasadas"""
        filtered_tasks = [t for t in self.tasks if t.get('status') == 'Atrasada']
        self.load_filtered_tasks(filtered_tasks)
        self.status_var.set(f"⚠️ Mostrando tarefas atrasadas: {len(filtered_tasks)} encontradas")
    
    def show_categories(self):
        """Abre gerenciador de categorias"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Gerenciar Categorias")
        dialog.geometry("400x500")
        
        tk.Label(dialog, text="Gerenciar Categorias Personalizadas",
                font=('Segoe UI', 12, 'bold')).pack(pady=10)
        
        # Lista de categorias
        listbox = tk.Listbox(dialog, height=15)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Carregar categorias personalizadas
        custom_cats = self.config.get("custom_categories", [])
        for cat in custom_cats:
            listbox.insert(tk.END, cat)
        
        # Controles
        control_frame = tk.Frame(dialog)
        control_frame.pack(pady=10)
        
        cat_entry = tk.Entry(control_frame, width=20)
        cat_entry.pack(side=tk.LEFT, padx=5)
        
        def add_category():
            new_cat = cat_entry.get().strip()
            if new_cat and new_cat not in custom_cats:
                custom_cats.append(new_cat)
                listbox.insert(tk.END, new_cat)
                cat_entry.delete(0, tk.END)
                
                self.config["custom_categories"] = custom_cats
                self.save_config()
        
        def remove_category():
            selection = listbox.curselection()
            if selection:
                index = selection[0]
                removed = listbox.get(index)
                listbox.delete(index)
                
                if removed in custom_cats:
                    custom_cats.remove(removed)
                    self.config["custom_categories"] = custom_cats
                    self.save_config()
        
        tk.Button(control_frame, text="Adicionar", command=add_category).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Remover", command=remove_category).pack(side=tk.LEFT, padx=5)
    
    def load_filtered_tasks(self, tasks):
        """Carrega tarefas filtradas na tabela"""
        # Limpar tabela atual
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Adicionar tarefas filtradas
        for task in tasks:
            task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
            
            # Determinar tag para cor
            status = task.get('status', 'Pendente')
            if status == 'Concluída':
                tag = 'completed'
            elif status == 'Atrasada':
                tag = 'overdue'
            else:
                tag = 'pending'
            
            # Adicionar à tabela
            self.tree.insert("", tk.END, values=(
                "",  # Checkbox vazio
                task['id'],
                task['task'],
                task_date.strftime("%d/%m/%Y %H:%M"),
                task.get('priority', 'Normal'),
                task.get('category', 'Geral'),
                status
            ), tags=(tag,))
        
        # Configurar cores das tags
        self.tree.tag_configure('overdue', foreground='#e74c3c', font=('Segoe UI', 9, 'bold'))
        self.tree.tag_configure('pending', foreground='#6c757d')
        self.tree.tag_configure('completed', foreground='#27ae60', font=('Segoe UI', 9, 'italic'))
    
    def open_quick_task_window(self):
        """Abre janela de tarefa rápida"""
        QuickTaskWindow(self.root, self.add_quick_task)
    
    def add_quick_task(self, task_data):
        """Adiciona tarefa rápida à fila"""
        self.quick_task_queue.put(task_data)
    
    def process_quick_task_queue(self):
        """Processa fila de tarefas rápidas"""
        while True:
            try:
                task_data = self.quick_task_queue.get(timeout=1)
                
                # Adicionar ID e outros campos necessários
                task_data['id'] = max([t['id'] for t in self.tasks], default=0) + 1
                task_data['created_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                task_data['is_overdue'] = False
                task_data['status'] = 'Pendente'
                
                if 'datetime' not in task_data:
                    task_data['datetime'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    task_data['formatted_datetime'] = datetime.now().strftime("%d/%m/%Y %H:%M")
                
                # Adicionar à lista principal
                self.tasks.append(task_data)
                
                # Salvar e atualizar na thread principal
                self.save_tasks()
                self.root.after(0, self.load_tasks_to_table)
                self.root.after(0, self.update_task_count)
                
                # Notificação
                if PLYER_AVAILABLE:
                    try:
                        notification.notify(
                            title="✅ Tarefa Rápida Adicionada",
                            message=f"{task_data['task'][:50]}...",
                            timeout=3
                        )
                    except:
                        pass
                
                self.quick_task_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Erro ao processar tarefa rápida: {e}")
    
    def open_pomodoro_timer(self):
        """Abre temporizador Pomodoro"""
        if not self.pomodoro_timer or not self.pomodoro_timer.window.winfo_exists():
            self.pomodoro_timer = PomodoroTimer(self.root)
    
    def open_statistics(self):
        """Abre janela de estatísticas"""
        StatisticsWindow(self.root, self.tasks)
    
    def open_search_window(self):
        """Abre janela de pesquisa avançada"""
        dialog = tk.Toplevel(self.root)
        dialog.title("🔍 Pesquisa Avançada")
        dialog.geometry("500x400")
        
        tk.Label(dialog, text="Pesquisa Avançada de Tarefas",
                font=('Segoe UI', 14, 'bold')).pack(pady=10)
        
        # Campos de pesquisa
        form_frame = tk.Frame(dialog)
        form_frame.pack(pady=10, padx=20)
        
        tk.Label(form_frame, text="Texto:").grid(row=0, column=0, sticky=tk.W, pady=5)
        text_entry = tk.Entry(form_frame, width=40)
        text_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        
        tk.Label(form_frame, text="Data Início:").grid(row=1, column=0, sticky=tk.W, pady=5)
        start_entry = tk.Entry(form_frame, width=15)
        start_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        start_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        
        tk.Label(form_frame, text="Data Fim:").grid(row=2, column=0, sticky=tk.W, pady=5)
        end_entry = tk.Entry(form_frame, width=15)
        end_entry.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        end_entry.insert(0, (datetime.now() + timedelta(days=7)).strftime("%d/%m/%Y"))
        
        # Opções de pesquisa
        options_frame = tk.Frame(dialog)
        options_frame.pack(pady=10)
        
        search_in_text = tk.BooleanVar(value=True)
        search_in_notes = tk.BooleanVar(value=False)
        
        tk.Checkbutton(options_frame, text="Buscar na descrição", 
                      variable=search_in_text).pack(anchor=tk.W)
        tk.Checkbutton(options_frame, text="Buscar nas notas", 
                      variable=search_in_notes).pack(anchor=tk.W)
        
        def perform_search():
            search_text = text_entry.get().lower()
            start_date = start_entry.get()
            end_date = end_entry.get()
            
            filtered_tasks = []
            for task in self.tasks:
                # Filtro por texto
                text_match = False
                if search_text:
                    if search_in_text.get() and search_text in task['task'].lower():
                        text_match = True
                    if search_in_notes.get() and 'notes' in task:
                        if search_text in task['notes'].lower():
                            text_match = True
                else:
                    text_match = True
                
                # Filtro por data
                date_match = False
                try:
                    task_date = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S").date()
                    start = datetime.strptime(start_date, "%d/%m/%Y").date()
                    end = datetime.strptime(end_date, "%d/%m/%Y").date()
                    
                    if start <= task_date <= end:
                        date_match = True
                except:
                    date_match = True
                
                if text_match and date_match:
                    filtered_tasks.append(task)
            
            self.load_filtered_tasks(filtered_tasks)
            dialog.destroy()
            self.status_var.set(f"🔍 {len(filtered_tasks)} tarefa(s) encontrada(s)")
        
        # Botões
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)
        
        tk.Button(button_frame, text="Pesquisar", command=perform_search,
                 bg='#3498db', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Cancelar", command=dialog.destroy,
                 bg='#6c757d', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
    
    def create_backup_now(self):
        """Cria um backup manual"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_path / f"backup_{timestamp}.json"
            
            backup_data = {
                "tasks": self.tasks,
                "config": self.config,
                "backup_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "3.0.0"
            }
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            self.update_backup_list()
            messagebox.showinfo("Sucesso", f"Backup criado:\n{backup_file.name}")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao criar backup: {e}")
    
    def start_auto_backup(self):
        """Inicia sistema de backup automático"""
        if not self.config.get("auto_backup", True):
            return
        
        def backup_job():
            try:
                # Manter apenas últimos 7 backups
                backups = list(self.backup_path.glob("backup_*.json"))
                if len(backups) > 7:
                    backups.sort(key=lambda x: x.stat().st_mtime)
                    for old_backup in backups[:-7]:
                        old_backup.unlink()
                
                # Criar novo backup
                self.create_backup_now()
                
            except Exception as e:
                print(f"Erro no backup automático: {e}")
        
        # Agendar backup
        if SCHEDULE_AVAILABLE:
            interval = self.config.get("backup_interval_hours", 24)
            schedule.every(interval).hours.do(backup_job)
    
    def update_backup_list(self):
        """Atualiza lista de backups"""
        if hasattr(self, 'backup_listbox'):
            self.backup_listbox.delete(0, tk.END)
            
            backups = list(self.backup_path.glob("backup_*.json"))
            backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for backup in backups[:10]:  # Mostrar últimos 10
                timestamp = backup.stem.replace("backup_", "")
                try:
                    dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                    display = dt.strftime("%d/%m/%Y %H:%M:%S")
                except:
                    display = timestamp
                
                self.backup_listbox.insert(tk.END, display)
    
    def restore_backup(self):
        """Restaura backup selecionado"""
        selection = self.backup_listbox.curselection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um backup para restaurar!")
            return
        
        index = selection[0]
        backups = list(self.backup_path.glob("backup_*.json"))
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if index < len(backups):
            backup_file = backups[index]
            
            if not messagebox.askyesno("Confirmar", 
                                      f"Restaurar backup de {backup_file.name}?\n\n"
                                      f"Esta ação substituirá os dados atuais."):
                return
            
            try:
                with open(backup_file, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                
                self.tasks = backup_data.get("tasks", [])
                self.config = backup_data.get("config", self.config)
                
                self.save_tasks()
                self.save_config()
                self.load_tasks_to_table()
                self.update_task_count()
                
                messagebox.showinfo("Sucesso", "Backup restaurado com sucesso!")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao restaurar backup: {e}")
    
    def delete_backup(self):
        """Exclui backup selecionado"""
        selection = self.backup_listbox.curselection()
        if not selection:
            messagebox.showwarning("Aviso", "Selecione um backup para excluir!")
            return
        
        index = selection[0]
        backups = list(self.backup_path.glob("backup_*.json"))
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if index < len(backups):
            backup_file = backups[index]
            
            if messagebox.askyesno("Confirmar", f"Excluir backup {backup_file.name}?"):
                try:
                    backup_file.unlink()
                    self.update_backup_list()
                    messagebox.showinfo("Sucesso", "Backup excluído!")
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao excluir: {e}")
    
    def export_all_data(self):
        """Exporta todos os dados"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), 
                      ("All files", "*.*")]
        )
        
        if filename:
            try:
                export_data = {
                    "tasks": self.tasks,
                    "config": self.config,
                    "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "version": "3.0.0"
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                messagebox.showinfo("Sucesso", f"Dados exportados para: {filename}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {e}")
    
    def import_data(self):
        """Importa dados de arquivo"""
        from tkinter import filedialog
        
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), 
                      ("All files", "*.*")]
        )
        
        if filename:
            if not messagebox.askyesno("Confirmar", 
                                      "Importar dados?\n\n"
                                      "Esta ação substituirá os dados atuais."):
                return
            
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)
                
                self.tasks = import_data.get("tasks", [])
                self.config.update(import_data.get("config", {}))
                
                self.save_tasks()
                self.save_config()
                self.load_tasks_to_table()
                self.update_task_count()
                
                messagebox.showinfo("Sucesso", "Dados importados com sucesso!")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao importar: {e}")
    
    def export_all_tasks(self):
        """Exporta todas as tarefas"""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"),
                      ("JSON files", "*.json"),
                      ("Text files", "*.txt")]
        )
        
        if filename:
            try:
                if filename.endswith('.json'):
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(self.tasks, f, ensure_ascii=False, indent=2)
                
                elif filename.endswith('.csv'):
                    import csv
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['ID', 'Tarefa', 'Data/Hora', 'Prioridade', 'Categoria', 'Status', 'Notas'])
                        for task in self.tasks:
                            writer.writerow([
                                task['id'],
                                task['task'],
                                task.get('formatted_datetime', task['datetime']),
                                task.get('priority', ''),
                                task.get('category', ''),
                                task.get('status', ''),
                                task.get('notes', '')[:100]
                            ])
                
                else:  # TXT
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"RELATÓRIO DE TAREFAS - {datetime.now().strftime('%d/%m/%Y %H:%M')}\n")
                        f.write("="*60 + "\n\n")
                        
                        for task in self.tasks:
                            f.write(f"ID: {task['id']}\n")
                            f.write(f"Tarefa: {task['task']}\n")
                            f.write(f"Data/Hora: {task.get('formatted_datetime', task['datetime'])}\n")
                            f.write(f"Prioridade: {task.get('priority', '')}\n")
                            f.write(f"Categoria: {task.get('category', '')}\n")
                            f.write(f"Status: {task.get('status', '')}\n")
                            
                            if 'notes' in task and task['notes']:
                                f.write(f"Notas: {task['notes'][:100]}\n")
                            
                            f.write("-"*40 + "\n\n")
                
                messagebox.showinfo("Sucesso", f"Tarefas exportadas para: {filename}")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao exportar: {e}")
    
    def report_bug(self):
        """Abre interface para reportar bugs"""
        dialog = tk.Toplevel(self.root)
        dialog.title("🐛 Reportar Bug")
        dialog.geometry("500x400")
        
        tk.Label(dialog, text="Reportar Problema ou Bug",
                font=('Segoe UI', 14, 'bold')).pack(pady=10)
        
        # Formulário
        form_frame = tk.Frame(dialog)
        form_frame.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        tk.Label(form_frame, text="Título:").pack(anchor=tk.W)
        title_entry = tk.Entry(form_frame)
        title_entry.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(form_frame, text="Descrição:").pack(anchor=tk.W)
        desc_text = scrolledtext.ScrolledText(form_frame, height=10)
        desc_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        def send_report():
            title = title_entry.get().strip()
            description = desc_text.get(1.0, tk.END).strip()
            
            if not title or not description:
                messagebox.showwarning("Aviso", "Preencha todos os campos!")
                return
            
            # Aqui você implementaria o envio real do bug
            # Por enquanto, apenas mostra mensagem
            messagebox.showinfo("Relatório Enviado", 
                              "Obrigado pelo seu relatório!\n\n"
                              "Em uma versão real, isso seria enviado para nossos desenvolvedores.")
            dialog.destroy()
        
        tk.Button(dialog, text="📤 Enviar Relatório", command=send_report,
                 bg='#e74c3c', fg='white', padx=20, pady=10).pack(pady=10)
    
    def check_for_updates(self):
        """Verifica atualizações"""
        # Simulação de verificação de atualizações
        import random
        if random.choice([True, False]):
            messagebox.showinfo("Atualizações", 
                              "✅ Você está usando a versão mais recente!")
        else:
            if messagebox.askyesno("Atualização Disponível",
                                  "Nova versão disponível!\n\n"
                                  "Deseja visitar o site para baixar?"):
                webbrowser.open("https://www.seusite.com/download")
    
    def on_closing(self):
        """Trata o fechamento da janela"""
        if self.config.get("minimize_to_tray", True):
            self.hide_to_tray()
        else:
            self.quit_app_silent()
    
    def hide_to_tray(self):
        """Esconde a janela para a bandeja do sistema"""
        self.root.withdraw()
        if self.config.get("show_notification_on_minimize", True) and PLYER_AVAILABLE:
            try:
                notification.notify(
                    title="Task Reminder",
                    message="O aplicativo continua em execução na bandeja do sistema.",
                    timeout=3,
                    app_name="Task Reminder"
                )
            except:
                pass
    
    def show_window(self):
        """Mostra a janela principal"""
        self.root.deiconify()
        self.root.state('normal')
        self.root.lift()
        self.root.focus_force()
    
    def open_settings(self):
        """Abre a janela de configurações"""
        self.notebook.select(3)  # Seleciona a aba de configurações
        self.show_window()
    
    def quit_app_silent(self):
        """Encerra o aplicativo silenciosamente"""
        self.is_quitting = True
        self.quit_app()
    
    def quit_app(self):
        """Encerra o aplicativo corretamente"""
        self.scheduler_running = False
        
        # Fechar janelas de notificação
        for window in self.notification_windows[:]:
            try:
                window.window.destroy()
            except:
                pass
        
        # Parar hotkeys
        if KEYBOARD_AVAILABLE and self.hotkey_enabled:
            try:
                keyboard.unhook_all()
            except:
                pass
        
        # Salvar dados
        try:
            self.save_tasks()
            self.save_config()
        except:
            pass
        
        # Parar ícone da bandeja
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
        
        # Fechar janela
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        
        sys.exit(0)
    
    def validate_datetime(self, date_str, time_str):
        """Valida data e hora"""
        try:
            datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M")
            return True
        except ValueError:
            return False
    
    def set_current_time(self):
        """Define a data e hora atuais"""
        now = datetime.now()
        self.date_entry.delete(0, tk.END)
        self.time_entry.delete(0, tk.END)
        self.date_entry.insert(0, now.strftime("%d/%m/%Y"))
        self.time_entry.insert(0, now.strftime("%H:%M"))
    
    def save_tasks(self):
        """Salva tarefas no arquivo"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Erro ao salvar tarefas: {e}")
            return False
    
    def load_tasks(self):
        """Carrega tarefas do arquivo"""
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                
                # Atualizar estrutura se necessário
                for task in tasks:
                    if 'is_overdue' not in task:
                        task_datetime = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
                        task['is_overdue'] = task_datetime < datetime.now()
                
                return tasks
            except Exception as e:
                print(f"Erro ao carregar tarefas: {e}")
                return []
        return []
    
    def load_tasks_to_table(self):
        """Carrega tarefas na tabela"""
        # Limpar tabela
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Ordenar tarefas
        pending_tasks = [t for t in self.tasks if t.get('status') == 'Pendente']
        completed_tasks = [t for t in self.tasks if t.get('status') == 'Concluída']
        overdue_tasks = [t for t in self.tasks if t.get('status') == 'Atrasada']
        
        # Ordenar pendentes por data
        pending_tasks.sort(key=lambda x: x['datetime'])
        overdue_tasks.sort(key=lambda x: x['datetime'])
        
        # Combinar listas: atrasadas, pendentes, concluídas
        sorted_tasks = overdue_tasks + pending_tasks + completed_tasks
        
        # Adicionar à tabela
        for index, task in enumerate(sorted_tasks):
            task_datetime = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
            
            # Determinar tag para status
            status = task.get('status', 'Pendente')
            if status == 'Concluída':
                status_tag = 'completed'
            elif status == 'Atrasada':
                status_tag = 'overdue'
            else:
                status_tag = 'pending'
            
            # Determinar tag para cor alternada
            row_tag = 'evenrow' if index % 2 == 0 else 'oddrow'
            
            # Tags combinadas
            all_tags = (status_tag, row_tag)
            
            # Adicionar à tabela
            self.tree.insert("", tk.END, values=(
                "",  # Checkbox vazio
                task['id'],
                task['task'][:80] + "..." if len(task['task']) > 80 else task['task'],
                task_datetime.strftime("%d/%m/%Y %H:%M"),
                task.get('priority', 'Normal'),
                task.get('category', 'Geral'),
                status
            ), tags=all_tags)
        
        # Configurar cores das tags
        self.style_tree_tags()
        
        # Atualizar contador
        self.update_task_count()

        # Atualizar estatísticas da sidebar
        self.update_sidebar_stats()

    def style_tree_tags(self):
        """Estiliza as tags da árvore para melhor visualização"""
        # Configurar estilos para diferentes status
        self.tree.tag_configure('overdue', 
                            background='#ffeaea', 
                            foreground='#d63031',
                            font=('Segoe UI', 9, 'bold'))
        
        self.tree.tag_configure('pending', 
                            background='#fff9e6', 
                            foreground='#e17055',
                            font=('Segoe UI', 9))
        
        self.tree.tag_configure('completed', 
                            background='#e8f6ef', 
                            foreground='#27ae60',
                            font=('Segoe UI', 9, 'italic'))
        
        # Alternar cores para linhas
        self.tree.tag_configure('oddrow', background='#f8f9fa')
        self.tree.tag_configure('evenrow', background='#ffffff')
    
    def schedule_task_notifications(self, task):
        """Agenda notificações para uma tarefa"""
        if not SCHEDULE_AVAILABLE or task.get('status') != 'Pendente':
            return
        
        try:
            task_time = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            
            if task_time > now:
                # Notificação principal
                schedule.every().day.at(task_time.strftime("%H:%M")).do(
                    self.send_main_notification, task['id']).tag(f"task_{task['id']}")
                
                # Notificações de lembrete
                for key in task:
                    if key.startswith('reminder_') and task[key]:
                        minutes = int(key.replace('reminder_', '').replace('min', ''))
                        reminder_time = task_time - timedelta(minutes=minutes)
                        if reminder_time > now:
                            schedule.every().day.at(reminder_time.strftime("%H:%M")).do(
                                self.send_reminder_notification, 
                                task['id'], f"{minutes} minutos"
                            ).tag(f"reminder_{minutes}min_{task['id']}")
                            
        except Exception as e:
            print(f"Erro ao agendar notificações: {e}")
    
    def reschedule_all_tasks(self):
        """Reagenda todas as notificações"""
        if not SCHEDULE_AVAILABLE:
            return
        
        schedule.clear()
        for task in self.tasks:
            if task.get('status') == 'Pendente':
                self.schedule_task_notifications(task)
    
    def send_main_notification(self, task_id):
        """Envia notificação principal"""
        # Encontrar tarefa
        task = None
        for t in self.tasks:
            if t['id'] == task_id:
                task = t
                break
        
        if not task:
            return
        
        # Notificação do sistema
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title="🚨 Task Reminder",
                    message=f"⏰ HORA DA TAREFA!\n\n{task['task']}",
                    timeout=self.config.get("notification_duration", 15),
                    app_name="Task Reminder"
                )
            except:
                pass
        
        # Janela de notificação personalizada (AGORA COM task_data COMPLETO incluindo ID)
        self.show_notification_window(task['task'], None, task.copy())  # Usar .copy() para não modificar original
    
    def send_reminder_notification(self, task_id, minutes):
        """Envia notificação de lembrete"""
        # Encontrar tarefa
        task = None
        for t in self.tasks:
            if t['id'] == task_id:
                task = t
                break
        
        if not task:
            return
        
        # Notificação do sistema
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title="🔔 Task Reminder",
                    message=f"⏰ Lembrete ({minutes}):\n\n{task['task']}",
                    timeout=10,
                    app_name="Task Reminder"
                )
            except:
                pass
        
        # Janela de notificação personalizada (COM task_data COMPLETO)
        self.show_notification_window(task['task'], f"Lembrete ({minutes})", task.copy())
    
    def show_notification_window(self, task_text, reminder_text, task_data):
        """Mostra janela de notificação"""
        def create_window():
            try:
                # Usar thread principal para criar a janela
                self.root.after(0, lambda: self._create_notification_window(task_text, reminder_text, task_data))
            except Exception as e:
                print(f"Erro ao criar janela de notificação: {e}")
        
        threading.Thread(target=create_window, daemon=True).start()
    
    def _create_notification_window(self, task_text, reminder_text, task_data):
        """Cria janela de notificação na thread principal"""
        try:
            # Passar self (app principal) como parent_app
            notif_window = NotificationWindow(self, task_text, reminder_text, task_data)
            self.notification_windows.append(notif_window)
        except Exception as e:
            print(f"Erro ao criar janela de notificação: {e}")
    
    def check_pending_tasks(self):
        """Verifica tarefas pendentes periodicamente"""
        check_interval = self.config.get("check_interval", 60)
        
        while self.scheduler_running:
            time.sleep(check_interval)
            
            now = datetime.now()
            needs_update = False
            
            # Verificar tarefas atrasadas
            for task in self.tasks:
                if task.get('status') == 'Pendente':
                    task_time = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
                    if task_time < now and not task.get('is_overdue', False):
                        task['is_overdue'] = True
                        task['status'] = 'Atrasada'
                        needs_update = True
            
            # Atualizar interface se necessário
            if needs_update:
                self.root.after(0, self.load_tasks_to_table)
                self.root.after(0, self.update_task_count)
    
    def start_scheduler(self):
        """Inicia o scheduler"""
        if not SCHEDULE_AVAILABLE:
            return
        
        def run_scheduler():
            while self.scheduler_running:
                schedule.run_pending()
                time.sleep(1)
        
        threading.Thread(target=run_scheduler, daemon=True).start()
    
    def save_all_settings(self):
        """Salva todas as configurações"""
        # Atualizar config com valores atuais
        config_updates = {
            'start_with_windows': self.start_with_windows_var.get() if hasattr(self, 'start_with_windows_var') else True,
            'minimize_to_tray': self.minimize_to_tray_var.get() if hasattr(self, 'minimize_to_tray_var') else True,
            'show_tray_icon': self.show_tray_icon_var.get() if hasattr(self, 'show_tray_icon_var') else True,
            'enable_global_hotkey': self.enable_hotkey_var.get() if hasattr(self, 'enable_hotkey_var') else True,
            'global_hotkey': self.hotkey_entry.get() if hasattr(self, 'hotkey_entry') else 'ctrl+shift+t',
            'auto_backup': self.auto_backup_var.get() if hasattr(self, 'auto_backup_var') else True,
            'backup_interval_hours': self.backup_interval_var.get() if hasattr(self, 'backup_interval_var') else 24,
            'auto_complete_overdue': self.auto_complete_var.get() if hasattr(self, 'auto_complete_var') else False,
            'voice_reminders': self.voice_reminders_var.get() if hasattr(self, 'voice_reminders_var') else False,
            'default_priority': self.default_priority_var.get() if hasattr(self, 'default_priority_var') else Priority.MEDIUM.value,
            'default_category': self.default_category_var.get() if hasattr(self, 'default_category_var') else TaskCategory.WORK.value,
            'notification_sound': self.notification_sound_var.get() if hasattr(self, 'notification_sound_var') else True,
            'show_notification_on_minimize': self.show_notification_var.get() if hasattr(self, 'show_notification_var') else True,
            'notification_duration': self.notification_duration_var.get() if hasattr(self, 'notification_duration_var') else 15,
            'notification_type': self.notification_type_var.get() if hasattr(self, 'notification_type_var') else 'ambos'
        }

        old_start_with_windows = self.config.get("start_with_windows", True)
        new_start_with_windows = config_updates['start_with_windows']

        # Gerenciar autostart se a configuração mudou
        if old_start_with_windows != new_start_with_windows:
            if new_start_with_windows:
                self.setup_autostart()
            else:
                self.remove_autostart()
        
        self.config.update(config_updates)
        
        if self.save_config():
            if not self.is_quitting:
                messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
                self.status_var.set("✅ Configurações salvas")
        else:
            if not self.is_quitting:
                messagebox.showerror("Erro", "Erro ao salvar configurações.")
        
        self.config.update(config_updates)
    
    def restore_default_settings(self):
        """Restaura configurações padrão"""
        if messagebox.askyesno("Confirmar", 
                              "Restaurar todas as configurações para os valores padrão?\n\n"
                              "Esta ação não pode ser desfeita."):
            
            if self.config.get("start_with_windows", True):
                self.remove_autostart()

            default_config = {
                "start_with_windows": False,
                "minimize_to_tray": True,
                "show_tray_icon": True,
                "enable_global_hotkey": True,
                "global_hotkey": "ctrl+shift+t",
                "auto_backup": True,
                "backup_interval_hours": 24,
                "auto_complete_overdue": False,
                "voice_reminders": False,
                "default_priority": Priority.MEDIUM.value,
                "default_category": TaskCategory.WORK.value,
                "notification_sound": True,
                "show_notification_on_minimize": True,
                "notification_duration": 15,
                "notification_type": "ambos",
                "show_warnings": True
            }
            
            self.config = default_config
            self.save_config(default_config)
            
            # Atualizar variáveis
            for var_name in ['start_with_windows_var', 'minimize_to_tray_var', 
                           'show_tray_icon_var', 'enable_hotkey_var', 'auto_backup_var',
                           'auto_complete_var', 'voice_reminders_var', 'notification_sound_var',
                           'show_notification_var']:
                if hasattr(self, var_name):
                    getattr(self, var_name).set(True if 'enable' in var_name or 'show' in var_name 
                                              or 'auto' in var_name else False)
            
            if hasattr(self, 'hotkey_entry'):
                self.hotkey_entry.delete(0, tk.END)
                self.hotkey_entry.insert(0, "ctrl+shift+t")
            
            if hasattr(self, 'backup_interval_var'):
                self.backup_interval_var.set(24)
            
            if hasattr(self, 'default_priority_var'):
                self.default_priority_var.set(Priority.MEDIUM.value)
            
            if hasattr(self, 'default_category_var'):
                self.default_category_var.set(TaskCategory.WORK.value)
            
            if hasattr(self, 'notification_duration_var'):
                self.notification_duration_var.set(15)
            
            if hasattr(self, 'notification_type_var'):
                self.notification_type_var.set("ambos")
            
            # Reconfigurar autostart
            if WINSHELL_AVAILABLE:
                self.setup_autostart()
            
            # Reconfigurar hotkey
            if KEYBOARD_AVAILABLE:
                try:
                    keyboard.unhook_all()
                    if self.config.get("enable_global_hotkey", True):
                        self.setup_global_hotkey()
                except:
                    pass
            
            # Reconfigurar ícone da bandeja
            if self.tray_icon:
                try:
                    self.tray_icon.stop()
                except:
                    pass
                self.tray_icon = None
            
            if PYSTRAY_AVAILABLE and PILLOW_AVAILABLE and self.config.get("show_tray_icon", True):
                self.setup_tray_icon()
            
            messagebox.showinfo("Sucesso", "Configurações padrão restauradas!")
            self.status_var.set("🔄 Configurações restauradas")

# Função principal
def main():
    """Função principal"""
    import ctypes
    mutex_name = "Global\\TaskReminderProAppV3"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    
    if last_error == 183:
        try:
            messagebox.showinfo(
                "Task Reminder",
                "O aplicativo já está em execução!\n"
                "Verifique o ícone na bandeja do sistema."
            )
        except:
            pass
        sys.exit(0)
    
    # Criar janela principal
    root = tk.Tk()
    
    try:
        app = TaskReminderApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Erro fatal: {e}")
        traceback.print_exc()
        try:
            messagebox.showerror("Erro Fatal", f"Ocorreu um erro no aplicativo:\n\n{e}")
        except:
            pass
    finally:
        ctypes.windll.kernel32.CloseHandle(mutex)

if __name__ == "__main__":
    main()