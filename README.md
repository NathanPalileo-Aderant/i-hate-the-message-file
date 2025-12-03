# CMS Message File Diff Checker

Automatically compares large CMS_MESSAGE files in Pull Requests and posts a detailed diff report with AI-powered summaries as a PR comment.

## Problem

The `dbo.CMS_MESSAGE.EN06 (11).txt` file is too large (~2GB) for GitHub to display diffs in the PR interface. This makes it tedious to review changes since you have to download the file manually.

## Solution

A GitHub Action that:
1. **Detects changes** to the message file in PRs
2. **Compares versions** between base branch and PR branch
3. **Categorizes changes** into Added, Removed, and Modified messages
4. **Generates an AI summary** using Claude to explain what changed in plain English
5. **Posts a PR comment** with both the summary and detailed diff tables

## Setup

### 1. Add the Anthropic API Key Secret

The AI summary feature requires an Anthropic API key:

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `ANTHROPIC_API_KEY`
5. Value: Your Anthropic API key (get one at https://console.anthropic.com/)
6. Click **Add secret**

> **Note:** The workflow will still function without the API key, but will generate a basic summary instead of an AI-powered one.

### 2. File Structure

Ensure these files are in your repository:

```
.github/
  workflows/
    message-file-diff.yml     # GitHub Actions workflow
  scripts/
    message_diff.py           # Diff parser script
    ai_summarize.py           # AI summarizer script
```

### 3. Trigger the Workflow

The workflow automatically runs when a PR modifies:
- `i-hate-the-message-file/dbo.CMS_MESSAGE.EN06 (11).txt`

## PR Comment Output

When changes are detected, the workflow posts a comment like this:

### 🤖 AI Summary
> This PR adds 15 new messages related to the Disbursements feature, including tooltips and error messages. Two existing messages were modified to fix typos. The changes appear focused on the Expert Disbursements module...

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

Edit `.github/scripts/ai_summarize.py`:

```python
model="claude-3-5-sonnet-20241022"  # Change to a different Claude model
```

## Troubleshooting

### "AI Summary unavailable: ANTHROPIC_API_KEY secret not configured"

Add the `ANTHROPIC_API_KEY` secret as described in the Setup section.

### Workflow not triggering

- Ensure the file path in the workflow matches your actual file location
- Check that the workflow file is in `.github/workflows/`
- Verify the PR is targeting a branch that has the workflow

### Large diffs timing out

The scripts are optimized for large files, but if you have extremely large diffs:
- Reduce `MAX_ITEMS` in `message_diff.py`
- The AI summarizer only processes the first 100 items per category

## License

MIT
