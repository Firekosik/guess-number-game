from flask import Flask, render_template, request, jsonify, session
import random
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Важный для сессий

class WebNumberGame:
    def __init__(self):
        self.save_file = "game_data.json"
        self.load_stats()
    
    def load_stats(self):
        """Загружает общую статистику всех игроков"""
        try:
            if os.path.exists(self.save_file):
                with open(self.save_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
            else:
                self.stats = {
                    'total_games': 0,
                    'total_wins': 0,
                    'best_players': [],
                    'recent_games': []
                }
        except:
            self.stats = {
                'total_games': 0,
                'total_wins': 0,
                'best_players': [],
                'recent_games': []
            }
    
    def save_stats(self, player_name, score, won=False):
        """Сохраняет статистику игры"""
        self.stats['total_games'] += 1
        if won:
            self.stats['total_wins'] += 1
        
        # Добавляем в лучшие игроки
        player_exists = False
        for player in self.stats['best_players']:
            if player['name'] == player_name:
                player['score'] = max(player['score'], score)
                player_exists = True
                break
        
        if not player_exists:
            self.stats['best_players'].append({
                'name': player_name,
                'score': score
            })
        
        # Сортируем лучших игроков
        self.stats['best_players'] = sorted(
            self.stats['best_players'], 
            key=lambda x: x['score'], 
            reverse=True
        )[:10]  # Топ-10
        
        # Добавляем в недавние игры
        self.stats['recent_games'].insert(0, {
            'name': player_name,
            'score': score,
            'won': won,
            'time': datetime.now().strftime("%d.%m.%Y %H:%M")
        })
        self.stats['recent_games'] = self.stats['recent_games'][:10]  # Последние 10 игр
        
        # Сохраняем в файл
        with open(self.save_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

game_manager = WebNumberGame()

@app.route('/')
def index():
    """Главная страница"""
    # Инициализируем игровую сессию
    if 'secret_number' not in session:
        session['secret_number'] = random.randint(1, 100)
        session['attempts'] = 0
        session['max_attempts'] = 7
        session['score'] = 0
        session['player_name'] = 'Игрок'
        session['game_over'] = False
    
    return render_template('index.html', 
                         attempts=session['attempts'],
                         max_attempts=session['max_attempts'],
                         score=session['score'],
                         player_name=session['player_name'],
                         game_over=session['game_over'],
                         stats=game_manager.stats)

@app.route('/guess', methods=['POST'])
def make_guess():
    guess = int(request.form['guess'])
    secret_number = session['secret_number']
    
    # Определяем диапазон в зависимости от сложности
    max_range = 100  # по умолчанию средний уровень
    if session['max_attempts'] == 10:  # легкий уровень
        max_range = 50
    elif session['max_attempts'] == 5:  # сложный уровень
        max_range = 200
    
    # Проверяем входит ли число в допустимый диапазон
    if guess < 1 or guess > max_range:
        return jsonify({
            'result': 'error',
            'message': f'❌ Введите число от 1 до {max_range}!'
        })
    
    session['attempts'] += 1
    
    response = {
        'attempt': session['attempts'],
        'max_attempts': session['max_attempts'],
        'guess': guess
    }
    
    if guess == secret_number:
        points = 100 - (session['attempts'] * 10)
        session['score'] += max(points, 10)
        session['game_over'] = True
        
        response.update({
            'result': 'win',
            'message': f'🎉 Поздравляю! Вы угадали число {secret_number}!',
            'points': points,
            'total_score': session['score']
        })
        
        game_manager.save_stats(session['player_name'], session['score'], won=True)
        
    elif session['attempts'] >= session['max_attempts']:
        session['game_over'] = True
        response.update({
            'result': 'lose',
            'message': f'💔 Игра окончена! Загаданное число было: {secret_number}'
        })
        
        game_manager.save_stats(session['player_name'], session['score'], won=False)
        
    else:
        if guess < secret_number:
            hint = '📈 Загаданное число БОЛЬШЕ'
        else:
            hint = '📉 Загаданное число МЕНЬШЕ'
        
        response.update({
            'result': 'hint',
            'message': hint
        })
    
    return jsonify(response)

@app.route('/new_game', methods=['POST'])
def new_game():
    """Начинает новую игру"""
    difficulty = request.form.get('difficulty', 'medium')
    
    if difficulty == 'easy':
        session['max_attempts'] = 10
        session['secret_number'] = random.randint(1, 50)
    elif difficulty == 'hard':
        session['max_attempts'] = 5
        session['secret_number'] = random.randint(1, 200)
    else:  # medium
        session['max_attempts'] = 7
        session['secret_number'] = random.randint(1, 100)
    
    session['attempts'] = 0
    session['game_over'] = False
    
    # Обновляем имя если нужно
    new_name = request.form.get('player_name')
    if new_name:
        session['player_name'] = new_name
    
    return jsonify({
        'message': f'🎮 Новая игра начата! Угадай число от 1 до {100 if difficulty == "medium" else (50 if difficulty == "easy" else 200)}',
        'max_attempts': session['max_attempts'],
        'player_name': session['player_name']
    })

@app.route('/stats')
def get_stats():
    """Возвращает статистику"""
    return jsonify(game_manager.stats)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)