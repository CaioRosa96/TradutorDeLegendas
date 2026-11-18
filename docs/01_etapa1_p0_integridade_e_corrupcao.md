# Etapa 1 (P0): Integridade de Dados, Corrupcao e Falsos Sucessos

**Instrucao para o Antigravity:** Aplique exatamente os blocos `SEARCH` / `REPLACE` abaixo sem explorar outros arquivos do repositorio.

---

## 1. `tradutor/servico_traducao.py`
**Objetivo:** Adicionar orcamento maximo de caracteres na montagem dos lotes (`LIMITE_CARACTERES_LOTE = 3500`) e salvar o arquivo final de forma atomica preservando a extensao para o `pysubs2`.

### Alteracao 1.1: Metodo `_montar_lotes` e escrita atomica em `pipeline`

#### SEARCH
```python
        lotes = [
            indices_map[i : i + GerenciadorConfig.TAMANHO_LOTE]
            for i in range(0, self._total_linhas, GerenciadorConfig.TAMANHO_LOTE)
        ]
        semaforo = asyncio.Semaphore(GerenciadorConfig.MAX_CONCORRENTE)
        pbar_lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=GerenciadorConfig.MAX_CONCORRENTE) as executor:
            tasks = [self._traduzir_lote(executor, semaforo, lote, subs, pbar_lock, src_lang, dest_norm) for lote in lotes]
            await asyncio.gather(*tasks)

        if self._is_cancelled():
            self._logger("[AVISO] Tradução abortada pelo usuário.")
            return False

        if self._disjuntor_disparado:
            self._logger("[ERRO CRÍTICO] Tradução interrompida: Circuit Breaker disparado.")
            raise ExcecaoDisjuntorAberto("Circuit Breaker ABERTO: Abortando para evitar banimentos.")

        if self._total_linhas > 0 and self._linhas_traduzidas_sucesso == 0:
            self._logger("[ERRO CRÍTICO] Falha total: nenhuma linha pôde ser traduzida com sucesso.")
            raise RuntimeError("Falha total na tradução: nenhuma linha foi traduzida.")

        self._logger("Salvando arquivo de legendas traduzido...")
        subs.save(destino)
        return True
```

#### REPLACE
```python
        lotes = self._montar_lotes(subs, indices_map)
        semaforo = asyncio.Semaphore(GerenciadorConfig.MAX_CONCORRENTE)
        pbar_lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=GerenciadorConfig.MAX_CONCORRENTE) as executor:
            tasks = [self._traduzir_lote(executor, semaforo, lote, subs, pbar_lock, src_lang, dest_norm) for lote in lotes]
            await asyncio.gather(*tasks)

        if self._is_cancelled():
            self._logger("[AVISO] Tradução abortada pelo usuário.")
            return False

        if self._disjuntor_disparado:
            self._logger("[ERRO CRÍTICO] Tradução interrompida: Circuit Breaker disparado.")
            raise ExcecaoDisjuntorAberto("Circuit Breaker ABERTO: Abortando para evitar banimentos.")

        if self._total_linhas > 0 and self._linhas_traduzidas_sucesso == 0:
            self._logger("[ERRO CRÍTICO] Falha total: nenhuma linha pôde ser traduzida com sucesso.")
            raise RuntimeError("Falha total na tradução: nenhuma linha foi traduzida.")

        self._logger("Salvando arquivo de legendas traduzido...")
        self._salvar_legenda_atomico(subs, destino)
        return True

    @staticmethod
    def _montar_lotes(subs, indices_map: list[int]) -> list[list[int]]:
        """Agrupa índices respeitando simultaneamente limite de linhas e orçamento de caracteres."""
        max_linhas = max(1, int(getattr(GerenciadorConfig, "TAMANHO_LOTE", 40)))
        max_chars = max(200, int(getattr(GerenciadorConfig, "LIMITE_CARACTERES_LOTE", 3500)))
        lotes: list[list[int]] = []
        lote_atual: list[int] = []
        chars_atual = 0

        for idx in indices_map:
            tam_linha = len(subs[idx].text) + 1
            if lote_atual and (len(lote_atual) >= max_linhas or chars_atual + tam_linha > max_chars):
                lotes.append(lote_atual)
                lote_atual = [idx]
                chars_atual = tam_linha
            else:
                lote_atual.append(idx)
                chars_atual += tam_linha

        if lote_atual:
            lotes.append(lote_atual)
        return lotes

    @staticmethod
    def _salvar_legenda_atomico(subs, destino: str) -> None:
        """Salva a legenda em arquivo temporário com a mesma extensão e promove via os.replace."""
        base_dest, ext_dest = os.path.splitext(destino)
        ext_efetiva = ext_dest if ext_dest else ".srt"
        destino_tmp = f"{base_dest}.tmp_{os.getpid()}_{threading.get_ident()}{ext_efetiva}"
        try:
            subs.save(destino_tmp)
            os.replace(destino_tmp, destino)
        except Exception:
            if os.path.isfile(destino_tmp):
                try:
                    os.remove(destino_tmp)
                except OSError:
                    pass
            raise
```

---

## 2. `tradutor/estrategias/processador_base.py`
**Objetivo:** Impedir que o cancelamento ou falha antes da gravacao apague uma legenda preexistente no destino quando `manter_legenda=False`.

### Alteracao 2.1: Rastrear `legenda_preexistente` e `legenda_gerada_nesta_execucao`

#### SEARCH
```python
        try:
            caminho_legenda_final = caminhos_saida['legenda']

            # 5. Tradução (ou cópia direta quando já transcrito no idioma de destino)
            if mesmo_idioma and getattr(self, "_transcrito_por_ia", False):
                shutil.copyfile(arq_trabalho, caminho_legenda_final)
            else:
                self.log(self.get_translation_message())
                engine = self.engine or MotorTraducaoGoogle(max_retries=GerenciadorConfig.MAX_RETENTATIVAS)
                translator_svc = ServicoTraducao(
                    logger=self.log,
                    progress_callback=self.update_progress,
                    is_cancelled_callback=lambda: not self.is_running(),
                    engine=engine,
                    video_filename=os.path.basename(origem),
                )
                sucesso_trad = asyncio.run(
                    translator_svc.pipeline(arq_trabalho, caminho_legenda_final, idioma_real, idioma_destino)
                )
                if not sucesso_trad or not os.path.isfile(caminho_legenda_final):
                    self.log("[ERRO CRÍTICO] Tradução falhou ou arquivo final ausente. Abortando multiplexação.")
                    self.cleanup_temporary(arq_trabalho)
                    if not manter_legenda and os.path.isfile(caminho_legenda_final) and os.path.abspath(caminho_legenda_final) != os.path.abspath(origem):
                        try:
                            os.remove(caminho_legenda_final)
                        except OSError:
                            pass
                    return False

            if not self.is_running():
                self.cleanup_temporary(arq_trabalho)
                if not manter_legenda and os.path.isfile(caminho_legenda_final) and os.path.abspath(caminho_legenda_final) != os.path.abspath(origem):
                    try:
                        os.remove(caminho_legenda_final)
                    except OSError:
                        pass
                return False

            # 6. Finalização (Muxing MKV ou Conclusão SRT)
            self.finalize(origem, caminho_legenda_final, caminhos_saida, idioma_destino, arq_trabalho, manter_legenda)
            return True

        except Exception as e:
            self.cleanup_temporary(arq_trabalho)
            if (
                not manter_legenda
                and 'caminho_legenda_final' in locals()
                and os.path.isfile(caminho_legenda_final)
                and os.path.abspath(caminho_legenda_final) != os.path.abspath(origem)
            ):
                try:
                    os.remove(caminho_legenda_final)
                except OSError:
                    pass
            raise e
```

#### REPLACE
```python
        caminho_legenda_final = caminhos_saida['legenda']
        legenda_preexistente = bool(caminho_legenda_final and os.path.isfile(caminho_legenda_final))
        legenda_gerada_nesta_execucao = False

        try:
            # 5. Tradução (ou cópia direta quando já transcrito no idioma de destino)
            if mesmo_idioma and getattr(self, "_transcrito_por_ia", False):
                shutil.copyfile(arq_trabalho, caminho_legenda_final)
                legenda_gerada_nesta_execucao = True
            else:
                self.log(self.get_translation_message())
                engine = self.engine or MotorTraducaoGoogle(max_retries=GerenciadorConfig.MAX_RETENTATIVAS)
                translator_svc = ServicoTraducao(
                    logger=self.log,
                    progress_callback=self.update_progress,
                    is_cancelled_callback=lambda: not self.is_running(),
                    engine=engine,
                    video_filename=os.path.basename(origem),
                )
                sucesso_trad = asyncio.run(
                    translator_svc.pipeline(arq_trabalho, caminho_legenda_final, idioma_real, idioma_destino)
                )
                legenda_gerada_nesta_execucao = bool(sucesso_trad and os.path.isfile(caminho_legenda_final))
                if not legenda_gerada_nesta_execucao:
                    self.log("[ERRO CRÍTICO] Tradução falhou ou arquivo final ausente. Abortando multiplexação.")
                    self.cleanup_temporary(arq_trabalho)
                    self._limpar_legenda_intermediaria(
                        caminho_legenda_final,
                        origem,
                        manter_legenda,
                        legenda_preexistente,
                        legenda_gerada_nesta_execucao,
                    )
                    return False

            if not self.is_running():
                self.cleanup_temporary(arq_trabalho)
                self._limpar_legenda_intermediaria(
                    caminho_legenda_final,
                    origem,
                    manter_legenda,
                    legenda_preexistente,
                    legenda_gerada_nesta_execucao,
                )
                return False

            # 6. Finalização (Muxing MKV ou Conclusão SRT)
            self.finalize(origem, caminho_legenda_final, caminhos_saida, idioma_destino, arq_trabalho, manter_legenda)
            return True

        except Exception as e:
            self.cleanup_temporary(arq_trabalho)
            self._limpar_legenda_intermediaria(
                caminho_legenda_final,
                origem,
                manter_legenda,
                legenda_preexistente,
                legenda_gerada_nesta_execucao,
            )
            raise e

    @staticmethod
    def _limpar_legenda_intermediaria(
        caminho_legenda_final: str | None,
        origem: str,
        manter_legenda: bool,
        legenda_preexistente: bool,
        legenda_gerada_nesta_execucao: bool,
    ) -> None:
        """Remove a legenda intermediária apenas se não era um arquivo preexistente intocado."""
        if (
            not manter_legenda
            and caminho_legenda_final
            and os.path.isfile(caminho_legenda_final)
            and os.path.abspath(caminho_legenda_final) != os.path.abspath(origem)
            and (legenda_gerada_nesta_execucao or not legenda_preexistente)
        ):
            try:
                os.remove(caminho_legenda_final)
            except OSError:
                pass
```

---

## 3. `tradutor/glossario.py`
**Objetivo:** Remover espaco injetado antes de ponto final (`.`) e ao redor de tags HTML/ASS na restauracao do escudo.

### Alteracao 3.1: Ajuste de `remove_shield`

#### SEARCH
```python
        # Limpa espaços duplos linha a linha preservando quebras \n de borda do lote
        linhas = [re.sub(r'[ \t]+', ' ', linha).strip() for linha in final_text.split('\n')]
        final_text = '\n'.join(linhas)
        final_text = re.sub(r'(\{[^}\n]+\})[ \t]+', r'\1', final_text)
        final_text = re.sub(r'[ \t]+([!?,;:])', r'\1', final_text)
        return final_text
```

#### REPLACE
```python
        # Limpa espaços duplos linha a linha preservando quebras \n de borda do lote
        linhas = [re.sub(r'[ \t]+', ' ', linha).strip() for linha in final_text.split('\n')]
        final_text = '\n'.join(linhas)
        final_text = re.sub(r'(\{[^}\n]+\})[ \t]+', r'\1', final_text)
        final_text = re.sub(r'(<[a-zA-Z][^>/\n]*>)[ \t]+', r'\1', final_text)
        final_text = re.sub(r'[ \t]+(</[a-zA-Z][^>\n]*>)', r'\1', final_text)
        final_text = re.sub(r'[ \t]+([!?,;:.])', r'\1', final_text)
        return final_text
```

---

## 4. `tradutor/particionador_texto.py`
**Objetivo:** Manter a pontuacao de fim de sentenca (`.`, `!`, `?`, `;`) anexada ao bloco de texto enviado ao tradutor, deixando apenas o espaco como delimitador externo.

### Alteracao 4.1: Ajuste em `_dividir_em_unidades`

#### SEARCH
```python
        unidades: list[tuple[str, str]] = []
        for i, parte in enumerate(partes):
            delimitador = sep if i < len(partes) - 1 else ""
            if len(parte) <= self._limite_caracteres:
                if parte:
                    unidades.append((parte, delimitador))
                elif delimitador:
                    if unidades:
                        u_ant, d_ant = unidades[-1]
                        unidades[-1] = (u_ant, d_ant + delimitador)
                    else:
                        unidades.append(("", delimitador))
            else:
                sub = self._dividir_em_unidades(parte, nivel + 1)
                if sub and delimitador:
                    u_ult, d_ult = sub[-1]
                    sub[-1] = (u_ult, d_ult + delimitador)
                unidades.extend(sub)
        return unidades
```

#### REPLACE
```python
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
```

---

## 5. Testes de Regressao da Etapa 1
Adicione ao final de `tests/unit/test_boost_regressoes.py`:

```python
def test_etapa1_orcamento_caracteres_divide_lote_grande(tmp_path):
    import pysubs2
    from tradutor.servico_traducao import ServicoTraducao

    subs = pysubs2.SSAFile()
    for _ in range(10):
        subs.append(pysubs2.SSAEvent(start=0, end=1000, text="A" * 600))

    indices = list(range(len(subs)))
    lotes = ServicoTraducao._montar_lotes(subs, indices)
    assert len(lotes) >= 2
    for lote in lotes:
        assert sum(len(subs[i].text) for i in lote) <= 3500


def test_etapa1_escudo_remove_espaco_antes_de_ponto_e_tags_html(tmp_path):
    from tradutor.glossario import GerenciadorGlossario

    arq_gloss = tmp_path / "glossario.txt"
    arq_gloss.write_text("Goku\n", encoding="utf-8")
    g = GerenciadorGlossario(filepath=str(arq_gloss))

    payload = g.proteger("<i>Goku</i>.")
    restaurado = g.restaurar(payload.texto_mascarado, payload)
    assert restaurado == "<i>Goku</i>."


def test_etapa1_particionador_preserva_interrogacao_no_bloco():
    from tradutor.particionador_texto import ParticionadorTexto

    p = ParticionadorTexto(limite_caracteres=18)
    texto = "Voce esta bem? Eu estou otimo!"
    blocos = p.particionar(texto)
    assert blocos[0].endswith("?")
    assert p.recompor_texto(texto, blocos, blocos) == texto
```