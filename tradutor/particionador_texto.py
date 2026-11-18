"""Módulo de particionamento de textos extensos baseado em orçamento de caracteres.

Divide textos corridos em blocos atômicos respeitando limites de caracteres e
mantendo a hierarquia estrutural de parágrafos, quebras de linha e sentenças.
"""

from __future__ import annotations

from typing import Sequence


class ParticionadorTexto:
    """Particiona textos contínuos respeitando um orçamento máximo de caracteres.

    Utiliza divisão hierárquica por delimitadores (parágrafos, quebras de linha,
    pontuação e espaços) e recomposição exata sem perda de caracteres estruturais.
    """

    _DELIMITADORES: tuple[str, ...] = (
        "\r\n\r\n",
        "\n\n",
        "\r\n",
        "\n",
        ". ",
        "! ",
        "? ",
        "; ",
        " ",
        "",
    )

    def __init__(self, limite_caracteres: int = 3500) -> None:
        self._limite_caracteres = max(1, limite_caracteres)

    @property
    def limite_caracteres(self) -> int:
        """Limite máximo de caracteres por bloco."""
        return self._limite_caracteres

    @property
    def delimitadores(self) -> tuple[str, ...]:
        """Hierarquia pública de delimitadores para particionamento e fallback."""
        return self._DELIMITADORES

    def particionar(self, texto: str) -> list[str]:
        """Divide o texto em blocos de tamanho menor ou igual ao limite."""
        if not texto:
            return []
        if len(texto) <= self._limite_caracteres:
            return [texto]

        unidades = self._dividir_em_unidades(texto, 0)
        return self._agrupar_em_blocos(unidades)

    def _dividir_em_unidades(self, trecho: str, nivel: int) -> list[tuple[str, str]]:
        """Divide recursivamente o trecho usando delimitadores ordenados."""
        if not trecho:
            return []
        if len(trecho) <= self._limite_caracteres or nivel >= len(self._DELIMITADORES):
            if len(trecho) > self._limite_caracteres:
                return [
                    (trecho[i : i + self._limite_caracteres], "")
                    for i in range(0, len(trecho), self._limite_caracteres)
                ]
            return [(trecho, "")]

        sep = self._DELIMITADORES[nivel]
        if sep == "":
            return [
                (trecho[i : i + self._limite_caracteres], "")
                for i in range(0, len(trecho), self._limite_caracteres)
            ]

        partes = trecho.split(sep)
        if len(partes) == 1:
            return self._dividir_em_unidades(trecho, nivel + 1)

        unidades: list[tuple[str, str]] = []
        pontuacao_embutida = len(sep) == 2 and sep[0] in ".!?;" and sep[1] == " "

        for i, parte in enumerate(partes):
            tem_proximo = i < len(partes) - 1
            if tem_proximo and pontuacao_embutida and parte:
                parte_efetiva = parte + sep[0]
                delimitador = sep[1:]
            else:
                parte_efetiva = parte
                delimitador = sep if tem_proximo else ""

            if len(parte_efetiva) <= self._limite_caracteres:
                if parte_efetiva:
                    unidades.append((parte_efetiva, delimitador))
                elif delimitador:
                    if unidades:
                        u_ant, d_ant = unidades[-1]
                        unidades[-1] = (u_ant, d_ant + delimitador)
                    else:
                        unidades.append(("", delimitador))
            else:
                sub = self._dividir_em_unidades(parte_efetiva, nivel + 1)
                if sub and delimitador:
                    u_ult, d_ult = sub[-1]
                    sub[-1] = (u_ult, d_ult + delimitador)
                unidades.extend(sub)
        return unidades

    def _agrupar_em_blocos(self, unidades: list[tuple[str, str]]) -> list[str]:
        """Agrupa unidades atômicas no maior bloco possível até o limite."""
        blocos: list[str] = []
        cur_texto = ""
        d_anterior = ""

        for u, d in unidades:
            candidato = cur_texto + u if not cur_texto else cur_texto + d_anterior + u
            if len(candidato) <= self._limite_caracteres:
                cur_texto = candidato
                d_anterior = d
            else:
                if cur_texto:
                    blocos.append(cur_texto)
                cur_texto = u
                d_anterior = d

        if cur_texto:
            blocos.append(cur_texto)
        return blocos

    def recompor_texto(
        self,
        texto_original: str,
        blocos_originais: Sequence[str],
        blocos_traduzidos: Sequence[str],
    ) -> str:
        """Recompõe o texto traduzido preservando os separadores originais."""
        pos = 0
        partes_resultado: list[str] = []

        for b_orig, b_trad in zip(blocos_originais, blocos_traduzidos):
            idx = texto_original.find(b_orig, pos)
            if idx != -1:
                separador = texto_original[pos:idx]
                partes_resultado.append(separador)
                partes_resultado.append(b_trad)
                pos = idx + len(b_orig)
            else:
                partes_resultado.append(b_trad)

        partes_resultado.append(texto_original[pos:])
        return "".join(partes_resultado)
