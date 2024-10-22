import asyncio
import os
import uuid
from datetime import timedelta, datetime

import requests_async
from PIL import Image

from dotenv import load_dotenv
from fastapi import HTTPException
from jose import jwt

from sqlalchemy.ext.asyncio import AsyncSession



from qrcode_styled import QRCodeStyled, ERROR_CORRECT_Q

from src.models import RefreshToken

load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


load_dotenv()


def create_access_token(data: dict, expires_delta: timedelta = None):
    """
    Создает access токен
    :param data:
    :param expires_delta:
    :return:
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def create_refresh_token(db: AsyncSession, user_id: int):
    """
    Создает refresh токен
    :param db:
    :param user_id:
    :return:
    """
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    token = str(uuid.uuid4())
    refresh_token = RefreshToken(user_id=user_id, token=token, expires_at=expire)
    db.add(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)
    return token


async def verify_jwt_token(token):
    """
    Проверяет токен, возвращает данные из него
    :param token:
    :return:
    """
    token = token.credentials
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        expiration_time = decoded_token.get("exp")
        if expiration_time:
            current_time = datetime.utcnow()
            if current_time < datetime.fromtimestamp(expiration_time):
                return decoded_token
    except jwt.ExpiredSignatureError:
        raise HTTPException(401,"Срок действия токена истёк. Обрaтитесь за новым токеном")
    except jwt.JWTError:
        raise HTTPException(401, "Неверный токен")
    raise HTTPException(401, "Токен недействителен")


class QRCodeGenerator:
    def __init__(self):
        self.output_filename = None
        self.hash = self._generate_long_hash(128)

    def _generate_long_hash(self, length=128):
        hash_string = ''.join(str(uuid.uuid4()).replace('-', '') for _ in range((length // 32) + 1))
        self.hash = hash_string
        return self.hash[:length]

    async def generate_styled_qr(self, output_filename=None, image_path=None, lossless=True, quality=100, method=4, fill_color=None, background_color='black'):
        qr = QRCodeStyled(border=2)
        qr.error_correction = ERROR_CORRECT_Q
        image = None
        if image_path:
            image = Image.open(image_path)

        img = qr.get_image(self.hash, image=image)

        img.fill_color = fill_color
        img.back_color = background_color

        self.output_filename = f'qr_{uuid.uuid4()}.png'
        os.makedirs(os.getenv("QRCODES_PATH"), exist_ok=True)
        with open(os.path.join(os.getenv("QRCODES_PATH"), self.output_filename), 'wb') as stream:
            img.save(stream, 'PNG', lossless=lossless, quality=quality)

        result = await self.upload_photo()
        return result



    async def upload_photo(self):
        token = os.getenv("ADMIN")
        url = 'http://s33.enotgpt.ru/upload/photo'
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {token}',
        }

        file_name = self.output_filename
        path = os.path.join(os.getenv("QRCODES_PATH"), file_name)
        with open(path, 'rb') as file:
            files = {'file': (file_name, file, 'image/png')}
            response = await requests_async.post(url, headers=headers, files=files)

        print(response.json())
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(403, "Error create qr code: " + response.text)


