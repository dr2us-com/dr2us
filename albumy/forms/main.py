# -*- coding: utf-8 -*-
"""
    :author: Grey Li (李辉)
    :url: http://greyli.com
    :copyright: © 2018 Grey Li <withlihui@gmail.com>
    :license: MIT, see LICENSE for more details.
"""
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, FloatField
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from wtforms.validators import ValidationError
from flask_login import current_user

class DescriptionForm(FlaskForm):
    description = TextAreaField('Description', validators=[Optional(), Length(0, 500)])
    submit = SubmitField()


class TagForm(FlaskForm):
    tag = StringField('Add Tag (use space to separate)', validators=[Optional(), Length(0, 64)])
    submit = SubmitField()


class CommentForm(FlaskForm):
    body = TextAreaField('', validators=[DataRequired()])
    submit = SubmitField()


class WithdrawForm(FlaskForm):
    amount = FloatField('Amount')
    bank_code = StringField('Bank Code', validators=[DataRequired(), Length(0, 255)])
    branch_code = StringField('Branch Code', validators=[ DataRequired(), Length(0, 255)])
    account_number = StringField('Account Number', validators=[DataRequired(), Length(0, 255)])
    additional_info = TextAreaField('Additional Info', validators=[Optional()])
    submit = SubmitField()
    def validate_amount(form,field):
        if not current_user.doctor:
            return
        balance = current_user.doctor.balance
        if not current_user.doctor.balance:
            raise ValidationError('You don\'t have enough Money')
        if float(field.data) > balance:
            raise ValidationError('Your Withdraw Request Amount is bigger than your Balance')
        elif float(field.data) < 0 :
            raise ValidationError('Your Withdraw Request Amount must be bigger than 0')