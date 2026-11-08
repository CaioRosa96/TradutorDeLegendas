"""Sintetizador em memoria de feedback sonoro suave ao concluir processamento."""

import io
import math
import struct
import wave

try:
    import winsound
except ImportError:
    winsound = None

_WAV_CACHE: bytes | None = None


def gerar_wav_acorde_conclusao(taxa_amostragem: int = 22050) -> bytes:
    """Sintetiza em memoria um acorde curto e suave (Do5 -> Sol5/Mi5) em formato WAV PCM 16-bit."""
    global _WAV_CACHE
    if _WAV_CACHE is not None and taxa_amostragem == 22050:
        return _WAV_CACHE

    segmentos = [
        (0.09, (523.25,)),          # Nota inicial: C5 (90ms)
        (0.15, (659.25, 783.99)),   # Acorde de resolucao: E5 + G5 (150ms)
    ]
    amplitude_max = 0.22 * 32767.0
    amostras = bytearray()

    for duracao, frequencias in segmentos:
        total_frames = int(taxa_amostragem * duracao)
        fade_frames = max(1, int(total_frames * 0.18))
        for i in range(total_frames):
            t = i / taxa_amostragem
            sinal = sum(math.sin(2.0 * math.pi * freq * t) for freq in frequencias) / len(frequencias)

            if i < fade_frames:
                envelope = i / fade_frames
            elif i > total_frames - fade_frames:
                envelope = max(0.0, (total_frames - i) / fade_frames)
            else:
                envelope = 1.0

            decaimento = math.exp(-3.0 * (i / max(1, total_frames)))
            valor = int(max(-32767, min(32767, sinal * amplitude_max * envelope * decaimento)))
            amostras.extend(struct.pack("<h", valor))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(taxa_amostragem)
        wav_file.writeframes(bytes(amostras))

    resultado = buffer.getvalue()
    if taxa_amostragem == 22050:
        _WAV_CACHE = resultado
    return resultado


def tocar_som_conclusao() -> bool:
    """Reproduz de forma assincrona o acorde de conclusao em memoria sem arquivos externos."""
    if winsound is None:
        return False

    try:
        dados_wav = gerar_wav_acorde_conclusao()
        flags = winsound.SND_MEMORY | winsound.SND_ASYNC | getattr(winsound, "SND_NODEFAULT", 0)
        winsound.PlaySound(dados_wav, flags)
        return True
    except Exception:
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
            return True
        except Exception:
            return False

