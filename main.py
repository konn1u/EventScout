import os
from flask import Flask, render_template, redirect
from data import db_session
from data.models import User, Event
from forms.user import RegisterForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandex_lyceum_secret_key'


@app.route('/')
def index():
    db_sess = db_session.create_session()
    events = db_sess.query(Event).all()
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
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)


if __name__ == '__main__':
    if not os.path.exists('db'):
        os.mkdir('db')
    db_session.global_init("db/events.db")
    app.run(port=8080, host='127.0.0.1')