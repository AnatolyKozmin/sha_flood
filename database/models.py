from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Chat(Base):
    """Модель для хранения информации о чатах"""
    __tablename__ = 'chats'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    chat_type = Column(String(20), nullable=False)  # 'participants' или 'organizers'
    chat_title = Column(String(255))
    added_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Chat(chat_id={self.chat_id}, type={self.chat_type})>"


class User(Base):
    """Модель для хранения информации об организаторах"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    
    # Обязательные поля
    full_name = Column(String(255), nullable=False, index=True)  # ФИО
    department = Column(String(255), nullable=False)  # Подразделение
    
    # Необязательные поля
    telegram_username = Column(String(255), nullable=True)  # Телеграмм юзернейм
    telegram_id = Column(BigInteger, nullable=True, index=True)  # ID пользователя в Telegram
    birth_date = Column(String(10), nullable=True)  # Дата рождения (18.06.2004)
    faculty = Column(String(255), nullable=True)  # Факультет
    course = Column(Integer, nullable=True)  # Курс обучения
    study_group = Column(String(50), nullable=True)  # Учебная группа (ШАЦ25-1)
    phone_number = Column(String(20), nullable=True)  # Номер телефона (8 (999) 123-45-67)
    has_car = Column(String(255), nullable=True)  # Есть ли водительские права и машина
    nearest_metro = Column(Text, nullable=True)  # Ближайшие станции метро
    address = Column(Text, nullable=True)  # Адрес проживания (для технической поддержки)
    
    # Служебные поля
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<User(full_name={self.full_name}, department={self.department})>"


class Quote(Base):
    """Цитаты из переписки"""
    __tablename__ = 'quotes'

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    author_user_id = Column(BigInteger, index=True, nullable=False)  # чей текст процитировали
    author_name = Column(String(255), nullable=True)  # сохраняем name на момент цитирования
    quoter_user_id = Column(BigInteger, index=True, nullable=False)  # кто процитировал
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class BeerStat(Base):
    """Статистика налитого пива по пользователям в рамках чата"""
    __tablename__ = 'beer_stats'

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    user_id = Column(BigInteger, index=True, nullable=False)
    username = Column(String(255), nullable=True)  # последняя известная метка
    count = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Wakeup(Base):
    """Запланированные побудки"""
    __tablename__ = 'wakeups'

    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, index=True, nullable=False)
    user_id = Column(BigInteger, index=True, nullable=False)
    wake_at = Column(DateTime, index=True, nullable=False)
    done = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
