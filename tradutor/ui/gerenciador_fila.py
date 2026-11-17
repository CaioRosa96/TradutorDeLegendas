"""Gerenciamento desacoplado de estado da fila de arquivos e configurações de IA por arquivo."""

import os
from typing import Sequence


class GerenciadorFila:
    """Controla a lista de arquivos da fila, extensões suportadas e metadados de transcrição por arquivo."""

    EXTENSOES_SUPORTADAS = (
        ".mkv",
        ".mp4",
        ".webm",
        ".avi",
        ".wmv",
        ".srt",
        ".ass",
        ".txt",
    )

    def __init__(self):
        self._arquivos: list[str] = []
        self._arquivos_sem_legenda: set[str] = set()
        self._modelos_ia_por_arquivo: dict[str, str] = {}
        self._em_execucao: bool = False

    @property
    def arquivos(self) -> list[str]:
        """Retorna uma cópia da lista atual de caminhos na fila."""
        return list(self._arquivos)

    @property
    def arquivos_sem_legenda(self) -> set[str]:
        """Retorna uma cópia do conjunto de arquivos detectados sem legenda embutida."""
        return set(self._arquivos_sem_legenda)

    @property
    def modelos_ia_por_arquivo(self) -> dict[str, str]:
        """Retorna uma cópia do mapeamento de caminho para o modelo Whisper configurado."""
        return dict(self._modelos_ia_por_arquivo)

    @property
    def em_execucao(self) -> bool:
        """Indica se há processamento ativo na fila."""
        return self._em_execucao

    @em_execucao.setter
    def em_execucao(self, valor: bool):
        self._em_execucao = bool(valor)

    def eh_extensao_valida(self, caminho: str) -> bool:
        """Verifica se o arquivo possui extensão suportada pelo pipeline."""
        if not caminho:
            return False
        return caminho.lower().endswith(self.EXTENSOES_SUPORTADAS)

    def adicionar_arquivos(self, caminhos: Sequence[str]) -> list[str]:
        """Filtra extensões suportadas, deduplica e adiciona novos arquivos à fila.

        Retorna a lista dos arquivos efetivamente adicionados nesta chamada.
        """
        adicionados = []
        for c in caminhos:
            if not c or not self.eh_extensao_valida(c):
                continue
            if c not in self._arquivos:
                self._arquivos.append(c)
                adicionados.append(c)
        return adicionados

    def remover_arquivo(self, caminho: str) -> bool:
        """Remove o arquivo da fila e limpa seus metadados associados."""
        if caminho in self._arquivos:
            self._arquivos.remove(caminho)
            self._arquivos_sem_legenda.discard(caminho)
            self._modelos_ia_por_arquivo.pop(caminho, None)
            return True
        return False

    def limpar(self):
        """Limpa todos os arquivos da fila e metadados."""
        self._arquivos.clear()
        self._arquivos_sem_legenda.clear()
        self._modelos_ia_por_arquivo.clear()

    def definir_modelo_whisper(self, caminho: str, modelo: str):
        """Associa um modelo Whisper específico a um arquivo da fila."""
        self._modelos_ia_por_arquivo[caminho] = modelo

    def obter_modelo_whisper(self, caminho: str) -> str | None:
        """Retorna o modelo Whisper associado ao arquivo, se houver."""
        return self._modelos_ia_por_arquivo.get(caminho)

    def definir_arquivos_sem_legenda(self, caminhos: Sequence[str]):
        """Atualiza o conjunto de arquivos sem legenda embutida."""
        self._arquivos_sem_legenda = set(caminhos)

    def eh_sem_legenda(self, caminho: str) -> bool:
        """Indica se o arquivo está marcado como sem legenda embutida."""
        return caminho in self._arquivos_sem_legenda

    def resolver_caminho_por_nome(self, nome_arquivo: str) -> str | None:
        """Localiza o caminho completo do arquivo na fila a partir do nome base."""
        if os.path.isfile(nome_arquivo):
            return nome_arquivo
        alvo = os.path.basename(nome_arquivo)
        for f in self._arquivos:
            if os.path.basename(f) == alvo:
                return f
        return None

    def __len__(self) -> int:
        return len(self._arquivos)

    def __bool__(self) -> bool:
        return len(self._arquivos) > 0
