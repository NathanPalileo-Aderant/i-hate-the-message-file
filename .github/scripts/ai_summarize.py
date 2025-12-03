#!/usr/bin/env python3
"""
Uses Claude AI to generate a natural language summary of CMS_MESSAGE file changes.
Reads the diff output from message_diff.py and extracts the embedded JSON data.
"""

import sys
import os
import re
import json

try:
    import anthropic
except ImportError:
    print("⚠️ Anthropic library not installed. Run: pip install anthropic")
    print("Skipping AI summary generation.")
    sys.exit(0)


def extract_diff_data(markdown_content):
    """Extract the JSON diff data embedded in the markdown output."""
    pattern = r'<!-- RAW_DIFF_DATA\s*(.*?)\s*RAW_DIFF_DATA -->'
    match = re.search(pattern, markdown_content, re.DOTALL)
    
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse embedded JSON: {e}", file=sys.stderr)
            return None
    return None


def build_prompt(diff_data):
    """Build the prompt for Claude to summarize the changes."""
    stats = diff_data.get('stats', {})
    added = diff_data.get('added', [])
    removed = diff_data.get('removed', [])
    modified = diff_data.get('modified', [])
    
    # Build context about the changes
    context_parts = []
    
    context_parts.append(f"Total messages in base: {stats.get('base_total', 'unknown')}")
    context_parts.append(f"Total messages in new version: {stats.get('head_total', 'unknown')}")
    context_parts.append(f"Added: {stats.get('added', 0)}")
    context_parts.append(f"Removed: {stats.get('removed', 0)}")
    context_parts.append(f"Modified: {stats.get('modified', 0)}")
    
    # Sample of added messages
    if added:
        context_parts.append("\n--- ADDED MESSAGES (sample) ---")
        for item in added[:20]:
            context_parts.append(f"- [{item.get('key', 'N/A')}]: {item.get('text', '')[:100]}")
    
    # Sample of removed messages
    if removed:
        context_parts.append("\n--- REMOVED MESSAGES (sample) ---")
        for item in removed[:20]:
            context_parts.append(f"- [{item.get('key', 'N/A')}]: {item.get('text', '')[:100]}")
    
    # Sample of modified messages
    if modified:
        context_parts.append("\n--- MODIFIED MESSAGES (sample) ---")
        for item in modified[:20]:
            context_parts.append(f"- [{item.get('key', 'N/A')}]:")
            context_parts.append(f"  Old: {item.get('old_text', '')[:80]}")
            context_parts.append(f"  New: {item.get('new_text', '')[:80]}")
    
    context = "\n".join(context_parts)
    
    prompt = f"""You are analyzing changes to a CMS (Content Management System) message file used for UI localization and system messages in a legal/financial software application.

Here are the changes detected between the base branch and the PR branch:

{context}

Please provide a concise summary (2-3 paragraphs) that covers:

1. **Overview**: What types of changes were made? Are these primarily new features, bug fixes, text corrections, or removals?

2. **Patterns**: Do you notice any patterns in the message keys or text? Are the changes focused on a specific feature area (e.g., billing, payments, disbursements, user interface)?

3. **Impact**: What areas of the application might be affected? Are there any potentially breaking changes (removed messages that might still be referenced)?

Keep the summary professional and focused on what a code reviewer would need to know. Use plain language, not technical jargon. Do not use markdown formatting in your response."""

    return prompt


def generate_summary(diff_data):
    """Call Claude API to generate a summary of the changes."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        return "⚠️ **AI Summary unavailable**: `ANTHROPIC_API_KEY` secret not configured.\n\nTo enable AI summaries, add your Anthropic API key as a repository secret."
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = build_prompt(diff_data)
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the text response
        if message.content and len(message.content) > 0:
            return message.content[0].text
        else:
            return "⚠️ AI generated an empty response."
            
    except anthropic.APIConnectionError:
        return "⚠️ **AI Summary unavailable**: Could not connect to Anthropic API."
    except anthropic.RateLimitError:
        return "⚠️ **AI Summary unavailable**: API rate limit exceeded. Please try again later."
    except anthropic.APIStatusError as e:
        return f"⚠️ **AI Summary unavailable**: API error ({e.status_code})"
    except Exception as e:
        return f"⚠️ **AI Summary unavailable**: {str(e)}"


def generate_fallback_summary(diff_data):
    """Generate a basic summary without AI when API is unavailable."""
    stats = diff_data.get('stats', {})
    added = diff_data.get('added', [])
    removed = diff_data.get('removed', [])
    modified = diff_data.get('modified', [])
    
    lines = []
    
    # Basic stats
    total_changes = stats.get('added', 0) + stats.get('removed', 0) + stats.get('modified', 0)
    
    if total_changes == 0:
        return "No significant changes detected in this PR."
    
    lines.append(f"This PR contains **{total_changes}** message changes:")
    
    if stats.get('added', 0) > 0:
        lines.append(f"- {stats['added']} new message(s) added")
    if stats.get('removed', 0) > 0:
        lines.append(f"- {stats['removed']} message(s) removed")
    if stats.get('modified', 0) > 0:
        lines.append(f"- {stats['modified']} message(s) modified")
    
    # Try to identify patterns in message keys
    all_keys = []
    all_keys.extend([item.get('key', '') for item in added])
    all_keys.extend([item.get('key', '') for item in removed])
    all_keys.extend([item.get('key', '') for item in modified])
    
    # Find common prefixes
    prefixes = {}
    for key in all_keys:
        if key:
            prefix = key.split('_')[0] if '_' in key else key[:10]
            prefixes[prefix] = prefixes.get(prefix, 0) + 1
    
    if prefixes:
        top_prefixes = sorted(prefixes.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_prefixes:
            areas = ", ".join([f"`{p[0]}`" for p in top_prefixes if p[1] > 1])
            if areas:
                lines.append(f"\nAffected areas appear to include: {areas}")
    
    return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        print("Usage: ai_summarize.py <diff_output.md>", file=sys.stderr)
        sys.exit(1)
    
    diff_file = sys.argv[1]
    
    try:
        with open(diff_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except FileNotFoundError:
        print(f"Error: File not found: {diff_file}", file=sys.stderr)
        sys.exit(1)
    
    # Extract the embedded diff data
    diff_data = extract_diff_data(markdown_content)
    
    if not diff_data:
        print("No diff data found in the input file. The file may not have any changes.")
        sys.exit(0)
    
    # Check if there are any actual changes
    stats = diff_data.get('stats', {})
    if stats.get('added', 0) == 0 and stats.get('removed', 0) == 0 and stats.get('modified', 0) == 0:
        print("No changes detected between the base and PR branches.")
        sys.exit(0)
    
    # Try to generate AI summary
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if api_key:
        summary = generate_summary(diff_data)
    else:
        # Fallback to basic summary
        summary = generate_fallback_summary(diff_data)
    
    print(summary)


if __name__ == "__main__":
    main()

