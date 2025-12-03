# CMS Message File Diff Checker

Automatically compares large CMS_MESSAGE files in Pull Requests and posts a detailed diff report with AI-powered style suggestions as a PR comment.

## Problem

The `dbo.CMS_MESSAGE.EN06 (11).txt` file is too large (~2GB) for GitHub to display diffs in the PR interface. This makes it tedious to review changes since you have to download the file manually.

## Solution

A GitHub Action that:
1. **Detects changes** to the message file in PRs
2. **Compares versions** between base branch and PR branch
3. **Categorizes changes** into Added, Removed, and Modified messages
4. **Generates AI-powered style suggestions** using Claude to check new messages against formatting guidelines
5. **Posts a PR comment** with style suggestions and detailed diff tables

## Setup

### 1. Add the Anthropic API Key Secret

The AI style suggestions feature requires an Anthropic API key:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `ANTHROPIC_API_KEY`
5. Value: Your Anthropic API key (get one at https://console.anthropic.com/)
6. Click **Add secret**

> **Note:** The workflow will still function without the API key, but will only perform basic checks instead of full AI-powered analysis.

### 2. File Structure

Ensure these files are in your repository:

```
.github/
  workflows/
    message-file-diff.yml     # GitHub Actions workflow
  scripts/
    message_diff.py           # Diff parser script
    message_suggestions.py    # AI message style checker script
```

### 3. Trigger the Workflow

The workflow automatically runs when a PR modifies:
- `i-hate-the-message-file/dbo.CMS_MESSAGE.EN06 (11).txt`

## PR Comment Output

When changes are detected, the workflow posts a comment like this:

### 💡 Message Style Suggestions
> ✅ No issues found. All new messages follow the style guidelines.

Or if issues are detected:
> 1. **ID 555393 (DELETEPOSTEDERROR)**: Uses "Please refresh" - Content Text should not use "please". Suggested fix: "Refresh to view the current status."

### 📋 Detailed Changes

| Metric | Count |
|--------|-------|
| Base file messages | 5,945 |
| New file messages | 5,960 |
| ✅ Added | **15** |
| ❌ Removed | **0** |
| ✏️ Modified | **2** |

<details>
<summary>✅ Added Messages (15)</summary>

| ID | Key | Text | User |
|---|---|---|---|
| 539999 | `NEW_FEATURE_MSG` | This is a new message | john.doe |
| ... | ... | ... | ... |

</details>

## Customization

### Change the tracked file

Edit `.github/workflows/message-file-diff.yml`:

```yaml
on:
  pull_request:
    paths:
      - 'path/to/your/file.txt'  # Change this path
```

### Adjust output limits

Edit `.github/scripts/message_diff.py`:

```python
MAX_ITEMS = 50  # Change to show more/fewer items per category
```

### Change the AI model

Edit `.github/scripts/message_suggestions.py`:

```python
model="claude-haiku-4-5"  # Change to a different Claude model
```

## Troubleshooting

### "Message suggestions unavailable: ANTHROPIC_API_KEY secret not configured"

Add the `ANTHROPIC_API_KEY` secret as described in the Setup section.

### Workflow not triggering

- Ensure the file path in the workflow matches your actual file location
- Check that the workflow file is in `.github/workflows/`
- Verify the PR is targeting a branch that has the workflow

### Large diffs timing out

The scripts are optimized for large files, but if you have extremely large diffs:
- Reduce `MAX_ITEMS` in `message_diff.py`
- The message suggestions script only processes the first 20 added messages

## License

MIT
