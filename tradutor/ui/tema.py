"""Gerenciador central de temas visuais e paletas de cores calibradas."""

import customtkinter as ctk
from ..config_usuario import PreferenciasUsuario

TEMAS = {
    "escuro": {
        "nome": "Escuro (Ardósia)",
        "ctk_mode": "Dark",
        "bg_janela": "#111218",
        "bg_sidebar": "#1a1b26",
        "bg_card": "#242636",
        "bg_card_hover": "#2e3146",
        "borda_card": "#383a52",
        "borda_largura": 1,
        "raio_card": 6,
        "fonte_ui": "Segoe UI",
        "destaque_azul": "#3b82f6",
        "destaque_azul_hover": "#2563eb",
        "destaque_verde": "#10b981",
        "destaque_verde_hover": "#059669",
        "destaque_vermelho": "#ef4444",
        "destaque_vermelho_hover": "#dc2626",
        "btn_destaque_txt": "#ffffff",
        "texto_principal": "#f8fafc",
        "texto_secundario": "#94a3b8",
        "texto_escuro": "#64748b",
        "bg_console": "#0c0d12",
        "combo_bg": "#161722",
        "combo_btn": "#2a2c3d",
        "progressbar_bg": "#242636",
        "badge_ext_mkv_bg": "#2563eb",
        "badge_ext_mkv_txt": "#ffffff",
        "badge_ext_outros_bg": "#7c3aed",
        "badge_ext_outros_txt": "#ffffff",
        "badge_fluxo_bg": "#161722",
        "badge_fluxo_txt": "#10b981"
    },
    "claro": {
        "nome": "Claro (Clean)",
        "ctk_mode": "Light",
        "bg_janela": "#f1f5f9",
        "bg_sidebar": "#ffffff",
        "bg_card": "#f8fafc",
        "bg_card_hover": "#e2e8f0",
        "borda_card": "#cbd5e1",
        "borda_largura": 1,
        "raio_card": 6,
        "fonte_ui": "Segoe UI",
        "destaque_azul": "#2563eb",
        "destaque_azul_hover": "#1d4ed8",
        "destaque_verde": "#059669",
        "destaque_verde_hover": "#047857",
        "destaque_vermelho": "#dc2626",
        "destaque_vermelho_hover": "#b91c1c",
        "btn_destaque_txt": "#ffffff",
        "texto_principal": "#0f172a",
        "texto_secundario": "#475569",
        "texto_escuro": "#64748b",
        "bg_console": "#f8fafc",
        "combo_bg": "#ffffff",
        "combo_btn": "#e2e8f0",
        "progressbar_bg": "#cbd5e1",
        "badge_ext_mkv_bg": "#dbeafe",
        "badge_ext_mkv_txt": "#1e40af",
        "badge_ext_outros_bg": "#ede9fe",
        "badge_ext_outros_txt": "#5b21b6",
        "badge_fluxo_bg": "#dcfce7",
        "badge_fluxo_txt": "#166534"
    },
    "alto_contraste": {
        "nome": "Alto Contraste",
        "ctk_mode": "Dark",
        "bg_janela": "#000000",
        "bg_sidebar": "#000000",
        "bg_card": "#080808",
        "bg_card_hover": "#1f1f1f",
        "borda_card": "#ffffff",
        "borda_largura": 2,
        "raio_card": 4,
        "fonte_ui": "Segoe UI",
        "destaque_azul": "#00e5ff",
        "destaque_azul_hover": "#00b4d8",
        "destaque_verde": "#00ff66",
        "destaque_verde_hover": "#00cc55",
        "destaque_vermelho": "#ff4d4d",
        "destaque_vermelho_hover": "#cc0000",
        "btn_destaque_txt": "#000000",
        "texto_principal": "#ffffff",
        "texto_secundario": "#ffff00",
        "texto_escuro": "#ffffff",
        "bg_console": "#000000",
        "combo_bg": "#080808",
        "combo_btn": "#1f1f1f",
        "progressbar_bg": "#1f1f1f",
        "badge_ext_mkv_bg": "#00e5ff",
        "badge_ext_mkv_txt": "#000000",
        "badge_ext_outros_bg": "#ffff00",
        "badge_ext_outros_txt": "#000000",
        "badge_fluxo_bg": "#ffff00",
        "badge_fluxo_txt": "#000000"
    },
    "ms_dos": {
        "nome": "MS-DOS Retrô",
        "ctk_mode": "Dark",
        "bg_janela": "#000000",
        "bg_sidebar": "#000d00",
        "bg_card": "#001a00",
        "bg_card_hover": "#002b00",
        "borda_card": "#33ff33",
        "borda_largura": 2,
        "raio_card": 0,
        "fonte_ui": "Consolas",
        "destaque_azul": "#ffb000",
        "destaque_azul_hover": "#cc8c00",
        "destaque_verde": "#33ff33",
        "destaque_verde_hover": "#14b814",
        "destaque_vermelho": "#ff5555",
        "destaque_vermelho_hover": "#cc0000",
        "btn_destaque_txt": "#000000",
        "texto_principal": "#33ff33",
        "texto_secundario": "#14b814",
        "texto_escuro": "#0d8a0d",
        "bg_console": "#000500",
        "combo_bg": "#001200",
        "combo_btn": "#002b00",
        "progressbar_bg": "#002200",
        "badge_ext_mkv_bg": "#ffb000",
        "badge_ext_mkv_txt": "#000000",
        "badge_ext_outros_bg": "#33ff33",
        "badge_ext_outros_txt": "#000000",
        "badge_fluxo_bg": "#002b00",
        "badge_fluxo_txt": "#ffb000"
    }
}

# Paleta global ativa por padrao
_tema_ativo = "escuro"
CORES = dict(TEMAS[_tema_ativo])


def obter_tema_ativo() -> str:
    """Retorna o identificador do tema ativo."""
    return _tema_ativo


def definir_tema(nome_tema: str) -> dict:
    """Atualiza a paleta de cores global ativa, sincroniza o modo CTk e persiste a escolha."""
    global _tema_ativo, CORES
    if nome_tema in TEMAS:
        _tema_ativo = nome_tema
        CORES.clear()
        CORES.update(TEMAS[nome_tema])
        try:
            ctk.set_appearance_mode(CORES["ctk_mode"])
        except Exception:
            pass
        PreferenciasUsuario.definir("tema", nome_tema)
        return CORES


def inicializar_tema():
    """Carrega o tema salvo nas preferencias do usuario."""
    salvo = PreferenciasUsuario.obter("tema", "escuro")
    definir_tema(salvo)
