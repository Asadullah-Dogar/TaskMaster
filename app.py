from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SelectField, DateField, BooleanField
from wtforms.validators import DataRequired, Email, Length, Optional
from forms import LoginForm
from forms import RegisterForm
from forms import TaskForm
from passlib.hash import bcrypt
from forms import EditTaskForm
from dotenv import load_dotenv
import os


load_dotenv()



app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', False)

# Initialize Extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'


# ---------- Models ----------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    priority = db.Column(db.String(10), nullable=True, default='Medium')
    category = db.Column(db.String(50), nullable=True, default='General')
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

login_manager.init_app(app)

# ---------- Routes ----------

@app.route('/')
def home():
    # Fetch only incomplete tasks for the current user if authenticated
    if current_user.is_authenticated:
        tasks = Task.query.filter_by(user_id=current_user.id, completed=False).all()
    else:
        tasks = []

    return render_template('index.html', tasks=tasks)


# Authentication Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        if User.query.filter_by(email=email).first():
            flash('Email already exists.')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Email or password incorrect.')


    return render_template('login.html', form=form)  # Ensure that the login form is rendered when GET request

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Task Management Routes
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        due_date = request.form.get('due_date')
        priority = request.form.get('priority')
        category = request.form.get('category')

        new_task = Task(
            title=title,
            description=description,
            due_date=datetime.strptime(due_date, '%Y-%m-%d'),
            category=category,
            user_id=current_user.id
        )
        db.session.add(new_task)
        db.session.commit()
        flash('Task added successfully.')
        return redirect(url_for('home'))
    return render_template('add_task.html')


@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)

    # Ensure the task belongs to the current user
    if task.user_id != current_user.id:
        flash('You are not authorized to edit this task.')
        return redirect(url_for('home'))

    # Initialize the form after retrieving the task
    form = EditTaskForm(obj=task)

    if form.validate_on_submit():
        # Update task fields with form data
        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data
        task.priority = form.priority.data
        task.completed = 'completed' in request.form

        # Commit changes to the database
        db.session.commit()

        flash('Task updated successfully.')
        return redirect(url_for('home'))

    return render_template('edit_task.html', task=task, form=form)

@app.route('/delete/<int:task_id>', methods=['GET', 'POST'])
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id != current_user.id:
        flash('You are not authorized to delete this task.')
        return redirect(url_for('home'))
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully.')
    return redirect(url_for('home'))

# Search Route
@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('query')
    tasks = Task.query.filter(Task.user_id == current_user.id, (Task.title.contains(query) | Task.description.contains(query))).all()
    return render_template('tasks.html', tasks=tasks)

@app.route('/completed')
def completed_tasks():
    if current_user.is_authenticated:
        tasks = Task.query.filter_by(user_id=current_user.id, completed=True).all()  # Show only completed tasks for the logged-in user
    else:
        tasks = []
    return render_template('completed.html', tasks=tasks)

@app.route("/complete/<int:task_id>")
@app.route("/complete/<int:task_id>")
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    task.completed = True
    db.session.commit()
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(debug=True)
