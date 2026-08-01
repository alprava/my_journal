import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from functools import wraps

app = Flask(__name__)
app.secret_key = 'supersecretkey'

def get_db():
    db = sqlite3.connect('progress.db')
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL, teacher_id INTEGER)')
    cursor.execute('CREATE TABLE IF NOT EXISTS students (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE NOT NULL, full_name TEXT NOT NULL, teacher_id INTEGER, FOREIGN KEY (user_id) REFERENCES users (id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS blocks (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS topics (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, block_id INTEGER NOT NULL, FOREIGN KEY (block_id) REFERENCES blocks (id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS lessons (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, date TEXT NOT NULL, topic_id INTEGER NOT NULL, subtopic TEXT, module_id INTEGER, grade_lesson INTEGER, grade_homework INTEGER, homework_desc TEXT, comment_lesson TEXT, comment_homework TEXT, payment_status TEXT DEFAULT "Не оплачено", plan_id INTEGER, format TEXT DEFAULT "Очно", link_call TEXT, link_board TEXT, address TEXT, teacher_id INTEGER, FOREIGN KEY (student_id) REFERENCES students (id), FOREIGN KEY (topic_id) REFERENCES topics (id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS plans (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, topic_id INTEGER NOT NULL, order_num INTEGER NOT NULL, status TEXT DEFAULT "pending", format TEXT DEFAULT "Очно", link_call TEXT, link_board TEXT, address TEXT, teacher_id INTEGER, teacher_note TEXT, FOREIGN KEY (student_id) REFERENCES students (id), FOREIGN KEY (topic_id) REFERENCES topics (id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS modules (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, name TEXT NOT NULL, color TEXT DEFAULT "#4f8ea7", order_num INTEGER NOT NULL, start_date TEXT, end_date TEXT, teacher_id INTEGER, FOREIGN KEY (student_id) REFERENCES students (id))')
    cursor.execute('CREATE TABLE IF NOT EXISTS recommendations (id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, text TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, teacher_id INTEGER, FOREIGN KEY (student_id) REFERENCES students (id))')
    
    cursor.execute("SELECT * FROM users WHERE username='teacher'")
    if not cursor.fetchone():
        # ВОТ ТУТ ИЗМЕНЕНИЕ:
        from werkzeug.security import generate_password_hash
        hashed_password = generate_password_hash('123')
        cursor.execute("INSERT INTO users (username, password, role, teacher_id) VALUES ('teacher', ?, 'teacher', 1)", (hashed_password,))
    
    cursor.execute("SELECT * FROM blocks")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO blocks (name) VALUES ('Механика')")
        cursor.execute("INSERT INTO blocks (name) VALUES ('Термодинамика')")
        cursor.execute("INSERT INTO blocks (name) VALUES ('Электричество')")
        cursor.execute("INSERT INTO blocks (name) VALUES ('Оптика')")
        
        cursor.execute("INSERT INTO topics (name, block_id) VALUES ('Кинематика', 1)")
        cursor.execute("INSERT INTO topics (name, block_id) VALUES ('Законы Ньютона', 1)")
        cursor.execute("INSERT INTO topics (name, block_id) VALUES ('Работа и энергия', 1)")
        cursor.execute("INSERT INTO topics (name, block_id) VALUES ('Импульс', 1)")
        cursor.execute("INSERT INTO topics (name, block_id) VALUES ('Основы термодинамики', 2)")
        cursor.execute("INSERT INTO topics (name, block_id) VALUES ('Газовые законы', 2)")
        cursor.execute("INSERT INTO topics (name, block_id) VALUES ('Электростатика', 3)")
        cursor.execute("INSERT INTO topics (name, block_id) VALUES ('Электрический ток', 3)")
    
    db.commit()
    db.close()

def login_required(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                return "Доступ запрещен", 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
if user and check_password_hash(user['password'], password):
    # вход разрешён
else:
    flash('Неверный логин или пароль')
        db.close()
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['username'] = user['username']
            if user['role'] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add_student', methods=['POST'])
def add_student():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    full_name = request.form['full_name']
    username = request.form['username']
    password = request.form['password']
    teacher_id = session['user_id']
    db = get_db()
    try:
        cursor = db.cursor()
        hashed_password = generate_password_hash(password)
cursor.execute("INSERT INTO users (username, password, role, teacher_id) VALUES (?, ?, 'student', ?)", 
               (username, hashed_password, teacher_id))
        cursor.execute("INSERT INTO students (user_id, full_name, teacher_id) VALUES (?, ?, ?)", (user_id, full_name, teacher_id))
        db.commit()
        flash('Ученик добавлен!')
    except sqlite3.IntegrityError:
        flash('Пользователь с таким логином уже существует')
    db.close()
    return redirect(url_for('teacher_dashboard'))

@app.route('/student')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    db = get_db()
    user_id = session['user_id']
    student = db.execute("SELECT * FROM students WHERE user_id=?", (user_id,)).fetchone()
    if not student:
        return "Ученик не найден"
    from datetime import datetime, timedelta
    today = datetime.now().date()
    rows = db.execute("""
        SELECT lessons.*, topics.name as topic_name, blocks.name as block_name 
        FROM lessons 
        JOIN topics ON lessons.topic_id = topics.id 
        JOIN blocks ON topics.block_id = blocks.id 
        WHERE lessons.student_id=? 
        ORDER BY lessons.date DESC
    """, (student['id'],)).fetchall()
    lessons = []
    months = set()
    for row in rows:
        lesson = dict(row)
        lesson['date_obj'] = datetime.strptime(lesson['date'], '%Y-%m-%d').date()
        month_key = lesson['date_obj'].strftime('%Y-%m')
        months.add(month_key)
        lessons.append(lesson)
    months = sorted(list(months), reverse=True)
    total_grade = 0
    grade_count = 0
    for l in lessons:
        if l.get('grade_lesson'):
            total_grade += l['grade_lesson']
            grade_count += 1
    overall_avg = round(total_grade / grade_count, 1) if grade_count > 0 else 0
    blocks_stats = {}
    for l in lessons:
        block = l.get('block_name', 'Без блока')
        if block not in blocks_stats:
            blocks_stats[block] = {'grades': [], 'dates': [], 'avg': 0, 'count': 0}
        if l.get('grade_lesson'):
            blocks_stats[block]['grades'].append(l['grade_lesson'])
            blocks_stats[block]['dates'].append(l['date'])
            blocks_stats[block]['count'] += 1
    for block, data in blocks_stats.items():
        sorted_data = sorted(zip(data['dates'], data['grades']), key=lambda x: x[0])
        data['dates'] = [d for d, g in sorted_data]
        data['grades'] = [g for d, g in sorted_data]
        if data['count'] > 0:
            data['avg'] = round(sum(data['grades']) / data['count'], 1)
    recommendations = db.execute("SELECT * FROM recommendations WHERE student_id=? ORDER BY created_at DESC", (student['id'],)).fetchall()
    db.close()
    return render_template('student_dashboard.html', 
                           student=student, 
                           lessons=lessons, 
                           today=today, 
                           timedelta=timedelta,
                           months=months,
                           overall_avg=overall_avg,
                           blocks_stats=blocks_stats,
                           recommendations=recommendations)

@app.route('/teacher')
def teacher_dashboard():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    teacher_id = session['user_id']
    db = get_db()
    students = db.execute("SELECT * FROM students WHERE teacher_id=?", (teacher_id,)).fetchall()
    blocks = db.execute("SELECT * FROM blocks").fetchall()
    topics = db.execute("SELECT * FROM topics").fetchall()
    lessons = db.execute("""
        SELECT lessons.*, topics.name as topic_name 
        FROM lessons 
        JOIN topics ON lessons.topic_id = topics.id 
        WHERE lessons.teacher_id=?
        ORDER BY lessons.date DESC
    """, (teacher_id,)).fetchall()
    plans = db.execute("""
        SELECT plans.*, topics.name as topic_name, students.full_name as student_name
        FROM plans 
        JOIN topics ON plans.topic_id = topics.id
        JOIN students ON plans.student_id = students.id
        WHERE plans.teacher_id=?
        ORDER BY plans.student_id, plans.order_num
    """, (teacher_id,)).fetchall()
    db.close()
    return render_template('teacher_dashboard.html', 
                           students=students, 
                           blocks=blocks, 
                           topics=topics, 
                           lessons=lessons,
                           plans=plans)

@app.route('/add_lesson', methods=['POST'])
def add_lesson():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    teacher_id = session['user_id']
    student_id = request.form['student_id']
    date = request.form['date']
    topic_id = request.form['topic_id']
    subtopic = request.form['subtopic']
    grade_lesson = request.form.get('grade_lesson', type=int)
    grade_homework = request.form.get('grade_homework', type=int)
    homework_desc = request.form['homework_desc']
    comment_lesson = request.form['comment_lesson']
    comment_homework = request.form.get('comment_homework', '')
    payment_status = request.form.get('payment_status_hidden', 'Не оплачено')
    plan_id = request.form.get('plan_id')
    if plan_id == '':
        plan_id = None
    format_type = request.form.get('format', 'Очно')
    link_call = request.form.get('link_call', '')
    link_board = request.form.get('link_board', '')
    address = request.form.get('address', '')
    db = get_db()
    db.execute("""
        INSERT INTO lessons 
        (student_id, date, topic_id, subtopic, grade_lesson, grade_homework, homework_desc, comment_lesson, comment_homework, payment_status, plan_id, format, link_call, link_board, address, teacher_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_id, date, topic_id, subtopic, grade_lesson, grade_homework, homework_desc, comment_lesson, comment_homework, payment_status, plan_id, format_type, link_call, link_board, address, teacher_id))
    db.commit()
    db.close()
    flash('Занятие добавлено!')
    return redirect(url_for('teacher_dashboard'))

@app.route('/student_plan/<int:student_id>')
def student_plan(student_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    teacher_id = session['user_id']
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=? AND teacher_id=?", (student_id, teacher_id)).fetchone()
    if not student:
        return "Ученик не найден", 404
    all_topics = db.execute("SELECT topics.*, blocks.name as block_name FROM topics JOIN blocks ON topics.block_id = blocks.id ORDER BY blocks.name, topics.name").fetchall()
    plan = db.execute("""
        SELECT plans.*, topics.name as topic_name, blocks.name as block_name
        FROM plans
        JOIN topics ON plans.topic_id = topics.id
        JOIN blocks ON topics.block_id = blocks.id
        WHERE plans.student_id=? AND plans.teacher_id=?
        ORDER BY plans.order_num
    """, (student_id, teacher_id)).fetchall()
    lessons = db.execute("""
        SELECT lessons.*, topics.name as topic_name
        FROM lessons
        JOIN topics ON lessons.topic_id = topics.id
        WHERE lessons.student_id=? AND lessons.teacher_id=?
    """, (student_id, teacher_id)).fetchall()
    modules = db.execute("SELECT * FROM modules WHERE student_id=? AND teacher_id=? ORDER BY order_num", (student_id, teacher_id)).fetchall()
    db.close()
    return render_template('student_plan.html', student=student, all_topics=all_topics, plan=plan, lessons=lessons, modules=modules)

@app.route('/add_to_plan', methods=['POST'])
def add_to_plan():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    teacher_id = session['user_id']
    student_id = request.form['student_id']
    topic_id = request.form['topic_id']
    format_type = request.form.get('format', 'Очно')
    link_call = request.form.get('link_call', '')
    link_board = request.form.get('link_board', '')
    address = request.form.get('address', '')
    teacher_note = request.form.get('teacher_note', '')
    db = get_db()
    max_order = db.execute("SELECT MAX(order_num) as max FROM plans WHERE student_id=?", (student_id,)).fetchone()['max']
    next_order = 0 if max_order is None else max_order + 1
    db.execute("""
        INSERT INTO plans (student_id, topic_id, order_num, format, link_call, link_board, address, teacher_id, teacher_note) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_id, topic_id, next_order, format_type, link_call, link_board, address, teacher_id, teacher_note))
    db.commit()
    db.close()
    flash('Тема добавлена в план!')
    return redirect(url_for('student_plan', student_id=student_id))

@app.route('/remove_from_plan', methods=['POST'])
def remove_from_plan():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    plan_id = request.form['plan_id']
    student_id = request.form['student_id']
    db = get_db()
    db.execute("DELETE FROM plans WHERE id=?", (plan_id,))
    db.commit()
    db.close()
    flash('Тема удалена из плана!')
    return redirect(url_for('student_plan', student_id=student_id))

@app.route('/topic_bank')
def topic_bank():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    db = get_db()
    blocks = db.execute("SELECT * FROM blocks ORDER BY name").fetchall()
    topics = db.execute("SELECT topics.*, blocks.name as block_name FROM topics JOIN blocks ON topics.block_id = blocks.id ORDER BY blocks.name, topics.name").fetchall()
    db.close()
    return render_template('topic_bank.html', blocks=blocks, topics=topics)

@app.route('/add_topic', methods=['POST'])
def add_topic():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    name = request.form['name']
    block_id = request.form['block_id']
    db = get_db()
    db.execute("INSERT INTO topics (name, block_id) VALUES (?, ?)", (name, block_id))
    db.commit()
    db.close()
    flash('Тема добавлена!')
    return redirect(url_for('topic_bank'))

@app.route('/delete_topic', methods=['POST'])
def delete_topic():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    topic_id = request.form['topic_id']
    db = get_db()
    db.execute("DELETE FROM topics WHERE id=?", (topic_id,))
    db.commit()
    db.close()
    flash('Тема удалена!')
    return redirect(url_for('topic_bank'))

@app.route('/add_block', methods=['POST'])
def add_block():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    name = request.form['name']
    db = get_db()
    db.execute("INSERT INTO blocks (name) VALUES (?)", (name,))
    db.commit()
    db.close()
    flash('Раздел добавлен!')
    return redirect(url_for('topic_bank'))

@app.route('/delete_block', methods=['POST'])
def delete_block():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    block_id = request.form['block_id']
    db = get_db()
    db.execute("DELETE FROM blocks WHERE id=?", (block_id,))
    db.commit()
    db.close()
    flash('Раздел удалён!')
    return redirect(url_for('topic_bank'))

@app.route('/add_module', methods=['POST'])
def add_module():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    teacher_id = session['user_id']
    student_id = request.form['student_id']
    name = request.form['module_name']
    color = request.form.get('module_color', '#4f8ea7')
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    db = get_db()
    max_order = db.execute("SELECT MAX(order_num) as max FROM modules WHERE student_id=?", (student_id,)).fetchone()['max']
    next_order = 0 if max_order is None else max_order + 1
    db.execute("INSERT INTO modules (student_id, name, color, order_num, start_date, end_date, teacher_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
               (student_id, name, color, next_order, start_date, end_date, teacher_id))
    db.commit()
    db.close()
    flash('Блок создан!')
    return redirect(url_for('student_plan', student_id=student_id))

@app.route('/delete_module', methods=['POST'])
def delete_module():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    module_id = request.form['module_id']
    student_id = request.form['student_id']
    db = get_db()
    db.execute("DELETE FROM modules WHERE id=?", (module_id,))
    db.commit()
    db.close()
    flash('Блок удалён!')
    return redirect(url_for('student_plan', student_id=student_id))

@app.route('/add_lesson_to_module', methods=['POST'])
def add_lesson_to_module():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    teacher_id = session['user_id']
    student_id = request.form['student_id']
    module_id = request.form['module_id']
    date = request.form['date']
    topic_id = request.form['topic_id']
    subtopic = request.form.get('subtopic', '')
    format_type = request.form.get('format', 'Очно')
    link_call = request.form.get('link_call', '')
    link_board = request.form.get('link_board', '')
    address = request.form.get('address', '')
    teacher_note = request.form.get('teacher_note', '')
    db = get_db()
    db.execute("""
        INSERT INTO lessons 
        (student_id, date, topic_id, subtopic, module_id, format, link_call, link_board, address, teacher_id, teacher_note) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (student_id, date, topic_id, subtopic, module_id, format_type, link_call, link_board, address, teacher_id, teacher_note))
    db.commit()
    db.close()
    flash('Занятие добавлено в блок!')
    return redirect(url_for('student_plan', student_id=student_id))

@app.route('/remove_lesson_from_module', methods=['POST'])
def remove_lesson_from_module():
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    lesson_id = request.form['lesson_id']
    student_id = request.form['student_id']
    db = get_db()
    db.execute("DELETE FROM lessons WHERE id=?", (lesson_id,))
    db.commit()
    db.close()
    flash('Занятие удалено!')
    return redirect(url_for('student_plan', student_id=student_id))

@app.route('/student_stats/<int:student_id>')
def student_stats(student_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    teacher_id = session['user_id']
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=? AND teacher_id=?", (student_id, teacher_id)).fetchone()
    if not student:
        return "Ученик не найден", 404
    rows = db.execute("""
        SELECT lessons.*, topics.name as topic_name, blocks.name as block_name 
        FROM lessons 
        JOIN topics ON lessons.topic_id = topics.id 
        JOIN blocks ON topics.block_id = blocks.id 
        WHERE lessons.student_id=? AND lessons.teacher_id=?
        ORDER BY lessons.date DESC
    """, (student_id, teacher_id)).fetchall()
    from datetime import datetime, timedelta
    today = datetime.now().date()
    lessons = []
    months = set()
    for row in rows:
        lesson = dict(row)
        lesson['date_obj'] = datetime.strptime(lesson['date'], '%Y-%m-%d').date()
        month_key = lesson['date_obj'].strftime('%Y-%m')
        months.add(month_key)
        lessons.append(lesson)
    months = sorted(list(months), reverse=True)
    total_grade = 0
    grade_count = 0
    for l in lessons:
        if l.get('grade_lesson'):
            total_grade += l['grade_lesson']
            grade_count += 1
    overall_avg = round(total_grade / grade_count, 1) if grade_count > 0 else 0
    blocks_stats = {}
    for l in lessons:
        block = l.get('block_name', 'Без блока')
        if block not in blocks_stats:
            blocks_stats[block] = {'grades': [], 'dates': [], 'avg': 0, 'count': 0}
        if l.get('grade_lesson'):
            blocks_stats[block]['grades'].append(l['grade_lesson'])
            blocks_stats[block]['dates'].append(l['date'])
            blocks_stats[block]['count'] += 1
    for block, data in blocks_stats.items():
        sorted_data = sorted(zip(data['dates'], data['grades']), key=lambda x: x[0])
        data['dates'] = [d for d, g in sorted_data]
        data['grades'] = [g for d, g in sorted_data]
        if data['count'] > 0:
            data['avg'] = round(sum(data['grades']) / data['count'], 1)
    recommendations = db.execute("SELECT * FROM recommendations WHERE student_id=? ORDER BY created_at DESC", (student_id,)).fetchall()
    db.close()
    return render_template('student_stats.html', 
                           student=student, 
                           lessons=lessons, 
                           today=today, 
                           timedelta=timedelta,
                           months=months,
                           overall_avg=overall_avg,
                           blocks_stats=blocks_stats,
                           recommendations=recommendations)

@app.route('/add_recommendation/<int:student_id>', methods=['POST'])
def add_recommendation(student_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    teacher_id = session['user_id']
    text = request.form['text']
    if not text.strip():
        flash('Рекомендация не может быть пустой')
        return redirect(url_for('student_stats', student_id=student_id))
    db = get_db()
    db.execute("INSERT INTO recommendations (student_id, text, teacher_id) VALUES (?, ?, ?)", (student_id, text, teacher_id))
    db.commit()
    db.close()
    flash('Рекомендация добавлена!')
    return redirect(url_for('student_stats', student_id=student_id))

@app.route('/delete_recommendation/<int:rec_id>/<int:student_id>', methods=['POST'])
def delete_recommendation(rec_id, student_id):
    if 'user_id' not in session or session.get('role') != 'teacher':
        return redirect(url_for('login'))
    db = get_db()
    db.execute("DELETE FROM recommendations WHERE id=?", (rec_id,))
    db.commit()
    db.close()
    flash('Рекомендация удалена')
    return redirect(url_for('student_stats', student_id=student_id))

@app.route('/lesson_card/<int:lesson_id>')
def lesson_card(lesson_id):
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect(url_for('login'))
    user_id = session['user_id']
    db = get_db()
    lesson = db.execute("""
        SELECT lessons.*, topics.name as topic_name, blocks.name as block_name 
        FROM lessons 
        JOIN topics ON lessons.topic_id = topics.id 
        JOIN blocks ON topics.block_id = blocks.id 
        WHERE lessons.id=? AND lessons.student_id=(SELECT id FROM students WHERE user_id=?)
    """, (lesson_id, user_id)).fetchone()
    db.close()
    if not lesson:
        return "Занятие не найдено или доступ запрещён", 404
    return render_template('lesson_card.html', lesson=lesson)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=8080)

application = app
