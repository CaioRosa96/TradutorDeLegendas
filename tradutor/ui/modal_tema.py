"""Dialogo de selecao e troca rapida de temas visuais (Visualizar)."""

import customtkinter as ctk

from .tema import TEMAS, obter_tema_ativo, definir_tema, CORES
from ..i18n import I18n


class ModalTemas(ctk.CTkToplevel):
    """Janela compacta de escolha e alternancia dinamica de temas visuais."""

    def __init__(self, master, ao_trocar_tema_cb=None):
        super().__init__(master)
        self.title(I18n.t("modal_tema_titulo"))
        self.geometry("420x320")
        self.minsize(380, 290)
        self.resizable(False, False)
        self.configure(fg_color=CORES["bg_janela"])
        self.transient(master)
        self.after(50, self.focus)

        self._ao_trocar_tema_cb = ao_trocar_tema_cb
        self._construir_interface()

    def _construir_interface(self):
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 2)
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")

        lbl_tit = ctk.CTkLabel(
            self,
            text=I18n.t("tema_titulo_topo"),
            font=(fonte_ui, 12, "bold"),
            text_color=CORES["texto_principal"],
        )
        lbl_tit.pack(pady=(12, 2))

        lbl_desc = ctk.CTkLabel(
            self,
            text=I18n.t("tema_subtitulo"),
            font=(fonte_ui, 11),
            text_color=CORES["texto_secundario"],
        )
        lbl_desc.pack(pady=(0, 10))

        container = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_sidebar"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            corner_radius=raio_card,
        )
        container.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        tema_ativo = obter_tema_ativo()

        detalhes = {
            "escuro": (I18n.t("tema_escuro_nome"), I18n.t("tema_escuro_desc")),
            "claro": (I18n.t("tema_claro_nome"), I18n.t("tema_claro_desc")),
            "alto_contraste": (I18n.t("tema_alto_contraste_nome"), I18n.t("tema_alto_contraste_desc")),
            "ms_dos": (I18n.t("tema_ms_dos_nome"), I18n.t("tema_ms_dos_desc")),
        }

        for chave, (nome_exibicao, _descricao) in detalhes.items():
            ativo = chave == tema_ativo
            card = ctk.CTkFrame(
                container,
                fg_color=CORES["bg_card_hover"] if ativo else CORES["bg_card"],
                corner_radius=raio_card,
                border_width=largura_borda,
                border_color=CORES["destaque_azul"] if ativo else CORES["borda_card"],
                height=38,
            )
            card.pack(fill="x", padx=8, pady=4)
            card.pack_propagate(False)

            lbl_nome = ctk.CTkLabel(
                card,
                text=f"{'* ' if ativo else '  '}{nome_exibicao}",
                font=(fonte_ui, 11, "bold" if ativo else "normal"),
                text_color=CORES["texto_principal"],
            )
            lbl_nome.pack(side="left", padx=10, pady=6)

            btn_aplicar = ctk.CTkButton(
                card,
                text=I18n.t("tema_btn_ativo") if ativo else I18n.t("tema_btn_aplicar"),
                font=(fonte_ui, 10, "bold"),
                fg_color=CORES["destaque_verde"] if ativo else CORES["destaque_azul"],
                hover_color=CORES["destaque_verde_hover"] if ativo else CORES["destaque_azul_hover"],
                text_color=CORES.get("btn_destaque_txt", "#ffffff"),
                corner_radius=raio_card,
                width=72,
                height=24,
                command=lambda k=chave: self._aplicar_tema(k),
            )
            btn_aplicar.pack(side="right", padx=8, pady=6)

    def _aplicar_tema(self, chave: str):
        definir_tema(chave)
        config = TEMAS[chave]
        ctk.set_appearance_mode(config["ctk_mode"])

        if self._ao_trocar_tema_cb:
            self._ao_trocar_tema_cb(chave)

        self.destroy()
