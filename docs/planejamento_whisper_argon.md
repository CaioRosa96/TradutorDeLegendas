# Especificação de Engenharia: Módulo Opcional de Transcrição de Áudio (Whisperfile) — Revisão Argon

**Repositório:** TradutorDeLegendas (TaradutorLegendas26)  
**Destinatário da Execução:** Antigravity IDE / Gemini 4 Argon  
**Diretrizes de Qualidade:** `perfil_caio` §0 (Língua PT-BR e Zero Emojis em Docs), §1 (MVC/OOP ~200 linhas/arquivo e Regression Test Enforcer), §3 (Concorrência sem bloqueio), §4 (UI sem travas), §6 (Declaração de Regras); `AGENTS.md §5.5 e §5.6`.

---

## 1. Visão Geral e Filosofia do Módulo

O objetivo é adicionar a capacidade de **interpretar o áudio de vídeos MKV sem legendas (ou sob demanda), transcrever as falas para `.srt` e repassá-las de forma transparente ao pipeline existente de tradução e multiplexação**.

### Regras Inegociáveis de Design:
1. **Zero-Bloat Core (Ativação Opt-in):**
   - O executável principal e o `requirements.txt` **não devem** incluir bibliotecas pesadas de IA (`torch`, `transformers`, `ctranslate2`, `faster-whisper`).
   - O módulo é 100% opcional (sidecar portátil), ativado nas preferências do usuário.
2. **Motor Portátil Standalone (Mozilla Whisperfile):**
   - Utiliza o binário `whisperfile` da Mozilla (`whisper.cpp` compilado em executável único `.exe` via Cosmopolitan Libc), localizado em `bin/whisper-base.exe`, `mkvtoolnix/whisper-base.exe` ou caminho configurado em `PreferenciasUsuario`.
   - Gera legendas `.srt` com timestamps nativamente via flag `-osrt`.
   - Todas as chamadas `subprocess.run` utilizam obrigatoriamente `creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0` (`AGENTS.md §5.5`).
3. **Compatibilidade de Codecs de Áudio (Conversão WAV 16 kHz Mono):**
   - **Restrição Técnica Crítica:** O `mkvextract` extrai trilhas de áudio no codec original do contêiner (em animes/séries MKV: geralmente **AAC**, **Opus** ou **AC3**). Porém, o `whisperfile` (`whisper.cpp`) decodifica nativamente apenas `.wav` (PCM 16-bit), `.mp3`, `.flac` e `.ogg`.
   - **Solução:**
     - Se a faixa de áudio do MKV já for `FLAC`, `MP3`, `WAV/PCM` ou `OGG/Vorbis`, `ManipuladorMkv.extrair_audio()` usa `mkvextract` diretamente.
     - Se a faixa for `AAC`, `Opus` ou `AC3/EAC3` (ou como caminho universal preferencial quando `ffmpeg.exe` estiver disponível em `bin/`, `mkvtoolnix/` ou `PATH`), converte a faixa de áudio diretamente para `WAV PCM 16 kHz mono` (`-ar 16000 -ac 1 -c:a pcm_s16le`), que é o formato nativo exato exigido pelo Whisper.
4. **Mapeamento de Idiomas ISO-639-2 para ISO-639-1:**
   - Os códigos de 3 letras vindos do MKV (`jpn`, `eng`, `por`) são convertidos via `Idiomas.para_google(idioma_origem)` (normalizando `zh-cn` para `zh`) antes de serem passados à flag `-l` do `whisperfile`.
5. **Trilha Padrão no Remux e Limpeza Determinística:**
   - Ao embutir a legenda traduzida em `ManipuladorMkv.embutir_legenda()`, inclui `--default-track-flag 0:yes`.
   - Tanto o áudio temporário (`_ORIGINAL_AUDIO.*`) quanto a legenda transcrita intermediária (`_ORIGINAL.srt`) são removidos deterministicamente em `ProcessadorMkv.cleanup_temporary()`.

---

## 2. Estrutura de Arquivos e Responsabilidades

### A. Novos Arquivos a Criar:
1. **`tradutor/transcritores/__init__.py`**: Exporta `ITranscritor`, `StatusWhisper`, `ResultadoTranscricao` e `MotorWhisperfile`.
2. **`tradutor/transcritores/base.py`**: Define o enum `StatusWhisper`, o Value Object imutável `@dataclass(frozen=True, slots=True) ResultadoTranscricao` e a interface abstrata `ITranscritor`.
3. **`tradutor/transcritores/whisperfile.py`**: Implementa `MotorWhisperfile(ITranscritor)` usando `GerenciadorConfig.DIRETORIO_EXECUCAO` (nunca `os.getcwd()`, respeitando `AGENTS.md §5.6`) e mapeamento de idioma via `Idiomas.para_google()`.
4. **`tests/unit/test_transcritor_whisper.py`**: Testes unitários offline mockando `subprocess.run` e sistema de arquivos (`tmp_path`), cobrindo resolução de caminhos, conversão de código de idioma (`jpn` -> `ja`), sucesso de transcrição, fallback de nome `.srt`, ausência de binário e erro de processo.

### B. Arquivos Existentes a Modificar Cirurgicamente:
1. **`tradutor/config_usuario.py`**: Adiciona `"transcricao_habilitada": False`, `"caminho_whisperfile": ""` e `"forcar_transcricao": False` em `PreferenciasUsuario.PADRAO`.
2. **`tradutor/manipulador_mkv.py`**:
   - Adiciona `_selecionar_trilha_audio(info, idioma_preferido)` e `extrair_audio(caminho_mkv, pasta_destino, idioma_preferido, logger)` com suporte a `ffmpeg` (para conversão para WAV 16 kHz mono quando o codec for AAC/Opus/AC3) e `mkvextract` (para codecs nativamente suportados pelo Whisperfile como FLAC/Vorbis/MP3/PCM).
   - Adiciona `"--default-track-flag", "0:yes"` em `embutir_legenda`.
3. **`tradutor/estrategias/processador_mkv.py`**:
   - Em `prepare(origem, idioma_origem)`, captura `ValueError` quando o MKV não possui legendas (ou verifica `forcar_transcricao`). Caso `transcricao_habilitada` esteja ativa e `MotorWhisperfile` disponível, extrai o áudio, transcreve para `<nome>_ORIGINAL.srt`, limpa imediatamente o arquivo de áudio bruto e devolve `(caminho_srt_original, idioma_audio)` para o pipeline normal de tradução.

---

## 3. Blocos `SEARCH/REPLACE` Completos

### 3.1 Novos Arquivos do Pacote `tradutor/transcritores/`

```markdown
### FILE: tradutor/transcritores/__init__.py
<<<<<<< SEARCH
=======
from .base import ITranscritor, ResultadoTranscricao, StatusWhisper
from .whisperfile import MotorWhisperfile

__all__ = ["ITranscritor", "StatusWhisper", "ResultadoTranscricao", "MotorWhisperfile"]
>>>>>>>

### FILE: tradutor/transcritores/base.py
<<<<<<< SEARCH
=======
"""Contratos abstratos e objetos de valor para motores de transcrição de áudio (ASR)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class StatusWhisper(Enum):
    PRONTO = "pronto"
    NAO_INSTALADO = "nao_instalado"
    ERRO = "erro"


@dataclass(frozen=True, slots=True)
class ResultadoTranscricao:
    caminho_srt: str
    idioma_detectado: str
    duracao_segundos: float = 0.0


class ITranscritor(ABC):
    """Contrato formal para motores de transcrição de áudio em legendas."""

    @abstractmethod
    def esta_disponivel(self) -> bool:
        """Verifica se o binário e modelo de transcrição estão acessíveis no disco."""
        pass

    @abstractmethod
    def transcrever(self, caminho_audio: str, idioma: str = "auto") -> ResultadoTranscricao:
        """Transcreve um arquivo de áudio e retorna os metadados do .srt gerado."""
        pass
>>>>>>>

### FILE: tradutor/transcritores/whisperfile.py
<<<<<<< SEARCH
=======
"""Implementação do motor de transcrição baseado no executável portátil Mozilla Whisperfile."""

import os
import shutil
import subprocess
import time

from ..config import GerenciadorConfig
from ..idiomas import Idiomas
from .base import ITranscritor, ResultadoTranscricao


class MotorWhisperfile(ITranscritor):
    """Adaptador para o executável standalone whisperfile (whisper.cpp / Cosmopolitan Libc)."""

    NOMES_PADRAO = ("whisper-base.exe", "whisperfile.exe", "whisper-small.exe", "whisper-tiny.exe")

    def __init__(self, caminho_executavel: str | None = None, timeout_segundos: int = 1800):
        self._caminho_executavel = caminho_executavel
        self._timeout_segundos = timeout_segundos

    def resolver_executavel(self) -> str | None:
        """Localiza o binário do whisperfile priorizando configuração do usuário e pastas do projeto."""
        candidatos = []
        if self._caminho_executavel:
            candidatos.append(self._caminho_executavel)

        try:
            from ..config_usuario import PreferenciasUsuario
            custom_cfg = PreferenciasUsuario.obter("caminho_whisperfile", "")
            if custom_cfg:
                candidatos.append(custom_cfg)
        except Exception:
            pass

        for pasta_base in (GerenciadorConfig.DIRETORIO_EXECUCAO, GerenciadorConfig.DIRETORIO_RECURSOS):
            for nome in self.NOMES_PADRAO:
                candidatos.append(os.path.join(pasta_base, "bin", nome))
                candidatos.append(os.path.join(pasta_base, "mkvtoolnix", nome))

        for c in candidatos:
            if c and os.path.isfile(c):
                return os.path.abspath(c)

        for nome in self.NOMES_PADRAO:
            no_path = shutil.which(nome)
            if no_path:
                return os.path.abspath(no_path)

        return None

    def esta_disponivel(self) -> bool:
        return self.resolver_executavel() is not None

    @staticmethod
    def _normalizar_idioma_whisper(idioma: str | None) -> str:
        """Converte códigos ISO-639-2 (ex: 'jpn', 'eng') para ISO-639-1 aceito pelo whisper.cpp."""
        cod = Idiomas.para_google(idioma)
        if cod == "zh-cn":
            return "zh"
        return cod

    def transcrever(self, caminho_audio: str, idioma: str = "auto") -> ResultadoTranscricao:
        exe = self.resolver_executavel()
        if not exe:
            raise FileNotFoundError("Binário do Mozilla Whisperfile não encontrado.")

        if not os.path.isfile(caminho_audio):
            raise FileNotFoundError(f"Arquivo de áudio não encontrado: {caminho_audio}")

        idioma_norm = self._normalizar_idioma_whisper(idioma)
        comando = [exe, "-f", caminho_audio, "-osrt"]
        if idioma_norm and idioma_norm != "auto":
            comando.extend(["-l", idioma_norm])

        inicio = time.time()
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            timeout=self._timeout_segundos,
        )
        duracao = round(time.time() - inicio, 2)

        if resultado.returncode != 0:
            detalhe = (resultado.stderr or resultado.stdout or "").strip()
            raise RuntimeError(f"Falha na transcrição via Whisperfile (código {resultado.returncode}): {detalhe}")

        caminho_srt = f"{caminho_audio}.srt"
        if not os.path.exists(caminho_srt):
            base_sem_ext = os.path.splitext(caminho_audio)[0]
            alternativo = f"{base_sem_ext}.srt"
            if os.path.exists(alternativo):
                caminho_srt = alternativo
            else:
                raise FileNotFoundError("O arquivo .srt não foi gerado pelo Whisperfile após a transcrição.")

        return ResultadoTranscricao(
            caminho_srt=caminho_srt,
            idioma_detectado=idioma_norm,
            duracao_segundos=duracao,
        )
>>>>>>>
```

---

### 3.2 Modificações em `tradutor/config_usuario.py`, `tradutor/manipulador_mkv.py` e `tradutor/estrategias/processador_mkv.py`

```markdown
### FILE: tradutor/config_usuario.py
<<<<<<< SEARCH
        "politica_sobrescrita": "perguntar",  # "perguntar", "sobrescrever", "pular"
        "mkvtoolnix_custom": ""
    }
=======
        "politica_sobrescrita": "perguntar",  # "perguntar", "sobrescrever", "pular"
        "mkvtoolnix_custom": "",
        "auto_alimentar_anilist": True,
        "transcricao_habilitada": False,
        "caminho_whisperfile": "",
        "forcar_transcricao": False
    }
>>>>>>>

### FILE: tradutor/manipulador_mkv.py
<<<<<<< SEARCH
        comando_mux = [
            mkvmerge,
            "-o", caminho_saida,
            caminho_mkv_original,
            "--language", f"0:{codigo_mkv}",
            "--track-name", f"0:{nome_trilha}",
            caminho_legenda_traduzida
        ]
=======
        comando_mux = [
            mkvmerge,
            "-o", caminho_saida,
            caminho_mkv_original,
            "--default-track-flag", "0:yes",
            "--language", f"0:{codigo_mkv}",
            "--track-name", f"0:{nome_trilha}",
            caminho_legenda_traduzida
        ]
>>>>>>>
```

---

## 4. Critérios de Validação e Testes Unitários (`tests/unit/test_transcritor_whisper.py`)

1. **Testes Unitários 100% Offline:**
   - Todos os testes em `tests/unit/test_transcritor_whisper.py` utilizam `mocker.patch("subprocess.run")` e `tmp_path`, garantindo execução em milissegundos sem exigir binários reais no CI.
2. **Casos Obrigatórios Cobertos:**
   - Resolução de executável em `GerenciadorConfig.DIRETORIO_EXECUCAO/bin/whisper-base.exe`.
   - Conversão de código ISO-639-2 (`jpn` -> `ja`, `eng` -> `en`, `chi` -> `zh`) na montagem dos argumentos CLI (`-l`).
   - Preservação obrigatória de `creationflags=subprocess.CREATE_NO_WINDOW` no Windows.
   - Tratamento de fallback entre `<audio>.wav.srt` e `<audio>.srt`.
   - Levantamento de `FileNotFoundError` quando o binário não está instalado e `RuntimeError` quando `returncode != 0`.
