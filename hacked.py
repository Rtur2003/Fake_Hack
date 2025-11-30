import argparse
import getpass
import json
import os
import platform
import random
import socket
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime

import pygame
import psutil
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# Sabit değişkenler
TOTAL_TIME = 30  # Toplam simülasyon süresi (saniye)
DEFAULT_DURATION = 35  # Ana simulasyon suresi (saniye)
DEFAULT_AUTO_CLOSE = 15  # Pixel savasi sonrasi ekstra bekleme (saniye)
BACKGROUND_COLOR = "#0c0c0c"
TEXT_COLOR = "#00ff41"
HIGHLIGHT_COLOR = "#ff4444"
TERMINAL_BG = "#1a1a1a"
SECONDARY_TEXT = "#888888"


@dataclass
class SimulatorConfig:
    duration: int = DEFAULT_DURATION
    auto_close: int = DEFAULT_AUTO_CLOSE
    fullscreen: bool = True
    enable_pixel_war: bool = True
    block_input: bool = False
    pixel_size: int = 5
    war_tick_ms: int = 60


class RealSystemInfo:
    """Gerçek sistem bilgilerini toplayan sınıf"""
    
    @staticmethod
    def get_system_info():
        """Detaylı sistem bilgilerini al"""
        try:
            info = {}
            
            # Temel sistem bilgileri
            info['os'] = f"{platform.system()} {platform.release()}"
            info['version'] = platform.version()
            info['architecture'] = platform.machine()
            info['processor'] = platform.processor()
            info['hostname'] = socket.gethostname()
            info['username'] = getpass.getuser()
            
            # Bellek bilgileri
            memory = psutil.virtual_memory()
            info['total_memory'] = f"{memory.total // (1024**3)} GB"
            info['available_memory'] = f"{memory.available // (1024**3)} GB"
            info['memory_usage'] = f"{memory.percent}%"
            
            # CPU bilgileri
            info['cpu_count'] = psutil.cpu_count()
            info['cpu_freq'] = f"{psutil.cpu_freq().current:.0f} MHz" if psutil.cpu_freq() else "N/A"
            info['cpu_usage'] = f"{psutil.cpu_percent(interval=1)}%"
            
            # Disk bilgileri
            disk = psutil.disk_usage('/')
            info['disk_total'] = f"{disk.total // (1024**3)} GB"
            info['disk_used'] = f"{disk.used // (1024**3)} GB"
            info['disk_free'] = f"{disk.free // (1024**3)} GB"
            info['disk_usage'] = f"{(disk.used/disk.total)*100:.1f}%"
            
            # Network bilgileri
            info['ip_address'] = RealSystemInfo.get_local_ip()
            info['mac_address'] = RealSystemInfo.get_mac_address()
            info['network_interfaces'] = list(psutil.net_if_addrs().keys())
            
            # Process bilgileri
            info['process_count'] = len(psutil.pids())
            info['boot_time'] = datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
            
            return info
        except Exception as e:
            print(f"Sistem bilgisi alınırken hata: {e}")
            return {}
    
    @staticmethod
    def get_local_ip():
        """Yerel IP adresini al"""
        try:
            with socket.create_connection(("8.8.8.8", 80), timeout=0.5) as s:
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    @staticmethod
    def get_mac_address():
        """MAC adresini al"""
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                           for elements in range(0,2*6,2)][::-1])
            return mac
        except:
            return "00:00:00:00:00:00"
    
    @staticmethod
    def get_running_processes():
        """Çalışan işlemleri al"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            return sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:20]
        except:
            return []
    
    @staticmethod
    def get_network_connections():
        """Network bağlantılarını al"""
        try:
            connections = []
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'ESTABLISHED':
                    connections.append({
                        'local': f"{conn.laddr.ip}:{conn.laddr.port}",
                        'remote': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A",
                        'status': conn.status,
                        'pid': conn.pid
                    })
            return connections[:15]
        except:
            return []

class HackSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("System Access Terminal")
        self.root.configure(bg=BACKGROUND_COLOR)
        self.root.attributes('-fullscreen', True)
        self.root.config(cursor="none")
        
        # Gerçek sistem verilerini al
        self.system_data = RealSystemInfo.get_system_info()
        
        # Veri dosyalarını yükle
        self.load_data()
        
        # GUI elemanlarını oluştur
        self.create_gui()
        
        # Pygame başlat (ses için)
        try:
            pygame.init()
            pygame.mixer.init()
            self.load_sounds()
        except Exception as e:
            print(f"Ses sistemi başlatılamadı: {e}")
        
        # Giriş engellemeyi aktifleştir
        self.root.bind_all("<Key>", self.block_input)
        self.root.bind_all("<Button>", self.block_input)
        
        # Çıkış tuşu (gizli)
        self.root.bind("<Escape>", self.emergency_exit)
        
        # Otomatik kapanma zamanlayıcısı
        self.auto_close_time = 45
        self.auto_close_timer = None
        
        # Simülasyonu başlat
        self.start_simulation()
    
    def load_sounds(self):
        """Ses dosyalarını yükle"""
        try:
            # Basit bip sesleri oluştur
            self.has_sound = True
        except Exception as e:
            self.has_sound = False
            print(f"Ses yüklenemedi: {e}")
    
    def load_data(self):
        """Veri dosyalarını yükle - gerçek sistem verileriyle"""
        # Gerçek sistem bilgilerini kullan
        self.system_info = [
            f"Target: {self.system_data.get('os', 'Unknown OS')}",
            f"Version: {self.system_data.get('version', 'Unknown')}",
            f"Architecture: {self.system_data.get('architecture', 'Unknown')}",
            f"Processor: {self.system_data.get('processor', 'Unknown')}",
            f"Hostname: {self.system_data.get('hostname', 'Unknown')}",
            f"User: {self.system_data.get('username', 'Unknown')}",
            f"IP Address: {self.system_data.get('ip_address', '127.0.0.1')}",
            f"MAC Address: {self.system_data.get('mac_address', 'Unknown')}",
            f"Memory: {self.system_data.get('total_memory', 'Unknown')} ({self.system_data.get('memory_usage', '0%')} used)",
            f"CPU Cores: {self.system_data.get('cpu_count', 'Unknown')}",
            f"CPU Frequency: {self.system_data.get('cpu_freq', 'Unknown')}",
            f"CPU Usage: {self.system_data.get('cpu_usage', '0%')}",
            f"Disk Total: {self.system_data.get('disk_total', 'Unknown')}",
            f"Disk Used: {self.system_data.get('disk_used', 'Unknown')} ({self.system_data.get('disk_usage', '0%')})",
            f"Boot Time: {self.system_data.get('boot_time', 'Unknown')}",
            f"Processes: {self.system_data.get('process_count', 0)} running"
        ]
        
        # Gerçekçi hack logları
        self.logs = [
            f"Establishing connection to {self.system_data.get('hostname', 'target')}...",
            f"Scanning {self.system_data.get('ip_address', '127.0.0.1')} for vulnerabilities...",
            f"Found {self.system_data.get('os', 'target OS')} running on target system",
            f"Exploiting {self.system_data.get('architecture', 'unknown')} architecture vulnerabilities...",
            f"Bypassing {self.system_data.get('username', 'user')} account restrictions...",
            f"Accessing system with {self.system_data.get('cpu_count', '1')} CPU cores detected...",
            f"Memory footprint: {self.system_data.get('memory_usage', 'unknown')} utilization",
            f"Infiltrating {len(self.system_data.get('network_interfaces', []))} network interfaces...",
            "Escalating privileges to administrator level...",
            "Installing keylogger and screen capture modules...",
            f"Backdoor installed on port {random.randint(8000, 9999)}",
            "Encrypting harvested credentials...",
            f"Exfiltrating data via MAC {self.system_data.get('mac_address', 'unknown')}...",
            "Covering tracks and clearing event logs...",
            "Establishing persistent remote access...",
            "Operation completed - Full system compromise achieved."
        ]
        
        self.status_messages = [
            f"STATUS: Connected to {self.system_data.get('hostname', 'target')}",
            "STATUS: Vulnerability scan complete",
            "STATUS: Payload injection successful", 
            "STATUS: Privilege escalation in progress",
            "STATUS: System enumeration complete",
            "WARNING: Antivirus software detected - evading...",
            "INFO: Stealth mode activated",
            "SUCCESS: Root access obtained",
            "STATUS: Installing persistence mechanisms",
            "STATUS: Data harvesting in progress",
            "INFO: Network traffic masking enabled",
            "STATUS: Credential dump successful",
            "WARNING: User activity detected - hiding presence",
            "STATUS: Log cleanup completed",
            "SUCCESS: Remote backdoor established",
            "COMPLETE: Mission accomplished - Full control achieved"
        ]
    
    def create_gui(self):
        """Sade ve profesyonel arayüz oluştur"""
        # Ana konteyner
        main_container = tk.Frame(self.root, bg=BACKGROUND_COLOR)
        main_container.pack(fill='both', expand=True, padx=40, pady=30)
        
        # Başlık bölümü
        self.create_header(main_container)
        
        # İçerik alanı
        content_frame = tk.Frame(main_container, bg=BACKGROUND_COLOR)
        content_frame.pack(fill='both', expand=True, pady=(20, 0))
        
        # Sol panel - Sistem bilgileri
        self.create_info_panel(content_frame)
        
        # Ana terminal
        self.create_terminal(content_frame)
        
        # Sağ panel - Canlı veriler
        self.create_live_panel(content_frame)
        
        # Alt durum çubuğu
        self.create_status_bar(main_container)
    
    def create_header(self, parent):
        """Basit başlık"""
        header_frame = tk.Frame(parent, bg=BACKGROUND_COLOR)
        header_frame.pack(fill='x')
        
        # Ana başlık
        title_label = tk.Label(
            header_frame,
            text=f"SYSTEM ACCESS GRANTED - {self.system_data.get('hostname', 'TARGET').upper()}",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
            font=("Consolas", 24, "bold")
        )
        title_label.pack(pady=(0, 5))
        
        # Alt başlık
        subtitle_label = tk.Label(
            header_frame,
            text=f"Compromising {self.system_data.get('os', 'Unknown System')} | User: {self.system_data.get('username', 'Unknown')}",
            fg=SECONDARY_TEXT,
            bg=BACKGROUND_COLOR,
            font=("Consolas", 12)
        )
        subtitle_label.pack()
        
        # Ayırıcı çizgi
        separator = tk.Frame(header_frame, bg=TEXT_COLOR, height=1)
        separator.pack(fill='x', pady=(15, 0))
    
    def create_info_panel(self, parent):
        """Sol panel - Sistem bilgileri"""
        info_frame = tk.Frame(parent, bg=TERMINAL_BG, relief="solid", bd=1)
        info_frame.pack(side='left', fill='y', padx=(0, 10))
        
        # Panel başlığı
        info_title = tk.Label(
            info_frame,
            text="TARGET SYSTEM INFO",
            fg=TEXT_COLOR,
            bg=TERMINAL_BG,
            font=("Consolas", 10, "bold")
        )
        info_title.pack(pady=(10, 5), padx=10)
        
        # Sistem bilgileri
        self.info_text = tk.Text(
            info_frame,
            width=35,
            height=25,
            bg=TERMINAL_BG,
            fg=SECONDARY_TEXT,
            font=("Consolas", 8),
            bd=0,
            wrap='word',
            state='disabled',
            cursor=""
        )
        self.info_text.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Sistem bilgilerini ekle
        self.update_info_panel()
    
    def create_live_panel(self, parent):
        """Sağ panel - Canlı veriler"""
        live_frame = tk.Frame(parent, bg=TERMINAL_BG, relief="solid", bd=1)
        live_frame.pack(side='right', fill='y', padx=(10, 0))
        
        # Panel başlığı
        live_title = tk.Label(
            live_frame,
            text="LIVE MONITORING",
            fg=HIGHLIGHT_COLOR,
            bg=TERMINAL_BG,
            font=("Consolas", 10, "bold")
        )
        live_title.pack(pady=(10, 5), padx=10)
        
        # Canlı veriler
        self.live_text = tk.Text(
            live_frame,
            width=30,
            height=25,
            bg=TERMINAL_BG,
            fg=TEXT_COLOR,
            font=("Consolas", 8),
            bd=0,
            wrap='word',
            state='disabled',
            cursor=""
        )
        self.live_text.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Canlı veri güncellemesini başlat
        self.update_live_data()
    
    def create_terminal(self, parent):
        """Ana terminal alanı"""
        terminal_container = tk.Frame(parent, bg=BACKGROUND_COLOR)
        terminal_container.pack(side='left', fill='both', expand=True)
        
        # Terminal başlığı
        terminal_header = tk.Frame(terminal_container, bg="#2d2d2d", height=30)
        terminal_header.pack(fill='x')
        terminal_header.pack_propagate(False)
        
        terminal_title = tk.Label(
            terminal_header,
            text=f" {self.system_data.get('username', 'root')}@{self.system_data.get('hostname', 'target')}:~# ",
            fg="white",
            bg="#2d2d2d",
            font=("Consolas", 10),
            anchor='w'
        )
        terminal_title.pack(side='left', fill='y')
        
        # Terminal içeriği
        self.terminal_text = tk.Text(
            terminal_container,
            bg=TERMINAL_BG,
            fg=TEXT_COLOR,
            font=("Consolas", 11),
            bd=0,
            wrap='word',
            state='disabled',
            cursor=""
        )
        self.terminal_text.pack(fill='both', expand=True, pady=(0, 20))
        
        # İlerleme alanı
        progress_frame = tk.Frame(terminal_container, bg=BACKGROUND_COLOR)
        progress_frame.pack(fill='x')
        
        self.progress_label = tk.Label(
            progress_frame,
            text=f"Initializing attack on {self.system_data.get('hostname', 'target')}...",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
            font=("Consolas", 10)
        )
        self.progress_label.pack(anchor='w')
        
        # İlerleme çubuğu
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            length=500,
            mode="determinate"
        )
        self.progress_bar.pack(anchor='w', pady=(5, 0))
        
        # İlerleme yüzdesi
        self.progress_percent = tk.Label(
            progress_frame,
            text="0%",
            fg=SECONDARY_TEXT,
            bg=BACKGROUND_COLOR,
            font=("Consolas", 9)
        )
        self.progress_percent.pack(anchor='w', pady=(2, 0))
    
    def create_status_bar(self, parent):
        """Alt durum çubuğu"""
        status_frame = tk.Frame(parent, bg="#2d2d2d", height=25)
        status_frame.pack(fill='x', side='bottom')
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_frame,
            text="Initiating system penetration...",
            fg="white",
            bg="#2d2d2d",
            font=("Consolas", 9),
            anchor='w'
        )
        self.status_label.pack(side='left', padx=10, fill='y')
        
        # Sistem durumu
        system_status = tk.Label(
            status_frame,
            text=f"Target: {self.system_data.get('ip_address', '127.0.0.1')} | CPU: {self.system_data.get('cpu_usage', '0%')} | RAM: {self.system_data.get('memory_usage', '0%')}",
            fg=SECONDARY_TEXT,
            bg="#2d2d2d",
            font=("Consolas", 9)
        )
        system_status.pack(side='left', padx=20, fill='y')
        
        # Saat
        self.time_label = tk.Label(
            status_frame,
            text="",
            fg="white",
            bg="#2d2d2d",
            font=("Consolas", 9)
        )
        self.time_label.pack(side='right', padx=10, fill='y')
        
        self.update_clock()
    
    def update_info_panel(self):
        """Sistem bilgilerini güncelle"""
        self.info_text.config(state='normal')
        self.info_text.delete(1.0, tk.END)
        for info in self.system_info:
            self.info_text.insert(tk.END, info + "\n\n")
        self.info_text.config(state='disabled')
    
    def update_live_data(self):
        """Canlı verileri güncelle"""
        try:
            # Güncel sistem verilerini al
            current_cpu = psutil.cpu_percent(interval=0.1)
            current_memory = psutil.virtual_memory().percent
            
            # Network bağlantıları
            connections = RealSystemInfo.get_network_connections()
            
            # Top processes
            top_processes = RealSystemInfo.get_running_processes()[:10]
            
            # Canlı veri metnini oluştur
            live_data = f"=== REAL-TIME MONITORING ===\n\n"
            live_data += f"CPU Usage: {current_cpu}%\n"
            live_data += f"Memory Usage: {current_memory}%\n\n"
            
            live_data += "=== ACTIVE CONNECTIONS ===\n"
            for i, conn in enumerate(connections[:8]):
                live_data += f"{conn['local']} -> {conn['remote']}\n"
            
            live_data += "\n=== TOP PROCESSES ===\n"
            for proc in top_processes[:8]:
                cpu_pct = proc['cpu_percent'] or 0
                mem_pct = proc['memory_percent'] or 0
                live_data += f"{proc['name'][:15]:<15} CPU:{cpu_pct:4.1f}% MEM:{mem_pct:4.1f}%\n"
            
            # Güncelle
            self.live_text.config(state='normal')
            self.live_text.delete(1.0, tk.END)
            self.live_text.insert(tk.END, live_data)
            self.live_text.config(state='disabled')
            
        except Exception as e:
            print(f"Canlı veri güncellemesi hatası: {e}")
        
        # 2 saniyede bir güncelle
        self.root.after(2000, self.update_live_data)
    
    def update_clock(self):
        """Saati güncelle"""
        current_time = time.strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_clock)
    
    def block_input(self, event):
        """Kullanıcı girdilerini engelle"""
        return "break"
    
    def emergency_exit(self, event=None):
        """Acil çıkış"""
        if hasattr(self, 'auto_close_timer') and self.auto_close_timer:
            self.root.after_cancel(self.auto_close_timer)
        try:
            pygame.mixer.quit()
            pygame.quit()
        except:
            pass
        self.root.destroy()
        sys.exit()
    
    def start_simulation(self):
        """Simülasyonu başlat"""
        # Ana süreci başlat
        self.hack_thread = threading.Thread(target=self.hack_sequence, daemon=True)
        self.hack_thread.start()
        
        # Otomatik kapanma
        self.auto_close_timer = self.root.after(
            (self.auto_close_time + TOTAL_TIME) * 1000, 
            self.emergency_exit
        )
    
    def hack_sequence(self):
        """Ana hack sıralaması - gerçek sistem verileriyle"""
        start_time = time.time()
        log_index = 0
        
        while log_index < len(self.logs):
            elapsed = time.time() - start_time
            progress = min(elapsed / TOTAL_TIME, 1)
            
            # İlerleme güncelle
            self.progress_bar['value'] = progress * 100
            self.progress_percent.config(text=f"{int(progress * 100)}%")
            
            # İlerleme etiketini güncelle
            if progress < 0.3:
                self.progress_label.config(text="Scanning target system...")
            elif progress < 0.6:
                self.progress_label.config(text="Exploiting vulnerabilities...")
            elif progress < 0.9:
                self.progress_label.config(text="Installing backdoors...")
            else:
                self.progress_label.config(text="Finalizing system compromise...")
            
            # Yeni log ekleme zamanı
            if log_index < len(self.logs) and elapsed > log_index * (TOTAL_TIME / len(self.logs)):
                log = self.logs[log_index]
                
                # Terminal'e yaz
                self.add_terminal_line(log)
                
                # Durum güncelle
                if log_index < len(self.status_messages):
                    self.status_label.config(text=self.status_messages[log_index])
                
                log_index += 1
            
            if progress >= 1:
                break
            
            time.sleep(0.1)
        
        # Tamamlandı
        self.add_terminal_line(f"\n=== SYSTEM {self.system_data.get('hostname', 'TARGET').upper()} FULLY COMPROMISED ===", color=HIGHLIGHT_COLOR)
        self.status_label.config(text=f"Full control of {self.system_data.get('hostname', 'target')} achieved")
        self.progress_label.config(text="System compromise completed successfully!")
        
        # 3 saniye bekle sonra pixel savaşını başlat
        time.sleep(3)
        self.start_pixel_war()
    
    def add_terminal_line(self, text, color=TEXT_COLOR):
        """Terminal'e satır ekle"""
        self.terminal_text.config(state='normal')
        
        # Zaman damgası ekle
        timestamp = time.strftime("[%H:%M:%S] ")
        self.terminal_text.insert(tk.END, timestamp, "timestamp")
        self.terminal_text.insert(tk.END, text + "\n", "text")
        
        # Renkleri ayarla
        self.terminal_text.tag_configure("timestamp", foreground=SECONDARY_TEXT)
        self.terminal_text.tag_configure("text", foreground=color)
        
        # Scroll to end
        self.terminal_text.see(tk.END)
        self.terminal_text.config(state='disabled')
        
        # Metin sınırla
        lines = int(self.terminal_text.index('end-1c').split('.')[0])
        if lines > 25:
            self.terminal_text.config(state='normal')
            self.terminal_text.delete("1.0", "3.0")
            self.terminal_text.config(state='disabled')
    
    def start_pixel_war(self):
        """Pixel savaşı efektini başlat"""
        # Mevcut arayüzü gizle
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Yeni canvas oluştur (tam ekran)
        self.canvas = tk.Canvas(
            self.root, 
            bg='black', 
            highlightthickness=0,
            width=self.root.winfo_screenwidth(),
            height=self.root.winfo_screenheight()
        )
        self.canvas.pack(fill='both', expand=True)
        
        # Ekran boyutlarını al
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()
        
        # Pixel savaşı değişkenleri
        self.pixel_size = 4
        self.pixels = []
        self.war_active = True
        
        # İki farklı renk ordusu
        self.colors = {
            'red_army': ['#ff0000', '#ff3333', '#ff6666', '#cc0000', '#990000'],
            'blue_army': ['#0000ff', '#3333ff', '#6666ff', '#0000cc', '#000099'],
            'green_army': ['#00ff00', '#33ff33', '#66ff66', '#00cc00', '#009900'],
            'chaos': ['#ffffff', '#ffff00', '#ff00ff', '#00ffff']
        }
        
        # Başlangıç mesajı
        self.show_war_message()
        
        # Pixel savaşını başlat
        self.root.after(2000, self.initialize_armies)
    
    def show_war_message(self):
        """Savaş başlangıç mesajını göster"""
        # Ekranı karartan efekt
        for i in range(10):
            self.canvas.create_rectangle(
                0, 0, self.screen_width, self.screen_height,
                fill='black', outline='', tags='fade'
            )
        
        # Uyarı mesajı
        warning_text = "SYSTEM CORE DESTABILIZED"
        self.canvas.create_text(
            self.screen_width//2, self.screen_height//2 - 100,
            text=warning_text,
            fill='#ff0000',
            font=('Consolas', 36, 'bold'),
            tags='warning'
        )
        
        # Alt mesaj
        sub_text = "PIXEL ENTITIES ENGAGING IN DIGITAL WARFARE"
        self.canvas.create_text(
            self.screen_width//2, self.screen_height//2 - 50,
            text=sub_text,
            fill='#ffff00',
            font=('Consolas', 18),
            tags='warning'
        )
        
        # Yanıp sönme efekti
        self.blink_warning()
    
    def blink_warning(self, count=0):
        """Uyarı mesajını yanıp söndür"""
        if count < 6:
            if count % 2 == 0:
                self.canvas.itemconfig('warning', state='normal')
            else:
                self.canvas.itemconfig('warning', state='hidden')
            self.root.after(500, lambda: self.blink_warning(count + 1))
        else:
            self.canvas.delete('warning')
    
    def initialize_armies(self):
        """Pixel ordularını başlat"""
        # Grid boyutlarını hesapla
        self.grid_width = self.screen_width // self.pixel_size
        self.grid_height = self.screen_height // self.pixel_size
        
        # Pixel grid'i oluştur
        self.pixel_grid = {}
        
        # Kırmızı ordu (sol taraf)
        red_pixels = []
        for x in range(0, self.grid_width // 4):
            for y in range(self.grid_height):
                if random.random() < 0.3:  # %30 yoğunluk
                    pixel_id = self.create_pixel(x, y, random.choice(self.colors['red_army']))
                    red_pixels.append({'id': pixel_id, 'x': x, 'y': y, 'army': 'red'})
        
        # Mavi ordu (sağ taraf)
        blue_pixels = []
        for x in range(3 * self.grid_width // 4, self.grid_width):
            for y in range(self.grid_height):
                if random.random() < 0.3:  # %30 yoğunluk
                    pixel_id = self.create_pixel(x, y, random.choice(self.colors['blue_army']))
                    blue_pixels.append({'id': pixel_id, 'x': x, 'y': y, 'army': 'blue'})
        
        # Yeşil ordu (merkez üst)
        green_pixels = []
        for x in range(self.grid_width // 3, 2 * self.grid_width // 3):
            for y in range(0, self.grid_height // 4):
                if random.random() < 0.2:  # %20 yoğunluk
                    pixel_id = self.create_pixel(x, y, random.choice(self.colors['green_army']))
                    green_pixels.append({'id': pixel_id, 'x': x, 'y': y, 'army': 'green'})
        
        self.armies = {
            'red': red_pixels,
            'blue': blue_pixels,
            'green': green_pixels
        }
        
        # Savaşı başlat
        self.battle_round = 0
        self.start_battle()
    
    def create_pixel(self, grid_x, grid_y, color):
        """Tek bir pixel oluştur"""
        x1 = grid_x * self.pixel_size
        y1 = grid_y * self.pixel_size
        x2 = x1 + self.pixel_size
        y2 = y1 + self.pixel_size
        
        pixel_id = self.canvas.create_rectangle(
            x1, y1, x2, y2,
            fill=color, outline='', tags='pixel'
        )
        
        # Grid'e kaydet
        self.pixel_grid[(grid_x, grid_y)] = {
            'id': pixel_id, 
            'color': color, 
            'army': self.get_army_from_color(color)
        }
        
        return pixel_id
    
    def get_army_from_color(self, color):
        """Renkten orduyu belirle"""
        for army, colors in self.colors.items():
            if color in colors:
                return army
        return 'neutral'
    
    def start_battle(self):
        """Savaş turunu başlat"""
        if not self.war_active or self.battle_round > 200:
            self.end_war()
            return
            
        # Her ordu için hareket et
        for army_name, army_pixels in self.armies.items():
            self.move_army(army_name, army_pixels)
        
        # Çatışmaları kontrol et
        self.handle_conflicts()
        
        # Rastgele kaos pixelleri ekle
        if random.random() < 0.1:
            self.spawn_chaos_pixels()
        
        # Sonraki tur
        self.battle_round += 1
        self.root.after(50, self.start_battle)  # 50ms aralıklarla
    
    def move_army(self, army_name, army_pixels):
        """Orduyu hareket ettir"""
        new_positions = []
        
        for pixel in army_pixels[:]:  # Copy list to avoid modification during iteration
            current_x, current_y = pixel['x'], pixel['y']
            
            # Hareket yönünü belirle (orduya göre)
            if army_name == 'red':
                # Sağa doğru hareket
                new_x = current_x + random.choice([-1, 0, 1, 1, 1])
                new_y = current_y + random.choice([-1, 0, 1])
            elif army_name == 'blue':
                # Sola doğru hareket
                new_x = current_x + random.choice([-1, -1, -1, 0, 1])
                new_y = current_y + random.choice([-1, 0, 1])
            else:  # green
                # Aşağı doğru hareket
                new_x = current_x + random.choice([-1, 0, 1])
                new_y = current_y + random.choice([0, 1, 1, 1])
            
            # Sınırları kontrol et
            new_x = max(0, min(new_x, self.grid_width - 1))
            new_y = max(0, min(new_y, self.grid_height - 1))
            
            # Yeni pozisyon mevcut mu kontrol et
            if (new_x, new_y) not in self.pixel_grid or random.random() < 0.3:
                # Eski pixeli sil
                if (current_x, current_y) in self.pixel_grid:
                    self.canvas.delete(self.pixel_grid[(current_x, current_y)]['id'])
                    del self.pixel_grid[(current_x, current_y)]
                
                # Yeni pozisyonda pixel oluştur
                if (new_x, new_y) not in self.pixel_grid:
                    color = random.choice(self.colors[army_name + '_army'])
                    new_pixel_id = self.create_pixel(new_x, new_y, color)
                    
                    pixel['x'] = new_x
                    pixel['y'] = new_y
                    pixel['id'] = new_pixel_id
                    new_positions.append(pixel)
        
        # Ordu listesini güncelle
        self.armies[army_name] = new_positions
    
    def handle_conflicts(self):
        """Çatışmaları yönet"""
        conflict_positions = []
        
        # Çakışan pozisyonları bul
        position_armies = {}
        for army_name, army_pixels in self.armies.items():
            for pixel in army_pixels:
                pos = (pixel['x'], pixel['y'])
                if pos not in position_armies:
                    position_armies[pos] = []
                position_armies[pos].append((army_name, pixel))
        
        # Çakışmaları çöz
        for pos, army_pixels in position_armies.items():
            if len(army_pixels) > 1:
                # Çatışma var! Rastgele kazanan belirle
                winner_army, winner_pixel = random.choice(army_pixels)
                
                # Kaybedenleri sil
                for army_name, pixel in army_pixels:
                    if army_name != winner_army:
                        if pixel in self.armies[army_name]:
                            self.armies[army_name].remove(pixel)
                        if pos in self.pixel_grid:
                            self.canvas.delete(self.pixel_grid[pos]['id'])
                
                # Kazananı güçlendir (parlak renk)
                if pos in self.pixel_grid:
                    bright_colors = ['#ffffff', '#ffff00', '#ff00ff']
                    new_color = random.choice(bright_colors)
                    self.canvas.itemconfig(self.pixel_grid[pos]['id'], fill=new_color)
    
    def spawn_chaos_pixels(self):
        """Rastgele kaos pixelleri oluştur"""
        for _ in range(random.randint(10, 30)):
            x = random.randint(0, self.grid_width - 1)
            y = random.randint(0, self.grid_height - 1)
            
            if (x, y) not in self.pixel_grid:
                color = random.choice(self.colors['chaos'])
                self.create_pixel(x, y, color)
    
    def end_war(self):
        """Savaşı bitir"""
        # Final efekti - tüm ekranı beyaz yap
        self.canvas.create_rectangle(
            0, 0, self.screen_width, self.screen_height,
            fill='white', outline='', tags='final'
        )
        
        # Bitiş mesajı
        end_text = "DIGITAL REALITY RESTORED"
        self.canvas.create_text(
            self.screen_width//2, self.screen_height//2,
            text=end_text,
            fill='black',
            font=('Consolas', 48, 'bold'),
            tags='final'
        )
        
        # 3 saniye sonra uygulamayı kapat
        self.root.after(3000, self.emergency_exit)

def main():
    try:
        # Gerekli kütüphaneleri kontrol et
        required_modules = ['psutil', 'pygame', 'PIL']
        missing_modules = []
        
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            print(f"Eksik kütüphaneler: {', '.join(missing_modules)}")
            print("Yüklemek için: pip install psutil pygame Pillow")
            return
        
        root = tk.Tk()
        app = HackSimulator(root)
        root.mainloop()
    except Exception as e:
        print(f"Uygulama hatası: {e}")
        try:
            pygame.mixer.quit()
            pygame.quit()
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
