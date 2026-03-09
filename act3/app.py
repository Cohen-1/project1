import os
import sqlite3
from datetime import datetime, timedelta
from flask_login import login_required

from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'secret_key'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'forum.db')

#to let instrutor remove student
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  
    return conn


def get_db_connection():
    conn = sqlite3.connect('forum.db')
    conn.row_factory = sqlite3.Row  
    return conn


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin', 'instructor', 'student')) NOT NULL
        )
    ''')
   
    

    c.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            posted_by INTEGER,
            timestamp TEXT,
            FOREIGN KEY(posted_by) REFERENCES users(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS replies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            comment_id INTEGER,
            user_id INTEGER,
            timestamp TEXT,
            FOREIGN KEY(comment_id) REFERENCES comments(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS notification_visibility (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            notification_id INTEGER NOT NULL,
            hidden INTEGER DEFAULT 0,
            UNIQUE(user_email, notification_id),
            FOREIGN KEY(notification_id) REFERENCES notifications(id)
        )
    ''')

        
    conn.commit()
    conn.close()

def is_logged_in():
    return 'user_id' in session

def is_admin():
    return session.get('role') == 'admin'

def is_instructor():
    return session.get('role') == 'instructor'

# Helper to format "time since"
def time_since(timestamp_str):
    try:
        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        now = datetime.utcnow()
        diff = now - timestamp

        if diff < timedelta(minutes=1):
            return "Just now"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return timestamp.strftime('%B %d, %Y')
    except Exception:
        return "Unknown time"

# Register the filter for templates
app.jinja_env.filters['time_since'] = time_since

###############################################################################################
def get_current_user_email():
    return session.get('email')

def get_visible_notifications(user_email):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    query = """
    SELECT n.id, n.title, n.message, n.created_at
    FROM notifications n
    LEFT JOIN notification_visibility nv
      ON n.id = nv.notification_id AND nv.user_email = ?
    WHERE nv.hidden IS NULL OR nv.hidden = 0
    ORDER BY n.created_at DESC
    """
    c.execute(query, (user_email,))
    notifications = c.fetchall()
    conn.close()
    return notifications


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, password, role) VALUES (?, ?, ?)", (email, password, role))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already registered.', 'error')
        finally:
            conn.close()
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, role, password FROM users WHERE email=? AND role=?", (email, role))
        user = c.fetchone()
        conn.close()

        if user and user[2] == password:
            session['user_id'] = user[0]
            session['email'] = email
            session['role'] = user[1]
            
            # ✅ INSERT login log into SQLite
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("""
                INSERT INTO notifications (user_email, title, message, created_at)
                VALUES (?, ?, ?, ?)
            """, (
                email,
                'Login Success',
                f'{email} successfully logged in as {role}',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            conn.commit()
            conn.close()

            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    return render_template('login.html')




@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


#########################################################################


@app.route('/jmeter_login', methods=['GET'])
def jmeter_login():
    email = request.args.get('email')
    password = request.args.get('password')
    role = request.args.get('role')

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, role, password FROM users WHERE email=? AND role=?", (email, role))
    user = c.fetchone()
    conn.close()
    if user and user[2] == password:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO notifications (user_email, title, message, created_at) VALUES (?, ?, ?, datetime('now'))",
                  (email, 'Login Event', f'{email} logged in successfully', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        conn.close()
        return "Login successful", 200
    else:
        return "Login failed", 401



#########################################################################

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        return redirect(url_for('login'))
    role = session['role']
    user_id = session['user_id']
    email = session['email']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if role == 'student':
        c.execute("SELECT content FROM comments WHERE user_id=?", (user_id,))
        notifications = c.fetchall()
        conn.close()
        return render_template('dashboard_student.html', email=email, notifications=notifications)
    elif role == 'instructor':
        c.execute("SELECT email FROM users WHERE role='student'")
        students = c.fetchall()
        students_by_subject = {
            'Subject A': [s[0] for i, s in enumerate(students) if i % 2 == 0],
            'Subject B': [s[0] for i, s in enumerate(students) if i % 2 != 0]
        }
        conn.close()
        return render_template('dashboard_instructor.html', email=email, students_by_subject=students_by_subject)
    elif role == 'admin':
        c.execute("SELECT id, email FROM users WHERE role='student'")
        students = c.fetchall()
        c.execute("SELECT id, email FROM users WHERE role='instructor'")
        instructors = c.fetchall()
        conn.close()
        return render_template('dashboard_admin.html', email=email, students=students, instructors=instructors)
    conn.close()
    return "Invalid role."



@app.route('/dashboard_instructor')
def dashboard_instructor():
    if not is_logged_in() or not is_instructor():
        flash("Unauthorized access", "error")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Fetch all students (you can adjust this query if you want only students related to this instructor)
    c.execute('SELECT email FROM users WHERE role = "student"')
    students = [row[0] for row in c.fetchall()]

    conn.close()

    # Pass students as a simple list, no subjects involved
    return render_template('dashboard_instructor.html', email=session.get('email'), students=students)



@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not is_logged_in() or not is_admin():
        flash("Unauthorized action.", "error")
        return redirect(url_for('login'))
    if user_id == session['user_id']:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for('dashboard'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    flash("User deleted successfully.", "success")
    return redirect(url_for('dashboard'))



@app.route('/forum')
def forum():
    if not is_logged_in():
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT topics.id, topics.title, users.email 
        FROM topics 
        JOIN users ON topics.user_id = users.id
        ORDER BY topics.id DESC
    ''')
    topics = c.fetchall()
    conn.close()
    return render_template('forum.html', topics=topics)




@app.route('/forum/new', methods=['GET', 'POST'])
def new_topic():
    if not is_logged_in():
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()
        if not title:
            flash("Title is required.", "error")
            return redirect(url_for('new_topic'))
        user_id = session['user_id']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO topics (title, description, user_id) VALUES (?, ?, ?)",
                  (title, description, user_id))
        conn.commit()
        conn.close()
        flash("Topic created!", "success")
        return redirect(url_for('forum'))
    return render_template('new_topic.html')




@app.route('/forum/topic/<int:topic_id>', methods=['GET', 'POST'])
def topic(topic_id):
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 1) Fetch raw tuple: (id, title, description, email)
    c.execute('''
        SELECT topics.id, topics.title, topics.description, users.email 
        FROM topics 
        JOIN users ON topics.user_id = users.id 
        WHERE topics.id=?
    ''', (topic_id,))
    row = c.fetchone()

    # 2) If not found, bail out
    if not row:
        conn.close()
        flash("Topic not found.", "error")
        return redirect(url_for('forum'))

    # 3) Unpack into a dict so template can use topic.id, topic.title, etc.
    topic = {
        'id':          row[0],
        'title':       row[1],
        'description': row[2],
        'email':       row[3],
    }

    # Handle new comment POST
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content:
            flash("Comment content cannot be empty.", "error")
            return redirect(url_for('topic', topic_id=topic_id))
        user_id   = session['user_id']
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        c.execute(
            "INSERT INTO comments (content, topic_id, user_id, timestamp) VALUES (?, ?, ?, ?)",
            (content, topic_id, user_id, timestamp)
        )
        conn.commit()
        flash("Comment added!", "success")
        return redirect(url_for('topic', topic_id=topic_id))

    # Fetch comments as before...
    c.execute('''
        SELECT comments.id, comments.content, comments.timestamp, users.email
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.topic_id=?
        ORDER BY comments.timestamp ASC
    ''', (topic_id,))
    comments_raw = c.fetchall()

    comments = []
    for cid, content, timestamp, email in comments_raw:
        comments.append({
            'id':         cid,
            'content':    content,
            'time_since': time_since(timestamp),
            'email':      email
        })

    # Fetch replies as before...
    c.execute('''
        SELECT replies.id, replies.content, replies.timestamp, replies.comment_id, users.email
        FROM replies
        JOIN users ON replies.user_id = users.id
        WHERE replies.comment_id IN (
            SELECT id FROM comments WHERE topic_id=?
        )
        ORDER BY replies.timestamp ASC
    ''', (topic_id,))
    replies_raw = c.fetchall()
    conn.close()

    replies_by_comment = {}
    for rid, content, timestamp, comment_id, email in replies_raw:
        replies_by_comment.setdefault(comment_id, []).append({
            'id':         rid,
            'content':    content,
            'time_since': time_since(timestamp),
            'email':      email
        })

    # Pass the dict 'topic' and lists of dicts into the template
    return render_template(
        'topic.html',
        topic=topic,
        comments=comments,
        replies_by_comment=replies_by_comment
    )


@app.route('/delete_topic/<int:topic_id>', methods=['POST'])
@login_required
def delete_topic(topic_id):
    conn = get_db_connection()
    topic = conn.execute('SELECT * FROM topics WHERE id = ?', (topic_id,)).fetchone()

    if topic is None:
        flash('Topic not found.')
        conn.close()
        return redirect(url_for('forum'))

    if topic['author'] != session['username']:
        flash('You are not authorized to delete this topic.')
        conn.close()
        return redirect(url_for('forum'))

    conn.execute('DELETE FROM topics WHERE id = ?', (topic_id,))
    conn.commit()
    conn.close()

    flash('Topic deleted successfully.')
    return redirect(url_for('forum'))


@app.route('/announcement', methods=['GET', 'POST'])
def announcement():
    if not is_logged_in():
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if request.method == 'POST':
        if not is_instructor():
            flash("Only instructors can post announcements.", "error")
            return redirect(url_for('announcement'))

        content = request.form['content'].strip()
        if not content:
            flash("Announcement content cannot be empty.", "error")
            return redirect(url_for('announcement'))

        posted_by = session['user_id']
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        c.execute("INSERT INTO announcements (content, posted_by, timestamp) VALUES (?, ?, ?)",
                  (content, posted_by, timestamp))
        conn.commit()
        flash("Announcement posted!", "success")

    # Get announcements
    c.execute('''
        SELECT announcements.id, announcements.content, announcements.timestamp, users.email, announcements.posted_by
        FROM announcements
        JOIN users ON announcements.posted_by = users.id
        ORDER BY announcements.timestamp DESC
    ''')
    announcements_raw = c.fetchall()
    conn.close()

    announcements = [{
        'id': aid,
        'content': content,
        'time_since': time_since(timestamp),
        'email': email,
        'posted_by': posted_by
    } for aid, content, timestamp, email, posted_by in announcements_raw]

    return render_template('announcement.html', announcements=announcements)





@app.route('/forum/add_reply', methods=['POST'])
def add_reply():
    if not is_logged_in():
        return redirect(url_for('login'))

    content = request.form.get('reply_content', '').strip()
    comment_id = request.form.get('comment_id')
    topic_id = request.form.get('topic_id')

    # Validate content
    if not content:
        flash("Reply content cannot be empty.", "error")
        return redirect(url_for('topic', topic_id=topic_id or 0))

    # Validate comment_id and topic_id as integers
    try:
        comment_id = int(comment_id)
        topic_id = int(topic_id)
    except (TypeError, ValueError):
        flash("Invalid comment or topic ID.", "error")
        return redirect(url_for('forum'))

    user_id = session.get('user_id')
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO replies (content, comment_id, user_id, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (content, comment_id, user_id, timestamp)
        )
        conn.commit()
    except Exception as e:
        flash(f"An error occurred while adding reply: {e}", "error")
    finally:
        conn.close()

    flash("Reply added!", "success")
    return redirect(url_for('topic', topic_id=topic_id))


#####################################################################
@app.route('/edit_comment', methods=['POST'])
def edit_comment():
    comment_id = request.form.get('comment_id')
    new_content = request.form.get('edited_content', '').strip()

    if not new_content:
        flash("Comment content cannot be empty.", "error")
        return redirect(request.referrer)

    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to edit a comment.", "error")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT user_id FROM comments WHERE id = ?", (comment_id,))
    result = c.fetchone()
    if not result or result[0] != user_id:
        conn.close()
        flash("Unauthorized to edit this comment.", "error")
        return redirect(request.referrer)

    c.execute("UPDATE comments SET content = ? WHERE id = ?", (new_content, comment_id))
    conn.commit()
    conn.close()
    flash("Comment updated successfully.", "success")
    return redirect(request.referrer)



@app.route('/edit_reply', methods=['POST'])
def edit_reply():
    reply_id = request.form.get('reply_id')
    new_content = request.form.get('edited_content', '').strip()

    if not new_content:
        flash("Reply content cannot be empty.", "error")
        return redirect(request.referrer or url_for('forum'))

    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to edit a reply.", "error")
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT user_id FROM replies WHERE id = ?", (reply_id,))
    row = c.fetchone()
    if not row or row[0] != user_id:
        conn.close()
        flash("Unauthorized to edit this reply.", "error")
        return redirect(request.referrer or url_for('forum'))

    c.execute("UPDATE replies SET content = ? WHERE id = ?", (new_content, reply_id))
    conn.commit()
    conn.close()
    flash("Reply updated successfully.", "success")
    return redirect(request.referrer or url_for('forum'))





#####################################################################
@app.route('/notifications')
def notifications():
    if not is_logged_in():
        flash("Please log in.", "error")
        return redirect(url_for('login'))

    user_email = get_current_user_email()
    notifications = get_visible_notifications(user_email)
    return render_template('notifications.html', notifications=notifications)

@app.route('/hide_notification', methods=['POST'])
def hide_notification():
    if not is_logged_in():
        flash("Please log in.", "error")
        return redirect(url_for('login'))

    user_email = get_current_user_email()
    notification_id = request.form.get('notification_id')

    if not notification_id:
        flash("Invalid notification.", "error")
        return redirect(request.referrer or url_for('notifications'))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Check if entry exists
    c.execute('SELECT id FROM notification_visibility WHERE user_email = ? AND notification_id = ?', (user_email, notification_id))
    existing = c.fetchone()

    if existing:
        c.execute('UPDATE notification_visibility SET hidden = 1 WHERE id = ?', (existing[0],))
    else:
        c.execute('INSERT INTO notification_visibility (user_email, notification_id, hidden) VALUES (?, ?, 1)', (user_email, notification_id))

    conn.commit()
    conn.close()

    flash("Notification hidden.", "success")
    return redirect(request.referrer or url_for('notifications'))






if __name__ == '__main__':
    init_db()
    app.run(debug=True)
