# -*- coding: utf-8 -*-
"""
    :author: Grey Li (李辉)
    :url: http://greyli.com
    :copyright: © 2018 Grey Li <withlihui@gmail.com>
    :license: MIT, see LICENSE for more details.
"""
import os
import random

from PIL import Image
from faker import Faker
from flask import current_app
from sqlalchemy.exc import IntegrityError

from albumy.extensions import db
from albumy.models import User, Photo, Tag, Comment, Notification,Doctor,Patient,Role

fake = Faker()


def fake_admin():
    admin = User(name='Grey Li',
                 username='greyli',
                 email='admin@helloflask.com',
                 bio=fake.sentence(),
                 website='http://greyli.com',
                 confirmed=True)
    admin.set_password('helloflask')
    notification = Notification(message='Hello, welcome to Albumy.', receiver=admin)
    db.session.add(notification)
    db.session.add(admin)
    db.session.commit()

def fake_hospital_cv():
    lists = ["Silver Gardens Medical Clinic",
        "Peace River General Hospital",
        "Jade Forest Community Hospital",
        "Hallmark Hospital",
        "Healthbridge Medical Clinic",
        "Great River Hospital Center",
        "Peace Forest General Hospital",
        "Bayview Community Hospital",
        "Bayhealth General Hospital",
        "Edgewater Community Hospital"]
    return lists[random.randint(0, len(lists)-1)]
def fake_user(count=10):
    for i in range(count):
        user = User(name=fake.name(),
                    confirmed=True,
                    username=fake.user_name(),
                    bio=fake.sentence(),
                    location=fake.city(),
                    website=fake.url(),
                    member_since=fake.date_this_decade(),
                    email=fake.email())
        if(user.role.name == 'Doctor'):
            doctor = Doctor(cv = fake_hospital_cv(),
                            speciality = fake.word(),
                            address=fake.address(),
                            latitude = str(fake.latitude()),
                            longitude = str(fake.longitude()))
            user.doctor = doctor
        elif(user.role.name == 'Patient'):
            patient = Patient(chief_complaint = fake.sentence(),
                            present_illness = fake.sentence(),
                            past_history=fake.sentence(),
                            diagnosis = fake.sentence(),
                            family_history = fake.sentence())
            user.patient = patient
        user.set_password('123456')
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def fake_follow(count=30):
    for i in range(count):
        user = User.query.get(random.randint(1, User.query.count()))
        user.follow(User.query.get(random.randint(1, User.query.count())))
    db.session.commit()


def fake_tag(count=20):
    for i in range(count):
        tag = Tag(name=fake.word())
        db.session.add(tag)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


def fake_photo(count=30):
    # photos
    upload_path = current_app.config['ALBUMY_UPLOAD_PATH']
    for i in range(count):
        print(i)

        filename = 'random_%d.jpg' % i
        r = lambda: random.randint(128, 255)
        img = Image.new(mode='RGB', size=(800, 800), color=(r(), r(), r()))
        img.save(os.path.join(upload_path, filename))

        photo = Photo(
            description=fake.text(),
            filename=filename,
            filename_m=filename,
            filename_s=filename,
            author=User.query.get(random.randint(1, User.query.count())),
            timestamp=fake.date_time_this_year()
        )

        # tags
        for j in range(random.randint(1, 5)):
            tag = Tag.query.get(random.randint(1, Tag.query.count()))
            if tag not in photo.tags:
                photo.tags.append(tag)

        db.session.add(photo)
    db.session.commit()


def fake_collect(count=50):
    for i in range(count):
        user = User.query.get(random.randint(1, User.query.count()))
        user.collect(Photo.query.get(random.randint(1, Photo.query.count())))
    db.session.commit()


def fake_comment(count=100):
    doctors = User.query.join(Role).filter(Role.name == 'Doctor').all()
    for i in range(count):
        comment = Comment(
            author=doctors[random.randint(0, len(doctors)-1)],
            body=fake.sentence(),
            timestamp=fake.date_time_this_year(),
            photo=Photo.query.get(random.randint(1, Photo.query.count()))
        )
        # comment = Comment(
        #     author=User.query.get(random.randint(1, User.query.count())),
        #     body=fake.sentence(),
        #     timestamp=fake.date_time_this_year(),
        #     photo=Photo.query.get(random.randint(1, Photo.query.count()))
        # )
        db.session.add(comment)
    db.session.commit()
