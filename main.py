import os
import uuid
from flask import Flask, render_template, redirect, abort, jsonify, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename
import random
from datetime import datetime, timedelta
from forms.user import EditProfileForm

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
    pass


@login_manager.user_loader
def load_user(user_id):
    with db_session.create_session() as db_sess:
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
    with db_session.create_session() as db_sess:
        event = db_sess.get(Event, id)
        if not event:
            abort(404)

        now = datetime.now()
        is_past = event.event_date < now
        show_confirm = False

        if current_user.is_authenticated and not event.is_confirmed:
            is_participant = any(u.id == current_user.id for u in event.participants)
            if event.event_date <= now <= (event.event_date + timedelta(minutes=5)):
                if is_participant and current_user.id != event.user_id:
                    random.seed(event.id)
                    lucky_one = random.choice(event.participants)
                    if current_user.id == lucky_one.id:
                        show_confirm = True

        return render_template(
            'event_detail.html',
            title=event.title,
            event=event,
            is_past=is_past,
            show_confirm=show_confirm
        )


@app.route('/profile/<username>')
def profile(username):
    with db_session.create_session() as db_sess:
        user = db_sess.query(User).filter(User.name == username).first()
        if not user:
            abort(404)

        now = datetime.now()
        archive_threshold = now - timedelta(minutes=5)

        active_events = db_sess.query(Event).filter(
            Event.user_id == user.id,
            Event.is_confirmed == False,
            Event.event_date > archive_threshold
        ).order_by(Event.event_date.asc()).all()

        archive_events = db_sess.query(Event).filter(
            Event.user_id == user.id,
            (Event.is_confirmed == True) | (Event.event_date <= archive_threshold)
        ).order_by(Event.event_date.desc()).all()

        return render_template(
            'profile.html',
            title=f'Профиль {user.name}',
            user=user,
            active_events=active_events,
            archive_events=archive_events
        )


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
            image_path = os.path.join(app.static_folder, 'img', event.preview_img)

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


@app.route('/toggle_participation/<int:event_id>', methods=['POST'])
@login_required
def toggle_participation(event_id):
    with db_session.create_session() as db_sess:
        event = db_sess.get(Event, event_id)
        user = db_sess.get(User, current_user.id)

        if not event:
            return jsonify({'error': 'Событие не найдено'}), 404

        if event.user_id == current_user.id:
            return jsonify({'error': 'Организатор не может записываться на свое событие'}), 400

        if event.event_date < datetime.now():
            return jsonify({
                'error': 'Регистрация невозможна: мероприятие уже началось или завершено'
            }), 400

        if user in event.participants:
            event.participants.remove(user)
            status = 'left'
        else:
            event.participants.append(user)
            status = 'joined'

        db_sess.commit()
        return jsonify({
            'status': status,
            'count': len(event.participants)
        })


@app.route('/api/confirm_event/<int:event_id>', methods=['POST'])
@login_required
def confirm_event(event_id):
    db_sess = db_session.create_session()
    event = db_sess.query(Event).get(event_id)

    if event and not event.is_confirmed:
        if datetime.now() <= (event.event_date + timedelta(minutes=5)):
            event.is_confirmed = True
            event.is_finished = True

            organizer = event.owner
            organizer.score += len(event.participants)

            db_sess.commit()
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Время подтверждения истекло"}), 400

    return jsonify({"success": False}), 400


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    db_sess = db_session.create_session()
    user = db_sess.query(User).get(current_user.id)

    if form.validate_on_submit():
        if form.avatar.data:
            file = form.avatar.data
            ext = secure_filename(file.filename).split('.')[-1]
            filename = f"avatar_{user.id}_{uuid.uuid4().hex[:8]}.{ext}"

            if user.avatar and user.avatar != 'default_avatar.png':
                old_path = os.path.join(app.static_folder, 'img', user.avatar)
                if os.path.exists(old_path):
                    os.remove(old_path)

            file.save(os.path.join(app.static_folder, 'img', filename))
            user.avatar = filename

        user.name = form.name.data
        user.about = form.about.data
        db_sess.commit()
        return redirect(f'/profile/{user.name}')

    elif request.method == 'GET':
        form.name.data = user.name
        form.about.data = user.about

    return render_template('edit_profile.html', title='Редактирование профиля', form=form)


@app.route('/rating')
def rating():
    with db_session.create_session() as db_sess:
        users = db_sess.query(User).order_by(User.score.desc()).all()

        return render_template(
            'rating.html',
            title='Рейтинг пользователей',
            users=users
        )


if __name__ == '__main__':
    if not os.path.exists('db'):
        os.mkdir('db')
    db_session.global_init("db/events.db")

    uploads_dir = os.path.join(static_dir, 'img')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)

    app.run(port=8080, host='127.0.0.1')