"""Servico de verificacao de novas versoes via API publica do GitHub Releases."""

from dataclasses import dataclass
import re
import requests


@dataclass(frozen=True, slots=True)
class ResultadoAtualizacao:
    """Value Object imutavel com o diagnostico de verificacao de versao."""

    sucesso: bool
    atualizacao_disponivel: bool
    versao_atual: str
    versao_remota: str
    url_download: str
    erro: str = ""


class VerificadorAtualizacao:
    """Consulta a ultima release publicada no GitHub e compara semanticamente a versao."""

    VERSAO_ATUAL = "2.9.0"
    URL_REPOSITORIO = "https://github.com/CaioRosa96/TradutorDeLegendas"
    URL_PERFIL_AUTOR = "https://github.com/CaioRosa96"
    URL_API_ULTIMA_RELEASE = (
        "https://api.github.com/repos/CaioRosa96/TradutorDeLegendas/releases/latest"
    )
    TIMEOUT_SEGUNDOS = 8

    @staticmethod
    def normalizar_versao(tag: str) -> tuple[int, ...]:
        """Extrai a tupla numerica (major, minor, patch) de uma tag como 'v2.8.0'."""
        limpa = (tag or "").strip().lstrip("vV")
        limpa = limpa.split("-")[0]
        partes = [int(p) for p in re.findall(r"\d+", limpa)]
        if not partes:
            return (0, 0, 0)
        while len(partes) < 3:
            partes.append(0)
        return tuple(partes[:3])

    @classmethod
    def verificar(cls, versao_atual: str = VERSAO_ATUAL) -> ResultadoAtualizacao:
        """Consulta o endpoint releases/latest do GitHub com timeout controlado."""
        versao_base = (versao_atual or cls.VERSAO_ATUAL).strip().lstrip("vV")
        cabecalhos = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"TradutorDeLegendas/{versao_base}",
        }
        try:
            resposta = requests.get(
                cls.URL_API_ULTIMA_RELEASE,
                headers=cabecalhos,
                timeout=cls.TIMEOUT_SEGUNDOS,
            )
            if resposta.status_code != 200:
                return ResultadoAtualizacao(
                    sucesso=False,
                    atualizacao_disponivel=False,
                    versao_atual=f"v{versao_base}",
                    versao_remota="",
                    url_download=f"{cls.URL_REPOSITORIO}/releases",
                    erro=f"HTTP {resposta.status_code}",
                )

            dados = resposta.json()
            tag_remota = str(dados.get("tag_name") or "").strip()
            url_html = str(dados.get("html_url") or f"{cls.URL_REPOSITORIO}/releases").strip()

            if not tag_remota:
                return ResultadoAtualizacao(
                    sucesso=False,
                    atualizacao_disponivel=False,
                    versao_atual=f"v{versao_base}",
                    versao_remota="",
                    url_download=url_html,
                    erro="Tag ausente na resposta",
                )

            tupla_remota = cls.normalizar_versao(tag_remota)
            tupla_local = cls.normalizar_versao(versao_base)
            tag_formatada = tag_remota if tag_remota.lower().startswith("v") else f"v{tag_remota}"

            return ResultadoAtualizacao(
                sucesso=True,
                atualizacao_disponivel=tupla_remota > tupla_local,
                versao_atual=f"v{versao_base}",
                versao_remota=tag_formatada,
                url_download=url_html,
            )
        except Exception as exc:
            return ResultadoAtualizacao(
                sucesso=False,
                atualizacao_disponivel=False,
                versao_atual=f"v{versao_base}",
                versao_remota="",
                url_download=f"{cls.URL_REPOSITORIO}/releases",
                erro=str(exc),
            )

