#!/usr/bin/env python3
"""
Uses Claude AI to analyze newly added CMS_MESSAGE entries and provide
style/formatting suggestions based on message type rules.
"""

import sys
import os
import re
import json
import base64

try:
    import anthropic
except ImportError:
    print("⚠️ Anthropic library not installed. Run: pip install anthropic")
    print("Skipping message suggestions.")
    sys.exit(0)


# Message type classification patterns
DIALOG_TITLE_PATTERNS = ['_TITLE', '_HEADER', '_LABEL', '_NAME', '_CAPTION']
MAIN_INSTRUCTION_PATTERNS = ['_INSTRUCT', '_CONFIRM', 'MESSAGE', '_PROMPT', '_QUESTION']
CONTENT_TEXT_PATTERNS = ['ERROR', 'ERR_', 'INVALID', '_API_', '_WARN', '_FAIL']


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


def classify_message_type(key):
    """
    Classify a message by its KEY pattern.
    Returns: 'dialog_title', 'main_instruction', 'content_text', or 'unknown'
    """
    key_upper = key.upper()
    
    # Check for Dialog Title patterns
    for pattern in DIALOG_TITLE_PATTERNS:
        if pattern in key_upper:
            return 'dialog_title'
    
    # Check for Content Text patterns (check before main instruction)
    for pattern in CONTENT_TEXT_PATTERNS:
        if pattern in key_upper:
            return 'content_text'
    
    # Check for Main Instruction patterns
    for pattern in MAIN_INSTRUCTION_PATTERNS:
        if pattern in key_upper:
            return 'main_instruction'
    
    # Default to content_text for unknown patterns (safer to check)
    return 'content_text'


def build_suggestions_prompt(added_messages):
    """Build the prompt for Claude to analyze messages and suggest improvements."""
    
    # Filter out dialog titles (no suggestions needed)
    messages_to_review = []
    for msg in added_messages:
        key = msg.get('key', '')
        text = msg.get('text', '')
        msg_id = msg.get('id', '')
        msg_type = classify_message_type(key)
        
        if msg_type != 'dialog_title' and text:
            messages_to_review.append({
                'id': msg_id,
                'key': key,
                'text': text,
                'type': msg_type
            })
    
    if not messages_to_review:
        return None
    
    # Build the message list for the prompt
    message_list = []
    for msg in messages_to_review[:20]:  # Limit to 20 messages
        message_list.append(f"- ID: {msg['id']}, KEY: {msg['key']}, TYPE: {msg['type']}")
        message_list.append(f"  TEXT: \"{msg['text']}\"")
    
    messages_text = "\n".join(message_list)
    
    prompt = f"""You are a technical writer reviewing CMS (Content Management System) messages for a legal/financial software application. The attached image shows an example of how these messages appear in dialog boxes to end users. Use this visual context when reviewing messages.

Analyze the following newly added messages and identify any style guideline violations.

## Style Guidelines

### Main Instruction Text

Main Instruction Text is a brief message, warning or error from the user's perspective.

- The user should immediately understand the impact of their actions when reading this

- NO ending punctuation EXCEPT for "?" if it is a question

- Example: "Are you sure you want to continue?"

- Example: "Select a matter to proceed"

- Example: "Invalid search employee uno"

- Example: "Not Authorized"

### Content Text

Content Text expands on the message in the Main Instruction Text to provide additional context and instruction.

- May include elaboration on the message, warning, or error from the Main Instruction Text

- Offers appropriate solutions the end user can perform

- Uses short sentences with minimal commas.

- Use sentence capitalization

- MUST have ending punctuation (period, exclamation, or question mark)

- MUST refer to the user as "you" instead of "the user"

- Content Text does NOT use "please" EXCEPT for when the user is being asked to contact the system administrator

- Content Text uses short, complete sentences when possible

- Example: "The cash receipt status is invalid. The cash receipt cannot be inserted."

- Example: "You must select a valid matter before proceeding."

- Example: "The refund amount cannot exceed the advance balance."

- Example: "You do not have the required permissions to run Expert Accounts Payable. Please contact your system administrator to gain access to this application."

## Messages to Review

{messages_text}

## Instructions

Review each message against its type's guidelines. Provide 0 to 3 suggestions for improvements. Not all messages require improvement. Focus on the most important issues:

1. Content Text using "the user" instead of "you"

2. Content Text using "please" without a request to contact the administrator

3. Main Instruction Text with incorrect ending punctuation

4. Content Text missing ending punctuation

If all messages follow the guidelines correctly, respond with exactly:

✅ No issues found. All new messages follow the style guidelines.

If there are issues, respond with a numbered list (max 3 items) in this format:

1. **ID [id] ([KEY])**: [Brief description of the issue]. Suggested fix: "[corrected text]"

Keep suggestions concise and actionable. Do not use any other formatting."""

    return prompt


def generate_suggestions(diff_data):
    """Call Claude API to generate message suggestions."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        return "⚠️ **Message suggestions unavailable**: `ANTHROPIC_API_KEY` secret not configured.\n\nTo enable AI-powered suggestions, add your Anthropic API key as a repository secret."
    
    added = diff_data.get('added', [])
    
    if not added:
        return "✅ No new messages to review."
    
    prompt = build_suggestions_prompt(added)
    
    if not prompt:
        return "✅ No messages requiring review (only Dialog Titles were added)."
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        # Load the example dialog image
        image_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'image.png')
        image_content = []
        
        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                image_data = base64.standard_b64encode(f.read()).decode('utf-8')
            image_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_data
                    }
                }
            ]
        
        # Build multimodal message with image + text
        message_content = image_content + [{"type": "text", "text": prompt}]
        
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": message_content}
            ]
        )
        
        if message.content and len(message.content) > 0:
            return message.content[0].text
        else:
            return "⚠️ AI generated an empty response."
            
    except anthropic.APIConnectionError:
        return "⚠️ **Message suggestions unavailable**: Could not connect to Anthropic API."
    except anthropic.RateLimitError:
        return "⚠️ **Message suggestions unavailable**: API rate limit exceeded. Please try again later."
    except anthropic.APIStatusError as e:
        return f"⚠️ **Message suggestions unavailable**: API error ({e.status_code})"
    except Exception as e:
        return f"⚠️ **Message suggestions unavailable**: {str(e)}"


def generate_fallback_suggestions(diff_data):
    """Generate basic suggestions without AI when API is unavailable."""
    added = diff_data.get('added', [])
    
    if not added:
        return "✅ No new messages to review."
    
    issues = []
    
    for msg in added[:20]:
        key = msg.get('key', '')
        text = msg.get('text', '')
        msg_id = msg.get('id', '')
        msg_type = classify_message_type(key)
        
        if msg_type == 'dialog_title':
            continue
        
        # Check for common issues
        if msg_type == 'content_text':
            # Check for "please" without "administrator" or "admin"
            if 'please' in text.lower() and 'admin' not in text.lower():
                issues.append(f"**ID {msg_id} ({key})**: Contains \"please\" without administrator contact - Content Text should not use \"please\" except when asking to contact admin.")
            # Check for "the user" instead of "you"
            if 'the user' in text.lower():
                issues.append(f"**ID {msg_id} ({key})**: Uses \"the user\" - Content Text should use \"you\" instead.")
        
        if len(issues) >= 3:
            break
    
    if not issues:
        return "✅ No obvious issues found. (Full AI analysis unavailable)"
    
    return "\n".join([f"{i+1}. {issue}" for i, issue in enumerate(issues)])


def main():
    if len(sys.argv) != 2:
        print("Usage: message_suggestions.py <diff_output.md>", file=sys.stderr)
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
        print("No diff data found in the input file.")
        sys.exit(0)
    
    # Check if there are any added messages
    stats = diff_data.get('stats', {})
    if stats.get('added', 0) == 0:
        print("✅ No new messages added in this PR.")
        sys.exit(0)
    
    # Generate suggestions
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if api_key:
        suggestions = generate_suggestions(diff_data)
    else:
        suggestions = generate_fallback_suggestions(diff_data)
    
    print(suggestions)


if __name__ == "__main__":
    main()

