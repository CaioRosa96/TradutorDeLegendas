class Idiomas:
    """Mapeamento centralizado de códigos de idioma e rótulos localizados por idioma da interface.

    Converte os códigos ISO-639-2 do MKV (ex: 'jpn') para os códigos do
    Google Translate (ex: 'ja') e os códigos de destino do Google de volta
    para os metadados exigidos pelo mkvmerge, mantendo abreviações de interface
    100% adaptadas ao idioma selecionado pelo usuário.
    """

    _MKV_PARA_GOOGLE = {
        "eng": "en", "fra": "fr", "fre": "fr", "jpn": "ja", "spa": "es",
        "ger": "de", "deu": "de", "ita": "it", "por": "pt", "rus": "ru",
        "chi": "zh-cn", "zho": "zh-cn", "kor": "ko", "ara": "ar", "tha": "th",
        "pol": "pl", "nld": "nl", "dut": "nl", "tur": "tr", "ces": "cs",
        "cze": "cs", "swe": "sv", "hin": "hi", "vie": "vi", "ind": "id",
        "ukr": "uk", "ell": "el", "gre": "el", "hun": "hu", "ron": "ro",
        "rum": "ro", "dan": "da", "fin": "fi", "nor": "no", "bul": "bg",
    }

    # Códigos técnicos que significam "idioma desconhecido" no contêiner e acionam autodetecção.
    _INDEFINIDOS = {"auto", "und", "mis", "mul", "zxx"}

    # Destino (código Google) -> (código ISO-639-2 do mkvmerge, nome da trilha).
    _DESTINO_PARA_MKV = {
        "pt": ("por", "Português (Brasil)"),
        "en": ("eng", "English"),
        "es": ("spa", "Español"),
        "fr": ("fra", "Français"),
        "de": ("ger", "Deutsch"),
        "it": ("ita", "Italiano"),
        "ru": ("rus", "Русский"),
        "ja": ("jpn", "日本語"),
        "ko": ("kor", "한국어"),
        "zh-cn": ("chi", "中文 (简体)"),
    }

    @staticmethod
    def para_google(codigo):
        """Converte um código de idioma (MKV ou Google) para o código do Google Translate.

        Retorna 'auto' quando o idioma é desconhecido ou não mapeado.
        """
        if not codigo:
            return "auto"
        codigo = codigo.strip().lower()
        if codigo in Idiomas._INDEFINIDOS:
            return "auto"
        if codigo in Idiomas._MKV_PARA_GOOGLE.values():
            return codigo
        return Idiomas._MKV_PARA_GOOGLE.get(codigo, "auto")

    @staticmethod
    def destino_para_mkv(codigo_google):
        """Retorna (código ISO-639-2, nome da trilha) para embutir a legenda no MKV."""
        codigo = (codigo_google or "").strip().lower()
        return Idiomas._DESTINO_PARA_MKV.get(codigo, (codigo or "und", codigo.upper() or "Legenda"))

    _NOMES_DESTINO_MULTI = {
        "pt-br": {
            "pt": "Português (pt)", "en": "Inglês (ing)", "es": "Espanhol (esp)",
            "ja": "Japonês (jap)", "fr": "Francês (fra)", "de": "Alemão (ale)",
            "it": "Italiano (ita)", "ru": "Russo (rus)", "ko": "Coreano (cor)", "zh-cn": "Chinês (chi)"
        },
        "en": {
            "en": "English (en)", "pt": "Portuguese (pt)", "es": "Spanish (es)",
            "ja": "Japanese (ja)", "fr": "French (fr)", "de": "German (de)",
            "it": "Italian (it)", "ru": "Russian (ru)", "ko": "Korean (ko)", "zh-cn": "Chinese (zh)"
        },
        "es": {
            "es": "Español (esp)", "pt": "Portugués (por)", "en": "Inglés (ing)",
            "ja": "Japonés (jap)", "fr": "Francés (fra)", "de": "Alemán (ale)",
            "it": "Italiano (ita)", "ru": "Ruso (rus)", "ko": "Coreano (cor)", "zh-cn": "Chino (chi)"
        },
        "ja": {
            "ja": "日本語 (日)", "pt": "ポルトガル語 (葡)", "en": "英語 (英)",
            "es": "スペイン語 (西)", "fr": "フランス語 (仏)", "de": "ドイツ語 (独)",
            "it": "イタリア語 (伊)", "ru": "ロシア語 (露)", "ko": "韓国語 (韓)", "zh-cn": "中国語 (中)"
        },
        "zh-cn": {
            "zh-cn": "中文 (中)", "pt": "葡萄牙语 (葡)", "en": "英语 (英)",
            "es": "西班牙语 (西)", "ja": "日语 (日)", "fr": "法语 (法)",
            "de": "德语 (德)", "it": "意大利语 (意)", "ru": "俄语 (俄)", "ko": "韩语 (韩)"
        }
    }

    _NOMES_ORIGEM_MULTI = {
        "pt-br": {
            "auto": "Automático (auto)", "und": "Indefinido no vídeo (ind)",
            "jpn": "Japonês (jap)", "eng": "Inglês (ing)",
            "por": "Português (por)", "spa": "Espanhol (esp)", "fra": "Francês (fra)",
            "deu": "Alemão (ale)", "ger": "Alemão (ale)", "ita": "Italiano (ita)",
            "rus": "Russo (rus)", "kor": "Coreano (cor)", "chi": "Chinês (chi)", "zho": "Chinês (chi)"
        },
        "en": {
            "auto": "Auto (auto)", "und": "Undefined in video (und)",
            "jpn": "Japanese (jpn)", "eng": "English (eng)",
            "por": "Portuguese (por)", "spa": "Spanish (spa)", "fra": "French (fra)",
            "deu": "German (ger)", "ger": "German (ger)", "ita": "Italian (ita)",
            "rus": "Russian (rus)", "kor": "Korean (kor)", "chi": "Chinese (chi)", "zho": "Chinese (chi)"
        },
        "es": {
            "auto": "Automático (auto)", "und": "Indefinido en vídeo (ind)",
            "jpn": "Japonés (jap)", "eng": "Inglés (ing)",
            "por": "Portugués (por)", "spa": "Español (esp)", "fra": "Francés (fra)",
            "deu": "Alemán (ale)", "ger": "Alemán (ale)", "ita": "Italiano (ita)",
            "rus": "Ruso (rus)", "kor": "Coreano (cor)", "chi": "Chino (chi)", "zho": "Chino (chi)"
        },
        "ja": {
            "auto": "自動検出 (自動)", "und": "動画内で未定義 (未定)",
            "jpn": "日本語 (日)", "eng": "英語 (英)",
            "por": "ポルトガル語 (葡)", "spa": "スペイン語 (西)", "fra": "フランス語 (仏)",
            "deu": "ドイツ語 (独)", "ger": "ドイツ語 (独)", "ita": "イタリア語 (伊)",
            "rus": "ロシア語 (露)", "kor": "韓国語 (韓)", "chi": "中国語 (中)", "zho": "中国語 (中)"
        },
        "zh-cn": {
            "auto": "自动检测 (自动)", "und": "视频未定义语言 (未定)",
            "chi": "中文 (中)", "zho": "中文 (中)",
            "eng": "英语 (英)", "jpn": "日语 (日)", "por": "葡萄牙语 (葡)",
            "spa": "西班牙语 (西)", "fra": "法语 (法)", "deu": "德语 (德)",
            "ger": "德语 (德)", "ita": "意大利语 (意)", "rus": "俄语 (俄)", "kor": "韩语 (韩)"
        }
    }

    _CODIGOS_ORIGEM_PADRAO = ["auto", "por", "eng", "jpn", "spa", "fra", "deu", "ita", "rus", "kor", "chi"]

    _NOMES_DESTINO = _NOMES_DESTINO_MULTI["pt-br"]
    _NOMES_ORIGEM = _NOMES_ORIGEM_MULTI["pt-br"]

    @classmethod
    def opcoes_origem_padrao(cls) -> list[str]:
        """Retorna a lista de códigos de idioma de origem padrão para seleção manual."""
        return list(cls._CODIGOS_ORIGEM_PADRAO)

    @classmethod
    def opcoes_destino_exibicao(cls, idioma_ui: str = None):
        """Retorna lista de rotulos legiveis para o menu suspenso de destino no idioma ativo."""
        idioma = idioma_ui or "pt-br"
        mapa = cls._NOMES_DESTINO_MULTI.get(idioma, cls._NOMES_DESTINO_MULTI["pt-br"])
        return list(mapa.values())

    @classmethod
    def rotular_destino(cls, codigo: str, idioma_ui: str = None) -> str:
        """Retorna o rotulo de exibicao correspondente ao codigo Google no idioma da UI."""
        cod = (codigo or "pt").strip().lower()
        idioma = idioma_ui or "pt-br"
        mapa = cls._NOMES_DESTINO_MULTI.get(idioma, cls._NOMES_DESTINO_MULTI["pt-br"])
        return mapa.get(cod, f"{cod.upper()} ({cod})")

    @classmethod
    def abreviar_destino(cls, codigo: str, idioma_ui: str = None) -> str:
        """Retorna a abreviação localizada de destino (ex: 'ING' em pt-br, '英' em ja/zh-cn)."""
        rotulo = cls.rotular_destino(codigo, idioma_ui)
        if "(" in rotulo and ")" in rotulo:
            return rotulo.split("(")[-1].split(")")[0].strip().upper()
        return (codigo or "PT").upper()

    @classmethod
    def nome_para_codigo_destino(cls, nome_ou_codigo):
        """Converte o rotulo amigavel localizado de volta para o codigo tecnico Google."""
        if not nome_ou_codigo:
            return "pt"
        val = nome_ou_codigo.strip()
        for mapa in cls._NOMES_DESTINO_MULTI.values():
            for cod, nome in mapa.items():
                if val == nome or val.lower() == cod:
                    return cod
        if "(" in val and ")" in val:
            abrev = val.split("(")[-1].split(")")[0].strip().lower()
            for mapa in cls._NOMES_DESTINO_MULTI.values():
                for cod, nome in mapa.items():
                    if nome.lower().endswith(f"({abrev})"):
                        return cod
            return abrev
        return val.lower()

    @classmethod
    def rotular_origem(cls, codigo_mkv: str, idioma_ui: str = None) -> str:
        """Retorna o rotulo amigavel para um codigo de trilha MKV no idioma ativo da UI."""
        cod = (codigo_mkv or "auto").strip().lower()
        idioma = idioma_ui or "pt-br"
        mapa = cls._NOMES_ORIGEM_MULTI.get(idioma, cls._NOMES_ORIGEM_MULTI["pt-br"])
        return mapa.get(cod, f"{cod.upper()} ({cod})")

    @classmethod
    def nome_para_codigo_origem(cls, nome_ou_codigo):
        """Converte o rotulo amigavel localizado da UI de volta para o codigo tecnico MKV."""
        if not nome_ou_codigo:
            return "auto"
        val = nome_ou_codigo.strip()
        for mapa in cls._NOMES_ORIGEM_MULTI.values():
            for cod, nome in mapa.items():
                if val == nome or val.lower() == cod:
                    return cod
        if "(" in val and ")" in val:
            abrev = val.split("(")[-1].split(")")[0].strip().lower()
            for mapa in cls._NOMES_ORIGEM_MULTI.values():
                for cod, nome in mapa.items():
                    if nome.lower().endswith(f"({abrev})"):
                        return cod
            return abrev
        return val.lower()
