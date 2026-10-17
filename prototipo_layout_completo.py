"""Protótipo Interativo Completo da Nova Interface (v2.7.0).

Ferramenta interativa para fins de testes, homologação e demonstração:
- Ações Rápidas no Header: [📖 Grimório], [🎨 Visualizar] e [⚙ Configurações]
- 4 Temas Visuais completos: Escuro, Claro, Alto Contraste e MS-DOS Retrô
- Inspeção dinâmica de entidades de Lore e animes no Grimório
- Sistema de abas de Configurações, suporte i18n e limpeza de cache SQLite
- Barra de Ferramentas de Testes com injeção de arquivos demo, alternância rápida e testes de conflito
- Simulação de esteira completa de processamento com logs detalhados, progresso suave e cancelamento gracioso
"""

import sys
import os
import time
import threading
import customtkinter as ctk

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tradutor.ui.tema import inicializar_tema, definir_tema, obter_tema_ativo, CORES, TEMAS
from tradutor.i18n import I18n
from tradutor.interface import InterfaceGrafica


class ControladorPrototipo:
    """Controlador simulado para fins de testes completos e isolados."""

    def __init__(self, view: InterfaceGrafica):
        self._view = view
        self._interrompido = threading.Event()
        self._simular_conflito = False

        self._view.set_controller(self)

    def set_simular_conflito(self, ativo: bool):
        """Habilita ou desabilita a simulação de arquivo em conflito."""
        self._simular_conflito = ativo

    def start_translation(self, files, idioma_origem, idioma_destino, manter_legenda):
        """Inicia a simulação assíncrona da esteira de tradução em background."""
        self._interrompido.clear()
        self._view.prepare_for_processing()
        self._view.log(f"[INÍCIO] Iniciando simulação de esteira para {len(files)} arquivo(s)...")
        self._view.log(f"[CONFIG] Origem: {idioma_origem} | Destino: {idioma_destino} | Manter avulsa: {manter_legenda}")

        def _simular():
            total_arquivos = len(files)
            for idx, caminho in enumerate(files, 1):
                if self._interrompido.is_set():
                    break

                nome_base = os.path.basename(caminho)
                ext = nome_base.rsplit('.', 1)[-1].upper() if '.' in nome_base else "RAW"

                # 1. Simulação de Detecção de Conflito de Arquivo
                if self._simular_conflito:
                    self._view.log(f"[{idx}/{total_arquivos}] Verificando existência de {nome_base}_PT.{ext.lower()}...")
                    sobrescrever = self._view.ask_overwrite(f"{nome_base}_PT.{ext.lower()}")
                    if not sobrescrever:
                        self._view.log(f"[{idx}/{total_arquivos}] [PULADO] Arquivo ignorado conforme decisão do usuário.")
                        continue
                    self._view.log(f"[{idx}/{total_arquivos}] [CONFIRMADO] Prosseguindo com sobrescrita autorizada.")

                # 2. Etapa de Extração / Preparação
                if ext == "MKV":
                    self._view.log(f"[{idx}/{total_arquivos}] Extraindo faixa ASS selecionada via mkvextract...")
                    time.sleep(0.4)
                else:
                    self._view.log(f"[{idx}/{total_arquivos}] Carregando arquivo de legenda avulsa {ext}...")
                    time.sleep(0.2)

                if self._interrompido.is_set():
                    break

                # 3. Etapa do Escudo Anti-Alucinação e Blindagem
                self._view.log(f"[{idx}/{total_arquivos}] Ativando Escudo Anti-Alucinação: 38 termos de lore mapeados.")
                self._view.log(f"[{idx}/{total_arquivos}] Blindadas 24 tags ASS/HTML ({{\\an8}}, {{\\i1}}, <b>) contra mutação.")
                time.sleep(0.3)

                # 4. Processamento em Lotes com Cache SQLite Simulado
                lotes_totais = 5
                for lote in range(1, lotes_totais + 1):
                    if self._interrompido.is_set():
                        break
                    time.sleep(0.25)
                    pct_geral = int(((idx - 1) / total_arquivos + (lote / lotes_totais) / total_arquivos) * 100)
                    self._view.update_progress(pct_geral, 100)

                    if lote % 2 == 0:
                        self._view.log(f"  -> Lote {lote}/{lotes_totais} ({nome_base}): 40 diálogos (100% Cache SQLite Hit)")
                    else:
                        self._view.log(f"  -> Lote {lote}/{lotes_totais} ({nome_base}): 40 diálogos traduzidos com sucesso")

                if self._interrompido.is_set():
                    break

                # 5. Etapa de Finalização e Muxing
                if ext == "MKV":
                    self._view.log(f"[{idx}/{total_arquivos}] Multiplexando novo MKV com trilha de legenda embutida...")
                    time.sleep(0.3)
                self._view.log(f"[{idx}/{total_arquivos}] [OK] Processamento finalizado com sucesso para: {nome_base}")
                time.sleep(0.2)

            if self._interrompido.is_set():
                self._view.log("[CANCELADO] Operação abortada pelo usuário. Limpeza de arquivos temporários concluída.")
                self._view.footer.configurar_modo_pronto(len(self._view.files) > 0)
                self._view.fila.set_interativo(True)
                self._view.footer.set_status("Cancelado")
            else:
                self._view.update_progress(100, 100)
                self._view.log("[SUCESSO] Todos os arquivos da fila foram processados!")
                self._view.on_processing_finished()

        threading.Thread(target=_simular, daemon=True).start()

    def cancel_translation(self):
        """Sinaliza interrupção imediata da esteira de teste."""
        self._interrompido.set()
        self._view.log("[CANCELANDO] Interrompendo processamento em background...")

    def on_files_selected(self, files):
        """Simula a detecção de trilhas de áudio/legenda em MKVs."""
        mkvs = [f for f in files if f.lower().endswith(".mkv")]
        if mkvs:
            langs = ["jpn (Japonês)", "eng (Inglês)", "por (Português)"]
            self._view.update_language_options(langs)

    def on_closing(self):
        """Encerra a aplicação protótipo."""
        self._interrompido.set()
        self._view.destroy()


class PrototipoApp(InterfaceGrafica):
    """Interface Gráfica estendida com Barra de Ferramentas de Testes e Homologação."""

    DEMO_POOL = [
        "Bleach_Thousand-Year_Blood_War_Ep30_[Dual_Audio].mkv",
        "One_Piece_Wano_Kuni_Climax_E1080.ass",
        "Sousou_no_Frieren_Beyond_Journeys_End_E12.srt",
        "Jujutsu_Kaisen_Shibuya_Incident_E15.mkv",
        "The_Apothecary_Diaries_Ep04.ass",
        "Chainsaw_Man_Public_Safety_Arc_E01.srt"
    ]

    def __init__(self):
        super().__init__()
        self.title("Protótipo de Testes — Tradutor de Legendas v2.7.0")
        self._demo_idx = 0
        self._modo_conflito = False

        self._injetar_barra_testes()

    def _injetar_barra_testes(self):
        """Cria uma barra superior de controles rápidos de homologação."""
        largura_borda = CORES.get("borda_largura", 1)
        raio_card = CORES.get("raio_card", 6)
        fonte_ui = CORES.get("fonte_ui", "Segoe UI")

        self.frame_test_bar = ctk.CTkFrame(
            self,
            fg_color=CORES["bg_card"],
            border_color=CORES["destaque_azul"],
            border_width=largura_borda,
            corner_radius=raio_card,
            height=38
        )
        self.frame_test_bar.pack(before=self.header, fill="x", padx=16, pady=(10, 4))

        self.lbl_tag_test = ctk.CTkLabel(
            self.frame_test_bar,
            text="TEST TOOLBAR:",
            font=(fonte_ui, 10, "bold"),
            text_color=CORES["destaque_azul"]
        )
        self.lbl_tag_test.pack(side="left", padx=(12, 8), pady=5)

        self.btn_add_demo = ctk.CTkButton(
            self.frame_test_bar,
            text="+ Arquivo Demo",
            font=(fonte_ui, 10, "bold"),
            width=110,
            height=24,
            corner_radius=raio_card,
            fg_color=CORES["destaque_azul"],
            hover_color=CORES["destaque_azul_hover"],
            text_color=CORES.get("btn_destaque_txt", "#ffffff"),
            command=self._adicionar_arquivo_demo
        )
        self.btn_add_demo.pack(side="left", padx=4, pady=5)

        self.btn_toggle_conflito = ctk.CTkButton(
            self.frame_test_bar,
            text="Sobrescrita: OFF",
            font=(fonte_ui, 10, "bold"),
            width=115,
            height=24,
            corner_radius=raio_card,
            fg_color=CORES["bg_sidebar"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            text_color=CORES["texto_secundario"],
            command=self._alternar_teste_sobrescrita
        )
        self.btn_toggle_conflito.pack(side="left", padx=4, pady=5)

        self.btn_ciclar_temas = ctk.CTkButton(
            self.frame_test_bar,
            text="Ciclar Temas",
            font=(fonte_ui, 10, "bold"),
            width=95,
            height=24,
            corner_radius=raio_card,
            fg_color=CORES["bg_sidebar"],
            hover_color=CORES["bg_card_hover"],
            border_color=CORES["borda_card"],
            border_width=largura_borda,
            text_color=CORES["texto_principal"],
            command=self._ciclar_temas
        )
        self.btn_ciclar_temas.pack(side="left", padx=4, pady=5)

        self.btn_limpar_logs = ctk.CTkButton(
            self.frame_test_bar,
            text="Limpar Logs",
            font=(fonte_ui, 10),
            width=85,
            height=24,
            corner_radius=raio_card,
            fg_color="transparent",
            hover_color=CORES["bg_card_hover"],
            text_color=CORES["texto_secundario"],
            command=self._limpar_console_logs
        )
        self.btn_limpar_logs.pack(side="right", padx=(4, 10), pady=5)

    def _adicionar_arquivo_demo(self):
        """Injeta um novo arquivo demonstrativo na esteira de testes."""
        base_dir = os.path.abspath(os.path.dirname(__file__))
        novo_arquivo = os.path.join(base_dir, self.DEMO_POOL[self._demo_idx % len(self.DEMO_POOL)])
        self._demo_idx += 1

        if novo_arquivo not in self.files:
            self.files.append(novo_arquivo)
            self._sincronizar_fila()
            self.log(f"[TESTE] Adicionado arquivo à fila: {os.path.basename(novo_arquivo)}")
            ctrl = getattr(self, "controller", None)
            if ctrl:
                ctrl.on_files_selected(self.files)

    def _alternar_teste_sobrescrita(self):
        """Alterna a flag de simulação de conflito de sobrescrita."""
        self._modo_conflito = not self._modo_conflito
        if self._modo_conflito:
            self.btn_toggle_conflito.configure(
                text="Sobrescrita: ON",
                fg_color=CORES["destaque_vermelho"],
                text_color="white"
            )
            self.log("[TESTE] Modo de simulação de sobrescrita ATIVADO: abrirá diálogo modal de conflito.")
        else:
            self.btn_toggle_conflito.configure(
                text="Sobrescrita: OFF",
                fg_color=CORES["bg_sidebar"],
                text_color=CORES["texto_secundario"]
            )
            self.log("[TESTE] Modo de simulação de sobrescrita DESATIVADO.")

        ctrl = getattr(self, "controller", None)
        if ctrl and hasattr(ctrl, "set_simular_conflito"):
            ctrl.set_simular_conflito(self._modo_conflito)

    def _ciclar_temas(self):
        """Cicla dinamicamente entre os 4 temas disponíveis."""
        ordem = ["escuro", "claro", "alto_contraste", "ms_dos"]
        tema_atual = obter_tema_ativo()
        idx_atual = ordem.index(tema_atual) if tema_atual in ordem else 0
        proximo_tema = ordem[(idx_atual + 1) % len(ordem)]

        definir_tema(proximo_tema)
        self._aplicar_novo_tema(proximo_tema)
        self.log(f"[TEMA] Tema alterado para: {TEMAS[proximo_tema]['nome']}")

        # Atualiza a propria barra de testes
        cores = CORES
        largura_borda = cores.get("borda_largura", 1)
        raio_card = cores.get("raio_card", 6)
        fonte_ui = cores.get("fonte_ui", "Segoe UI")

        self.frame_test_bar.configure(
            fg_color=cores["bg_card"],
            border_color=cores["destaque_azul"],
            border_width=largura_borda,
            corner_radius=raio_card
        )
        self.lbl_tag_test.configure(text_color=cores["destaque_azul"], font=(fonte_ui, 10, "bold"))
        self.btn_add_demo.configure(
            fg_color=cores["destaque_azul"],
            hover_color=cores["destaque_azul_hover"],
            text_color=cores.get("btn_destaque_txt", "#ffffff"),
            font=(fonte_ui, 10, "bold"),
            corner_radius=raio_card
        )
        self.btn_ciclar_temas.configure(
            fg_color=cores["bg_sidebar"],
            border_color=cores["borda_card"],
            border_width=largura_borda,
            text_color=cores["texto_principal"],
            font=(fonte_ui, 10, "bold"),
            corner_radius=raio_card
        )
        self.btn_limpar_logs.configure(
            text_color=cores["texto_secundario"],
            font=(fonte_ui, 10),
            corner_radius=raio_card
        )

    def _limpar_console_logs(self):
        """Esvazia o textbox do console de logs."""
        try:
            self.footer.textbox.configure(state="normal")
            self.footer.textbox.delete("1.0", "end")
            self.footer.textbox.configure(state="disabled")
        except Exception:
            pass


def executar_prototipo():
    """Inicializa e executa a interface de testes com dados pré-carregados."""
    inicializar_tema()
    I18n.inicializar()

    app = PrototipoApp()
    controlador = ControladorPrototipo(app)

    # Pre-carrega 3 arquivos ficticios para demonstracao imediata
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.files = [
        os.path.join(base_dir, "Bleach_Thousand-Year_Blood_War_Ep30_[Dual_Audio].mkv"),
        os.path.join(base_dir, "One_Piece_Wano_Kuni_Climax_E1080.ass"),
        os.path.join(base_dir, "Sousou_no_Frieren_Beyond_Journeys_End_E12.srt")
    ]
    app._sincronizar_fila()
    controlador.on_files_selected(app.files)

    print("=" * 72)
    print(" TRADUTOR DE LEGENDAS (v2.7.0) — PROTÓTIPO DE HOMOLOGAÇÃO E TESTES")
    print("=" * 72)
    print("Ambiente 100% isolado (sem consumo de API externa ou ferramentas de sistema).")
    print("\nGuia Rápido de Testes Disponíveis:")
    print("  1. BARRA SUPERIOR:")
    print("     - [+ Arquivo Demo]: Injeta novos arquivos (.mkv, .ass, .srt) na fila.")
    print("     - [Sobrescrita: OFF/ON]: Ativa/desativa simulação de arquivos conflitantes.")
    print("     - [Ciclar Temas]: Alterna em tempo real entre Escuro, Claro, Alto Contraste e MS-DOS.")
    print("     - [Limpar Logs]: Esvazia o console retrátil.")
    print("  2. CABEÇALHO (HEADER):")
    print("     - [📖 Grimório]: Abre a janela de visualização e busca de Lore de animes.")
    print("     - [🎨 Visualizar]: Abre o modal dedicado de seleção de temas.")
    print("     - [⚙]: Abre as Configurações (Preferências, Política de Sobrescrita, Cache).")
    print("  3. FLUXO DE EXECUÇÃO:")
    print("     - [INICIAR TRADUÇÃO]: Dispara esteira simulada com progresso e logs em lote.")
    print("     - [CANCELAR]: Aborta o processamento no meio do caminho de forma graciosa.")
    print("     - [CONSOLE]: Abre a gaveta retrátil sanfonada de logs.")
    print("=" * 72)

    app.mainloop()


if __name__ == "__main__":
    executar_prototipo()
