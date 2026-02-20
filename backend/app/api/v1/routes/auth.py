import uuid
from datetime import date
from secrets import token_urlsafe
from typing import Dict, Literal

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.v1.routes.deps import get_db
from app.db.models.owner import Owner
from app.db.models.owner_pet import OwnerPet
from app.db.models.pet import Pet
from app.db.models.user import User

router = APIRouter()

TOKENS: Dict[str, str] = {}
VALID_ROLES = {"ADMIN", "VET", "OWNER"}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


class LoginRequest(BaseModel):
    email: str
    password: str


class PetCreatePayload(BaseModel):
    name: str
    species: str
    breed: str | None = None
    sex: str | None = None
    date_of_birth: date | None = None
    photo_url: str | None = None


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str | None = None
    role: Literal["ADMIN", "VET", "OWNER"] = "OWNER"
    pet: PetCreatePayload | None = None


class UserPayload(BaseModel):
    user_id: str
    email: str
    full_name: str
    phone: str | None = None
    role: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPayload


def _normalize_email(value: str) -> str:
    return value.strip().lower()


def _as_user_payload(user: User) -> UserPayload:
    role = (user.role or "OWNER").upper()
    return UserPayload(
        user_id=str(user.user_id),
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=role,
    )


def _get_token_value(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    return parts[1].strip()


async def _read_image_file(photo: UploadFile | None) -> tuple[bytes | None, str | None]:
    if not photo:
        return None, None

    content_type = (photo.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Photo must be JPEG or PNG")

    data = await photo.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Photo must be 5MB or smaller")

    return data, content_type


@router.post("/register", response_model=UserPayload)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    normalized_email = _normalize_email(payload.email)

    exists = db.execute(select(User.user_id).where(func.lower(User.email) == normalized_email)).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")

    role = payload.role.upper()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")

    if role == "OWNER" and payload.pet is None:
        raise HTTPException(status_code=400, detail="Owner registration requires pet details")

    user = User(
        email=normalized_email,
        password=payload.password,
        role=role,
        full_name=payload.full_name,
        phone=payload.phone,
    )
    db.add(user)
    db.flush()

    if role == "OWNER":
        owner = Owner(user_id=user.user_id, verified_identity_level=0)
        db.add(owner)
        db.flush()

        pet = Pet(
            name=payload.pet.name,
            species=payload.pet.species,
            breed=payload.pet.breed,
            sex=payload.pet.sex,
            date_of_birth=payload.pet.date_of_birth,
            photo_url=payload.pet.photo_url,
        )
        db.add(pet)
        db.flush()

        db.add(
            OwnerPet(
                owner_id=owner.owner_id,
                pet_id=pet.pet_id,
                start_date=date.today(),
                end_date=None,
                relationship_type="primary_owner",
            )
        )

    db.commit()
    db.refresh(user)
    return _as_user_payload(user)


@router.post("/register-owner", response_model=UserPayload)
async def register_owner(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    phone: str | None = Form(default=None),
    pet_name: str = Form(...),
    pet_species: str = Form(...),
    pet_breed: str | None = Form(default=None),
    pet_sex: str | None = Form(default=None),
    pet_date_of_birth: date | None = Form(default=None),
    photo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    normalized_email = _normalize_email(email)

    exists = db.execute(select(User.user_id).where(func.lower(User.email) == normalized_email)).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=normalized_email,
        password=password,
        role="OWNER",
        full_name=full_name,
        phone=phone,
    )
    db.add(user)
    db.flush()

    owner = Owner(user_id=user.user_id, verified_identity_level=0)
    db.add(owner)
    db.flush()

    photo_data, photo_mime_type = await _read_image_file(photo)

    pet = Pet(
        name=pet_name.strip(),
        species=pet_species.strip(),
        breed=pet_breed.strip() if pet_breed and pet_breed.strip() else None,
        sex=pet_sex.strip() if pet_sex and pet_sex.strip() else None,
        date_of_birth=pet_date_of_birth,
        photo_data=photo_data,
        photo_mime_type=photo_mime_type,
        photo_url=None,
    )
    db.add(pet)
    db.flush()

    db.add(
        OwnerPet(
            owner_id=owner.owner_id,
            pet_id=pet.pet_id,
            start_date=date.today(),
            end_date=None,
            relationship_type="primary_owner",
        )
    )

    db.commit()
    db.refresh(user)
    return _as_user_payload(user)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    normalized_email = _normalize_email(payload.email)
    user = db.execute(
        select(User).where(func.lower(User.email) == normalized_email)
    ).scalar_one_or_none()

    if not user or user.password != payload.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = token_urlsafe(32)
    TOKENS[token] = str(user.user_id)

    return LoginResponse(
        access_token=token,
        user=_as_user_payload(user),
    )


@router.get("/me", response_model=UserPayload)
def me(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    token = _get_token_value(authorization)
    user_id = TOKENS.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.execute(select(User).where(User.user_id == uuid.UUID(user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return _as_user_payload(user)
