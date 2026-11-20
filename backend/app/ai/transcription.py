"""
Transcrição de áudio com Whisper rodando LOCALMENTE (faster-whisper).

O áudio nunca sai do nosso servidor: nenhum serviço externo recebe a
voz do paciente.

Configuração (.env):
    WHISPER_MODEL   tamanho do modelo: tiny, base, small, medium, large-v3
                    (maior = mais preciso e mais lento). Padrão: small.
    WHISPER_DEVICE  cpu ou cuda (GPU NVIDIA). Padrão: cpu.

Na primeira execução o modelo é baixado (uma única vez) e fica em cache.
"""
import os
import threading

_model = None
_lock = threading.Lock()


def model_name() -> str:
    return os.getenv("WHISPER_MODEL", "small")


def _get_model():
    """Carrega o modelo uma única vez (é pesado) e reaproveita."""
    global _model
    with _lock:
        if _model is None:
            from faster_whisper import WhisperModel  # import tardio: só quando usado

            device = os.getenv("WHISPER_DEVICE", "cpu")
            compute_type = "int8" if device == "cpu" else "float16"
            _model = WhisperModel(model_name(), device=device, compute_type=compute_type)
        return _model


class Transcript(str):
    """O texto transcrito, com a duração do áudio (em segundos) junto."""
    duration: float | None = None


def transcribe(audio_path: str) -> str:
    """Transcreve um arquivo de áudio em português e devolve o texto (um Transcript)."""
    segments, info = _get_model().transcribe(
        audio_path,
        language="pt",
        vad_filter=True,  # ignora trechos de silêncio
    )
    result = Transcript(" ".join(segment.text.strip() for segment in segments).strip())
    result.duration = getattr(info, "duration", None)
    return result
