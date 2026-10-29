# Avisos de Software de Terceiros (Third-Party Notices)

O código-fonte original do projeto **Tradutor de Legendas** é licenciado sob a **Licença MIT** (consulte o arquivo [LICENSE](LICENSE)).

Para executar operações de multiplexação de contêineres, extração de faixas de mídia e transcrição acústica opcional, o aplicativo interage com ferramentas externas independentes via linha de comando (`subprocess` / comunicação interprocessos, caracterizando agregação simples nos termos da FAQ oficial da Free Software Foundation).

Abaixo estão listados os avisos de direitos autorais, licenças e links para obtenção do código-fonte dos componentes de terceiros utilizados ou suportados pelo ecossistema:

---

## 1. MKVToolNix (`mkvmerge` e `mkvextract`)

- **Autor / Copyright:** Copyright (c) Moritz Bunkus e colaboradores.
- **Licença:** GNU General Public License, Version 2 (GPLv2).
- **Forma de Integração:** Executado exclusivamente como processo externo independente via linha de comando (`mkvmerge -J`, `mkvmerge -o`, `mkvextract tracks`), sem linkagem estática ou dinâmica com o código Python deste repositório e sem qualquer modificação nos binários originais.
- **Distribuição em Executáveis Standalone (Releases):** Quando os binários inalterados `mkvmerge.exe` e `mkvextract.exe` acompanham os pacotes portáteis distribuídos nas Releases do GitHub, sua distribuição ocorre sob os termos da licença **GPLv2** (Seção 3).
- **Texto Integral da Licença GPLv2:** https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
- **Código-Fonte Oficial do MKVToolNix:**
  - Página oficial de código-fonte: https://mkvtoolnix.download/source.html
  - Repositório Git oficial: https://gitlab.com/mbunkus/mkvtoolnix

---

## 2. Mozilla Whisperfile / Llamafile (`whisper.cpp` + Cosmopolitan Libc)

- **Autores / Copyright:**
  - **Llamafile / Whisperfile:** Copyright (c) Mozilla Foundation, Justine Tunney e colaboradores.
  - **whisper.cpp:** Copyright (c) Georgi Gerganov e colaboradores.
  - **Modelos Whisper:** Copyright (c) OpenAI.
- **Licenças:**
  - **Llamafile / Cosmopolitan:** Apache License, Version 2.0 (https://www.apache.org/licenses/LICENSE-2.0).
  - **whisper.cpp e Pesos Whisper:** MIT License (https://opensource.org/licenses/MIT).
- **Forma de Integração:** Os executáveis do Whisperfile não são distribuídos dentro deste repositório Git. Quando o usuário opta por utilizar a transcrição local de áudio, o aplicativo realiza o download sob demanda diretamente dos repositórios oficiais da Mozilla no Hugging Face para a pasta local `bin/` do usuário.
- **Repositórios e Código-Fonte Oficial:**
  - Mozilla Llamafile (GitHub): https://github.com/Mozilla-Ocho/llamafile
  - Mozilla Whisperfile (Hugging Face): https://huggingface.co/Mozilla/whisperfile
  - whisper.cpp (GitHub): https://github.com/ggerganov/whisper.cpp

---

## 3. FFmpeg (`ffmpeg` e `ffprobe`)

- **Autor / Copyright:** Copyright (c) FFmpeg Developers.
- **Licença:** GNU Lesser General Public License (LGPL) v2.1+ ou GNU General Public License (GPL) v2+, dependendo das flags de compilação do binário instalado no sistema do usuário.
- **Forma de Integração:** Invocado opcionalmente como processo externo via linha de comando quando disponível no ambiente do usuário.
- **Informações Legais e Código-Fonte Oficial:** https://ffmpeg.org/legal.html e https://ffmpeg.org/download.html

---

## 4. Bibliotecas Python ( Ambiente de Execução )

As dependências Python listadas em `requirements.txt` possuem licenças permissivas compatíveis com a distribuição MIT:
- **CustomTkinter:** MIT License — Copyright (c) Tom Schimansky.
- **tkinterdnd2:** MIT License — Copyright (c) Eliav2 / Petasis.
- **pysubs2:** MIT License — Copyright (c) Tomas Karabela.
- **requests:** Apache License 2.0 — Copyright (c) Kenneth Reitz.
- **googletrans:** MIT License — Copyright (c) SuHun Han.
- **pytest / pytest-asyncio / pytest-mock:** MIT License.
