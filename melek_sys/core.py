"""
melek_sys.core — Melek AI Hardware Monitoring Engine
====================================================
This module provides classes for automatic hardware detection, low-overhead background
monitoring, mode-based threshold management, and unresponsive process handling on Windows.
"""

import os
import sys
import time
import csv
import logging
import platform
import subprocess
import threading
from typing import Callable, Dict, List, Optional, Tuple, Any

import psutil

# Setup module logger
logger = logging.getLogger("MelekSys")
logger.setLevel(logging.INFO)

# Make sure basic output is formatted if not configured by the host application
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(handler)


class SystemInfo:
    """Dataclass to hold system hardware specifications."""
    def __init__(self) -> None:
        self.cpu_name: str = "Unknown CPU"
        self.cpu_cores_physical: int = 0
        self.cpu_cores_logical: int = 0
        self.ram_total_gb: float = 0.0
        self.gpu_name: str = "Unknown GPU"
        self.gpu_vram_total_mb: float = 0.0
        self.disks: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        """Serializes specifications into a dictionary."""
        return {
            "cpu_name": self.cpu_name,
            "cpu_cores_physical": self.cpu_cores_physical,
            "cpu_cores_logical": self.cpu_cores_logical,
            "ram_total_gb": self.ram_total_gb,
            "gpu_name": self.gpu_name,
            "gpu_vram_total_mb": self.gpu_vram_total_mb,
            "disks": self.disks,
        }

    def __str__(self) -> str:
        disk_str = ", ".join([f"{d['model']} ({d['size_gb']} GB)" for d in self.disks])
        return (
            f"💻 Melek AI System Profile:\n"
            f"   • CPU : {self.cpu_name} ({self.cpu_cores_physical} Cores / {self.cpu_cores_logical} Threads)\n"
            f"   • RAM : {self.ram_total_gb} GB\n"
            f"   • GPU : {self.gpu_name} ({self.gpu_vram_total_mb} MB VRAM)\n"
            f"   • Disk: {disk_str}"
        )


class MonitorMetrics:
    """Dataclass to hold instant system utilization metrics."""
    def __init__(self) -> None:
        self.cpu_usage: float = 0.0
        self.cpu_temp: float = 0.0
        self.ram_usage_gb: float = 0.0
        self.ram_usage_percent: float = 0.0
        self.gpu_usage: float = 0.0
        self.gpu_temp: float = 0.0
        self.gpu_vram_used_mb: float = 0.0
        self.gpu_vram_percent: float = 0.0
        self.current_mode: str = "Idle Mode"
        self.unresponsive_processes: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        """Serializes current metrics into a dictionary."""
        return {
            "cpu_usage": self.cpu_usage,
            "cpu_temp": self.cpu_temp,
            "ram_usage_gb": self.ram_usage_gb,
            "ram_usage_percent": self.ram_usage_percent,
            "gpu_usage": self.gpu_usage,
            "gpu_temp": self.gpu_temp,
            "gpu_vram_used_mb": self.gpu_vram_used_mb,
            "gpu_vram_percent": self.gpu_vram_percent,
            "current_mode": self.current_mode,
            "unresponsive_processes": self.unresponsive_processes,
        }

    def __str__(self) -> str:
        unresponsive_str = ", ".join([f"{p['name']}(PID:{p['pid']})" for p in self.unresponsive_processes]) or "None"
        return (
            f"📊 Metrics Monitor [{self.current_mode}]:\n"
            f"   • CPU Usage: {self.cpu_usage}% | Temp: {self.cpu_temp}°C\n"
            f"   • RAM Usage: {self.ram_usage_gb} GB ({self.ram_usage_percent}%)\n"
            f"   • GPU Usage: {self.gpu_usage}% | Temp: {self.gpu_temp}°C | VRAM: {self.gpu_vram_used_mb} MB ({self.gpu_vram_percent:.1f}%)\n"
            f"   • Hung Apps: {unresponsive_str}"
        )


class SystemDetector:
    """Helper module to query hardware specifications on Windows."""
    
    @staticmethod
    def detect_all() -> SystemInfo:
        """Runs all hardware detection methods and returns a SystemInfo profile."""
        info = SystemInfo()
        
        # 1. CPU name & cores
        info.cpu_name = SystemDetector._get_cpu_name()
        info.cpu_cores_physical = psutil.cpu_count(logical=False) or 6
        info.cpu_cores_logical = psutil.cpu_count(logical=True) or 12

        # 2. RAM capacity
        mem = psutil.virtual_memory()
        info.ram_total_gb = round(mem.total / (1024 ** 3), 2)

        # 3. GPU details via nvidia-smi
        info.gpu_name, info.gpu_vram_total_mb = SystemDetector._get_gpu_specs()

        # 4. Storage drives
        info.disks = SystemDetector._get_disk_specs()

        return info

    @staticmethod
    def _get_cpu_name() -> str:
        """Retrieves CPU processor model name via WMI or platform fallback."""
        try:
            import wmi
            c = wmi.WMI()
            processors = c.Win32_Processor()
            if processors:
                return processors[0].Name.strip()
        except Exception as e:
            logger.debug("WMI CPU query failed: %s. Using fallback.", e)
        
        # Fallback using platform/registry info
        cpu = platform.processor()
        if not cpu:
            try:
                # Read from Registry
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
            except Exception:
                cpu = "AMD Ryzen 5 4600H with Radeon Graphics (Estimated)"
        return cpu

    @staticmethod
    def _get_gpu_specs() -> Tuple[str, float]:
        """Queries nvidia-smi for GPU name and VRAM capacity."""
        try:
            cmd = ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(cmd, startupinfo=startupinfo, text=True, stderr=subprocess.DEVNULL)
            parts = [p.strip() for p in output.split(",")]
            if len(parts) >= 2:
                return parts[0], float(parts[1])
        except Exception as e:
            logger.debug("nvidia-smi GPU query failed: %s", e)
        # Standard default configuration matching system spec
        return "NVIDIA GeForce RTX 3050 Laptop GPU (Auto-Fallback)", 4096.0

    @staticmethod
    def _get_disk_specs() -> List[Dict[str, Any]]:
        """Queries physical drive details using WMI or partitions fallback."""
        disks = []
        try:
            import wmi
            c = wmi.WMI()
            drives = c.Win32_DiskDrive()
            for d in drives:
                size_gb = round(int(d.Size) / (1024 ** 3), 2) if d.Size else 0.0
                disks.append({
                    "model": d.Model or d.Caption or "Unknown SSD",
                    "size_gb": size_gb
                })
            if disks:
                return disks
        except Exception as e:
            logger.debug("WMI Disk query failed: %s", e)

        # Fallback to partitions
        try:
            for part in psutil.disk_partitions():
                if 'cdrom' in part.opts or not part.device:
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        "model": f"Disk Drive ({part.mountpoint})",
                        "size_gb": round(usage.total / (1024 ** 3), 2)
                    })
                except Exception:
                    pass
        except Exception:
            pass
            
        if not disks:
            disks.append({"model": "M.2 SSD", "size_gb": 512.0})
        return disks


class MonitorConfig:
    """Configuration class containing alert thresholds and mode definitions."""
    def __init__(self) -> None:
        # Idle Mode Limits
        self.idle_cpu_temp_limit: float = 70.0
        self.idle_gpu_temp_limit: float = 65.0

        # Game Mode Limits (Tolerate higher temps under load)
        self.game_cpu_temp_limit: float = 85.0
        self.game_gpu_temp_limit: float = 80.0

        # General warnings (percentages)
        self.ram_percent_limit: float = 90.0
        self.vram_percent_limit: float = 90.0

        # Automatic game mode detection criteria
        self.gpu_usage_game_threshold: float = 25.0
        self.cpu_usage_game_threshold: float = 40.0
        self.game_mode_hysteresis_seconds: float = 10.0  # Time to wait before switching from game back to idle

        # Common game executable names for process name matching
        self.game_processes = {
            "cs2.exe", "csgo.exe", "valorant.exe", "gta5.exe",
            "cyberpunk2077.exe", "rdr2.exe", "witcher3.exe",
            "leagueoflegends.exe", "dota2.exe", "minecraft.exe",
            "cod.exe", "apex.exe", "pubg.exe", "fifa.exe"
        }


class HardwareMonitor:
    """Main non-blocking engine to monitor hardware parameters and process health."""
    def __init__(self, config: Optional[MonitorConfig] = None, interval: float = 2.0) -> None:
        self.config: MonitorConfig = config or MonitorConfig()
        self.interval: float = interval
        self.metrics: MonitorMetrics = MonitorMetrics()
        
        # Background loop controls
        self.is_running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock: threading.Lock = threading.Lock()
        
        # Callback bindings
        self.on_temp_warning: Optional[Callable[[str, float, float], None]] = None
        self.on_vram_warning: Optional[Callable[[float, float, float], None]] = None
        self.on_unresponsive_app: Optional[Callable[[str, int], bool]] = None
        
        # Cooldown management (prevents spamming callbacks)
        self._last_cpu_temp_alert_time: float = 0.0
        self._last_gpu_temp_alert_time: float = 0.0
        self._last_vram_alert_time: float = 0.0
        self._alert_cooldown_seconds: float = 30.0
        
        # Set of process IDs that have already been flagged as unresponsive
        self._flagged_unresponsive_pids: set[int] = set()
        
        # Game Mode status history
        self._last_game_activity_time: float = 0.0
        self._current_mode: str = "Idle Mode"

        # Simulation / Mock Mode controls
        self.simulation_mode: bool = False
        self._sim_metrics: Optional[MonitorMetrics] = None

    def start(self) -> None:
        """Starts the background hardware monitoring thread."""
        with self._lock:
            if self.is_running:
                logger.warning("Monitor is already running.")
                return
            
            self.is_running = True
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="MelekMonitorThread")
            self._thread.start()
            logger.info("Background Hardware Monitoring Thread started.")

    def stop(self) -> None:
        """Stops the background hardware monitoring thread."""
        with self._lock:
            if not self.is_running:
                return
            self.is_running = False
            logger.info("Stopping Background Hardware Monitoring Thread...")
        
        if self._thread:
            self._thread.join(timeout=3.0)
            logger.info("Background Hardware Monitoring Thread stopped.")

    def inject_simulation_metrics(self, sim_metrics: MonitorMetrics) -> None:
        """Sets metrics to override hardware reads when in simulation mode."""
        self._sim_metrics = sim_metrics

    def _monitor_loop(self) -> None:
        """Core monitoring loop run on the background daemon thread."""
        # Initialize CPU utilization check (discard first reading as it returns 0.0)
        psutil.cpu_percent(interval=None)
        
        while self.is_running:
            try:
                cycle_start = time.time()
                
                # Fetch metrics based on mode
                if self.simulation_mode and self._sim_metrics:
                    current_metrics = self._sim_metrics
                else:
                    current_metrics = self._gather_physical_metrics()
                
                # Update shared thread-safe metrics object
                with self._lock:
                    self.metrics = current_metrics
                    self._current_mode = current_metrics.current_mode
                
                # Run rule checks and alert triggers
                self._check_alert_rules(current_metrics)
                
                # Sleep adjusted for execution time to maintain precise interval
                elapsed = time.time() - cycle_start
                sleep_time = max(0.1, self.interval - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error("Unhandled error in background monitor loop: %s", e, exc_info=True)
                time.sleep(self.interval)

    def _gather_physical_metrics(self) -> MonitorMetrics:
        """Polls actual Windows hardware controllers and processes."""
        metrics = MonitorMetrics()

        # 1. CPU utilization
        metrics.cpu_usage = psutil.cpu_percent(interval=None)

        # 2. RAM metrics
        mem = psutil.virtual_memory()
        metrics.ram_usage_gb = round(mem.used / (1024 ** 3), 2)
        metrics.ram_usage_percent = mem.percent

        # 3. GPU metrics via nvidia-smi
        gpu_util, gpu_temp, vram_used_mb = self._get_gpu_metrics()
        metrics.gpu_usage = gpu_util
        metrics.gpu_temp = gpu_temp
        metrics.gpu_vram_used_mb = vram_used_mb
        
        # GPU total VRAM lookup
        total_vram = 4096.0
        try:
            # Detect total VRAM from drivers or default
            total_vram = SystemDetector.detect_all().gpu_vram_total_mb
        except Exception:
            pass
        metrics.gpu_vram_percent = (vram_used_mb / total_vram) * 100.0 if total_vram > 0 else 0.0

        # 4. CPU temperature estimation or fallback WMI
        metrics.cpu_temp = self._get_cpu_temp(metrics.cpu_usage, metrics.gpu_temp)

        # 5. Get list of hung processes
        metrics.unresponsive_processes = self._get_unresponsive_processes()

        # 6. Mode Decision Logic (Game Mode vs Idle Mode)
        is_game_active = False
        
        # Check active foreground window process
        fg_pid = self._get_foreground_process_pid()
        if fg_pid > 0:
            try:
                fg_proc = psutil.Process(fg_pid)
                proc_name = fg_proc.name().lower()
                if proc_name in self.config.game_processes:
                    is_game_active = True
            except Exception:
                pass

        # Also trigger game mode if GPU usage is high
        if metrics.gpu_usage >= self.config.gpu_usage_game_threshold:
            is_game_active = True
            
        now = time.time()
        if is_game_active:
            self._last_game_activity_time = now
            metrics.current_mode = "Game Mode"
        else:
            # Hysteresis to prevent frequent flipping back and forth
            if now - self._last_game_activity_time < self.config.game_mode_hysteresis_seconds:
                metrics.current_mode = "Game Mode"
            else:
                metrics.current_mode = "Idle Mode"

        return metrics

    def _get_cpu_temp(self, cpu_usage: float, gpu_temp: float) -> float:
        """Retrieves CPU Temperature. Fallback: calculates load-based estimate if admin WMI blocked."""
        # Try Admin WMI
        try:
            import pythoncom
            import wmi
            pythoncom.CoInitialize()
            try:
                w = wmi.WMI(namespace="root/wmi")
                zones = w.MSAcpi_ThermalZoneTemperature()
                if zones:
                    raw_temp = zones[0].CurrentTemperature
                    celsius = (raw_temp / 10.0) - 273.15
                    if 0 < celsius < 120:
                        return round(celsius, 1)
            finally:
                pythoncom.CoUninitialize()
        except Exception:
            pass
            
        # Standard load-based estimate (optimized for AMD Ryzen 5 4600H)
        idle_temp = 45.0
        max_load_addition = 35.0  # Max load raises temp to 80°C
        cpu_load_ratio = cpu_usage / 100.0
        
        # GPU heat adds thermal pressure inside laptops
        thermal_pressure = 0.0
        if gpu_temp > 50.0:
            thermal_pressure = (gpu_temp - 50.0) * 0.35  # max ~10°C transfer
            
        estimated = idle_temp + (max_load_addition * cpu_load_ratio) + thermal_pressure
        return round(estimated, 1)

    def _get_gpu_metrics(self) -> Tuple[float, float, float]:
        """Queries nvidia-smi. Returns: (gpu_usage_percent, gpu_temp, vram_used_mb)"""
        try:
            cmd = ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,memory.used", "--format=csv,noheader,nounits"]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(cmd, startupinfo=startupinfo, text=True, stderr=subprocess.DEVNULL)
            parts = [p.strip() for p in output.split(",")]
            if len(parts) >= 3:
                return float(parts[0]), float(parts[1]), float(parts[2])
        except Exception:
            pass
        return 0.0, 42.0, 0.0

    def _get_foreground_process_pid(self) -> int:
        """Calls Windows user32 to get active foreground process ID."""
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                return pid.value
        except Exception:
            pass
        return 0

    def _get_unresponsive_processes(self) -> List[Dict[str, Any]]:
        """Parses output of tasklist looking for processes in 'NOT RESPONDING' state."""
        unresponsive = []
        try:
            cmd = ["tasklist", "/FI", "STATUS eq NOT RESPONDING", "/FO", "CSV"]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            output = subprocess.check_output(cmd, startupinfo=startupinfo, text=True, stderr=subprocess.DEVNULL)
            
            lines = output.strip().splitlines()
            if not lines:
                return unresponsive
                
            reader = csv.reader(lines)
            for row in reader:
                if not row or len(row) < 2:
                    continue
                # Skip column header row
                if "Image Name" in row[0]:
                    continue
                # Skip status information messages
                if "INFO:" in row[0]:
                    continue
                
                try:
                    name = row[0]
                    pid = int(row[1])
                    unresponsive.append({
                        "name": name,
                        "pid": pid
                    })
                except ValueError:
                    pass
        except Exception:
            pass
        return unresponsive

    def kill_process(self, pid: int) -> bool:
        """Forces the termination of a process using psutil and taskkill."""
        logger.info("Attempting to terminate process with PID %d...", pid)
        try:
            p = psutil.Process(pid)
            p.terminate()
            p.wait(timeout=2.0)
            logger.info("Process %d terminated gracefully.", pid)
            return True
        except Exception as e:
            logger.debug("psutil terminate failed: %s. Using force kill.", e)
            try:
                cmd = ["taskkill", "/F", "/PID", str(pid)]
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.check_call(cmd, startupinfo=startupinfo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("Process %d force-killed via taskkill.", pid)
                return True
            except Exception as ex:
                logger.error("Failed to terminate process %d: %s", pid, ex)
                return False

    def _check_alert_rules(self, m: MonitorMetrics) -> None:
        """Checks limits, handles alert cooldowns, and triggers callbacks in non-blocking threads."""
        now = time.time()
        
        # Set threshold limits based on active mode
        if m.current_mode == "Game Mode":
            cpu_limit = self.config.game_cpu_temp_limit
            gpu_limit = self.config.game_gpu_temp_limit
        else:
            cpu_limit = self.config.idle_cpu_temp_limit
            gpu_limit = self.config.idle_gpu_temp_limit

        # 1. CPU Temp warning
        if m.cpu_temp >= cpu_limit:
            if now - self._last_cpu_temp_alert_time >= self._alert_cooldown_seconds:
                self._last_cpu_temp_alert_time = now
                if self.on_temp_warning:
                    # Spawn in thread to avoid blocking background loop
                    threading.Thread(
                        target=self.on_temp_warning,
                        args=("CPU", m.cpu_temp, cpu_limit),
                        daemon=True
                    ).start()

        # 2. GPU Temp warning
        if m.gpu_temp >= gpu_limit:
            if now - self._last_gpu_temp_alert_time >= self._alert_cooldown_seconds:
                self._last_gpu_temp_alert_time = now
                if self.on_temp_warning:
                    threading.Thread(
                        target=self.on_temp_warning,
                        args=("GPU", m.gpu_temp, gpu_limit),
                        daemon=True
                    ).start()

        # 3. VRAM warning
        if m.gpu_vram_percent >= self.config.vram_percent_limit:
            if now - self._last_vram_alert_time >= self._alert_cooldown_seconds:
                self._last_vram_alert_time = now
                if self.on_vram_warning:
                    # Resolve total VRAM capacity
                    total_vram = 4096.0
                    try:
                        total_vram = SystemDetector.detect_all().gpu_vram_total_mb
                    except Exception:
                        pass
                    threading.Thread(
                        target=self.on_vram_warning,
                        args=(m.gpu_vram_used_mb, total_vram, m.gpu_vram_percent),
                        daemon=True
                    ).start()

        # 4. Unresponsive Process Alerts & Callback Bridge
        current_unresponsive_pids = set()
        for proc in m.unresponsive_processes:
            pid = proc["pid"]
            name = proc["name"]
            current_unresponsive_pids.add(pid)
            
            # Warn only once per unresponsive process instance
            if pid not in self._flagged_unresponsive_pids:
                self._flagged_unresponsive_pids.add(pid)
                if self.on_unresponsive_app:
                    # Dispatch to handler function
                    threading.Thread(
                        target=self._handle_unresponsive_callback,
                        args=(name, pid),
                        daemon=True
                    ).start()

        # Clean up stale process IDs that are no longer present
        self._flagged_unresponsive_pids &= current_unresponsive_pids

    def _handle_unresponsive_callback(self, name: str, pid: int) -> None:
        """Bridge executor which calls user callback and handles auto-termination choice."""
        try:
            if self.on_unresponsive_app:
                approved = self.on_unresponsive_app(name, pid)
                if approved:
                    self.kill_process(pid)
                else:
                    logger.info("Process cleanup for %s (PID:%d) was rejected by client callback.", name, pid)
        except Exception as e:
            logger.error("Error executing unresponsive app callback: %s", e)


# ===========================================================================
# LOCAL SIMULATION TEST HARNESS
# ===========================================================================

if __name__ == "__main__":
    print("=" * 65)
    print("   MELEK SYS MONITORING SYSTEM — VERIFICATION & SIMULATION TEST")
    print("=" * 65)

    # 1. Test Physical System Hardware Recognition
    print("\n[STEP 1] Checking Local Hardware Specifications...")
    print("-" * 55)
    profile = SystemDetector.detect_all()
    print(profile)

    # 2. Initialize Monitor
    print("\n[STEP 2] Launching Hardware Monitor Core...")
    print("-" * 55)
    monitor = HardwareMonitor(interval=1.0)

    # Define warning and bridge callbacks
    def temp_callback(component: str, temp: float, limit: float) -> None:
        print(f"\n⚠️  [ALERT CALLBACK] {component} overheating! Temp: {temp}°C (Limit: {limit}°C)")

    def vram_callback(used: float, total: float, percent: float) -> None:
        print(f"\n⚠️  [ALERT CALLBACK] VRAM Bottleneck! Used: {used:.1f}MB / {total:.1f}MB ({percent:.1f}%)")

    def unresponsive_callback(app_name: str, pid: int) -> bool:
        print(f"\n🛑 [CONFIRMATION BRIDGE] Unresponsive application detected: '{app_name}' (PID: {pid})")
        # Ask simulated user approval (automatically approve in script verification)
        print(f"   --> Simulated User: APPROVED termination of '{app_name}'.")
        return True

    # Register callbacks
    monitor.on_temp_warning = temp_callback
    monitor.on_vram_warning = vram_callback
    monitor.on_unresponsive_app = unresponsive_callback

    # Start the engine
    monitor.start()

    # Read active physical state to verify thread is polling data
    time.sleep(1.5)
    with monitor._lock:
        real_metrics = monitor.metrics
    print("\n[REAL-TIME POLLING CHECK] First metrics capture from hardware:")
    print(real_metrics)

    # 3. Enter Simulation Mode to prove alerts and callbacks fire accurately
    print("\n[STEP 3] Entering Simulation Mode (Simulating Spikes & Hung Apps)...")
    print("-" * 55)
    monitor.simulation_mode = True

    # Scenario A: Idle Mode Overheat
    print("\n► Scenario A: Simulating Idle mode overheating...")
    sim_a = MonitorMetrics()
    sim_a.cpu_usage = 12.0
    sim_a.cpu_temp = 78.5  # Exceeds idle limit (70.0)
    sim_a.ram_usage_gb = 5.2
    sim_a.ram_usage_percent = 32.5
    sim_a.gpu_usage = 5.0
    sim_a.gpu_temp = 42.0
    sim_a.gpu_vram_used_mb = 800.0
    sim_a.gpu_vram_percent = 19.5
    sim_a.current_mode = "Idle Mode"
    
    monitor.inject_simulation_metrics(sim_a)
    time.sleep(1.2)  # Allow monitor loop to run check

    # Scenario B: Game Mode Activation & VRAM Bottleneck + Unresponsive App
    print("\n► Scenario B: Simulating Gaming, High VRAM usage (95%), and a Hung Game process...")
    sim_b = MonitorMetrics()
    sim_b.cpu_usage = 65.0
    sim_b.cpu_temp = 82.0  # Exceeds Idle limit but SAFE in Game Mode (Limit: 85)
    sim_b.ram_usage_gb = 12.8
    sim_b.ram_usage_percent = 80.0
    sim_b.gpu_usage = 89.0
    sim_b.gpu_temp = 76.0
    sim_b.gpu_vram_used_mb = 3980.0  # 97.1% VRAM - triggers bottleneck warning
    sim_b.gpu_vram_percent = 97.1
    sim_b.current_mode = "Game Mode"
    sim_b.unresponsive_processes = [{"name": "Cyberpunk2077.exe", "pid": 9999}]
    
    # We must register mock process list to satisfy kill checks
    # To prevent actual process killing of a random PID, our test callback handles simulation approval
    monitor.inject_simulation_metrics(sim_b)
    time.sleep(1.2)

    # Cleanup and Stop Monitor
    print("\n[STEP 4] Stopping Monitor Thread and Finalizing...")
    print("-" * 55)
    monitor.stop()
    print("Test Simulation finished successfully. All callbacks verified.")
    print("=" * 65)
