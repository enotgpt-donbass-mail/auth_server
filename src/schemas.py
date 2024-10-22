from datetime import date, datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, EmailStr, validator, field_validator, ConfigDict


class UserCreate(BaseModel):
    """Базовые данные о пользователе"""
    first_name: str = Field(..., example="Иван")
    last_name: str = Field(..., example="Сыгинь")
    middle_name: Optional[str] = Field(None, example="Ярославович")
    birth_date: Optional[date] = Field(None, example="1990-01-01")
    gender: Optional[int] = Field(..., example=1)


class UserCreatePhoneRequest(UserCreate):
    """Запрос на создание пользователя по номеру телефона"""
    phone_number: str = Field(..., example="79493686568")

    @field_validator('phone_number')
    def phone_number_must_be_valid(cls, v):
        if v and not v.isdigit():
            raise ValueError('Phone number must be digits only')
        return v


class UserCreateEmailRequest(UserCreate):
    """Запрос на создание пользователя по почте"""
    email: EmailStr = Field(..., example="a2004@webcam.com")


class SuccessResponse(BaseModel):
    status: bool = True
    model_config = ConfigDict(from_attributes=True)


class UserCreateResponse(SuccessResponse):
    """Ответ на запрос о регистрации"""
    code_id: int


class Confirm(BaseModel):
    code_id: int
    code: int


class RegistrationPhoneConfirm(Confirm):
    """Подтверждение регистрации по Phone"""
    phone_number: str = Field(..., example="79493686568")

    @field_validator('phone_number')
    def phone_number_must_be_valid(cls, v):
        if v and not v.isdigit():
            raise ValueError('Phone number must be digits only')
        return v


class RegistrationEmailConfirm(Confirm):
    """Подтверждение регистрации по email"""
    email: EmailStr = Field(..., example="a2004@webcam.com")


class RegistrationResponse(SuccessResponse):
    access_token: str
    refresh_token: str


class AuthGetCodeByPhone(BaseModel):
    phone_number: str = Field(..., example="79493686568")

    @field_validator('phone_number')
    def phone_number_must_be_valid(cls, v):
        if v and not v.isdigit():
            raise ValueError('Phone number must be digits only')
        return v


class AuthGetCodeByEmail(BaseModel):
    email: EmailStr = Field(..., example="a2004@webcam.com")


class AuthTelegram(BaseModel):
    password: str


class AuthGetCodeByPhoneTelegram(AuthGetCodeByPhone, AuthTelegram):
    pass

class AuthGetCodeByEmailTelegram(AuthGetCodeByEmail, AuthTelegram):
    pass


class AuthGetOutput(SuccessResponse):
    code_id: int = Field(..., example=1)


class AuthConfirm(BaseModel):
    code_id: int = Field(..., example=1)
    code: int = Field(..., example=11111)


class AuthConfirmPhone(AuthConfirm):
    phone_number: str = Field(..., example="79493686568")


class AuthConfirmEmail(AuthConfirm):
    email: EmailStr = Field(..., example="a2004@webcam.com")


class AuthConfirmPhoneTelegram(AuthConfirmPhone, AuthTelegram):
    pass

class AuthConfirmEmailTelegram(AuthConfirmEmail, AuthTelegram):
    pass


class AuthOutput(SuccessResponse):
    access_token: str
    refresh_token: str


class ChangeToken(BaseModel):
    refresh_token: str


class ChangeTokenOutput(SuccessResponse):
    access_token: str


class UserOutput(SuccessResponse):
    id: int
    first_name: str
    last_name: str
    middle_name: str
    gender: int
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: datetime


    class Config:
        orm_mode = True


class GetQROutput(SuccessResponse):
    token: str
    url: str

# class UserCreateRequest(BaseModel):
#     name: str = Field(max_length=30)
#     fullname: str
#
#
# class UserResponse(BaseModel):
#     id: int
#     name: str
#     fullname: str
#
#     model_config = ConfigDict(from_attributes=True)
#     # .model_dump(mode='json')
#
#
# class APIUserResponse(BaseModel):
#     status: Literal['ok'] = 'ok'
#     data: UserResponse
#
#
# class APIUserListResponse(BaseModel):
#     status: Literal['ok'] = 'ok'
#     data: list[UserResponse]
