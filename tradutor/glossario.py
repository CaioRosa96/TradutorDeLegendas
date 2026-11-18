import os
import re
from .config import GerenciadorConfig
from .contratos import LinhaProtegida
from .glossario_port import AdaptadorAniListGraphQL, BuscadorEntidadesPort

class GerenciadorGlossario:
    """Gerenciador do Dicionário Anti-Tradução (Glossário).
    
    Implementa a técnica de Tokenização Isolada:
    Substitui termos protegidos por tokens alienígenas antes de enviar ao Google,
    e restaura os termos originais após a tradução, impedindo alucinações da API.
    """
    
    def __init__(
        self,
        filepath=None,
        video_filename=None,
        habilitar_auto_alimentar=False,
        buscador_entidades: BuscadorEntidadesPort | None = None,
    ):
        self.filepath = filepath or GerenciadorConfig.ARQUIVO_GLOSSARIO_PADRAO
        self.video_filename = video_filename
        self.habilitar_auto_alimentar = habilitar_auto_alimentar
        self.buscador_entidades = buscador_entidades
        self.glossario_map = {}
        self.load()

    @staticmethod
    def _extrair_aliases_arquivo(path: str) -> list[str]:
        """Lê diretivas '# Alias: a, b' do glossário em minúsculas para casamento alternativo."""
        aliases: list[str] = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    limpa = line.strip()
                    if limpa.lower().startswith('# alias:'):
                        bruto = limpa.split(':', 1)[1]
                        aliases.extend(a.strip().lower() for a in bruto.split(',') if a.strip())
        except Exception:
            pass
        return aliases

    def _load_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        src, tgt = line.split('=', 1)
                        self.glossario_map[src.strip()] = tgt.strip()
                    else:
                        self.glossario_map[line] = line
        except Exception:
            pass

    def load(self):
        """Carrega os termos do arquivo de glossário global e específicos."""
        GerenciadorConfig.garantir_estrutura_glossarios(self.filepath)
        if not os.path.exists(self.filepath):
            # Cria um arquivo de exemplo se não existir
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    f.write("# Dicionário / Glossário de Proteção\n")
                    f.write("# Adicione as palavras que você NÃO quer que o Google traduza errado.\n")
                    f.write("# Formato 1: Palavra Original = Palavra Destino\n")
                    f.write("# Formato 2: Apenas a Palavra (protege contra qualquer mudança)\n")
                    f.write("# Exemplos:\n")
                    f.write("# The Force=A Força\n")
                    f.write("# Hogwarts\n")
                    f.write("# Goku\n")
            except Exception:
                pass
        else:
            self._load_file(self.filepath)
            
        # Carrega dicionários específicos baseados no nome do vídeo
        dir_especificos = GerenciadorConfig.DIRETORIO_GLOSSARIOS
        if not os.path.exists(dir_especificos):
            try:
                os.makedirs(dir_especificos, exist_ok=True)
                with open(os.path.join(dir_especificos, 'LEIA_ME.txt'), 'w', encoding='utf-8') as f:
                    f.write("Coloque aqui dicionários específicos de animes (ex: Bleach.txt, One Piece.txt).\n")
                    f.write("Se o nome do vídeo que está sendo traduzido contiver o nome do arquivo, este dicionário será carregado automaticamente junto com o global.\n")
            except Exception:
                pass
                
        encontrou_especifico = False
        if self.video_filename and os.path.exists(dir_especificos):
            video_name_norm = self.video_filename.lower().replace('_', ' ').replace('-', ' ')
            for arquivo in os.listdir(dir_especificos):
                if arquivo.lower().endswith(".txt") and arquivo.lower() != "leia_me.txt":
                    caminho_especifico = os.path.join(dir_especificos, arquivo)
                    nome_anime = arquivo[:-4].lower().replace('_', ' ').replace('-', ' ')
                    aliases = [
                        a.replace('_', ' ').replace('-', ' ')
                        for a in self._extrair_aliases_arquivo(caminho_especifico)
                    ]
                    if nome_anime in video_name_norm or any(alias in video_name_norm for alias in aliases):
                        self._load_file(caminho_especifico)
                        encontrou_especifico = True
            
        # Se não encontrou na pasta e a busca automática estiver ativada, utiliza o buscador de entidades
        if self.video_filename and not encontrou_especifico and self.habilitar_auto_alimentar:
            try:
                buscador = self.buscador_entidades or AdaptadorAniListGraphQL(
                    pasta_destino=dir_especificos,
                    persistir_arquivo=True,
                )
                nomes = buscador.buscar_nomes_proprios(self.video_filename)
                if nomes:
                    for nome in nomes:
                        if nome and nome not in self.glossario_map:
                            self.glossario_map[nome] = nome
            except Exception:
                pass

    _PADRAO_TAGS_FORMATACAO = re.compile(r'(\{[^}\n]+\}|</?[a-zA-Z][^>\n]*>)')
    _PADRAO_TOKEN_RESTAURACAO = re.compile(
        r'(?i)\bT[ \t]*K[ \t]*G[ \t]*L[ \t]*O[ \t]*S[ \t]*S[ \t]*(\d+)[ \t]*T\b'
    )

    def _obter_padroes_termos(self):
        """Retorna lista de (pattern, key) pré-compilados em ordem decrescente de tamanho."""
        assinatura = tuple(self.glossario_map.items())
        if getattr(self, "_assinatura_regex", None) != assinatura:
            if not self.glossario_map:
                self._padroes_termos = []
            else:
                sorted_keys = sorted(self.glossario_map.keys(), key=len, reverse=True)
                self._padroes_termos = [
                    (re.compile(rf'(?i)(?<!\w){re.escape(k)}(?!\w)'), k)
                    for k in sorted_keys
                    if k
                ]
            self._assinatura_regex = assinatura
        return self._padroes_termos

    def apply_shield(self, text):
        """Aplica o escudo substituindo termos e tags de formatação por tokens."""
        mapping = {}
        tem_tags = bool(self._PADRAO_TAGS_FORMATACAO.search(text))
        if not self.glossario_map and not tem_tags:
            return text, mapping

        shielded_text = text
        counter = 0

        if tem_tags:
            def repl_tag(match):
                nonlocal counter
                token = f"TKGLOSS{counter}T"
                mapping[token] = match.group(0)
                counter += 1
                return f" {token} "

            shielded_text, _ = self._PADRAO_TAGS_FORMATACAO.subn(repl_tag, shielded_text)

        padroes = self._obter_padroes_termos()
        for pattern, key in padroes:
            def repl(match):
                nonlocal counter
                token = f"TKGLOSS{counter}T"
                mapping[token] = self.glossario_map[key]
                counter += 1
                return f" {token} "

            shielded_text, _ = pattern.subn(repl, shielded_text)

        return shielded_text, mapping

    def remove_shield(self, text, mapping):
        """Remove o escudo restaurando os termos traduzidos em passagem única."""
        if not mapping:
            return text

        def repl_restaurar(match):
            chave = f"TKGLOSS{match.group(1)}T"
            return mapping.get(chave, match.group(0))

        final_text = self._PADRAO_TOKEN_RESTAURACAO.sub(repl_restaurar, text)
            
        # Limpa espaços duplos linha a linha preservando quebras \n de borda do lote
        linhas = [re.sub(r'[ \t]+', ' ', linha).strip() for linha in final_text.split('\n')]
        final_text = '\n'.join(linhas)
        final_text = re.sub(r'(\{[^}\n]+\})[ \t]+', r'\1', final_text)
        final_text = re.sub(r'(<[a-zA-Z][^>/\n]*>)[ \t]+', r'\1', final_text)
        final_text = re.sub(r'[ \t]+(</[a-zA-Z][^>\n]*>)', r'\1', final_text)
        final_text = re.sub(r'[ \t]+([!?,;:.])', r'\1', final_text)
        return final_text

    def proteger(self, texto: str, id_linha: int = 0) -> LinhaProtegida:
        """Aplica o escudo e devolve um Value Object imutável vinculado ao id da linha.

        Delega integralmente para `apply_shield`, preservando o texto mascarado
        usado como chave do cache SQLite.
        """
        texto_mascarado, mapa_tokens = self.apply_shield(texto)
        return LinhaProtegida(
            id_linha=id_linha,
            texto_original=texto,
            texto_mascarado=texto_mascarado,
            mapa_tokens=mapa_tokens,
        )

    def restaurar(self, texto_traduzido: str, payload: LinhaProtegida) -> str:
        """Restaura os tokens do payload no texto devolvido pelo motor de tradução."""
        return self.remove_shield(texto_traduzido, payload.mapa_tokens)

