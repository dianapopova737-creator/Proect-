from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

#  базовый класс для моделей
Base = declarative_base()

# модели
class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    
    # Связь с блюдами
    dishes = relationship('Dish', back_populates='category', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"

class Dish(Base):
    __tablename__ = 'dishes'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    price = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    
    # Связи
    category = relationship('Category', back_populates='dishes')
    order_details = relationship('OrderDetail', back_populates='dish')
    
    def __repr__(self):
        return f"<Dish(id={self.id}, name='{self.name}', price={self.price})>"

class Order(Base):
    __tablename__ = 'orders'
    
    id = Column(Integer, primary_key=True)
    table_number = Column(Integer, nullable=False)
    total = Column(Float, nullable=False, default=0)
    status = Column(String(50), nullable=False, default='в обработке')  # в обработке, готовится, готов
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    # Связи
    details = relationship('OrderDetail', back_populates='order', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Order(id={self.id}, table={self.table_number}, status='{self.status}')>"

class OrderDetail(Base):
    __tablename__ = 'order_details'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    dish_id = Column(Integer, ForeignKey('dishes.id'), nullable=False)
    dish_name = Column(String(200), nullable=False)  # Сохраняем название на момент заказа
    dish_price = Column(Float, nullable=False)  # Сохраняем цену на момент заказа
    quantity = Column(Integer, nullable=False, default=1)
    
    # Связи
    order = relationship('Order', back_populates='details')
    dish = relationship('Dish', back_populates='order_details')
    
    def __repr__(self):
        return f"<OrderDetail(order_id={self.order_id}, dish='{self.dish_name}', quantity={self.quantity})>"

# Функция для инициализации базы данных
def init_db(db_name='cafe.db'):
    """Создает движок базы данных и все таблицы"""
    engine = create_engine(f'sqlite:///{db_name}', echo=True)
    Base.metadata.create_all(engine)
    return engine

# Функция для заполнения базы начальными данными
def seed_db(session):
    """Заполняет базу начальными данными"""
    
    # Проверяем, есть ли уже категории
    if session.query(Category).count() > 0:
        print("База уже содержит данные, пропускаем инициализацию")
        return
    
    # Создаем категории
    categories = [
        Category(name="Горячие блюда"),
        Category(name="Супы"),
        Category(name="Салаты"),
        Category(name="Напитки"),
        Category(name="Десерты"),
        Category(name="Закуски")
    ]
    
    for cat in categories:
        session.add(cat)
    
    session.flush()  # Чтобы получить id для категорий
    
    # Создаем блюда
    dishes = [
        # Горячие блюда (id: 1)
        Dish(name="Стейк из говядины", price=850, category_id=1),
        Dish(name="Куриная грудка на гриле", price=450, category_id=1),
        Dish(name="Паста Карбонара", price=550, category_id=1),
        Dish(name="Ризотто с грибами", price=480, category_id=1),
        Dish(name="Рыба по-гречески", price=620, category_id=1),
        
        # Супы (id: 2)
        Dish(name="Борщ", price=320, category_id=2),
        Dish(name="Солянка", price=380, category_id=2),
        Dish(name="Крем-суп из грибов", price=350, category_id=2),
        Dish(name="Том Ям", price=450, category_id=2),
        
        # Салаты (id: 3)
        Dish(name="Цезарь с курицей", price=420, category_id=3),
        Dish(name="Греческий салат", price=380, category_id=3),
        Dish(name="Теплый салат с морепродуктами", price=590, category_id=3),
        
        # Напитки (id: 4)
        Dish(name="Кофе американо", price=180, category_id=4),
        Dish(name="Капучино", price=250, category_id=4),
        Dish(name="Чай черный", price=150, category_id=4),
        Dish(name="Чай зеленый", price=150, category_id=4),
        Dish(name="Сок апельсиновый", price=220, category_id=4),
        Dish(name="Лимонад", price=280, category_id=4),
        
        # Десерты (id: 5)
        Dish(name="Чизкейк", price=380, category_id=5),
        Dish(name="Тирамису", price=420, category_id=5),
        Dish(name="Брауни с мороженым", price=390, category_id=5),
        
        # Закуски (id: 6)
        Dish(name="Картошка фри", price=220, category_id=6),
        Dish(name="Кольца кальмара", price=380, category_id=6),
        Dish(name="Сырные палочки", price=320, category_id=6),
        Dish(name="Оливки", price=150, category_id=6),
    ]
    
    for dish in dishes:
        session.add(dish)
    
    session.commit()
    print("База данных успешно заполнена начальными данными!")

# Если файл запускается напрямую, создаем базу и заполняем данными
if __name__ == "__main__":
    engine = init_db()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        seed_db(session)
    finally:
        session.close()
