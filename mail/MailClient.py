import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from http.client import HTTPException


#from src.utils.exceptions import FileNotFound


class BaseSMTPClient:
    """
    Для Gmail:
    1. В настройках аккаунта добавить двухфакторную аутентификацию
    2. Создать приложение, назвать его как угоодно. https://myaccount.google.com/apppasswords?utm_source=google-account&utm_medium=web
    3. Получить пароль от gmail
    4. Вставить этот пароль в .env
    """
    def __init__(self):
        self.server = None

    def connect(self, host: str, port: int) -> None:
        raise NotImplementedError("Not implemented this")

    def login(self, username, password):
        self.server.login(username, password)

    def send_email(self, from_addr: str, to_address: list, subject: str, body: str,
                   content_type: str = 'plain', attachments: list = None):
        """
            Отправляет сообщение

            :param from_addr: str - Адрес отправителя
            :param to_address: list - Список адресов получателей
            :param subject: str - Тема письма
            :param body: str - Текст письма (в формате plain text / html)
            :param content_type: str - Тип содержимого ('plain' для текстового письма, 'html' для HTML-содержимого)
            :param attachments: list - Список абсолютных путей к файлам, которые нужно прикрепить к письму

            :raises FileNotFoundError: Если любой из файлов в списке attachments не найден
            """
        msg = MIMEMultipart()
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_address)
        msg['Subject'] = subject

        msg.attach(MIMEText(body, content_type))

        if attachments:
            for file_path in attachments:
                if os.path.isfile(file_path):
                    with open(file_path, 'rb') as file:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
                        msg.attach(part)
                else:
                    raise HTTPException(404, f"File {file_path} does not exist")

        self.server.sendmail(from_addr, to_address, msg.as_string())

    def disconnect(self):
        self.server.quit()


class SMTPSSLClient(BaseSMTPClient):
    def connect(self, host: str = 'smtp.gmail.com', port: int = 465) -> None:
        self.server = smtplib.SMTP_SSL(host, port)
        self.server.ehlo()


class SMTPTLSClient(BaseSMTPClient):
    def connect(self, host: str = 'smtp.gmail.com', port: int = 587) -> None:
        self.server = smtplib.SMTP(host, port)
        self.server.starttls()
        self.server.ehlo()

