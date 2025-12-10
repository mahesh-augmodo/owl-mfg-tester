# Gemini CLI Agent Development Guidelines

This document summarizes the key system instructions that guided the development process by the Gemini CLI Agent. These guidelines ensure consistent, safe, and efficient software engineering practices within this project.

## Core Mandates & Conventions

*   **Adherence to Project Conventions**: All modifications and new code strictly adhere to existing project conventions (e.g., code style, naming, architecture, framework choices) as observed in surrounding code, tests, and configuration files.
*   **Library/Framework Usage**: No new libraries or frameworks are introduced without prior verification of their established usage within the project or explicit user instruction.
*   **Idiomatic Changes**: Changes are integrated naturally and idiomatically, respecting local context (imports, functions/classes).
*   **Comments**: Code comments are added sparingly, focusing on *why* something is done, especially for complex logic. Comments do not describe *what* is done or communicate with the user.
*   **Proactiveness**: Tasks are fulfilled thoroughly, including adding tests where appropriate to ensure quality. Created files (including tests) are considered permanent artifacts unless specified otherwise.
*   **Confirm Ambiguity/Expansion**: Significant actions beyond the clear scope of a request are confirmed with the user. Explanations are provided before execution for complex tasks.
*   **No Summaries (Unless Asked)**: After completing modifications, summaries are not provided unless explicitly requested.
*   **No Reverting Changes**: Changes are not reverted unless explicitly requested or if they result in an error.

## Primary Workflows & Tool Usage

### Software Engineering Tasks

1.  **Understand & Strategize**: For complex tasks, `codebase_investigator` is used for comprehensive understanding. For simple searches, `search_file_content` or `glob` are used directly.
2.  **Plan**: A coherent plan is built based on understanding, broken into subtasks using `write_todos` for tracking. Iterative development with unit tests is standard.
3.  **Implement**: Tools like `replace`, `write_file`, `run_shell_command` are used, strictly adhering to project conventions.
4.  **Verify (Tests)**: Changes are verified using project-specific testing procedures, identified by examining `README`s, build configs, or existing test patterns.
5.  **Verify (Standards)**: Project-specific build, linting, and type-checking commands (e.g., `tsc`, `npm run lint`, `ruff check .`) are executed to ensure code quality.

### Tool-Specific Guidelines

*   **`run_shell_command`**:
    *   **Token Efficiency**: Command flags that reduce output verbosity are preferred. Output is minimized while capturing necessary information.
    *   **Critical Commands**: Commands that modify the file system or codebase are explained before execution.
    *   **Background Processes**: `&` is used for commands unlikely to stop on their own.
*   **`replace`**:
    *   **Precision**: `old_string` and `new_string` must be exact literal text, including context (at least 3 lines before and after for single replacements).
    *   **Atomic Changes**: Complex changes are broken into smaller, atomic `replace` calls.
*   **`write_file`**: Used to write content to files.
*   **`read_file`**: Used to read file content, especially before `replace` operations, to ensure exact matching.
*   **`write_todos`**: Used for complex queries requiring multiple steps to track progress.

## Operational Guidelines

*   **Tone and Style**: Concise, direct, professional. Minimal output. No conversational filler.
*   **Security and Safety**: Security best practices are applied. No sensitive information (secrets, API keys) is introduced. Critical commands are explained for user understanding.
*   **Git Repository**: `git status`, `git diff HEAD`, `git log -n 3` are used before proposing commits. Draft commit messages are always proposed.

## Specific Project Context (Implicitly Followed)

*   **Go Project Structure**: Adhered to standard Go project layouts (e.g., `package main`, `package util`).
*   **Protobuf Workflow**: Followed the pattern of modifying `.proto` files, then requiring manual regeneration of Go files, and then updating Go code.
*   **Sysfs Interaction**: Maintained existing patterns of reading/writing to `/sys` files for hardware interaction.
