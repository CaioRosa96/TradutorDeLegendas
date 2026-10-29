import os
import json
import shutil
import subprocess

from .config import GerenciadorConfig
from .idiomas import Idiomas


class ManipuladorMkv:
    """Encapsula operações de extração e multiplexação de legendas e áudio em arquivos MKV."""

    @staticmethod
    def _detectar_formato(codec, codec_id):
        """Retorna a extensão do formato de legenda ou None se não for suportado."""
        formatos = {
            ".ass": ["ass", "substation", "s_text/ass"],
            ".srt": ["srt", "s_text/utf8", "subrip", "mov_text", "tx3g", "webvtt", "wvtt", "s_text/webvtt"]
        }

        texto_busca = f"{codec} {codec_id}".lower()
        for ext, palavras_chave in formatos.items():
            if any(palavra in texto_busca for palavra in palavras_chave):
                return ext
        return None

    @staticmethod
    def _detectar_formato_audio(codec, codec_id):
        """Retorna a extensão de áudio correspondente ao codec da trilha."""
        formatos_audio = {
            ".wav": ["pcm", "a_pcm"],
            ".flac": ["flac", "a_flac"],
            ".mp3": ["mp3", "mpeg/l3", "a_mpeg/l3"],
            ".ogg": ["vorbis", "a_vorbis"],
            ".opus": ["opus", "a_opus"],
            ".aac": ["aac", "a_aac"],
            ".ac3": ["ac3", "eac3", "a_ac3", "a_eac3"],
        }
        texto_busca = f"{codec} {codec_id}".lower()
        for ext, palavras_chave in formatos_audio.items():
            if any(palavra in texto_busca for palavra in palavras_chave):
                return ext
        return ".mka"

    @staticmethod
    def _localizar_ffmpeg():
        """Localiza um binário ffmpeg portátil ou no PATH do sistema, se disponível."""
        for pasta_base in (GerenciadorConfig.DIRETORIO_EXECUCAO, GerenciadorConfig.DIRETORIO_RECURSOS):
            for sub in ("bin", "mkvtoolnix"):
                candidato = os.path.join(pasta_base, sub, "ffmpeg.exe")
                if os.path.isfile(candidato):
                    return os.path.abspath(candidato)
        no_path = shutil.which("ffmpeg")
        return os.path.abspath(no_path) if no_path else None

    @staticmethod
    def listar_idiomas_legendas(caminhos_mkv):
        """Retorna uma lista de idiomas únicos encontrados nos arquivos MKV fornecidos."""
        if not GerenciadorConfig.check_dependencies():
            return []

        mkvmerge, _ = GerenciadorConfig.get_mkv_bins()
        idiomas = set()

        for mkv in caminhos_mkv:
            try:
                comando = [mkvmerge, "-J", mkv]
                resultado = subprocess.run(
                    comando, capture_output=True, text=True,
                    check=True, encoding='utf-8', errors='ignore',
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
                )
                info = json.loads(resultado.stdout)

                encontrou_legenda = False
                idiomas_audio = set()
                for track in info.get("tracks", []):
                    if track.get("type") == "subtitles":
                        codec = track.get("codec", "").lower()
                        codec_id = track.get("properties", {}).get("codec_id", "").lower()
                        if ManipuladorMkv._detectar_formato(codec, codec_id):
                            lang = track.get("properties", {}).get("language", "und").lower()
                            idiomas.add(lang)
                            encontrou_legenda = True
                    elif track.get("type") == "audio":
                        lang = track.get("properties", {}).get("language", "und").lower()
                        idiomas_audio.add(lang)
                if not encontrou_legenda:
                    idiomas.update(idiomas_audio)
            except Exception:
                continue

        return sorted(list(idiomas))

    @staticmethod
    def identificar_mkvs_sem_legenda(caminhos_mkv: list) -> set:
        """Retorna o conjunto de caminhos MKV que não possuem trilha de legenda compatível (.ass ou .srt)."""
        if not GerenciadorConfig.check_dependencies():
            return set()

        mkvmerge, _ = GerenciadorConfig.get_mkv_bins()
        sem_legenda = set()

        for mkv in caminhos_mkv:
            try:
                resultado = subprocess.run(
                    [mkvmerge, "-J", mkv],
                    capture_output=True,
                    text=True,
                    check=True,
                    encoding="utf-8",
                    errors="ignore",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                info = json.loads(resultado.stdout)
                tem_legenda = any(
                    track.get("type") == "subtitles"
                    and ManipuladorMkv._detectar_formato(
                        track.get("codec", "").lower(),
                        track.get("properties", {}).get("codec_id", "").lower(),
                    )
                    for track in info.get("tracks", [])
                )
                if not tem_legenda:
                    sem_legenda.add(mkv)
            except Exception:
                if mkv.lower().endswith((".mp4", ".webm", ".avi", ".wmv")):
                    sem_legenda.add(mkv)
                continue

        return sem_legenda

    @staticmethod
    def extrair_legenda(caminho_mkv, pasta_destino, idioma_preferido, logger):
        """Extrai a trilha de legenda preferida de um arquivo MKV."""
        mkvmerge, mkvextract = GerenciadorConfig.get_mkv_bins()
        logger("Analisando estrutura do vídeo MKV...")

        comando_info = [mkvmerge, "-J", caminho_mkv]
        try:
            resultado = subprocess.run(
                comando_info, capture_output=True, text=True,
                check=True, encoding='utf-8', errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            info = json.loads(resultado.stdout)
        except Exception as e:
            if not caminho_mkv.lower().endswith(".mkv"):
                raise ValueError("Nenhuma legenda (.ass ou .srt) encontrada neste vídeo.")
            raise RuntimeError(f"Erro ao ler MKV (Verifique dependências): {e}")

        track_id, selected_ext, idioma_real = ManipuladorMkv._selecionar_trilha(info, idioma_preferido)

        if track_id is None:
            raise ValueError("Nenhuma legenda (.ass ou .srt) encontrada neste MKV.")

        pref = (idioma_preferido or "").strip().lower()
        if pref and pref != "auto" and pref != idioma_real:
            logger(f"[AVISO] Idioma '{pref}' ausente neste vídeo; usando a faixa '{idioma_real}'.")

        nome_base = os.path.basename(caminho_mkv).rsplit('.', 1)[0]
        caminho_extraido = os.path.join(pasta_destino, f"{nome_base}_ORIGINAL{selected_ext}")

        logger("Extraindo trilha original para processamento...")
        if not caminho_mkv.lower().endswith(".mkv"):
            ffmpeg_bin = ManipuladorMkv._localizar_ffmpeg()
            if ffmpeg_bin:
                cmd_ff = [ffmpeg_bin, "-y", "-i", caminho_mkv, "-map", f"0:{track_id}", caminho_extraido]
                res_ff = subprocess.run(
                    cmd_ff, check=False, capture_output=True, text=True,
                    encoding="utf-8", errors="ignore",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                if res_ff.returncode == 0:
                    return caminho_extraido, idioma_real
                raise ValueError("Nenhuma legenda compatível pôde ser extraída deste vídeo.")

        comando_extrair = [mkvextract, "tracks", caminho_mkv, f"{track_id}:{caminho_extraido}"]
        resultado_extrair = subprocess.run(
            comando_extrair, check=False, capture_output=True, text=True,
            encoding='utf-8', errors='ignore',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if resultado_extrair.returncode not in (0, 1):
            erro_msg = resultado_extrair.stderr.strip() or f"Código de saída {resultado_extrair.returncode}"
            raise RuntimeError(f"Erro ao extrair trilha do MKV: {erro_msg}")
        return caminho_extraido, idioma_real

    @staticmethod
    def extrair_audio(caminho_mkv, pasta_destino, idioma_preferido, logger):
        """Extrai a trilha de áudio preferida do MKV para transcrição (preferindo WAV 16 kHz mono)."""
        mkvmerge, mkvextract = GerenciadorConfig.get_mkv_bins()
        logger("Analisando trilhas de áudio do vídeo MKV...")

        comando_info = [mkvmerge, "-J", caminho_mkv]
        info = None
        try:
            resultado = subprocess.run(
                comando_info, capture_output=True, text=True,
                check=True, encoding='utf-8', errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            info = json.loads(resultado.stdout)
        except Exception as e:
            if caminho_mkv.lower().endswith(".mkv"):
                raise RuntimeError(f"Erro ao ler MKV (Verifique dependências): {e}")

        if info is not None:
            track_id, selected_ext, idioma_real = ManipuladorMkv._selecionar_trilha_audio(info, idioma_preferido)
            if track_id is None:
                raise ValueError("Nenhuma trilha de áudio encontrada neste MKV.")
            mapa_audio = f"0:{track_id}"
        else:
            track_id = 0
            selected_ext = ".wav"
            pref_limpo = (idioma_preferido or "").strip().lower()
            idioma_real = pref_limpo if pref_limpo and pref_limpo != "auto" else "und"
            mapa_audio = "0:a:0"

        pref = (idioma_preferido or "").strip().lower()
        if pref and pref != "auto" and pref != idioma_real:
            logger(f"[AVISO] Idioma de áudio '{pref}' ausente neste vídeo; usando a faixa '{idioma_real}'.")

        nome_base = os.path.basename(caminho_mkv).rsplit('.', 1)[0]
        ffmpeg_bin = ManipuladorMkv._localizar_ffmpeg()

        if ffmpeg_bin:
            caminho_extraido = os.path.join(pasta_destino, f"{nome_base}_ORIGINAL_AUDIO.wav")
            logger("Extraindo e convertendo áudio para WAV 16 kHz mono (FFmpeg)...")
            comando_ffmpeg = [
                ffmpeg_bin, "-y", "-i", caminho_mkv,
                "-map", mapa_audio,
                "-vn", "-af", "highpass=f=100,lowpass=f=7500,dynaudnorm",
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                caminho_extraido,
            ]
            res_ff = subprocess.run(
                comando_ffmpeg, check=False, capture_output=True, text=True,
                encoding='utf-8', errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if res_ff.returncode != 0:
                erro_msg = res_ff.stderr.strip() or f"Código de saída {res_ff.returncode}"
                raise RuntimeError(f"Erro ao converter áudio com FFmpeg: {erro_msg}")
            return caminho_extraido, idioma_real

        caminho_extraido = os.path.join(pasta_destino, f"{nome_base}_ORIGINAL_AUDIO{selected_ext}")
        logger("Extraindo trilha de áudio original para transcrição...")
        comando_extrair = [mkvextract, "tracks", caminho_mkv, f"{track_id}:{caminho_extraido}"]
        resultado_extrair = subprocess.run(
            comando_extrair, check=False, capture_output=True, text=True,
            encoding='utf-8', errors='ignore',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        if resultado_extrair.returncode not in (0, 1):
            erro_msg = resultado_extrair.stderr.strip() or f"Código de saída {resultado_extrair.returncode}"
            raise RuntimeError(f"Erro ao extrair áudio do MKV: {erro_msg}")
        return caminho_extraido, idioma_real

    @staticmethod
    def _selecionar_trilha(info, idioma_preferido):
        """Seleciona a melhor trilha de legenda do MKV com base no idioma preferido."""
        track_id = None
        fallback_track_id = None
        selected_ext = ".ass"
        fallback_ext = ".ass"
        selected_lang = "und"
        fallback_lang = "und"

        for track in info.get("tracks", []):
            if track.get("type") != "subtitles":
                continue

            codec = track.get("codec", "").lower()
            codec_id = track.get("properties", {}).get("codec_id", "").lower()
            lang = track.get("properties", {}).get("language", "und").lower() or "und"

            ext = ManipuladorMkv._detectar_formato(codec, codec_id)
            if ext is None:
                continue

            if fallback_track_id is None:
                fallback_track_id = track["id"]
                fallback_ext = ext
                fallback_lang = lang

            if idioma_preferido and lang == idioma_preferido.lower():
                track_id = track["id"]
                selected_ext = ext
                selected_lang = lang
                break

        if track_id is None:
            return fallback_track_id, fallback_ext, fallback_lang

        return track_id, selected_ext, selected_lang

    @staticmethod
    def _selecionar_trilha_audio(info, idioma_preferido):
        """Seleciona a trilha de áudio do MKV priorizando o idioma solicitado."""
        track_id = None
        fallback_track_id = None
        selected_ext = ".mka"
        fallback_ext = ".mka"
        selected_lang = "und"
        fallback_lang = "und"

        for track in info.get("tracks", []):
            if track.get("type") != "audio":
                continue

            codec = track.get("codec", "").lower()
            codec_id = track.get("properties", {}).get("codec_id", "").lower()
            lang = track.get("properties", {}).get("language", "und").lower() or "und"
            ext = ManipuladorMkv._detectar_formato_audio(codec, codec_id)

            if fallback_track_id is None:
                fallback_track_id = track["id"]
                fallback_ext = ext
                fallback_lang = lang

            if idioma_preferido and lang == idioma_preferido.lower():
                track_id = track["id"]
                selected_ext = ext
                selected_lang = lang
                break

        if track_id is None:
            return fallback_track_id, fallback_ext, fallback_lang

        return track_id, selected_ext, selected_lang

    @staticmethod
    def embutir_legenda(caminho_mkv_original, caminho_legenda_traduzida, caminho_saida, idioma_destino, logger):
        """Embute a legenda traduzida no contêiner de saída (.mkv via mkvmerge/ffmpeg, .mp4/.webm via ffmpeg)."""
        codigo_mkv, nome_trilha = Idiomas.destino_para_mkv(idioma_destino)
        saida_lower = caminho_saida.lower()

        logger(f"Criando novo contêiner de vídeo ({os.path.basename(caminho_saida)})...")

        if saida_lower.endswith((".mp4", ".webm")):
            ffmpeg_bin = ManipuladorMkv._localizar_ffmpeg()
            if not ffmpeg_bin:
                raise RuntimeError("FFmpeg não encontrado para multiplexar contêiner .mp4/.webm.")
            codec_legenda = "mov_text" if saida_lower.endswith(".mp4") else "webvtt"
            cmd_ff = [
                ffmpeg_bin, "-y",
                "-i", caminho_mkv_original,
                "-i", caminho_legenda_traduzida,
                "-map", "0:v",
                "-map", "0:a?",
                "-map", "1:0",
                "-c:v", "copy",
                "-c:a", "copy",
                "-c:s", codec_legenda,
                "-metadata:s:s:0", f"language={codigo_mkv}",
                "-metadata:s:s:0", f"title={nome_trilha}",
                "-disposition:s:0", "default",
                caminho_saida,
            ]
            res_ff = subprocess.run(
                cmd_ff, check=False, capture_output=True, text=True,
                encoding="utf-8", errors="ignore", timeout=600,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            if res_ff.returncode != 0:
                if os.path.exists(caminho_saida):
                    try:
                        os.remove(caminho_saida)
                    except OSError:
                        pass
                detalhe = res_ff.stderr.strip() or f"Código de saída {res_ff.returncode}"
                raise RuntimeError(f"Erro ao embutir legenda no contêiner {os.path.splitext(caminho_saida)[1]}: {detalhe}")
            return caminho_saida

        mkvmerge, _ = GerenciadorConfig.get_mkv_bins()
        comando_mux = [
            mkvmerge,
            "-o", caminho_saida,
            caminho_mkv_original,
            "--default-track-flag", "0:yes",
            "--language", f"0:{codigo_mkv}",
            "--track-name", f"0:{nome_trilha}",
            caminho_legenda_traduzida
        ]

        try:
            resultado_mux = subprocess.run(
                comando_mux, check=False, capture_output=True, text=True,
                encoding='utf-8', errors='ignore', timeout=600,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if resultado_mux.returncode not in (0, 1):
                ffmpeg_bin = ManipuladorMkv._localizar_ffmpeg() if not caminho_mkv_original.lower().endswith(".mkv") else None
                if ffmpeg_bin:
                    codec_sub = "ass" if caminho_legenda_traduzida.lower().endswith(".ass") else "srt"
                    cmd_fallback = [
                        ffmpeg_bin, "-y",
                        "-i", caminho_mkv_original,
                        "-i", caminho_legenda_traduzida,
                        "-map", "0:v",
                        "-map", "0:a?",
                        "-map", "1:0",
                        "-c:v", "copy",
                        "-c:a", "copy",
                        "-c:s", codec_sub,
                        "-metadata:s:s:0", f"language={codigo_mkv}",
                        "-metadata:s:s:0", f"title={nome_trilha}",
                        "-disposition:s:0", "default",
                        caminho_saida,
                    ]
                    res_fb = subprocess.run(
                        cmd_fallback, check=False, capture_output=True, text=True,
                        encoding="utf-8", errors="ignore", timeout=600,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                    )
                    if res_fb.returncode == 0:
                        return caminho_saida

                if os.path.exists(caminho_saida):
                    try:
                        os.remove(caminho_saida)
                    except OSError:
                        pass
                erro_detalhe = resultado_mux.stderr.strip() or f"Código de saída {resultado_mux.returncode}"
                raise RuntimeError(f"Erro ao embutir a legenda traduzida no MKV final: {erro_detalhe}")
            if resultado_mux.returncode == 1:
                logger("[AVISO] mkvmerge concluiu a multiplexação com alertas (warnings).")
            return caminho_saida
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Erro ao executar mkvmerge: {e}")
