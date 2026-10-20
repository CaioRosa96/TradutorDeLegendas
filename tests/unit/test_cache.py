import os
import sys
import pytest
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tradutor.cache import CacheTraducoes

@pytest.fixture
def cache_temporario(tmp_path):
    """
    Cria uma instância do Cache apontando para um banco de dados real 
    temporário criado pelo pytest (que será deletado ao fim do teste).
    Isso é necessário pois a classe abre e fecha conexões a cada operação,
    o que apagaria os dados se usássemos ":memory:".
    """
    # Como tmp_path é um caminho absoluto, o os.path.join dentro do cache
    # irá ignorar o diretório base do projeto e usar o caminho absoluto temporário.
    db_fake = str(tmp_path / "teste_cache.db")
    return CacheTraducoes(db_path=db_fake)


def test_criacao_implicita_tabela(cache_temporario):
    """Verifica se a tabela 'traducoes' é criada automaticamente no construtor."""
    # Acessa o banco diretamente para ver se a tabela existe
    with sqlite3.connect(cache_temporario.db_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traducoes';")
        tabela = cursor.fetchone()
        
    assert tabela is not None
    assert tabela[0] == "traducoes"


def test_put_e_get_basico(cache_temporario):
    """Testa se o cache salva (put) e recupera (get) uma tradução (Hit)."""
    texto = "Hello World"
    traducao = "Olá Mundo"
    
    # Busca antes de inserir (Miss)
    assert cache_temporario.get(texto, "en", "pt") is None
    
    # Insere
    cache_temporario.put(texto, "en", "pt", traducao)
    
    # Busca depois de inserir (Hit)
    resultado = cache_temporario.get(texto, "en", "pt")
    assert resultado == traducao


def test_isolamento_por_idiomas(cache_temporario):
    """
    Garante que traduções do mesmo texto mas para idiomas 
    diferentes não se sobrescrevem (verificação do Hash).
    """
    texto = "Good Morning"
    
    cache_temporario.put(texto, "en", "pt", "Bom dia")
    cache_temporario.put(texto, "en", "es", "Buenos días")
    
    assert cache_temporario.get(texto, "en", "pt") == "Bom dia"
    assert cache_temporario.get(texto, "en", "es") == "Buenos días"
    # Miss para um destino não cacheado
    assert cache_temporario.get(texto, "en", "ja") is None


def test_sobrescrita_update(cache_temporario):
    """
    Se fizermos um PUT novamente com o mesmo texto e idiomas, 
    a tradução deve ser atualizada e não deve gerar erro de Unique Constraint.
    """
    texto = "Apple"
    
    cache_temporario.put(texto, "en", "pt", "Maca")
    assert cache_temporario.get(texto, "en", "pt") == "Maca"
    
    # Atualiza (corrigindo acento)
    cache_temporario.put(texto, "en", "pt", "Maçã")
    assert cache_temporario.get(texto, "en", "pt") == "Maçã"


def test_concorrencia_multithread_sem_lock(cache_temporario):
    """
    Simula rajadas de escritas e leituras concorrentes em múltiplas threads
    para garantir que não ocorra 'sqlite3.OperationalError: database is locked'.
    """
    from concurrent.futures import ThreadPoolExecutor

    def operacao(i):
        texto = f"Frase {i}"
        traducao = f"Tradução {i}"
        cache_temporario.put(texto, "en", "pt", traducao)
        val = cache_temporario.get(texto, "en", "pt")
        assert val == traducao

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(operacao, range(40)))


def test_metricas_e_limpeza_cache(cache_temporario):
    """Verifica contagem de registros, calculo de tamanho e limpeza completa do cache."""
    assert cache_temporario.contar_traducoes() == 0
    cache_temporario.put("Text 1", "en", "pt", "Texto 1")
    cache_temporario.put("Text 2", "en", "pt", "Texto 2")
    assert cache_temporario.contar_traducoes() == 2
    assert cache_temporario.obter_tamanho_bytes() > 0

    cache_temporario.limpar_tudo()
    assert cache_temporario.contar_traducoes() == 0


def test_put_many_e_get_many_chunked(cache_temporario):
    """Testa inserção e recuperação em lote ultrapassando o limite de 500 parâmetros."""
    # Gera 550 itens para garantir teste do fatiamento em chunks
    total = 550
    itens = [(f"Text {i}", "en", "pt", f"Texto {i}") for i in range(total)]
    cache_temporario.put_many(itens)

    assert cache_temporario.contar_traducoes() == total

    # Recupera todos os 550 via get_many (deve fatiar em 500 + 50)
    textos_busca = [f"Text {i}" for i in range(total)]
    recuperados = cache_temporario.get_many(textos_busca, "en", "pt")
    assert len(recuperados) == total
    assert recuperados["Text 0"] == "Texto 0"
    assert recuperados[f"Text {total - 1}"] == f"Texto {total - 1}"


def test_salvar_lote_com_mapping_e_lista(cache_temporario):
    """Testa salvar_lote usando dicionário e usando lista de tuplas."""
    mapa = {"Hello": "Olá", "World": "Mundo"}
    cache_temporario.salvar_lote(mapa, src_lang="en", dest_lang="pt")

    assert cache_temporario.get("Hello", "en", "pt") == "Olá"
    assert cache_temporario.get("World", "en", "pt") == "Mundo"

    lista_tuplas = [("Bye", "en", "pt", "Adeus")]
    cache_temporario.salvar_lote(lista_tuplas)
    assert cache_temporario.get("Bye", "en", "pt") == "Adeus"


def test_concorrencia_alta_20_threads_lote_sem_lock(cache_temporario):
    """Simula 20 threads simultâneas lendo e escrevendo em lote no SQLite com modo WAL.
    
    Garante zero ocorrências de 'sqlite3.OperationalError: database is locked'.
    """
    from concurrent.futures import ThreadPoolExecutor

    def trabalhador(thread_id: int):
        lote = [(f"Thread_{thread_id}_Item_{i}", "en", "pt", f"Trad_{thread_id}_{i}") for i in range(50)]
        cache_temporario.put_many(lote)
        textos = [f"Thread_{thread_id}_Item_{i}" for i in range(50)]
        recuperados = cache_temporario.get_many(textos, "en", "pt")
        assert len(recuperados) == 50
        assert recuperados[f"Thread_{thread_id}_Item_0"] == f"Trad_{thread_id}_0"
        assert recuperados[f"Thread_{thread_id}_Item_49"] == f"Trad_{thread_id}_49"

    with ThreadPoolExecutor(max_workers=20) as executor:
        futuros = [executor.submit(trabalhador, t) for t in range(20)]
        for f in futuros:
            f.result()

    assert cache_temporario.contar_traducoes() == 20 * 50


def test_cache_satisfaz_contrato_cache_traducao_port(cache_temporario):
    """Verifica se CacheTraducoes e RepositorioCacheSqlite satisfazem CacheTraducaoPort."""
    from tradutor.contratos import CacheTraducaoPort
    from tradutor.cache import RepositorioCacheSqlite

    assert isinstance(cache_temporario, CacheTraducaoPort)
    assert RepositorioCacheSqlite is CacheTraducoes


