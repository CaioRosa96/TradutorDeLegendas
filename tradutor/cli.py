"""Interface de linha de comando (Headless CLI) para o TradutorLegendas26."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from enum import IntEnum
from typing import Optional, Sequence

from .config import GerenciadorConfig
from .config_usuario import PreferenciasUsuario
from .estrategias.fabrica import FabricaProcessadores
from .idiomas import Idiomas
from .logger import app_logger
from .manipulador_mkv import ManipuladorMkv
from .tradutores.base import ExcecaoDisjuntorAberto


class CodigoSaidaCli(IntEnum):
    """Codigos de saida padronizados da CLI."""

    SUCESSO = 0
    ERRO_FATAL_ARQUIVO = 1
    IGNORADO_IDIOMA_EXISTENTE = 2
    ERRO_REDE_OU_DISJUNTOR = 3
    SEM_LEGENDA_DISPONIVEL = 4
    DEPENDENCIA_AUSENTE = 5


@dataclass(frozen=True, slots=True)
class ResultadoExecucaoCli:
    """Metadados do resultado emitidos estruturadamente no stdout."""

    status: str
    exit_code: int
    input_path: str
    output_video_path: Optional[str]
    output_subtitle_path: Optional[str]
    source_lang_detected: Optional[str]
    target_lang: str
    anime_title_used: Optional[str]
    glossary_terms_count: int
    used_whisper_transcription: bool
    elapsed_seconds: float
    error_message: Optional[str] = None


def construir_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        prog="TradutorLegendas26",
        description="Interface de Linha de Comando Headless do Tradutor de Legendas.",
    )
    parser.add_argument("--headless", action="store_true", help="Executa sem interface grafica.")
    parser.add_argument("-i", "--input", required=True, help="Caminho do arquivo de video ou legenda.")
    parser.add_argument("-o", "--output-dir", default=None, help="Diretorio de saida customizado.")
    parser.add_argument("-s", "--src", default="auto", help="Idioma de origem (padrao: auto).")
    parser.add_argument("-d", "--dest", default="pt", help="Idioma de destino (padrao: pt).")
    parser.add_argument("--anime-title", default=None, help="Titulo canonico do anime para o glossario.")
    parser.add_argument("--anilist-id", type=int, default=None, help="ID do anime no AniList.")
    parser.add_argument(
        "--skip-if-target-exists",
        action="store_true",
        help="Retorna codigo 2 se o video ja possuir legenda no idioma de destino.",
    )
    parser.add_argument("--keep-external-sub", action="store_true", help="Mantem arquivo de legenda externo.")
    parser.add_argument("--enable-whisper", action="store_true", help="Ativa transcricao Whisperfile se sem legenda.")
    parser.add_argument("--force-whisper", action="store_true", help="Forca transcricao via Whisperfile ignorando legendas embutidas.")
    parser.add_argument("-y", "--overwrite", action="store_true", help="Sobrescreve arquivos de saida sem perguntar.")
    parser.add_argument(
        "--json-output",
        "--json",
        dest="json_output",
        action="store_true",
        help="Imprime JSON de resultado no stdout.",
    )
    return parser


def executar_cli(args_list: Optional[Sequence[str]] = None) -> int:
    """Ponto de entrada da execucao em modo headless."""
    parser = construir_parser()
    args = parser.parse_args(args_list)

    if getattr(args, "force_whisper", False):
        args.enable_whisper = True

    inicio_tempo = time.time()
    input_path = os.path.abspath(args.input)
    json_output = bool(args.json_output)

    def log(msg: str) -> None:
        app_logger.info(msg)
        if json_output:
            sys.stderr.write(str(msg) + "\n")
            sys.stderr.flush()
        else:
            print(msg)

    def responder(resultado: ResultadoExecucaoCli) -> int:
        if json_output:
            sys.stdout.write(json.dumps(asdict(resultado), ensure_ascii=False) + "\n")
            sys.stdout.flush()
        else:
            log(f"Status: {resultado.status} (Exit Code: {resultado.exit_code})")
            if resultado.error_message:
                log(f"Erro: {resultado.error_message}")
            if resultado.output_video_path:
                log(f"Video final: {resultado.output_video_path}")
            if resultado.output_subtitle_path:
                log(f"Legenda final: {resultado.output_subtitle_path}")
        return resultado.exit_code

    # 0. Sanitizacao e validacao antecipada dos parametros de idioma
    dest_norm = Idiomas.normalizar_destino(args.dest)
    if not dest_norm:
        return responder(
            ResultadoExecucaoCli(
                status="ERRO_FATAL_ARQUIVO",
                exit_code=CodigoSaidaCli.ERRO_FATAL_ARQUIVO,
                input_path=input_path,
                output_video_path=None,
                output_subtitle_path=None,
                source_lang_detected=None,
                target_lang=args.dest,
                anime_title_used=args.anime_title,
                glossary_terms_count=0,
                used_whisper_transcription=False,
                elapsed_seconds=round(time.time() - inicio_tempo, 2),
                error_message=f"Idioma de destino invalido: '{args.dest}'. Destinos suportados: {', '.join(Idiomas.DESTINOS_SUPORTADOS)}",
            )
        )
    src_norm = Idiomas.para_google(args.src)

    # 1. Validacao de existencia do arquivo
    if not os.path.isfile(input_path):
        return responder(
            ResultadoExecucaoCli(
                status="ERRO_FATAL_ARQUIVO",
                exit_code=CodigoSaidaCli.ERRO_FATAL_ARQUIVO,
                input_path=input_path,
                output_video_path=None,
                output_subtitle_path=None,
                source_lang_detected=src_norm,
                target_lang=dest_norm,
                anime_title_used=args.anime_title,
                glossary_terms_count=0,
                used_whisper_transcription=False,
                elapsed_seconds=round(time.time() - inicio_tempo, 2),
                error_message=f"Arquivo de entrada inexistente: {input_path}",
            )
        )

    ext = os.path.splitext(input_path)[1].lower()
    is_video = ext in FabricaProcessadores.EXTENSOES_VIDEO

    # 2. Validacao de dependencias externas para videos
    if is_video and not GerenciadorConfig.check_dependencies():
        return responder(
            ResultadoExecucaoCli(
                status="DEPENDENCIA_AUSENTE",
                exit_code=CodigoSaidaCli.DEPENDENCIA_AUSENTE,
                input_path=input_path,
                output_video_path=None,
                output_subtitle_path=None,
                source_lang_detected=src_norm,
                target_lang=dest_norm,
                anime_title_used=args.anime_title,
                glossary_terms_count=0,
                used_whisper_transcription=False,
                elapsed_seconds=round(time.time() - inicio_tempo, 2),
                error_message="MKVToolNix nao encontrado ou dependencias ausentes.",
            )
        )

    # 3. Verificacao de legenda existente (--skip-if-target-exists)
    if is_video and args.skip_if_target_exists:
        try:
            langs = ManipuladorMkv.listar_idiomas_legendas([input_path])
            for l in langs:
                if Idiomas.para_google(l) == dest_norm:
                    return responder(
                        ResultadoExecucaoCli(
                            status="IGNORADO_IDIOMA_EXISTENTE",
                            exit_code=CodigoSaidaCli.IGNORADO_IDIOMA_EXISTENTE,
                            input_path=input_path,
                            output_video_path=input_path,
                            output_subtitle_path=None,
                            source_lang_detected=l,
                            target_lang=dest_norm,
                            anime_title_used=args.anime_title,
                            glossary_terms_count=0,
                            used_whisper_transcription=False,
                            elapsed_seconds=round(time.time() - inicio_tempo, 2),
                            error_message=None,
                        )
                    )
        except Exception as e:
            app_logger.warning(f"Falha ao checar trilhas existentes: {e}")

    # 4. Verificacao de legendas compativeis
    if is_video:
        try:
            sem_legenda = ManipuladorMkv.identificar_mkvs_sem_legenda([input_path])
            if input_path in sem_legenda and not args.enable_whisper:
                return responder(
                    ResultadoExecucaoCli(
                        status="SEM_LEGENDA_DISPONIVEL",
                        exit_code=CodigoSaidaCli.SEM_LEGENDA_DISPONIVEL,
                        input_path=input_path,
                        output_video_path=None,
                        output_subtitle_path=None,
                        source_lang_detected=src_norm,
                        target_lang=dest_norm,
                        anime_title_used=args.anime_title,
                        glossary_terms_count=0,
                        used_whisper_transcription=False,
                        elapsed_seconds=round(time.time() - inicio_tempo, 2),
                        error_message="O video nao possui legendas embutidas e Whisper esta desativado.",
                    )
                )
        except Exception as e:
            app_logger.warning(f"Falha ao inspecionar presenca de legendas: {e}")

    # 5. Pre-alimentacao do glossario via AniList se solicitado
    glossary_count = 0
    if args.anime_title or args.anilist_id is not None:
        try:
            from .anilist import auto_alimentar
            caminho_gloss = auto_alimentar(
                input_path,
                anime_title=args.anime_title,
                anilist_id=args.anilist_id,
            )
            if caminho_gloss and os.path.isfile(caminho_gloss):
                with open(caminho_gloss, "r", encoding="utf-8") as f:
                    glossary_count = sum(1 for line in f if line.strip() and not line.strip().startswith("#"))
        except Exception as e:
            log(f"[AVISO] Falha ao auto-alimentar glossario: {e}")

    # 6. Execucao do processador
    orig_forcar = PreferenciasUsuario.obter("forcar_transcricao", False)
    if getattr(args, "force_whisper", False):
        PreferenciasUsuario.definir("forcar_transcricao", True)
        args.enable_whisper = True

    try:
        processador = FabricaProcessadores.get_processor(
            input_path,
            log_cb=log,
            progress_cb=lambda c, t: None,
            ask_overwrite_cb=lambda _: bool(args.overwrite),
            is_running_cb=lambda: True,
            ask_whisper_cb=lambda _: bool(args.enable_whisper),
            ask_output_format_cb=lambda *_: "converter_mkv",
            output_dir=args.output_dir,
        )

        sucesso = processador.process(
            input_path,
            idioma_origem=src_norm,
            idioma_destino=dest_norm,
            manter_legenda=args.keep_external_sub,
        )

        elapsed = round(time.time() - inicio_tempo, 2)
        raw_detected = getattr(processador, "ultimo_idioma_detectado", None)
        detected_src = raw_detected if isinstance(raw_detected, str) and raw_detected else src_norm
        if sucesso:
            ultimos = getattr(processador, "ultimos_caminhos_saida", None)
            caminhos = ultimos if isinstance(ultimos, dict) and ultimos else processador.get_output_paths(input_path, dest_norm, input_path)
            out_video = caminhos.get("video")
            out_sub = caminhos.get("legenda") if (args.keep_external_sub or not is_video) else None
            used_whisper = bool(getattr(processador, "_transcrito_por_ia", False))
            return responder(
                ResultadoExecucaoCli(
                    status="SUCESSO",
                    exit_code=CodigoSaidaCli.SUCESSO,
                    input_path=input_path,
                    output_video_path=out_video,
                    output_subtitle_path=out_sub,
                    source_lang_detected=detected_src,
                    target_lang=dest_norm,
                    anime_title_used=args.anime_title,
                    glossary_terms_count=glossary_count,
                    used_whisper_transcription=used_whisper,
                    elapsed_seconds=elapsed,
                    error_message=None,
                )
            )
        else:
            return responder(
                ResultadoExecucaoCli(
                    status="ERRO_FATAL_ARQUIVO",
                    exit_code=CodigoSaidaCli.ERRO_FATAL_ARQUIVO,
                    input_path=input_path,
                    output_video_path=None,
                    output_subtitle_path=None,
                    source_lang_detected=detected_src,
                    target_lang=dest_norm,
                    anime_title_used=args.anime_title,
                    glossary_terms_count=glossary_count,
                    used_whisper_transcription=False,
                    elapsed_seconds=elapsed,
                    error_message="Processamento nao concluido.",
                )
            )

    except ExcecaoDisjuntorAberto as e:
        return responder(
            ResultadoExecucaoCli(
                status="ERRO_REDE_OU_DISJUNTOR",
                exit_code=CodigoSaidaCli.ERRO_REDE_OU_DISJUNTOR,
                input_path=input_path,
                output_video_path=None,
                output_subtitle_path=None,
                source_lang_detected=src_norm,
                target_lang=dest_norm,
                anime_title_used=args.anime_title,
                glossary_terms_count=glossary_count,
                used_whisper_transcription=False,
                elapsed_seconds=round(time.time() - inicio_tempo, 2),
                error_message=f"Circuit Breaker aberto: {e}",
            )
        )
    except Exception as e:
        msg = str(e).lower()
        if "circuit breaker" in msg or "disjuntor" in msg or "rate limit" in msg or "conexao" in msg:
            cod = CodigoSaidaCli.ERRO_REDE_OU_DISJUNTOR
            status_str = "ERRO_REDE_OU_DISJUNTOR"
        else:
            cod = CodigoSaidaCli.ERRO_FATAL_ARQUIVO
            status_str = "ERRO_FATAL_ARQUIVO"

        return responder(
            ResultadoExecucaoCli(
                status=status_str,
                exit_code=cod,
                input_path=input_path,
                output_video_path=None,
                output_subtitle_path=None,
                source_lang_detected=src_norm,
                target_lang=dest_norm,
                anime_title_used=args.anime_title,
                glossary_terms_count=glossary_count,
                used_whisper_transcription=False,
                elapsed_seconds=round(time.time() - inicio_tempo, 2),
                error_message=str(e),
            )
        )
    finally:
        if getattr(args, "force_whisper", False):
            PreferenciasUsuario.definir("forcar_transcricao", orig_forcar)
