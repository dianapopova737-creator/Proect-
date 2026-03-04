from sqlalchemy import select, func
from sqlalchemy.orm import sessionmaker
from nicegui import ui
import os
from datetime import datetime, timedelta
from collections import Counter

from create_db import init_db, Category, Dish, Order, OrderDetail

LOGO_PATH = 'pun.png'
engine = init_db()
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

current_order_items = []
current_order_container = None
stats_container = None
orders_container = None

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def get_time_diff_minutes(created_at):
    """Считает, сколько минут прошло с момента заказа"""
    diff = datetime.now() - created_at
    return int(diff.total_seconds() / 60)

# --- БЛОК СТАТИСТИКИ ---
async def refresh_stats():
    """Обновляет блок со статистикой"""
    global stats_container
    
    if stats_container is None:
        return
        
    try:
        stats_container.clear()
        with stats_container:
            # Статистика за сегодня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Общая выручка за сегодня
            today_orders = session.scalars(
                select(Order)
                .where(Order.created_at >= today_start)
            ).all()
            
            today_revenue = sum(order.total for order in today_orders)
            today_orders_count = len(today_orders)
            
            # Статистика по статусам
            active_orders = session.scalars(
                select(Order)
                .where(Order.status.in_(['в обработке', 'готовится']))
            ).all()
            
            ready_orders = session.scalars(
                select(Order)
                .where(Order.status == 'готов')
            ).all()
            
            # Статистика за всё время
            all_time_orders = session.scalars(select(Order)).all()
            all_time_revenue = sum(order.total for order in all_time_orders)
            all_time_count = len(all_time_orders)
            
            # Популярные блюда
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_details = session.scalars(
                select(OrderDetail)
                .join(Order)
                .where(Order.created_at >= thirty_days_ago)
            ).all()
            
            dish_counter = Counter()
            for detail in recent_details:
                dish_counter[detail.dish_name] += detail.quantity
            
            top_dishes = dish_counter.most_common(5)
            
            # Выручка по дням (последние 7 дней)
            revenue_by_day = []
            for i in range(6, -1, -1):
                day = datetime.now() - timedelta(days=i)
                day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                day_orders = session.scalars(
                    select(Order)
                    .where(Order.created_at.between(day_start, day_end))
                ).all()
                
                day_revenue = sum(order.total for order in day_orders)
                revenue_by_day.append({
                    'date': day.strftime('%d.%m'),
                    'revenue': day_revenue
                })
            
            # Если нет данных, показываем заглушку
            if today_orders_count == 0 and all_time_count == 0:
                with ui.card().classes('w-full p-12 bg-gray-50'):
                    with ui.column().classes('items-center gap-4'):
                        ui.icon('analytics', color='gray', size='80px')
                        ui.label('Нет данных для статистики').classes('text-2xl text-gray-400 font-bold')
                        ui.label('Создайте несколько заказов, чтобы увидеть аналитику').classes('text-gray-400')
                return
            
            # Карточки с основной статистикой
            with ui.grid(columns=3).classes('w-full gap-4'):
                # Карточка с выручкой за сегодня
                with ui.card().classes('p-6 bg-gradient-to-br from-amber-50 to-amber-100 shadow-lg hover:shadow-xl transition-shadow'):
                    with ui.column().classes('items-center'):
                        ui.icon('paid', color='#8B6F4C', size='lg')
                        ui.label('Выручка за сегодня').classes('text-sm text-gray-600 mt-2')
                        ui.label(f'{today_revenue:,.0f} ₽').classes('text-3xl font-black text-[#8B6F4C]')
                        ui.label(f'{today_orders_count} заказов').classes('text-sm text-gray-600 mt-1')
                
                # Карточка с заказами в работе
                with ui.card().classes('p-6 bg-gradient-to-br from-blue-50 to-blue-100 shadow-lg hover:shadow-xl transition-shadow'):
                    with ui.column().classes('items-center'):
                        ui.icon('restaurant', color='#3B82F6', size='lg')
                        ui.label('В работе').classes('text-sm text-gray-600 mt-2')
                        ui.label(f'{len(active_orders)}').classes('text-3xl font-black text-blue-600')
                        ui.label(f'Готово: {len(ready_orders)}').classes('text-sm text-gray-600 mt-1')
                
                # Карточка со средним чеком
                with ui.card().classes('p-6 bg-gradient-to-br from-purple-50 to-purple-100 shadow-lg hover:shadow-xl transition-shadow'):
                    with ui.column().classes('items-center'):
                        ui.icon('receipt', color='#8B6F4C', size='lg')
                        ui.label('Средний чек').classes('text-sm text-gray-600 mt-2')
                        avg_bill = today_revenue / today_orders_count if today_orders_count > 0 else 0
                        ui.label(f'{avg_bill:,.0f} ₽').classes('text-3xl font-black text-[#8B6F4C]')
                        ui.label(f'Всего: {all_time_revenue:,.0f} ₽').classes('text-sm text-gray-600 mt-1')
            
            # Популярные блюда
            with ui.card().classes('w-full mt-4 p-6 shadow-lg hover:shadow-xl transition-shadow'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('star', color='#FFB800', size='md')
                    ui.label('Популярные блюда за 30 дней').classes('text-xl font-bold text-[#5D4A36]')
                
                if top_dishes:
                    with ui.column().classes('w-full gap-3'):
                        for i, (dish_name, count) in enumerate(top_dishes, 1):
                            with ui.row().classes('w-full items-center'):
                                # Медалька за место
                                medal_color = 'text-yellow-500' if i == 1 else 'text-gray-400' if i == 2 else 'text-amber-600' if i == 3 else 'text-gray-500'
                                ui.label(f'#{i}').classes(f'font-bold {medal_color} w-8')
                                
                                # Название блюда
                                ui.label(dish_name).classes('flex-1 text-gray-700 font-medium')
                                
                                # Количество заказов
                                ui.badge(str(count), color='orange').classes('text-sm')
                                
                                # Прогресс бар
                                max_count = top_dishes[0][1] if top_dishes else 1
                                percent = (count / max_count * 100) if max_count > 0 else 0
                                with ui.row().classes('w-24 h-2 bg-gray-200 rounded-full overflow-hidden ml-2'):
                                    ui.element('div').classes(f'h-full bg-orange-500').style(f'width: {percent}%')
                else:
                    ui.label('Нет данных за последние 30 дней').classes('text-gray-400 italic text-center w-full py-8')
            
            # График выручки
            with ui.card().classes('w-full mt-4 p-6 shadow-lg hover:shadow-xl transition-shadow'):
                with ui.row().classes('items-center gap-2 mb-4'):
                    ui.icon('trending_up', color='#8B6F4C', size='md')
                    ui.label('Динамика выручки за 7 дней').classes('text-xl font-bold text-[#5D4A36]')
                
                with ui.column().classes('w-full gap-4'):
                    max_revenue = max([d['revenue'] for d in revenue_by_day]) if revenue_by_day and max([d['revenue'] for d in revenue_by_day]) > 0 else 1
                    for day_data in revenue_by_day:
                        with ui.column().classes('w-full'):
                            with ui.row().classes('w-full justify-between items-center'):
                                ui.label(day_data['date']).classes('text-sm font-medium text-gray-600')
                                ui.label(f"{day_data['revenue']:,.0f} ₽").classes('text-sm font-bold text-[#8B6F4C]')
                            
                            # Полоса прогресса
                            percent = (day_data['revenue'] / max_revenue * 100) if max_revenue > 0 else 0
                            with ui.row().classes('w-full h-3 bg-gray-200 rounded-full overflow-hidden mt-1'):
                                ui.element('div').classes(f'h-full bg-gradient-to-r from-green-400 to-green-600').style(f'width: {percent}%')
    except Exception as e:
        print(f"Ошибка при обновлении статистики: {e}")

# --- БЛОК КУХНИ ---
async def refresh_kitchen_orders(container):
    if container is None:
        return
    
    try:    
        container.clear()
        with container:
            orders = session.scalars(
                select(Order)
                .where(Order.status.in_(['в обработке', 'готовится']))
                .order_by(Order.created_at)
            ).all()

            if not orders:
                ui.label('Заказов нет. Отличная работа! ☕').classes('text-gray-500 italic text-center w-full p-8 text-xl')
                return

            for order in orders:
                mins_passed = get_time_diff_minutes(order.created_at)

                # Меняем цвет рамки в зависимости от времени ожидания
                border_color = 'border-red-500' if mins_passed > 15 else ('border-yellow-400' if order.status == 'в обработке' else 'border-blue-400')
                bg_color = 'bg-white' if mins_passed <= 15 else 'bg-red-50'

                with ui.card().classes(f'w-full hover:shadow-xl transition-shadow border-t-4 {border_color} {bg_color} p-4'):
                    with ui.row().classes('items-center justify-between w-full'):
                        with ui.row().classes('items-center gap-2'):
                            ui.label(f'Стол #{order.table_number}').classes('text-2xl font-black text-[#5D4A36]')
                            ui.badge(f'{mins_passed} мин', color='red' if mins_passed > 15 else 'gray').classes('text-sm')
                            
                            if order.status == 'в обработке':
                                ui.badge('Новый', color='orange').props('rounded outline')
                            else:
                                ui.badge('Готовится', color='blue').props('rounded')
                    
                    ui.separator().classes('my-2')
                    details = session.scalars(select(OrderDetail).where(OrderDetail.order_id == order.id)).all()
                    with ui.column().classes('w-full gap-1'):
                        for detail in details:
                            with ui.row().classes('w-full justify-between items-center bg-gray-50 p-2 rounded'):
                                ui.label(detail.dish_name).classes('text-lg font-medium text-gray-800')
                                ui.label(f'x{detail.quantity}').classes('text-lg font-bold text-[#8B6F4C]')
                    
                    with ui.row().classes('justify-end gap-2 mt-4 w-full'):
                        if order.status == 'в обработке':
                            ui.button('Начать готовить', icon='local_fire_department', color='blue-500').on(
                                'click', lambda o=order: update_status(o, 'готовится', container, True)
                            ).classes('w-full')
                        elif order.status == 'готовится':
                            ui.button('Готово (В зал)', icon='done_all', color='green-600').on(
                                'click', lambda o=order: update_status(o, 'готов', container, True)
                            ).classes('w-full')
    except Exception as e:
        print(f"Ошибка при обновлении кухни: {e}")

# --- БЛОК ЗАЛА (ОФИЦИАНТЫ) ---

async def refresh_orders(container):
    if container is None:
        return
    
    try:    
        container.clear()
        with container:
            orders = session.scalars(select(Order).order_by(Order.id.desc())).all()
            for order in orders:
                status_colors = {
                    'готов': 'bg-green-100 text-green-800 border-green-200',
                    'готовится': 'bg-blue-100 text-blue-800 border-blue-200',
                    'в обработке': 'bg-orange-100 text-orange-800 border-orange-200'
                }
                colors = status_colors.get(order.status, 'bg-gray-100 text-gray-800 border-gray-200')

                with ui.card().classes(f'w-full border {colors} shadow-sm'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(f'Стол #{order.table_number}').classes('font-bold text-lg')
                        ui.label(order.status.upper()).classes('text-xs font-bold tracking-wider')
                        ui.label(f'{order.total} ₽').classes('font-bold')
                    with ui.row().classes('w-full justify-end mt-2 gap-2'):
                        ui.button('Чек', icon='receipt', color='white').props('text-color=black size=sm').on('click', lambda o=order: show_receipt(o))
                        if order.status == 'готов':
                            ui.button('Закрыть счет', icon='check', color='green').props('size=sm').on('click', lambda o=order: delete_order(o))
    except Exception as e:
        print(f"Ошибка при обновлении заказов: {e}")

def show_receipt(order):
    with ui.dialog() as dialog, ui.card().classes('w-80 p-0 bg-[#F9F6F0]'):
        with ui.column().classes('w-full bg-[#5D4A36] p-4 items-center'):
            if os.path.exists(LOGO_PATH):
                ui.image(LOGO_PATH).classes('w-10 h-10 rounded-full mb-2')
            ui.label('КАССОВЫЙ ЧЕК').classes('text-white font-bold tracking-widest')
            ui.label(f'Стол: {order.table_number} | Заказ: #{order.id}').classes('text-white text-xs opacity-80')
        
        with ui.column().classes('w-full p-4 gap-1'):
            details = session.scalars(select(OrderDetail).where(OrderDetail.order_id == order.id)).all()
            for d in details:
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label(f'{d.dish_name} x{d.quantity}').classes('text-sm')
                    ui.label(f'{d.dish_price * d.quantity} ₽').classes('text-sm font-bold')
            
            ui.separator().classes('my-2 border-dashed border-gray-400')
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('ИТОГО:').classes('font-black text-lg')
                ui.label(f'{order.total} ₽').classes('font-black text-xl text-[#8B6F4C]')
            ui.label(f'Время: {order.created_at.strftime("%H:%M")}').classes('text-xs text-gray-400 mt-2 mx-auto')
    dialog.open()

# --- МЕНЮ И КОРЗИНА ---

async def render_menu(container):
    if container is None:
        return
    
    try:    
        container.clear()
        with container:
            categories = session.scalars(select(Category)).all()
            
            if not categories:
                ui.label('Нет категорий').classes('text-gray-500 p-4')
                return

            # Создаем стильные вкладки
            with ui.tabs().classes('w-full bg-[#F5E6D3] text-[#5D4A36] font-bold rounded-t-lg') as tabs:
                tab_elements = {cat.id: ui.tab(cat.name) for cat in categories}

            with ui.tab_panels(tabs, value=tab_elements[categories[0].id]).classes('w-full bg-white border border-[#F5E6D3] rounded-b-lg p-0'):
                for cat in categories:
                    with ui.tab_panel(tab_elements[cat.id]).classes('p-0'):
                        dishes = session.scalars(select(Dish).where(Dish.category_id == cat.id)).all()
                        for dish in dishes:
                            with ui.row().classes('items-center justify-between w-full p-4 border-b hover:bg-orange-50 cursor-pointer transition-colors').on('click', lambda d=dish: add_to_order(d)):
                                with ui.column().classes('gap-0'):
                                    ui.label(dish.name).classes('text-md font-bold text-gray-800')
                                ui.label(f'{dish.price} ₽').classes('text-[#8B6F4C] font-black bg-[#F9F6F0] px-3 py-1 rounded-full')
    except Exception as e:
        print(f"Ошибка при отображении меню: {e}")

def refresh_cart():
    if current_order_container is None:
        return
    
    try:    
        current_order_container.clear()
        with current_order_container:
            if not current_order_items:
                ui.label('Корзина пуста').classes('text-gray-400 p-4 mx-auto')
                return

            total = sum(item['price'] for item in current_order_items)
            item_counts = Counter(item['id'] for item in current_order_items)
            unique_items = {item['id']: item for item in current_order_items}

            with ui.column().classes('w-full gap-0 max-h-[300px] overflow-y-auto'):
                for dish_id, count in item_counts.items():
                    item = unique_items[dish_id]
                    with ui.row().classes('items-center justify-between w-full p-2 border-b'):
                        ui.label(f"{item['name']}").classes('text-sm font-medium w-1/2 truncate')
                        with ui.row().classes('items-center gap-2'):
                            ui.button('-', color='red-300').props('round flat size=xs').on('click', lambda i=item: remove_from_order(i))
                            ui.label(f"{count}").classes('font-bold w-4 text-center')
                            ui.button('+', color='green-300').props('round flat size=xs').on('click', lambda i=item: add_to_order(i))
                        ui.label(f"{item['price'] * count}₽").classes('text-sm font-bold text-[#8B6F4C]')

            with ui.row().classes('w-full justify-between items-center p-4 bg-[#F5E6D3] rounded-b-lg mt-auto'):
                ui.label('Сумма:').classes('font-bold')
                ui.label(f'{total} ₽').classes('text-xl font-black text-[#5D4A36]')
    except Exception as e:
        print(f"Ошибка при обновлении корзины: {e}")

def add_to_order(dish):
    # Принимаем либо объект Dish (из меню), либо dict (из корзины)
    dish_id = dish.id if hasattr(dish, 'id') else dish['id']
    name = dish.name if hasattr(dish, 'name') else dish['name']
    price = dish.price if hasattr(dish, 'price') else dish['price']
    
    current_order_items.append({'id': dish_id, 'name': name, 'price': price})
    refresh_cart()

def remove_from_order(item):
    for i, current_item in enumerate(current_order_items):
        if current_item['id'] == item['id']:
            current_order_items.pop(i)
            break
    refresh_cart()

# --- ЛОГИКА БД ---

async def submit_order(table_input):
    if not current_order_items:
        ui.notify('Корзина пуста!', color='warning')
        return
    if not table_input.value or not str(table_input.value).isdigit():
        ui.notify('Укажите номер стола!', color='warning')
        return

    try:
        table_number = int(table_input.value)
        total = sum(item['price'] for item in current_order_items)

        new_order = Order(table_number=table_number, total=total)
        session.add(new_order)
        session.flush()

        item_counts = Counter(item['id'] for item in current_order_items)
        unique_items = {item['id']: item for item in current_order_items}

        for dish_id, count in item_counts.items():
            info = unique_items[dish_id]
            session.add(OrderDetail(
                order_id=new_order.id, 
                dish_id=dish_id, 
                dish_name=info['name'], 
                dish_price=info['price'], 
                quantity=count
            ))

        session.commit()
        current_order_items.clear()
        table_input.set_value('')
        refresh_cart()

        await refresh_orders(orders_container)
        
        if stats_container:
            ui.timer(0.1, refresh_stats, once=True)
            
        ui.notify(f'Заказ на стол {table_number} отправлен!', color='positive', icon='done')
    except Exception as e:
        session.rollback()
        ui.notify(f'Ошибка: {e}', color='negative')

async def update_status(order, new_status, container, is_kitchen=False):
    order.status = new_status
    session.commit()
    if is_kitchen:
        await refresh_kitchen_orders(container)
    else:
        await refresh_orders(container)
    
    # Обновляем статистику через таймер
    if stats_container:
        ui.timer(0.1, refresh_stats, once=True)

async def delete_order(order):
    try:
        table_number = order.table_number
        session.delete(order)
        session.commit()
        
        await refresh_orders(orders_container)
        
        # Обновляем статистику через таймер
        if stats_container:
            ui.timer(0.1, refresh_stats, once=True)
            
        ui.notify(f'Счет стола {table_number} закрыт', color='info')
    except Exception as e:
        session.rollback()
        ui.notify(f'Ошибка при удалении: {e}', color='negative')

# --- СТРАНИЦЫ ---

@ui.page('/')
async def main_page():
    ui.colors(primary='#8B6F4C', secondary='#5D4A36', accent='#F5E6D3')
    
    with ui.header(elevated=True).classes('items-center justify-between bg-[#5D4A36] px-6 py-3'):
        with ui.row().classes('items-center gap-3'):
            if os.path.exists(LOGO_PATH):
                ui.image(LOGO_PATH).classes('w-12 h-12 rounded bg-white p-1')
            ui.label('Касса | Зал').classes('text-xl font-bold text-white')
        with ui.row().classes('gap-2'):
            ui.link('Статистика', '/stats').classes('text-white font-medium bg-[#8B6F4C] px-4 py-2 rounded-lg hover:bg-[#A67B5B]')
            ui.link('Кухня', '/kitchen').classes('text-white font-medium bg-[#8B6F4C] px-4 py-2 rounded-lg hover:bg-[#A67B5B]')

    with ui.row().classes('w-full max-w-7xl mx-auto gap-6 p-4 mt-2 items-start'):
        # ЛЕВАЯ КОЛОНКА: МЕНЮ
        with ui.column().classes('w-7/12 gap-4'):
            menu_container = ui.column().classes('w-full shadow-lg rounded-lg')
            await render_menu(menu_container)

        # ПРАВАЯ КОЛОНКА: КОРЗИНА И УПРАВЛЕНИЕ
        with ui.column().classes('w-4/12 gap-4 flex-grow'):
            with ui.card().classes('w-full p-0 shadow-lg'):
                with ui.row().classes('w-full bg-[#5D4A36] p-4 rounded-t-lg'):
                    ui.label('Новый заказ').classes('text-white font-bold text-lg')

                global current_order_container
                current_order_container = ui.column().classes('w-full min-h-[150px]')
                refresh_cart()

                with ui.column().classes('w-full p-4 gap-2 bg-gray-50 rounded-b-lg'):
                    table_input = ui.input('Номер стола', placeholder='Например: 5').classes('w-full').props('outlined')
                    ui.button('Отправить на кухню', icon='send').classes('w-full h-12 shadow-md').on('click', lambda: submit_order(table_input))

            # АКТИВНЫЕ ЗАКАЗЫ
            with ui.card().classes('w-full mt-4 p-4 shadow-lg bg-gray-50'):
                with ui.row().classes('justify-between w-full items-center mb-2'):
                    ui.label('В работе у зала').classes('font-bold text-[#5D4A36]')
                    ui.button(icon='refresh', color='gray').props('round flat size=sm').on('click', lambda: refresh_orders(orders_container))
                
                global orders_container
                orders_container = ui.column().classes('w-full gap-2')
                await refresh_orders(orders_container)

@ui.page('/kitchen')
async def kitchen_page():
    ui.page_title('Экран Повара')
    
    with ui.header(elevated=True).classes('items-center justify-between bg-black px-6 py-3'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('restaurant', color='white', size='md')
            ui.label('Кухня | Терминал повара').classes('text-xl font-bold text-white')
        ui.link('Вернуться в Зал', '/').classes('text-white font-medium border border-white px-4 py-2 rounded-lg hover:bg-gray-800')

    with ui.column().classes('w-full max-w-7xl mx-auto p-4'):
        kitchen_orders_container = ui.column().classes('w-full gap-6')
        
        # Автообновление раз в 10 секунд
        ui.timer(10.0, lambda: refresh_kitchen_orders(kitchen_orders_container))
        await refresh_kitchen_orders(kitchen_orders_container)

@ui.page('/stats')
async def stats_page():
    ui.page_title('Статистика | Аналитика')
    
    ui.colors(primary='#8B6F4C', secondary='#5D4A36', accent='#F5E6D3')
    
    with ui.header(elevated=True).classes('items-center justify-between bg-[#5D4A36] px-6 py-3'):
        with ui.row().classes('items-center gap-3'):
            ui.icon('bar_chart', color='white', size='md')
            ui.label('Статистика | Аналитика').classes('text-xl font-bold text-white')
        with ui.row().classes('gap-2'):
            ui.link('В зал', '/').classes('text-white font-medium bg-[#8B6F4C] px-4 py-2 rounded-lg hover:bg-[#A67B5B]')
            ui.link('На кухню', '/kitchen').classes('text-white font-medium bg-[#8B6F4C] px-4 py-2 rounded-lg hover:bg-[#A67B5B]')
    
    with ui.column().classes('w-full max-w-7xl mx-auto p-4'):
        # Заголовок страницы
        with ui.row().classes('w-full justify-between items-center mb-4'):
            ui.label('📊 Аналитика и статистика').classes('text-2xl font-black text-[#5D4A36]')
            ui.button(icon='refresh', color='gray').props('round flat size=md').on('click', refresh_stats)
        
        global stats_container
        stats_container = ui.column().classes('w-full gap-4')
        
        # Автообновление статистики раз в 30 секунд
        ui.timer(30.0, refresh_stats)
        await refresh_stats()

if __name__ == "__main__":
    ui.run(title='Система управления кафе', port=8080, reload=False, favicon='🍔')
