from __future__ import annotations

from datetime import datetime, timedelta

from flask import current_app

from .models import ContactEntry, Phonebook, SyncProfile, db
from .secrets import decrypt_secret, encrypt_secret
from .services import export_phonebook_xml
from .yealink_ax86r import YealinkAX86RClient


def create_sync_profile(
    *,
    name: str,
    phonebook_id: int,
    phone_host: str,
    web_username: str,
    web_password: str,
    verify_tls: bool,
    interval_minutes: int,
    enabled: bool,
) -> SyncProfile:
    secret_key = current_app.config["SECRET_KEY"]
    profile = SyncProfile(
        name=name.strip(),
        phonebook_id=phonebook_id,
        phone_host=_normalize_host(phone_host),
        web_username=web_username.strip(),
        web_password_enc=encrypt_secret(web_password, secret_key),
        verify_tls=verify_tls,
        interval_minutes=max(1, int(interval_minutes)),
        enabled=enabled,
        next_run_at=_compute_next_run(datetime.utcnow(), interval_minutes) if enabled else None,
    )
    db.session.add(profile)
    db.session.commit()
    return profile


def update_sync_profile(
    profile: SyncProfile,
    *,
    name: str,
    phonebook_id: int,
    phone_host: str,
    web_username: str,
    web_password: str | None,
    verify_tls: bool,
    interval_minutes: int,
    enabled: bool,
) -> None:
    profile.name = name.strip()
    profile.phonebook_id = phonebook_id
    profile.phone_host = _normalize_host(phone_host)
    profile.web_username = web_username.strip()
    if web_password:
        profile.web_password_enc = encrypt_secret(web_password, current_app.config["SECRET_KEY"])
    profile.verify_tls = verify_tls
    profile.interval_minutes = max(1, int(interval_minutes))
    profile.enabled = enabled
    profile.next_run_at = _compute_next_run(datetime.utcnow(), profile.interval_minutes) if enabled else None
    db.session.commit()


def run_profile_sync(profile: SyncProfile) -> int:
    now = datetime.utcnow()
    try:
        phonebook = Phonebook.query.get(profile.phonebook_id)
        if not phonebook:
            raise ValueError("Linked phonebook not found.")

        web_password = decrypt_secret(profile.web_password_enc, current_app.config["SECRET_KEY"])
        client = YealinkAX86RClient(
            base_url=profile.phone_host,
            username=profile.web_username,
            password=web_password,
            verify_tls=profile.verify_tls,
        )
        contacts = client.fetch_local_contacts()
        imported = _replace_phonebook_entries(phonebook, contacts)
        export_phonebook_xml(phonebook, current_app.config["EXPORT_DIR"])

        profile.last_run_at = now
        profile.last_status = "ok"
        profile.last_message = f"Imported {imported} contacts."
        if profile.enabled:
            profile.next_run_at = _compute_next_run(now, profile.interval_minutes)
        db.session.commit()
        return imported
    except Exception as exc:
        profile.last_run_at = now
        profile.last_status = "error"
        profile.last_message = str(exc)[:250]
        if profile.enabled:
            profile.next_run_at = _compute_next_run(now, profile.interval_minutes)
        db.session.commit()
        raise


def run_due_syncs(now: datetime | None = None) -> int:
    run_time = now or datetime.utcnow()
    due = (
        SyncProfile.query.filter_by(enabled=True)
        .filter(SyncProfile.next_run_at.isnot(None))
        .filter(SyncProfile.next_run_at <= run_time)
        .all()
    )
    count = 0
    for profile in due:
        try:
            run_profile_sync(profile)
        except Exception:
            pass
        count += 1
    return count


def _replace_phonebook_entries(phonebook: Phonebook, contacts: list[dict[str, str | None]]) -> int:
    ContactEntry.query.filter_by(phonebook_id=phonebook.id).delete()

    is_business = bool(phonebook.settings and phonebook.settings.category == "business")
    inserted = 0
    for item in contacts:
        office = item.get("office")
        mobile = item.get("mobile")
        other = item.get("other")
        if not any([office, mobile, other]):
            continue
        group = item.get("group")
        if not is_business:
            group = None
        db.session.add(
            ContactEntry(
                phonebook_id=phonebook.id,
                name=(item.get("name") or "").strip(),
                office=office,
                mobile=mobile,
                other=other,
                line=item.get("line"),
                group=group,
            )
        )
        inserted += 1
    db.session.commit()
    return inserted


def _normalize_host(phone_host: str) -> str:
    host = (phone_host or "").strip()
    if not host:
        raise ValueError("Phone host is required.")
    if not host.startswith("http://") and not host.startswith("https://"):
        host = f"https://{host}"
    return host.rstrip("/")


def _compute_next_run(base: datetime, interval_minutes: int) -> datetime:
    return base + timedelta(minutes=max(1, int(interval_minutes)))
