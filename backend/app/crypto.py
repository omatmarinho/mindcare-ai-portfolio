"""
Criptografia do conteúdo clínico (transcrições e resumos).

O banco já é criptografado em disco pelo Supabase, mas isso não protege
contra quem consegue CONSULTAR o banco (credencial vazada, backup
copiado, erro de permissão). Por isso o conteúdo clínico é criptografado
também pela aplicação, antes de ser gravado: no banco fica só texto
embaralhado, e só a API (que tem a chave) consegue ler.

Algoritmo: Fernet (AES-128-CBC + HMAC-SHA256), da biblioteca
"cryptography": criptografa e garante que o texto não foi adulterado.

ATENÇÃO: se a chave NOTES_ENCRYPTION_KEY for perdida, os registros
criptografados NÃO podem ser recuperados. Guarde uma cópia segura dela
(ex.: gerenciador de senhas) separada dos backups do banco.

Gerar uma chave:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import json
import os

from cryptography.fernet import Fernet, InvalidToken


class EncryptionKeyMissing(RuntimeError):
    pass


def _fernet() -> Fernet:
    key = os.getenv("NOTES_ENCRYPTION_KEY")
    if not key:
        raise EncryptionKeyMissing(
            "NOTES_ENCRYPTION_KEY não está configurada no .env "
            "(necessária para gravar registros clínicos)."
        )
    return Fernet(key.encode())


def encrypt_text(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_text(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Conteúdo criptografado inválido ou chave incorreta.") from exc


def encrypt_json(data: dict) -> str:
    return encrypt_text(json.dumps(data, ensure_ascii=False))


def decrypt_json(token: str) -> dict:
    return json.loads(decrypt_text(token))
