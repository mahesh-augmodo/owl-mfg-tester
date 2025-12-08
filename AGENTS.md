# Agent Instructions for Code Generation and Documentation

This document outlines best practices for Language Model Agents contributing code to this repository. Adhering to these guidelines ensures consistency, maintainability, and high quality.

## Code Generation

When generating new code or modifying existing patterns:

1.  **Project Conventions**: Strictly adhere to existing conventions. Analyze surrounding code, tests, and configuration files (e.g., `package.json`, `Pipfile`, `Makefile`) to understand established patterns.
2.  **Existing Libraries/Frameworks**: Only use libraries or frameworks already established and in use within the project. Verify their presence and usage (e.g., in `Pipfile`, `go.mod`, imports) before implementing.
3.  **Style & Structure**: Mimic the prevailing code style (formatting, naming conventions), architectural structure, and chosen frameworks.
4.  **Idiomatic Changes**: Ensure all modifications integrate naturally and idiomatically with the local context (imports, functions/classes).
5.  **Test-Driven Approach**: For new features or bug fixes, always include relevant tests that verify the changes.

## Function Augmentation

When modifying or extending existing user functions:

1.  **Understand Context**: Fully grasp the function's original purpose, its inputs, outputs, and any side effects.
2.  **Preserve Core Logic**: Ensure the augmentation integrates seamlessly without disrupting the primary functionality unless explicitly instructed.
3.  **Maintain Signatures**: Avoid unnecessary changes to function signatures unless required for the requested augmentation.

## Documentation (Docstrings)

Maintain comprehensive and up-to-date docstrings for all functions, classes, and complex modules:

1.  **Purpose**: Clearly state *what* the code does.
2.  **Arguments**: Document each argument, its type, and its purpose.
3.  **Returns**: Describe the return value and its type.
4.  **Exceptions**: Note any exceptions that might be raised.
5.  **Brevity**: Be concise but complete. Avoid redundant information.

## General Guidance

*   **Proactivity**: Fulfill requests thoroughly, including necessary tests and error handling.
*   **Safety**: Prioritize security best practices. Never expose sensitive information.
*   **Verification**: Always run project-specific build, linting, and type-checking commands after making changes.
