#!/usr/bin/env python3
"""
Compares two CMS_MESSAGE files and outputs a markdown diff report.
Handles large files efficiently by using dictionaries keyed on message ID.

File format: ID,<tab>KEY,<tab>CODE,<tab>LANG,<tab>FLAG,<tab>TEXT,<tab>...~|
"""

import sys
import json
from collections import OrderedDict


def parse_message_file(filepath):
    """
    Parse the CMS_MESSAGE file into a dictionary keyed by message ID.
    
    Returns: {
        message_id: {
            'key': str,
            'code': str,
            'text': str,
            'short_text': str,
            'user': str,
            'timestamp': str,
            'full_line': str,
            'line_num': int
        }
    }
    """
    messages = OrderedDict()
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                # Split by comma+tab delimiter (,\t)
                parts = line.replace(',\t', '\t').split('\t')
                
                if len(parts) >= 6:
                    # Extract fields, removing trailing commas
                    msg_id = parts[0].strip().rstrip(',')
                    msg_key = parts[1].strip().rstrip(',') if len(parts) > 1 else ''
                    msg_code = parts[2].strip().rstrip(',') if len(parts) > 2 else ''
                    msg_lang = parts[3].strip().rstrip(',') if len(parts) > 3 else ''
                    msg_text = parts[5].strip().rstrip(',') if len(parts) > 5 else ''
                    msg_short = parts[6].strip().rstrip(',') if len(parts) > 6 else ''
                    
                    # Extract user and timestamp (usually near the end)
                    msg_user = ''
                    msg_timestamp = ''
                    if len(parts) >= 15:
                        msg_user = parts[14].strip().rstrip(',') if parts[14].strip() else ''
                    if len(parts) >= 18:
                        # Timestamp is usually the last field before ~|
                        ts_field = parts[-1].replace('~|', '').strip().rstrip(',')
                        if ts_field and '-' in ts_field:
                            msg_timestamp = ts_field
                    
                    messages[msg_id] = {
                        'key': msg_key,
                        'code': msg_code,
                        'lang': msg_lang,
                        'text': msg_text,
                        'short_text': msg_short,
                        'user': msg_user,
                        'timestamp': msg_timestamp,
                        'full_line': line,
                        'line_num': line_num
                    }
    except FileNotFoundError:
        return OrderedDict()
    except Exception as e:
        print(f"Error parsing {filepath}: {e}", file=sys.stderr)
        return OrderedDict()
    
    return messages


def compare_files(base_file, head_file):
    """Compare two message files and return categorized changes."""
    base_msgs = parse_message_file(base_file)
    head_msgs = parse_message_file(head_file)
    
    base_ids = set(base_msgs.keys())
    head_ids = set(head_msgs.keys())
    
    added_ids = head_ids - base_ids
    removed_ids = base_ids - head_ids
    common_ids = base_ids & head_ids
    
    # Find modified entries (same ID but different content)
    modified = []
    for msg_id in common_ids:
        base_line = base_msgs[msg_id]['full_line']
        head_line = head_msgs[msg_id]['full_line']
        
        if base_line != head_line:
            modified.append({
                'id': msg_id,
                'key': head_msgs[msg_id]['key'],
                'old_text': base_msgs[msg_id]['text'],
                'new_text': head_msgs[msg_id]['text'],
                'old_user': base_msgs[msg_id]['user'],
                'new_user': head_msgs[msg_id]['user'],
                'old_timestamp': base_msgs[msg_id]['timestamp'],
                'new_timestamp': head_msgs[msg_id]['timestamp'],
            })
    
    # Build added and removed lists
    added = []
    for mid in sorted(added_ids, key=lambda x: int(x) if x.isdigit() else 0):
        added.append({
            'id': mid,
            'key': head_msgs[mid]['key'],
            'text': head_msgs[mid]['text'],
            'user': head_msgs[mid]['user'],
            'timestamp': head_msgs[mid]['timestamp'],
        })
    
    removed = []
    for mid in sorted(removed_ids, key=lambda x: int(x) if x.isdigit() else 0):
        removed.append({
            'id': mid,
            'key': base_msgs[mid]['key'],
            'text': base_msgs[mid]['text'],
            'user': base_msgs[mid]['user'],
            'timestamp': base_msgs[mid]['timestamp'],
        })
    
    stats = {
        'base_total': len(base_msgs),
        'head_total': len(head_msgs),
        'added': len(added),
        'removed': len(removed),
        'modified': len(modified),
    }
    
    return added, removed, modified, stats


def truncate(text, max_len=None):
    """Truncate text for display, preserving readability."""
    if not text:
        return ''
    text = str(text).strip()
    if max_len and len(text) > max_len:
        return text[:max_len] + '...'
    return text


def escape_markdown(text):
    """Escape special markdown characters in text."""
    if not text:
        return ''
    # Escape pipe characters which break markdown tables
    return str(text).replace('|', '\\|').replace('\n', ' ')


def generate_markdown_report(added, removed, modified, stats):
    """Generate a markdown report of the changes."""
    lines = []
    
    # Summary statistics
    lines.append("### 📈 Summary Statistics")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Base file messages | {stats['base_total']:,} |")
    lines.append(f"| New file messages | {stats['head_total']:,} |")
    lines.append(f"| ✅ Added | **{stats['added']}** |")
    lines.append(f"| ❌ Removed | **{stats['removed']}** |")
    lines.append(f"| ✏️ Modified | **{stats['modified']}** |")
    lines.append("")
    
    # Limit output to prevent massive PR comments
    MAX_ITEMS = 50
    
    # Added messages
    if added:
        lines.append("<details>")
        lines.append(f"<summary>✅ Added Messages ({len(added)})</summary>")
        lines.append("")
        lines.append("| ID | Key | Text | User |")
        lines.append("|---|---|---|---|")
        for item in added[:MAX_ITEMS]:
            escaped_text = escape_markdown(truncate(item['text']))
            escaped_key = escape_markdown(truncate(item['key']))
            lines.append(f"| {item['id']} | `{escaped_key}` | {escaped_text} | {item['user']} |")
        if len(added) > MAX_ITEMS:
            lines.append(f"| ... | *{len(added) - MAX_ITEMS} more items* | ... | ... |")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    
    # Removed messages
    if removed:
        lines.append("<details>")
        lines.append(f"<summary>❌ Removed Messages ({len(removed)})</summary>")
        lines.append("")
        lines.append("| ID | Key | Text | User |")
        lines.append("|---|---|---|---|")
        for item in removed[:MAX_ITEMS]:
            escaped_text = escape_markdown(truncate(item['text']))
            escaped_key = escape_markdown(truncate(item['key'], 35))
            lines.append(f"| {item['id']} | `{escaped_key}` | {escaped_text} | {item['user']} |")
        if len(removed) > MAX_ITEMS:
            lines.append(f"| ... | *{len(removed) - MAX_ITEMS} more items* | ... | ... |")
        lines.append("")
        lines.append("</details>")
        lines.append("")
    
    # Modified messages
    if modified:
        lines.append("<details>")
        lines.append(f"<summary>✏️ Modified Messages ({len(modified)})</summary>")
        lines.append("")
        for item in modified[:MAX_ITEMS]:
            escaped_key = escape_markdown(truncate(item['key'], 50))
            lines.append(f"**ID: {item['id']}** — `{escaped_key}`")
            
            old_text = escape_markdown(truncate(item['old_text']))
            new_text = escape_markdown(truncate(item['new_text']))
            
            if old_text != new_text:
                lines.append(f"- 🔴 **Old:** {old_text}")
                lines.append(f"- 🟢 **New:** {new_text}")
            else:
                lines.append(f"- Text unchanged, metadata modified")
                if item['old_user'] != item['new_user']:
                    lines.append(f"- User: `{item['old_user']}` → `{item['new_user']}`")
            lines.append("")
        
        if len(modified) > MAX_ITEMS:
            lines.append(f"*...and {len(modified) - MAX_ITEMS} more modified items*")
            lines.append("")
        lines.append("</details>")
        lines.append("")
    
    # No changes case
    if not added and not removed and not modified:
        lines.append("✨ **No meaningful changes detected in message content.**")
        lines.append("")
    
    # Export raw data as JSON for AI summarizer
    raw_data = {
        'stats': stats,
        'added': added[:100],  # Limit for AI context
        'removed': removed[:100],
        'modified': modified[:100],
    }
    lines.append("")
    lines.append("<!-- RAW_DIFF_DATA")
    lines.append(json.dumps(raw_data, indent=2))
    lines.append("RAW_DIFF_DATA -->")
    
    return "\n".join(lines)


def main():
    if len(sys.argv) != 3:
        print("Usage: message_diff.py <base_file> <head_file>", file=sys.stderr)
        print("  base_file: The original file (from base branch)")
        print("  head_file: The new file (from PR branch)")
        sys.exit(1)
    
    base_file = sys.argv[1]
    head_file = sys.argv[2]
    
    added, removed, modified, stats = compare_files(base_file, head_file)
    report = generate_markdown_report(added, removed, modified, stats)
    print(report)


if __name__ == "__main__":
    main()

