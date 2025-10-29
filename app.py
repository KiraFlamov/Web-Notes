from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages
#import json
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = "1"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///notes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created = db.Column(db.String(50))
    updated = db.Column(db.String(50))





@app.route("/")
def index():
    sort_order = request.args.get("sort", "asc")  # получаем параметр сортировки, по умолчанию "asc"
    notes = Note.query.order_by(Note.updated.desc() if sort_order == "desc" else Note.updated.asc()).all()
    return render_template("index.html", notes=notes, sort_order=sort_order)

@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title")
    content = request.form.get("content")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_note = Note(title=title, content=content, created=now, updated=now)
    db.session.add(new_note)
    db.session.commit()
    flash("Заметка успешно сохранена!")
    return redirect(url_for("index"))

@app.route("/delete/<int:note_id>", methods=["POST"])
def delete(note_id):
    note = Note.query.get(note_id)
    if note:
        db.session.delete(note)
        db.session.commit()
        flash("Заметка удалена!")
    flash('Заметка удалена!')
    return redirect(url_for("index"))

@app.route("/edit/<int:note_id>", methods=["GET", "POST"])
def edit(note_id):
    note = Note.query.get(note_id)
    if not note:
        return "Заметка не найдена", 404

    if request.method == "POST":
        note.title = request.form.get("title")
        note.content = request.form.get("content")
        note.updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.session.commit()
        flash("Заметка успешно сохранена!")
        return redirect(url_for("index"))

    return render_template("edit.html", note=note)

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query", "").lower()
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


if __name__ == "__main__":
    app.run(debug=True)
