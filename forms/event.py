from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeLocalField, SubmitField
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import DataRequired

class EventForm(FlaskForm):
    title = StringField('Название события', validators=[DataRequired()])
    description = TextAreaField('Описание')
    address = StringField('Место проведения', validators=[DataRequired()])
    event_date = DateTimeLocalField('Дата и время', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    preview_img = FileField('Обложка мероприятия', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Только изображения!')
    ])
    submit = SubmitField('Создать событие')