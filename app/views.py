import os
import tempfile
from pathlib import Path

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
from .models import ContactEntry, Phonebook, User, db
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


@web.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        flash("Invalid credentials.", "danger")
        return redirect(url_for("web.login"))

    session["user_id"] = user.id
    flash("Signed in.", "success")
    return redirect(url_for("web.index"))


@web.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("Signed out.", "success")
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


@web.route("/users", methods=["POST"])
@admin_required
def create_user():
    username = (request.form.get("username") or "").strip()
    password = (request.form.get("password") or "").strip()
    is_admin = request.form.get("is_admin") == "on"

    ftp_enabled = request.form.get("ftp_enabled") == "on"
    ftp_username = (request.form.get("ftp_username") or "").strip() or None
    ftp_password = (request.form.get("ftp_password") or "").strip()

    if not username or not password:
        flash("Username and password are required.", "danger")
        return redirect(url_for("web.users"))

    if User.query.filter_by(username=username).first():
        flash("Username already exists.", "danger")
        return redirect(url_for("web.users"))

    if ftp_enabled and (not ftp_username or not ftp_password):
        flash("FTP username and password are required when FTP is enabled.", "danger")
        return redirect(url_for("web.users"))

    if ftp_username and User.query.filter_by(ftp_username=ftp_username).first():
        flash("FTP username already exists.", "danger")
        return redirect(url_for("web.users"))

    user = User(
        username=username,
        is_admin=is_admin,
        ftp_enabled=ftp_enabled,
        ftp_username=ftp_username,
    )
    user.set_password(password)
    if ftp_enabled and ftp_password:
        user.set_ftp_password(ftp_password)

    db.session.add(user)
    db.session.commit()
    flash("User created.", "success")
    return redirect(url_for("web.users"))


@web.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id: int):
    user = User.query.get_or_404(user_id)
    me = current_user()

    if me and user.id == me.id:
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("web.users"))

    db.session.delete(user)
    db.session.commit()
    flash("User deleted.", "success")
    return redirect(url_for("web.users"))


@web.route("/phonebooks", methods=["POST"])
@login_required
def create_phonebook():
    name = (request.form.get("name") or "").strip()
    description = (request.form.get("description") or "").strip() or None

    if not name:
        flash("Phonebook name is required.", "danger")
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
    flash("Phonebook created.", "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/phonebooks/<int:phonebook_id>")
@login_required
def view_phonebook(phonebook_id: int):
    phonebook = Phonebook.query.get_or_404(phonebook_id)
    entries = phonebook.entries.order_by(ContactEntry.name.asc()).all()

    ftp_path = f"/{phonebook.slug}.xml"
    provisioning_url = f"{current_app.config['BASE_HTTP_URL'].rstrip('/')}/{phonebook.slug}.xml"
    username = (current_app.config.get("PROVISION_USERNAME") or "").strip()
    password = (current_app.config.get("PROVISION_PASSWORD") or "").strip()
    provisioning_url_with_auth = provisioning_url
    if username and password:
        provisioning_url_with_auth = provisioning_url.replace(
            "://", f"://{username}:{password}@"
        )

    return render_template(
        "phonebook.html",
        phonebook=phonebook,
        entries=entries,
        ftp_path=ftp_path,
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
        flash("Name and at least one phone number are required.", "danger")
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

    flash("Entry added.", "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/entries/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_entry(entry_id: int):
    entry = ContactEntry.query.get_or_404(entry_id)
    phonebook = entry.phonebook

    db.session.delete(entry)
    db.session.commit()
    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])

    flash("Entry deleted.", "success")
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
        flash("Please select a CSV file.", "danger")
        return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))

    with tempfile.NamedTemporaryFile(prefix="import-", suffix=".csv", delete=False) as tmp:
        upload.save(tmp.name)
        temp_path = Path(tmp.name)

    inserted = import_phonebook_csv(phonebook, temp_path)
    export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])

    flash(f"Imported {inserted} entries.", "success")
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
        flash("Please select an XML file.", "danger")
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
    flash(f"Imported {inserted} entries from XML.", "success")
    return redirect(url_for("web.view_phonebook", phonebook_id=phonebook.id))


@web.route("/api/phonebooks/<slug>.xml")
@web.route("/<slug>.xml")
def phonebook_xml(slug: str):
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
