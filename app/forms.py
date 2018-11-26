from flask_wtf import Form
from wtforms import StringField, BooleanField, SubmitField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired

class NewActivityForm(Form):
    title = StringField('Title', validators=[DataRequired()])
    category = StringField('Category', validators=[DataRequired()])
    description = StringField('Description', validators=[DataRequired()])
    submit = SubmitField('Create Activity')



class NewContainerForm(Form):
    name = StringField('Title', validators=[DataRequired()])
    image = StringField('Image URI', validators=[DataRequired()])
    ports = StringField('Ports', validators=[DataRequired()])
    description = StringField('Description', widget=TextArea(), validators=[DataRequired()])
    submit = SubmitField('Create Container')