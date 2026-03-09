import csv
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .models import ContactEntry, Phonebook, db


CSV_COLUMNS = ["name", "office", "mobile", "other", "line", "ring", "group"]


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "phonebook"


def export_phonebook_xml(phonebook: Phonebook, export_dir: str) -> Path:
    root = ET.Element("YealinkIPPhoneDirectory")
    title = ET.SubElement(root, "Title")
    title.text = phonebook.name

    prompt = ET.SubElement(root, "Prompt")
    prompt.text = f"Directory: {phonebook.name}"

    for entry in phonebook.entries.order_by(ContactEntry.name.asc()).all():
        item = ET.SubElement(root, "DirectoryEntry")
        name_node = ET.SubElement(item, "Name")
        name_node.text = entry.name

        # Yealink supports one or more telephone numbers per contact entry.
        for number in [entry.office, entry.mobile, entry.other]:
            if number:
                telephone_node = ET.SubElement(item, "Telephone")
                telephone_node.text = number

    os.makedirs(export_dir, exist_ok=True)
    path = Path(export_dir) / f"{phonebook.slug}.xml"
    tree = ET.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path


def import_phonebook_xml(phonebook: Phonebook, xml_path: Path, replace_existing: bool = False) -> int:
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid XML file: {exc}") from exc

    root = tree.getroot()
    valid_roots = {"YealinkIPPhoneDirectory", "YealinkIPPhoneBook"}
    if root.tag not in valid_roots:
        raise ValueError("Invalid Yealink XML: root element must be YealinkIPPhoneDirectory or YealinkIPPhoneBook")

    if replace_existing:
        ContactEntry.query.filter_by(phonebook_id=phonebook.id).delete()

    inserted = 0
    for item in root.findall("DirectoryEntry"):
        name = (item.findtext("Name") or "").strip()
        numbers = [
            (node.text or "").strip()
            for node in item.findall("Telephone")
            if (node.text or "").strip()
        ]

        if not name or not numbers:
            continue

        office = numbers[0] if len(numbers) > 0 else None
        mobile = numbers[1] if len(numbers) > 1 else None
        other = numbers[2] if len(numbers) > 2 else None

        db.session.add(
            ContactEntry(
                phonebook_id=phonebook.id,
                name=name,
                office=office,
                mobile=mobile,
                other=other,
            )
        )
        inserted += 1

    db.session.commit()
    return inserted


def export_phonebook_csv(phonebook: Phonebook, export_path: Path) -> Path:
    with export_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for entry in phonebook.entries.order_by(ContactEntry.name.asc()).all():
            writer.writerow(
                {
                    "name": entry.name,
                    "office": entry.office or "",
                    "mobile": entry.mobile or "",
                    "other": entry.other or "",
                    "line": entry.line or "",
                    "ring": entry.ring or "",
                    "group": entry.group or "",
                }
            )
    return export_path


def import_phonebook_csv(phonebook: Phonebook, csv_path: Path) -> int:
    inserted = 0
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = (row.get("name") or "").strip()
            office = (row.get("office") or "").strip() or None
            mobile = (row.get("mobile") or "").strip() or None
            other = (row.get("other") or "").strip() or None
            line = (row.get("line") or "").strip() or None
            ring = (row.get("ring") or "").strip() or None
            group = (row.get("group") or "").strip() or None

            if not name or not any([office, mobile, other]):
                continue

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
            inserted += 1

    db.session.commit()
    return inserted