import os
import re
from .config import GerenciadorConfig

class GerenciadorGlossario:
    """Gerenciador do Dicionário Anti-Tradução (Glossário).
    
    Implementa a técnica de Tokenização Isolada:
    Substitui termos protegidos por tokens alienígenas antes de enviar ao Google,
    e restaura os termos originais após a tradução, impedindo alucinações da API.
    """
    
    def __init__(self, filepath=None, video_filename=None, habilitar_auto_alimentar=False):
        self.filepath = filepath or GerenciadorConfig.ARQUIVO_GLOSSARIO_PADRAO
        self.video_filename = video_filename
        self.habilitar_auto_alimentar = habilitar_auto_alimentar
        self.glossario_map = {}
        self.load()

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
            video_name_lower = self.video_filename.lower()
            for arquivo in os.listdir(dir_especificos):
                if arquivo.lower().endswith(".txt") and arquivo.lower() != "leia_me.txt":
                    nome_anime = arquivo[:-4].lower() # remove .txt
                    if nome_anime in video_name_lower:
                        self._load_file(os.path.join(dir_especificos, arquivo))
                        encontrou_especifico = True
            
            # Se não encontrou na pasta e a busca automática estiver ativada, roda o extrator
            if not encontrou_especifico and self.habilitar_auto_alimentar:
                try:
                    from .anilist import auto_alimentar
                    novo_arquivo = auto_alimentar(self.video_filename, dir_especificos)
                    if novo_arquivo and os.path.exists(novo_arquivo):
                        self._load_file(novo_arquivo)
                except Exception:
                    pass

    _PADRAO_TAGS_FORMATACAO = re.compile(r'(\{[^}\n]+\}|</?[a-zA-Z][^>\n]*>)')

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

        # Substitui os termos mais longos primeiro para evitar conflitos parciais
        sorted_keys = sorted(self.glossario_map.keys(), key=len, reverse=True)
        
        for key in sorted_keys:
            escaped_key = re.escape(key)
            pattern = re.compile(rf'(?i)\b{escaped_key}\b')
            
            def repl(match):
                nonlocal counter
                token = f"TKGLOSS{counter}T"
                mapping[token] = self.glossario_map[key]
                counter += 1
                return f" {token} "

            shielded_text, _ = pattern.subn(repl, shielded_text)
            
        return shielded_text, mapping

    def remove_shield(self, text, mapping):
        """Remove o escudo restaurando os termos traduzidos."""
        if not mapping:
            return text
            
        final_text = text
        for token, tgt in mapping.items():
            # O token sempre começa com TKGLOSS e termina com T
            # Usa [ \t]* em vez de \s* para nunca atravessar quebras de linha (\n) entre lotes.
            num = token[7:-1]
            pattern = re.compile(r'(?i)\bT[ \t]*K[ \t]*G[ \t]*L[ \t]*O[ \t]*S[ \t]*S[ \t]*' + str(num) + r'[ \t]*T\b')
            final_text = pattern.sub(lambda _: tgt, final_text)
            
        # Limpa espaços duplos linha a linha preservando quebras \n de borda do lote
        linhas = [re.sub(r'[ \t]+', ' ', linha).strip() for linha in final_text.split('\n')]
        final_text = '\n'.join(linhas)
        final_text = re.sub(r'(\{[^}\n]+\})[ \t]+', r'\1', final_text)
        return final_text

