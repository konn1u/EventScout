import os
import uuid
from flask import Flask, render_template, redirect, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename

from data import db_session
from data.models import User, Event
from forms.user import RegisterForm, LoginForm
from forms.event import EventForm

template_dir = os.path.abspath('templates')
static_dir = os.path.abspath('static')

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['SECRET_KEY'] = 'yandex_lyceum_secret_key'

login_manager = LoginManager()
login_manager.init_app(app)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.create_session().close()


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)


@app.route('/')
def index():
    db_sess = db_session.create_session()
    events = db_sess.query(Event).order_by(Event.event_date.asc()).all()
    return render_template('index.html', title='EventScout', events=events)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form, message="Такой пользователь уже есть")

        user = User(name=form.name.data, email=form.email.data)
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


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


@app.route('/add_event', methods=['GET', 'POST'])
@login_required
def add_event():
    form = EventForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()

        filename = 'placeholder.png'
        if form.preview_img.data:
            file = form.preview_img.data
            ext = secure_filename(file.filename).split('.')[-1]
            filename = f"{uuid.uuid4()}.{ext}"

            file.save(os.path.join(app.static_folder, 'img', filename))

        event = Event(
            title=form.title.data,
            description=form.description.data,
            address=form.address.data,
            event_date=form.event_date.data,
            user_id=current_user.id,
            preview_img=filename
        )
        db_sess.add(event)
        db_sess.commit()
        return redirect('/')
    return render_template('create_event.html', title='Добавить событие', form=form)


@app.route('/event/<int:id>')
def event_info(id):
    db_sess = db_session.create_session()
    event = db_sess.get(Event, id)
    if not event:
        abort(404)
    return render_template('event_detail.html', title=event.title, event=event)


@app.route('/event_delete/<int:id>', methods=['GET', 'POST'])
@login_required
def event_delete(id):
    db_sess = db_session.create_session()

    event = db_sess.query(Event).filter(
        Event.id == id,
        Event.user_id == current_user.id
    ).first()

    if event:
        if event.preview_img:
            image_path = os.path.join(app.root_path, 'static', 'img', event.preview_img)

            if os.path.exists(image_path) and event.preview_img != 'placeholder.png':
                try:
                    os.remove(image_path)
                except Exception as e:
                    print(f"Ошибка при удалении файла: {e}")

        db_sess.delete(event)
        db_sess.commit()
    else:
        abort(404)

    return redirect('/')


if __name__ == '__main__':
    if not os.path.exists('db'):
        os.mkdir('db')
    db_session.global_init("db/events.db")

    uploads_dir = os.path.join(static_dir, 'img')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)

    app.run(port=8080, host='127.0.0.1')