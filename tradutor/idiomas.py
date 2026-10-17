class Idiomas:
    """Mapeamento centralizado de códigos de idioma.

    Converte os códigos ISO-639-2 do MKV (ex: 'jpn') para os códigos do
    Google Translate (ex: 'ja') e os códigos de destino do Google de volta
    para os metadados exigidos pelo mkvmerge.
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

    # Códigos que significam "idioma desconhecido" e devem usar a autodetecção.
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
            "pt": "Português (pt)", "en": "Inglês (en)", "es": "Espanhol (es)",
            "ja": "Japonês (ja)", "fr": "Francês (fr)", "de": "Alemão (de)",
            "it": "Italiano (it)", "ru": "Russo (ru)", "ko": "Coreano (ko)", "zh-cn": "Chinês (zh-cn)"
        },
        "en": {
            "en": "English (en)", "pt": "Portuguese (pt)", "es": "Spanish (es)",
            "ja": "Japanese (ja)", "fr": "French (fr)", "de": "German (de)",
            "it": "Italian (it)", "ru": "Russian (ru)", "ko": "Korean (ko)", "zh-cn": "Chinese (zh-cn)"
        },
        "es": {
            "es": "Español (es)", "pt": "Portugués (pt)", "en": "Inglés (en)",
            "ja": "Japonés (ja)", "fr": "Francés (fr)", "de": "Alemán (de)",
            "it": "Italiano (it)", "ru": "Ruso (ru)", "ko": "Coreano (ko)", "zh-cn": "Chino (zh-cn)"
        },
        "ja": {
            "ja": "日本語 (ja)", "pt": "ポルトガル語 (pt)", "en": "英語 (en)",
            "es": "スペイン語 (es)", "fr": "フランス語 (fr)", "de": "ドイツ語 (de)",
            "it": "イタリア語 (it)", "ru": "ロシア語 (ru)", "ko": "韓国語 (ko)", "zh-cn": "中国語 (zh-cn)"
        },
        "zh-cn": {
            "zh-cn": "中文 (zh-cn)", "pt": "葡萄牙语 (pt)", "en": "英语 (en)",
            "es": "西班牙语 (es)", "ja": "日语 (ja)", "fr": "法语 (fr)",
            "de": "德语 (de)", "it": "意大利语 (it)", "ru": "俄语 (ru)", "ko": "韩语 (ko)"
        }
    }

    _NOMES_ORIGEM_MULTI = {
        "pt-br": {
            "auto": "Automático (auto)", "jpn": "Japonês (jpn)", "eng": "Inglês (eng)",
            "por": "Português (por)", "spa": "Espanhol (spa)", "fra": "Francês (fra)",
            "deu": "Alemão (deu)", "ger": "Alemão (ger)", "ita": "Italiano (ita)",
            "rus": "Russo (rus)", "kor": "Coreano (kor)", "chi": "Chinês (chi)", "zho": "Chinês (zho)"
        },
        "en": {
            "auto": "Auto (auto)", "jpn": "Japanese (jpn)", "eng": "English (eng)",
            "por": "Portuguese (por)", "spa": "Spanish (spa)", "fra": "French (fra)",
            "deu": "German (deu)", "ger": "German (ger)", "ita": "Italian (ita)",
            "rus": "Russian (rus)", "kor": "Korean (kor)", "chi": "Chinese (chi)", "zho": "Chinese (zho)"
        },
        "es": {
            "auto": "Automático (auto)", "jpn": "Japonés (jpn)", "eng": "Inglés (eng)",
            "por": "Portugués (por)", "spa": "Español (spa)", "fra": "Francés (fra)",
            "deu": "Alemán (deu)", "ger": "Alemán (ger)", "ita": "Italiano (ita)",
            "rus": "Ruso (rus)", "kor": "Coreano (kor)", "chi": "Chino (chi)", "zho": "Chino (zho)"
        },
        "ja": {
            "auto": "自動検出 (auto)", "jpn": "日本語 (jpn)", "eng": "英語 (eng)",
            "por": "ポルトガル語 (por)", "spa": "スペイン語 (spa)", "fra": "フランス語 (fra)",
            "deu": "ドイツ語 (deu)", "ger": "ドイツ語 (ger)", "ita": "イタリア語 (ita)",
            "rus": "ロシア語 (rus)", "kor": "韓国語 (kor)", "chi": "中国語 (chi)", "zho": "中国語 (zho)"
        },
        "zh-cn": {
            "auto": "自动检测 (auto)", "chi": "中文 (chi)", "zho": "中文 (zho)",
            "eng": "英语 (eng)", "jpn": "日语 (jpn)", "por": "葡萄牙语 (por)",
            "spa": "西班牙语 (spa)", "fra": "法语 (fra)", "deu": "德语 (deu)",
            "ger": "德语 (ger)", "ita": "意大利语 (ita)", "rus": "俄语 (rus)", "kor": "韩语 (kor)"
        }
    }

    _NOMES_DESTINO = _NOMES_DESTINO_MULTI["pt-br"]
    _NOMES_ORIGEM = _NOMES_ORIGEM_MULTI["pt-br"]

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
    def nome_para_codigo_destino(cls, nome_ou_codigo):
        """Converte o rotulo amigavel de volta para o codigo Google (ex: 'English (en)' -> 'en')."""
        if not nome_ou_codigo:
            return "pt"
        val = nome_ou_codigo.strip()
        if "(" in val and ")" in val:
            return val.split("(")[-1].split(")")[0].strip().lower()
        for mapa in cls._NOMES_DESTINO_MULTI.values():
            for cod, nome in mapa.items():
                if val == nome or val.lower() == cod:
                    return cod
        return val.lower()

    @classmethod
    def rotular_origem(cls, codigo, idioma_ui: str = None):
        """Retorna o rotulo legivel para o idioma de origem no idioma da UI."""
        cod = (codigo or "").strip().lower()
        idioma = idioma_ui or "pt-br"
        mapa = cls._NOMES_ORIGEM_MULTI.get(idioma, cls._NOMES_ORIGEM_MULTI["pt-br"])
        padrao_auto = mapa.get("auto", "Automático (auto)")
        return mapa.get(cod, f"{cod.upper()} ({cod})" if cod else padrao_auto)

    @classmethod
    def nome_para_codigo_origem(cls, nome_ou_codigo):
        """Converte o rotulo de exibicao de volta para o codigo de origem (ex: 'Japanese (jpn)' -> 'jpn')."""
        if not nome_ou_codigo:
            return "auto"
        val = nome_ou_codigo.strip()
        if "(" in val and ")" in val:
            return val.split("(")[-1].split(")")[0].strip().lower()
        for mapa in cls._NOMES_ORIGEM_MULTI.values():
            for cod, nome in mapa.items():
                if val == nome or val.lower() == cod:
                    return cod
        return val.lower()

