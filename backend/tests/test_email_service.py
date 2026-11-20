"""Envio pelo Resend: falhas viram log com o motivo, sem vazar a chave."""
import logging

import httpx

from app import email_service


def _fake_post(status, body):
    def fake(url, headers, json, timeout):
        return httpx.Response(status, json=body, request=httpx.Request("POST", url))
    return fake


def test_resend_rejection_is_logged_with_reason(monkeypatch, caplog):
    monkeypatch.setenv("EMAIL_BACKEND", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "re_chave_ficticia_123")
    monkeypatch.setenv("EMAIL_FROM", "MindCare AI <nao-responda@exemplo.com>")
    monkeypatch.setattr(email_service.httpx, "post",
                        _fake_post(403, {"message": "The domain is not verified"}))

    with caplog.at_level(logging.ERROR, logger="mindcare.email"):
        email_service.send_email("pessoa@exemplo.com", "Assunto", "Texto")  # não lança exceção

    log = caplog.text
    assert "HTTP 403" in log and "The domain is not verified" in log
    assert "re_chave_ficticia_123" not in log


def test_resend_success_does_not_log_error(monkeypatch, caplog):
    monkeypatch.setenv("EMAIL_BACKEND", "resend")
    monkeypatch.setenv("RESEND_API_KEY", "re_chave_ficticia_123")
    monkeypatch.setenv("EMAIL_FROM", "MindCare AI <nao-responda@exemplo.com>")
    monkeypatch.setattr(email_service.httpx, "post", _fake_post(200, {"id": "abc"}))

    with caplog.at_level(logging.ERROR, logger="mindcare.email"):
        email_service.send_email("pessoa@exemplo.com", "Assunto", "Texto")

    assert caplog.text == ""
