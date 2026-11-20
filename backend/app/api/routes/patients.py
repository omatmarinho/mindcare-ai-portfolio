from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app import audit
from app.api.deps import get_current_user
from app.database.database import get_db
from app.database import crud
from app.database.models import User
from app.schemas import PatientCreate, PatientResponse

# Todas as rotas deste arquivo exigem login: a dependência get_current_user
# roda antes de cada uma e entrega o psicólogo autenticado.
router = APIRouter(
    dependencies=[Depends(get_current_user)]
)


def _not_found(db: Session, request: Request, user: User, patient_id: int) -> HTTPException:
    """
    Registra a tentativa e devolve o 404. A mesma resposta vale para
    "não existe" e "é de outro psicólogo": ninguém descobre quais ids
    existem em outras contas. Na auditoria, porém, a tentativa fica
    registrada (útil para detectar alguém testando ids em sequência).
    """
    audit.record(
        db, request, audit.PATIENT_ACCESS_DENIED,
        user_id=user.id,
        resource_type=audit.RESOURCE_PATIENT,
        resource_id=patient_id,
        details={"method": request.method},
    )
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Paciente não encontrado"
    )


def _audit_patient(db, request, action, user, patient_id, details=None):
    audit.record(
        db, request, action,
        user_id=user.id,
        resource_type=audit.RESOURCE_PATIENT,
        resource_id=patient_id,
        details=details,
    )


@router.post(
    "/patients",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED
)
def create_patient(
    request: Request,
    patient: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_patient = crud.create_patient(
        db=db,
        owner_id=current_user.id,
        full_name=patient.full_name,
        email=patient.email,
        phone=patient.phone
    )
    _audit_patient(db, request, audit.PATIENT_CREATE, current_user, new_patient.id)
    return new_patient


@router.get("/patients", response_model=list[PatientResponse])
def list_patients(
    request: Request,
    archived: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # /patients              -> pacientes ativos
    # /patients?archived=true -> pacientes arquivados
    patients = crud.get_patients(db, owner_id=current_user.id, archived=archived)

    audit.record(
        db, request, audit.PATIENT_LIST,
        user_id=current_user.id,
        resource_type=audit.RESOURCE_PATIENT,
        details={"archived": archived, "count": len(patients)},
    )
    return patients


@router.get("/patients/{patient_id}", response_model=PatientResponse)
def read_patient(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = crud.get_patient(
        db,
        owner_id=current_user.id,
        patient_id=patient_id
    )

    if patient is None:
        raise _not_found(db, request, current_user, patient_id)

    _audit_patient(db, request, audit.PATIENT_READ, current_user, patient_id)
    return patient


@router.put("/patients/{patient_id}", response_model=PatientResponse)
def update_patient(
    request: Request,
    patient_id: int,
    patient: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    updated_patient = crud.update_patient(
        db=db,
        owner_id=current_user.id,
        patient_id=patient_id,
        full_name=patient.full_name,
        email=patient.email,
        phone=patient.phone
    )

    if updated_patient is None:
        raise _not_found(db, request, current_user, patient_id)

    # Registra QUAIS campos foram enviados, nunca os valores
    _audit_patient(
        db, request, audit.PATIENT_UPDATE, current_user, patient_id,
        details={"fields": sorted(patient.model_fields_set)},
    )
    return updated_patient


# DELETE não apaga: ARQUIVA. Os registros precisam ser guardados
# (Resolução CFP nº 001/2009). Chamar duas vezes não causa erro.
@router.delete("/patients/{patient_id}", response_model=PatientResponse)
def archive_patient(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = crud.archive_patient(
        db=db,
        owner_id=current_user.id,
        patient_id=patient_id
    )

    if patient is None:
        raise _not_found(db, request, current_user, patient_id)

    _audit_patient(db, request, audit.PATIENT_ARCHIVE, current_user, patient_id)
    return patient


@router.post("/patients/{patient_id}/restore", response_model=PatientResponse)
def restore_patient(
    request: Request,
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    patient = crud.restore_patient(
        db=db,
        owner_id=current_user.id,
        patient_id=patient_id
    )

    if patient is None:
        raise _not_found(db, request, current_user, patient_id)

    _audit_patient(db, request, audit.PATIENT_RESTORE, current_user, patient_id)
    return patient
