from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.responses import JSONResponse

import orm
from src import service
from src.models import User
from src.schemas import (  # APIUserResponse, UserResponse, APIUserListResponse, UserCreateRequest,
    UserCreatePhoneRequest, UserCreateEmailRequest, RegistrationPhoneConfirm,
    RegistrationEmailConfirm, AuthGetCodeByPhone, AuthGetCodeByEmail, AuthGetOutput, UserCreateResponse,
    RegistrationResponse, AuthConfirmPhone, AuthConfirmEmail, ChangeToken, ChangeTokenOutput, AuthOutput,
    AuthGetCodeByPhoneTelegram, AuthGetCodeByEmailTelegram, AuthConfirmPhoneTelegram, AuthConfirmEmailTelegram,
    GetQROutput)
from src.utils import verify_jwt_token

router = APIRouter()
security = HTTPBearer()

# @router.get("/{user_id}/", response_model=APIUserResponse)
# async def get_user(
#     user_id: int, session: AsyncSession = Depends(orm.get_session)
# ) -> JSONResponse:
#     user = await session.get(User, user_id)
#     if not user:
#         return JSONResponse(
#             content={"status": "error", "message": "User not found"},
#             status_code=status.HTTP_404_NOT_FOUND,
#         )
#     response_model = UserResponse.model_validate(user)
#     return JSONResponse(
#         content={
#             "status": "ok",
#             "data": response_model.model_dump(),
#         }
#     )
#
#
# @router.get("/", response_model=APIUserListResponse)
# async def get_users(session: AsyncSession = Depends(orm.get_session)) -> JSONResponse:
#     users_results = await session.scalars(select(User))
#     response_data = [
#         UserResponse.model_validate(u).model_dump() for u in users_results.all()
#     ]
#     return JSONResponse(
#         content={
#             "status": "ok",
#             "data": response_data,
#         }
#     )
#
#
# @router.post("/", response_model=APIUserResponse, status_code=status.HTTP_201_CREATED)
# async def create_user(
#     user_data: UserCreateRequest, db: AsyncSession = Depends(orm.get_session)
# ) -> JSONResponse:
#     user_candidate = User(**user_data.model_dump())
#     db.add(user_candidate)
#     # I skip error handling
#     await db.commit()
#     await db.refresh(user_candidate)
#     response_model = UserResponse.model_validate(user_candidate)
#     return JSONResponse(
#         content={
#             "status": "ok",
#             "data": response_model.model_dump(),
#         },
#         status_code=status.HTTP_201_CREATED,
#     )

@router.post("/registration_by_phone",
             summary="Регистрация по номеру телефона",
             description="Зарегистрироваться по номеру. Получить id записи кода для подтверждения регистрации",
             response_model=UserCreateResponse,
             tags=['Registration'])
async def registration_by_phone(data: UserCreatePhoneRequest, db=Depends(orm.get_session)):
    return await service.registration_by_phone(data, db)


@router.post("/registration_by_email",
             summary="Регистрация по номеру email",
             description="Зарегистрироваться по email. Получить id записи кода для подтверждения регистрации",
             response_model=UserCreateResponse,
             tags=['Registration'])
async def registration_by_phone(data: UserCreateEmailRequest, db=Depends(orm.get_session)):
    return await service.registration_by_email(data, db)


@router.post("/registration_confirm_phone",
             summary="Подтверждение регистрации телефона",
             description="Отправить код подтверждения для успешной регистрации",
             response_model=RegistrationResponse,
             tags=['Registration'])
async def registration_confirm_phone(data: RegistrationPhoneConfirm, db=Depends(orm.get_session)):
    return await service.registration_confirm(data, db)


@router.post("/registration_confirm_email",
             summary="Подтверждение регистрации email",
             description="Отправить код подтверждения для успешной регистрации",
             response_model=RegistrationResponse,
             tags=['Registration'])
async def registration_confirm_email(data: RegistrationEmailConfirm, db=Depends(orm.get_session)):
    return await service.registration_confirm(data, db)


@router.post("/auth/get_code_by_phone",
             summary="Направить код подтверждения на телефон",
             response_model=AuthGetOutput,
             tags=['Authorization'])
async def auth_get_code_by_phone(data: AuthGetCodeByPhone, db=Depends(orm.get_session)):
    return await service.auth_get_code(db, data)

@router.post("/auth/get_code_by_email",
             summary="Направить код подтверждения на email",
             response_model=AuthGetOutput,
             tags=['Authorization'])
async def auth_get_code_by_email(data: AuthGetCodeByEmail, db=Depends(orm.get_session)):
    return await service.auth_get_code(db, data)


@router.post("/auth/confirm_phone",
             summary="Подтвердить авторизацию по телефону",
             response_model=AuthOutput,
             tags=['Authorization'])
async def auth_confirm_phone(data: AuthConfirmPhone, db=Depends(orm.get_session)):
    return await service.auth_confirm(db, data)


@router.post("/auth/confirm_email",
             summary="Подтвердить авторизацию email",
             response_model=AuthOutput,
             tags=['Authorization'])
async def auth_confirm_email(data: AuthConfirmEmail, db=Depends(orm.get_session)):
    return await service.auth_confirm(db, data)


@router.post("/change_token", summary="Заменить токен", response_model=ChangeTokenOutput, tags=["Token"])
async def change_token(data: ChangeToken, db=Depends(orm.get_session)):
    return await service.change_token(db, data)


@router.post("/auth/telegram/get_code/phone",
             summary="Запросить код для авторизации в Telegram по номеру телефона",
             description="Получишь code_id, его нужно будет ввести вместе с кодом в методе подтверждения. "
                         "Не работает если пользователь не зарегистрирован на сайте",
             tags=["Telegram"],
             response_model=AuthGetOutput)
async def auth_telegram_get_code_phone(data: AuthGetCodeByPhoneTelegram, db=Depends(orm.get_session)):
    return await service.auth_telegram_get_code(db, data)


@router.post("/auth/telegram/get_code/email",
             summary="Запросить код для авторизации в Telegram по E-mail",
             description="Получишь code_id, его нужно будет ввести вместе с кодом в методе подтверждения. "
                         "Не работает, если пользователь не зарегистрирован на сайте",
             tags=["Telegram"],
             response_model=AuthGetOutput)
async def auth_telegram_get_code_email(data: AuthGetCodeByEmailTelegram, db=Depends(orm.get_session)):
    return await service.auth_telegram_get_code(db, data)


@router.post("/auth/telegram/confirm_phone",
             summary="Отправить код подтверждения телефона",
             tags=["Telegram"],
             response_model=AuthOutput)
async def auth_telegram_confirm_phone(data: AuthConfirmPhoneTelegram, db=Depends(orm.get_session)):
    return await service.auth_telegram_confirm(db, data)


@router.post("/auth/telegram/confirm_email",
             summary="Отправить код подтверждения E-mail",
             tags=["Telegram"],
             response_model=AuthOutput)
async def auth_telegram_confirm_email(data: AuthConfirmEmailTelegram, db=Depends(orm.get_session)):
    return await service.auth_telegram_confirm(db, data)


@router.get("/auth/qr",
            summary="Запросить QR-код",
            description="Запрашиваешь QR-код. выводишь его на экран. Отправляешь lp-запрос по вернувшемуся адресу",
            response_model=GetQROutput,
            tags=["QR"])
async def auth_qr_get_code(db=Depends(orm.get_session)):
    return await service.get_qr_code_info(db)


@router.get("/qr_code/auth/{hashed}", summary="Переход по ссылке авторизованным пользователем", tags=["QR"])
async def qr_code_auth(hashed: str,
                       db: AsyncSession = Depends(orm.get_session),
                       token: HTTPAuthorizationCredentials = Depends(security)):
    token = await verify_jwt_token(token)
    return await service.qr_code_auth(db, token['id'], hashed)


@router.get("/qr/longpoll/{hashed}", summary='Лонгпулл QR. Ждем пока пользователь перейдет по ссылке', tags=["QR"])
async def qr_longpoll(hashed: str, db=Depends(orm.get_session)):
    return await service.qr_longpoll(db, hashed)


@router.get("/users/me",
            summary="Получить информацию о себе",
            tags=["Users"])
async def users_me(token: HTTPAuthorizationCredentials = Depends(security), db=Depends(orm.get_session)):
    token = await verify_jwt_token(token)
    return await service.users_me(db, token['id'])






