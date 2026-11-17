"""Testes unitários para TradutorTextosExtensos e ParticionadorTexto."""

import pytest
from unittest.mock import MagicMock, call

from tradutor.contratos import CacheTraducaoPort
from tradutor.particionador_texto import ParticionadorTexto
from tradutor.servico_textos_extensos import TradutorTextosExtensos
from tradutor.tradutores.base import ExcecaoDisjuntorAberto, ITradutor


class MotorTraducaoFake(ITradutor):
    """Implementação simples em memória para testes."""

    def __init__(self, prefixo: str = "[PT] ") -> None:
        self.prefixo = prefixo
        self.chamadas: list[tuple[str, str, str]] = []

    def translate(self, text: str, src_lang: str, dest_lang: str) -> str:
        self.chamadas.append((text, src_lang, dest_lang))
        return f"{self.prefixo}{text}"


class CacheFake:
    """Implementação em memória de CacheTraducaoPort para testes."""

    def __init__(self) -> None:
        self._dados: dict[tuple[str, str, str], str] = {}
        self.leituras = 0
        self.escritas = 0

    def get(self, texto: str, src_lang: str, dest_lang: str) -> str | None:
        self.leituras += 1
        return self._dados.get((texto, src_lang, dest_lang))

    def put(self, texto: str, src_lang: str, dest_lang: str, texto_traduzido: str) -> None:
        self.escritas += 1
        self._dados[(texto, src_lang, dest_lang)] = texto_traduzido

    def get_many(self, textos: list[str], src_lang: str, dest_lang: str) -> dict[str, str]:
        resultado = {}
        for t in textos:
            val = self.get(t, src_lang, dest_lang)
            if val is not None:
                resultado[t] = val
        return resultado

    def put_many(self, itens: dict[str, str], src_lang: str = "auto", dest_lang: str = "pt") -> None:
        for k, v in itens.items():
            self.put(k, src_lang, dest_lang, v)


# --- Testes do ParticionadorTexto ---


def test_particionador_texto_curto_e_vazio():
    particionador = ParticionadorTexto(limite_caracteres=100)
    assert particionador.particionar("") == []
    assert particionador.particionar("Texto pequeno") == ["Texto pequeno"]


def test_particionador_por_paragrafos_e_orcamento():
    particionador = ParticionadorTexto(limite_caracteres=100)
    p1 = "A" * 40
    p2 = "B" * 40
    p3 = "C" * 40
    texto = f"{p1}\n\n{p2}\n\n{p3}"

    blocos = particionador.particionar(texto)
    # Bloco 1 deve agrupar p1 e p2 (40 + 2 + 40 = 82 <= 100)
    # Bloco 2 deve conter p3 (40 <= 100)
    assert len(blocos) == 2
    assert blocos[0] == f"{p1}\n\n{p2}"
    assert blocos[1] == p3
    assert all(len(b) <= 100 for b in blocos)


def test_particionador_paragrafo_gigante_por_sentencas():
    particionador = ParticionadorTexto(limite_caracteres=60)
    frase1 = "Primeira frase curta."
    frase2 = "Segunda frase com mais detalhes aqui para teste."
    frase3 = "Terceira frase final do bloco."
    texto = f"{frase1} {frase2} {frase3}"

    blocos = particionador.particionar(texto)
    assert len(blocos) > 1
    assert all(len(b) <= 60 for b in blocos)
    for b in blocos:
        assert b.strip() != ""


def test_particionador_sem_espacos_divisao_forcada():
    particionador = ParticionadorTexto(limite_caracteres=50)
    texto = "X" * 125
    blocos = particionador.particionar(texto)
    assert len(blocos) == 3
    assert len(blocos[0]) == 50
    assert len(blocos[1]) == 50
    assert len(blocos[2]) == 25
    assert "".join(blocos) == texto


def test_particionador_texto_longo_acima_3500_caracteres():
    particionador = ParticionadorTexto()  # limite padrão: 3500
    # Cria texto de 10.000 caracteres com múltiplos parágrafos
    paragrafos = [f"Parágrafo {i}: " + ("Sinopse detalhada do anime. " * 50) for i in range(8)]
    texto = "\n\n".join(paragrafos)
    assert len(texto) > 3500

    blocos = particionador.particionar(texto)
    assert len(blocos) >= 3
    assert all(len(b) <= 3500 for b in blocos)
    for b in blocos:
        assert b.strip() != ""

    # Recomposição deve preservar o texto original na íntegra
    recomposto = particionador.recompor_texto(texto, blocos, blocos)
    assert recomposto == texto


def test_recompor_texto_preserva_separadores_exatos():
    particionador = ParticionadorTexto(limite_caracteres=50)
    texto = "  \n\nParagrafo 1.\nLinha 1B.\n\nParagrafo 2.\n\n  "
    b0 = "Paragrafo 1.\nLinha 1B."
    b1 = "Paragrafo 2."
    blocos_orig = [b0, b1]
    blocos_trad = ["[TRAD 1]", "[TRAD 2]"]

    resultado = particionador.recompor_texto(texto, blocos_orig, blocos_trad)
    assert resultado == "  \n\n[TRAD 1]\n\n[TRAD 2]\n\n  "


# --- Testes do TradutorTextosExtensos ---


def test_inicializacao_sem_motor_lanca_erro():
    with pytest.raises(ValueError, match="Um motor de tradução"):
        TradutorTextosExtensos(tradutor=None, engine=None)


def test_inicializacao_com_propriedades():
    motor = MotorTraducaoFake()
    cache = CacheFake()
    tradutor = TradutorTextosExtensos(
        tradutor=motor,
        cache=cache,
        limite_caracteres=2000,
        max_concorrente=2,
    )
    assert tradutor.tradutor is motor
    assert tradutor.engine is motor
    assert tradutor.cache is cache
    assert tradutor.limite_caracteres == 2000


@pytest.mark.asyncio
async def test_traduzir_texto_vazio_ou_em_branco():
    motor = MotorTraducaoFake()
    tradutor = TradutorTextosExtensos(tradutor=motor)
    assert await tradutor.traduzir("") == ""
    assert await tradutor.traduzir("   \n\n   ") == "   \n\n   "
    assert len(motor.chamadas) == 0


@pytest.mark.asyncio
async def test_traduzir_happy_path_assincrono():
    motor = MotorTraducaoFake(prefixo="[BR] ")
    tradutor = TradutorTextosExtensos(tradutor=motor)
    texto = "Sinopse do anime de teste."

    resultado = await tradutor.traduzir(texto, idioma_origem="en", idioma_destino="pt")
    assert resultado == "[BR] Sinopse do anime de teste."
    assert len(motor.chamadas) == 1
    assert motor.chamadas[0] == (texto, "en", "pt")


def test_traduzir_sincrono():
    motor = MotorTraducaoFake(prefixo="[SYNC] ")
    tradutor = TradutorTextosExtensos(tradutor=motor)
    texto = "Texto para tradução síncrona."

    resultado = tradutor.traduzir_sincrono(texto, "en", "pt")
    assert resultado == "[SYNC] Texto para tradução síncrona."


@pytest.mark.asyncio
async def test_traduzir_preserva_paragrafos_em_texto_longo():
    motor = MotorTraducaoFake(prefixo="[PT] ")
    tradutor = TradutorTextosExtensos(tradutor=motor, limite_caracteres=100)

    p1 = "Primeiro paragrafo de teste que possui tamanho razoavel."
    p2 = "Segundo paragrafo tambem com tamanho suficiente para ultrapassar."
    p3 = "Terceiro paragrafo de conclusao da sinopse."
    texto = f"{p1}\n\n{p2}\n\n{p3}"

    resultado = await tradutor.traduzir(texto, "en", "pt")
    assert f"[PT] {p1}" in resultado
    assert f"[PT] {p2}" in resultado
    assert f"[PT] {p3}" in resultado
    assert "\n\n" in resultado


@pytest.mark.asyncio
async def test_integracao_com_cache():
    motor = MotorTraducaoFake()
    cache = CacheFake()
    tradutor = TradutorTextosExtensos(tradutor=motor, cache=cache)

    texto = "Texto para verificar cache."
    res1 = await tradutor.traduzir(texto, "en", "pt")
    assert res1 == "[PT] Texto para verificar cache."
    assert cache.escritas == 1
    assert len(motor.chamadas) == 1

    # Segunda chamada deve atingir o cache sem invocar o motor
    res2 = await tradutor.traduzir(texto, "en", "pt")
    assert res2 == res1
    assert len(motor.chamadas) == 1


@pytest.mark.asyncio
async def test_cache_get_many_parcial():
    motor = MotorTraducaoFake()
    cache = CacheFake()
    tradutor = TradutorTextosExtensos(tradutor=motor, cache=cache, limite_caracteres=50)

    p1 = "Primeiro paragrafo curto."
    p2 = "Segundo paragrafo curto."
    texto = f"{p1}\n\n{p2}"

    # Pré-popula cache apenas para p1
    cache.put(p1, "en", "pt", "Cache do p1")

    resultado = await tradutor.traduzir(texto, "en", "pt")
    assert "Cache do p1" in resultado
    assert f"[PT] {p2}" in resultado
    # Apenas p2 deve ter sido traduzido pelo motor
    assert len(motor.chamadas) == 1
    assert motor.chamadas[0][0] == p2


@pytest.mark.asyncio
async def test_falha_de_cache_nao_aborta_traducao():
    mock_cache = MagicMock(spec=CacheTraducaoPort)
    mock_cache.get.side_effect = RuntimeError("Falha de IO no cache")
    mock_cache.put.side_effect = RuntimeError("Falha de escrita no cache")

    motor = MotorTraducaoFake()
    tradutor = TradutorTextosExtensos(tradutor=motor, cache=mock_cache)

    resultado = await tradutor.traduzir("Texto teste", "en", "pt")
    assert resultado == "[PT] Texto teste"


@pytest.mark.asyncio
async def test_fallback_resiliente_ao_falhar_bloco():
    mock_motor = MagicMock(spec=ITradutor)
    
    def side_effect_translate(txt, src, dest):
        if "\n" in txt:
            raise RuntimeError("Erro ao traduzir bloco grande com quebras")
        return f"[OK] {txt}"

    mock_motor.translate.side_effect = side_effect_translate

    tradutor = TradutorTextosExtensos(tradutor=mock_motor, limite_caracteres=200)
    texto = "Linha um do texto.\nLinha dois do texto."

    resultado = await tradutor.traduzir(texto, "en", "pt")
    assert "[OK] Linha um do texto." in resultado
    assert "[OK] Linha dois do texto." in resultado


@pytest.mark.asyncio
async def test_fallback_preserva_texto_original_em_falha_persistente():
    mock_motor = MagicMock(spec=ITradutor)
    mock_motor.translate.side_effect = RuntimeError("API Google Indisponível")

    tradutor = TradutorTextosExtensos(tradutor=mock_motor)
    texto = "Texto que ira falhar totalmente."

    resultado = await tradutor.traduzir(texto, "en", "pt")
    # Deve retornar o texto original sem quebrar o sistema
    assert resultado == texto


@pytest.mark.asyncio
async def test_excecao_disjuntor_aberto_e_propagada():
    mock_motor = MagicMock(spec=ITradutor)
    mock_motor.translate.side_effect = ExcecaoDisjuntorAberto("Disjuntor aberto para evitar banimento")

    tradutor = TradutorTextosExtensos(tradutor=mock_motor)
    with pytest.raises(ExcecaoDisjuntorAberto, match="Disjuntor aberto"):
        await tradutor.traduzir("Texto", "en", "pt")


@pytest.mark.asyncio
async def test_cancelamento_aborta_traducao():
    motor = MotorTraducaoFake()
    tradutor = TradutorTextosExtensos(
        tradutor=motor,
        is_cancelled_callback=lambda: True,
    )
    resultado = await tradutor.traduzir("Texto para cancelar", "en", "pt")
    assert resultado == "Texto para cancelar"
    assert len(motor.chamadas) == 0


@pytest.mark.asyncio
async def test_progresso_callback():
    motor = MotorTraducaoFake()
    mock_progresso = MagicMock()
    tradutor = TradutorTextosExtensos(
        tradutor=motor,
        limite_caracteres=50,
        progress_callback=mock_progresso,
    )
    p1 = "A" * 40
    p2 = "B" * 40
    texto = f"{p1}\n\n{p2}"

    await tradutor.traduzir(texto, "en", "pt")
    assert mock_progresso.call_count == 2
    mock_progresso.assert_has_calls([call(1, 2), call(2, 2)])


@pytest.mark.asyncio
async def test_traduzir_texto_longo_acima_3500_caracteres_integridade_e_cache():
    motor = MotorTraducaoFake(prefixo="[PT] ")
    cache = CacheFake()
    tradutor = TradutorTextosExtensos(tradutor=motor, cache=cache)  # limite padrão 3500

    paragrafos = [
        f"Parágrafo {i}: " + ("Resumo épico da série com eventos e reviravoltas. " * 45)
        for i in range(6)
    ]
    texto = "\n\n".join(paragrafos)
    assert len(texto) > 7000

    # Primeira tradução: particiona e alimenta o cache
    resultado = await tradutor.traduzir(texto, "en", "pt")
    assert len(motor.chamadas) >= 2
    assert all("[PT] Parágrafo" in resultado for _ in range(6))
    assert "\n\n" in resultado
    assert cache.escritas == len(motor.chamadas)

    # Segunda tradução: deve usar o cache na íntegra
    chamadas_antes = len(motor.chamadas)
    resultado_cache = await tradutor.traduzir(texto, "en", "pt")
    assert resultado_cache == resultado
    assert len(motor.chamadas) == chamadas_antes  # Nenhuma chamada extra ao motor

