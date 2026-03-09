import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

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

from .auth import admin_required, current_user, login_required
from .i18n import SUPPORTED_LANGUAGES, detect_language, translate
from .models import AccessCredential, ContactEntry, Phonebook, User, db
from .services import (
    export_phonebook_csv,
    export_phonebook_xml,
    import_phonebook_csv,
    import_phonebook_xml,
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


@web.route("/language/<lang_code>", methods=["POST"])
def set_language(lang_code: str):
    if lang_code in SUPPORTED_LANGUAGES:
        session["lang"] = lang_code
    next_url = request.form.get("next") or url_for("web.index")
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
    return render_template("index.html", books=books)


@web.route("/users")
@admin_required
def users():
    all_users = User.query.order_by(User.username.asc()).all()
    return render_template("users.html", users=all_users)


@web.route("/access")
@admin_required
def access_credentials():
    credentials = AccessCredential.query.order_by(AccessCredential.username.asc()).all()
    return render_template("access.html", credentials=credentials)


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
    db.session.commit()
    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])
    flash(translate(g.lang, "phonebook_updated"), "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/phonebooks/<int:phonebook_id>")
@login_required
def view_phonebook(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)
    entries = phonebook.entries.order_by(ContactEntry.name.asc()).all()

    provisioning_url = f"{current_app.config['BASE_HTTP_URL'].rstrip('/')}/{phonebook.slug}.xml"
    provisioning_url_with_auth = provisioning_url
    first_cred = AccessCredential.query.filter_by(is_active=True).order_by(AccessCredential.id.asc()).first()
    if first_cred:
        provisioning_url_with_auth = provisioning_url.replace(
            "://", f"://{first_cred.username}:<password>@"
        )

    return render_template(
        "phonebook.html",
        phonebook=phonebook,
        entries=entries,
        provisioning_url=provisioning_url,
        provisioning_url_with_auth=provisioning_url_with_auth,
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

    if not name or not any([office, mobile, other]):
        flash(translate(g.lang, "entry_fields_required"), "danger")
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
    db.session.commit()
    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])

    flash(translate(g.lang, "entry_updated"), "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/entries/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(entry_id: int):
    entry = ContactEntry.query.get_or_404(entry_id)
    phonebook = entry.phonebook

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
    if not _basic_auth_allowed():
        return _basic_auth_challenge()

    phonebook = Phonebook.query.filter_by(slug=slug).first()
    if not phonebook:
        abort(404)

    path = Path(current_app.config["EXPORT_DIR"]) / f"{phonebook.slug}.xml"

    if not path.exists():
        export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])

    xml = path.read_text(encoding="utf-8")
    return Response(xml, mimetype="application/xml")


@web.route("/healthz")
def healthz():
    return {"status": "ok", "pid": os.getpid()}


def _basic_auth_allowed() -> bool:
    auth = request.authorization
    if not auth or not auth.username or not auth.password:
        return False

    credential = AccessCredential.query.filter_by(
        username=auth.username,
        is_active=True,
    ).first()
    if not credential:
        return False

    return credential.check_password(auth.password)


def _basic_auth_challenge():
    return Response(
        "Authentication required",
        401,
        {"WWW-Authenticate": 'Basic realm="YeaBook Phonebook"'},
    )
