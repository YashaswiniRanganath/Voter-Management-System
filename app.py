from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from functools import wraps
from datetime import datetime

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '9945311114'
app.config['MYSQL_DB'] = 'voting_system'

mysql = MySQL(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'is_admin' not in session or not session['is_admin']:
            flash('Admin access required', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM elections WHERE is_active = TRUE ORDER BY start_date")
    elections = cur.fetchall()
    cur.close()
    return render_template('index.html', elections=elections)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        cur = mysql.connection.cursor()
        
        # Call stored procedure to register user
        try:
            cur.callproc('RegisterUser', (username, password, email))
            result = cur.fetchall()

            # If stored procedure raises an error (like username already exists)
            if result:
                flash(result[0][0], 'danger')  # Assuming the error message is returned
                return redirect(url_for('register'))

            mysql.connection.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error occurred: {str(e)}', 'danger')
        finally:
            cur.close()
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        # Direct password comparison
        cur.execute("SELECT id, password, is_admin FROM users WHERE username = %s AND password = %s", 
                   (username, password))
        user = cur.fetchone()
        cur.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = username
            session['is_admin'] = user[2]
            flash('Welcome back!', 'success')
            return redirect(url_for('index'))
        
        flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/admin/elections', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_elections():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO elections (title, description, start_date, end_date, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (title, description, start_date, end_date))
        mysql.connection.commit()
        cur.close()
        
        flash('Election created successfully', 'success')
        return redirect(url_for('manage_elections'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM elections ORDER BY created_at DESC")
    elections = cur.fetchall()
    cur.close()
    
    return render_template('admin/elections.html', elections=elections)

@app.route('/admin/candidates/<int:election_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_candidates(election_id):
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO candidates (election_id, name, description)
            VALUES (%s, %s, %s)
        """, (election_id, name, description))
        mysql.connection.commit()
        cur.close()
        
        flash('Candidate added successfully', 'success')
        return redirect(url_for('manage_candidates', election_id=election_id))

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM elections WHERE id = %s", (election_id,))
    election = cur.fetchone()
    
    if not election:
        flash('Election not found', 'danger')
        return redirect(url_for('manage_elections'))
    
    cur.execute("SELECT * FROM candidates WHERE election_id = %s", (election_id,))
    candidates = cur.fetchall()
    cur.close()
    
    return render_template('admin/candidates.html', 
                         election=election, 
                         candidates=candidates)

@app.route('/election/<int:election_id>')
def election_detail(election_id):
    cur = mysql.connection.cursor()
    
    cur.execute("SELECT * FROM elections WHERE id = %s", (election_id,))
    election = cur.fetchone()
    
    if not election:
        flash('Election not found', 'danger')
        return redirect(url_for('index'))
    
    cur.execute("SELECT * FROM candidates WHERE election_id = %s", (election_id,))
    candidates = cur.fetchall()
    
    user_vote = None
    if 'user_id' in session:
        cur.execute("""
            SELECT candidate_id FROM votes 
            WHERE user_id = %s AND election_id = %s
        """, (session['user_id'], election_id))
        vote = cur.fetchone()
        if vote:
            user_vote = vote[0]
    
    cur.close()
    return render_template('election_detail.html', 
                         election=election,
                         candidates=candidates,
                         user_vote=user_vote,
                         now=datetime.now)

    
@app.route('/vote', methods=['POST'])
@login_required
def vote():
    election_id = request.form.get('election_id')
    candidate_id = request.form.get('candidate_id')
    
    if not election_id or not candidate_id:
        flash('Invalid voting data', 'danger')
        return redirect(url_for('index'))
    
    cur = mysql.connection.cursor()
    

    cur.execute("""
        SELECT id FROM elections 
        WHERE id = %s AND is_active = TRUE 
        AND NOW() < end_date
    """, (election_id,))
    
    if not cur.fetchone():
        flash('This election is not active or has ended', 'danger')
        return redirect(url_for('election_detail', election_id=election_id))
    
    cur.execute("SELECT id FROM votes WHERE user_id = %s AND election_id = %s",
                (session['user_id'], election_id))
    if cur.fetchone():
        flash('You have already voted in this election', 'warning')
        return redirect(url_for('election_detail', election_id=election_id))
    
    try:
        cur.execute("INSERT INTO votes (user_id, election_id, candidate_id) VALUES (%s, %s, %s)",
                    (session['user_id'], election_id, candidate_id))
        mysql.connection.commit()
        flash('Your vote has been recorded successfully!', 'success')
    except Exception as e:
        mysql.connection.rollback()
        flash('An error occurred while recording your vote.', 'danger')
    finally:
        cur.close()
    
    return redirect(url_for('election_detail', election_id=election_id))



@app.route('/election/<int:election_id>/results')
def election_results(election_id):
    cur = mysql.connection.cursor()
    
    cur.execute("SELECT * FROM elections WHERE id = %s", (election_id,))
    election = cur.fetchone()
    
    if not election:
        flash('Election not found', 'danger')
        return redirect(url_for('index'))
    
    cur.execute("""
        SELECT c.name, COUNT(v.id) as vote_count 
        FROM candidates c 
        LEFT JOIN votes v ON c.id = v.candidate_id 
        WHERE c.election_id = %s 
        GROUP BY c.id, c.name 
        ORDER BY vote_count DESC
    """, (election_id,))
    results = cur.fetchall()
    cur.close()
    
    return render_template('election_results.html', 
                         election=election,
                         results=results)

@app.route('/admin/election/<int:election_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_election(election_id):
    cur = mysql.connection.cursor()
    
    cur.execute("SELECT is_active FROM elections WHERE id = %s", (election_id,))
    election = cur.fetchone()
    
    if not election:
        flash('Election not found', 'danger')
        return redirect(url_for('manage_elections'))
    
    new_status = not election[0]
    cur.execute("UPDATE elections SET is_active = %s WHERE id = %s",
                (new_status, election_id))
    mysql.connection.commit()
    cur.close()
    
    status_msg = "activated" if new_status else "deactivated"
    flash(f'Election has been {status_msg}', 'success')
    return redirect(url_for('manage_elections'))

if __name__ == '__main__':
    app.run(debug=True)