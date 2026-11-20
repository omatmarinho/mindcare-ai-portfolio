"""
Resumo estruturado com um modelo de linguagem OPEN SOURCE rodando
localmente via Ollama (https://ollama.com).

O texto clínico nunca sai do nosso servidor.

Configuração (.env):
    OLLAMA_URL   endereço do Ollama. Padrão: http://127.0.0.1:11434
    LLM_MODEL    modelo instalado no Ollama (ex.: qwen2:7b). Padrão: qwen2:7b

LIMITES DA IA (definidos no prompt e reforçados na revisão humana):
- não faz diagnóstico, não sugere tratamento nem medicação;
- só organiza o que está no texto, sem inventar;
- o resultado é um RASCUNHO que o psicólogo revisa e aprova.
"""
import os

import httpx
from pydantic import BaseModel, Field, ValidationError


class SessionSummary(BaseModel):
    """Formato do resumo devolvido pela IA (e editado pelo psicólogo)."""
    resumo: str = Field(default="", max_length=5000)
    topicos: list[str] = Field(default_factory=list, max_length=30)
    pontos_de_acompanhamento: list[str] = Field(default_factory=list, max_length=30)
    trechos_para_revisao: list[str] = Field(default_factory=list, max_length=30)


SYSTEM_PROMPT = """Você é um assistente de documentação para psicólogos. Sua única tarefa é \
ORGANIZAR, em português do Brasil, o conteúdo de uma transcrição ou anotação de sessão.

Regras obrigatórias:
1. Use somente informações presentes no texto. Nunca invente fatos, falas ou detalhes.
2. NÃO faça diagnósticos, NÃO levante hipóteses diagnósticas, NÃO sugira tratamentos, \
técnicas, encaminhamentos ou medicações. Decisões clínicas são exclusivas do psicólogo.
3. Escreva de forma objetiva e neutra, sem julgamentos.
4. Se algum trecho estiver confuso, incompleto ou ambíguo, não tente adivinhar: \
liste-o em "trechos_para_revisao".

Responda APENAS com um JSON contendo:
- "resumo": um parágrafo curto com o que foi tratado na sessão;
- "topicos": lista dos temas discutidos;
- "pontos_de_acompanhamento": itens mencionados que o psicólogo pode querer retomar \
(compromissos combinados, assuntos a continuar), sem recomendações clínicas;
- "trechos_para_revisao": trechos que precisam de conferência humana."""


class SummarizationError(RuntimeError):
    pass


def model_name() -> str:
    return os.getenv("LLM_MODEL", "qwen2:7b")


def summarize(text: str) -> SessionSummary:
    """Gera o resumo estruturado de um texto de sessão."""
    url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")

    try:
        response = httpx.post(
            f"{url}/api/chat",
            json={
                "model": model_name(),
                "stream": False,
                # Saída estruturada: o Ollama força o JSON a seguir este schema
                "format": SessionSummary.model_json_schema(),
                "options": {"temperature": 0.2},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Texto da sessão:\n\n{text}"},
                ],
            },
            timeout=900,  # modelos locais em CPU podem levar alguns minutos
        )
        response.raise_for_status()
        content = response.json()["message"]["content"]
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise SummarizationError("Falha ao comunicar com o modelo de IA local.") from exc

    try:
        return SessionSummary.model_validate_json(content)
    except ValidationError as exc:
        raise SummarizationError("A IA devolveu um resumo em formato inválido.") from exc
