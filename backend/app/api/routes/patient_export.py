"""
Exportação de todos os dados de um paciente, em JSON.

Atende aos direitos de acesso e portabilidade da LGPD (art. 18): o psicólogo,
que é o controlador dos dados, consegue entregar ao paciente (ou levar para
outro sistema) tudo o que o MindCare guarda sobre ele:

- cadastro e consentimento para IA;
- consultas;
- lançamentos financeiros ligados ao paciente;
- registros de sessão, já descriptografados (transcrição e resumo).

O arquivo contém dados sensíveis de saúde: o aviso no próprio arquivo lembra
disso. Cada exportação fica na trilha de auditoria.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import get_current_user
from app.api.routes.agenda import _response as appointment_response
from app.api.routes.notes import _detail as note_detail
from app.api.routes.notes import _owned_patient
from app.database.database import get_db
from app.database.models import Appointment, ClinicalNote, User
from app.schemas import PatientExport, PatientExportProfile
from app.timeutils import now_utc

router = APIRouter(prefix="/patients", tags=["Pacientes"], dependencies=[Depends(get_current_user)])

NOTICE = (
    "Este arquivo contém dados pessoais sensíveis de saúde, protegidos por sigilo "
    "profissional e pela LGPD. Guarde-o em local seguro e compartilhe apenas com o "
    "próprio paciente ou com quem tiver autorização legal."
)


@router.get("/{patient_id}/export", response_model=PatientExport)
def export_patient(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = _owned_patient(db, request, current_user, patient_id)

    appointments = (
        db.query(Appointment)
        .filter(Appointment.user_id == current_user.id, Appointment.patient_id == patient.id)
        .order_by(Appointment.starts_at)
        .all()
    )
    notes = (
        db.query(ClinicalNote)
        .filter(ClinicalNote.user_id == current_user.id, ClinicalNote.patient_id == patient.id)
        .order_by(ClinicalNote.created_at)
        .all()
    )

    export = PatientExport(
        exported_at=now_utc(),
        exported_by=current_user.full_name,
        notice=NOTICE,
        patient=PatientExportProfile.model_validate(patient),
        appointments=[appointment_response(db, a) for a in appointments],
        clinical_notes=[note_detail(n) for n in notes],
    )

    audit.record(
        db, request, audit.PATIENT_EXPORT, user_id=current_user.id,
        resource_type=audit.RESOURCE_PATIENT, resource_id=patient.id,
        details={"appointments": len(appointments), "notes": len(notes)},
    )
    return export
