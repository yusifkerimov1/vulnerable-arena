from flask import Flask, render_template, request, redirect, session, g
import sqlite3
from markupsafe import escape

app = Flask(__name__)
app.secret_key = 'ctf_secret_key'
DATABASE = 'db.sqlite3'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        next_url = request.form.get('next', '/dashboard')  # POST ilə gəlir
        username = request.form['username']
        password = request.form['password']

        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        # ✅ SQL Injection zəifliyi — istifadəçi inputu birbaşa SQL query-də istifadə olunur
        cursor = get_db().execute(query)
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            return redirect(next_url)  # ✅ Open Redirect zəifliyi
        return "Invalid credentials"

    next_url = request.args.get('next', '/dashboard')  # GET ilə gəlir
    return render_template('login.html', next=next_url)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        query = f"INSERT INTO users (username, email, password) VALUES ('{username}', '{email}', '{password}')"
        try:
            get_db().execute(query)
            get_db().commit()
            return redirect('/login')
        except Exception as e:
            return f"Error: {e}"
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return redirect(f'/profile/{session["user_id"]}')

@app.route('/redirect')
def redirect_direct():
    url = request.args.get('url')  # `url` parametri
    next_url = request.args.get('next')  # `next` parametri

    # Parametrlərdən birinin olmaması halında, redirect URL təyin edilir
    if url:
        return redirect(url)
    elif next_url:
        return redirect(next_url)
    
    return "No redirect URL provided"  # ✅ Open Redirect zəifliyi

@app.route('/profile/<int:user_id>', methods=['GET', 'POST'])
def profile(user_id):
    db = get_db()

    if request.method == 'POST':
        message = request.form['message']
        if "<script>" in message.lower() or "</script>" in message.lower():
            filtered = escape(message)
        else:
            filtered = message

        db.execute("INSERT INTO comments (user_id, message) VALUES (?, ?)", (user_id, filtered))
        db.commit()
        # ✅ Stored XSS zəifliyi — yalnız `<script>` yoxlanılır, digər payload-lar keçir
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return "User not found"

    comments = db.execute("SELECT message FROM comments WHERE user_id = ?", (user_id,)).fetchall()
    return render_template('profile.html', user=user, comments=comments)
    # ✅ IDOR zəifliyi — istifadəçi session-dəki user_id ilə uyğunluğu yoxlanmır
    
if __name__ == '__main__':
    app.run(debug=True)
