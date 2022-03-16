#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import string
import random
from flask import Flask, render_template, redirect, make_response, jsonify, session, request
from flask_restful import Api
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room, rooms
from sqlalchemy import or_

from data import db_session
from data.users import User
from data.games import Game
from data.lobbies import Lobby
from data import game_board

from forms.user import LoginForm, RegisterForm

GAMES = {}
UPLOAD_FOLDER = 'static/img'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
socketio = SocketIO(app)

api = Api(app)

login_manager = LoginManager()
login_manager.init_app(app)


def keygen(l):
    alphabet = string.ascii_letters + string.digits
    rand_string = ''.join([random.choice(alphabet) for _ in range(l)])
    return rand_string


def get_lobbies():
    db = db_session.create_session()

    # Ищем свободные лобби
    lobbies = db.query(Lobby).filter(or_(Lobby.p1 == None, Lobby.p2 == None)).all()
    res_lobbies = []
    for lst_lobby in lobbies:
        owner_id = lst_lobby.p1
        owner_name = db.query(User).filter(User.id == owner_id).first().name
        res_lobbies.append((owner_name, lst_lobby.id))

    return list(sorted(res_lobbies))


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@login_manager.user_loader
def load_user(user_id):
    db = db_session.create_session()
    return db.query(User).get(user_id)


@app.route('/')
def index():
    db = db_session.create_session()

    if not current_user.is_authenticated:
        return redirect("/login")

    lobby = db.query(Lobby).filter(
        or_(Lobby.p1 == current_user.id, Lobby.p2 == current_user.id)).first()
    lobby_id = lobby.id if lobby else None

    lobbies = get_lobbies()
    return render_template('index.html', lobby_id=lobby_id, lobbies=list(sorted(lobbies)))


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")

        user = User(name=form.name.data,
                    email=form.email.data)
        user.set_password(form.password.data)

        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/game/<string:lobby_id>')
def game(lobby_id):
    db = db_session.create_session()
    session['lobby_id'] = lobby_id
    game_session = db.query(Game).filter(Game.lobby_id == lobby_id).first()
    if game_session:
        size = game_session.size
        GAMES[session['lobby_id']] = game_board.init_game(size)
        board_img = game_board.render_board([[' '] * size] * size, matrix=True)
        board_img.save(app.config['UPLOAD_FOLDER'] + '/' + str(session['lobby_id']) + '.png')

        players = list(map(int, game_session.players.split(";")))

        if players[0] == current_user.id:
            session["color"] = "white"
            session['enemy_name'] = db.query(User).get(players[1]).name
            return render_template('game.html', title='Игра', size=size,
                                   game_id=session['lobby_id'],
                                   white=current_user.name, black=session['enemy_name'])
        else:
            session["color"] = "black"
            session['enemy_name'] = db.query(User).get(players[0]).name
            return render_template('game.html', title='Игра', size=size,
                                   game_id=session['lobby_id'],
                                   white=session['enemy_name'], black=current_user.name)
    else:
        return redirect('/')


@socketio.on('create_lobby')
def create_lobby():
    db = db_session.create_session()

    lobby_id = keygen(16)
    while db.query(Lobby).filter(Lobby.id == lobby_id).first():
        lobby_id = keygen(16)

    lobby = Lobby(id=lobby_id,
                  p1=current_user.id)
    db.add(lobby)
    db.commit()

    join_room(lobby_id)

    lobbies = get_lobbies()

    emit('update_lobbies_list', {'lobbies': lobbies}, broadcast=True)
    emit("refresh")
    session['lobby_id'] = lobby_id


@socketio.on('leave_lobby')
def leave_lobby():
    db = db_session.create_session()

    lobby = db.query(Lobby).filter(
        or_(Lobby.p1 == current_user.id, Lobby.p2 == current_user.id)).first()
    players = [lobby.p1, lobby.p2]
    players.remove(current_user.id)
    players.append(None)
    # try:
    if players[0] or players[1]:
        [lobby.p1, lobby.p2] = players
    else:
        db.delete(lobby)
        if lobby.id in GAMES:
            del GAMES[lobby.id]
    db.commit()
    # except Exception:
    #     pass
    lobbies = get_lobbies()
    emit('update_lobbies_list', {'lobbies': lobbies}, broadcast=True)
    emit("refresh")
    emit('put_lobby_msg', {'name': current_user.name, 'msg': 'покинул лобби'}, room=lobby.id)
    leave_room(lobby.id)
    session['lobby_id'] = ''


@socketio.on('join_lobby')
def join_lobby(data):
    db = db_session.create_session()

    lobby_id = data["code"]
    lobby = db.query(Lobby).filter(Lobby.id == lobby_id).first()
    if not lobby:
        return emit("notification", {"msg": "Лобби с таким кодом не существует"})

    if lobby.p1 and lobby.p2:
        return emit("notification", {"msg": "В лобби отсутстсвуют свободные места"})

    players = [lobby.p1, lobby.p2]

    players[players.index(None)] = current_user.id
    lobby.p1, lobby.p2 = players

    db.commit()
    join_room(lobby_id)

    lobbies = get_lobbies()

    emit('update_lobbies_list', {'lobbies': lobbies}, broadcast=True)
    emit("refresh")
    emit('put_lobby_msg', {'name': current_user.name, 'msg': 'присоединился к лобби'},
         room=lobby.id)

    session['lobby_id'] = lobby.id


@socketio.on('chat_msg')
def chat_msg(data):
    db = db_session.create_session()
    lobby = db.query(Lobby).filter(
        or_(Lobby.p1 == current_user.id, Lobby.p2 == current_user.id)).first()
    msg = data["msg"]
    emit("put_msg", {"msg": msg, "name": current_user.name}, room=lobby.id)


@socketio.on('get_players')
def get_players():
    db = db_session.create_session()

    lobby = db.query(Lobby).filter(
        or_(Lobby.p1 == current_user.id, Lobby.p2 == current_user.id)).first()

    if not lobby:
        return

    p1 = db.query(User).filter(User.id == lobby.p1).first()
    p2 = db.query(User).filter(User.id == lobby.p2).first()

    p1_name = p1.name if p1 else None
    p2_name = p2.name if p2 else None

    emit("players", {"p1": p1_name, "p2": p2_name}, room=lobby.id)


@socketio.on('start_game')
def start_game():
    db = db_session.create_session()

    lobby = db.query(Lobby).filter(
        or_(Lobby.p1 == current_user.id, Lobby.p2 == current_user.id)).first()
    players = [lobby.p1, lobby.p2]

    game = Game(lobby_id=lobby.id,
                players=";".join(list(map(str, players))),
                size=19)

    db.add(game)
    db.commit()

    session['lobby_id'] = lobby.id
    if players[0] and players[1]:
        emit("game_redirect", {"id": session['lobby_id']}, room=lobby.id)
    else:
        emit("no_player", room=lobby.id)


@socketio.on('disconnect')
@socketio.on('leave_game')
def leave_game():
    db = db_session.create_session()
    lobby = db.query(Lobby).filter(
        or_(Lobby.p1 == current_user.id, Lobby.p2 == current_user.id)).first()
    try:
        game_session = db.query(Game).filter(Game.lobby_id == session['lobby_id']).all()
        for game in game_session:
            db.delete(game)
        os.remove(app.config['UPLOAD_FOLDER'] + '/' + str(session['lobby_id']) + '.png')
        db.commit()

        emit('put_lobby_msg', {'name': current_user.name, 'msg': 'покинул игру'},
             room=lobby.id)

        emit('end', {'winner': session['enemy_name']},
             room=lobby.id)
    except Exception:
        pass

    return emit('lobby_redirect')


@socketio.on('connect')
def test_connect():
    db = db_session.create_session()
    lobby = db.query(Lobby).filter(
        or_(Lobby.p1 == current_user.id, Lobby.p2 == current_user.id)).first()
    if lobby:
        join_room(lobby.id)


@socketio.on('make_move')
def move(data):
    prev_color = data["prev_color"]
    move = data['move']
    color = session["color"]
    if prev_color != color and not GAMES[session['lobby_id']]['result']:
        if move != '':
            y, x = list(map(int, move.split('-')))
            if not game_board.is_free_node(y, x, GAMES[session['lobby_id']]['board']):
                return
            GAMES[session['lobby_id']] = game_board.get_updated_game(
                GAMES[session['lobby_id']], color,
                move=(x, y))
        else:
            GAMES[session['lobby_id']] = game_board.get_updated_game(
                GAMES[session['lobby_id']], color,
                move='pass')
            emit('put_lobby_msg', {'name': current_user.name, 'msg': 'пропустил ход'},
                 room=session['lobby_id'])

        board_img = game_board.render_board(GAMES[session['lobby_id']]['board'])
        board_img.save(app.config['UPLOAD_FOLDER'] + '/' + str(session['lobby_id']) + '.png')

    if game_board.is_end_of_game(GAMES[session['lobby_id']]):
        GAMES[session['lobby_id']] = game_board.get_results(GAMES[session['lobby_id']])

    result = GAMES[session['lobby_id']]['result']
    if result:
        if result == 'end':
            return
        if result == 'draw':
            winner = ''
        elif session['color'] == result['winner']:
            winner = current_user.name
        else:
            winner = session['enemy_name']
        GAMES[session['lobby_id']]['result'] = 'end'
        return emit('end', {'winner': winner}, room=session['lobby_id'])
    return emit('moved', {'color': color, 'score': GAMES[session['lobby_id']]['score'],
                          'name': session['enemy_name'], 'game_id': session['lobby_id']},
                room=session['lobby_id'])


def main():
    db_session.global_init("db/db.db")
    port = int(os.environ.get("PORT", 80))
    socketio.run(app, host="0.0.0.0", port=port)


if __name__ == '__main__':
    main()
