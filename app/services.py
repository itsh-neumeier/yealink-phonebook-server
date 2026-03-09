import csv
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .models import ContactEntry, Phonebook, db


CSV_COLUMNS = ["name", "office", "mobile", "other", "line", "group"]


def slugify(value: str) -> str:
    normalized = (
        value.strip()
        .replace("Ä", "Ae")
        .replace("Ö", "Oe")
        .replace("Ü", "Ue")
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "phonebook"


def export_phonebook_xml(phonebook: Phonebook, export_dir: str) -> Path:
    root = ET.Element("YealinkIPPhoneDirectory")
    is_business = bool(phonebook.settings and phonebook.settings.category == "business")
    title = ET.SubElement(root, "Title")
    title.text = phonebook.name

    prompt = ET.SubElement(root, "Prompt")
    prompt.text = f"Directory: {phonebook.name}"

    for entry in phonebook.entries.order_by(ContactEntry.name.asc()).all():
        item = ET.SubElement(root, "DirectoryEntry")
        name_node = ET.SubElement(item, "Name")
        name_node.text = entry.name

        for number in [entry.office, entry.mobile, entry.other]:
            if number:
                telephone_node = ET.SubElement(item, "Telephone")
                telephone_node.text = number

        if is_business and entry.group:
            group_node = ET.SubElement(item, "Group")
            group_node.text = entry.group

    os.makedirs(export_dir, exist_ok=True)
    path = Path(export_dir) / f"{phonebook.slug}.xml"
    tree = ET.ElementTree(root)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path


def render_directory_xml(title_text: str, prompt_text: str, entries: list[ContactEntry], include_group: bool) -> str:
    root = ET.Element("YealinkIPPhoneDirectory")
    title = ET.SubElement(root, "Title")
    title.text = title_text
    prompt = ET.SubElement(root, "Prompt")
    prompt.text = prompt_text

    for entry in entries:
        item = ET.SubElement(root, "DirectoryEntry")
        name_node = ET.SubElement(item, "Name")
        name_node.text = entry.name
        for number in [entry.office, entry.mobile, entry.other]:
            if number:
                telephone_node = ET.SubElement(item, "Telephone")
                telephone_node.text = number
        if include_group and entry.group:
            group_node = ET.SubElement(item, "Group")
            group_node.text = entry.group

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def render_menu_xml(title_text: str, prompt_text: str, items: list[tuple[str, str]]) -> str:
    root = ET.Element("YealinkIPPhoneMenu")
    title = ET.SubElement(root, "Title")
    title.text = title_text
    prompt = ET.SubElement(root, "Prompt")
    prompt.text = prompt_text

    for item_name, item_url in items:
        menu_item = ET.SubElement(root, "MenuItem")
        name_node = ET.SubElement(menu_item, "Name")
        name_node.text = item_name
        url_node = ET.SubElement(menu_item, "URL")
        url_node.text = item_url

    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def import_phonebook_xml(phonebook: Phonebook, xml_path: Path, replace_existing: bool = False) -> int:
    is_business = bool(phonebook.settings and phonebook.settings.category == "business")
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
        group = (item.findtext("Group") or "").strip() or None
        if not is_business:
            group = None

        db.session.add(
            ContactEntry(
                phonebook_id=phonebook.id,
                name=name,
                office=office,
                mobile=mobile,
                other=other,
                group=group,
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
                    group=group,
                )
            )
            inserted += 1

    db.session.commit()
    return inserted
