"""
IA simulada para a demonstração pública (AI_BACKEND=demo).

Rodar Whisper + um modelo de linguagem exige um servidor com ~8 GB de RAM.
Na demonstração, este módulo ocupa o lugar deles com regras simples e
determinísticas, mantendo exatamente o mesmo fluxo do sistema:
    texto/áudio -> transcrição -> resumo estruturado -> revisão -> aprovação.

- Áudio: devolve uma transcrição de exemplo (o arquivo é apagado sem ser lido).
- Texto: organiza o próprio texto digitado em resumo, tópicos, pontos de
  acompanhamento e trechos para revisão, sem inventar nada e sem diagnóstico.

A implementação real continua em transcription.py e summarizer.py.
"""
import os
import re

from app.ai.summarizer import SessionSummary

SAMPLE_TRANSCRIPT = (
    "Paciente relatou que a semana foi mais tranquila no trabalho depois da conversa com a coordenadora. "
    "Contou que voltou a caminhar três vezes por semana e que tem dormido melhor. "
    "Falou sobre a ansiedade antes das reuniões de segunda-feira, que continua aparecendo. "
    "Mencionou uma discussão com o irmão no fim de semana, mas disse que conseguiram conversar depois. "
    "Combinamos que ela vai anotar, durante a semana, os momentos em que a ansiedade aparece. "
    "Na próxima sessão vamos retomar o tema da relação com o irmão. "
    "Ela comentou algo sobre mudar de cidade, mas não ficou claro se é um plano ou só uma ideia."
)

TOPICS = {
    "trabalho": "Trabalho",
    "reuni": "Trabalho",
    "sono": "Sono",
    "dorm": "Sono",
    "ansiedade": "Ansiedade",
    "ansios": "Ansiedade",
    "famíl": "Família",
    "irmã": "Família",
    "irmão": "Família",
    "mãe": "Família",
    "pai ": "Família",
    "caminh": "Atividade física",
    "exercício": "Atividade física",
    "relacionamento": "Relacionamentos",
    "namor": "Relacionamentos",
    "amig": "Relacionamentos",
    "estud": "Estudos",
    "faculdade": "Estudos",
    "mudar de cidade": "Mudanças",
    "mudança": "Mudanças",
}
FOLLOW_UP = ("combinamos", "combinou", "próxima sessão", "retomar", "vai anotar", "tarefa", "compromisso")
UNCLEAR = ("não ficou claro", "talvez", "não sei", "acho que", "?")


def enabled() -> bool:
    return os.getenv("AI_BACKEND", "local").lower() == "demo"


def transcribe(_audio_path: str) -> str:
    return SAMPLE_TRANSCRIPT


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 3]


def summarize(text: str) -> SessionSummary:
    sentences = _sentences(text)
    lower = text.lower()
    topics = []
    for key, label in TOPICS.items():
        if key in lower and label not in topics:
            topics.append(label)

    follow = [s for s in sentences if any(k in s.lower() for k in FOLLOW_UP)]
    unclear = [s for s in sentences if any(k in s.lower() for k in UNCLEAR)]
    body = [s for s in sentences if s not in follow and s not in unclear]
    summary = " ".join(body[:3]) or (sentences[0] if sentences else "")

    return SessionSummary(
        resumo=summary[:1000],
        topicos=topics or ["Tema geral da sessão"],
        pontos_de_acompanhamento=follow[:5],
        trechos_para_revisao=unclear[:5],
    )
