from typing import Any

from langchain_openai import ChatOpenAI

from app.activity.create_from_onboarding import Activity
from app.activity.models import ActivityLevel


async def create_activity_from_concepts(
    *,
    level: ActivityLevel,
    concepts: list[str],
    guided_description: str | None = None,
    user_context: dict[str, Any] | None = None,  # Optionally pass user info for context
) -> Activity:
    """
    Generate a single Activity based on level, concepts, and optional description/context.
    """
    llm = ChatOpenAI(model="o3-2025-04-16")

    # Compose the system prompt
    system_prompt = f"""\
You are a financial education expert. Your task is to design a single, self-contained learning activity for a user.

Guidelines:
- The activity should be at the '{level}' level.
- It must focus on the following financial concepts: {", ".join(concepts)}.
- If a guided description is provided, use it to shape the activity's context, background, or scenario.
- If user context is provided, use it to personalize the activity (e.g., profession, age, hobbies, goals).
- The activity should include:
    - A clear, engaging title.
    - A concise description introducing the topic and its importance.
    - An overall objective.
    - A background section that defines and explains each concept, shows how they relate, and why they matter.
    - 3-6 sequential, actionable steps (with index, title, content, and step objective).
    - A glossary of key terms (if jargon is used).
    - At least one alternative (non-technical) method if technical tools are suggested.
    - The correct 'level' field.
- Make the activity interactive and encourage reflection.
- Use clear, accessible language.
- Output a single JSON object matching the provided Activity schema.

**Important**

All the generated content should be markdown-formatted.

{f"Guided description: {guided_description}" if guided_description else ""}
{f"User context: {user_context}" if user_context else ""}
"""

    # Prepare the user message (concepts, level, etc.)
    user_message = {
        "level": level,
        "concepts": concepts,
        "guided_description": guided_description,
        "user_context": user_context,
    }

    # Call the LLM with structured output
    activity = await llm.with_structured_output(schema=Activity, strict=True).ainvoke(
        [
            ("system", system_prompt),
            ("user", str(user_message)),
        ]
    )

    if not isinstance(activity, Activity):
        raise ValueError("Invalid activity structure")

    return activity
