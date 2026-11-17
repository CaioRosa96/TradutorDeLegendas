"""Testes unitários do GerenciadorFila (camada de apresentação desacoplada de GUI)."""

from tradutor.ui.gerenciador_fila import GerenciadorFila


def test_gerenciador_fila_inicializacao():
    """Valida estado inicial limpo e contratos básicos."""
    fila = GerenciadorFila()
    assert len(fila) == 0
    assert not bool(fila)
    assert fila.arquivos == []
    assert fila.arquivos_sem_legenda == set()
    assert fila.modelos_ia_por_arquivo == {}
    assert fila.em_execucao is False


def test_adicionar_arquivos_filtragem_e_deduplicacao():
    """Filtra extensões suportadas, rejeita formatos inválidos e descarta duplicados."""
    fila = GerenciadorFila()
    candidatos = [
        "video1.mkv",
        "video2.mp4",
        "doc.pdf",
        "app.exe",
        "legenda.srt",
        "video1.mkv",  # duplicado
        "legenda.ass",
        "texto.txt",
        "",  # vazio
    ]

    adicionados = fila.adicionar_arquivos(candidatos)
    assert adicionados == ["video1.mkv", "video2.mp4", "legenda.srt", "legenda.ass", "texto.txt"]
    assert len(fila) == 5
    assert bool(fila) is True

    # Adicionar novamente deve retornar lista vazia
    assert fila.adicionar_arquivos(["video1.mkv", "legenda.srt"]) == []
    assert len(fila) == 5


def test_remover_arquivo_limpa_metadados():
    """Remover arquivo expurga também metadados de legenda e IA associados."""
    fila = GerenciadorFila()
    fila.adicionar_arquivos(["video1.mkv", "video2.mp4"])
    fila.definir_arquivos_sem_legenda(["video1.mkv"])
    fila.definir_modelo_whisper("video1.mkv", "medium")

    assert fila.eh_sem_legenda("video1.mkv") is True
    assert fila.obter_modelo_whisper("video1.mkv") == "medium"

    removido = fila.remover_arquivo("video1.mkv")
    assert removido is True
    assert "video1.mkv" not in fila.arquivos
    assert fila.eh_sem_legenda("video1.mkv") is False
    assert fila.obter_modelo_whisper("video1.mkv") is None

    # Remover item que não existe retorna False
    assert fila.remover_arquivo("inexistente.mkv") is False


def test_limpar_fila():
    """Limpar esvazia lista de arquivos e todos os mapeamentos de metadados."""
    fila = GerenciadorFila()
    fila.adicionar_arquivos(["a.mkv", "b.srt"])
    fila.definir_arquivos_sem_legenda(["a.mkv"])
    fila.definir_modelo_whisper("a.mkv", "large-v3")

    fila.limpar()
    assert len(fila) == 0
    assert fila.arquivos_sem_legenda == set()
    assert fila.modelos_ia_por_arquivo == {}


def test_resolver_caminho_por_nome(tmp_path):
    """Localiza o caminho completo do arquivo a partir de seu basename ou arquivo real."""
    fila = GerenciadorFila()
    arq1 = str(tmp_path / "Episodio_01.mkv")
    arq2 = str(tmp_path / "Episodio_02.mp4")
    (tmp_path / "Episodio_01.mkv").write_text("fake", encoding="utf-8")

    fila.adicionar_arquivos([arq1, arq2])

    assert fila.resolver_caminho_por_nome(arq1) == arq1
    assert fila.resolver_caminho_por_nome("Episodio_01.mkv") == arq1
    assert fila.resolver_caminho_por_nome("Episodio_02.mp4") == arq2
    assert fila.resolver_caminho_por_nome("Episodio_99.mkv") is None


def test_controle_em_execucao():
    """Valida controle do estado em execução."""
    fila = GerenciadorFila()
    assert fila.em_execucao is False
    fila.em_execucao = True
    assert fila.em_execucao is True
    fila.em_execucao = False
    assert fila.em_execucao is False
