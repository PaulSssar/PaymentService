from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import validate_api_key
from app.db.session import get_session
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_payment(
    body: PaymentCreate,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    _api_key: bool = Depends(validate_api_key),
    session: AsyncSession = Depends(get_session),
):
    """
    Создаёт новый платёж.
    Требует X-API-Key в заголовке и Idempotency-Key для идемпотентности.
    """
    service = PaymentService(session)
    try:
        payment = await service.create_payment(body, idempotency_key)
    except IntegrityError:
        await session.rollback()
        existing = await service.payment_repo.get_by_idempotency_key(idempotency_key)
        if existing:
            return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key conflict",
        )
    return payment


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    _api_key: bool = Depends(validate_api_key),
    session: AsyncSession = Depends(get_session),
):
    """Возвращает платёж по ID."""
    service = PaymentService(session)
    payment = await service.payment_repo.get_by_id(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment
