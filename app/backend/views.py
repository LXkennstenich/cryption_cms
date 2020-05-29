#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
from datetime import timedelta, datetime
from flask import render_template, request, flash, redirect, url_for, escape, abort, make_response, current_app
from validate_email import validate_email
from werkzeug.utils import secure_filename
from app.libs.libs import allowed_file, get_real_ip
from app.models import SystemMail, Session, News, Trash, SystemSettings, Page
from . import backend
from .models import BeUser, FailedLoginRecord
from .forms import LoginForm, EditBeUserForm, EditAccountForm, NewsEditorForm, AddBeUserForm, PageEditorForm
from flask_login import login_user, current_user, login_required, logout_user
from app import login_manager, my_logger
from .nav import create_nav


############################################################################
# Logout
############################################################################

@backend.route("/logout", methods=["GET"])
@login_required
def logout():
    """

    Returns:

    """
    user = current_user
    session = Session()
    session.set_user_id(user.get_id())
    session.load()
    session.delete()
    if logout_user():
        flash("Erfolgreich abgemeldet", "success")
        return redirect(url_for("backend.login"))


############################################################################
# Login
############################################################################

@backend.route("/login", methods=["GET", "POST"])
def login():
    """
    Login Endpunkt

    Returns:
        Rendert das Login Template oder leitet an das Dashboard weiter nach erfolgreichem Login

    """
    form = LoginForm()

    ip_address = get_real_ip()
    my_logger.debug(ip_address)
    if request.method == "POST":
        if form.validate_on_submit():
            my_logger.debug("form validate on submit")
            be_user = BeUser()
            be_user.set("username", escape(request.form["username"]))
            be_user.temp_password = escape(request.form["password"])
            if be_user.validate_login():
                be_user.load()
                session = Session()
                session.set_user_id(be_user.get_id())
                if session.session_exists():
                    session.delete()
                    session = Session()
                    session.set_user_id(be_user.get_id())

                ip_address = escape(ip_address)
                user_agent = escape(request.user_agent)
                token = session.encryption.create_random_token(32)

                session.set_ip_address(ip_address)
                session.set_user_agent(user_agent)
                session.set_token(token)
                time = datetime.now()
                session.set_timestamp(time)
                # my_logger.log("session timestamp: {0}".format(time.strftime("d.m.Y H:i:s")))
                if session.save() is not False:
                    session_user = be_user.create_session_user()
                    if login_user(session_user):
                        my_logger.log(10, "User mit der ID {0} eingeloggt".format(session_user.get_id()))
                        return redirect(url_for("backend.dashboard"))
            else:
                failed_login_record = FailedLoginRecord()
                failed_login_record.set_user_id(be_user.get_id())
                failed_login_record.set_username(be_user.get_username())
                failed_login_record.set_ip_address(request.remote_addr)
                failed_login_record.set_user_agent(str(request.user_agent))
                failed_login_record.save()
        else:
            flash(form.errors)
            my_logger.debug("form nicht valid")
    return render_template("login.html", form=form)


############################################################################
# Dashboard
############################################################################

@backend.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    """
     hauptnavigation

    """
    # erstellt die navigation in bezug auf die benutzerrechte
    create_nav()
    return render_template("dashboard.html")


############################################################################
# Trash
############################################################################

@backend.route("/trash", methods=["GET", "POST"])
@login_required
def trash():
    """

    """
    trash = Trash()
    return render_template("system/trash.html", trash=trash)


@backend.route("/trash/<int:id>", methods=["GET", "POST"])
@login_required
def delete_trash(id):
    """

    """
    trash = Trash()
    if id > 0:
        trash.set_id(id)
        trash.load()
        trash.delete()
    return render_template("system/trash.html", trash=trash)


############################################################################
# System Settings
############################################################################

@backend.route("/system_settings", methods=["GET"])
@login_required
def system_settings():
    """

    """
    system_settings = SystemSettings()
    return render_template("system/settings.html", system_settings=system_settings)


@backend.route("/system_settings/<int:id>", methods=["POST"])
@login_required
def edit_system_settings():
    """

    """
    form = EditAccountForm()
    return render_template("account/edit_account.html", form=form)


############################################################################
# Account
############################################################################


@backend.route("/account/edit", methods=["GET", "POST"])
@login_required
def account_edit():
    """
    account editieren
    """
    user_id = current_user.get_id()
    be_user = BeUser()
    be_user.set_id(user_id)
    be_user.load()
    form = EditAccountForm(request.form)
    if request.method == "GET":
        form.init_values(be_user)
    if request.method == "POST":
        if form.validate_on_submit():
            be_user.temp_password = escape(request.form["user_password"])
            if be_user.encryption.validate_hash(be_user.get_password(), be_user.temp_password):
                be_user.prepare_form_input(request.form)
                be_user.save()
            else:
                flash("Sie haben ein falsches Passwort eingegeben", "danger")
        else:
            form.get_error_messages()
    return render_template("account/edit_account.html", form=form)


############################################################################
# BeUser
############################################################################

@backend.route("/be_user/activate/<int:user_id>/<string:activation_token>", methods=["GET"])
def be_user_activate(user_id, activation_token):
    """

    Args:
        user_id:
        activation_token:

    Returns:

    """
    if user_id <= 0:
        abort(400)

    if len(activation_token) > 64 or len(activation_token) < 64:
        abort(401)

    be_user = BeUser()
    be_user.set("id", user_id)
    be_user.load()

    if not be_user.is_active:
        saved_activation_token = be_user.get("activation_token")
        if len(saved_activation_token) > 64 or len(saved_activation_token) < 64:
            abort(401)
        if saved_activation_token == activation_token:
            be_user.set("ctrl_active", 1)
            be_user.set("activation_token", be_user.generate_activation_token())
            be_user.save()
            flash("Dein Account wurde erfolgreich aktiviert", "success")
    flash("Aktivierung fehlgeschlagen", 'danger')
    return redirect(url_for("backend.login"))


@backend.route("/be_user/delete_be_user/<int:id>", methods=["POST"])
@login_required
def delete_be_user(id=0):
    """

    Args:
        user_id:

    Returns:

    """

    if id > 0:
        user = BeUser()
        user.set("id", id)
        user.load()
        user.delete()

    return render_template("be_user/be_user.html", user=BeUser())


@backend.route("/be_user/edit_be_user/<int:id>", methods=["GET", "POST"])
@login_required
def edit_be_user(id):
    """

    Args:
        user_id:

    Returns:

    """
    form = EditBeUserForm()
    form.id = id
    user = BeUser()
    if id > 0:
        user.set("id", id)
        user.load()
    if request.method == "GET":
        if current_user.is_admin:
            form.init_values(user)
    if request.method == "POST":
        if form.validate_on_submit():
            be_user = BeUser()
            be_user.set_id(current_user.get_id())
            be_user.load()
            be_user.temp_password = escape(request.form["user_password"])
            if be_user.encryption.validate_hash(be_user.get_password(), be_user.temp_password):
                user.prepare_form_input(request.form)
                user.save()
            else:
                flash("Sie haben ein falsches Passwort eingegeben", 'danger')
        else:
            form.get_error_messages()
    return render_template("be_user/edit_be_user.html", id=user.get_id(), form=form, user=user)


@backend.route("/be_user", methods=["GET"])
@login_required
def be_user():
    """

    Returns:

    """
    return render_template("be_user/be_user.html", be_user=BeUser())


@backend.route("/be_user/add_be_user", methods=["GET", "POST"])
@login_required
def add_be_user():
    """

    Returns:

    """
    form = AddBeUserForm()
    if current_user.is_admin:
        if request.method == "POST" and form.validate_on_submit():
            be_user = BeUser()
            username = escape(request.form["username"])
            password = escape(request.form["password"])
            email = escape(request.form["email"])
            token = be_user.generate_activation_token()
            password = be_user.hash_password(password)
            ctrl_access_level = int(request.form["ctrl_access_level"])
            be_user.set_username(username)
            be_user.set_password(password)
            be_user.set_email(email)
            be_user.set_activation_token(token)
            be_user.set_ctrl_access_level(ctrl_access_level)
            if validate_email(be_user.get_email(), verify=True):
                if be_user.register():
                    flash("Der Benutzer wurde erfolgreich hinzugefügt", 'success')
                else:
                    flash("Der Benutzer konnte nicht erstellt werden", 'danger')
            else:
                flash("Diese E-Mail Adresse scheint nicht zu existieren")
        return render_template("be_user/add_be_user.html", form=form)
    flash("Du hast nicht die benötigten Rechte", 'danger')
    return redirect(url_for("backend.dashboard"))


############################################################################
# Failed Login Record
############################################################################

@backend.route("/failed_login_records", methods=["GET"])
@login_required
def failed_login_records():
    """

    Returns:

    """
    if current_user.is_moderator or current_user.is_admin:
        failed_login_record = FailedLoginRecord()
        return render_template("system/failed_login_records.html", failed_login_record=failed_login_record)
    flash("Du hast nicht die benötigten Rechte", "danger")
    return redirect(url_for("backend.dashboard"))


@backend.route("/failed_login_records/delete/<int:id>", methods=["GET"])
@login_required
def delete_failed_login_records(id):
    """

    Args:
        id:

    Returns:

    """
    if current_user.is_admin:
        failed_login_record = FailedLoginRecord()
        failed_login_record.set("id", id)
        failed_login_record.delete()
    return render_template("system/failed_login_records.html", failed_login_record=failed_login_record)


############################################################################
# System Mail
############################################################################

@backend.route("/system_mails", methods=["GET"])
@login_required
def system_mails():
    """

    Returns:

    """
    if current_user.is_moderator or current_user.is_admin:
        system_mail = SystemMail()
        return render_template("system/system_mails.html", system_mail=system_mail)
    flash("Du hast nicht die benötigten Rechte", "danger")
    return redirect(url_for("backend.dashboard"))


############################################################################
# News
############################################################################

@backend.route("/content/news", methods=["GET"])
@login_required
def news():
    """

    Returns:

    """
    return render_template("content/news/news.html", news=News())


@backend.route("/content/news/add_news/", methods=["GET"])
@login_required
def add_news():
    """

    Returns:

    """

    form = NewsEditorForm()
    news = News()
    news.init_default()
    news.save()

    return render_template("content/news/add_news.html", form=form, form_object=news)


@backend.route("/content/news/edit_news/<int:id>", methods=["GET", "POST"])
@login_required
def edit_news(id):
    """

    Returns:

    """
    form = NewsEditorForm()
    news = News()

    if id > 0:
        news.set_id(id)
        news.load()

    if request.method == "GET":
        form.init_values(news)

    if request.method == "POST":
        if form.validate_on_submit():
            news.prepare_form_input(request.form)
            news.save()
        else:
            form.get_error_messages()
    return render_template("content/news/edit_news.html", form=form)


@backend.route("/content/news/delete_news/<int:id>", methods=["POST"])
@login_required
def delete_news(id):
    """

    Returns:

    """

    if id > 0:
        news = News()
        news.set_id(id)
        news.load()
        news.delete()

    return render_template("content/news/news.html", news=News())


############################################################################
# Pages
############################################################################

@backend.route("/content/pages", methods=["GET"])
@login_required
def pages():
    """

    Returns:

    """
    return render_template("content/pages/pages.html", pages=Page())


@backend.route("/content/pages/add_page/", methods=["GET"])
@login_required
def add_page():
    """

    Returns:

    """

    form = PageEditorForm()
    page = Page()
    page.init_default()
    page.save()

    return render_template("content/pages/add_page.html", form=form, form_object=page)


@backend.route("/content/pages/edit_page/<int:id>", methods=["GET", "POST"])
@login_required
def edit_page(id):
    """

    Returns:

    """
    form = PageEditorForm()
    form.id = id
    page = Page()
    form.parent_id.choices = page.get_id_label_list()

    if id > 0:
        page.set_id(id)
        page.load()

    if request.method == "GET":
        form.init_values(page)

    if request.method == "POST":
        if form.validate_on_submit():
            page.prepare_form_input(request.form)
            page.save()
        else:
            form.get_error_messages()
    return render_template("content/pages/edit_page.html", form=form)


@backend.route("/content/pages/delete_page/<int:id>", methods=["GET"])
@login_required
def delete_page(id):
    """

    Returns:

    """

    if id > 0:
        page = Page()
        page.set_id(id)
        page.load()
        page.delete()

    return redirect(url_for("backend.pages"))


############################################################################
# Ajax Handler
############################################################################

@backend.route("/ajax/image_upload", methods=["POST"])
@login_required
def image_upload():
    """

    Returns:

    """
    try:
        if "file" in request.files:
            file = request.files["file"]
            if file and allowed_file(file.filename):

                filename = secure_filename(file.filename)
                id = escape(request.form["id"])
                type = escape(request.form["type"])
                module = escape(request.form["module"])
                max_files = escape(request.form["max_files"])
                max_size = escape(request.form["max_size"])
                image_format = escape(request.form["image_format"])
                """
                z.B: ein page objekt erzeugen die id setzen und laden
                anhand von max_files prüfen ob eine liste benötigt wird
                wenn ja bild hinzufügen. andernfalls mit image_format einfach nur dem wert im
                dataitem setzen
                """

                if module == "pages":
                    module_object = Page()
                    module_object.set_id(id)
                    module_object.load()

                base_path = current_app.config["ROOT_DIR"] + "app/static/"
                final_upload_path = base_path + type + "/" + module + "/" + id + "/"
                print(final_upload_path)
                if not os.path.isdir(final_upload_path):
                    os.makedirs(final_upload_path)

                final_path = os.path.join(final_upload_path, filename)

                if int(max_files) > 1:
                    current_data = module_object.get_list_or_dict(image_format)
                    if len(current_data) < max_files:
                        module_object.add(image_format, final_path)
                    else:
                        return make_response(400)
                else:
                    module_object.set(image_format, final_path)

                file.save(final_path)

                module_object.save()

                return filename
        return make_response(500)
    except Exception as error:
        print(error)


############################################################################
# Unauthorized Handler
############################################################################

@login_manager.unauthorized_handler
def unauthorized():
    """

    Returns:

    """
    return redirect(url_for("backend.login"))


############################################################################
# Load User Callback von Flask_Login
############################################################################

@login_manager.user_loader
def load_user(user_id):
    """
    user loader
    hier wird beim aufruf von login.required dekorierten punkten
    der in der session gespeicherte benutzer geladen wenn vorhanden

    Args:
        user_id:

    Returns:

    """
    if user_id > 0:
        user = BeUser()
        user.set("id", user_id)
        user.load()
        session = Session()
        session.set_user_id(user.get_id())
        if session.load():
            session_user = user.create_session_user()
            ip_address = get_real_ip()
            session_user.ip_address = ip_address
            session_user.user_agent = request.user_agent
            session_user.token = session.get_token()
            session_user.timestamp = session.get_timestamp()
            hash = session.get_user_hash_string(session_user)
            my_logger.debug("session hash: {0}".format(hash))
            if session.is_valid(session.encryption.get_generic_hash(hash)):
                return session_user
            else:
                my_logger.debug("session nicht valid")
                # session.delete()
                pass
    return None
