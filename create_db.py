from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, select, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    dishes = relationship("Dish", back_populates="category")

class Dish(Base):
    __tablename__ = "dishes"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="dishes")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    table_number = Column(Integer, nullable=False)
    status = Column(String, default="в обработке")
    total = Column(Float, default=0.0)

def init_db():
    """Создает таблицы и заполняет SQLite данными (в памяти)"""
    # Используем SQLite в памяти вместо PostgreSQL
    engine = create_engine("sqlite:///:memory:", echo=False)
    Session = sessionmaker(bind=engine)
    
    Base.metadata.create_all(engine)
    
    session = Session()
    
    try:
        # Добавляем категории
        categories = [
            Category(name="Напитки"),
            Category(name="Основные блюда"),
            Category(name="Десерты"),
        ]
        session.add_all(categories)
        session.flush()  # Получаем ID категорий
        
        # Добавляем блюда
        dishes = [
            Dish(name="Кофе", price=150, category_id=categories[0].id),
            Dish(name="Чай", price=100, category_id=categories[0].id),
            Dish(name="Сок", price=200, category_id=categories[0].id),
            Dish(name="Стейк", price=800, category_id=categories[1].id),
            Dish(name="Салат", price=350, category_id=categories[1].id),
            Dish(name="Пицца", price=600, category_id=categories[1].id),
            Dish(name="Торт", price=300, category_id=categories[2].id),
            Dish(name="Мороженое", price=200, category_id=categories[2].id),
        ]
        session.add_all(dishes)
        
        # Добавляем тестовые заказы
        orders = [
            Order(table_number=1, status="готов", total=950),
            Order(table_number=3, status="готовится", total=800),
            Order(table_number=5, status="в обработке", total=400),
            Order(table_number=2, status="готов", total=1200),
            Order(table_number=1, status="готовится", total=450),
        ]
        session.add_all(orders)
        
        session.commit()
        print("✅ База SQLite в памяти заполнена")
        
    except Exception as e:
        session.rollback()
        print(f"Ошибка: {e}")
        raise
    finally:
        session.close()
    
    return engine