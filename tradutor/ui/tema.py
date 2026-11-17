"""Gerenciador central de temas visuais e paletas de cores calibradas (Desktop Utilitario)."""

import customtkinter as ctk
from ..config_usuario import PreferenciasUsuario

TEMAS = {
    "escuro": {
        "nome": "Escuro (Grafite)",
        "ctk_mode": "Dark",
        "bg_janela": "#141414",
        "bg_sidebar": "#1c1c1c",
        "bg_card": "#222222",
        "bg_card_hover": "#2c2c2c",
        "borda_card": "#333333",
        "borda_largura": 1,
        "raio_card": 2,
        "fonte_ui": "Segoe UI",
        "destaque_azul": "#2d6cdf",
        "destaque_azul_hover": "#2458b8",
        "destaque_verde": "#287d4e",
        "destaque_verde_hover": "#1f633d",
        "destaque_vermelho": "#c93b3b",
        "destaque_vermelho_hover": "#a62e2e",
        "btn_destaque_txt": "#ffffff",
        "texto_principal": "#e8e8e8",
        "texto_secundario": "#a0a0a0",
        "texto_escuro": "#707070",
        "bg_console": "#0f0f0f",
        "combo_bg": "#181818",
        "combo_btn": "#2c2c2c",
        "progressbar_bg": "#262626",
        "badge_ext_mkv_bg": "#1a2636",
        "badge_ext_mkv_txt": "#9ec5fe",
        "badge_ext_outros_bg": "#262626",
        "badge_ext_outros_txt": "#d4d4d4",
        "badge_fluxo_bg": "#18261f",
        "badge_fluxo_txt": "#7ee2a8",
    },
    "claro": {
        "nome": "Claro (Utilitário)",
        "ctk_mode": "Light",
        "bg_janela": "#eaeaea",
        "bg_sidebar": "#f5f5f5",
        "bg_card": "#ffffff",
        "bg_card_hover": "#e4e4e4",
        "borda_card": "#c8c8c8",
        "borda_largura": 1,
        "raio_card": 2,
        "fonte_ui": "Segoe UI",
        "destaque_azul": "#1f5cc7",
        "destaque_azul_hover": "#174699",
        "destaque_verde": "#1f6f43",
        "destaque_verde_hover": "#175432",
        "destaque_vermelho": "#b82e2e",
        "destaque_vermelho_hover": "#942222",
        "btn_destaque_txt": "#ffffff",
        "texto_principal": "#141414",
        "texto_secundario": "#525252",
        "texto_escuro": "#6e6e6e",
        "bg_console": "#ffffff",
        "combo_bg": "#ffffff",
        "combo_btn": "#dcdcdc",
        "progressbar_bg": "#d4d4d4",
        "badge_ext_mkv_bg": "#dde8f8",
        "badge_ext_mkv_txt": "#153e75",
        "badge_ext_outros_bg": "#e6e6e6",
        "badge_ext_outros_txt": "#262626",
        "badge_fluxo_bg": "#ddf0e4",
        "badge_fluxo_txt": "#14532d",
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
        "raio_card": 2,
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
        "badge_fluxo_txt": "#000000",
    },
    "ms_dos": {
        "nome": "MS-DOS Retrô",
        "ctk_mode": "Dark",
        "bg_janela": "#000000",
        "bg_sidebar": "#020a02",
        "bg_card": "#041204",
        "bg_card_hover": "#0a2a0a",
        "borda_card": "#1c7a1c",
        "borda_largura": 2,
        "raio_card": 0,
        "fonte_ui": "Consolas",
        "destaque_azul": "#26c426",
        "destaque_azul_hover": "#1c9a1c",
        "destaque_verde": "#33ff33",
        "destaque_verde_hover": "#26c426",
        "destaque_vermelho": "#ff5555",
        "destaque_vermelho_hover": "#cc0000",
        "btn_destaque_txt": "#000000",
        "texto_principal": "#33ff33",
        "texto_secundario": "#22b822",
        "texto_escuro": "#168a16",
        "bg_console": "#000300",
        "combo_bg": "#010d01",
        "combo_btn": "#0a2a0a",
        "progressbar_bg": "#0a2a0a",
        "badge_ext_mkv_bg": "#33ff33",
        "badge_ext_mkv_txt": "#000000",
        "badge_ext_outros_bg": "#26c426",
        "badge_ext_outros_txt": "#000000",
        "badge_fluxo_bg": "#0a2a0a",
        "badge_fluxo_txt": "#33ff33",
    },
}

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
