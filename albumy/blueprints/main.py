# -*- coding: utf-8 -*-
"""
    :author: Grey Li (李辉)
    :url: http://greyli.com
    :copyright: © 2018 Grey Li <withlihui@gmail.com>
    :license: MIT, see LICENSE for more details.
"""

import requests
import stripe
from flask import render_template, flash, redirect, send_from_directory, request, abort, Blueprint
from flask_login import login_required, current_user
from sqlalchemy.sql.expression import func

from albumy import settings
from albumy.decorators import confirm_required, permission_required
from albumy.emails import send_invite_email
from albumy.forms.main import DescriptionForm, TagForm, CommentForm
from albumy.models import *
from albumy.notifications import *
from albumy.settings import Operations
from albumy.utils import rename_image, resize_image, redirect_back, flash_errors, generate_token

os.environ['SECRET_KEY'] = settings.BaseConfig.STRIPE_SECRET_KEY
os.environ['PUBLISHABLE_KEY'] = settings.BaseConfig.STRIPE_PUBLISH_KEY
stripe_keys = {
    'secret_key': os.environ['SECRET_KEY'],
    'publishable_key': os.environ['PUBLISHABLE_KEY']
}

stripe.api_key = stripe_keys['secret_key']
main_bp = Blueprint('main', __name__)


@main_bp.route('/prev_home')
def prev_index():
    if current_user.is_authenticated:
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config['ALBUMY_PHOTO_PER_PAGE']
        pagination = Photo.query \
            .join(Follow, Follow.followed_id == Photo.author_id) \
            .filter(Follow.follower_id == current_user.id) \
            .order_by(Photo.timestamp.desc()) \
            .paginate(page, per_page)
        photos = pagination.items

    else:
        pagination = None
        photos = None
    tags = Tag.query.join(Tag.photos).group_by(Tag.id).order_by(func.count(Photo.id).desc()).limit(10)
    return render_template('main/index.html', pagination=pagination, photos=photos, tags=tags, Collect=Collect)


@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        page = request.args.get('page', 1, type=int)
        per_page = current_app.config['ALBUMY_PHOTO_PER_PAGE']

        tags = Tag.query.join(Tag.photos).group_by(Tag.id).order_by(func.count(Photo.id).desc()).limit(10)
        doctors = Doctor.query.all()
        if current_user.role.name == 'Doctor':
            if current_user.doctor.address == '' or current_user.doctor.cv == '' or current_user.doctor.speciality == '':
                return redirect(url_for('user.edit_doctor_info'))
            pagination = current_user.following.paginate(page, per_page)
            followings = pagination.items
            awards = current_user.awards
            awards_value = 0
            for award in awards:
                awards_value = awards_value + award.rate_value
            return render_template('main/doctor_index.html', pagination=pagination, followings=followings, tags=tags,
                                   awards_value=awards_value, doctors=doctors)
        if current_user.role.name == 'Patient':
            return redirect(url_for('user.index', username=current_user.username))
            # photos = current_user.photos
            # photos_id_list = [item.id for item in photos]

            # pagination = Comment.query.filter(Comment.photo_id.in_(photos_id_list)).order_by(Comment.timestamp.desc()).paginate(page, per_page)
            # comments = pagination.items
            # return render_template('main/patient_index.html', pagination=pagination, comments=comments, tags=tags,photos = photos,doctors=doctors)
        else:
            pagination = Photo.query \
                .join(Follow, Follow.followed_id == Photo.author_id) \
                .filter(Follow.follower_id == current_user.id) \
                .order_by(Photo.timestamp.desc()) \
                .paginate(page, per_page)
            photos = pagination.items
            return render_template('main/index.html', pagination=pagination, photos=photos, tags=tags)
    else:
        pagination = None
        followings = None

    return render_template('main/index.html')


@main_bp.route('/agreement')
def agreement():
    return render_template('main/agreement.html')


@main_bp.route('/terms')
def terms():
    return render_template('main/terms.html')


@main_bp.route('/explore')
def explore():
    photos = Photo.query.order_by(func.random()).limit(12)
    return render_template('main/explore.html', photos=photos)


@main_bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if q == '':
        flash('Enter keyword about photo, user or tag.', 'warning')
        return redirect_back()

    category = request.args.get('category', 'photo')
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_SEARCH_RESULT_PER_PAGE']
    if category == 'user':
        pagination = User.query.whooshee_search(q).paginate(page, per_page)
    elif category == 'tag':
        pagination = Tag.query.whooshee_search(q).paginate(page, per_page)
    else:
        pagination = Photo.query.whooshee_search(q).paginate(page, per_page)
    results = pagination.items
    return render_template('main/search.html', q=q, results=results, pagination=pagination, category=category)


@main_bp.route('/notifications')
@login_required
def show_notifications():
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_NOTIFICATION_PER_PAGE']
    notifications = Notification.query.with_parent(current_user)
    filter_rule = request.args.get('filter')
    if filter_rule == 'unread':
        notifications = notifications.filter_by(is_read=False)

    pagination = notifications.order_by(Notification.timestamp.desc()).paginate(page, per_page)
    notifications = pagination.items
    return render_template('main/notifications.html', pagination=pagination, notifications=notifications)


@main_bp.route('/notification/read/<int:notification_id>', methods=['POST'])
@login_required
def read_notification(notification_id):
    notification = Notification.query.get_or_404(notification_id)
    if current_user != notification.receiver:
        abort(403)

    notification.is_read = True
    db.session.commit()
    flash('Notification archived.', 'success')
    return redirect(url_for('.show_notifications'))


@main_bp.route('/notifications/read/all', methods=['POST'])
@login_required
def read_all_notification():
    for notification in current_user.notifications:
        notification.is_read = True
    db.session.commit()
    flash('All notifications archived.', 'success')
    return redirect(url_for('.show_notifications'))


@main_bp.route('/uploads/<path:filename>')
def get_image(filename):
    return send_from_directory(current_app.config['ALBUMY_UPLOAD_PATH'], filename)


@main_bp.route('/avatars/<path:filename>')
def get_avatar(filename):
    if not filename:
        return send_from_directory(current_app.config['AVATARS_SAVE_PATH'], 'default.png')
    return send_from_directory(current_app.config['AVATARS_SAVE_PATH'], filename)


@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
@confirm_required
@permission_required('UPLOAD')
def upload():
    if request.method == 'POST' and 'file' in request.files:
        f = request.files.get('file')
        filename = rename_image(f.filename)
        f.save(os.path.join(current_app.config['ALBUMY_UPLOAD_PATH'], filename))
        filename_s = resize_image(f, filename, current_app.config['ALBUMY_PHOTO_SIZE']['small'])
        filename_m = resize_image(f, filename, current_app.config['ALBUMY_PHOTO_SIZE']['medium'])
        photo = Photo(
            filename=filename,
            filename_s=filename_s,
            filename_m=filename_m,
            author=current_user._get_current_object()
        )
        db.session.add(photo)
        db.session.commit()
    return render_template('main/upload.html')


@main_bp.route('/photo/<int:photo_id>')
@login_required
@confirm_required
def show_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_COMMENT_PER_PAGE']
    pagination = Comment.query.with_parent(photo).order_by(Comment.timestamp.asc()).paginate(page, per_page)
    comments = pagination.items
    comment_form = CommentForm()
    description_form = DescriptionForm()
    tag_form = TagForm()

    description_form.description.data = photo.description
    if current_user.role.name != 'Doctor':
        doctors_leave_comment = []
        doctor_ids_leave_comment = []
        for comment in photo.comments:
            print(comment.author)
            if not comment.author in doctors_leave_comment:
                if comment.author.role.name == 'Doctor':
                    doctors_leave_comment.append(comment.author)
                    doctor_ids_leave_comment.append(comment.author.id)
        doctors_not_leave_comment = User.query.join(Role).filter(Role.name == 'Doctor').filter(
            ~User.id.in_(doctor_ids_leave_comment)).all()

        return render_template('main/photo.html', photo=photo, comment_form=comment_form,
                               description_form=description_form, tag_form=tag_form,
                               pagination=pagination, comments=comments, doctors_leave_comment=doctors_leave_comment,
                               doctors_not_leave_comment=doctors_not_leave_comment)
    else:
        invite = photo.invites.filter(Invite.user_id == current_user.id,Invite.status == False).first()
        return render_template('main/photo.html', photo=photo, comment_form=comment_form,
                               description_form=description_form, tag_form=tag_form,
                               pagination=pagination, comments=comments, invite=invite)


@main_bp.route('/photo/<int:photo_id>/hire', methods=['POST'])
@login_required
@confirm_required
def send_hire_request(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    user = User.query.get_or_404(request.form['doctor_id'])
    token_id = request.form['stripeToken']
    Invite.query.filter(Invite.photo_id == photo.id, Invite.user_id == user.id, Invite.status == False).delete()
    invite = Invite(photo=photo, user=user, token_id=token_id)
    db.session.add(invite)
    db.session.commit()
    flash('Your request has been sent! You will pay 109$ when doctor accept your request.', 'success')
    push_invite_notification(photo, user)
    return redirect(url_for('.show_photo', photo_id=photo_id))


@main_bp.route('/invite/<int:invite_id>/hire', methods=['POST'])
@login_required
@confirm_required
def accept_hire_request(invite_id):
    invite = Invite.query.get_or_404(invite_id)
    invite.status = True
    try:
        amount = current_app.config['APPLICATION_FEE'] + current_app.config['DOCTOR_PAYMENT']
        application_fee = current_app.config['APPLICATION_FEE']
        doctor = current_user.doctor
        if doctor.acct_id:
            charge = stripe.Charge.create(
                amount=amount,
                currency="usd",
                source=invite.token_id,
                application_fee_amount=application_fee,
                stripe_account=doctor.acct_id,
            )
            if not charge['paid']:
                flash('You can\'t Accept the Hire Request. Unexpected error is issued.', 'error')
                invite.delete()
                db.session.delete(invite)
                push_reinvite_notification(invite.photo, current_user)

            else:
                flash('Congratulations! You got payment accepting the hire request.', 'success')
                invite.status = True
                receipt_url = charge.receipt_url
                amount = charge.amount
                transaction = Transaction(patient_name=invite.photo.author.username,
                                          doctor_name=invite.user.username,
                                          token_id=invite.token_id,
                                          acct_id=invite.user.doctor.acct_id,
                                          amount=str(amount),
                                          currency=charge.currency,
                                          balance_transaction=charge.balance_transaction)
                db.session.add(transaction)
                push_invite_accept_notification(invite.photo, current_user, receipt_url, amount / 100)
        else:
            stripe_oauth_url = "https://connect.stripe.com/oauth/authorize?response_type=code&client_id=%s&scope=read_write" % \
                               current_app.config['STRIPE_CLIENT_ID']
            return redirect(stripe_oauth_url)

        db.session.commit()

    except Exception as e:
        print(e)
        flash('Unexpected error has been issued. Contact the Support', 'error')
        db.session.remove()

    return redirect(url_for('.show_photo', photo_id=invite.photo_id))


@main_bp.route('/stripe_redirect/')
@login_required
@confirm_required
def stripe_redirect():
    error = request.args.get('error')
    if error:
        flash(request.args.get('error_description'), 'error')
    else:
        code = request.args.get('code')
        res = requests.post('https://connect.stripe.com/oauth/token',
                            data={'client_secret': current_app.config['STRIPE_SECRET_KEY'],
                                  'code': code,
                                  'grant_type': 'authorization_code'
                                  })
        print(res.json())
        res = res.json()
        error = res.get('error')
        if error:
            flash(res.get('error_description'), 'error')
        else:
            if current_user.role.name == 'Doctor':
                current_user.doctor.acct_id = res['stripe_user_id']
                db.session.commit()
                flash('You have connected the stripe account. Now You can get payment.', 'success')
    return redirect('/')


@main_bp.route('/photo/<int:photo_id>/admire', methods=['POST'])
@login_required
@confirm_required
def send_email_to_admire_doctor(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    token_id = request.form['stripeToken']
    to = request.form['email']
    doctor_name = request.form['name']
    mail_token = generate_token(photo.author, Operations.Invite_Doctor, expire_in=None, stripe_token_id=token_id,
                                photo_id=photo_id, email=to, sender_name = photo.author.username)
    send_invite_email(photo.author, mail_token, to, doctor_name=doctor_name)
    flash('The Email has been sent to the Doctor %s' % doctor_name, 'success')
    return redirect(url_for('.show_photo', photo_id=photo_id))


@main_bp.route('/photo/n/<int:photo_id>')
def photo_next(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    photo_n = Photo.query.with_parent(photo.author).filter(Photo.id < photo_id).order_by(Photo.id.desc()).first()

    if photo_n is None:
        flash('This is already the last one.', 'info')
        return redirect(url_for('.show_photo', photo_id=photo_id))
    return redirect(url_for('.show_photo', photo_id=photo_n.id))


@main_bp.route('/photo/p/<int:photo_id>')
def photo_previous(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    photo_p = Photo.query.with_parent(photo.author).filter(Photo.id > photo_id).order_by(Photo.id.asc()).first()

    if photo_p is None:
        flash('This is already the first one.', 'info')
        return redirect(url_for('.show_photo', photo_id=photo_id))
    return redirect(url_for('.show_photo', photo_id=photo_p.id))


@main_bp.route('/collect/<int:photo_id>', methods=['POST'])
@login_required
@confirm_required
@permission_required('COLLECT')
def collect(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user.is_collecting(photo):
        flash('Already collected.', 'info')
        return redirect(url_for('.show_photo', photo_id=photo_id))

    current_user.collect(photo)
    flash('Photo collected.', 'success')
    if current_user != photo.author and photo.author.receive_collect_notification:
        push_collect_notification(collector=current_user, photo_id=photo_id, receiver=photo.author)
    return redirect(url_for('.show_photo', photo_id=photo_id))


@main_bp.route('/uncollect/<int:photo_id>', methods=['POST'])
@login_required
def uncollect(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if not current_user.is_collecting(photo):
        flash('Not collect yet.', 'info')
        return redirect(url_for('.show_photo', photo_id=photo_id))

    current_user.uncollect(photo)
    flash('Photo uncollected.', 'info')
    return redirect(url_for('.show_photo', photo_id=photo_id))


@main_bp.route('/report/comment/<int:comment_id>', methods=['POST'])
@login_required
@confirm_required
def report_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    comment.flag += 1
    db.session.commit()
    flash('Comment reported.', 'success')
    return redirect(url_for('.show_photo', photo_id=comment.photo_id))


@main_bp.route('/report/photo/<int:photo_id>', methods=['POST'])
@login_required
@confirm_required
def report_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    photo.flag += 1
    db.session.commit()
    flash('Photo reported.', 'success')
    return redirect(url_for('.show_photo', photo_id=photo.id))


@main_bp.route('/photo/<int:photo_id>/collectors')
def show_collectors(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_USER_PER_PAGE']
    pagination = Collect.query.with_parent(photo).order_by(Collect.timestamp.asc()).paginate(page, per_page)
    collects = pagination.items
    return render_template('main/collectors.html', collects=collects, photo=photo, pagination=pagination)


@main_bp.route('/photo/<int:photo_id>/description', methods=['POST'])
@login_required
def edit_description(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)

    form = DescriptionForm()
    if form.validate_on_submit():
        photo.description = form.description.data
        db.session.commit()
        flash('Description updated.', 'success')

    flash_errors(form)
    return redirect(url_for('.show_photo', photo_id=photo_id))


@main_bp.route('/photo/<int:photo_id>/comment/new', methods=['POST'])
@login_required
@permission_required('COMMENT')
def new_comment(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    page = request.args.get('page', 1, type=int)
    form = CommentForm()
    if form.validate_on_submit():
        body = form.body.data
        author = current_user._get_current_object()
        comment = Comment(body=body, author=author, photo=photo)

        replied_id = request.args.get('reply')
        if replied_id:
            comment.replied = Comment.query.get_or_404(replied_id)
            if comment.replied.author.receive_comment_notification:
                push_comment_notification(photo_id=photo.id, receiver=comment.replied.author)
        db.session.add(comment)
        db.session.commit()
        flash('Comment published.', 'success')

        if current_user != photo.author and photo.author.receive_comment_notification:
            push_comment_notification(photo_id, receiver=photo.author, page=page)

    flash_errors(form)
    return redirect(url_for('.show_photo', photo_id=photo_id, page=page))


@main_bp.route('/photo/<int:photo_id>/tag/new', methods=['POST'])
@login_required
def new_tag(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)

    form = TagForm()
    if form.validate_on_submit():
        for name in form.tag.data.split():
            tag = Tag.query.filter_by(name=name).first()
            if tag is None:
                tag = Tag(name=name)
                db.session.add(tag)
                db.session.commit()
            if tag not in photo.tags:
                photo.tags.append(tag)
                db.session.commit()
        flash('Tag added.', 'success')

    flash_errors(form)
    return redirect(url_for('.show_photo', photo_id=photo_id))


@main_bp.route('/set-comment/<int:photo_id>', methods=['POST'])
@login_required
def set_comment(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author:
        abort(403)

    if photo.can_comment:
        photo.can_comment = False
        flash('Comment disabled', 'info')
    else:
        photo.can_comment = True
        flash('Comment enabled.', 'info')
    db.session.commit()
    return redirect(url_for('.show_photo', photo_id=photo_id))


@main_bp.route('/reply/comment/<int:comment_id>')
@login_required
@permission_required('COMMENT')
def reply_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    return redirect(
        url_for('.show_photo', photo_id=comment.photo_id, reply=comment_id,
                author=comment.author.name) + '#comment-form')


@main_bp.route('/delete/photo/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)

    db.session.delete(photo)
    db.session.commit()
    flash('Photo deleted.', 'info')

    photo_n = Photo.query.with_parent(photo.author).filter(Photo.id < photo_id).order_by(Photo.id.desc()).first()
    if photo_n is None:
        photo_p = Photo.query.with_parent(photo.author).filter(Photo.id > photo_id).order_by(Photo.id.asc()).first()
        if photo_p is None:
            return redirect(url_for('user.index', username=photo.author.username))
        return redirect(url_for('.show_photo', photo_id=photo_p.id))
    return redirect(url_for('.show_photo', photo_id=photo_n.id))


@main_bp.route('/delete/comment/<int:comment_id>', methods=['POST'])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    if current_user != comment.author and current_user != comment.photo.author \
            and not current_user.can('MODERATE'):
        abort(403)
    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted.', 'info')
    return redirect(url_for('.show_photo', photo_id=comment.photo_id))


@main_bp.route('/tag/<int:tag_id>', defaults={'order': 'by_time'})
@main_bp.route('/tag/<int:tag_id>/<order>')
def show_tag(tag_id, order):
    tag = Tag.query.get_or_404(tag_id)
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config['ALBUMY_PHOTO_PER_PAGE']
    order_rule = 'time'
    pagination = Photo.query.with_parent(tag).order_by(Photo.timestamp.desc()).paginate(page, per_page)
    photos = pagination.items

    if order == 'by_collects':
        photos.sort(key=lambda x: len(x.collectors), reverse=True)
        order_rule = 'collects'
    return render_template('main/tag.html', tag=tag, pagination=pagination, photos=photos, order_rule=order_rule)


@main_bp.route('/delete/tag/<int:photo_id>/<int:tag_id>', methods=['POST'])
@login_required
def delete_tag(photo_id, tag_id):
    tag = Tag.query.get_or_404(tag_id)
    photo = Photo.query.get_or_404(photo_id)
    if current_user != photo.author and not current_user.can('MODERATE'):
        abort(403)
    photo.tags.remove(tag)
    db.session.commit()

    if not tag.photos:
        db.session.delete(tag)
        db.session.commit()

    flash('Tag deleted.', 'info')
    return redirect(url_for('.show_photo', photo_id=photo_id))
