import os
import shutil

from .processador_base import ProcessadorArquivoBase
from ..manipulador_mkv import ManipuladorMkv
from ..config import GerenciadorConfig
from ..config_usuario import PreferenciasUsuario
from ..transcritores import MotorWhisperfile


class ProcessadorMkv(ProcessadorArquivoBase):
    """Estratégia específica para arquivos de vídeo MKV com suporte a fallback de transcrição ASR."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._transcrito_por_ia = False

    def prepare(self, origem, idioma_origem):
        self._transcrito_por_ia = False
        if not GerenciadorConfig.check_dependencies():
            self.log("[AVISO] Processamento abortado. MKVToolNix não encontrado.")
            return None, None

        destino_dir = os.path.dirname(origem)
        forcar_whisper = bool(PreferenciasUsuario.obter("forcar_transcricao", False))

        if not forcar_whisper:
            self.log(f"[Etapa 1/3] Extração de Mídia via MKVToolNix (Idioma: {idioma_origem or 'Qualquer'})")
            try:
                return ManipuladorMkv.extrair_legenda(origem, destino_dir, idioma_origem, self.log)
            except ValueError as erro_sem_legenda:
                if self.ask_whisper is not None:
                    nome_arq = os.path.basename(origem)
                    self.log(f"[AVISO] Nenhuma legenda encontrada em '{nome_arq}'. Aguardando permissão do usuário para IA local...")
                    if not self.ask_whisper(nome_arq):
                        self.log("-> Transcrição por IA local recusada pelo usuário. Vídeo pulado.")
                        return None, None
                elif not PreferenciasUsuario.obter("transcricao_habilitada", False):
                    self.log("[AVISO] Vídeo sem legendas embutidas e transcrição de áudio desativada.")
                    raise erro_sem_legenda

                self.log("[INFO] Permissão concedida. Acionando transcrição de áudio via IA local (Whisperfile)...")

        self._transcrito_por_ia = True
        return self._transcrever_audio_mkv(origem, destino_dir, idioma_origem)

    def _transcrever_audio_mkv(self, origem: str, destino_dir: str, idioma_origem: str):
        """Extrai o áudio do MKV, executa o Whisperfile e retorna o caminho do .srt temporário."""
        motor_whisper = MotorWhisperfile()
        if not motor_whisper.esta_disponivel():
            raise RuntimeError(
                "Transcrição de áudio autorizada, mas o binário Whisperfile não foi encontrado em bin/ ou mkvtoolnix/."
            )

        caminho_audio, idioma_trilha = ManipuladorMkv.extrair_audio(origem, destino_dir, idioma_origem, self.log)
        idioma_efetivo = idioma_trilha
        if idioma_trilha in ("und", "auto", "") and idioma_origem and idioma_origem not in ("auto", "und"):
            idioma_efetivo = idioma_origem

        try:
            self.log(f"Transcrevendo áudio via Whisperfile (Idioma: {idioma_efetivo or 'auto'})...")
            resultado = motor_whisper.transcrever(caminho_audio, idioma=idioma_efetivo)
            nome_base = os.path.basename(origem).rsplit(".", 1)[0]
            caminho_srt_original = os.path.join(destino_dir, f"{nome_base}_ORIGINAL.srt")

            if os.path.abspath(resultado.caminho_srt) != os.path.abspath(caminho_srt_original):
                shutil.move(resultado.caminho_srt, caminho_srt_original)

            self.log(f"Transcrição concluída em {resultado.duracao_segundos}s.")
            return caminho_srt_original, idioma_efetivo
        finally:
            if caminho_audio and os.path.exists(caminho_audio):
                try:
                    os.remove(caminho_audio)
                except OSError:
                    pass

    def should_skip_if_same_language(self) -> bool:
        return not self._transcrito_por_ia

    def cleanup_temporary(self, arq_trabalho):
        if arq_trabalho and "_ORIGINAL" in arq_trabalho and os.path.exists(arq_trabalho):
            try:
                os.remove(arq_trabalho)
            except OSError:
                pass

    def _resolver_politica_saida_video(self, origem: str) -> str:
        """Determina se o vídeo de entrada deve ser remuxado para .mkv ou manter seu formato original."""
        ext_video = os.path.splitext(origem)[1].lower()
        if ext_video == ".mkv":
            return "converter_mkv"

        politica = PreferenciasUsuario.obter("formato_saida_video", "perguntar")
        if politica == "perguntar" and self.ask_output_format is not None:
            politica = self.ask_output_format(os.path.basename(origem), ext_video)
        return politica if politica in ("converter_mkv", "manter_original") else "converter_mkv"

    def get_output_paths(self, origem, idioma_destino, arq_trabalho) -> dict:
        destino_dir = os.path.dirname(origem)
        nome_base = os.path.basename(arq_trabalho)
        extensao = nome_base.rsplit('.', 1)[-1]
        nome_sem_ext = nome_base.rsplit('.', 1)[0].replace("_ORIGINAL", "")
        ext_video = os.path.splitext(origem)[1].lower() or ".mkv"

        politica_saida = self._resolver_politica_saida_video(origem)
        if politica_saida == "manter_original" and ext_video != ".mkv":
            if ext_video in (".mp4", ".webm"):
                extensao = "srt"
                caminho_video = os.path.join(destino_dir, f"{nome_sem_ext}_{idioma_destino.upper()}{ext_video}")
            else:
                # Para .avi e .wmv no modo manter_original, preserva-se apenas a legenda .srt externa
                extensao = "srt"
                caminho_video = None
        else:
            caminho_video = os.path.join(destino_dir, f"{nome_sem_ext}_{idioma_destino.upper()}.mkv")

        return {
            'legenda': os.path.join(destino_dir, f"{nome_sem_ext}_{idioma_destino.upper()}.{extensao}"),
            'video': caminho_video,
        }

    def get_translation_message(self) -> str:
        return "[Etapa 2/3] Tradução via Motor Injetado (Pysubs2)"

    def finalize(self, origem, legenda_traduzida, caminhos_saida, idioma_destino, arq_trabalho, manter_legenda):
        self.log("[Etapa 3/3] Multiplexação e Limpeza")
        caminho_mkv_saida = caminhos_saida.get('video')

        if caminho_mkv_saida:
            ManipuladorMkv.embutir_legenda(origem, legenda_traduzida, caminho_mkv_saida, idioma_destino, self.log)

        try:
            self.cleanup_temporary(arq_trabalho)
            if caminho_mkv_saida is None:
                self.log("[INFO] Contêiner original mantido; legenda traduzida salva externamente ao lado do vídeo.")
            elif not manter_legenda:
                if os.path.exists(legenda_traduzida):
                    os.remove(legenda_traduzida)
                self.log("Lixo temporário de legendas limpo com sucesso.")
            else:
                self.log("Legenda traduzida mantida na pasta.")
        except Exception as e:
            self.log(f"Aviso: Falha na limpeza: {e}")
