# -*- coding: utf-8 -*-
"""
    :author: Grey Li (李辉)
    :url: http://greyli.com
    :copyright: © 2018 Grey Li <withlihui@gmail.com>
    :license: MIT, see LICENSE for more details.
"""
from flask import url_for

from albumy.extensions import db
from albumy.models import Notification


def push_follow_notification(follower, receiver):
    message = 'User <a href="%s">%s</a> followed you.' % \
              (url_for('user.index', username=follower.username), follower.username)
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()


def push_comment_notification(photo_id, receiver, page=1):
    message = '<a href="%s#comments">This photo</a> has new comment/reply.' % \
              (url_for('main.show_photo', photo_id=photo_id, page=page))
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()


def push_collect_notification(collector, photo_id, receiver):
    message = 'User <a href="%s">%s</a> collected your <a href="%s">photo</a>' % \
              (url_for('user.index', username=collector.username),
               collector.username,
               url_for('main.show_photo', photo_id=photo_id))
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()


def push_invite_notification(photo, receiver):
    message = '<a href="%s" > You have received the invite request from "%s" </a>' % \
              (url_for('main.show_photo', photo_id=photo.id), photo.author.username)
    notification = Notification(message=message, receiver=receiver)
    db.session.add(notification)
    db.session.commit()


def push_reinvite_notification(photo, sender):
    message = '<a href="%s" > Your request for Dr %s  has been rejected because of unexpected error. But don\'t worry. You can Hire him again.</a>' % \
              (url_for('main.show_photo', photo_id=photo.id), sender.username)
    notification = Notification(message=message, receiver=photo.author)
    db.session.add(notification)
    db.session.commit()


def push_invite_accept_notification(photo, sender, receipt_url, amount):
    print(type(amount))
    message = '<a href="%s" > Dr %s  has been hired for you.</a> You paid <a href="%s">%.2f $ </a> for this.' % \
              (url_for('main.show_photo', photo_id=photo.id), sender.username,receipt_url,amount)
    notification = Notification(message=message, receiver=photo.author)
    db.session.add(notification)
    db.session.commit()
