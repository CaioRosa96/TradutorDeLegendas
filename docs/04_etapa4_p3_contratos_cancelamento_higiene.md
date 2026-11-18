# Etapa 4 (P3): Contratos, Cancelamento e Higiene de Arquitetura

**Instrucao para o Antigravity:** Aplique exatamente os blocos `SEARCH` / `REPLACE` abaixo apos confirmar que as Etapas 1, 2 e 3 passaram em todos os testes.

---

## 1. `tradutor/contratos.py`
**Objetivo:** Desacoplar `contratos.py` de `manipulador_midia.py` no carregamento inicial do modulo usando `__getattr__` (lazy re-export), mantendo 100% de compatibilidade com imports existentes (`from tradutor.contratos import ManipuladorMidiaPort, TrilhaMidia`).

### Alteracao 1.1: Lazy import de `ManipuladorMidiaPort` e `TrilhaMidia`

#### SEARCH
```python
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Protocol, Sequence, runtime_checkable

from .manipulador_midia import ManipuladorMidiaPort, TrilhaMidia
```

#### REPLACE
```python
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Mapping, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    from .manipulador_midia import ManipuladorMidiaPort, TrilhaMidia


def __getattr__(name: str) -> Any:
    if name in ("ManipuladorMidiaPort", "TrilhaMidia"):
        from . import manipulador_midia

        return getattr(manipulador_midia, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

---

## 2. `tradutor/particionador_texto.py`
**Objetivo:** Expor a propriedade publica `delimitadores` para que `TradutorTextosExtensos` nao dependa do atributo privado `_DELIMITADORES`.

### Alteracao 2.1: Propriedade `delimitadores`

#### SEARCH
```python
    @property
    def limite_caracteres(self) -> int:
        """Limite máximo de caracteres por bloco."""
        return self._limite_caracteres
```

#### REPLACE
```python
    @property
    def limite_caracteres(self) -> int:
        """Limite máximo de caracteres por bloco."""
        return self._limite_caracteres

    @property
    def delimitadores(self) -> tuple[str, ...]:
        """Hierarquia pública de delimitadores para particionamento e fallback."""
        return self._DELIMITADORES
```

---

## 3. `tradutor/estrategias/processador_base.py`
**Objetivo:** Substituir a inspecao de atributo privado de subclasse `getattr(self, "_transcrito_por_ia", False)` por um metodo gancho explicito `deve_copiar_sem_traduzir()`.

### Alteracao 3.1: Metodo gancho `deve_copiar_sem_traduzir`

#### SEARCH
```python
        try:
            # 5. Tradução (ou cópia direta quando já transcrito no idioma de destino)
            if mesmo_idioma and getattr(self, "_transcrito_por_ia", False):
                shutil.copyfile(arq_trabalho, caminho_legenda_final)
                legenda_gerada_nesta_execucao = True
```

#### REPLACE
```python
        try:
            # 5. Tradução (ou cópia direta quando já transcrito no idioma de destino)
            if mesmo_idioma and self.deve_copiar_sem_traduzir():
                shutil.copyfile(arq_trabalho, caminho_legenda_final)
                legenda_gerada_nesta_execucao = True
```

### Alteracao 3.2: Definicao do metodo gancho na classe base

#### SEARCH
```python
    @abstractmethod
    def should_skip_if_same_language(self) -> bool:
        """Define se deve abortar caso origem == destino."""
        pass
```

#### REPLACE
```python
    def deve_copiar_sem_traduzir(self) -> bool:
        """Indica se o arquivo preparado já está pronto no idioma de destino (ex: transcrição IA)."""
        return bool(getattr(self, "_transcrito_por_ia", False))

    @abstractmethod
    def should_skip_if_same_language(self) -> bool:
        """Define se deve abortar caso origem == destino."""
        pass
```

---

## 4. Limpeza de Artefatos `.pyc` Orfaos Locais
Execute no terminal PowerShell na raiz do repositorio para remover bytecodes antigos em ingles sem `.py` correspondente:

```powershell
Get-ChildItem -Path .\tradutor -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
.\venv\Scripts\pytest tests\unit -v
```