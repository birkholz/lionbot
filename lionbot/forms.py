from wtforms import Form, StringField, validators, IntegerField


class StreamForm(Form):
    description = StringField('Description', [validators.Length(min=1, max=255), validators.DataRequired()])
    title_contains = StringField('Title Contains...', [validators.Length(min=1, max=100), validators.DataRequired()])
    role_id = IntegerField('Role', validators=[validators.DataRequired()])
    channel_id = IntegerField('Channel', validators=[validators.DataRequired()])
