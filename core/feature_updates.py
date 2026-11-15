"""
What's New & Feature Updates Parser for Clarity Retail: Gadget Store System.
Reads and parses FEATURE_UPDATES.txt grouped by month, release tag, and category.
"""
import os
import re
from django.conf import settings


class UpdateItem:
    """Represents a single point-form feature update item with title and description."""
    def __init__(self, raw):
        self.raw = raw
        if ':' in raw and not raw.startswith('http'):
            self.title, _, self.desc = raw.partition(':')
            self.title = self.title.strip()
            self.desc = self.desc.strip()
        else:
            self.title = ''
            self.desc = raw

    def append_desc(self, text):
        cleaned = text.strip()
        if not cleaned:
            return
        if self.desc:
            self.desc += ' ' + cleaned
        else:
            self.desc = cleaned
        self.raw += ' ' + cleaned

    def __str__(self):
        return self.raw


def parse_feature_updates():
    """Reads and parses FEATURE_UPDATES.txt grouped by month and release version."""
    file_path = os.path.join(settings.BASE_DIR, 'FEATURE_UPDATES.txt')
    if not os.path.exists(file_path):
        return [], ""

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()
    except Exception:
        return [], ""

    months_data = []
    pattern = re.compile(r'\[([A-Z]+ \d{4})\](?:\s*-\s*([^\n\r]+))?', re.MULTILINE)
    matches = list(pattern.finditer(raw_text))

    for idx, match in enumerate(matches):
        month_name = match.group(1).title()
        version_tag = (match.group(2) or '').strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(raw_text)
        block = raw_text[start:end].strip()

        sections = []
        current_section = None
        last_item = None

        for line in block.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith('='):
                continue

            # Section headers: starting with '*', 'UPDATE:', or '###'
            if line_str.startswith('*'):
                sec_title = line_str.lstrip('*').strip()
                current_section = {'title': sec_title, 'items': []}
                sections.append(current_section)
                last_item = None
            elif line_str.upper().startswith('UPDATE:'):
                sec_title = line_str[7:].strip()
                current_section = {'title': sec_title, 'items': []}
                sections.append(current_section)
                last_item = None
            elif line_str.startswith('###'):
                sec_title = line_str.lstrip('#').strip()
                current_section = {'title': sec_title, 'items': []}
                sections.append(current_section)
                last_item = None
            elif line_str.startswith(('-', '•', '+')) or (
                line_str.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.'))
                and not re.match(r'^\d+\.\d+', line_str)
            ):
                if current_section is None:
                    current_section = {'title': 'General Enhancements & Fixes', 'items': []}
                    sections.append(current_section)

                if line_str.startswith(('-', '•', '+')):
                    item_text = line_str.lstrip('-•+').strip()
                else:
                    item_text = re.sub(r'^\d+\.\s*', '', line_str).strip()

                item = UpdateItem(item_text)
                current_section['items'].append(item)
                last_item = item
            elif current_section is not None:
                # If indented or continuing a bullet item, append to description
                if last_item is not None and (line.startswith(' ') or line.startswith('\t')):
                    last_item.append_desc(line_str)
                else:
                    item = UpdateItem(line_str)
                    current_section['items'].append(item)
                    last_item = item
            else:
                # Text before any section header: auto-create section
                current_section = {'title': 'General Enhancements & Fixes', 'items': []}
                sections.append(current_section)
                item = UpdateItem(line_str)
                current_section['items'].append(item)
                last_item = item

        months_data.append({
            'month': month_name,
            'version': version_tag,
            'is_latest': idx == 0,
            'sections': sections,
        })

    return months_data, raw_text
