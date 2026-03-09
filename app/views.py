import os
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.exceptions import HTTPException

from .auth import admin_required, current_user, login_required
from .i18n import SUPPORTED_LANGUAGES, detect_language, translate
from .models import (
    AccessCredential,
    AccessCredentialPhonebook,
    ContactEntry,
    Phonebook,
    PhonebookSettings,
    User,
    db,
)
from .services import (
    export_phonebook_csv,
    export_phonebook_xml,
    delete_contact_photo,
    import_phonebook_csv,
    import_phonebook_xml,
    render_directory_xml,
    render_menu_xml,
    save_contact_photo,
    DEFAULT_PHOTO_FILENAME,
    slugify,
)


web = Blueprint("web", __name__)


@web.before_app_request
def inject_current_user():
    g.user = current_user()
    g.lang = detect_language()


@web.app_context_processor
def inject_i18n():
    return {
        "tr": lambda key, **kwargs: translate(g.lang, key, **kwargs),
        "lang": g.lang,
        "supported_languages": SUPPORTED_LANGUAGES,
    }


@web.app_errorhandler(404)
def handle_not_found(error):
    return _render_error_page(404)


@web.app_errorhandler(403)
def handle_forbidden(error):
    return _render_error_page(403)


@web.app_errorhandler(500)
def handle_server_error(error):
    return _render_error_page(500)


@web.app_errorhandler(Exception)
def handle_unexpected_error(error):
    if isinstance(error, HTTPException):
        return _render_error_page(error.code or 500)
    current_app.logger.exception("Unhandled application error", exc_info=error)
    return _render_error_page(500)


@web.route("/language/<lang_code>", methods=["GET", "POST"])
def set_language(lang_code: str):
    if lang_code in SUPPORTED_LANGUAGES:
        session["lang"] = lang_code
    next_url = request.values.get("next") or url_for("web.index")
    parsed = urlparse(next_url)
    if parsed.netloc or parsed.scheme:
        next_url = url_for("web.index")
    return redirect(next_url)


@web.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        flash(translate(g.lang, "invalid_credentials"), "danger")
        return redirect(url_for("web.login"))

    session["user_id"] = user.id
    flash(translate(g.lang, "signed_in"), "success")
    return redirect(url_for("web.index"))


@web.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash(translate(g.lang, "signed_out"), "success")
    return redirect(url_for("web.login"))


@web.route("/")
@login_required
def index():
    books = Phonebook.query.order_by(Phonebook.name.asc()).all()
    book_rows = [{"book": book, "entry_count": book.entries.count()} for book in books]
    return render_template("index.html", books=book_rows)


@web.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.username.asc()).all()
    return render_template("users.html", users=all_users)


@web.route("/access")
@admin_required
def access_credentials():
    credentials = AccessCredential.query.order_by(AccessCredential.username.asc()).all()
    phonebooks = Phonebook.query.order_by(Phonebook.name.asc()).all()
    assigned_map: dict[int, set[int]] = {}
    for cred in credentials:
        assigned_map[cred.id] = {p.phonebook_id for p in cred.permissions.all()}
    return render_template(
        "access.html",
        credentials=credentials,
        phonebooks=phonebooks,
        assigned_map=assigned_map,
    )


@web.route("/users", methods=["POST"])
@admin_required
def create_user():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    is_admin = request.form.get("is_admin") == "on"

    if not username or not password:
        flash(translate(g.lang, "username_password_required"), "danger")
        return redirect(url_for("web.users"))

    if User.query.filter_by(username=username).first():
        flash(translate(g.lang, "username_exists"), "danger")
        return redirect(url_for("web.users"))

    user = User(
        username=username,
        is_admin=is_admin,
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()
    flash(translate(g.lang, "user_created"), "success")
    return redirect(url_for("web.users"))


@web.route("/access", methods=["POST"])
@admin_required
def create_access_credential():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    is_active = request.form.get("is_active") == "on"

    if not username or not password:
        flash(translate(g.lang, "username_password_required"), "danger")
        return redirect(url_for("web.access_credentials"))

    if AccessCredential.query.filter_by(username=username).first():
        flash(translate(g.lang, "username_exists"), "danger")
        return redirect(url_for("web.access_credentials"))

    cred = AccessCredential(username=username, is_active=is_active)
    cred.set_password(password)
    db.session.add(cred)
    db.session.flush()
    _set_credential_permissions(cred.id, request.form.getlist("phonebook_ids"))
    db.session.commit()
    flash(translate(g.lang, "access_credential_created"), "success")
    return redirect(url_for("web.access_credentials"))


@web.route("/access/<int:credential_id>/delete", methods=["POST"])
@admin_required
def delete_access_credential(credential_id: int):
    credential = AccessCredential.query.get_or_404(credential_id)
    db.session.delete(credential)
    db.session.commit()
    flash(translate(g.lang, "access_credential_deleted"), "success")
    return redirect(url_for("web.access_credentials"))


@web.route("/access/<int:credential_id>/toggle", methods=["POST"])
@admin_required
def toggle_access_credential(credential_id: int):
    credential = AccessCredential.query.get_or_404(credential_id)
    credential.is_active = not credential.is_active
    db.session.commit()
    flash(translate(g.lang, "access_credential_updated"), "success")
    return redirect(url_for("web.access_credentials"))


@web.route("/access/<int:credential_id>/phonebooks", methods=["POST"])
@admin_required
def update_access_credential_phonebooks(credential_id: int):
    credential = AccessCredential.query.get_or_404(credential_id)
    _set_credential_permissions(credential.id, request.form.getlist("phonebook_ids"))
    db.session.commit()
    flash(translate(g.lang, "permissions_updated"), "success")
    return redirect(url_for("web.access_credentials"))


@web.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id: int):
    user = User.query.get_or_404(user_id)
    me = current_user()

    if me and user.id == me.id:
        flash(translate(g.lang, "cannot_delete_self"), "danger")
        return redirect(url_for("web.users"))

    db.session.delete(user)
    db.session.commit()
    flash(translate(g.lang, "user_deleted"), "success")
    return redirect(url_for("web.users"))


@web.route("/phonebooks", methods=["POST"])
@login_required
def create_phonebook():
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip() or None
    category = (request.form.get("category") or "private").strip().lower()
    if category not in {"private", "business"}:
        category = "private"

    if not name:
        flash(translate(g.lang, "phonebook_name_required"), "danger")
        return redirect(url_for("web.index"))

    base_slug = slugify(name)
    slug = base_slug
    counter = 1
    while Phonebook.query.filter_by(slug=slug).first():
        counter += 1
        slug = f"{base_slug}-{counter}"

    phonebook = Phonebook(name=name, slug=slug, description=description)
    db.session.add(phonebook)
    db.session.flush()
    db.session.add(PhonebookSettings(phonebook_id=phonebook.id, category=category))
    db.session.commit()

    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])
    flash(translate(g.lang, "phonebook_created"), "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/phonebooks/<int:phonebook_id>/edit", methods=["POST"])
@login_required
def edit_phonebook(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip() or None
    category = (request.form.get("category") or "private").strip().lower()
    if category not in {"private", "business"}:
        category = "private"

    if not name:
        flash(translate(g.lang, "phonebook_name_required"), "danger")
        return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))

    duplicate = Phonebook.query.filter(
        Phonebook.name == name,
        Phonebook.id != phonebook.id,
    ).first()
    if duplicate:
        flash(translate(g.lang, "phonebook_name_exists"), "danger")
        return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))

    phonebook.name = name
    phonebook.description = description
    if phonebook.settings:
        phonebook.settings.category = category
    else:
        db.session.add(PhonebookSettings(phonebook_id=phonebook.id, category=category))
    db.session.commit()
    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])
    flash(translate(g.lang, "phonebook_updated"), "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/phonebooks/<int:phonebook_id>/delete", methods=["POST"])
@login_required
def delete_phonebook(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)
    confirm_slug = (request.form.get("confirm_slug") or "").strip()
    if confirm_slug != phonebook.slug:
        flash(translate(g.lang, "confirm_slug_mismatch"), "danger")
        return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))

    for entry in phonebook.entries.all():
        delete_contact_photo(Path(current_app.config["PHOTO_DIR"]), entry.photo_filename)

    db.session.delete(phonebook)
    db.session.commit()
    flash(translate(g.lang, "phonebook_deleted"), "success")
    return redirect(url_for("web.index"))


@web.route("/phonebooks/<int:phonebook_id>/photos.zip")
@login_required
def phonebook_photos_zip(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)
    photo_dir = Path(current_app.config["PHOTO_DIR"])
    entries = phonebook.entries.order_by(ContactEntry.name.asc()).all()

    with tempfile.NamedTemporaryFile(prefix="photos-", suffix=".zip", delete=False) as tmp:
        zip_path = Path(tmp.name)

    with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in entries:
            effective_name = entry.photo_filename or DEFAULT_PHOTO_FILENAME
            source = photo_dir / effective_name
            if not source.exists():
                continue
            safe_name = slugify(entry.name)
            archive_name = f"{phonebook.slug}/{entry.id}-{safe_name}.jpg"
            archive.write(source, arcname=archive_name)

    return send_file(
        zip_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{phonebook.slug}-photos.zip",
    )


@web.route("/phonebooks/<int:phonebook_id>")
@login_required
def view_phonebook(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)
    entries = phonebook.entries.order_by(ContactEntry.name.asc()).all()
    category = (
        phonebook.settings.category
        if phonebook.settings and phonebook.settings.category in {"private", "business"}
        else "private"
    )

    provisioning_url = f"{current_app.config['BASE_HTTP_URL'].rstrip('/')}/{phonebook.slug}.xml"
    provisioning_url_with_auth = provisioning_url
    first_cred = AccessCredential.query.filter_by(is_active=True).order_by(AccessCredential.id.asc()).first()
    if first_cred:
        provisioning_url_with_auth = provisioning_url.replace(
            "://", f"://{first_cred.username}:<password>@"
        )
    photo_urls = {entry.id: _build_photo_url(phonebook.slug, entry) for entry in entries}
    photo_entries = entries

    return render_template(
        "phonebook.html",
        phonebook=phonebook,
        entries=entries,
        category=category,
        grouped_entries=_group_entries(entries) if category == "business" else [],
        provisioning_url=provisioning_url,
        provisioning_url_with_auth=provisioning_url_with_auth,
        photo_urls=photo_urls,
        photo_entries=photo_entries,
    )


@web.route("/phonebooks/<int:phonebook_id>/entries", methods=["POST"])
@login_required
def add_entry(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)

    name = (request.form.get("name") or "").strip()
    office = (request.form.get("office") or "").strip() or None
    mobile = (request.form.get("mobile") or "").strip() or None
    other = (request.form.get("other") or "").strip() or None
    line = (request.form.get("line") or "").strip() or None
    ring = (request.form.get("ring") or "").strip() or None
    group = (request.form.get("group") or "").strip() or None
    photo_data = (request.form.get("photo_data") or "").strip()
    photo_filename = None
    if not _is_business_phonebook(phonebook):
        group = None

    if not name or not any([office, mobile, other]):
        flash(translate(g.lang, "entry_fields_required"), "danger")
        return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))

    if photo_data:
        try:
            photo_filename = save_contact_photo(photo_data, Path(current_app.config["PHOTO_DIR"]))
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))

    db.session.add(
        ContactEntry(
            phonebook_id=phonebook.id,
            name=name,
            office=office,
            mobile=mobile,
            other=other,
            line=line,
            ring=ring,
            group=group,
            photo_filename=photo_filename,
        )
    )
    db.session.commit()
    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])

    flash(translate(g.lang, "entry_added"), "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/entries/<int:entry_id>/edit", methods=["POST"])
@login_required
def edit_entry(entry_id: int):
    entry = ContactEntry.query.get_or_404(entry_id)
    phonebook = entry.phonebook

    name = (request.form.get("name") or "").strip()
    office = (request.form.get("office") or "").strip() or None
    mobile = (request.form.get("mobile") or "").strip() or None
    other = (request.form.get("other") or "").strip() or None
    line = (request.form.get("line") or "").strip() or None
    ring = (request.form.get("ring") or "").strip() or None
    group = (request.form.get("group") or "").strip() or None
    photo_data = (request.form.get("photo_data") or "").strip()
    remove_photo = request.form.get("remove_photo") == "on"
    if not _is_business_phonebook(phonebook):
        group = None

    if not name or not any([office, mobile, other]):
        flash(translate(g.lang, "entry_fields_required"), "danger")
        return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))

    entry.name = name
    entry.office = office
    entry.mobile = mobile
    entry.other = other
    entry.line = line
    entry.ring = ring
    entry.group = group
    if remove_photo and entry.photo_filename:
        delete_contact_photo(Path(current_app.config["PHOTO_DIR"]), entry.photo_filename)
        entry.photo_filename = None
    if photo_data:
        try:
            new_filename = save_contact_photo(photo_data, Path(current_app.config["PHOTO_DIR"]))
        except ValueError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))
        delete_contact_photo(Path(current_app.config["PHOTO_DIR"]), entry.photo_filename)
        entry.photo_filename = new_filename
    db.session.commit()
    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])

    flash(translate(g.lang, "entry_updated"), "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/entries/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(entry_id: int):
    entry = ContactEntry.query.get_or_404(entry_id)
    phonebook = entry.phonebook

    delete_contact_photo(Path(current_app.config["PHOTO_DIR"]), entry.photo_filename)
    db.session.delete(entry)
    db.session.commit()
    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])

    flash(translate(g.lang, "entry_deleted"), "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/phonebooks/<int:phonebook_id>/csv/export")
@login_required
def csv_export(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)
    with tempfile.NamedTemporaryFile(prefix="export-", suffix=".csv", delete=False) as tmp:
        temp_path = Path(tmp.name)

    export_phonebook_csv(phonebook, temp_path)
    return send_file(
        temp_path,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"{phonebook.slug}.csv",
    )


@web.route("/phonebooks/<int:phonebook_id>/csv/import", methods=["POST"])
@login_required
def csv_import(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)
    upload = request.files.get("csv_file")

    if not upload or not upload.filename:
        flash(translate(g.lang, "select_csv"), "danger")
        return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))

    with tempfile.NamedTemporaryFile(prefix="import-", suffix=".csv", delete=False) as tmp:
        upload.save(tmp.name)
        temp_path = Path(tmp.name)

    inserted = import_phonebook_csv(phonebook, temp_path)
    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])

    flash(translate(g.lang, "imported_entries", count=inserted), "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/phonebooks/<int:phonebook_id>/xml/export")
@login_required
def xml_export(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)
    path = export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])
    return send_file(
        path,
        mimetype="application/xml",
        as_attachment=True,
        download_name=f"{phonebook.slug}.xml",
    )


@web.route("/phonebooks/<int:phonebook_id>/xml/import", methods=["POST"])
@login_required
def xml_import(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)
    upload = request.files.get("xml_file")

    if not upload or not upload.filename:
        flash(translate(g.lang, "select_xml"), "danger")
        return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))

    with tempfile.NamedTemporaryFile(prefix="import-", suffix=".xml", delete=False) as tmp:
        upload.save(tmp.name)
        temp_path = Path(tmp.name)

    replace_existing = request.form.get("replace_existing") == "on"

    try:
        inserted = import_phonebook_xml(phonebook, temp_path, replace_existing=replace_existing)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))

    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])
    flash(translate(g.lang, "imported_entries_xml", count=inserted), "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/api/phonebooks/<slug>.xml")
@web.route("/<slug>.xml")
def phonebook_xml(slug: str):
    credential = _authorized_credential()
    if not credential:
        return _basic_auth_challenge()

    phonebook = Phonebook.query.filter_by(slug=slug).first()
    if not phonebook:
        abort(404)

    allowed = AccessCredentialPhonebook.query.filter_by(
        credential_id=credential.id,
        phonebook_id=phonebook.id,
    ).first()
    if not allowed:
        return Response(translate(g.lang, "forbidden"), 403)

    entries = phonebook.entries.order_by(ContactEntry.name.asc()).all()
    is_business = _is_business_phonebook(phonebook)

    if is_business:
        departments = sorted(
            {(entry.group or "General").strip() or "General" for entry in entries},
            key=lambda name: name.lower(),
        )
        base = current_app.config["BASE_HTTP_URL"].rstrip("/")
        items = []
        for dept in departments:
            dept_slug = slugify(dept)
            token = _issue_submenu_token(
                credential_id=credential.id,
                phonebook_id=phonebook.id,
                department_slug=dept_slug,
            )
            items.append(
                (
                    dept,
                    f"{base}/{phonebook.slug}/departments/{dept_slug}.xml?token={token}",
                )
            )
        xml = render_menu_xml(
            title_text=phonebook.name,
            prompt_text=f"Departments: {phonebook.name}",
            items=items,
        )
        return Response(xml, mimetype="application/xml")

    photo_urls = _photo_urls_for_entries(phonebook.slug, entries)
    xml = render_directory_xml(
        title_text=phonebook.name,
        prompt_text=f"Directory: {phonebook.name}",
        entries=entries,
        include_group=False,
        photo_urls=photo_urls,
    )
    return Response(xml, mimetype="application/xml")


@web.route("/api/phonebooks/<slug>/departments/<dept_slug>.xml")
@web.route("/<slug>/departments/<dept_slug>.xml")
def phonebook_department_xml(slug: str, dept_slug: str):
    phonebook = Phonebook.query.filter_by(slug=slug).first()
    if not phonebook:
        abort(404)

    credential = _authorized_credential()
    token_data = _verify_submenu_token(request.args.get("token", ""))
    access_ok = False

    if credential:
        allowed = AccessCredentialPhonebook.query.filter_by(
            credential_id=credential.id,
            phonebook_id=phonebook.id,
        ).first()
        access_ok = bool(allowed)

    if not access_ok and token_data:
        access_ok = (
            token_data.get("phonebook_id") == phonebook.id
            and token_data.get("department_slug") == dept_slug
            and AccessCredentialPhonebook.query.filter_by(
                credential_id=token_data.get("credential_id"),
                phonebook_id=phonebook.id,
            ).first()
            is not None
        )

    if not access_ok:
        return _basic_auth_challenge()

    if not _is_business_phonebook(phonebook):
        return Response(translate(g.lang, "forbidden"), 403)

    entries = phonebook.entries.order_by(ContactEntry.name.asc()).all()
    departments = {}
    for entry in entries:
        dept = (entry.group or "General").strip() or "General"
        departments[slugify(dept)] = dept

    dept_name = departments.get(dept_slug)
    if not dept_name:
        abort(404)

    filtered = [e for e in entries if ((e.group or "General").strip() or "General") == dept_name]
    photo_urls = _photo_urls_for_entries(phonebook.slug, filtered)
    xml = render_directory_xml(
        title_text=f"{phonebook.name} - {dept_name}",
        prompt_text=f"Department: {dept_name}",
        entries=filtered,
        include_group=True,
        photo_urls=photo_urls,
    )
    return Response(xml, mimetype="application/xml")


@web.route("/api/phonebooks/<slug>/photos/<photo_name>")
@web.route("/<slug>/photos/<photo_name>")
def photo_file(slug: str | None = None, photo_name: str | None = None):
    token_data = _verify_photo_token(request.args.get("token", ""))
    if not token_data:
        return _basic_auth_challenge()

    phonebook = Phonebook.query.filter_by(slug=slug).first()
    if not phonebook:
        abort(404)

    if token_data.get("phonebook_id") != phonebook.id:
        return Response(translate(g.lang, "forbidden"), 403)
    if token_data.get("photo_name") != photo_name:
        return Response(translate(g.lang, "forbidden"), 403)

    entry = ContactEntry.query.get(token_data.get("entry_id"))
    if not entry or entry.phonebook_id != phonebook.id:
        abort(404)
    expected = entry.photo_filename or DEFAULT_PHOTO_FILENAME
    if expected != photo_name:
        abort(404)

    path = Path(current_app.config["PHOTO_DIR"]) / photo_name
    if not path.exists():
        abort(404)
    return send_file(path, mimetype="image/jpeg")


@web.route("/healthz")
def healthz():
    return {"status": "ok", "pid": os.getpid()}


def _authorized_credential() -> AccessCredential | None:
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return None

    credential = AccessCredential.query.filter_by(
        username=auth.username,
        is_active=True,
    ).first()
    if not credential:
        return None

    return credential if credential.check_password(auth.password) else None


def _basic_auth_challenge():
    return Response(
        "Authentication required",
        401,
        {"WWW-Authenticate": 'Basic realm="YeaBook Phonebook"'},
    )


def _group_entries(entries: list[ContactEntry]) -> list[tuple[str, list[ContactEntry]]]:
    grouped: dict[str, list[ContactEntry]] = {}
    for entry in entries:
        key = (entry.group or "General").strip() or "General"
        grouped.setdefault(key, []).append(entry)
    return sorted(grouped.items(), key=lambda item: item[0].lower())


def _is_business_phonebook(phonebook: Phonebook) -> bool:
    return bool(phonebook.settings and phonebook.settings.category == "business")


def _set_credential_permissions(credential_id: int, phonebook_ids: list[str]) -> None:
    AccessCredentialPhonebook.query.filter_by(credential_id=credential_id).delete()
    for raw_id in phonebook_ids:
        try:
            phonebook_id = int(raw_id)
        except ValueError:
            continue
        exists = Phonebook.query.get(phonebook_id)
        if exists:
            db.session.add(
                AccessCredentialPhonebook(
                    credential_id=credential_id,
                    phonebook_id=phonebook_id,
                )
            )


def _token_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="submenu-token")


def _issue_submenu_token(credential_id: int, phonebook_id: int, department_slug: str) -> str:
    payload = {
        "credential_id": credential_id,
        "phonebook_id": phonebook_id,
        "department_slug": department_slug,
    }
    return _token_serializer().dumps(payload)


def _verify_submenu_token(token: str) -> dict | None:
    if not token:
        return None
    try:
        return _token_serializer().loads(token, max_age=3600)
    except (BadSignature, SignatureExpired):
        return None


def _photo_token_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="photo-token")


def _issue_photo_token(phonebook_id: int, entry_id: int, photo_name: str) -> str:
    payload = {
        "phonebook_id": phonebook_id,
        "entry_id": entry_id,
        "photo_name": photo_name,
    }
    return _photo_token_serializer().dumps(payload)


def _verify_photo_token(token: str) -> dict | None:
    if not token:
        return None
    try:
        return _photo_token_serializer().loads(token, max_age=3600)
    except (BadSignature, SignatureExpired):
        return None


def _photo_urls_for_entries(phonebook_slug: str, entries: list[ContactEntry]) -> dict[int, str]:
    urls: dict[int, str] = {}
    for entry in entries:
        urls[entry.id] = _build_photo_url(phonebook_slug, entry)
    return urls


def _build_photo_url(phonebook_slug: str, entry: ContactEntry) -> str:
    photo_name = entry.photo_filename or DEFAULT_PHOTO_FILENAME
    token = _issue_photo_token(entry.phonebook_id, entry.id, photo_name)
    base = current_app.config["BASE_HTTP_URL"].rstrip("/")
    return f"{base}/{phonebook_slug}/photos/{photo_name}?token={token}"


def _render_error_page(status_code: int):
    if _prefer_plain_error_response():
        text_map = {
            403: "Forbidden",
            404: "Not Found",
            500: "Internal Server Error",
        }
        return Response(text_map.get(status_code, "Error"), status_code, mimetype="text/plain")

    title_map = {
        403: "error_403_title",
        404: "error_404_title",
        500: "error_500_title",
    }
    message_map = {
        403: "error_403_message",
        404: "error_404_message",
        500: "error_500_message",
    }

    title_key = title_map.get(status_code, "error_page_title")
    message_key = message_map.get(status_code, "error_default_message")

    return (
        render_template(
            "error.html",
            status_code=status_code,
            error_title=translate(g.lang, title_key),
            error_message=translate(g.lang, message_key),
        ),
        status_code,
    )


def _prefer_plain_error_response() -> bool:
    path = (request.path or "").lower()
    if path.endswith(".xml"):
        return True
    best = request.accept_mimetypes.best
    return best in {"application/xml", "text/xml", "application/json"}
