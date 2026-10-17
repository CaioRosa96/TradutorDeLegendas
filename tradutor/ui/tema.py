"""Gerenciador central de temas visuais e paletas de cores calibradas."""

from ..config_usuario import PreferenciasUsuario

TEMAS = {
    "escuro": {
        "nome": "Escuro (Ardósia)",
        "ctk_mode": "Dark",
        "bg_janela": "#111218",       # Wallpaper mais escuro que as caixas
        "bg_sidebar": "#1a1b26",      # Caixa da barra lateral
        "bg_card": "#242636",         # Caixas internas dos cards
        "bg_card_hover": "#2e3146",
        "borda_card": "#383a52",
        "borda_largura": 1,
        "destaque_azul": "#3b82f6",
        "destaque_azul_hover": "#2563eb",
        "destaque_verde": "#10b981",
        "destaque_verde_hover": "#059669",
        "destaque_vermelho": "#ef4444",
        "destaque_vermelho_hover": "#dc2626",
        "texto_principal": "#f8fafc",
        "texto_secundario": "#94a3b8",
        "texto_escuro": "#64748b",
        "bg_console": "#0c0d12",
        "combo_bg": "#161722",
        "combo_btn": "#2a2c3d",
        "progressbar_bg": "#242636",
        "badge_ext_mkv_bg": "#3b82f6",
        "badge_ext_mkv_txt": "#ffffff",
        "badge_ext_outros_bg": "#8b5cf6",
        "badge_ext_outros_txt": "#ffffff",
        "badge_fluxo_bg": "#161722",
        "badge_fluxo_txt": "#10b981"
    },
    "claro": {
        "nome": "Claro (Clean)",
        "ctk_mode": "Light",
        "bg_janela": "#cbd5e1",       # Wallpaper cinza ardósia bem demarcado
        "bg_sidebar": "#ffffff",      # Caixas externas brancas puras
        "bg_card": "#f8fafc",         # Caixas internas com relevo suave e nítido
        "bg_card_hover": "#f1f5f9",
        "borda_card": "#94a3b8",      # Bordas nítidas de alto contraste
        "borda_largura": 1,
        "destaque_azul": "#2563eb",
        "destaque_azul_hover": "#1d4ed8",
        "destaque_verde": "#059669",
        "destaque_verde_hover": "#047857",
        "destaque_vermelho": "#dc2626",
        "destaque_vermelho_hover": "#b91c1c",
        "texto_principal": "#0f172a", # Preto ardósia de alta legibilidade
        "texto_secundario": "#334155",# Cinza escuro com contraste impecável
        "texto_escuro": "#64748b",
        "bg_console": "#f8fafc",
        "combo_bg": "#ffffff",
        "combo_btn": "#e2e8f0",
        "progressbar_bg": "#cbd5e1",  # Calha da barra de progresso perfeitamente visível
        "badge_ext_mkv_bg": "#2563eb",
        "badge_ext_mkv_txt": "#ffffff",
        "badge_ext_outros_bg": "#7c3aed",
        "badge_ext_outros_txt": "#ffffff",
        "badge_fluxo_bg": "#dcfce7",  # Fundo verde menta suave de badge moderno
        "badge_fluxo_txt": "#166534"  # Verde escuro de altíssimo contraste
    },
    "alto_contraste": {
        "nome": "Alto Contraste",
        "ctk_mode": "Dark",
        "bg_janela": "#000000",       # Wallpaper preto absoluto
        "bg_sidebar": "#121212",      # Caixa da barra lateral
        "bg_card": "#1e1e1e",         # Caixas dos cards
        "bg_card_hover": "#2a2a2a",
        "borda_card": "#ffffff",
        "borda_largura": 2,
        "destaque_azul": "#00e5ff",
        "destaque_azul_hover": "#00b4d8",
        "destaque_verde": "#00ff66",
        "destaque_verde_hover": "#00cc55",
        "destaque_vermelho": "#ff3333",
        "destaque_vermelho_hover": "#cc0000",
        "texto_principal": "#ffffff",
        "texto_secundario": "#ffff00",
        "texto_escuro": "#ffffff",
        "bg_console": "#0a0a0a",
        "combo_bg": "#121212",
        "combo_btn": "#2a2a2a",
        "progressbar_bg": "#222222",
        "badge_ext_mkv_bg": "#121212",
        "badge_ext_mkv_txt": "#00e5ff",
        "badge_ext_outros_bg": "#121212",
        "badge_ext_outros_txt": "#ffff00",
        "badge_fluxo_bg": "#121212",
        "badge_fluxo_txt": "#ffff00"
    },
    "ms_dos": {
        "nome": "MS-DOS Retrô",
        "ctk_mode": "Dark",
        "bg_janela": "#000000",       # Wallpaper preto absoluto de tela CRT
        "bg_sidebar": "#001800",      # Caixa da barra lateral verde escuro
        "bg_card": "#002a00",         # Caixas dos cards verde
        "bg_card_hover": "#003d00",
        "borda_card": "#00ff66",
        "borda_largura": 1,
        "destaque_azul": "#00ff66",
        "destaque_azul_hover": "#00cc55",
        "destaque_verde": "#00ff66",
        "destaque_verde_hover": "#00cc55",
        "destaque_vermelho": "#ff3333",
        "destaque_vermelho_hover": "#cc0000",
        "texto_principal": "#00ff66",
        "texto_secundario": "#00cc55",
        "texto_escuro": "#008833",
        "bg_console": "#001200",
        "combo_bg": "#001800",
        "combo_btn": "#003d00",
        "progressbar_bg": "#002200",
        "badge_ext_mkv_bg": "#001800",
        "badge_ext_mkv_txt": "#00ff66",
        "badge_ext_outros_bg": "#001800",
        "badge_ext_outros_txt": "#00ff66",
        "badge_fluxo_bg": "#001800",
        "badge_fluxo_txt": "#00ff66"
    }
}

# Paleta global ativa por padrao
_tema_ativo = "escuro"
CORES = dict(TEMAS[_tema_ativo])


def obter_tema_ativo() -> str:
    """Retorna o identificador do tema ativo."""
    return _tema_ativo


def definir_tema(nome_tema: str) -> dict:
    """Atualiza a paleta de cores global ativa e persiste a escolha."""
    global _tema_ativo, CORES
    if nome_tema in TEMAS:
        _tema_ativo = nome_tema
        CORES.clear()
        CORES.update(TEMAS[nome_tema])
        PreferenciasUsuario.definir("tema", nome_tema)
    return CORES


def inicializar_tema():
    """Carrega o tema salvo nas preferencias do usuario."""
    salvo = PreferenciasUsuario.obter("tema", "escuro")
    definir_tema(salvo)
