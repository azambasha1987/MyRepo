"""
AzamLabs Desktop Terminal URI Scheme & Multi-Tab Launcher Generator
Generates native URIs (telnet://) and 1-click batch launcher scripts for:
Windows Terminal, SecureCRT, PuTTY, and macOS iTerm2.
"""

from typing import List, Dict, Any
from azamlabs.core.schema import AzamNode, NodeStatus


class TerminalLauncherManager:
    """Produces native OS URI schemes and 1-click multi-tab desktop launcher scripts."""

    @staticmethod
    def get_node_uri(node: AzamNode, host: str = "127.0.0.1") -> str:
        """Returns standard desktop URI scheme (e.g. telnet://127.0.0.1:32768)."""
        port = node.console_port or 23
        return f"{node.console_type}://{host}:{port}"

    @classmethod
    def generate_windows_terminal_script(
        cls,
        lab_name: str,
        nodes: List[AzamNode],
        host: str = "127.0.0.1"
    ) -> str:
        """Generates a Windows Terminal (wt.exe) multi-tab batch launcher (.bat)."""
        active_nodes = [n for n in nodes if n.console_port]
        if not active_nodes:
            return "@echo off\necho No active console ports found for this lab.\npause\n"

        cmd_parts = ["wt.exe"]
        for idx, node in enumerate(active_nodes):
            tab_arg = "new-tab" if idx > 0 else ""
            if tab_arg:
                cmd_parts.append(f"; {tab_arg}")
            cmd_parts.append(f"--title \"{node.name}\" telnet {host} {node.console_port}")

        full_command = " ".join(cmd_parts)
        return (
            f"@echo off\n"
            f":: AzamLabs Windows Terminal 1-Click Launcher\n"
            f":: Lab: {lab_name}\n\n"
            f"echo Launching {len(active_nodes)} terminal tabs in Windows Terminal...\n"
            f"start \"\" {full_command}\n"
        )

    @classmethod
    def generate_securecrt_script(
        cls,
        lab_name: str,
        nodes: List[AzamNode],
        host: str = "127.0.0.1"
    ) -> str:
        """Generates a SecureCRT multi-tab VBScript (.vbs)."""
        active_nodes = [n for n in nodes if n.console_port]
        lines = [
            "#$language = \"VBScript\"",
            "#$interface = \"1.0\"",
            "",
            f"' AzamLabs SecureCRT 1-Click Multi-Tab Launcher for '{lab_name}'",
            "Sub Main",
        ]
        for node in active_nodes:
            lines.append(f"    crt.Session.ConnectInTab(\"/TELNET {host} {node.console_port}\")")
            lines.append(f"    crt.GetScriptTab.Caption = \"{node.name}\"")
        lines.append("End Sub")
        return "\n".join(lines) + "\n"

    @classmethod
    def generate_iterm2_script(
        cls,
        lab_name: str,
        nodes: List[AzamNode],
        host: str = "127.0.0.1"
    ) -> str:
        """Generates a macOS iTerm2 multi-tab AppleScript (.scpt)."""
        active_nodes = [n for n in nodes if n.console_port]
        lines = [
            f"-- AzamLabs iTerm2 Multi-Tab Launcher for '{lab_name}'",
            "tell application \"iTerm\"",
            "    activate",
            "    set newWindow to (create window with default profile)",
            "    tell newWindow",
        ]
        for idx, node in enumerate(active_nodes):
            if idx == 0:
                lines.append(f"        tell current session")
                lines.append(f"            set name to \"{node.name}\"")
                lines.append(f"            write text \"telnet {host} {node.console_port}\"")
                lines.append(f"        end tell")
            else:
                lines.append(f"        set newTab to (create tab with default profile)")
                lines.append(f"        tell current session")
                lines.append(f"            set name to \"{node.name}\"")
                lines.append(f"            write text \"telnet {host} {node.console_port}\"")
                lines.append(f"        end tell")
        lines.append("    end tell")
        lines.append("end tell")
        return "\n".join(lines) + "\n"

    @classmethod
    def generate_putty_batch_script(
        cls,
        lab_name: str,
        nodes: List[AzamNode],
        host: str = "127.0.0.1"
    ) -> str:
        """Generates a Windows PuTTY batch launcher (.bat)."""
        active_nodes = [n for n in nodes if n.console_port]
        lines = [
            "@echo off",
            f":: AzamLabs PuTTY Launcher for '{lab_name}'",
            f"echo Launching {len(active_nodes)} PuTTY windows...",
        ]
        for node in active_nodes:
            lines.append(f"start \"{node.name}\" putty.exe -telnet {host} {node.console_port}")
        return "\n".join(lines) + "\n"


# Global Launcher Manager
launcher_manager = TerminalLauncherManager()
