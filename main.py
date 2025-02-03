import websocket
import json
import time
import logging
import os
from datetime import datetime
import threading
from colorama import init
import random
import customtkinter as ctk




init(autoreset=True)



BASE_DIR = os.path.dirname(os.path.abspath(__file__))


log_dir = os.path.join(BASE_DIR, "logs")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

class GUIHandler(logging.Handler):
    def __init__(self, gui_callback):
        super().__init__()
        self.gui_callback = gui_callback

    def emit(self, record):
        log_message = self.format(record)
        self.gui_callback(log_message)

class TeneoConnection:
    def __init__(self, access_token, proxy=None, proxy_auth=None):
        self.access_token = access_token
        self.proxy = proxy
        self.proxy_auth = proxy_auth
        self.ws = None
        self.is_connected = False
        self.last_ping_sent = 0
        self.stop_flag = False
        self.points = 0
        self.points_today = 0
        self.last_update = None
        self.connection_time = None
        self._ping_started = False
        self.bytes_sent = 0
        self.bytes_received = 0
        self.log_prefix = f"[Token: {access_token[:8]}...]"

        
        self.desktop_user_agents = [
            
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Edge/120.0.0.0",
            
            
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            
            
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
            
            
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 YaBrowser/24.1.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 YaBrowser/24.1.0.0 Safari/537.36",
            
            
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
        ]

        
        self.on_status_change = None
        self.on_points_update = None
        self.on_error = None

    def connect(self):
        
        ws_url = f"wss://secure.ws.teneo.pro/websocket?accessToken={self.access_token}&version=v0.2"
        
        websocket.enableTrace(False)
        
        
        random_user_agent = random.choice(self.desktop_user_agents)
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            header={
                'Host': 'secure.ws.teneo.pro',
                'Upgrade': 'websocket',
                'Connection': 'Upgrade',
                'Origin': 'chrome-extension://emcclcoaglgcpoognfiggmhnhgabppkm',
                'User-Agent': random_user_agent,
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'ru,en;q=0.9,no;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
                'Sec-WebSocket-Version': '13'
            },
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        ws_thread = threading.Thread(target=self.ws.run_forever, 
                                   kwargs={
                                       'ping_interval': None,
                                       'ping_timeout': None,
                                       'proxy_type': 'http' if self.proxy else None,
                                       'http_proxy_host': self.proxy.split(':')[0] if self.proxy else None,
                                       'http_proxy_port': int(self.proxy.split(':')[1]) if self.proxy else None,
                                       'http_proxy_auth': self.proxy_auth
                                   })
        ws_thread.daemon = True
        ws_thread.start()
        return ws_thread

    def on_open(self, ws):
        
        self.connection_time = datetime.now()
        self.last_update = datetime.now()
        self.is_connected = True
        
    def on_message(self, ws, message):
        
        try:
            self.bytes_received += len(message.encode('utf-8'))
            data = json.loads(message)
            current_time = datetime.now()
            self.last_update = current_time
            
           
            if "message" in data and data["message"] == "Connected successfully":
                self.is_connected = True
                if "pointsTotal" in data:
                    self.points = data["pointsTotal"]
                    self.points_today = data.get("pointsToday", 0)
                    if not self._ping_started:
                        self._ping_started = True
                        self.start_ping()
                    
                    if self.on_points_update:
                        self.on_points_update(self)

            # Обновление баланса
            elif "pointsTotal" in data:
                old_points = self.points
                old_points_today = self.points_today
                self.points = data["pointsTotal"]
                self.points_today = data.get("pointsToday", 0)
                
                if self.points != old_points or self.points_today != old_points_today:
                    
                    if self.on_points_update:
                        self.on_points_update(self)

        except Exception as e:
            if self.on_error:
                self.on_error(str(e))

    def on_error(self, ws, error):
        
        self.is_connected = False
        logging.error(f"WebSocket error: {str(error)}")
        if self.on_status_change:
            self.on_status_change(self)
        if self.on_error:
            self.on_error(str(error))

    def on_close(self, ws, close_status_code, close_msg):
        
        self.is_connected = False
        if self.on_status_change:
            self.on_status_change(self)

    def start_ping(self):
      
        def ping_thread():
            while not self.stop_flag and self.is_connected:
                try:
                    ping_message = json.dumps({"type": "PING"})
                    self.ws.send(ping_message)
                    self.bytes_sent += len(ping_message.encode('utf-8'))
                    self.last_ping_sent = time.time()
                    time.sleep(10.0)
                except Exception as e:
                    if not self.is_connected:
                        break
                    logging.error(f"⚠️ PING error: {str(e)}")
                    time.sleep(1)

        thread = threading.Thread(target=ping_thread)
        thread.daemon = True
        thread.start()

    def stop(self):
       
        self.stop_flag = True
        if self.ws and hasattr(self.ws, 'sock') and self.ws.sock:
            try:
                self.ws.close()
            except Exception as e:
                logging.debug(f"Error during WebSocket closure: {str(e)}")

def load_tokens(filename="accounts.txt"):
  
    tokens = []
    try:
        file_path = os.path.join(BASE_DIR, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            tokens = [line.strip() for line in f if line.strip()]
        logging.info(f"✅ Loaded tokens: {len(tokens)}")
        return tokens
    except FileNotFoundError:
        logging.error(f"❌ File {filename} not found")
        return []
    except Exception as e:
        logging.error(f"⚠️ Error reading file {filename}: {str(e)}")
        return []

def load_proxies(filename="proxies.txt"):

    proxies = []
    try:
        file_path = os.path.join(BASE_DIR, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(':')
                if len(parts) == 4:
                    host, port, username, password = parts
                    proxies.append({
                        'host': host,
                        'port': port,
                        'auth': (username, password)
                    })
                elif len(parts) == 2:
                    host, port = parts
                    proxies.append({
                        'host': host,
                        'port': port,
                        'auth': None
                    })
        logging.info(f"✅ Loaded proxies: {len(proxies)}")
        return proxies
    except FileNotFoundError:
        logging.info(f"ℹ️ Proxies file not found, working without proxies")
        return []
    except Exception as e:
        logging.error(f"⚠️ Error reading proxies file: {str(e)}")
        return []

def clear_console():

    os.system('cls' if os.name == 'nt' else 'clear')

def format_time_ago(seconds):

    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds/60)}m {int(seconds%60)}s"
    else:
        hours = int(seconds/3600)
        minutes = int((seconds%3600)/60)
        return f"{hours}h {minutes}m"

def format_bytes(bytes_count):

    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024:
            return f"{bytes_count:.2f} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.2f} TB"

class TeneoGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        

        self.title("Teneo Node Manager")
        self.geometry("1400x800")
        

        self.colors = {
            "bg_dark": "#0F0B1A",        # Более темный фон
            "bg_medium": "#161229",      # Средний фон
            "bg_light": "#1E1833",       # Светлый фон
            "accent": "#7C3AED",         # Основной фиолетовый
            "accent_hover": "#8B5CF6",   # Светлый фиолетовый
            "accent_glow": "#6D28D9",    # Фиолетовый для свечения
            "text": "#F8FAFC",           # Яркий текст
            "text_dim": "#94A3B8",       # Приглушенный текст
            "border": "#2D2B3B",         # Границы
            "success": "#10B981",        # Зеленый
            "error": "#EF4444",          # Красный
            "gradient_start": "#13111C",  # Начало градиента
            "gradient_end": "#1A1527"    # Конец градиента
        }
        

        ctk.set_appearance_mode("dark")
        self.configure(fg_color=self.colors["bg_dark"])

        self.gradient_frame = ctk.CTkFrame(
            self,
            fg_color=self.colors["gradient_start"],
            corner_radius=0
        )
        self.gradient_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        self.main_container = ctk.CTkFrame(
            self,
            fg_color=self.colors["bg_medium"],
            corner_radius=15,
            border_width=1,
            border_color=self.colors["border"]
        )
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.create_left_sidebar()
        
        self.content_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_container.pack(side="left", fill="both", expand=True)

        self.create_header()
        self.create_main_area()
        self.create_footer()

        self.connections = []
        self.threads = []
        self.is_running = False
        
        self.setup_logging()
        
    def create_left_sidebar(self):

        self.left_sidebar = ctk.CTkFrame(
            self.main_container,
            fg_color=self.colors["bg_light"],
            corner_radius=12,
            width=260,  
            border_width=1,
            border_color=self.colors["border"]
        )
        self.left_sidebar.pack(side="left", fill="y", padx=(10, 20), pady=10)
        

        logo_frame = ctk.CTkFrame(self.left_sidebar, fg_color="transparent")
        logo_frame.pack(pady=(20, 30), padx=20, fill="x")
        
        title_label = ctk.CTkLabel(
            logo_frame,
            text="Teneo Manager",
            font=("Inter", 24, "bold"),
            text_color=self.colors["text"]
        )
        title_label.pack(anchor="w")
        
        version_label = ctk.CTkLabel(
            logo_frame,
            text="v1.0.0",
            font=("Inter", 12),
            text_color=self.colors["text_dim"]
        )
        version_label.pack(anchor="w")
        

        separator = ctk.CTkFrame(
            self.left_sidebar,
            fg_color=self.colors["border"],
            height=1
        )
        separator.pack(fill="x", padx=20, pady=(0, 20))
        

        menu_button_style = {
            "font": ("Inter", 14),
            "fg_color": "transparent",
            "text_color": self.colors["text"],
            "hover_color": self.colors["bg_medium"],
            "anchor": "w",
            "height": 45,
            "corner_radius": 8
        }
        

        menu_container = ctk.CTkFrame(self.left_sidebar, fg_color="transparent")
        menu_container.pack(fill="x", padx=10)

        self.menu_button = ctk.CTkButton(
            menu_container,
            text="🏠   Dashboard",
            command=self.show_dashboard,
            **menu_button_style
        )
        self.menu_button.pack(pady=5, padx=5, fill="x")
        
        self.files_button = ctk.CTkButton(
            menu_container,
            text="📁   Files",
            command=self.show_files,
            **menu_button_style
        )
        self.files_button.pack(pady=5, padx=5, fill="x")

        self.files_frame = ctk.CTkFrame(
            self.left_sidebar,
            fg_color=self.colors["bg_medium"],
            corner_radius=12
        )
        

        files_title = ctk.CTkLabel(
            self.files_frame,
            text="File Settings",
            font=("Inter", 12, "bold"),
            text_color=self.colors["text_dim"]
        )
        files_title.pack(pady=(15, 10), padx=15, anchor="w")
        

        file_button_style = {
            "font": ("Inter", 13),
            "fg_color": self.colors["bg_dark"],
            "text_color": self.colors["text"],
            "hover_color": self.colors["accent"],
            "height": 36,
            "corner_radius": 8
        }
        

        accounts_container = ctk.CTkFrame(self.files_frame, fg_color="transparent")
        accounts_container.pack(fill="x", padx=15, pady=5)
        
        self.accounts_button = ctk.CTkButton(
            accounts_container,
            text="Select Accounts",
            command=self.select_accounts_file,
            **file_button_style
        )
        self.accounts_button.pack(fill="x")
        
        self.accounts_path = ctk.CTkLabel(
            accounts_container,
            text="accounts.txt",
            font=("Inter", 11),
            text_color=self.colors["text_dim"]
        )
        self.accounts_path.pack(pady=(5, 0), anchor="w")

        proxies_container = ctk.CTkFrame(self.files_frame, fg_color="transparent")
        proxies_container.pack(fill="x", padx=15, pady=(10, 15))
        
        self.proxies_button = ctk.CTkButton(
            proxies_container,
            text="Select Proxies",
            command=self.select_proxies_file,
            **file_button_style
        )
        self.proxies_button.pack(fill="x")
        
        self.proxies_path = ctk.CTkLabel(
            proxies_container,
            text="proxies.txt",
            font=("Inter", 11),
            text_color=self.colors["text_dim"]
        )
        self.proxies_path.pack(pady=(5, 0), anchor="w")

        bottom_frame = ctk.CTkFrame(self.left_sidebar, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", pady=20, padx=15)
        
        separator_bottom = ctk.CTkFrame(
            bottom_frame,
            fg_color=self.colors["border"],
            height=1
        )
        separator_bottom.pack(fill="x", pady=(0, 15))
        
        info_label = ctk.CTkLabel(
            bottom_frame,
            text="Made with ❤️",
            font=("Inter", 12),
            text_color=self.colors["text_dim"]
        )
        info_label.pack()

    def create_header(self):

        self.header = ctk.CTkFrame(
            self.content_container,
            fg_color=self.colors["bg_light"],
            corner_radius=12,
            border_width=1,
            border_color=self.colors["border"]
        )
        self.header.pack(fill="x", pady=(0, 10))
        
        header_container = ctk.CTkFrame(self.header, fg_color="transparent")
        header_container.pack(fill="x", padx=20, pady=15)
        
        stats_container = ctk.CTkFrame(header_container, fg_color="transparent")
        stats_container.pack(side="left", fill="x", expand=True)

        stats_style = {
            "font": ("Inter", 14),
            "fg_color": self.colors["bg_medium"],
            "corner_radius": 8,
            "width": 200,
            "height": 36
        }
        
        active_container = ctk.CTkFrame(stats_container, fg_color="transparent")
        active_container.pack(side="left", padx=(0, 15))
        
        active_title = ctk.CTkLabel(
            active_container,
            text="Active Nodes",
            font=("Inter", 12),
            text_color=self.colors["text_dim"]
        )
        active_title.pack(anchor="w")
        
        self.active_label = ctk.CTkLabel(
            active_container,
            text="0/0",
            **stats_style
        )
        self.active_label.pack()
        
        points_container = ctk.CTkFrame(stats_container, fg_color="transparent")
        points_container.pack(side="left")
        
        points_title = ctk.CTkLabel(
            points_container,
            text="Total Points",
            font=("Inter", 12),
            text_color=self.colors["text_dim"]
        )
        points_title.pack(anchor="w")
        
        self.points_label = ctk.CTkLabel(
            points_container,
            text="0",
            **stats_style
        )
        self.points_label.pack()

        self.start_button = ctk.CTkButton(
            header_container,
            text="Start",
            font=("Inter", 13, "bold"),
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            height=36,
            width=120,
            corner_radius=8,
            border_width=1,
            border_color=self.colors["accent_glow"],
            command=self.start_nodes
        )
        self.start_button.pack(side="right")

    def create_main_area(self):

        self.main_frame = ctk.CTkFrame(
            self.content_container,
            fg_color=self.colors["bg_medium"],
            corner_radius=15,
            border_width=1,
            border_color=self.colors["border"]
        )
        self.main_frame.pack(fill="both", expand=True)
        
        table_container = ctk.CTkScrollableFrame(
            self.main_frame,
            fg_color=self.colors["bg_dark"],
            corner_radius=12,
            border_width=1,
            border_color=self.colors["accent_glow"],
            height=400  
        )
        table_container.pack(fill="both", expand=True, padx=15, pady=15)

        self.table = ctk.CTkLabel(
            table_container,
            text="",
            font=("Cascadia Code", 14),
            text_color=self.colors["text"],
            justify="left",
            anchor="nw"
        )
        self.table.pack(fill="both", expand=True, padx=2, pady=2)

        self.log_text = ctk.CTkTextbox(
            self.main_frame,
            font=("Cascadia Code", 11),
            fg_color=self.colors["bg_dark"],
            text_color=self.colors["text_dim"],
            border_width=0,
            height=120  # Фиксированная высота
        )
        self.log_text.pack(fill="x", expand=False, padx=15, pady=(0, 15))
        self.log_text.configure(state="disabled")

    def create_footer(self):

        self.status_bar = ctk.CTkFrame(self)
        self.status_bar.pack(fill="x", side="bottom", padx=10, pady=5)
        
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="Ready",
            font=("Roboto", 12)
        )
        self.status_label.pack(side="left", padx=10)
        
        self.traffic_label = ctk.CTkLabel(
            self.status_bar,
            text="Traffic: ↑0 B ↓0 B",
            font=("Roboto", 12)
        )
        self.traffic_label.pack(side="right", padx=10)
        
    def start_nodes(self):

        if not self.is_running:
            self.is_running = True
            self.start_button.configure(
                text="Stop",
                fg_color="#EF4444",      
                hover_color="#DC2626",    
                border_color="#B91C1C"    
            )
            

            threading.Thread(target=self.run_nodes, daemon=True).start()
        else:
            self.stop_nodes()
            
    def stop_nodes(self):

        self.is_running = False  
        
        # Обновляем кнопку
        self.start_button.configure(
            text="Start",
            fg_color=self.colors["accent"],
            hover_color=self.colors["accent_hover"],
            border_color=self.colors["accent_glow"]
        )
        

        for connection in self.connections:
            try:
                connection.stop_flag = True  
                if connection.ws:
                    connection.ws.close()
            except Exception as e:
                logging.debug(f"Error stopping connection: {str(e)}")
        

        for thread in self.threads:
            try:
                thread.join(timeout=1.0)  
            except Exception as e:
                logging.debug(f"Error joining thread: {str(e)}")
        

        self.connections.clear()
        self.threads.clear()
        

        self.update_statistics()
        self.update_table()
        self.add_log("All nodes stopped")

    def run_nodes(self):

        tokens = load_tokens()
        proxies = load_proxies()
        
        if not tokens:
            self.show_error("No tokens found!")
            self.stop_nodes()
            return
            

        for i, token in enumerate(tokens):
            if not self.is_running:  
                break
            
            proxy_info = proxies[i % len(proxies)] if proxies else None
            proxy = f"{proxy_info['host']}:{proxy_info['port']}" if proxy_info else None
            proxy_auth = proxy_info['auth'] if proxy_info else None
            
            connection = TeneoConnection(token, proxy, proxy_auth)
            thread = connection.connect()
            
            self.connections.append(connection)
            self.threads.append(thread)
            time.sleep(1)
            

        while self.is_running:
            self.update_statistics()
            self.update_table()
            self.check_connections()
            time.sleep(5)

    def update_statistics(self):

        active_connections = sum(1 for conn in self.connections if conn.is_connected)
        total_points = sum(conn.points for conn in self.connections)
        total_points_today = sum(conn.points_today for conn in self.connections)
        total_traffic_sent = sum(conn.bytes_sent for conn in self.connections)
        total_traffic_received = sum(conn.bytes_received for conn in self.connections)
        
        self.active_label.configure(
            text=f"{active_connections}/{len(self.connections)}"
        )
        self.points_label.configure(
            text=f"{total_points:,}"
        )
        self.traffic_label.configure(
            text=f"Traffic: ↑{format_bytes(total_traffic_sent)} ↓{format_bytes(total_traffic_received)}"
        )
    
    def check_connections(self):

        if not self.is_running:  
            return
        
        current_time = datetime.now()
        for i, connection in enumerate(self.connections):
            if not self.is_running: 
                break
            
            if not connection.is_connected:
                time_since_update = (current_time - connection.last_update).total_seconds() if connection.last_update else float('inf')
                if time_since_update > 30:
                    self.status_label.configure(text=f"Reconnecting {i+1}/{len(self.connections)}")
                    connection.stop()
                    time.sleep(1)
                    
                    if not self.is_running: 
                        break
                    
                    new_connection = TeneoConnection(connection.access_token, connection.proxy, connection.proxy_auth)
                    self.connections[i] = new_connection
                    self.threads[i] = new_connection.connect()
                    time.sleep(1)

    def show_error(self, message):
        """Отображение ошибки"""
        self.status_label.configure(text=f"Error: {message}")

    def update_table(self):

        columns = {
            "id": {"width": 6, "align": "<", "title": "ID"},
            "token": {"width": 10, "align": "<", "title": "Token"},
            "points": {"width": 12, "align": ">", "title": "Points"},
            "today": {"width": 8, "align": ">", "title": "Today"},
            "last_update": {"width": 12, "align": "<", "title": "Last Update"},
            "uptime": {"width": 8, "align": "<", "title": "Uptime"},
            "proxy": {"width": 70, "align": "<", "title": "Proxy"}
        }
        

        spacing = "    "  
        padding_left = "    "  

        header_line = padding_left
        for col, props in columns.items():
            header_line += f"{props['title']:{props['align']}{props['width']}}{spacing}"
        

        divider = padding_left
        for col, props in columns.items():
            divider += "─" * props['width'] + spacing
        

        table_text = header_line + "\n" + divider + "\n"
        

        for i, conn in enumerate(self.connections, 1):
            data = self.format_connection_data(i, conn)
            line = padding_left
            
 
            for (col, props), value in zip(columns.items(), data):
                line += f"{value:{props['align']}{props['width']}}{spacing}"
            
            table_text += line + "\n"
        

        self.table.configure(text=table_text)

    def format_connection_data(self, index, conn):

        current_time = datetime.now()
        

        status = "🟢" if conn.is_connected else "🔴"
        

        token = "eyJhbGci"
        points = f"{conn.points:,}"
        today = str(conn.points_today)
        last_update = conn.last_update.strftime("%H:%M:%S") if conn.last_update else "Never"
        uptime = format_time_ago((current_time - conn.connection_time).total_seconds() if conn.connection_time else 0)

        proxy = conn.proxy if conn.proxy else "Direct"
        
        return [
            f"{status}{index:02d}",  
            token,                    
            points,                   
            today,                    
            last_update,             
            uptime,                  
            proxy                    
        ]

    def setup_logging(self):


        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', 
                                    datefmt='%H:%M:%S')
        

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
 
        gui_handler = GUIHandler(self.add_log)
        gui_handler.setFormatter(formatter)
        

        root_logger = logging.getLogger()
        root_logger.handlers = []
        

        root_logger.addHandler(console_handler)
        root_logger.addHandler(gui_handler)
        root_logger.setLevel(logging.INFO)

    def add_log(self, message):

        current_time = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")  
        self.log_text.insert("end", f"[{current_time}] {message}\n")
        self.log_text.see("end")  
        self.log_text.configure(state="disabled")  
        
    def setup_connection_callbacks(self, connection):

        connection.on_status_change = lambda conn: self.on_connection_status_change(conn)
        connection.on_points_update = lambda conn: self.on_points_update(conn)
        connection.on_error = lambda error: self.add_log(f"Error: {error}")
        
    def on_connection_status_change(self, connection):

        self.update_statistics()
        self.update_table()
        status = "connected" if connection.is_connected else "disconnected"
        self.add_log(f"Connection {connection.access_token[:8]}... {status}")
        
    def on_points_update(self, connection):

        self.update_statistics()
        self.update_table()
        self.add_log(f"Points updated for {connection.access_token[:8]}...")

    def show_dashboard(self):

        self.files_frame.pack_forget()
        self.menu_button.configure(
            fg_color=self.colors["accent"],
            text_color="#FFFFFF",
            hover_color=self.colors["accent_hover"]
        )
        self.files_button.configure(
            fg_color="transparent",
            text_color=self.colors["text"],
            hover_color=self.colors["bg_medium"]
        )

    def show_files(self):

        self.files_frame.pack(pady=10, padx=15, fill="x")
        self.menu_button.configure(
            fg_color="transparent",
            text_color=self.colors["text"],
            hover_color=self.colors["bg_medium"]
        )
        self.files_button.configure(
            fg_color=self.colors["accent"],
            text_color="#FFFFFF",
            hover_color=self.colors["accent_hover"]
        )

    def select_accounts_file(self):

        filename = ctk.filedialog.askopenfilename(
            title="Select Accounts File",
            filetypes=[("Text files", "*.txt")]
        )
        if filename:
            self.accounts_path.configure(text=filename)

    def select_proxies_file(self):

        filename = ctk.filedialog.askopenfilename(
            title="Select Proxies File",
            filetypes=[("Text files", "*.txt")]
        )
        if filename:
            self.proxies_path.configure(text=filename)

def main():
    app = TeneoGUI()
    app.mainloop()

if __name__ == "__main__":
        main()