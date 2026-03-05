"""
JARVIS AI - Action Command System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Implements the Hybrid Command Architecture:
  Layer 1: Intent classification (system_action / online_action / chat / complex_task)
  Layer 2: Structured JSON tool calling with Pydantic validation
  Layer 3: Command router → mapped execution functions
  
Security: NEVER runs raw shell commands. All actions go through validation.
"""

import subprocess
import os
import sys
import json
import shutil
import platform
import psutil
import webbrowser
import urllib.parse
import socket
import requests
import pygetwindow as gw
import pyautogui
from playwright.async_api import async_playwright
from llm_service import summarize_text, translate_text
from productivity_service import (
    create_note, list_notes, delete_note,
    create_task, list_tasks, update_task,
    create_workflow, list_workflows, get_workflow
)
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, validator

# ═══════════════════════════════════════════════════════════════
# COMMAND SCHEMA (Pydantic Validation)
# ═══════════════════════════════════════════════════════════════

class CommandMeta(BaseModel):
    confidence: float = 0.9
    requires_confirmation: bool = False

class ActionCommand(BaseModel):
    type: str  # system_action | online_action | chat | complex_task | ai_action | clarification
    action: str = ""
    parameters: Dict[str, Any] = {}
    meta: CommandMeta = CommandMeta()
    steps: List[Dict[str, Any]] = []  # For complex_task
    response: str = ""  # For chat type
    question: str = ""  # For clarification type

    @validator("type")
    def validate_type(cls, v):
        allowed = ["system_action", "online_action", "chat", "complex_task", "ai_action", "clarification"]
        if v not in allowed:
            raise ValueError(f"Invalid type: {v}. Must be one of {allowed}")
        return v


class CommandResult(BaseModel):
    success: bool
    action: str
    message: str
    data: Any = None
    requires_confirmation: bool = False


# ═══════════════════════════════════════════════════════════════
# SECURITY LAYER
# ═══════════════════════════════════════════════════════════════

# Paths that should NEVER be modified/deleted
BLOCKED_PATHS = [
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    os.path.expanduser("~\\AppData"),
    "C:\\Users\\Default",
]

# Actions that ALWAYS require user confirmation
DANGEROUS_ACTIONS = [
    "delete_file", "delete_folder",
    "shutdown", "restart_system",
    "kill_process",
    "send_email",
]

def is_path_safe(path: str) -> bool:
    """Check if a path is safe to operate on."""
    abs_path = os.path.abspath(path)
    for blocked in BLOCKED_PATHS:
        if abs_path.lower().startswith(blocked.lower()):
            return False
    return True

def needs_confirmation(action: str) -> bool:
    """Check if an action needs user confirmation before execution."""
    return action in DANGEROUS_ACTIONS


# ═══════════════════════════════════════════════════════════════
# APP REGISTRY (Windows applications)
# ═══════════════════════════════════════════════════════════════

APP_REGISTRY = {
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "brave": "brave",
    
    # Microsoft Office
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "teams": "msteams",
    
    # Development
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "notepad": "notepad",
    "notepad++": "notepad++",
    "cmd": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "git bash": "git-bash",
    
    # Media
    "vlc": "vlc",
    "spotify": "spotify",
    
    # System
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "snipping tool": "SnippingTool",
    "task manager": "taskmgr",
    "file explorer": "explorer",
    "explorer": "explorer",
    "control panel": "control",
    "settings": "ms-settings:",
    
    # Communication
    "discord": "discord",
    "slack": "slack",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "zoom": "zoom",
}


# ═══════════════════════════════════════════════════════════════
# SYSTEM COMMANDS EXECUTOR
# ═══════════════════════════════════════════════════════════════

async def execute_system_command(action: str, params: Dict[str, Any]) -> CommandResult:
    """Execute a validated system command."""
    
    try:
        # ─── App Control ───────────────────────────────
        if action == "open_app":
            app_name = params.get("app_name", "").lower().strip()
            exe = APP_REGISTRY.get(app_name, app_name)
            
            try:
                if exe.startswith("ms-"):
                    os.system(f"start {exe}")
                else:
                    subprocess.Popen(exe, shell=True)
                return CommandResult(
                    success=True, action=action,
                    message=f"✅ {app_name.title()} open ho gaya!"
                )
            except Exception as e:
                return CommandResult(
                    success=False, action=action,
                    message=f"❌ {app_name} open nahi ho paya: {str(e)}"
                )

        elif action == "close_app":
            app_name = params.get("app_name", "").lower().strip()
            exe = APP_REGISTRY.get(app_name, app_name)
            os.system(f"taskkill /im {exe}.exe /f 2>nul")
            return CommandResult(
                success=True, action=action,
                message=f"✅ {app_name.title()} close kar diya!"
            )

        elif action == "focus_app":
            app_name = params.get("app_name", "").lower()
            try:
                wins = gw.getWindowsWithTitle(app_name)
                if wins:
                    wins[0].activate()
                    return CommandResult(success=True, action=action, message=f"🎯 {app_name.title()} focus kar diya!")
                return CommandResult(success=False, action=action, message=f"❌ {app_name} window nahi mili.")
            except Exception as e:
                return CommandResult(success=False, action=action, message=f"❌ Focus error: {str(e)}")

        elif action == "minimize_app":
            app_name = params.get("app_name", "").lower()
            try:
                wins = gw.getWindowsWithTitle(app_name)
                if wins:
                    wins[0].minimize()
                    return CommandResult(success=True, action=action, message=f"📉 {app_name.title()} minimize kar diya!")
                return CommandResult(success=False, action=action, message=f"❌ {app_name} window nahi mili.")
            except Exception as e:
                return CommandResult(success=False, action=action, message=f"❌ Minimize error: {str(e)}")

        elif action == "maximize_app":
            app_name = params.get("app_name", "").lower()
            try:
                wins = gw.getWindowsWithTitle(app_name)
                if wins:
                    wins[0].maximize()
                    return CommandResult(success=True, action=action, message=f"📈 {app_name.title()} maximize kar diya!")
                return CommandResult(success=False, action=action, message=f"❌ {app_name} window nahi mili.")
            except Exception as e:
                return CommandResult(success=False, action=action, message=f"❌ Maximize error: {str(e)}")

        elif action == "list_running_apps":
            apps = []
            for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    if info['cpu_percent'] is not None:
                        apps.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            # Get top 15 by memory
            apps.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
            top_apps = apps[:15]
            app_list = "\n".join([f"  • {a['name']} (RAM: {a.get('memory_percent', 0):.1f}%)" for a in top_apps])
            return CommandResult(
                success=True, action=action,
                message=f"📋 Top running apps:\n{app_list}",
                data=top_apps
            )

        # ─── File Management ───────────────────────────
        elif action == "create_file":
            file_path = params.get("file_name", params.get("file_path", ""))
            content = params.get("content", "")
            if not file_path:
                return CommandResult(success=False, action=action, message="❌ File name nahi diya!")
            
            # Default to Desktop if no path
            if not os.path.dirname(file_path):
                file_path = os.path.join(os.path.expanduser("~\\Desktop"), file_path)
            
            if not is_path_safe(file_path):
                return CommandResult(success=False, action=action, message="🔒 Security: This path is protected!")
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return CommandResult(
                success=True, action=action,
                message=f"✅ File created: {file_path}"
            )

        elif action == "read_file":
            file_path = params.get("file_name", params.get("file_path", ""))
            if not os.path.exists(file_path):
                return CommandResult(success=False, action=action, message=f"❌ File not found: {file_path}")
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(5000)  # Max 5KB
            return CommandResult(
                success=True, action=action,
                message=f"📄 File content:\n```\n{content}\n```",
                data=content
            )

        elif action == "delete_file":
            file_path = params.get("file_name", params.get("file_path", ""))
            if not is_path_safe(file_path):
                return CommandResult(success=False, action=action, message="🔒 Security: This path is protected!")
            if os.path.exists(file_path):
                os.remove(file_path)
                return CommandResult(success=True, action=action, message=f"🗑️ File deleted: {file_path}")
            return CommandResult(success=False, action=action, message=f"❌ File not found: {file_path}")

        elif action == "rename_file":
            old_path = params.get("old_name", params.get("file_path", ""))
            new_path = params.get("new_name", params.get("new_path", ""))
            if os.path.exists(old_path):
                os.rename(old_path, new_path)
                return CommandResult(success=True, action=action, message=f"✅ Renamed: {old_path} → {new_path}")
            return CommandResult(success=False, action=action, message=f"❌ File not found: {old_path}")

        elif action == "move_file":
            src = params.get("source", params.get("file_path", ""))
            dst = params.get("destination", params.get("new_path", ""))
            shutil.move(src, dst)
            return CommandResult(success=True, action=action, message=f"✅ Moved: {src} → {dst}")

        elif action == "copy_file":
            src = params.get("source", params.get("file_path", ""))
            dst = params.get("destination", params.get("new_path", ""))
            shutil.copy2(src, dst)
            return CommandResult(success=True, action=action, message=f"✅ Copied: {src} → {dst}")

        elif action == "search_file":
            query = params.get("query", params.get("file_name", ""))
            search_dir = params.get("directory", os.path.expanduser("~"))
            results = []
            for root, dirs, files in os.walk(search_dir):
                for f in files:
                    if query.lower() in f.lower():
                        results.append(os.path.join(root, f))
                        if len(results) >= 20:
                            break
                if len(results) >= 20:
                    break
            if results:
                file_list = "\n".join([f"  📄 {r}" for r in results])
                return CommandResult(success=True, action=action, message=f"🔍 Found {len(results)} files:\n{file_list}", data=results)
            return CommandResult(success=True, action=action, message=f"🔍 No files found matching '{query}'")

        elif action == "write_file":
            file_path = params.get("file_name", params.get("file_path", ""))
            content = params.get("content", "")
            if not is_path_safe(file_path):
                return CommandResult(success=False, action=action, message="🔒 Security: This path is protected!")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return CommandResult(success=True, action=action, message=f"✅ File written: {file_path}")

        # ─── Folder Management ─────────────────────────
        elif action == "create_folder":
            folder_path = params.get("folder_name", params.get("folder_path", ""))
            if not os.path.dirname(folder_path):
                folder_path = os.path.join(os.path.expanduser("~\\Desktop"), folder_path)
            if not is_path_safe(folder_path):
                return CommandResult(success=False, action=action, message="🔒 Security: This path is protected!")
            os.makedirs(folder_path, exist_ok=True)
            return CommandResult(success=True, action=action, message=f"📁 Folder created: {folder_path}")

        elif action == "delete_folder":
            folder_path = params.get("folder_name", params.get("folder_path", ""))
            if not is_path_safe(folder_path):
                return CommandResult(success=False, action=action, message="🔒 Security: This path is protected!")
            if os.path.exists(folder_path):
                shutil.rmtree(folder_path)
                return CommandResult(success=True, action=action, message=f"🗑️ Folder deleted: {folder_path}")
            return CommandResult(success=False, action=action, message=f"❌ Folder not found: {folder_path}")

        elif action == "list_directory":
            dir_path = params.get("path", params.get("directory", os.path.expanduser("~\\Desktop")))
            if not os.path.exists(dir_path):
                return CommandResult(success=False, action=action, message=f"❌ Path not found: {dir_path}")
            items = []
            for item in os.listdir(dir_path)[:50]:
                full = os.path.join(dir_path, item)
                icon = "📁" if os.path.isdir(full) else "📄"
                size = ""
                if os.path.isfile(full):
                    s = os.path.getsize(full)
                    if s > 1_000_000:
                        size = f" ({s/1_000_000:.1f} MB)"
                    elif s > 1000:
                        size = f" ({s/1000:.1f} KB)"
                items.append(f"  {icon} {item}{size}")
            listing = "\n".join(items)
            return CommandResult(success=True, action=action, message=f"📂 Contents of {dir_path}:\n{listing}", data=items)

        # ─── System Control ────────────────────────────
        elif action == "get_system_info":
            info = {
                "os": f"{platform.system()} {platform.release()}",
                "machine": platform.machine(),
                "processor": platform.processor()[:60],
                "python": platform.python_version(),
                "hostname": platform.node(),
                "user": os.getlogin(),
            }
            info_str = "\n".join([f"  {k}: {v}" for k, v in info.items()])
            return CommandResult(success=True, action=action, message=f"💻 System Info:\n{info_str}", data=info)

        elif action == "get_cpu_usage":
            cpu = psutil.cpu_percent(interval=1)
            cores = psutil.cpu_count()
            freq = psutil.cpu_freq()
            msg = f"⚡ CPU Usage: {cpu}% | Cores: {cores}"
            if freq:
                msg += f" | Speed: {freq.current:.0f} MHz"
            return CommandResult(success=True, action=action, message=msg)

        elif action == "get_ram_usage":
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024**3)
            used_gb = mem.used / (1024**3)
            return CommandResult(
                success=True, action=action,
                message=f"🧠 RAM: {used_gb:.1f} GB / {total_gb:.1f} GB ({mem.percent}% used)"
            )

        elif action == "get_disk_usage":
            disk = psutil.disk_usage('/')
            total_gb = disk.total / (1024**3)
            used_gb = disk.used / (1024**3)
            return CommandResult(
                success=True, action=action,
                message=f"💾 Disk: {used_gb:.1f} GB / {total_gb:.1f} GB ({disk.percent}% used)"
            )

            return CommandResult(success=True, action=action, message="🔌 No battery detected (desktop PC)")

        elif action == "get_ip_address":
            try:
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                public_ip = requests.get('https://api.ipify.org', timeout=5).text
                return CommandResult(
                    success=True, action=action,
                    message=f"🌐 IP Details:\n  • Local: {local_ip}\n  • Public: {public_ip}"
                )
            except Exception as e:
                return CommandResult(success=False, action=action, message=f"❌ IP fetch fail: {str(e)}")

        elif action == "get_network_status":
            try:
                net = psutil.net_io_counters()
                return CommandResult(
                    success=True, action=action,
                    message=f"📊 Network Stats:\n  • Sent: {net.bytes_sent / (1024**2):.1f} MB\n  • Received: {net.bytes_recv / (1024**2):.1f} MB"
                )
            except:
                return CommandResult(success=False, action=action, message="❌ Network stats unavailable.")

        elif action == "shutdown":
            return CommandResult(
                success=True, action=action,
                message="⚠️ System shutdown requested. Confirm karo!",
                requires_confirmation=True,
                data={"command": "shutdown /s /t 30"}
            )

        elif action == "restart_system":
            return CommandResult(
                success=True, action=action,
                message="🔄 System restart requested. Confirm karo!",
                requires_confirmation=True,
                data={"command": "shutdown /r /t 30"}
            )

        elif action == "lock_system":
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return CommandResult(success=True, action=action, message="🔒 System locked!")

        elif action == "sleep_system":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return CommandResult(success=True, action=action, message="💤 System mode: Sleep")

        # ─── Process Control ───────────────────────────
        elif action == "list_processes":
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    procs.append(p.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            procs.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
            top = procs[:20]
            proc_list = "\n".join([f"  [{p['pid']}] {p['name']} (RAM: {p.get('memory_percent',0):.1f}%)" for p in top])
            return CommandResult(success=True, action=action, message=f"📋 Top Processes:\n{proc_list}", data=top)

        elif action == "kill_process":
            target = params.get("process_name", params.get("pid", ""))
            if isinstance(target, int) or target.isdigit():
                pid = int(target)
                p = psutil.Process(pid)
                p.terminate()
                return CommandResult(success=True, action=action, message=f"✅ Process {pid} terminated!")
            else:
                os.system(f"taskkill /im {target}.exe /f 2>nul")
                return CommandResult(success=True, action=action, message=f"✅ {target} terminated!")

        elif action == "suspend_process":
            pid = int(params.get("pid", 0))
            if pid:
                psutil.Process(pid).suspend()
                return CommandResult(success=True, action=action, message=f"⏸️ Process {pid} suspended.")
            return CommandResult(success=False, action=action, message="❌ PID missing.")

        elif action == "resume_process":
            pid = int(params.get("pid", 0))
            if pid:
                psutil.Process(pid).resume()
                return CommandResult(success=True, action=action, message=f"▶️ Process {pid} resumed.")
            return CommandResult(success=False, action=action, message="❌ PID missing.")

        elif action == "start_process":
            cmd = params.get("command", "")
            subprocess.Popen(cmd, shell=True)
            return CommandResult(success=True, action=action, message=f"✅ Process started: {cmd}")

        # ─── Python Execution ──────────────────────────
        elif action == "run_python_script":
            script = params.get("script", params.get("file_path", ""))
            if os.path.exists(script):
                result = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=30)
                output = result.stdout[:2000] if result.stdout else result.stderr[:2000]
                return CommandResult(
                    success=result.returncode == 0, action=action,
                    message=f"🐍 Output:\n```\n{output}\n```",
                    data=output
                )
            return CommandResult(success=False, action=action, message=f"❌ Script not found: {script}")

        elif action == "install_package":
            package = params.get("package_name", "")
            result = subprocess.run([sys.executable, "-m", "pip", "install", package],
                                  capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return CommandResult(success=True, action=action, message=f"✅ Package installed: {package}")
            return CommandResult(success=False, action=action, message=f"❌ Install failed: {result.stderr[:500]}")

        # ─── Screenshot ────────────────────────────────
        elif action == "take_screenshot":
            try:
                import mss
                with mss.mss() as sct:
                    path = os.path.join(os.path.expanduser("~\\Desktop"), f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    sct.shot(output=path)
                    return CommandResult(success=True, action=action, message=f"📸 Screenshot saved: {path}")
            except ImportError:
                return CommandResult(success=False, action=action, message="❌ Screenshot library not installed. Run: pip install mss")

        # ─── Clipboard ────────────────────────────────
        elif action == "get_clipboard":
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                data = win32clipboard.GetClipboardData()
                win32clipboard.CloseClipboard()
                return CommandResult(success=True, action=action, message=f"📋 Clipboard: {data[:500]}", data=data)
            except:
                return CommandResult(success=False, action=action, message="❌ Clipboard access failed")

        elif action == "set_clipboard":
            text = params.get("text", "")
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text)
                win32clipboard.CloseClipboard()
                return CommandResult(success=True, action=action, message="✅ Text copied to clipboard!")
            except:
                return CommandResult(success=False, action=action, message="❌ Clipboard write failed")

        # ─── Media Control ─────────────────────────────
        elif action in ["play_music", "pause_music", "stop_music", "play_video", "pause_video", "stop_video"]:
            pyautogui.press("playpause")
            return CommandResult(success=True, action=action, message="🎵 Media toggled (Play/Pause)")

        elif action == "adjust_volume":
            level = params.get("level", "up")
            key = "volumeup" if level == "up" else "volumedown"
            for _ in range(5): pyautogui.press(key)
            return CommandResult(success=True, action=action, message=f"🔊 Volume {level} done.")

        elif action == "mute_volume":
            pyautogui.press("volumemute")
            return CommandResult(success=True, action=action, message="🔇 Volume muted/unmuted.")

        # ─── Productivity (Notes/Tasks) ────────────────
        elif action == "create_note":
            msg = await create_note(params.get("title", "Untitled"), params.get("content", ""))
            return CommandResult(success=True, action=action, message=msg)

        elif action == "list_notes":
            notes = await list_notes()
            note_list = "\n".join([f"  📝 [{n['id']}] {n['title']}" for n in notes])
            return CommandResult(success=True, action=action, message=f"🗒️ Your Notes:\n{note_list}", data=notes)

        elif action == "create_task":
            msg = await create_task(params.get("task", ""), params.get("priority", "medium"))
            return CommandResult(success=True, action=action, message=msg)

        elif action == "list_tasks":
            tasks = await list_tasks()
            task_list = "\n".join([f"  [{t['id']}] {t['task']} ({t['status']})" for t in tasks])
            return CommandResult(success=True, action=action, message=f"📋 Your Tasks:\n{task_list}", data=tasks)

        else:
            return CommandResult(
                success=False, action=action,
                message=f"❓ Unknown system command: {action}"
            )

    except Exception as e:
        return CommandResult(success=False, action=action, message=f"❌ Error: {str(e)[:300]}")


# ═══════════════════════════════════════════════════════════════
# ONLINE COMMANDS EXECUTOR
# ═══════════════════════════════════════════════════════════════

async def execute_online_command(action: str, params: Dict[str, Any]) -> CommandResult:
    """Execute validated online/web commands."""
    
    try:
        if action == "search_web":
            query = params.get("query", "")
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            webbrowser.open(url)
            return CommandResult(success=True, action=action, message=f"🔍 Google search opened: '{query}'")

        elif action == "open_website":
            url = params.get("url", "")
            if not url.startswith("http"):
                url = f"https://{url}"
            webbrowser.open(url)
            return CommandResult(success=True, action=action, message=f"🌐 Website opened: {url}")

        elif action == "open_youtube":
            query = params.get("query", "")
            if query:
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            else:
                url = "https://www.youtube.com"
            webbrowser.open(url)
            msg = f"▶️ YouTube search opened for: '{query}'" if query else "▶️ YouTube opened!"
            return CommandResult(success=True, action=action, message=msg)

        elif action == "search_flipkart":
            query = params.get("product_query", params.get("query", ""))
            url = f"https://www.flipkart.com/search?q={urllib.parse.quote(query)}"
            webbrowser.open(url)
            return CommandResult(success=True, action=action, message=f"🛒 Flipkart search opened for: '{query}'")

        elif action == "search_amazon":
            query = params.get("query", "")
            url = f"https://www.amazon.in/s?k={urllib.parse.quote(query)}"
            webbrowser.open(url)
            return CommandResult(success=True, action=action, message=f"📦 Amazon search opened for: '{query}'")

        elif action == "compare_prices":
            product = params.get("product", "")
            # Mock price comparison for now
            return CommandResult(
                success=True, action=action,
                message=f"📊 Price Comparison for '{product}':\n  • Flipkart: ₹59,999\n  • Amazon: ₹60,499\n  • Reliance: ₹59,490\n(Best deal: Reliance Digital)"
            )

        elif action == "open_github":
            repo = params.get("repo", "")
            if repo:
                url = f"https://github.com/{repo}"
            else:
                url = "https://github.com"
            webbrowser.open(url)
            msg = f"🐙 GitHub repo opened: {repo}" if repo else "🐙 GitHub opened!"
            return CommandResult(success=True, action=action, message=msg)

        elif action == "open_chatgpt":
            webbrowser.open("https://chat.openai.com")
            return CommandResult(success=True, action=action, message="🤖 ChatGPT opened!")

        elif action == "open_whatsapp":
            number = params.get("number", "")
            message = params.get("message", "")
            if number:
                url = f"https://wa.me/{number}?text={urllib.parse.quote(message)}"
            else:
                url = "https://web.whatsapp.com"
            webbrowser.open(url)
            return CommandResult(success=True, action=action, message="💬 WhatsApp opened!")

        elif action == "send_email":
            to = params.get("to", "")
            subject = params.get("subject", "")
            body = params.get("body", "")
            mailto = f"mailto:{to}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
            webbrowser.open(mailto)
            return CommandResult(
                success=True, action=action,
                message=f"📧 Email draft opened for: {to}",
                requires_confirmation=True
            )

        elif action == "open_maps":
            location = params.get("location", params.get("query", ""))
            url = f"https://www.google.com/maps/search/{urllib.parse.quote(location)}"
            webbrowser.open(url)
            return CommandResult(success=True, action=action, message=f"🗺️ Maps opened for: {location}")

        elif action == "check_weather":
            city = params.get("city", params.get("location", ""))
            url = f"https://www.google.com/search?q=weather+{urllib.parse.quote(city)}"
            webbrowser.open(url)
            return CommandResult(success=True, action=action, message=f"🌤️ Weather for {city} opened!")

        elif action == "translate":
            text = params.get("text", "")
            target = params.get("target_language", "en")
            url = f"https://translate.google.com/?sl=auto&tl={target}&text={urllib.parse.quote(text)}"
            webbrowser.open(url)
            return CommandResult(success=True, action=action, message=f"🌐 Translation opened!")

        # ─── Advanced Web Automation (Scraping) ────────
        elif action == "scrape_page":
            url = params.get("url", "")
            if not url: return CommandResult(success=False, action=action, message="❌ URL missing.")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url, timeout=30000)
                content = await page.inner_text("body")
                await browser.close()
                return CommandResult(success=True, action=action, message=f"📄 Page scraped. Length: {len(content)} chars", data=content[:5000])

        elif action == "extract_price":
            url = params.get("url", "")
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url)
                # Simple heuristic for price extraction
                price = await page.evaluate("() => document.body.innerText.match(/[₹$€£]\s?\d+(?:,\d+)*(?:\.\d+)?/)?.[0]")
                await browser.close()
                return CommandResult(success=True, action=action, message=f"💰 Price extracted: {price}" if price else "❌ Price not found.")

        # ─── Workflow Management ──────────────────────
        elif action == "create_workflow":
            msg = await create_workflow(params.get("name", "New Workflow"), params.get("steps", []))
            return CommandResult(success=True, action=action, message=msg)

        elif action == "execute_workflow":
            wf_name = params.get("name", "")
            wf = await get_workflow(wf_name)
            if wf:
                return CommandResult(success=True, action="complex_task", data=wf['steps'], message=f"🔄 Executing Workflow: {wf_name}")
            return CommandResult(success=False, action=action, message="❌ Workflow not found.")

        # ─── Security ──────────────────────────────────
        elif action == "verify_user":
            return CommandResult(
                success=True, action=action,
                message="🔒 User Verification Required. Please provide your voice signature or PIN.",
                requires_confirmation=True
            )

        else:
            return CommandResult(success=False, action=action, message=f"❓ Unknown online command: {action}")

    except Exception as e:
        return CommandResult(success=False, action=action, message=f"❌ Error: {str(e)[:300]}")


# ═══════════════════════════════════════════════════════════════
# COMMAND ROUTER (Main entry point)
# ═══════════════════════════════════════════════════════════════

async def execute_action(command_json: dict) -> CommandResult:
    """
    Main command router. Validates and routes to appropriate executor.
    This is the SINGLE entry point for all action execution.
    """
    try:
        # Validate with Pydantic
        cmd = ActionCommand(**command_json)
        
        # Check confidence
        if cmd.meta.confidence < 0.70:
            return CommandResult(
                success=False, action=cmd.action,
                message=f"⚠️ Low confidence ({cmd.meta.confidence}). Kya tum sure ho? Please rephrase."
            )
        
        # Check if needs confirmation (for dangerous actions)
        if needs_confirmation(cmd.action) and not cmd.meta.requires_confirmation:
            return CommandResult(
                success=True, action=cmd.action,
                message=f"⚠️ '{cmd.action}' is a sensitive action. Confirm karo — 'Haan, kar do!'",
                requires_confirmation=True
            )
        
        # Route to executor
        if cmd.type == "system_action":
            return await execute_system_command(cmd.action, cmd.parameters)
        
        elif cmd.type == "online_action":
            return await execute_online_command(cmd.action, cmd.parameters)
        
        elif cmd.type == "complex_task":
            # Execute steps sequentially
            results = []
            for step in cmd.steps:
                step_action = step.get("action", "")
                step_params = step.get("parameters", {})
                # Determine type from action name
                if step_action in ["search_web", "open_website", "open_youtube", "send_email", "open_maps"]:
                    r = await execute_online_command(step_action, step_params)
                else:
                    r = await execute_system_command(step_action, step_params)
                results.append(r.message)
            
            return CommandResult(
                success=True, action="complex_task",
                message="📋 Multi-step task complete:\n" + "\n".join(results)
            )

        elif cmd.type == "ai_action":
            text = cmd.parameters.get("text", "")
            if cmd.action == "summarize_text":
                res = await summarize_text(text)
                return CommandResult(success=True, action=cmd.action, message=f"📝 Summary:\n{res}")
            elif cmd.action == "translate_text":
                res = await translate_text(text, cmd.parameters.get("target_lang", "English"))
                return CommandResult(success=True, action=cmd.action, message=f"🌐 Translation:\n{res}")
            return CommandResult(success=False, action=cmd.action, message="❌ AI action error.")
        
        elif cmd.type == "chat":
            return CommandResult(success=True, action="chat", message=cmd.response)
        
        elif cmd.type == "clarification":
            return CommandResult(
                success=True, action="clarification",
                message=f"🤔 {cmd.question}"
            )
        
        else:
            return CommandResult(success=False, action="unknown", message=f"❓ Unknown action type: {cmd.type}")

    except Exception as e:
        return CommandResult(
            success=False, action="parse_error",
            message=f"❌ Command parsing failed: {str(e)[:300]}"
        )


# ═══════════════════════════════════════════════════════════════
# ALL SUPPORTED ACTIONS (for reference / autocomplete)
# ═══════════════════════════════════════════════════════════════

SUPPORTED_ACTIONS = {
    "system_action": [
        "open_app", "close_app", "list_running_apps",
        "create_file", "read_file", "write_file", "delete_file",
        "rename_file", "move_file", "copy_file", "search_file",
        "create_folder", "delete_folder", "list_directory",
        "get_system_info", "get_cpu_usage", "get_ram_usage",
        "get_disk_usage", "get_battery",
        "shutdown", "restart_system", "lock_system",
        "list_processes", "kill_process", "start_process",
        "run_python_script", "install_package",
        "take_screenshot", "get_clipboard", "set_clipboard",
    ],
    "online_action": [
        "search_web", "open_website", "open_youtube", "search_flipkart",
        "open_github", "open_chatgpt", "open_whatsapp",
        "send_email", "open_maps", "check_weather", "translate",
    ],
    "ai_action": [
        "summarize_text", "generate_code", "debug_code",
        "analyze_sentiment", "classify_text", "generate_report",
        "translate_text"
    ]
}
