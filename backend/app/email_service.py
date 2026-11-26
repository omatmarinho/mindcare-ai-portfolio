"""
Envio de e-mails.

O provedor é escolhido pela variável EMAIL_BACKEND no .env:

- "console" (padrão): NÃO envia nada; imprime o e-mail no terminal do
  uvicorn. Para desenvolvimento. NUNCA use em produção: os links
  apareceriam nos logs do servidor.
- "resend": envia de verdade pela API do Resend (https://resend.com).
  Exige RESEND_API_KEY e EMAIL_FROM (remetente de um domínio verificado
  no Resend).
- "memory": guarda os e-mails na lista OUTBOX. Usado pelos testes.

Regra de privacidade: e-mails levam apenas links e textos genéricos,
nunca dados de pacientes ou registros clínicos.
"""
import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger("psinara.email")

RESEND_API_URL = "https://api.resend.com/emails"


@dataclass
class EmailMessage:
    to: str
    subject: str
    text: str
    reply_to: str | None = None


# Caixa de saída usada pelos testes (EMAIL_BACKEND=memory)
OUTBOX: list[EmailMessage] = []


def frontend_url() -> str:
    """Endereço do frontend, usado para montar os links dos e-mails."""
    return os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")


def send_email(to: str, subject: str, text: str, reply_to: str | None = None,
               raise_errors: bool = False) -> None:
    """
    Envia um e-mail. Por padrão nunca lança exceção: é chamado em segundo
    plano, depois que a resposta já foi enviada, então só registra o erro no
    log. Rotinas que precisam saber se deu certo usam raise_errors=True.
    """
    backend = os.getenv("EMAIL_BACKEND", "console").lower()
    message = EmailMessage(to=to, subject=subject, text=text, reply_to=reply_to)

    try:
        if backend == "memory":
            OUTBOX.append(message)
        elif backend == "resend":
            _send_with_resend(message)
        else:
            _print_to_console(message)
    except Exception:
        logger.exception("Falha ao enviar e-mail (assunto: %s)", subject)
        if raise_errors:
            raise


def _print_to_console(message: EmailMessage) -> None:
    print(
        "\n" + "=" * 70
        + "\n[E-MAIL DE DESENVOLVIMENTO - NÃO FOI ENVIADO]"
        + f"\nPara: {message.to}\nResponder a: {message.reply_to or '-'}"
        + f"\nAssunto: {message.subject}\n\n{message.text}\n"
        + "=" * 70 + "\n",
        flush=True,
    )


def _send_with_resend(message: EmailMessage) -> None:
    api_key = os.getenv("RESEND_API_KEY")
    sender = os.getenv("EMAIL_FROM")
    if not api_key or not sender:
        raise RuntimeError("RESEND_API_KEY e EMAIL_FROM precisam estar no .env")

    response = httpx.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": sender,
            "to": [message.to],
            "subject": message.subject,
            "text": message.text,
            **({"reply_to": [message.reply_to]} if message.reply_to else {}),
        },
        timeout=10,
    )
    if response.is_error:
        # O Resend explica o motivo no corpo (ex.: domínio não verificado).
        # Registramos só o status e essa explicação: nunca a chave nem o texto do e-mail.
        try:
            reason = response.json().get("message", "")
        except ValueError:
            reason = response.text[:200]
        raise RuntimeError(f"Resend recusou o envio (HTTP {response.status_code}): {reason}")


# ---------------------------------------------------------------------
# Modelos dos e-mails
# ---------------------------------------------------------------------

def send_password_reset_email(to: str, token: str, valid_minutes: int) -> None:
    link = f"{frontend_url()}/redefinir-senha?token={token}"
    send_email(
        to=to,
        subject="Psinara - Redefinição de senha",
        text=(
            "Recebemos um pedido para redefinir a senha da sua conta no Psinara.\n\n"
            f"Para criar uma nova senha, acesse o link abaixo (válido por {valid_minutes} minutos):\n"
            f"{link}\n\n"
            "Se você não fez esse pedido, ignore este e-mail. Sua senha continua a mesma."
        ),
    )


def send_account_exists_email(to: str) -> None:
    """Enviado quando alguém tenta cadastrar um e-mail que já tem conta."""
    send_email(
        to=to,
        subject="Psinara - Tentativa de cadastro com seu e-mail",
        text=(
            "Alguém tentou criar uma conta no Psinara usando este e-mail, "
            "mas você já possui uma conta.\n\n"
            f"Se foi você, basta entrar: {frontend_url()}/login\n"
            f"Esqueceu a senha? Redefina aqui: {frontend_url()}/esqueci-senha\n\n"
            "Se não foi você, pode ignorar este e-mail. Nenhuma alteração foi feita na sua conta."
        ),
    )


def send_email_verification_email(to: str, token: str, valid_hours: int) -> None:
    link = f"{frontend_url()}/verificar-email?token={token}"
    send_email(
        to=to,
        subject="Psinara - Confirme seu e-mail",
        text=(
            "Bem-vindo(a) ao Psinara!\n\n"
            f"Para confirmar seu e-mail, acesse o link abaixo (válido por {valid_hours} horas):\n"
            f"{link}\n\n"
            "Se você não criou esta conta, ignore este e-mail."
        ),
    )
