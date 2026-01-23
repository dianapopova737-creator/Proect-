from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker
from nicegui import ui
from create_db import init_db, Category, Dish, Order

# Инициализация SQLite в памяти
engine = init_db()
SessionLocal = sessionmaker(bind=engine)

# Храним ссылку на глобальную сессию
session = SessionLocal()

# Глобальные переменные для хранения текущего заказа
current_order_items = []
current_table_number = None

# Глобальный контейнер для текущего заказа
current_order_container = None

async def refresh_orders(orders_container):
    """Обновление списка заказов"""
    orders_container.clear()
    with orders_container:
        try:
            orders = session.scalars(select(Order).order_by(Order.id)).all()
            
            if not orders:
                ui.label('Нет заказов')
                return
            
            for order in orders:
                with ui.card().classes('w-full'):
                    with ui.row().classes('items-center justify-between'):
                        with ui.column().classes('gap-1'):
                            ui.label(f'Стол #{order.table_number}').classes('font-bold')
                            ui.label(f'ID: {order.id}').classes('text-sm text-gray-500')
                        ui.label(f'Статус: {order.status}').classes(
                            'px-2 py-1 rounded'+
                            ('bg-green-100 text-green-800' if order.status == 'готов' else
                            'bg-yellow-100 text-yellow-800' if order.status == 'готовится' else
                            'bg-blue-100 text-blue-800')
                        )
                        ui.label(f'{order.total} ₽').classes('text-lg font-semibold')
                    
                    # Кнопки управления заказом
                    with ui.row().classes('justify-end gap-2 mt-2'):
                        if order.status == 'в обработке':
                            ui.button('Готовится', icon='timer', color='orange').on(
                                'click', lambda o=order: update_order_status(o, 'готовится', orders_container)
                            )
                        elif order.status == 'готовится':
                            ui.button('Готово', icon='check', color='green').on(
                                'click', lambda o=order: update_order_status(o, 'готов', orders_container)
                            )
                        ui.button('Удалить', icon='delete', color='red').on(
                            'click', lambda o=order: delete_order(o, orders_container)
                        )
        except Exception as e:
            ui.label(f'Ошибка загрузки заказов: {str(e)}')

async def refresh_menu(menu_container):
    """Обновление меню"""
    menu_container.clear()
    with menu_container:
        try:
            categories = session.scalars(select(Category)).all()
            
            for category in categories:
                with ui.expansion(category.name, icon='restaurant_menu').classes('w-full'):
                    dishes = session.scalars(
                        select(Dish).where(Dish.category_id == category.id)
                    ).all()
                    
                    for dish in dishes:
                        with ui.row().classes('items-center justify-between w-full p-2 hover:bg-gray-50'):
                            with ui.column().classes('gap-1'):
                                ui.label(dish.name).classes('text-lg')
                                ui.label(f'{dish.price} ₽').classes('text-sm text-gray-600')
                            ui.button('Добавить в заказ', icon='add', color='primary').on(
                                'click', lambda d=dish: add_to_order(d)
                            )
        except Exception as e:
            ui.label(f'Ошибка загрузки меню: {str(e)}')

def refresh_current_order():
    """Обновление отображения текущего заказа"""
    if current_order_container:
        current_order_container.clear()
        with current_order_container:
            display_current_order()

def display_current_order():
    """Отображение текущего заказа"""
    if not current_order_items:
        ui.label('Нет выбранных блюд').classes('text-gray-500 italic p-4')
        return
    
    total = 0
    
    # Заголовок текущего заказа
    with ui.row().classes('items-center justify-between w-full p-2 bg-blue-50'):
        ui.label('🛒 Текущий заказ').classes('text-lg font-bold')
        if current_order_items:
            ui.label(f'{len(current_order_items)} блюд').classes('text-sm text-gray-600')
    
    # Список блюд
    for item in current_order_items:
        with ui.row().classes('items-center justify-between w-full p-3 border-b hover:bg-gray-50'):
            with ui.column().classes('gap-1 flex-grow'):
                ui.label(item['name']).classes('text-md font-medium')
                ui.label(f"{item['price']} ₽").classes('text-sm text-gray-600')
            
            # Кнопка удаления
            ui.button(icon='delete', color='red').on(
                'click', lambda i=item: remove_from_order(i)
            ).props('flat').classes('ml-2')
        
        total += item['price']
    
    # Итоговая сумма
    ui.separator()
    with ui.row().classes('items-center justify-between w-full p-3 bg-green-50'):
        ui.label('Итого:').classes('text-lg font-bold')
        ui.label(f'{total} ₽').classes('text-xl font-bold text-green-600')
    
    # Информация о количестве блюд
    with ui.row().classes('justify-center w-full p-2'):
        ui.label(f'Всего блюд: {len(current_order_items)}').classes('text-sm text-gray-500')

def add_to_order(dish):
    """Добавить блюдо в текущий заказ"""
    current_order_items.append({
        'id': dish.id,
        'name': dish.name,
        'price': dish.price
    })
    
    # Автоматическое обновление отображения
    refresh_current_order()
    
    ui.notify(f'✅ Добавлено: {dish.name}', color='positive', position='top')
    
    # Показываем краткую информацию о текущем заказе
    total = sum(item['price'] for item in current_order_items)
    ui.notify(f'В заказе: {len(current_order_items)} блюд на сумму {total} ₽', 
              color='info', position='top-right', timeout=2000)

def remove_from_order(item):
    """Удалить блюдо из текущего заказа"""
    if item in current_order_items:
        current_order_items.remove(item)
        refresh_current_order()
        ui.notify(f'🗑️ Удалено: {item["name"]}', color='warning')
        
        if current_order_items:
            total = sum(item['price'] for item in current_order_items)
            ui.notify(f'Осталось: {len(current_order_items)} блюд на сумму {total} ₽', 
                      color='info', position='top-right', timeout=2000)

async def create_order(table_input, orders_container):
    """Создать новый заказ"""
    global current_order_items, current_table_number
    
    if not current_order_items:
        ui.notify('Добавьте блюда в заказ!', color='warning')
        return
    
    if not table_input.value or not table_input.value.isdigit():
        ui.notify('Введите корректный номер стола!', color='warning')
        return
    
    try:
        table_number = int(table_input.value)
        total = sum(item['price'] for item in current_order_items)
        
        # Создаем новый заказ
        new_order = Order(
            table_number=table_number,
            status='в обработке',
            total=total
        )
        session.add(new_order)
        session.commit()
        
        # Очищаем текущий заказ
        current_order_items.clear()
        current_table_number = None
        table_input.set_value('')
        
        # Обновляем отображение
        refresh_current_order()
        await refresh_orders(orders_container)
        refresh_statistics()
        
        ui.notify(f'✅ Заказ для стола #{table_number} создан! Сумма: {total} ₽', 
                  color='positive', position='top')
        
    except Exception as e:
        session.rollback()
        ui.notify(f'Ошибка создания заказа: {str(e)}', color='negative')

async def update_order_status(order, new_status, orders_container):
    """Обновить статус заказа"""
    try:
        order.status = new_status
        session.commit()
        await refresh_orders(orders_container)
        refresh_statistics()
        ui.notify(f'Статус заказа #{order.id} обновлен: {new_status}', color='positive')
    except Exception as e:
        session.rollback()
        ui.notify(f'Ошибка обновления статуса: {str(e)}', color='negative')

async def delete_order(order, orders_container):
    """Удалить заказ"""
    try:
        session.delete(order)
        session.commit()
        await refresh_orders(orders_container)
        refresh_statistics()
        ui.notify(f'Заказ #{order.id} удален', color='positive')
    except Exception as e:
        session.rollback()
        ui.notify(f'Ошибка удаления заказа: {str(e)}', color='negative')

async def search_orders(query: str, results_container, orders_container):
    """Поиск заказов по номеру стола"""
    results_container.clear()
    with results_container:
        if not query.strip():
            ui.label('Введите номер стола для поиска').classes('text-gray-500')
            return
        
        try:
            table_num = int(query)
            orders = session.scalars(
                select(Order).where(Order.table_number == table_num)
            ).all()
            
            if orders:
                for order in orders:
                    with ui.card().classes('w-full bg-blue-50'):
                        with ui.column().classes('gap-2'):
                            ui.label(f'🎯 Найден заказ для стола #{order.table_number}').classes('font-bold text-lg')
                            ui.label(f'ID: {order.id}')
                            ui.label(f'Статус: {order.status}')
                            ui.label(f'Сумма: {order.total} ₽')
            else:
                ui.label(f'Заказы для стола #{table_num} не найдены').classes('text-red-500')
        except ValueError:
            ui.label('Введите корректный номер стола (число)').classes('text-red-500')
        except Exception as e:
            ui.label(f'Ошибка поиска: {str(e)}')
    
    # Обновляем основной список заказов после поиска
    await refresh_orders(orders_container)

def refresh_statistics():
    """Обновить статистику"""
    try:
        # Получаем статистику
        total_orders = session.scalar(select(func.count()).select_from(Order))
        total_revenue = session.scalar(select(func.sum(Order.total))) or 0
        
        # Статистика по статусам
        status_counts = session.execute(
            select(Order.status, func.count(Order.id))
            .group_by(Order.status)
        ).all()
        
        # Статистика по столам
        table_stats = session.execute(
            select(Order.table_number, func.count(Order.id), func.sum(Order.total))
            .group_by(Order.table_number)
            .order_by(func.sum(Order.total).desc())
        ).all()
        
        # Обновляем контейнеры
        stats_container.clear()
        status_container.clear()
        tables_container.clear()
        
        with stats_container:
            ui.label('📊 Общая статистика').classes('text-xl font-bold mb-2')
            with ui.row().classes('justify-between items-center'):
                ui.label(f'Всего заказов:').classes('text-lg')
                ui.label(f'{total_orders}').classes('text-lg font-bold')
            with ui.row().classes('justify-between items-center'):
                ui.label(f'Общая выручка:').classes('text-lg')
                ui.label(f'{total_revenue:.2f} ₽').classes('text-lg font-bold text-green-600')
        
        with status_container:
            ui.label('📈 Статусы заказов').classes('text-xl font-bold mb-2')
            for status, count in status_counts:
                with ui.row().classes('justify-between items-center'):
                    ui.label(f'{status}:').classes('text-md')
                    ui.label(f'{count}').classes('text-md font-semibold')
        
        with tables_container:
            ui.label('🍽️ Статистика по столам').classes('text-xl font-bold mb-2')
            if table_stats:
                for table_num, count, revenue in table_stats:
                    with ui.card().classes('w-full mb-2'):
                        with ui.row().classes('justify-between items-center'):
                            ui.label(f'Стол #{table_num}').classes('font-bold')
                            ui.label(f'{count} зак.').classes('text-sm')
                        ui.label(f'Выручка: {revenue or 0:.2f} ₽').classes('text-md text-green-600')
            else:
                ui.label('Нет данных').classes('text-gray-500')
                
    except Exception as e:
        print(f"Ошибка обновления статистики: {e}")

@ui.page('/')
async def main_page():
    ui.label('☕ Учет заказов кафе').classes('text-3xl font-bold text-center mb-6 text-gray-800')
    
    with ui.column().classes('w-full max-w-6xl mx-auto gap-6 p-4'):
        
        # Создание нового заказа
        with ui.card().classes('w-full bg-gradient-to-r from-green-50 to-blue-50'):
            ui.label('🛒 Создать новый заказ').classes('text-xl font-bold mb-4')
            
            with ui.row().classes('w-full items-center gap-4'):
                table_input = ui.input('Номер стола', placeholder='Введите номер стола...').classes('w-48')
                ui.button('Создать заказ', icon='add_shopping_cart', color='primary').on(
                    'click', lambda: create_order(table_input, orders_container)
                ).classes('h-10')
                ui.button('Очистить заказ', icon='clear', color='gray').on(
                    'click', lambda: [
                        current_order_items.clear(),
                        refresh_current_order(),
                        table_input.set_value(''),
                        ui.notify('Заказ очищен', color='info')
                    ]
                ).classes('h-10')
        
        with ui.row().classes('w-full gap-6'):
            # Меню
            with ui.column().classes('w-1/2 gap-4'):
                with ui.card().classes('w-full'):
                    with ui.row().classes('w-full items-center justify-between'):
                        ui.label('🍽️ Меню').classes('text-2xl font-semibold')
                        ui.button('Обновить', icon='refresh', color='orange').on(
                            'click', lambda: refresh_menu(menu_container)
                        )
                    menu_container = ui.column().classes('w-full max-h-96 overflow-y-auto')
            
            # Текущий заказ
            with ui.column().classes('w-1/2 gap-4'):
                with ui.card().classes('w-full'):
                    ui.label('📋 Текущий заказ').classes('text-2xl font-semibold mb-4')
                    # Сохраняем ссылку на контейнер текущего заказа
                    global current_order_container
                    current_order_container = ui.column().classes('w-full max-h-96 overflow-y-auto')
        
        ui.separator()
        
        # Поиск заказов
        with ui.card().classes('w-full'):
            ui.label('🔍 Поиск заказов').classes('text-xl font-semibold mb-2')
            with ui.row().classes('w-full items-center gap-4'):
                search_input = ui.input('Номер стола', placeholder='Введите номер стола...').classes('flex-grow')
                with ui.row().classes('gap-2'):
                    ui.button('Найти', icon='search', color='primary').on('click', lambda: search_orders(
                        search_input.value, results_container, orders_container
                    ))
                    ui.button('Очистить', icon='clear').on('click', lambda: [search_input.set_value(''), results_container.clear()])
        
        # Контейнер для результатов поиска
        results_container = ui.column().classes('w-full gap-4')
        
        ui.separator()
        
        # Список всех заказов
        with ui.card().classes('w-full'):
            with ui.row().classes('w-full items-center justify-between'):
                ui.label('📋 Все заказы').classes('text-2xl font-semibold')
                ui.button('Обновить', icon='refresh', color='green').on('click', lambda: refresh_orders(orders_container))
            orders_container = ui.column().classes('w-full gap-3 max-h-96 overflow-y-auto')
        
        ui.separator()
        
        # Статистика
        with ui.card().classes('w-full bg-gradient-to-r from-blue-50 to-purple-50'):
            with ui.row().classes('w-full items-center justify-between mb-4'):
                ui.label('📊 Статистика').classes('text-2xl font-bold')
                ui.button('Обновить', icon='refresh', color='primary').on('click', lambda: refresh_statistics())
            
            with ui.grid(columns=3).classes('w-full gap-6'):
                # Общая статистика
                with ui.card().classes('p-4'):
                    global stats_container
                    stats_container = ui.column().classes('w-full')
                
                # Статусы заказов
                with ui.card().classes('p-4'):
                    global status_container
                    status_container = ui.column().classes('w-full')
                
                # Статистика по столам
                with ui.card().classes('p-4'):
                    global tables_container
                    tables_container = ui.column().classes('w-full')
        
        # Первоначальная загрузка данных
        await refresh_orders(orders_container)
        await refresh_menu(menu_container)
        # Отображаем текущий заказ (пустой в начале)
        refresh_current_order()
        refresh_statistics()

# Запуск
if __name__ == "__main__":
    # Закрываем сессию при выходе
    import atexit
    def cleanup():
        session.close()
        engine.dispose()
    atexit.register(cleanup)
    
    ui.run(title='Кафе - Учет заказов', port=8080, reload=False)
