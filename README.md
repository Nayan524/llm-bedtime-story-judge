# LLM Bedtime Story Judge

An agentic Python command-line application that creates bedtime stories for
children ages 5–10, evaluates them with an LLM Judge, and improves weak drafts
before showing the best version to the user.

The project was built for the Hippocratic AI coding assignment. It keeps the
assignment-provided `gpt-3.5-turbo` model and differentiates the application’s
LLM roles through focused system prompts and task-specific prompt templates.

## Features

- Classifies each request into a primary story category.
- Applies a category-specific storytelling strategy.
- Generates warm, age-appropriate bedtime stories.
- Evaluates stories against seven quality and safety criteria.
- Checks every explicit user requirement with evidence.
- Automatically revises drafts that do not meet the approval rules.
- Retains evaluated drafts and returns the strongest version.
- Accepts user-requested changes and evaluates the updated story again.
- Validates structured LLM responses and retries one malformed Judge response.
- Includes automated tests that do not require live OpenAI API calls.

## Architecture

![Bedtime Story Judge architecture](docs/architecture-v2.png)

The workflow is intentionally bounded. A story can receive at most two automatic
revisions, and the user can provide at most two feedback rounds. These limits keep
the CLI predictable and prevent uncontrolled LLM loops.

### Major components

| Component | Responsibility |
| --- | --- |
| `src/main.py` | Runs the command-line experience and coordinates user interaction. |
| `src/prompts.py` | Stores the system prompts, task prompt builders, and fixed category strategies. |
| `src/utils.py` | Implements classification, generation, evaluation, revision, selection, parsing, and display helpers. |
| `src/call_llm.py` | Provides the single OpenAI API boundary used by every LLM role. |
| `src/config.py` | Loads environment configuration and centralizes model, temperature, token, retry, and revision settings. |
| `src/ResponseModel/` | Contains the structured models used for classification, Judge output, evaluated drafts, and final results. |
| `tests/` | Tests prompt construction, parsing, orchestration, retry behavior, classification, feedback, and model calls. |

### LLM roles

The application uses the same assignment-required model for three distinct roles:

1. **Request Classifier** — selects one primary category: adventure, comfort,
   educational, fantasy, humorous, values, or everyday.
2. **Storyteller** — generates the initial story and performs both Judge-directed
   and user-directed revisions. Revision is a separate task prompt, not a separate
   LLM identity.
3. **Judge** — evaluates the story independently, returns structured JSON, and
   supplies evidence and actionable revision instructions.

The Python coordinator is deterministic application logic rather than another LLM
agent. It validates outputs, applies approval rules, enforces iteration limits, and
selects the best evaluated draft.

## Requirements

- Python 3.9 or newer
- An OpenAI API key with available API credits

## Setup

Clone the repository and move into it:

```bash
git clone <repository-url>
cd llm-bedtime-story-judge
```

Create and activate a virtual environment.

Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Create the local environment file from the example:

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS or Linux:

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder with your key:

```dotenv
OPENAI_API_KEY=your_actual_openai_api_key
```

Never commit `.env` or a real API key.

## Run the application

Run the application from the repository root:

```bash
python -m src.main
```

On Windows, `py -m src.main` can be used if `python` is not registered as a
command.

Direct script execution is also supported:

```powershell
python src\main.py
```

Alternatively, change into `src` before running the script:

```powershell
cd src
python main.py
```

Windows PowerShell example:

```powershell
cd D:\llm-story-judge\llm-bedtime-story-judge
python -m src.main
```

Example request:

```text
A little rabbit learns not to be afraid of thunderstorms.
```

The application will display the selected category, generate and judge the story,
perform any required bounded revisions, show the selected version and Judge report,
and then ask whether the user wants to keep the story or request a change.

## Run the tests

```bash
pytest
```

The test suite mocks the model boundary, so running the tests does not consume API
credits or require network access.
