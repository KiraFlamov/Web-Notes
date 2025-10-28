from flask import Flask, render_template, request, redirect, url_for
import json
from datetime import datetime

app = Flask(__name__)

def load_notes():
    try:
        with open('notes.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_notes(notes):
    with open('notes.json', 'w', encoding='utf-8') as f:
        json.dump(notes, f, ensure_ascii=False, indent=4)


@app.route("/")
def index():
    notes = load_notes()
    return render_template("index.html", notes=notes)

@app.route("/add", methods=["POST"])
def add():
    notes = load_notes()
    new_id = max([note['id'] for note in notes], default=0) + 1
    title = request.form.get("title")
    content = request.form.get("content")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notes.append({
        'id': new_id,
        'title': title,
        'content': content,
        'created': now,
        'updated': now
    })
    save_notes(notes)
    return redirect(url_for("index"))

@app.route("/delete/<int:note_id>", methods=["POST"])
def delete(note_id):
    """Удаление заметки по ID"""
    notes = load_notes()
    new_notes = [note for note in notes if note['id'] != note_id]
    save_notes(new_notes)
    return redirect(url_for("index"))

@app.route("/edit/<int:note_id>", methods=["GET", "POST"])
def edit(note_id):
    notes = load_notes()
    note = next((n for n in notes if n["id"] == note_id), None)

    if not note:
        return "Заметка не найдена", 404

    if request.method == "POST":
        note["title"] = request.form.get("title")
        note["content"] = request.form.get("content")
        note["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_notes(notes)
        return redirect(url_for("index"))

    return render_template("edit.html", note=note)

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query", "").lower()
    notes = load_notes()
    results = [note for note in notes if query in note["title"].lower() or query in note["content"].lower()]
    return render_template("index.html", notes=results, search=True, query=request.args.get("query", ""), number_of_queries = len(results))

if __name__ == "__main__":
    app.run(debug=True)
