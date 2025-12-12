import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import threading
from datetime import datetime, timedelta
import time
from pathlib import Path
import traceback

# Tente importar bibliotecas opcionais
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
    from PIL import Image, ImageDraw
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
    from tkcalendar import Calendar, DateEntry
    TKCALENDAR_AVAILABLE = True
except ImportError:
    TKCALENDAR_AVAILABLE = False
    print("tkcalendar não está instalado. Use: pip install tkcalendar")

class NotificationWindow:
    """Janela de notificação"""
    def __init__(self, task_text, reminder_text=None):
        self.window = tk.Tk()
        self.window.title("Task Reminder - Notificação")
        self.window.geometry("400x200")
        self.window.configure(bg='#2c3e50')
        
        # Tornar a janela sempre no topo
        self.window.attributes('-topmost', True)
        
        # Impedir redimensionamento
        self.window.resizable(False, False)
        
        # Configurar fechamento
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Frame principal
        main_frame = tk.Frame(self.window, bg='#2c3e50', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Ícone e título
        icon_frame = tk.Frame(main_frame, bg='#2c3e50')
        icon_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Ícone
        icon_label = tk.Label(icon_frame, text="⏰", font=('Arial', 24), 
                            bg='#2c3e50', fg='#f39c12')
        icon_label.pack(side=tk.LEFT)
        
        title_text = "Lembrete de Tarefa" if reminder_text else "Tarefa Agora!"
        title_label = tk.Label(icon_frame, text=title_text, 
                             font=('Arial', 16, 'bold'), 
                             bg='#2c3e50', fg='white')
        title_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Texto da notificação
        if reminder_text:
            message = f"{reminder_text}\n\n{task_text}"
        else:
            message = f"É hora de realizar a tarefa:\n\n{task_text}"
        
        message_label = tk.Label(main_frame, text=message, 
                               font=('Arial', 12), 
                               bg='#2c3e50', fg='#ecf0f1',
                               justify=tk.LEFT, wraplength=350)
        message_label.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Botão OK
        button_frame = tk.Frame(main_frame, bg='#2c3e50')
        button_frame.pack(fill=tk.X)
        
        ok_button = tk.Button(button_frame, text="OK", 
                            font=('Arial', 12, 'bold'),
                            bg='#3498db', fg='white',
                            padx=30, pady=10,
                            command=self.on_close,
                            cursor='hand2')
        ok_button.pack()
        
        # Configurar estilo do botão
        ok_button.configure(activebackground='#2980b9', activeforeground='white')
        
        # Focar no botão OK
        ok_button.focus_set()
        self.window.bind('<Return>', lambda e: self.on_close())
        
    def on_close(self):
        self.window.destroy()
        
    def show(self):
        self.window.mainloop()

class TaskReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Task Reminder")
        self.root.geometry("900x750")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Ocultar console
        self.hide_console()
        
        # Configurar caminhos dos arquivos
        if getattr(sys, 'frozen', False):
            # Executando como .exe
            self.exe_dir = Path(sys.executable).parent.absolute()
        else:
            # Executando como script Python
            self.exe_dir = Path(__file__).parent.absolute()

        # Criar pasta images se não existir
        self.images_path = self.exe_dir / "images"
        self.images_path.mkdir(exist_ok=True)

        # Caminhos dos arquivos
        self.tasks_file = self.exe_dir / "tasks.json"
        self.config_file = self.exe_dir / "config.json"
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
        self.add_button = None 
        self.update_button = None 
        self.active_timers = []
        
        # Configurar cores
        self.setup_colors()
        
        # Configurar ícone do aplicativo
        if PILLOW_AVAILABLE:
            self.setup_app_icon()
        
        # Configurar interface
        self.setup_ui()
        
        # Configurar eventos de teclado
        self.setup_keyboard_shortcuts()
        
        # Carregar tarefas
        self.load_tasks()
        self.load_tasks_to_table()
        
        # Configurar autostart
        if self.config.get("start_with_windows", True) and WINSHELL_AVAILABLE:
            self.setup_autostart()
        
        # Configurar ícone na bandeja
        if self.config.get("show_tray_icon", True) and PYSTRAY_AVAILABLE and PILLOW_AVAILABLE:
            self.setup_tray_icon()
        
        # Verificar tarefas imediatamente
        threading.Thread(target=self.check_pending_tasks, daemon=True).start()
        
        # Verificar dependências
        self.check_dependencies()
        
        # Agendar notificações para tarefas existentes
        self.reschedule_all_tasks()

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

    def setup_keyboard_shortcuts(self):
        """atalhos de teclado"""
        # Apertar Enter
        self.root.bind('<Return>', self.handle_enter_key)
        
        # F2 para editar tarefa
        self.root.bind('<F2>', lambda e: self.edit_selected_task())
        
        # Delete para excluir tarefa
        self.root.bind('<Delete>', lambda e: self.remove_selected_task())
        
        # F1 para marcar como concluída
        self.root.bind('<F1>', lambda e: self.mark_as_completed())
        
        # Esc para cancelar edição
        self.root.bind('<Escape>', lambda e: self.cancel_edit())
        
        # Ctrl+N para nova tarefa
        self.root.bind('<Control-n>', lambda e: self.focus_new_task())
        
        # Ctrl+S para salvar
        self.root.bind('<Control-s>', lambda e: self.update_task() if self.editing_task_id else None)

        # F3 para limpar concluídas
        self.root.bind('<F3>', lambda e: self.clear_completed_tasks())

    def handle_enter_key(self, event):
        widget = event.widget
        
        if self.editing_task_id and widget in [self.task_entry, self.time_spinbox_hour, self.time_spinbox_minute]:
            self.update_task()
        elif not self.editing_task_id and widget in [self.task_entry, self.time_spinbox_hour, self.time_spinbox_minute]:
            self.add_task()
        elif widget == self.tree:
            self.edit_selected_task()
        
        # Prevenir comportamento padrão
        return "break"

    def focus_new_task(self):
        """Foca no campo de descrição para nova tarefa"""
        self.task_entry.focus()
        self.task_entry.select_range(0, tk.END)

    def check_dependencies(self):
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
        if not TKCALENDAR_AVAILABLE:
            missing.append("tkcalendar (para seleção de data)")
        
        if missing:
            self.status_var.set("⚠️ Algumas funcionalidades podem estar limitadas")

    def setup_colors(self):
        """Configura as cores"""
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
            'border': '#dee2e6'
        }

    def load_config(self):
        """Carrega as configurações"""
        default_config = {
            "start_with_windows": True,
            "minimize_to_tray": True,
            "show_tray_icon": True,
            "notification_sound": True,
            "notification_duration": 15,
            "check_interval": 60,
            "theme": "light",
            "show_notification_on_minimize": True
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
            # Salvar configurações
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
        if not PILLOW_AVAILABLE:
            return
            
        try:
            image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            draw.ellipse([(10, 10), (54, 54)], fill='#007bff')
            
            draw.rectangle([(26, 20), (38, 40)], fill='white')
            draw.polygon([(24, 20), (40, 20), (38, 18), (26, 18)], fill='white')
            
            draw.line([(32, 40), (32, 44)], fill='white', width=2)
            draw.ellipse([(30, 44), (34, 48)], fill='white')
            
            # Salvar como ICO
            image.save(self.icon_file, format='ICO')
        except Exception as e:
            print(f"Erro ao criar ícone padrão: {e}")

    def setup_autostart(self):
        """Configura o aplicativo para iniciar com o Windows"""
        if not WINSHELL_AVAILABLE:
            return
            
        try:
            startup_path = winshell.startup()
            shortcut_path = os.path.join(startup_path, "TaskReminder.lnk")
            
            target = sys.executable
            script = os.path.abspath(__file__)
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target
            shortcut.Arguments = f'"{script}" --minimized'
            shortcut.WorkingDirectory = os.path.dirname(script)

            if os.path.exists(self.icon_file):
                shortcut.IconLocation = str(self.icon_file)
            
            # Configurar para executar minimizado sem console
            shortcut.WindowStyle = 7  # 7 = Minimized, 1 = Normal, 3 = Maximized
            
            shortcut.save()
            
        except Exception as e:
            print(f"Erro ao configurar autostart: {e}")

    def remove_autostart(self):
        """Remove o aplicativo do início automático do Windows"""
        if not WINSHELL_AVAILABLE:
            return False
            
        try:
            startup_path = winshell.startup()
            shortcut_path = os.path.join(startup_path, "TaskReminder.lnk")
            
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
                return True
        except Exception as e:
            print(f"Erro ao remover autostart: {e}")
        return False

    def setup_tray_icon(self):
        """Configura o ícone na bandeja do sistema"""
        if not PYSTRAY_AVAILABLE or not PILLOW_AVAILABLE:
            return
            
        try:
            if os.path.exists(self.icon_file):
                image = Image.open(self.icon_file)
            else:
                image = Image.new('RGB', (64, 64), color='#007bff')
            
            menu = (
                item('Mostrar', self.show_window),
                item('Configurações', self.open_settings),
                item('Sair', self.quit_app_silent)
            )
            
            self.tray_icon = pystray.Icon(
                "task_reminder",
                image,
                "Task Reminder",
                menu
            )
            
            # Iniciar ícone da bandeja em thread separada
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            
        except Exception as e:
            print(f"Erro ao configurar ícone da bandeja: {e}")

    def on_closing(self):
        """fechamento da janela"""
        if self.config.get("minimize_to_tray", True):
            self.hide_to_tray()
        else:
            self.quit_app_silent()

    def hide_to_tray(self):
        """Esconde a janela"""
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

    def setup_ui(self):
        """Configura a interface do usuário"""
        # Configurar estilo
        self.setup_styles()
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Abas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=10)
        
        # Aba de Tarefas
        self.setup_tasks_tab()
        
        # Aba de Configurações
        self.setup_settings_tab()
        
        # Barra de status
        self.setup_status_bar()

    def setup_styles(self):
        """Configura os estilos do aplicativo"""
        style = ttk.Style()
        
        # Configurar tema
        if self.config.get("theme") == "dark":
            style.theme_use('alt')
        else:
            style.theme_use('clam')
        
        self.root.configure(bg=self.colors['bg'])
        
        style.configure("Accent.TButton", 
                       background=self.colors['accent'],
                       foreground='white',
                       font=('Segoe UI', 10, 'bold'))
        
        style.map("Accent.TButton",
                 background=[('active', self.colors['accent']),
                           ('pressed', self.colors['accent'])])

    def setup_tasks_tab(self):
        """Configura a aba de tarefas"""
        tasks_frame = ttk.Frame(self.notebook)
        self.notebook.add(tasks_frame, text="📋 Tarefas")
        
        tasks_frame.columnconfigure(0, weight=1)
        tasks_frame.rowconfigure(1, weight=1)
        
        input_frame = ttk.LabelFrame(tasks_frame, text="Nova Tarefa", padding="15")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)
        
        ttk.Label(input_frame, text="Descrição:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.task_entry = ttk.Entry(input_frame, width=50, font=('Segoe UI', 10))
        self.task_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        self.task_entry.focus()
        
        ttk.Label(input_frame, text="Data/Hora:").grid(row=1, column=0, sticky=tk.W, pady=5)
        
        datetime_frame = ttk.Frame(input_frame)
        datetime_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        if TKCALENDAR_AVAILABLE:
            # Configurar data atual como padrão
            today = datetime.now()
            self.date_entry = DateEntry(
                datetime_frame, 
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='dd/mm/yyyy',
                font=('Segoe UI', 10),
                mindate=today
            )
            self.date_entry.grid(row=0, column=0, padx=(0, 5))
        else:
            self.date_entry = ttk.Entry(datetime_frame, width=12, font=('Segoe UI', 10))
            self.date_entry.grid(row=0, column=0, padx=(0, 5))
            self.date_entry.insert(0, datetime.now().strftime("%d/%m/%Y"))
        
        ttk.Label(datetime_frame, text="às").grid(row=0, column=1, padx=(5, 5))
        
        self.time_spinbox_hour = ttk.Spinbox(
            datetime_frame,
            from_=0,
            to=23,
            width=4,
            font=('Segoe UI', 10),
            wrap=True
        )
        self.time_spinbox_hour.grid(row=0, column=2, padx=(0, 2))
        
        ttk.Label(datetime_frame, text=":").grid(row=0, column=3, padx=(0, 2))
        
        self.time_spinbox_minute = ttk.Spinbox(
            datetime_frame,
            from_=0,
            to=59,
            width=4,
            font=('Segoe UI', 10),
            wrap=True
        )
        self.time_spinbox_minute.grid(row=0, column=4, padx=(0, 5))
        
        next_hour = datetime.now() + timedelta(hours=1)
        self.time_spinbox_hour.set(next_hour.strftime("%H"))
        self.time_spinbox_minute.set("00")
        
        ttk.Button(
            datetime_frame, 
            text="Agora", 
            width=8,
            command=self.set_current_time
        ).grid(row=0, column=5, padx=(10, 0))
        
        ttk.Label(input_frame, text="Lembretes:").grid(row=2, column=0, sticky=tk.W, pady=5)
        
        reminders_frame = ttk.Frame(input_frame)
        reminders_frame.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        self.reminder_5min = tk.BooleanVar()
        self.reminder_10min = tk.BooleanVar()
        self.reminder_30min = tk.BooleanVar()
        self.reminder_1h = tk.BooleanVar()
        
        ttk.Checkbutton(reminders_frame, text="5 min antes", 
                       variable=self.reminder_5min).grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        ttk.Checkbutton(reminders_frame, text="10 min antes", 
                       variable=self.reminder_10min).grid(row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(reminders_frame, text="30 min antes", 
                       variable=self.reminder_30min).grid(row=1, column=0, padx=(0, 10), sticky=tk.W)
        ttk.Checkbutton(reminders_frame, text="1 hora antes", 
                       variable=self.reminder_1h).grid(row=1, column=1, sticky=tk.W)
        
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(15, 0))
        
        self.add_button = ttk.Button(
            button_frame, 
            text="➕ Adicionar Tarefa", 
            command=self.add_task,
            style='Accent.TButton',
            width=20
        )
        self.add_button.grid(row=0, column=0, padx=2)
        
        self.update_button = ttk.Button(
            button_frame, 
            text="✅ Atualizar Tarefa", 
            command=self.update_task,
            style='Accent.TButton',
            width=20
        )
        
        self.cancel_button = ttk.Button(
            button_frame, 
            text="❌ Cancelar Edição", 
            command=self.cancel_edit,
            width=20
        )
        
        list_frame = ttk.LabelFrame(tasks_frame, text="Tarefas Agendadas", padding="10")
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        columns = ("ID", "Tarefa", "Data/Hora", "Lembretes", "Status")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)
        
        self.tree.heading("ID", text="ID", anchor=tk.CENTER)
        self.tree.heading("Tarefa", text="Tarefa", anchor=tk.W)
        self.tree.heading("Data/Hora", text="Data/Hora", anchor=tk.CENTER)
        self.tree.heading("Lembretes", text="Lembretes", anchor=tk.CENTER)
        self.tree.heading("Status", text="Status", anchor=tk.CENTER)
        
        self.tree.column("ID", width=50, anchor=tk.CENTER, minwidth=40)
        self.tree.column("Tarefa", width=400, anchor=tk.W, minwidth=200)
        self.tree.column("Data/Hora", width=120, anchor=tk.CENTER, minwidth=100)
        self.tree.column("Lembretes", width=150, anchor=tk.CENTER, minwidth=120)
        self.tree.column("Status", width=100, anchor=tk.CENTER, minwidth=80)
        
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        vsb.grid(row=0, column=1, sticky=(tk.N, tk.S))
        hsb.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        action_frame = ttk.Frame(list_frame)
        action_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(
            action_frame,
            text="✏️ Editar",
            command=self.edit_selected_task,
            width=15
        ).grid(row=0, column=0, padx=2)
        
        ttk.Button(
            action_frame,
            text="🗑️ Excluir",
            command=self.remove_selected_task,
            width=15
        ).grid(row=0, column=1, padx=2)
        
        ttk.Button(
            action_frame,
            text="✅ Concluir",
            command=self.mark_as_completed,
            width=15
        ).grid(row=0, column=2, padx=2)
        
        ttk.Button(
            action_frame,
            text="🗑️ Limpar Concluídas",
            command=self.clear_completed_tasks,
            width=25
        ).grid(row=0, column=3, padx=2)
        
        self.tree.bind('<<TreeviewSelect>>', self.on_task_select)
        self.tree.bind('<Double-Button-1>', lambda e: self.edit_selected_task())

    def setup_settings_tab(self):
        """Configura a aba de configurações"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="⚙️ Configurações")
        
        settings_frame.columnconfigure(0, weight=1)
        
        general_frame = ttk.LabelFrame(settings_frame, text="Configurações Gerais", padding="15")
        general_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=10, pady=10)
        
        row = 0
        
        # Iniciar com Windows
        if WINSHELL_AVAILABLE:
            self.start_with_windows_var = tk.BooleanVar(value=self.config.get("start_with_windows", True))
            ttk.Checkbutton(
                general_frame,
                text="Iniciar automaticamente com o Windows",
                variable=self.start_with_windows_var
            ).grid(row=row, column=0, sticky=tk.W, pady=5)
            row += 1
        
        # Minimizar para bandeja
        self.minimize_to_tray_var = tk.BooleanVar(value=self.config.get("minimize_to_tray", True))
        ttk.Checkbutton(
            general_frame,
            text="Minimizar para bandeja do sistema ao fechar",
            variable=self.minimize_to_tray_var
        ).grid(row=row, column=0, sticky=tk.W, pady=5)
        row += 1
        
        # Mostrar ícone na bandeja
        if PYSTRAY_AVAILABLE and PILLOW_AVAILABLE:
            self.show_tray_icon_var = tk.BooleanVar(value=self.config.get("show_tray_icon", True))
            ttk.Checkbutton(
                general_frame,
                text="Mostrar ícone na bandeja do sistema",
                variable=self.show_tray_icon_var
            ).grid(row=row, column=0, sticky=tk.W, pady=5)
            row += 1
        
        # Notificação ao minimizar
        if PLYER_AVAILABLE:
            self.show_notification_var = tk.BooleanVar(value=self.config.get("show_notification_on_minimize", True))
            ttk.Checkbutton(
                general_frame,
                text="Mostrar notificação ao minimizar para bandeja",
                variable=self.show_notification_var
            ).grid(row=row, column=0, sticky=tk.W, pady=5)
            row += 1
        
        # Som de notificação
        if PLYER_AVAILABLE:
            self.notification_sound_var = tk.BooleanVar(value=self.config.get("notification_sound", True))
            ttk.Checkbutton(
                general_frame,
                text="Tocar som nas notificações",
                variable=self.notification_sound_var
            ).grid(row=row, column=0, sticky=tk.W, pady=5)
            row += 1
        
        # Duração da notificação
        if PLYER_AVAILABLE:
            ttk.Label(general_frame, text="Duração da notificação (segundos):").grid(row=row, column=0, sticky=tk.W, pady=5)
            
            duration_frame = ttk.Frame(general_frame)
            duration_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
            
            self.notification_duration_var = tk.IntVar(value=self.config.get("notification_duration", 15))
            duration_spinbox = ttk.Spinbox(
                duration_frame,
                from_=5,
                to=60,
                increment=5,
                textvariable=self.notification_duration_var,
                width=10
            )
            duration_spinbox.grid(row=0, column=0)
            row += 1
        
        # Intervalo de verificação
        ttk.Label(general_frame, text="Verificar tarefas a cada (minutos):").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        interval_frame = ttk.Frame(general_frame)
        interval_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        self.check_interval_var = tk.IntVar(value=self.config.get("check_interval", 60))
        interval_spinbox = ttk.Spinbox(
            interval_frame,
            from_=1,
            to=1440,
            increment=5,
            textvariable=self.check_interval_var,
            width=10
        )
        interval_spinbox.grid(row=0, column=0)
        row += 1
        
        # Tema
        ttk.Label(general_frame, text="Tema:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        self.theme_var = tk.StringVar(value=self.config.get("theme", "light"))
        theme_combo = ttk.Combobox(
            general_frame,
            textvariable=self.theme_var,
            values=["light", "dark"],
            state="readonly",
            width=10
        )
        theme_combo.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1
        
        # Botões de ação
        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=1, column=0, pady=20)
        
        ttk.Button(
            button_frame,
            text="💾 Salvar Configurações",
            command=self.save_all_settings,
            style='Accent.TButton',
            width=25
        ).grid(row=0, column=0, padx=5)
        
        ttk.Button(
            button_frame,
            text="🔄 Restaurar Padrões",
            command=self.restore_default_settings,
            width=20
        ).grid(row=0, column=1, padx=5)
        
        ttk.Button(
            button_frame,
            text="🗑️ Limpar Todos os Dados",
            command=self.clear_all_data,
            width=30
        ).grid(row=0, column=2, padx=5)

    def setup_status_bar(self):
        """Configura a barra de status"""
        self.status_var = tk.StringVar(value="👌 Pronto")
        status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN,
            padding=(10, 5)
        )
        status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))

    def set_current_time(self):
        """Define a data e hora atuais"""
        now = datetime.now()
        
        # Definir data
        if TKCALENDAR_AVAILABLE:
            self.date_entry.set_date(now)
        else:
            self.date_entry.delete(0, tk.END)
            self.date_entry.insert(0, now.strftime("%d/%m/%Y"))
        
        # Definir hora e minuto
        self.time_spinbox_hour.set(now.strftime("%H"))
        self.time_spinbox_minute.set(now.strftime("%M"))

    def validate_datetime(self, date_str, hour, minute):
        """Valida a data e hora inseridas"""
        try:
            if TKCALENDAR_AVAILABLE:
                selected_date = self.date_entry.get_date()
                date_str = selected_date.strftime("%d/%m/%Y")
            
            hour_str = f"{int(hour):02d}"
            minute_str = f"{int(minute):02d}"
            
            datetime_str = f"{date_str} {hour_str}:{minute_str}"
            datetime.strptime(datetime_str, "%d/%m/%Y %H:%M")
            return True
        except ValueError as e:
            print(f"Erro na validação: {e}")
            return False

    def on_task_select(self, event=None):
        """Trata a seleção de uma tarefa na tabela"""
        selected = self.tree.selection()
        if selected:
            pass

    def toggle_edit_buttons(self, editing=True):
        """Alterna entre os botões Adicionar/Atualizar/Cancelar"""
        if editing:

            self.add_button.grid_remove()

            self.update_button.grid(row=0, column=0, padx=2)
            self.cancel_button.grid(row=0, column=1, padx=2)
        else:

            self.update_button.grid_remove()
            self.cancel_button.grid_remove()

            self.add_button.grid(row=0, column=0, padx=2)

    def add_task(self):
        """Adiciona uma nova tarefa"""
        task_text = self.task_entry.get().strip()
        
        if TKCALENDAR_AVAILABLE:
            selected_date = self.date_entry.get_date()
            date_str = selected_date.strftime("%d/%m/%Y")
        else:
            date_str = self.date_entry.get().strip()
        
        hour = self.time_spinbox_hour.get().strip()
        minute = self.time_spinbox_minute.get().strip()
        
        if not task_text:
            messagebox.showwarning("Aviso", "Por favor, insira uma descrição para a tarefa!")
            self.task_entry.focus()
            return
        
        if not hour or not minute:
            messagebox.showwarning("Aviso", "Por favor, insira hora e minuto válidos!")
            self.time_spinbox_hour.focus()
            return
        
        if not self.validate_datetime(date_str, hour, minute):
            messagebox.showerror(
                "Erro", 
                "Formato de data/hora inválido!\n\n"
                "Use: DD/MM/AAAA HH:MM\n"
                "Exemplo: 25/12/2024 14:30"
            )
            self.date_entry.focus()
            return
        
        # Verificar se está editando
        if self.editing_task_id:
            self.update_task()
            return
        
        # Formatar hora e minuto
        hour_str = f"{int(hour):02d}"
        minute_str = f"{int(minute):02d}"
        
        # Adicionar nova tarefa
        task_datetime = datetime.strptime(f"{date_str} {hour_str}:{minute_str}", "%d/%m/%Y %H:%M")
        now = datetime.now()
        
        task = {
            "id": max([t['id'] for t in self.tasks], default=0) + 1,
            "task": task_text,
            "datetime": task_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            "reminder_5min": self.reminder_5min.get(),
            "reminder_10min": self.reminder_10min.get(),
            "reminder_30min": self.reminder_30min.get(),
            "reminder_1h": self.reminder_1h.get(),
            "status": "Pendente",
            "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
            "is_overdue": task_datetime < now
        }
        
        # Adicionar à lista
        self.tasks.append(task)
        
        # Salvar no arquivo
        self.save_tasks()
        
        # Atualizar interface
        self.load_tasks_to_table()
        
        # Agendar notificações
        self.schedule_task_notifications(task)
        
        # Limpar campos
        self.task_entry.delete(0, tk.END)
        
        # Resetar para próxima hora
        next_hour = (datetime.now() + timedelta(hours=1))
        if TKCALENDAR_AVAILABLE:
            self.date_entry.set_date(next_hour)
        
        self.time_spinbox_hour.set(next_hour.strftime("%H"))
        self.time_spinbox_minute.set("00")
        
        # Resetar lembretes
        self.reminder_5min.set(False)
        self.reminder_10min.set(False)
        self.reminder_30min.set(False)
        self.reminder_1h.set(False)
        
        # Atualizar status
        self.status_var.set(f"✅ Tarefa '{task_text[:30]}...' adicionada")
        
        # Voltar o foco para a descrição
        self.task_entry.focus()

    def update_task(self):
        """Atualiza uma tarefa existente"""
        task_text = self.task_entry.get().strip()
        
        if TKCALENDAR_AVAILABLE:
            selected_date = self.date_entry.get_date()
            date_str = selected_date.strftime("%d/%m/%Y")
        else:
            date_str = self.date_entry.get().strip()
        
        hour = self.time_spinbox_hour.get().strip()
        minute = self.time_spinbox_minute.get().strip()
        
        if not task_text:
            messagebox.showwarning("Aviso", "Por favor, insira uma descrição para a tarefa!")
            self.task_entry.focus()
            return
        
        if not hour or not minute:
            messagebox.showwarning("Aviso", "Por favor, insira hora e minuto válidos!")
            self.time_spinbox_hour.focus()
            return
        
        if not self.validate_datetime(date_str, hour, minute):
            messagebox.showerror(
                "Erro", 
                "Formato de data/hora inválido!\n\n"
                "Use: DD/MM/AAAA HH:MM\n"
                "Exemplo: 25/12/2024 14:30"
            )
            self.date_entry.focus()
            return
        
        if not self.editing_task_id:
            messagebox.showwarning("Aviso", "Nenhuma tarefa está sendo editada!")
            return
        
        hour_str = f"{int(hour):02d}"
        minute_str = f"{int(minute):02d}"
        
        task_datetime = datetime.strptime(f"{date_str} {hour_str}:{minute_str}", "%d/%m/%Y %H:%M")
        now = datetime.now()
        
        for task in self.tasks:
            if task['id'] == self.editing_task_id:
                task['task'] = task_text
                task['datetime'] = task_datetime.strftime("%Y-%m-%d %H:%M:%S")
                task['reminder_5min'] = self.reminder_5min.get()
                task['reminder_10min'] = self.reminder_10min.get()
                task['reminder_30min'] = self.reminder_30min.get()
                task['reminder_1h'] = self.reminder_1h.get()
                task['status'] = "Pendente"
                task['is_overdue'] = task_datetime < now
                
                self.save_tasks()
                self.load_tasks_to_table()
                
                self.reschedule_all_tasks()
                
                self.task_entry.delete(0, tk.END)
                self.reminder_5min.set(False)
                self.reminder_10min.set(False)
                self.reminder_30min.set(False)
                self.reminder_1h.set(False)
                
                self.editing_task_id = None
                self.toggle_edit_buttons(editing=False)
                
                self.status_var.set(f"✏️ Tarefa atualizada com sucesso")
                
                self.task_entry.focus()
                break

    def cancel_edit(self):
        """Cancela a edição atual e volta para o modo adicionar"""
        self.editing_task_id = None
        self.toggle_edit_buttons(editing=False)
        
        self.task_entry.delete(0, tk.END)
        
        next_hour = datetime.now() + timedelta(hours=1)
        if TKCALENDAR_AVAILABLE:
            self.date_entry.set_date(next_hour)
        
        self.time_spinbox_hour.set(next_hour.strftime("%H"))
        self.time_spinbox_minute.set("00")
        
        self.reminder_5min.set(False)
        self.reminder_10min.set(False)
        self.reminder_30min.set(False)
        self.reminder_1h.set(False)
        
        self.task_entry.focus()
        
        self.status_var.set("Edição cancelada")

    def edit_selected_task(self):
        """Carrega a tarefa selecionada para edição"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Por favor, selecione uma tarefa para editar!")
            return
        
        item = self.tree.item(selected[0])
        task_id = item['values'][0]
        
        for task in self.tasks:
            if task['id'] == task_id:
                # Carregar dados nos campos
                self.task_entry.delete(0, tk.END)
                self.task_entry.insert(0, task['task'])
                
                task_datetime = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
                
                if TKCALENDAR_AVAILABLE:
                    self.date_entry.set_date(task_datetime)
                else:
                    self.date_entry.delete(0, tk.END)
                    self.date_entry.insert(0, task_datetime.strftime("%d/%m/%Y"))
                
                self.time_spinbox_hour.set(task_datetime.strftime("%H"))
                self.time_spinbox_minute.set(task_datetime.strftime("%M"))
                
                self.reminder_5min.set(task.get('reminder_5min', False))
                self.reminder_10min.set(task.get('reminder_10min', False))
                self.reminder_30min.set(task.get('reminder_30min', False))
                self.reminder_1h.set(task.get('reminder_1h', False))
                
                self.editing_task_id = task_id
                self.toggle_edit_buttons(editing=True)
                
                self.status_var.set(f"✏️ Editando tarefa ID {task_id} - Clique em 'Atualizar Tarefa' para confirmar")
                self.task_entry.focus()
                break

    def remove_selected_task(self):
        """Exclui a tarefa selecionada"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Por favor, selecione uma tarefa para excluir!")
            return
        
        item = self.tree.item(selected[0])
        task_text = item['values'][1]
        task_id = item['values'][0]
        
        if messagebox.askyesno("Confirmar Exclusão", 
                              f"Deseja realmente excluir a tarefa?\n\n"
                              f"'{task_text[:50]}...'"):
            # Remover da lista
            self.tasks = [t for t in self.tasks if t['id'] != task_id]
            
            # Salvar alterações
            self.save_tasks()
            
            # Atualizar interface
            self.load_tasks_to_table()
            
            # Reagendar notificações
            self.reschedule_all_tasks()

            if self.editing_task_id == task_id:
                self.task_entry.delete(0, tk.END)
                self.reminder_5min.set(False)
                self.reminder_10min.set(False)
                self.reminder_30min.set(False)
                self.reminder_1h.set(False)
                self.editing_task_id = None
                self.toggle_edit_buttons(editing=False)
            
            self.status_var.set(f"🗑️ Tarefa excluída")

    def mark_as_completed(self):
        """Marca a tarefa selecionada como concluída"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Aviso", "Por favor, selecione uma tarefa para marcar como concluída!")
            return
        
        item = self.tree.item(selected[0])
        task_id = item['values'][0]
        
        for task in self.tasks:
            if task['id'] == task_id:
                task['status'] = 'Concluída'
                task['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        
        self.save_tasks()
        self.load_tasks_to_table()
        
        self.reschedule_all_tasks()
        
        self.status_var.set("✅ Tarefa marcada como concluída")

    def clear_completed_tasks(self):
        """Remove todas as tarefas concluídas"""
        completed_tasks = [t for t in self.tasks if t.get('status') == 'Concluída']
        
        if not completed_tasks:
            messagebox.showinfo("Informação", "Não há tarefas concluídas para remover.")
            return
        
        if messagebox.askyesno("Confirmar", 
                              f"Deseja remover {len(completed_tasks)} tarefa(s) concluída(s)?"):

            self.tasks = [t for t in self.tasks if t.get('status') != 'Concluída']
            
            self.save_tasks()
            self.load_tasks_to_table()
            
            # Reagendar notificações
            self.reschedule_all_tasks()
            
            self.status_var.set(f"🧹 {len(completed_tasks)} tarefa(s) concluída(s) removida(s)")

    def load_tasks_to_table(self):
        """Carrega as tarefas na tabela com cores por status"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Ordenar tarefas
        pending_tasks = [t for t in self.tasks if t.get('status') == 'Pendente']
        completed_tasks = [t for t in self.tasks if t.get('status') == 'Concluída']
        
        # Ordenar pendentes por data
        pending_tasks.sort(key=lambda x: x['datetime'])
        
        # Combinar listas
        sorted_tasks = pending_tasks + completed_tasks
        
        # Adicionar tarefas à tabela
        for task in sorted_tasks:
            task_datetime = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            
            reminders = []
            if task.get('reminder_5min'):
                reminders.append("5min")
            if task.get('reminder_10min'):
                reminders.append("10min")
            if task.get('reminder_30min'):
                reminders.append("30min")
            if task.get('reminder_1h'):
                reminders.append("1h")
            reminders_text = ", ".join(reminders) if reminders else "Nenhum"
            
            # Verificar se a tarefa está atrasada
            status = task.get('status', 'Pendente')
            is_overdue = False
            
            if status == 'Pendente':
                if task_datetime < now:
                    status = "Atrasada"
                    task['status'] = 'Atrasada'
                    task['is_overdue'] = True
                    is_overdue = True
                else:
                    task['is_overdue'] = False
            
            # Determinar tag para cor
            if status == 'Concluída':
                tag = 'completed'
            elif is_overdue:
                tag = 'overdue'
            else:
                tag = 'pending'
            
            # Adicionar à tabela
            item_id = self.tree.insert("", tk.END, values=(
                task['id'],
                task['task'],
                task_datetime.strftime("%d/%m/%Y %H:%M"),
                reminders_text,
                status
            ), tags=(tag,))
        
        # Configurar cores das tags
        self.tree.tag_configure('overdue', foreground='red', font=('Segoe UI', 9, 'bold'))
        self.tree.tag_configure('pending', foreground='#6c757d')
        self.tree.tag_configure('completed', foreground='#28a745')

    def save_tasks(self):
        """Salva as tarefas no arquivo tasks.json"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar tarefas: {e}")
            return False

    def load_tasks(self):
        """Carrega as tarefas do arquivo tasks.json"""
        if os.path.exists(self.tasks_file):
            try:
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    tasks = json.load(f)
                    
                    for task in tasks:
                        if 'is_overdue' not in task:
                            task_datetime = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
                            task['is_overdue'] = task_datetime < datetime.now()
                        if 'reminder_30min' not in task:
                            task['reminder_30min'] = False
                        if 'reminder_1h' not in task:
                            task['reminder_1h'] = False
                    
                    self.tasks = tasks
                    return tasks
            except Exception as e:
                print(f"Erro ao carregar tarefas: {e}")
                self.tasks = []
                return []
        self.tasks = []
        return []

    def schedule_task_notifications(self, task):
        """Agenda as notificações para uma tarefa"""
        try:
            if task.get('status') != 'Pendente':
                return
                
            task_time = datetime.strptime(task['datetime'], "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            
            if task_time > now:
                def main_notification():
                    self.send_main_notification(task['id'], task['task'])
                
                wait_seconds = (task_time - now).total_seconds()
                
                if wait_seconds > 0:
                    timer = threading.Timer(wait_seconds, main_notification)
                    timer.daemon = True
                    timer.start()
                    self.active_timers.append(timer)
                
                def create_reminder_notification(minutes):
                    def reminder():
                        self.send_reminder_notification(task['id'], task['task'], f"{minutes} minutos")
                    return reminder
                
                reminders = [
                    (5, task.get('reminder_5min')),
                    (10, task.get('reminder_10min')),
                    (30, task.get('reminder_30min')),
                    (60, task.get('reminder_1h'))
                ]
                
                for minutes, enabled in reminders:
                    if enabled:
                        reminder_time = task_time - timedelta(minutes=minutes)
                        if reminder_time > now:
                            wait_seconds = (reminder_time - now).total_seconds()
                            if wait_seconds > 0:
                                timer = threading.Timer(wait_seconds, create_reminder_notification(minutes))
                                timer.daemon = True
                                timer.start()
                                self.active_timers.append(timer)
                        
        except Exception as e:
            print(f"Erro ao agendar notificações para tarefa {task.get('id')}: {e}")

    def send_main_notification(self, task_id, task_text):
        """Envia notificação principal"""
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title="📢 Task Reminder",
                    message=f"⏰ HORA DA TAREFA!\n\n{task_text}",
                    timeout=self.config.get("notification_duration", 15),
                    toast=True,
                    app_name="Task Reminder"
                )
            except:
                pass
        
        # Mostrar janela de notificação personalizada
        self.show_notification_window(task_text, None)
        
        # Atualizar status da tarefa
        for task in self.tasks:
            if task['id'] == task_id:
                task['status'] = 'Concluída'
                task['completed_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                break
        
        # Salvar e atualizar na thread principal
        self.save_tasks()
        self.root.after(0, self.load_tasks_to_table)

    def send_reminder_notification(self, task_id, task_text, minutes):
        """Envia notificação antecipada"""
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title="🔔 Task Reminder",
                    message=f"⏰ Lembrete ({minutes} antes):\n\n{task_text}",
                    timeout=10,
                    toast=True,
                    app_name="Task Reminder"
                )
            except:
                pass
        
        # Mostrar janela de notificação personalizada
        self.show_notification_window(task_text, f"Lembrete ({minutes} antes)")

    def show_notification_window(self, task_text, reminder_text):
        """Mostra janela de notificação personalizada"""
        def create_window():
            try:
                notif_window = NotificationWindow(task_text, reminder_text)
                self.notification_windows.append(notif_window)
                notif_window.show()
                if notif_window in self.notification_windows:
                    self.notification_windows.remove(notif_window)
            except Exception as e:
                print(f"Erro ao criar janela de notificação: {e}")
        
        # Executar em thread separada
        threading.Thread(target=create_window, daemon=True).start()

    def reschedule_all_tasks(self):
        """Reagenda todas as notificações"""
        for timer in self.active_timers:
            try:
                timer.cancel()
            except:
                pass
        self.active_timers.clear()
        
        if SCHEDULE_AVAILABLE:
            schedule.clear()
        
        for task in self.tasks:
            if task.get('status') == 'Pendente':
                self.schedule_task_notifications(task)

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
                        needs_update = True
            
            if needs_update:
                self.root.after(0, self.load_tasks_to_table)

    # Métodos de configurações
    def save_all_settings(self):
        """Salva todas as configurações"""
        config_updates = {
            'minimize_to_tray': self.minimize_to_tray_var.get(),
            'check_interval': self.check_interval_var.get(),
            'theme': self.theme_var.get()
        }
        
        if hasattr(self, 'start_with_windows_var'):
            config_updates['start_with_windows'] = self.start_with_windows_var.get()
            if WINSHELL_AVAILABLE:
                if config_updates['start_with_windows']:
                    self.setup_autostart()
                else:
                    self.remove_autostart()
        
        if hasattr(self, 'show_tray_icon_var'):
            config_updates['show_tray_icon'] = self.show_tray_icon_var.get()
            # configuração do ícone da bandeja
            if PYSTRAY_AVAILABLE and PILLOW_AVAILABLE:
                if self.tray_icon:
                    self.tray_icon.stop()
                    self.tray_icon = None
                if config_updates['show_tray_icon']:
                    self.setup_tray_icon()
        
        if hasattr(self, 'show_notification_var'):
            config_updates['show_notification_on_minimize'] = self.show_notification_var.get()
        
        if hasattr(self, 'notification_sound_var'):
            config_updates['notification_sound'] = self.notification_sound_var.get()
        
        if hasattr(self, 'notification_duration_var'):
            duration = self.notification_duration_var.get()
            if 5 <= duration <= 60:
                config_updates['notification_duration'] = duration
            else:
                config_updates['notification_duration'] = self.config.get('notification_duration', 15)
                self.notification_duration_var.set(config_updates['notification_duration'])
        
        if hasattr(self, 'check_interval_var'):
            interval = self.check_interval_var.get()
            if 1 <= interval <= 1440:
                config_updates['check_interval'] = interval
            else:
                config_updates['check_interval'] = self.config.get('check_interval', 60)
                self.check_interval_var.set(config_updates['check_interval'])
        
        if hasattr(self, 'theme_var'):
            config_updates['theme'] = self.theme_var.get()
            if config_updates['theme'] != self.config.get('theme', 'light'):
                messagebox.showinfo("Tema", "O tema será aplicado na próxima inicialização do aplicativo.")
        
        self.config.update(config_updates)
        
        # Salvar no arquivo
        if self.save_config():
            if not self.is_quitting:
                messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
                self.status_var.set("✅ Configurações salvas")
        else:
            if not self.is_quitting:
                messagebox.showerror("Erro", "Erro ao salvar configurações.")

    def restore_default_settings(self):
        """Restaura as configurações padrão"""
        if messagebox.askyesno("Confirmar", 
                            "Deseja restaurar todas as configurações para os valores padrão?\n\n"
                            "Esta ação não pode ser desfeita."):
            default_config = {
                "start_with_windows": True,
                "minimize_to_tray": True,
                "show_tray_icon": True,
                "show_notification_on_minimize": True,
                "notification_sound": True,
                "notification_duration": 15,
                "check_interval": 60,
                "theme": "light"
            }
            
            self.config = default_config
            
            # Atualizar variáveis de interface
            if hasattr(self, 'start_with_windows_var'):
                self.start_with_windows_var.set(True)
            if hasattr(self, 'minimize_to_tray_var'):
                self.minimize_to_tray_var.set(True)
            if hasattr(self, 'show_tray_icon_var'):
                self.show_tray_icon_var.set(True)
            if hasattr(self, 'show_notification_var'):
                self.show_notification_var.set(True)
            if hasattr(self, 'notification_sound_var'):
                self.notification_sound_var.set(True)
            if hasattr(self, 'notification_duration_var'):
                self.notification_duration_var.set(15)
            if hasattr(self, 'check_interval_var'):
                self.check_interval_var.set(60)
            if hasattr(self, 'theme_var'):
                self.theme_var.set("light")
            
            # Aplicar mudanças imediatamente para restaurar padrões
            if WINSHELL_AVAILABLE:
                self.setup_autostart()
            
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None
            if PYSTRAY_AVAILABLE and PILLOW_AVAILABLE:
                self.setup_tray_icon()
            
            self.save_config(default_config)
            
            messagebox.showinfo("Sucesso", "Configurações padrão restauradas!")
            self.status_var.set("🔄 Configurações restauradas")

    def clear_all_data(self):
        """Limpa todos os dados do aplicativo"""
        if messagebox.askyesno("⚠️ Confirmação EXTREMA", 
                              "ATENÇÃO: Esta ação irá:\n\n"
                              "1. Excluir TODAS as tarefas agendadas\n"
                              "2. Restaurar configurações padrão\n"
                              "3. Remover o aplicativo do início automático\n\n"
                              "Esta ação NÃO pode ser desfeita!\n\n"
                              "Deseja continuar?"):
            try:
                # Limpar tarefas
                self.tasks = []
                if os.path.exists(self.tasks_file):
                    os.remove(self.tasks_file)
                
                # Restaurar configurações padrão
                self.restore_default_settings()
                
                # Remover autostart
                if WINSHELL_AVAILABLE:
                    self.remove_autostart()
                
                # Atualizar interface
                self.load_tasks_to_table()
                
                # Cancelar todos os timers
                self.reschedule_all_tasks()
                
                messagebox.showinfo("Sucesso", "Todos os dados foram limpos com sucesso!")
                self.status_var.set("🧹 Todos os dados foram limpos")
                
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao limpar dados: {e}")

    def open_settings(self):
        """Abre a janela de configurações"""
        self.notebook.select(1)
        self.show_window()

    def quit_app_silent(self):
        """Encerra o aplicativo silenciosamente"""
        self.is_quitting = True
        self.quit_app()

    def quit_app(self):
        """Encerra o aplicativo corretamente"""
        self.scheduler_running = False
        
        for timer in self.active_timers:
            try:
                timer.cancel()
            except:
                pass
        
        for window in self.notification_windows[:]:
            try:
                window.window.destroy()
            except:
                pass
        
        # Salvar tudo antes de sair
        try:
            self.save_tasks()
            self.save_config()
        except:
            pass
        
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
        
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass
        
        sys.exit(0)

def main():
    """Função principal"""
    import ctypes
    mutex_name = "Global\\TaskReminderApp"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    
    if last_error == 183:  # ERROR_ALREADY_EXISTS
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
    start_minimized = "--minimized" in sys.argv
    
    # Iniciar aplicação
    main()