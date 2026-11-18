import os
import shutil

from .processador_base import ProcessadorArquivoBase
from ..manipulador_mkv import ManipuladorMkv
from ..manipulador_midia import ManipuladorMidiaPort, AdaptadorMkvToolNixFFmpeg, TrilhaMidia
from ..config import GerenciadorConfig
from ..config_usuario import PreferenciasUsuario
from ..idiomas import Idiomas
from ..transcritores import MotorWhisperfile


class ProcessadorMkv(ProcessadorArquivoBase):
    """Estratégia específica para arquivos de vídeo MKV com suporte a fallback de transcrição ASR."""

    def __init__(
        self,
        *args,
        manipulador_midia: ManipuladorMidiaPort | None = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._transcrito_por_ia = False
        self._manipulador_midia: ManipuladorMidiaPort = (
            manipulador_midia
            if manipulador_midia is not None
            else AdaptadorMkvToolNixFFmpeg(logger=self.log)
        )

    @property
    def manipulador_midia(self) -> ManipuladorMidiaPort:
        """Retorna o manipulador de mídia em uso."""
        return self._manipulador_midia

    def _extrair_legenda_via_porta(self, origem: str, destino_dir: str, idioma_origem: str) -> tuple[str, str]:
        """Extrai a legenda de origem utilizando o manipulador de mídia injetado."""
        trilhas = self._manipulador_midia.listar_trilhas(origem)
        trilhas_sub = [
            t for t in trilhas
            if t.tipo == "subtitles" and t.formato in (".ass", ".srt")
        ]
        if not trilhas_sub:
            raise ValueError("Nenhuma legenda (.ass ou .srt) encontrada neste vídeo.")

        trilha_escolhida = None
        pref = (idioma_origem or "").strip().lower()
        if pref and pref != "auto":
            for t in trilhas_sub:
                if t.idioma.lower() == pref:
                    trilha_escolhida = t
                    break
        if trilha_escolhida is None:
            trilha_escolhida = trilhas_sub[0]

        idioma_real = trilha_escolhida.idioma or "und"
        if pref and pref != "auto" and pref != idioma_real.lower():
            self.log(f"[AVISO] Idioma '{pref}' ausente neste vídeo; usando a faixa '{idioma_real}'.")

        ext = trilha_escolhida.formato if trilha_escolhida.formato in (".ass", ".srt") else ".ass"
        nome_base = os.path.basename(origem).rsplit(".", 1)[0]
        caminho_extraido = os.path.join(destino_dir, f"{nome_base}_ORIGINAL{ext}")

        self.log("Extraindo trilha original para processamento...")
        caminho_final = self._manipulador_midia.extrair_legenda(origem, trilha_escolhida.id, caminho_extraido)
        return caminho_final, idioma_real

    def prepare(self, origem, idioma_origem):
        self._transcrito_por_ia = False
        if (
            isinstance(self._manipulador_midia, AdaptadorMkvToolNixFFmpeg)
            and not GerenciadorConfig.check_dependencies()
        ):
            if self.ask_dependencies is not None:
                self.log("[AVISO] MKVToolNix não encontrado. Aguardando configuração pelo usuário...")
                if not self.ask_dependencies():
                    self.log("[AVISO] Processamento abortado. MKVToolNix não configurado.")
                    return None, None
            if not GerenciadorConfig.check_dependencies():
                self.log("[AVISO] Processamento abortado. MKVToolNix não encontrado.")
                return None, None

        destino_dir = self.output_dir or os.path.dirname(origem)
        if destino_dir:
            os.makedirs(destino_dir, exist_ok=True)
        forcar_whisper = bool(PreferenciasUsuario.obter("forcar_transcricao", False))

        if not forcar_whisper:
            self.log(f"[Etapa 1/3] Extração de Mídia via MKVToolNix (Idioma: {idioma_origem or 'Qualquer'})")
            try:
                if isinstance(self._manipulador_midia, AdaptadorMkvToolNixFFmpeg):
                    return ManipuladorMkv.extrair_legenda(origem, destino_dir, idioma_origem, self.log)
                return self._extrair_legenda_via_porta(origem, destino_dir, idioma_origem)
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

        if isinstance(self._manipulador_midia, AdaptadorMkvToolNixFFmpeg):
            caminho_audio, idioma_trilha = ManipuladorMkv.extrair_audio(origem, destino_dir, idioma_origem, self.log)
        else:
            nome_base = os.path.basename(origem).rsplit(".", 1)[0]
            caminho_audio_dest = os.path.join(destino_dir, f"{nome_base}_ORIGINAL_AUDIO.wav")
            caminho_audio = self._manipulador_midia.extrair_audio(origem, caminho_audio_dest)
            trilhas = self._manipulador_midia.listar_trilhas(origem)
            trilhas_audio = [t for t in trilhas if t.tipo == "audio"]
            idioma_trilha = trilhas_audio[0].idioma if trilhas_audio else (idioma_origem or "und")

        idioma_efetivo = idioma_trilha
        if idioma_trilha in ("und", "auto", "") and idioma_origem and idioma_origem not in ("auto", "und"):
            idioma_efetivo = idioma_origem

        try:
            self.log(f"Transcrevendo áudio via Whisperfile (Idioma: {idioma_efetivo or 'auto'})...")
            resultado = motor_whisper.transcrever(
                caminho_audio,
                idioma=idioma_efetivo,
                cancelado_cb=lambda: not self.is_running(),
            )
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
        destino_dir = self.output_dir or os.path.dirname(origem)
        if destino_dir:
            os.makedirs(destino_dir, exist_ok=True)
        nome_base = os.path.basename(arq_trabalho)
        extensao = nome_base.rsplit('.', 1)[-1].lower()
        if extensao in ("mkv", "mp4", "webm", "avi", "wmv"):
            extensao = "srt"
        nome_sem_ext = nome_base.rsplit('.', 1)[0].replace("_ORIGINAL", "")
        ext_video = os.path.splitext(origem)[1].lower() or ".mkv"
        sufixo = (Idiomas.normalizar_destino(idioma_destino) or Idiomas.para_google(idioma_destino) or "pt").upper()

        politica_saida = self._resolver_politica_saida_video(origem)
        if politica_saida == "manter_original" and ext_video != ".mkv":
            if ext_video in (".mp4", ".webm"):
                extensao = "srt"
                caminho_video = os.path.join(destino_dir, f"{nome_sem_ext}_{sufixo}{ext_video}")
            else:
                # Para .avi e .wmv no modo manter_original, preserva-se apenas a legenda .srt externa
                extensao = "srt"
                caminho_video = None
        else:
            caminho_video = os.path.join(destino_dir, f"{nome_sem_ext}_{sufixo}.mkv")

        return {
            'legenda': os.path.join(destino_dir, f"{nome_sem_ext}_{sufixo}.{extensao}"),
            'video': caminho_video,
        }

    def get_translation_message(self) -> str:
        return "[Etapa 2/3] Tradução via Motor Injetado (Pysubs2)"

    def finalize(self, origem, legenda_traduzida, caminhos_saida, idioma_destino, arq_trabalho, manter_legenda):
        self.log("[Etapa 3/3] Multiplexação e Limpeza")
        caminho_mkv_saida = caminhos_saida.get('video')

        if caminho_mkv_saida:
            self._manipulador_midia.embutir_legenda(
                video=origem,
                legenda=legenda_traduzida,
                saida=caminho_mkv_saida,
                idioma=idioma_destino,
            )

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
