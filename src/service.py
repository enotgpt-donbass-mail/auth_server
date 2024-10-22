import asyncio
import os
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select, update, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from orm import db_manager
from src.models import User, VerificationCode, UserRoles, Role, RefreshToken, QRAuthTokens
from src.schemas import UserCreatePhoneRequest, UserCreateResponse, UserCreateEmailRequest, RegistrationPhoneConfirm, \
    RegistrationResponse, SuccessResponse, AuthGetOutput, AuthOutput, ChangeToken, ChangeTokenOutput, UserOutput, \
    GetQROutput
from src.utils import create_refresh_token, create_access_token, QRCodeGenerator

VERIFICATION_TYPES = {
    "registration_phone": "registration_phone",
    "registration_email": "registration_email",
    "auth_phone": "auth_phone",
    "auth_email": "auth_email"
}


async def create_user(data, db: AsyncSession):
    """
    Пытается добавить юзера, отдает 403, если что-то повторяется(email, phone)
    :param data:
    :param db:
    :return: User
    """
    user = User(**data.model_dump())
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    except IntegrityError:
        raise HTTPException(403, "Пользователь уже зарегистрирован. Подтвердите регистрацию либо воспользуйтесь методом авторизации")


def code_generator():
    return 11111
    # return random.randint(101010, 909090)


async def generate_security_code(db: AsyncSession, user_id: int, verification_type: str):
    """
    Создает код на 5 минут
    :param db:
    :param user_id:
    :param verification_type:
    :param expires_at:
    :return:
    """
    expires_at: datetime = datetime.utcnow() + timedelta(minutes=5)
    verification = VerificationCode(user_id=user_id, verification_type=verification_type, expires_at=expires_at,
                                    code=code_generator())
    try:
        db.add(verification)
        await db.commit()
        await db.refresh(verification)
        return verification
    except Exception as e:
        raise HTTPException(403, e.__str__())


async def user_exists_and_active(db: AsyncSession, data):
    """
    Возвращает True если User существует и подтвердил регистрацию
    :param db:
    :param data:
    :return:
    """
    if hasattr(data, 'phone_number'):
        user = await db.execute(select(User).where(User.phone_number == data.phone_number,
                                                   User.is_active==True))
    elif hasattr(data, 'email'):
        user = await db.execute(select(User).where(User.email == data.email,
                                                   User.is_active == True))
    else:
        raise HTTPException(400, "E-mail или phone_number не переданы")

    user = user.fetchone()
    if user:
        return True
    return False


async def register_user(data, db, verification_type):
    if await user_exists_and_active(db, data):
        raise HTTPException(401, "Пользователь зарегистрирован. Воспользуйтесь методами авторизации.")
    user = await create_user(data, db)
    user_id = user.id
    verification = await generate_security_code(db, user_id, verification_type)
    response = UserCreateResponse(code_id=verification.id).model_dump(mode='json')
    return JSONResponse(response)


async def registration_by_phone(data: UserCreatePhoneRequest, db: AsyncSession):
    """Регистрирует пользователя по номеру телефона"""
    return await register_user(data, db, VERIFICATION_TYPES['registration_phone'])


async def registration_by_email(data: UserCreateEmailRequest, db: AsyncSession):
    """Регистрирует пользователя по e-mail"""
    return await register_user(data, db, VERIFICATION_TYPES['registration_email'])


async def get_user_by_phone(phone_number: str, db: AsyncSession):
    user = await db.execute(select(User).where(User.phone_number == phone_number).order_by(User.created_at.desc()).limit(1))
    user = user.fetchone()
    if not user:
        raise HTTPException(404, "Пользователь не зарегистрирован")
    return user[0]


async def get_user_by_email(email: str, db: AsyncSession):
    user = await db.execute(select(User).where(User.email == email).order_by(User.created_at.desc()).limit(1))
    user = user.fetchone()
    if not user:
        raise HTTPException(404, "Пользователь не зарегистрирован")
    return user[0]


async def get_user_by_id(id: int, db: AsyncSession):
    user = await db.execute(select(User).where(User.id == id).limit(1))
    user = user.fetchone()
    if not user:
        raise HTTPException(404, "Пользователь не зарегистрирован")
    return user[0]


async def get_verification_data(db: AsyncSession, data):
    if hasattr(data, 'phone_number'):
        user = await get_user_by_phone(data.phone_number, db)
    elif hasattr(data, 'email'):
        user = await get_user_by_email(data.email, db)
    else:
        raise HTTPException(400, "Не переданы email или phone_number")

    user_id = user.id
    verification = await db.execute(select(VerificationCode).where(VerificationCode.id == data.code_id,
                                                                   user_id == VerificationCode.user_id,
                                                                   or_(
                                                                       VerificationCode.verification_type ==
                                                                       VERIFICATION_TYPES['registration_phone'],
                                                                       VerificationCode.verification_type ==
                                                                       VERIFICATION_TYPES['registration_email']
                                                                   ),
                                                                   VerificationCode.is_active==True).limit(1))
    verification = verification.fetchone()
    if not verification:
        raise HTTPException(404, "Код подтверждения не верен либо не найден")
    return verification[0]


async def registration_confirm(data, db: AsyncSession):
    verification = await get_verification_data(db, data)
    verification_id = verification.id
    user_id = verification.user_id
    if verification.expires_at < datetime.utcnow():
        raise HTTPException(401, "Срок кода подтверждения истёк. Запросите новый")

    if verification.code != data.code:
        raise HTTPException(401, "Код подтверждения неверный")

    verification_update = await db.execute(update(VerificationCode)
                                           .where(VerificationCode.id == verification_id)
                                           .values(is_active=False))
    user_active_update = await db.execute(update(User).where(User.id == user_id).values(is_active=True))
    refresh_token = await create_refresh_token(db, user_id)
    data = {
        "id": user_id,
        "roles": ["user"]
    }
    access_token = create_access_token(data)
    response = RegistrationResponse(refresh_token=refresh_token, access_token=access_token).model_dump(mode="json")
    role = UserRoles(user_id=user_id, role_id=1)
    db.add(role)
    await db.commit()
    return response



async def auth_set_code(db: AsyncSession, user_id: int, auth_param: str):
    """
    Запросить код
    :param db:
    :param data:
    :return:
    """
    verification_code = await generate_security_code(db, user_id, VERIFICATION_TYPES[auth_param])
    return AuthGetOutput(code_id=verification_code.id).model_dump(mode='json')



async def auth_get_code(db: AsyncSession, data):
    if hasattr(data, 'phone_number'):
        user = await get_user_by_phone(data.phone_number, db)
        auth_param = "auth_phone"
    elif hasattr(data, 'email'):
        user = await get_user_by_email(data.email, db)
        auth_param = "auth_phone"
    else:
        raise HTTPException(403, "Неверный тип данных передан")
    user_id = user.id
    if not user.is_active:
        raise HTTPException(401, "Пользователь не зарегистрирован. Пройдите регистрацию. Пожалуйста.")
    return await auth_set_code(db, user_id, auth_param)


async def get_verification_auth_data(db: AsyncSession, data):
    if hasattr(data, 'phone_number'):
        user = await get_user_by_phone(data.phone_number, db)
    elif hasattr(data, 'email'):
        user = await get_user_by_email(data.email, db)
    else:
        raise HTTPException(400, "Не переданы email или phone_number")

    user_id = user.id
    verification = await db.execute(select(VerificationCode).where(VerificationCode.id == data.code_id,
                                                                   user_id == VerificationCode.user_id,
                                                                   or_(
                                                                       VerificationCode.verification_type ==
                                                                       VERIFICATION_TYPES['auth_phone'],
                                                                       VerificationCode.verification_type ==
                                                                       VERIFICATION_TYPES['auth_email']
                                                                   ),
                                                                   VerificationCode.is_active==True).limit(1))
    verification = verification.fetchone()
    if not verification:
        raise HTTPException(404, "Код подтверждения не верен либо не найден")
    return verification[0]


async def get_user_roles(db: AsyncSession, user_id: int) -> list:
    user_roles_query = select(UserRoles.role_id).where(UserRoles.user_id == user_id)
    user_roles_result = await db.execute(user_roles_query)
    unique_role_ids = {role_id[0] for role_id in user_roles_result.fetchall()}

    if unique_role_ids:
        roles_query = select(Role.name).where(Role.id.in_(unique_role_ids))
        roles_result = await db.execute(roles_query)

        unique_roles = {role[0] for role in roles_result.fetchall()}

        return list(unique_roles)

    return []


async def auth_confirm(db: AsyncSession, data):
    verification = await get_verification_auth_data(db, data)
    verification_id = verification.id
    user_id = verification.user_id
    user_roles = await get_user_roles(db, user_id)
    if verification.expires_at < datetime.utcnow():
        raise HTTPException(401, "Срок кода подтверждения истёк. Запросите новый")

    if verification.code != data.code:
        raise HTTPException(401, "Код подтверждения неверный")

    verification_update = await db.execute(update(VerificationCode)
                                           .where(VerificationCode.id == verification_id)
                                           .values(is_active=False))
    #user_active_update = await db.execute(update(User).where(User.id == user_id).values(is_active=True))
    refresh_token = await create_refresh_token(db, user_id)
    data = {
        "id": user_id,
        "roles": user_roles
    }
    access_token = create_access_token(data)
    response = AuthOutput(refresh_token=refresh_token, access_token=access_token).model_dump(mode="json")
    await db.commit()
    return response


async def change_token(db: AsyncSession, data: ChangeToken):
    token = await db.execute(select(RefreshToken).where(RefreshToken.token == data.refresh_token).limit(1))
    token = token.fetchone()
    if not token:
        raise HTTPException(401, "Токен не найден")
    token = token[0]
    user_id = token.user_id
    if token.expires_at < datetime.utcnow():
        raise HTTPException(401, "Refresh token истёк. Получите новый")

    user_roles = await get_user_roles(db, user_id)
    data = {
        "id": user_id,
        "roles": user_roles
    }
    access_token = create_access_token(data)
    return JSONResponse(ChangeTokenOutput(access_token=access_token).model_dump(mode='json'))


async def auth_telegram_get_code(db: AsyncSession, data):
    if data.password != os.getenv("KOSTYA"):
        raise HTTPException(401, "Key is not valid")
    if hasattr(data, 'phone_number'):
        auth_param = "auth_phone"
        user = await get_user_by_phone(data.phone_number, db)
    elif hasattr(data, 'email'):
        auth_param = "auth_email"
        user = await get_user_by_email(data.email, db)
    else:
        raise HTTPException(400, "Не переданы email или phone_number")

    user_id = user.id
    if not user.is_active:
        raise HTTPException(401, "Пользователь не зарегистрирован. Пройдите регистрацию. Пожалуйста.")
    return await auth_set_code(db, user_id, auth_param)


async def auth_telegram_confirm(db: AsyncSession, data):
    if data.password != os.getenv("KOSTYA"):
        raise HTTPException(401, "Key is not valid")

    verification = await get_verification_auth_data(db, data)
    verification_id = verification.id
    user_id = verification.user_id
    user_roles = await get_user_roles(db, user_id)
    if verification.expires_at < datetime.utcnow():
        raise HTTPException(401, "Срок кода подтверждения истёк. Запросите новый")

    if verification.code != data.code:
        raise HTTPException(401, "Код подтверждения неверный")

    verification_update = await db.execute(update(VerificationCode)
                                           .where(VerificationCode.id == verification_id)
                                           .values(is_active=False))
    #refresh_token = await create_refresh_token(db, user_id)
    data = {
        "id": user_id,
        "roles": user_roles
    }
    access_token = create_access_token(data, timedelta(days=365*30))
    response = AuthOutput(refresh_token="", access_token=access_token).model_dump(mode="json")
    await db.commit()
    return response


async def users_me(db: AsyncSession, user_id: int):
    user = await db.execute(select(User).where(User.id == user_id).limit(1))
    user = user.scalar_one()
    return JSONResponse(content=UserOutput.model_validate(user).model_dump(mode='json'))


async def get_qr_code_info(db: AsyncSession):
    token = QRCodeGenerator().hash
    url = os.getenv("AUTH_SERVER") + "qr_code/auth/" + token
    qr_auth = QRAuthTokens(expires_at=datetime.utcnow() + timedelta(minutes=5), url=url, token=token)
    db.add(qr_auth)
    await db.commit()
    return JSONResponse(content=GetQROutput.model_validate(qr_auth).model_dump(mode='json'))


async def qr_code_auth(db: AsyncSession, user_id: int, hashed: str):
    verify_qr_token = await db.execute(select(QRAuthTokens).where(QRAuthTokens.token == hashed).limit(1))
    if not verify_qr_token:
        raise HTTPException(401, "Ошибка")
    verify_qr_token = verify_qr_token.scalar_one()

    if verify_qr_token.expires_at < datetime.utcnow():
        raise HTTPException(401, "Время сессии истекло.")

    verify_qr_token.user_id = user_id
    await db.commit()
    await db.refresh(verify_qr_token)
    return JSONResponse(content=SuccessResponse().model_dump(mode='json'))


async def qr_longpoll(db: AsyncSession, hashed: str):
    verify_qr_token = await db.execute(select(QRAuthTokens).where(QRAuthTokens.token == hashed).limit(1))
    qr = verify_qr_token.scalar_one_or_none()

    if qr is None:
        raise HTTPException(401, "Ошибка: QR код не найден")

    if qr.user_id is not None:
        raise HTTPException(401, "Странная ошибка")
    start_time = datetime.utcnow()
    expiration_time = start_time + timedelta(minutes=5)
    while True:
        async with db_manager.connect() as new_connection:
            await asyncio.sleep(1)
            qr_code = await new_connection.execute(select(QRAuthTokens).where(QRAuthTokens.token == hashed).limit(1))
            qr_code = qr_code.fetchone()
            if qr_code is None:
                raise HTTPException(401, "Ошибка: QR код не найден")

            if qr_code.user_id is not None:
                user_id = qr_code.user_id
                user_roles = await get_user_roles(db, user_id)
                refresh_token = await create_refresh_token(db, user_id)
                data = {
                    "id": user_id,
                    "roles": user_roles
                }
                access_token = create_access_token(data)
                response = AuthOutput(refresh_token=refresh_token, access_token=access_token).model_dump(mode="json")
                qr_token = await db.execute(select(QRAuthTokens).where(QRAuthTokens.token == hashed).limit(1))
                qr = qr_token.scalar_one_or_none()
                qr.expires_at = datetime.utcnow()
                await db.commit()
                return response
        if datetime.utcnow() >= expiration_time:
            raise HTTPException(408, "Ошибка: Время ожидания истекло")



