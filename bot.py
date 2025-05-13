import os
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# Загрузка данных из файлов (как в оригинальном коде)
def load_tanks(filename="tanks.txt"):
    tanks = {}
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден.")
        return tanks
    with open(filename, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split('. ')
            if len(parts) != 4:
                continue
            name = parts[0].lower()
            counters = [x.strip().lower() for x in parts[1].split(',') if x.strip()]
            countered_by = [x.strip().lower() for x in parts[2].split(',') if x.strip()]
            synergy = [x.strip().lower() for x in parts[3].split(',') if x.strip()]
            tanks[name] = {
                'roles': [],
                'counters': counters,
                'countered_by': countered_by,
                'synergy': synergy
            }
    return tanks

def load_heroes(filename="heroes.txt"):
    heroes = []
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден.")
        return heroes
    with open(filename, encoding="utf-8") as file:
        for line in file:
            parts = re.split(r'\.\s*', line.strip())
            if len(parts) < 2:
                continue
            hero = {
                'name': parts[0].lower(),
                'roles': [r.strip().lower() for r in parts[1].split(',')],
                'counters': [x.strip().lower() for x in parts[2].split(',')] if len(parts) > 2 else [],
                'countered_by': [x.strip().lower() for x in parts[3].split(',')] if len(parts) > 3 else [],
                'synergy': [x.strip().lower() for x in parts[4].split(',')] if len(parts) > 4 else []
            }
            heroes.append(hero)
    return heroes

# Глобальные переменные для хранения состояния
user_data = {}
tanks = load_tanks()
heroes = load_heroes()

# Клавиатуры
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🏆 Ввод союзников и вражеских героев", callback_data='recommend_mode')],
        [InlineKeyboardButton("ℹ️ Инфо о герое", callback_data='hero_info_mode')]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_to_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def change_choice_keyboard():
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить выбор", callback_data='recommend_mode')],
        [InlineKeyboardButton("🔙 Назад", callback_data='back_to_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Обработчики команд
def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    user_data[user_id] = {'state': None}
    
    update.message.reply_text(
        "Добро пожаловать в рекомендатель героев для Mobile Legends! 🎮\n"
        "Выберите режим работы:",
        reply_markup=main_menu_keyboard()
    )

# Режим информации о герое
def hero_info_mode(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    user_data[user_id] = {'state': 'hero_info'}
    
    query.answer()
    query.edit_message_text(
        "Введите имя героя для получения информации:",
        reply_markup=back_to_menu_keyboard()
    )

# Режим рекомендации
def recommend_mode(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = update.effective_user.id
    user_data[user_id] = {'state': 'allies_input'}
    
    query.answer()
    query.edit_message_text(
        "Введите список союзных героев через пробел (например: лолита флорин атлас):",
        reply_markup=back_to_menu_keyboard()
    )

# Обработка текстовых сообщений
def handle_message(update: Update, context: CallbackContext):
    
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()


    
    if user_id not in user_data or user_data[user_id]['state'] is None:
        update.message.reply_text("Пожалуйста, выберите режим работы:", reply_markup=main_menu_keyboard())
        return
    
    state = user_data[user_id]['state']
    
    if state == 'hero_info':
        # Обработка запроса информации о герое
        name = text
        found = next((h for h in heroes if h['name'] == name), None)
        
        if not found:
            update.message.reply_text(
                f"Герой '{name.capitalize()}' не найден. Попробуйте ещё раз:",
                reply_markup=back_to_menu_keyboard()
            )
            return
        
        roles = found['roles']
        counters = set(found['counters'])
        countered_by = set(found['countered_by'])
        synergy = set(found['synergy'])
        
        # Дополнение из tanks.txt если роль роум
        if 'роум' in roles and name in tanks:
            tank_data = tanks[name]
            counters.update(tank_data['counters'])
            countered_by.update(tank_data['countered_by'])
            synergy.update(tank_data['synergy'])
        
        response = f"=== Информация о герое '{name.capitalize()}' ===\n"
        response += f"Роли: {', '.join(r.capitalize() for r in roles)}\n"
        if counters:
            response += f"Контрит: {', '.join(sorted(c.capitalize() for c in counters))}\n"
        if countered_by:
            response += f"Контрится: {', '.join(sorted(c.capitalize() for c in countered_by))}\n"
        if synergy:
            response += f"Синергия с: {', '.join(sorted(s.capitalize() for s in synergy))}\n"
        response += "==================================="
        
        update.message.reply_text(response, reply_markup=back_to_menu_keyboard())
        user_data[user_id]['state'] = None
    
    elif state == 'allies_input':
        # Сохраняем союзных героев и запрашиваем вражеских
        user_data[user_id]['allies'] = text.split()
        user_data[user_id]['state'] = 'enemies_input'
        
        update.message.reply_text(
            "Теперь введите список вражеских героев через пробел:",
            reply_markup=back_to_menu_keyboard()
        )
    
    elif state == 'enemies_input':
        # Получаем вражеских героев и выдаем рекомендации
        enemies = text.split()
        allies = user_data[user_id].get('allies', [])
        
        # Проверка на контринг союзников врагами
        warnings = []
        for enemy in enemies:
            if enemy in tanks:
                for ally in allies:
                    if ally in tanks[enemy]['counters']:
                        warnings.append(f"⚠️ Враг {enemy.capitalize()} контрит вашего союзника {ally.capitalize()}!")
        
        if warnings:
            update.message.reply_text("\n".join(warnings))
        
        # Формирование рекомендаций
        recommendations = []
        for tank, data in tanks.items():
            if any(enemy in data['countered_by'] for enemy in enemies):
                continue
            cnt_counters = sum(1 for enemy in enemies if enemy in data['counters'])
            cnt_synergy = sum(1 for ally in allies if ally in data['synergy'])
            priority = cnt_counters + cnt_synergy * 0.5
            if priority > 0:
                recommendations.append({
                    'name': tank,
                    'roles': data['roles'],
                    'counters': [e for e in enemies if e in data['counters']],
                    'synergy': [a for a in allies if a in data['synergy']],
                    'priority': priority
                })
        
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        
        if not recommendations:
            update.message.reply_text(
                "Нет подходящих персонажей для рекомендации.",
                reply_markup=change_choice_keyboard()
            )
            return
        
        response = "=== Рекомендации по персонажам ===\n"
        for rec in recommendations[:5]:  # Ограничим 5 рекомендациями
            name = rec['name'].capitalize()
            roles = ', '.join(role.capitalize() for role in rec['roles']) if rec['roles'] else 'Не указаны'
            response += f"\n{name} ({roles}):\n"
            if rec['counters']:
                response += f"  +{len(rec['counters'])} за контр: {', '.join(e.capitalize() for e in rec['counters'])}\n"
            if rec['synergy']:
                response += f"  +{len(rec['synergy']) * 0.5} за синергию с: {', '.join(a.capitalize() for a in rec['synergy'])}\n"
            response += f"  Всего очков приоритета: {rec['priority']}\n"
        
        response += "==================================="
        
        update.message.reply_text(response, reply_markup=change_choice_keyboard())
        user_data[user_id]['state'] = None

# Обработка кнопок
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data == 'hero_info_mode':
        hero_info_mode(update, context)
    elif query.data == 'recommend_mode':
        recommend_mode(update, context)
    elif query.data == 'back_to_menu':
        user_id = update.effective_user.id
        user_data[user_id] = {'state': None}
        query.edit_message_text(
            "Выберите режим работы:",
            reply_markup=main_menu_keyboard()
        )

def main():
    TOKEN = "8001446088:AAH34RwK3mHP3FNKxoDlpxcbfxo8SZfRbTo"
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Обработчик команды /start (работает в личных чатах и группах)
    dp.add_handler(CommandHandler("start", start))

    # Обработчик для сообщений, начинающихся с /start@username_bot (для групп)
    dp.add_handler(MessageHandler(
        Filters.regex(r'^/start@[a-zA-Z0-9_]+_bot$') & Filters.chat_type.groups,
        start
    ))

    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()