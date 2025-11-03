from flask import Flask, render_template, request, redirect, url_for, flash, abort
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
import os
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.secret_key = "secret_key_wow"
csrf = CSRFProtect(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'  # Если неавторизованный пользователь попытается попасть на защищённую страницу — его перекинет на /login
login_manager.init_app(app)
login_manager.login_message = None #чтобы при переходе не было уведомления Please log in to access this page.


# Создаём папку для логов, если её нет
if not os.path.exists('logs'):
    os.mkdir('logs')


# Установим уровень логирования для app.logger
app.logger.setLevel(logging.INFO)

# Настройка RotatingFileHandler — лог с ротацией, чтобы файл не рос бесконечно
file_handler = RotatingFileHandler('logs/app.log', maxBytes=1024*1024, backupCount=3)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)

# Логируем запуск приложения
app.logger.info(f"Приложение запущено в debug={app.debug}")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created = db.Column(db.String(50), nullable=False)
    updated = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
@login_required
def index():
    sort_order = request.args.get("sort", "asc")  # получаем параметр сортировки, по умолчанию "asc"
    notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.updated.desc() if sort_order == "desc" else Note.updated.asc()).all()
    return render_template("index.html", notes=notes, sort_order=sort_order, user=current_user)

@app.route("/add", methods=["POST"])
@login_required
def add():
    title = request.form.get("title")
    content = request.form.get("content")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_note = Note(title=title, content=content, created=now, updated=now, user_id=current_user.id)
    db.session.add(new_note)
    db.session.commit()
    flash("Заметка успешно сохранена!")
    app.logger.info(f"User '{current_user.username}' создал заметку '{title}'")
    return redirect(url_for("index"))

@app.route("/delete/<int:note_id>", methods=["POST"])
@login_required
def delete(note_id):
    note = Note.query.get(note_id)
    if not note or note.user_id != current_user.id:
        abort(403)

    db.session.delete(note)
    db.session.commit()
    flash("Заметка удалена!")
    app.logger.info(f"User '{current_user.username}' удалил заметку '{note.title}' (ID {note.id})")
    return redirect(url_for("index"))

@app.route("/edit/<int:note_id>", methods=["GET", "POST"])
@login_required
def edit(note_id):
    note = Note.query.get(note_id)

    if not note or note.user_id != current_user.id:
        abort(403)

    if request.method == "POST":
        note.title = request.form.get("title")
        note.content = request.form.get("content")
        note.updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.session.commit()
        flash("Заметка успешно сохранена!")
        app.logger.info(f"User '{current_user.username}' отредактировал заметку '{note.title}' (ID {note.id})")
        return redirect(url_for("index"))

    return render_template("edit.html", note=note)

@app.route("/search", methods=["GET"])
@login_required
def search():
    query = request.args.get("query", "")
    sort_order = request.args.get("sort", "asc")  # добавляем параметр сортировки

    # фильтрация по заголовку и содержимому
    notes = Note.query.filter(
        (Note.title.ilike(f"%{query}%")) | (Note.content.ilike(f"%{query}%"))
    )

    # сортировка по дате
    if sort_order == "desc":
        notes = notes.order_by(Note.updated.desc())
    else:
        notes = notes.order_by(Note.updated.asc())

    notes = notes.all()

    return render_template(
        "index.html",
        notes=notes,
        search=True,
        query=request.args.get("query", ""),
        sort_order=sort_order,
        number_of_queries=len(notes)
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if User.query.filter_by(username=username).first():
            flash("Такой пользователь уже существует!")
            return redirect(url_for("register"))

        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Регистрация успешна! Теперь войдите.")
        app.logger.info(f"User '{username}' зарегистрировался, IP={request.remote_addr}")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash("Неверное имя пользователя или пароль")
            return redirect(url_for("login"))

        login_user(user)
        flash(f"Вход успешно произведен!")
        app.logger.info(f"User '{user.username}' вошёл в систему, IP={request.remote_addr}")
        return redirect(url_for("index"))

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    app.logger.info(f"User '{current_user.username}' вышел из системы")
    logout_user()
    return redirect(url_for("login"))


#обработка и логирование ошибок
@app.errorhandler(403)
def forbidden(e):
    username = getattr(current_user, "username", "Anonymous")
    app.logger.error(f"403 Forbidden - User '{username}' попытался зайти на {request.path}")
    flash("Доступ запрещён")
    return redirect(url_for("index"))

@app.errorhandler(404)
def page_not_found(e):
    username = getattr(current_user, "username", "Anonymous")
    app.logger.error(f"404 Not Found - User '{username}' попытался зайти на {request.path}")
    flash("Страница не найдена!")
    return redirect(url_for("index"))

@app.errorhandler(405)
def method_not_allowed(e):
    username = getattr(current_user, "username", "Anonymous")
    app.logger.error(f"405 Method Not Allowed - User '{username}' попытался вызвать {request.path} с неверным методом")
    flash("Метод запроса не разрешён")
    return redirect(url_for("index"))

@app.errorhandler(500)
def internal_error(e):
    username = getattr(current_user, "username", "Anonymous")
    app.logger.error(f"500 Internal Server Error - User '{username}' вызвал ошибку на {request.path}: {str(e)}")
    flash("Произошла внутренняя ошибка сервера. Попробуйте позже.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = 5000, debug=False)