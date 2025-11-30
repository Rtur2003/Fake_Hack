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
from PIL import Image, ImageTk, ImageGrab

# Sabit değişkenler
DEFAULT_DURATION = 90  # Ana simulasyon suresi (saniye)
DEFAULT_AUTO_CLOSE = 35  # Pixel savasi sonrasi ekstra bekleme (saniye)
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
    war_tick_ms: int = 45
    glitch_mode: bool = True  # Ekran karincalanma efekti acik


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
            # interval=0.0 for a quick, non-blocking sample
            info['cpu_usage'] = f"{psutil.cpu_percent(interval=0.0)}%"
            
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
    def __init__(self, root, config: SimulatorConfig):
        self.root = root
        self.config = config
        self.ui_active = True
        self.shutdown_flag = False
        self.after_jobs = []
        self.auto_close_timer = None
        self.sim_duration = self.config.duration
        self.sim_progress = 0.0
        self.current_phase_index = 0
        self.sequence_started_at = None
        self.root.title("System Access Terminal")
        self.root.configure(bg=BACKGROUND_COLOR)
        if self.config.fullscreen:
            self.root.attributes('-fullscreen', True)
            self.root.config(cursor="none")
        else:
            self.root.geometry("1280x720")
            self.root.config(cursor="arrow")
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.protocol("WM_DELETE_WINDOW", self.emergency_exit)
        self.root.bind("<Escape>", self.emergency_exit)
        self.root.bind("<Control-q>", self.emergency_exit)
        if self.config.block_input:
            self.root.bind_all("<Key>", self.block_input)
            self.root.bind_all("<Button>", self.block_input)
        
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
        self.operation_code = f"SIG-{random.randint(10000, 99999)}"
        process_snapshot = RealSystemInfo.get_running_processes()
        connections_snapshot = RealSystemInfo.get_network_connections()
        key_processes = [p['name'] for p in process_snapshot if p.get('name')]
        primary_remote = "external relay"
        if connections_snapshot:
            remote_candidate = connections_snapshot[0].get('remote', '')
            if remote_candidate and remote_candidate != "N/A":
                primary_remote = remote_candidate
        network_list = self.system_data.get('network_interfaces', [])
        interface_display = ", ".join(network_list[:4]) if network_list else "loopback only"
        cpu_load = self.system_data.get('cpu_usage', '0%')
        
        # Gerçek sistem bilgilerini kullan
        self.system_info = [
            f"Operation Code: {self.operation_code}",
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
            f"CPU Usage: {cpu_load}",
            f"Disk Total: {self.system_data.get('disk_total', 'Unknown')}",
            f"Disk Used: {self.system_data.get('disk_used', 'Unknown')} ({self.system_data.get('disk_usage', '0%')})",
            f"Boot Time: {self.system_data.get('boot_time', 'Unknown')}",
            f"Processes: {self.system_data.get('process_count', 0)} running",
            f"Leading Tasks: {', '.join(key_processes[:5]) if key_processes else 'n/a'}",
            f"Sample Remote: {primary_remote}"
        ]
        
        # Operasyon fazları - daha uzun ve katmanlı senaryo
        self.operation_phases = [
            {
                "name": "Reconnaissance",
                "status": "Mapping live telemetry",
                "logs": [
                    f"[RECON] fingerprint: {self.system_data.get('os', 'Unknown OS')} / {self.system_data.get('architecture', '?')}",
                    f"[RECON] host {self.system_data.get('hostname', 'target')} responds at {self.system_data.get('ip_address', '127.0.0.1')}",
                    f"[RECON] interfaces mapped: {interface_display}",
                    f"[RECON] cpu baseline {cpu_load} | mem {self.system_data.get('memory_usage', '0%')}",
                    f"[RECON] booted at {self.system_data.get('boot_time', 'Unknown')}",
                    f"[RECON] {self.system_data.get('process_count', 0)} running processes catalogued",
                    f"[RECON] top tasks: {', '.join(key_processes[:4]) if key_processes else 'idle'}",
                    f"[RECON] open link observed: {primary_remote}"
                ]
            },
            {
                "name": "Breach & Payload",
                "status": "Dropping signed implants",
                "logs": [
                    f"[BREACH] staged loader signed as system service ({self.operation_code})",
                    f"[BREACH] user token hijacked: {self.system_data.get('username', 'user')}",
                    f"[BREACH] memory tuned for {self.system_data.get('cpu_count', '1')} cores @ {self.system_data.get('cpu_freq', 'N/A')}",
                    "[BREACH] stealth hypervisor shim inserted",
                    f"[BREACH] fallback tunnel reserved on port {random.randint(6000, 9000)}",
                    "[BREACH] anti-forensics: event channel muted",
                    "[BREACH] credential cache mirrored and sealed",
                    "[BREACH] lateral kit warmed in memory"
                ]
            },
            {
                "name": "Pivot & Lateral",
                "status": "Moving across surfaces",
                "logs": [
                    f"[PIVOT] enumerating shared memory on {self.system_data.get('hostname', 'target')}",
                    f"[PIVOT] scanning {len(network_list)} interfaces for lateral paths",
                    f"[PIVOT] {random.randint(3, 8)} credential replays throttled for stealth",
                    "[PIVOT] RDP shadow session ghosted",
                    "[PIVOT] kernel callbacks patched for covert syscalls",
                    f"[PIVOT] privilege map compiled for user {self.system_data.get('username', 'user')}",
                    "[PIVOT] ARP cache poisoning staged for neighbors",
                    "[PIVOT] update service swapped for covert beacon"
                ]
            },
            {
                "name": "Data Ops & Exfil",
                "status": "Harvesting local assets",
                "logs": [
                    f"[EXFIL] compressing user profile for {self.system_data.get('username', 'user')}",
                    f"[EXFIL] streaming {random.randint(480, 980)} MB to {primary_remote}",
                    f"[EXFIL] disk utilization snapshot: {self.system_data.get('disk_usage', '0%')}",
                    "[EXFIL] clipboard and keystroke stream copied",
                    "[EXFIL] document manifest sealed with one-time pad",
                    "[EXFIL] camera probe denied; routing through virtual device",
                    "[EXFIL] password vault mimic responding",
                    "[EXFIL] dark dropbox handshake acknowledged"
                ]
            },
            {
                "name": "Cleanup & Control",
                "status": "Locking system down",
                "logs": [
                    "[COVER] wiping recent event traces",
                    f"[COVER] timestamps forged back to {self.system_data.get('boot_time', 'boot')}",
                    "[COVER] DNS cache poisoned with decoy nodes",
                    f"[COVER] persistence heartbeat pinned to {self.system_data.get('ip_address', '127.0.0.1')}",
                    f"[COVER] static backdoor armed ({self.operation_code})",
                    "[COVER] user prompts suppressed with phantom clicks",
                    "[COVER] security center telemetry muted",
                    "[COVER] watchdog triggers rerouted to dummy driver",
                    "[COVER] visual distortion module primed",
                    "[COVER] operator awaiting final lock sequence"
                ]
            }
        ]

        self.phase_count = len(self.operation_phases)
        self.logs, self.status_messages = self.compose_script(self.operation_phases)
        self.current_phase_name = self.operation_phases[0]["name"] if self.operation_phases else "Sequence"
        # 4. duvarı delen, gözlemci mesajları
        self.observer_messages = [
            "[OBSERVER] keep your hands off the keyboard. signal already bound.",
            "[OBSERVER] clicks are just metronome noise. we listen in silence.",
            f"[OBSERVER] {self.system_data.get('username', 'user')}, do you feel someone reading over your shoulder?",
            f"[OBSERVER] mirrors opened on {self.system_data.get('hostname', 'TARGET').upper()}. you are the reflection.",
            "[OBSERVER] payload lives after the screen goes dark.",
            "[OBSERVER] this is not real hacking. but it is real watching."
        ]

    def compose_script(self, phases):
        """Faz senaryolarını zaman çizgisine dök"""
        timeline = []
        statuses = []
        for phase in phases:
            label = f"{phase.get('name', 'PHASE')} | {phase.get('status', '')}"
            for entry in phase.get('logs', []):
                timeline.append(entry)
                statuses.append(label)
        return timeline, statuses
    
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

        controls_frame = tk.Frame(header_frame, bg=BACKGROUND_COLOR)
        controls_frame.pack(fill='x')
        # Alt başlık
        subtitle_label = tk.Label(
            controls_frame,
            text=f"Compromising {self.system_data.get('os', 'Unknown System')} | User: {self.system_data.get('username', 'Unknown')}",
            fg=SECONDARY_TEXT,
            bg=BACKGROUND_COLOR,
            font=("Consolas", 12)
        )
        subtitle_label.pack(side='left')
        self.operation_label = tk.Label(
            controls_frame,
            text=f"OP {self.operation_code} | {self.phase_count} phases",
            fg=TEXT_COLOR,
            bg=BACKGROUND_COLOR,
            font=("Consolas", 10, "bold")
        )
        self.operation_label.pack(side='left', padx=(15, 0))
        self.phase_badge = tk.Label(
            controls_frame,
            text=f"PHASE 1/{self.phase_count} | {self.current_phase_name.upper()}",
            fg=BACKGROUND_COLOR,
            bg=TEXT_COLOR,
            font=("Consolas", 9, "bold"),
            padx=8,
            pady=2
        )
        self.phase_badge.pack(side='right', padx=(0, 10))
        exit_button = tk.Button(
            controls_frame,
            text="EXIT",
            command=self.emergency_exit,
            bg=HIGHLIGHT_COLOR,
            fg="white",
            activebackground="#ff6666",
            activeforeground="white",
            bd=0,
            padx=10,
            pady=2,
            font=("Consolas", 10, "bold")
        )
        exit_button.pack(side='right')
        
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
            text=f"Target: {self.system_data.get('ip_address', '127.0.0.1')} | OP: {self.operation_code} | CPU: {self.system_data.get('cpu_usage', '0%')} | RAM: {self.system_data.get('memory_usage', '0%')}",
            fg=SECONDARY_TEXT,
            bg="#2d2d2d",
            font=("Consolas", 9)
        )
        system_status.pack(side='left', padx=20, fill='y')
        
        self.threat_label = tk.Label(
            status_frame,
            text="Threat: STEALTH",
            fg=HIGHLIGHT_COLOR,
            bg="#2d2d2d",
            font=("Consolas", 9, "bold")
        )
        self.threat_label.pack(side='right', padx=10, fill='y')
        
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

    def schedule(self, delay_ms, callback):
        """after çağrılarını takip ederek güvenli planlama"""
        if self.shutdown_flag:
            return None
        job = self.root.after(delay_ms, callback)
        self.after_jobs.append(job)
        return job

    def cancel_scheduled_tasks(self):
        """Çalışan after görevlerini temizle"""
        for job in list(self.after_jobs):
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        self.after_jobs.clear()
    
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
            if self.shutdown_flag or not self.ui_active:
                return
            if not self.live_text.winfo_exists():
                return

            # Güncel sistem verilerini al
            current_cpu = psutil.cpu_percent(interval=0.0)
            current_memory = psutil.virtual_memory().percent
            elapsed = int(time.time() - self.sequence_started_at) if self.sequence_started_at else 0
            active_phase = "INIT"
            if getattr(self, "operation_phases", None):
                active_phase = self.operation_phases[self.current_phase_index].get("name", "PHASE")
            staged_mb = 180 + int(self.sim_progress * 720)
            
            # Network bağlantıları
            connections = RealSystemInfo.get_network_connections()
            
            # Top processes
            top_processes = RealSystemInfo.get_running_processes()[:10]
            
            # Canlı veri metnini oluştur
            live_data = "=== REAL-TIME MONITORING ===\n"
            live_data += f"OP: {self.operation_code} | Phase: {active_phase} | Runtime: {elapsed}s\n"
            live_data += f"Operation Progress: {int(self.sim_progress * 100)}%\n"
            live_data += f"Data siphon staged: {staged_mb} MB\n\n"
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
            
            live_data += "\n=== ACTIVE ALERTS ===\n"
            live_data += f"Intrusion channel: {'encrypted' if random.random() > 0.3 else 'muted for stealth'}\n"
            live_data += f"User presence: {'detected' if random.random() > 0.5 else 'idle'}\n"
            
            # Güncelle
            self.live_text.config(state='normal')
            self.live_text.delete(1.0, tk.END)
            self.live_text.insert(tk.END, live_data)
            self.live_text.config(state='disabled')
            
        except Exception as e:
            print(f"Canlı veri güncellemesi hatası: {e}")
        
        # 1.5 saniyede bir güncelle
        self.schedule(1500, self.update_live_data)
    
    def update_clock(self):
        """Saati güncelle"""
        if self.shutdown_flag or not self.ui_active:
            return
        if not self.time_label.winfo_exists():
            return
        current_time = time.strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        self.schedule(1000, self.update_clock)
    
    def block_input(self, event):
        """Kullanıcı girdilerini engelle"""
        return "break"
    
    def toggle_fullscreen(self, event=None):
        """F11 ile tam ekran aç/kapa"""
        self.config.fullscreen = not self.config.fullscreen
        self.root.attributes("-fullscreen", self.config.fullscreen)
        self.root.config(cursor="none" if self.config.fullscreen else "arrow")
        return "break"
    
    def emergency_exit(self, event=None):
        """Acil çıkış"""
        if self.shutdown_flag:
            return
        self.shutdown_flag = True
        self.ui_active = False
        self.cancel_scheduled_tasks()
        if hasattr(self, 'auto_close_timer') and self.auto_close_timer:
            try:
                self.root.after_cancel(self.auto_close_timer)
            except Exception:
                pass
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
        self.sim_progress = 0.0
        self.current_phase_index = 0
        self.sequence_started_at = time.time()
        self.hack_thread = threading.Thread(target=self.hack_sequence, daemon=True)
        self.hack_thread.start()
        self.schedule_whispers()
        
        # Otomatik kapanma
        total_wait_ms = int((self.config.auto_close + self.sim_duration) * 1000)
        self.auto_close_timer = self.schedule(total_wait_ms, self.emergency_exit)
    
    def hack_sequence(self):
        """Ana hack sıralaması - gerçek sistem verileriyle"""
        start_time = time.time()
        log_index = 0
        
        while log_index < len(self.logs):
            elapsed = time.time() - start_time
            progress = min(elapsed / self.sim_duration, 1)
            self.sim_progress = progress
            
            # İlerleme güncelle
            self.progress_bar['value'] = progress * 100
            self.progress_percent.config(text=f"{int(progress * 100)}%")
            
            # Faz bazlı ilerleme etiketi
            if self.phase_count:
                phase_idx = min(int(progress * self.phase_count), self.phase_count - 1)
                if phase_idx != self.current_phase_index:
                    self.current_phase_index = phase_idx
                phase = self.operation_phases[self.current_phase_index]
                self.current_phase_name = phase.get("name", "PHASE")
                phase_label = f"{phase.get('name', 'PHASE')} - {phase.get('status', '')}"
                self.progress_label.config(text=phase_label)
                if hasattr(self, "phase_badge"):
                    self.phase_badge.config(text=f"PHASE {self.current_phase_index + 1}/{self.phase_count} | {self.current_phase_name.upper()}")
                if hasattr(self, "threat_label"):
                    threat_levels = ["STEALTH", "BREACH", "PIVOT", "EXFIL", "LOCKDOWN"]
                    threat_text = threat_levels[min(self.current_phase_index, len(threat_levels) - 1)]
                    self.threat_label.config(text=f"Threat: {threat_text}")
            else:
                if progress < 0.3:
                    self.progress_label.config(text="Scanning target system...")
                elif progress < 0.6:
                    self.progress_label.config(text="Exploiting vulnerabilities...")
                elif progress < 0.9:
                    self.progress_label.config(text="Installing backdoors...")
                else:
                    self.progress_label.config(text="Finalizing system compromise...")
            
            # Yeni log ekleme zamanı
            if log_index < len(self.logs) and elapsed > log_index * (self.sim_duration / len(self.logs)):
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
        self.add_terminal_line(f"Channel {self.operation_code} now persistent. Visual distortion on standby.", color=HIGHLIGHT_COLOR)
        self.status_label.config(text=f"Full control of {self.system_data.get('hostname', 'target')} achieved")
        self.progress_label.config(text="System compromise completed successfully!")
        self.sim_progress = 1.0
        
        # 3 saniye bekle sonra pixel savaşını başlat
        time.sleep(3)
        if self.config.enable_pixel_war:
            self.start_pixel_war()
        else:
            self.schedule(1500, self.emergency_exit)
    
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

    def typewriter_terminal(self, text, color=HIGHLIGHT_COLOR, speed=24):
        """Terminale yavaş akan satır ekle"""
        if self.shutdown_flag or not getattr(self, "terminal_text", None):
            return
        if not self.terminal_text.winfo_exists():
            return
        timestamp = time.strftime("[%H:%M:%S] ")
        self.terminal_text.config(state='normal')
        self.terminal_text.insert(tk.END, timestamp, "timestamp")
        self.terminal_text.tag_configure("observer", foreground=color)
        self.terminal_text.tag_configure("timestamp", foreground=SECONDARY_TEXT)
        self.terminal_text.config(state='disabled')

        def step(i=0):
            if self.shutdown_flag or not self.terminal_text.winfo_exists():
                return
            self.terminal_text.config(state='normal')
            self.terminal_text.insert(tk.END, text[i], "observer")
            self.terminal_text.config(state='disabled')
            self.terminal_text.see(tk.END)
            if i + 1 < len(text):
                self.schedule(speed, lambda: step(i + 1))
            else:
                self.terminal_text.config(state='normal')
                self.terminal_text.insert(tk.END, "\n")
                self.terminal_text.config(state='disabled')

        step()

    def schedule_whispers(self):
        """Gözlemci mesajlarını zamanlayarak terminale bırak"""
        if not getattr(self, "observer_messages", None):
            return
        base = 8000
        gap = 9500
        for idx, msg in enumerate(self.observer_messages):
            delay = base + idx * gap
            self.schedule(delay, lambda m=msg: self.typewriter_terminal(m, HIGHLIGHT_COLOR, speed=26))
    
    def start_pixel_war(self):
        """Pixel savaşı efektini başlat"""
        if self.shutdown_flag:
            return
        self.ui_active = False
        self.cancel_scheduled_tasks()

        # Mevcut arayüzü gizle
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Masastü decoy için ekran görüntüsü
        self.desktop_photo = None
        try:
            grab = ImageGrab.grab()
            grab = grab.resize((self.root.winfo_screenwidth(), self.root.winfo_screenheight()))
            self.desktop_photo = ImageTk.PhotoImage(grab)
        except Exception:
            self.desktop_photo = None
        
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
        self.pixel_size = max(3, self.config.pixel_size)
        self.pixels = []
        self.war_active = True
        self.war_tick_ms = max(30, self.config.war_tick_ms)
        self.battle_round_limit = 360 if self.config.glitch_mode else 240
        self.grid_width = max(1, self.screen_width // self.pixel_size)
        self.grid_height = max(1, self.screen_height // self.pixel_size)
        
        # İki farklı renk ordusu
        self.colors = {
            'red_army': ['#ff0000', '#ff3333', '#ff6666', '#cc0000', '#990000'],
            'blue_army': ['#0000ff', '#3333ff', '#6666ff', '#0000cc', '#000099'],
            'green_army': ['#00ff00', '#33ff33', '#66ff66', '#00cc00', '#009900'],
            'chaos': ['#ffffff', '#ffff00', '#ff00ff', '#00ffff'],
            'glitch': ['#00ff41', '#33ffaa', '#ff0080', '#ffffff', '#00ccff', '#ffcc00']
        }
        
        # Decoy sahne veya doğrudan glitch
        if self.desktop_photo:
            self.show_desktop_decoy()
        else:
            self.show_war_message()
            self.root.after(1200, self.initialize_armies)
            self.root.after(1200, self.start_overlay_script)

    def show_desktop_decoy(self):
        """Ekran düzelmiş gibi masaüstü görüntüsü göster, sonra bozulma başlat"""
        if self.shutdown_flag or not getattr(self, "desktop_photo", None):
            self.show_war_message()
            self.root.after(1200, self.initialize_armies)
            self.start_overlay_script()
            return
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.desktop_photo, anchor='nw', tags='desktop')
        self.canvas.create_rectangle(
            0, 0, self.screen_width, 28,
            fill="#000000", outline="", tags="desktop"
        )
        self.canvas.create_text(
            10, 14,
            text="Secure Desktop - restoring...",
            fill="#00ff41",
            font=("Consolas", 11, "bold"),
            anchor="w",
            tags="desktop"
        )
        self.schedule(900, self.glitch_decoy)
        self.schedule(1700, self.show_war_message)
        self.schedule(2400, self.initialize_armies)
        self.schedule(2400, self.start_overlay_script)

    def glitch_decoy(self):
        """Masaüstü üstüne kısa glitch taraması"""
        if self.shutdown_flag or not getattr(self, "canvas", None):
            return
        sweeps = 60
        for _ in range(sweeps):
            x1 = 0
            x2 = self.screen_width
            y = random.randint(0, self.screen_height)
            thickness = random.randint(3, 14)
            color = random.choice(self.colors['glitch'])
            self.canvas.create_rectangle(x1, y, x2, y + thickness, fill=color, outline='', tags='decoy_glitch')
        blocks = 220
        for _ in range(blocks):
            gx = random.randint(0, self.grid_width - 1)
            gy = random.randint(0, self.grid_height - 1)
            color = random.choice(self.colors['glitch'])
            x1 = gx * self.pixel_size
            y1 = gy * self.pixel_size
            self.canvas.create_rectangle(x1, y1, x1 + self.pixel_size, y1 + self.pixel_size, fill=color, outline='', tags='decoy_glitch')
    
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

    def start_overlay_script(self):
        """Glitch sonrası yavaş akan, 4. duvarı delen metinler"""
        if self.shutdown_flag:
            return
        host = self.system_data.get('hostname', 'TARGET').upper()
        user = self.system_data.get('username', 'user')
        overlay_script = [
            {"delay": 4200, "text": f"we are inside {host}", "color": "#ff5555", "y": self.screen_height//2 + 120},
            {"delay": 7200, "text": "stop moving the mouse. it does not help.", "color": "#ffaaaa", "y": self.screen_height//2 + 170},
            {"delay": 9800, "text": f"{user}, why are you still watching?", "color": "#ffeeaa", "y": self.screen_height//2 + 220},
            {"delay": 12800, "text": "we keep what we want. you keep the noise.", "color": "#ff5555", "y": self.screen_height//2 + 270},
            {"delay": 15600, "text": "the glitch is not the attack. it is the cover.", "color": "#ffcccc", "y": self.screen_height//2 + 320},
            {"delay": 18600, "text": "screen may go white. that is when we finish.", "color": "#ffffff", "y": self.screen_height//2 + 380},
        ]
        for item in overlay_script:
            self.schedule(item["delay"], lambda msg=item: self.typewriter_overlay(msg))

    def typewriter_overlay(self, msg):
        """Canvas üstünde yavaş yazı efekti"""
        if self.shutdown_flag or not getattr(self, "canvas", None):
            return
        text = msg.get("text", "")
        color = msg.get("color", "#ff5555")
        y_pos = msg.get("y", self.screen_height // 2)
        font = msg.get("font", ("Consolas", 18, "bold"))
        speed = msg.get("speed", 35)
        fade = msg.get("fade", 2000)

        text_id = self.canvas.create_text(
            self.screen_width // 2,
            y_pos,
            text="",
            fill=color,
            font=font,
            tags="overlay"
        )

        def step(i=0):
            if self.shutdown_flag or not self.canvas.winfo_exists():
                return
            self.canvas.itemconfig(text_id, text=text[:i])
            if i < len(text):
                self.schedule(speed, lambda: step(i + 1))
            else:
                self.schedule(fade, lambda: self.canvas.delete(text_id))

        step()
    
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
        
        if self.config.glitch_mode:
            # Glitch modu: ekranın tamamına rastgele gürültü
            glitch_pixels = []
            density = 0.22
            for x in range(self.grid_width):
                for y in range(self.grid_height):
                    if random.random() < density:
                        pixel_id = self.create_pixel(x, y, random.choice(self.colors['glitch']))
                        glitch_pixels.append({'id': pixel_id, 'x': x, 'y': y, 'army': 'glitch'})
            self.armies = {'glitch': glitch_pixels}
        else:
            # Kırmızı ordu (sol taraf)
            red_pixels = []
            for x in range(0, self.grid_width // 4):
                for y in range(self.grid_height):
                    if random.random() < 0.18:  # Daha dengeli yoğunluk
                        pixel_id = self.create_pixel(x, y, random.choice(self.colors['red_army']))
                        red_pixels.append({'id': pixel_id, 'x': x, 'y': y, 'army': 'red'})
            
            # Mavi ordu (sağ taraf)
            blue_pixels = []
            for x in range(3 * self.grid_width // 4, self.grid_width):
                for y in range(self.grid_height):
                    if random.random() < 0.18:  # Daha dengeli yoğunluk
                        pixel_id = self.create_pixel(x, y, random.choice(self.colors['blue_army']))
                        blue_pixels.append({'id': pixel_id, 'x': x, 'y': y, 'army': 'blue'})
            
            # Yeşil ordu (merkez üst)
            green_pixels = []
            for x in range(self.grid_width // 3, 2 * self.grid_width // 3):
                for y in range(0, self.grid_height // 4):
                    if random.random() < 0.12:  # Daha seyrek yoğunluk
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
        if self.shutdown_flag:
            return
        if not self.war_active or self.battle_round > self.battle_round_limit:
            self.end_war()
            return
            
        if self.config.glitch_mode:
            self.run_glitch_frame()
        else:
            # Her ordu için hareket et
            for army_name, army_pixels in self.armies.items():
                self.move_army(army_name, army_pixels)
            
            # Çatışmaları kontrol et
            self.handle_conflicts()
            
            # Rastgele kaos pixelleri ekle
            if random.random() < 0.08:
                self.spawn_chaos_pixels()
        
        # Sonraki tur
        self.battle_round += 1
        self.root.after(self.war_tick_ms, self.start_battle)
    
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
        if self.shutdown_flag or not self.war_active:
            return
        for _ in range(random.randint(6, 18)):
            x = random.randint(0, self.grid_width - 1)
            y = random.randint(0, self.grid_height - 1)
            
            if (x, y) not in self.pixel_grid:
                color = random.choice(self.colors['chaos'])
                self.create_pixel(x, y, color)

    def run_glitch_frame(self):
        """Glitch/karıncalanma efekti uygula"""
        if self.shutdown_flag or not self.war_active:
            return
        # Rastgele satırları invert/flicker et
        for _ in range(8):
            x1 = 0
            x2 = self.screen_width
            y = random.randint(0, self.screen_height)
            thickness = random.randint(1, 6)
            color = random.choice(self.colors['glitch'])
            self.canvas.create_rectangle(x1, y, x2, y + thickness, fill=color, outline='', tags='scan')
        # Rastgele blok gürültü
        for _ in range(150):
            gx = random.randint(0, self.grid_width - 1)
            gy = random.randint(0, self.grid_height - 1)
            color = random.choice(self.colors['glitch'])
            self.create_pixel(gx, gy, color)
        # Gürültüyü sınırlı tutmak için eski pixelleri temizle
        if len(self.canvas.find_withtag('pixel')) > 12000:
            self.canvas.delete(random.choice(self.canvas.find_withtag('pixel')))
    
    def end_war(self):
        """Savaşı bitir"""
        if self.shutdown_flag:
            return
        self.war_active = False
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
        # 4. duvar notu
        self.canvas.create_text(
            self.screen_width//2, self.screen_height//2 + 80,
            text="we kept the signal. you keep the screen.",
            fill='#ff0000',
            font=('Consolas', 18, 'bold'),
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
        
        parser = argparse.ArgumentParser(description="System Hack Simulator (visual only)")
        parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="Main simulation duration seconds")
        parser.add_argument("--auto-close", type=int, default=DEFAULT_AUTO_CLOSE, dest="auto_close", help="Extra wait before closing after pixel war")
        parser.add_argument("--no-fullscreen", action="store_true", help="Run windowed instead of fullscreen")
        parser.add_argument("--no-pixel-war", action="store_true", help="Skip pixel war finale")
        parser.add_argument("--block-input", action="store_true", help="Block all keyboard/mouse input except ESC")
        parser.add_argument("--pixel-size", type=int, default=5, help="Pixel size for war effect")
        parser.add_argument("--war-tick", type=int, default=60, help="Tick interval (ms) for pixel war updates")
        args = parser.parse_args()

        config = SimulatorConfig(
            duration=max(5, args.duration),
            auto_close=max(0, args.auto_close),
            fullscreen=not args.no_fullscreen,
            enable_pixel_war=not args.no_pixel_war,
            block_input=args.block_input,
            pixel_size=max(2, args.pixel_size),
            war_tick_ms=max(20, args.war_tick),
        )

        root = tk.Tk()
        app = HackSimulator(root, config)
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
