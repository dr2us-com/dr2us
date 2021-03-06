# -*- coding: utf-8 -*-
"""
    :author: Grey Li (李辉)
    :url: http://greyli.com
    :copyright: © 2018 Grey Li <withlihui@gmail.com>
    :license: MIT, see LICENSE for more details.
"""
import os
import random
from datetime import datetime

from flask import current_app
from flask_avatars import Identicon
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from albumy.extensions import db, whooshee

# relationship table
roles_permissions = db.Table('roles_permissions',
                             db.Column('role_id', db.Integer, db.ForeignKey('role.id')),
                             db.Column('permission_id', db.Integer, db.ForeignKey('permission.id'))
                             )


class Permission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    roles = db.relationship('Role', secondary=roles_permissions, back_populates='permissions')


class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)
    users = db.relationship('User', back_populates='role')
    permissions = db.relationship('Permission', secondary=roles_permissions, back_populates='roles')

    @staticmethod
    def init_role():
        roles_permissions_map = {
            # 'Locked': ['FOLLOW', 'COLLECT'],
            # 'User': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD'],
            'Doctor': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', ],
            'Patient': ['FOLLOW', 'COLLECT', 'UPLOAD', 'RATE'],
            # 'Moderator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE'],
            'Administrator': ['FOLLOW', 'COLLECT', 'COMMENT', 'UPLOAD', 'MODERATE', 'ADMINISTER', 'RATE']
        }

        for role_name in roles_permissions_map:
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(name=role_name)
                db.session.add(role)
            role.permissions = []
            for permission_name in roles_permissions_map[role_name]:
                permission = Permission.query.filter_by(name=permission_name).first()
                if permission is None:
                    permission = Permission(name=permission_name)
                    db.session.add(permission)
                role.permissions.append(permission)
        db.session.commit()


# relationship object
class Follow(db.Model):
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    follower = db.relationship('User', foreign_keys=[follower_id], back_populates='following', lazy='joined')
    followed = db.relationship('User', foreign_keys=[followed_id], back_populates='followers', lazy='joined')


# relationship object
class Collect(db.Model):
    collector_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                             primary_key=True)
    collected_id = db.Column(db.Integer, db.ForeignKey('photo.id'),
                             primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    collector = db.relationship('User', back_populates='collections', lazy='joined')
    collected = db.relationship('Photo', back_populates='collectors', lazy='joined')


class Doctor(db.Model):
    cv = db.Column(db.String(150))  # the hospital name that doctor works.
    address = db.Column(db.String(200))  # the address of hospital.
    speciality = db.Column(db.String(150))
    latitude = db.Column(db.String(20), default='35.392426')
    longitude = db.Column(db.String(20), default='139.476048')
    status = db.Column(db.String(20), default='BAD')    # represent status of the latitude and longitude, if it is flase, its values are not exact.
    acct_id = db.Column(db.String(250))    
    balance = db.Column(db.Float(),default=0.0)
    withdraws = db.relationship('WithDraw',back_populates='doctor',cascade='all')
    id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)


class WithDraw(db.Model):
    id = db.Column(db.Integer,primary_key = True)
    status = db.Column(db.Boolean,default=False)
    amount = db.Column(db.Float(),default=0.0)
    bank_code = db.Column(db.String(255))
    branch_code = db.Column(db.String(255))
    account_number = db.Column(db.String(255))
    additional_bank_info = db.Column(db.Text(1000))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    doctor = db.relationship('Doctor', foreign_keys=[doctor_id], back_populates='withdraws')

# class Patient(db.Model):
#     chief_complaint = db.Column(db.String(300))
#     present_illness = db.Column(db.String(300))
#     past_history = db.Column(db.String(300))
#     family_history = db.Column(db.String(300))
#     diagnosis = db.Column(db.String(300))
#     id = db.Column(db.Integer,db.ForeignKey('user.id'),primary_key = True)

# rater award the star to the user that has same id as awarded_id 
class Rate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rate_value = db.Column(db.Integer(), default=0)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    rater_photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
    awarded_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rater_photo = db.relationship('Photo', foreign_keys=[rater_photo_id], back_populates='rates')
    awarded = db.relationship('User', foreign_keys=[awarded_id], back_populates='awards')


class Invite(db.Model):  # user_id(doctor) has been invited to the photo_id.
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))
    photo = db.relationship('Photo', foreign_keys=[photo_id], back_populates='invites')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', foreign_keys=[user_id], back_populates='invites')
    status = db.Column(db.Boolean, default=False)
    token_id = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(250))
    doctor_name = db.Column(db.String(250))
    token_id = db.Column(db.String(250))
    acct_id = db.Column(db.String(250))
    amount = db.Column(db.String(250))
    currency = db.Column(db.String(250))
    balance_transaction = db.Column(db.String(250))
    description = db.Column(db.String(250))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)



@whooshee.register_model('name', 'username')
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, index=True)
    email = db.Column(db.String(254), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    name = db.Column(db.String(30))
    website = db.Column(db.String(255))
    bio = db.Column(db.String(120))
    location = db.Column(db.String(50))
    member_since = db.Column(db.DateTime, default=datetime.utcnow)
    avatar_s = db.Column(db.String(64))
    avatar_m = db.Column(db.String(64))
    avatar_l = db.Column(db.String(64))
    avatar_raw = db.Column(db.String(64), default='default.jpg')
    avatar_raw2 = db.Column(db.String(64), default='default2.jpg')


    confirmed = db.Column(db.Boolean, default=False)
    locked = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)

    public_collections = db.Column(db.Boolean, default=True)
    receive_comment_notification = db.Column(db.Boolean, default=True)
    receive_follow_notification = db.Column(db.Boolean, default=True)
    receive_collect_notification = db.Column(db.Boolean, default=True)

    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))

    role = db.relationship('Role', back_populates='users')
    photos = db.relationship('Photo', back_populates='author', cascade='all')
    comments = db.relationship('Comment', back_populates='author', cascade='all')
    notifications = db.relationship('Notification', back_populates='receiver', cascade='all')
    collections = db.relationship('Collect', back_populates='collector', cascade='all')
    following = db.relationship('Follow', foreign_keys=[Follow.follower_id], back_populates='follower',
                                lazy='dynamic', cascade='all')
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id], back_populates='followed',
                                lazy='dynamic', cascade='all')

    awards = db.relationship('Rate', foreign_keys=[Rate.awarded_id], back_populates='awarded', cascade='all',
                             lazy='dynamic')
    # added for doctor and patient
    doctor = db.relationship('Doctor', backref='user', cascade='all, delete-orphan', uselist=False)
    invites = db.relationship('Invite', foreign_keys=[Invite.user_id], back_populates='user', cascade='all',
                              lazy='dynamic')

    # patient = db.relationship('Patient',backref = 'user', cascade='all, delete-orphan',uselist=False)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self.generate_avatar()
        self.follow(self)  # follow self
        self.set_role()

    def spec(self):
        if self.role.name == 'Doctor':
            return self.doctor
        elif self.role.name == 'Patient':
            return self.patient

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def set_role(self):
        if self.role is None:
            if self.email == current_app.config['ALBUMY_ADMIN_EMAIL']:
                self.role = Role.query.filter_by(name='Administrator').first()
            else:
                randint = random.randint(1, 2)
                if randint == 1:
                    self.role = Role.query.filter_by(name='Doctor').first()
                if randint == 2:
                    self.role = Role.query.filter_by(name='Patient').first()
            # db.session.commit()

    def set_role_with_name(self, name):
        self.role = Role.query.filter_by(name=name).first()
        # db.session.commit()

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    def follow(self, user):
        if not self.is_following(user):
            follow = Follow(follower=self, followed=user)
            # db.session.add(follow)
            # db.session.commit()

    def unfollow(self, user):
        follow = self.following.filter_by(followed_id=user.id).first()
        if follow:
            db.session.delete(follow)
            db.session.commit()

    def is_following(self, user):
        if user.id is None:  # when follow self, user.id will be None
            return False
        return self.following.filter_by(followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        return self.followers.filter_by(follower_id=user.id).first() is not None

    # def get_rate_rated_by(self,user):        
    #     return self.awards.filter_by(rater_id = user.id).first()
    def get_rate_rated_by(self, photo):
        return self.awards.filter_by(rater_photo_id=photo.id).first()

    @property
    def followed_photos(self):
        return Photo.query.join(Follow, Follow.followed_id == Photo.author_id).filter(Follow.follower_id == self.id)

    @property
    def last_uploaded_photo(self):
        return Photo.query.filter(Photo.author_id == self.id).order_by(Photo.timestamp.desc()).first()

    def collect(self, photo):
        if not self.is_collecting(photo):
            collect = Collect(collector=self, collected=photo)
            db.session.add(collect)
            db.session.commit()

    def uncollect(self, photo):
        collect = Collect.query.with_parent(self).filter_by(collected_id=photo.id).first()
        if collect:
            db.session.delete(collect)
            db.session.commit()

    def is_collecting(self, photo):
        return Collect.query.with_parent(self).filter_by(collected_id=photo.id).first() is not None

    def lock(self):
        self.locked = True
        self.role = Role.query.filter_by(name='Locked').first()
        db.session.commit()

    def unlock(self):
        self.locked = False
        self.role = Role.query.filter_by(name='User').first()
        db.session.commit()

    def block(self):
        self.active = False
        db.session.commit()

    def unblock(self):
        self.active = True
        db.session.commit()

    def generate_avatar(self):
        avatar = Identicon()
        filenames = avatar.generate(text=self.username)
        self.avatar_s = filenames[0]
        self.avatar_m = filenames[1]
        self.avatar_l = filenames[2]
        # db.session.commit()

    def tags(self):
        photos = self.photos
        ret_tags = []
        for photo in photos:
            tags = photo.tags
            for tag in tags:
                if not tag in ret_tags:
                    ret_tags.append(tag)
        return ret_tags

    @property
    def is_admin(self):
        return self.role.name == 'Administrator'

    @property
    def is_active(self):
        return self.active

    def can(self, permission_name):
        permission = Permission.query.filter_by(name=permission_name).first()
        return permission is not None and self.role is not None and permission in self.role.permissions


tagging = db.Table('tagging',
                   db.Column('photo_id', db.Integer, db.ForeignKey('photo.id')),
                   db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
                   )


@whooshee.register_model('description')
class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(500))
    filename = db.Column(db.String(64))
    filename_s = db.Column(db.String(64))
    filename_m = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    can_comment = db.Column(db.Boolean, default=True)
    flag = db.Column(db.Integer, default=0)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    rates = db.relationship('Rate', foreign_keys=[Rate.rater_photo_id], back_populates='rater_photo', cascade='all',
                            lazy='dynamic')  # get the rate data that are given by this photo user
    author = db.relationship('User', back_populates='photos')
    comments = db.relationship('Comment', back_populates='photo', cascade='all')
    collectors = db.relationship('Collect', back_populates='collected', cascade='all')
    tags = db.relationship('Tag', secondary=tagging, back_populates='photos')
    invites = db.relationship('Invite', foreign_keys=[Invite.photo_id], back_populates='photo', cascade='all',
                              lazy='dynamic')


@whooshee.register_model('name')
class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)

    photos = db.relationship('Photo', secondary=tagging, back_populates='tags')


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    flag = db.Column(db.Integer, default=0)

    replied_id = db.Column(db.Integer, db.ForeignKey('comment.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    photo_id = db.Column(db.Integer, db.ForeignKey('photo.id'))

    photo = db.relationship('Photo', back_populates='comments')
    author = db.relationship('User', back_populates='comments')
    replies = db.relationship('Comment', back_populates='replied', cascade='all')
    replied = db.relationship('Comment', back_populates='replies', remote_side=[id])


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    receiver = db.relationship('User', back_populates='notifications')


@db.event.listens_for(User, 'after_delete', named=True)
def delete_avatars(**kwargs):
    target = kwargs['target']
    for filename in [target.avatar_s, target.avatar_m, target.avatar_l, target.avatar_raw]:
        if filename is not None:  # avatar_raw may be None
            path = os.path.join(current_app.config['AVATARS_SAVE_PATH'], filename)
            if os.path.exists(path):  # not every filename map a unique file
                os.remove(path)


@db.event.listens_for(Photo, 'after_delete', named=True)
def delete_photos(**kwargs):
    target = kwargs['target']
    for filename in [target.filename, target.filename_s, target.filename_m]:
        path = os.path.join(current_app.config['ALBUMY_UPLOAD_PATH'], filename)
        if os.path.exists(path):  # not every filename map a unique file
            os.remove(path)
