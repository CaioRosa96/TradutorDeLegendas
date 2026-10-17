"""Protótipo Interativo Completo da Nova Interface (v2.7.0).

Demonstra a arquitetura visual modular integrada com:
- Ações Rápidas no Header: [📖 Grimório], [🎨 Visualizar] e [⚙ Configurações]
- 4 Temas Visuais completos: Escuro, Claro, Alto Contraste e MS-DOS Retrô
- Inspeção dinâmica de entidades de Lore e animes no Grimório
- Sistema de abas de Configurações, suporte i18n e limpeza de cache
- Simulação de fila com cards modernos e progresso em lote
"""

import sys
import os
import time
import threading

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from tradutor.ui.tema import inicializar_tema, CORES
from tradutor.i18n import I18n
from tradutor.interface import InterfaceGrafica


def executar_prototipo():
    inicializar_tema()
    I18n.inicializar()

    app = InterfaceGrafica()
    app.title("Protótipo Interativo — Taradutor de Legendas v2.7.0")

    # Arquivos ficticios para demonstracao imediata do visual
    arquivos_demonstracao = [
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "Bleach_Episodio_366_[Dual_Audio].mkv"),
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "One_Piece_Wano_Kuni_E1080.ass"),
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "The_Apothecary_Diaries_Ep04.srt")
    ]
    app.files = arquivos_demonstracao
    app._sincronizar_fila()

    # Mock de execucao demonstrativa para o botao INICIAR TRADUCAO
    class ControladorMock:
        def on_files_selected(self, files):
            pass

        def start_translation(self, files, src_lang, dest_lang, manter_legenda):
            app.prepare_for_processing()
            app.log(f"Iniciando simulação de processamento para {len(files)} arquivo(s)...")
            app.log(f"Parâmetros: Origem={src_lang} | Destino={dest_lang} | Manter={manter_legenda}")

            def _simular():
                for idx, f in enumerate(files, 1):
                    nome = os.path.basename(f)
                    app.log(f"[{idx}/{len(files)}] Analisando faixas e aplicando Escudo Anti-Alucinação em: {nome}")
                    time.sleep(0.6)
                    for pct in range(20, 101, 20):
                        time.sleep(0.15)
                        app.update_progress(pct, 100)
                    app.log(f"[{idx}/{len(files)}] Finalizado com sucesso: {nome}")
                app.on_processing_finished()
                app.log("Simulação concluída com êxito!")

            threading.Thread(target=_simular, daemon=True).start()

        def cancel_translation(self):
            app.log("Cancelamento solicitado pelo usuário.")
            app.footer.configurar_modo_pronto(True)

        def on_closing(self):
            app.destroy()

    app.set_controller(ControladorMock())

    print("[PROTÓTIPO] Interface Grafica inicializada com sucesso.")
    print("[PROTÓTIPO] Experimente:")
    print("  1. Clicar em '📖 Grimório' para inspecionar termos de animes.")
    print("  2. Clicar em '🎨 Visualizar' para alternar entre Escuro, Claro, Alto Contraste e MS-DOS.")
    print("  3. Clicar em '⚙' para abrir configuracoes, trocar idioma e limpar cache.")
    print("  4. Clicar em 'INICIAR TRADUÇÃO' para simular a esteira de progresso.")

    app.mainloop()


if __name__ == "__main__":
    executar_prototipo()
