from typing import Literal

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from pydantic_ai import format_as_xml

from app.activity.models import ActivityLevel
from app.onboarding.agent import PersonalContext


class ActivityBackground(BaseModel):
    concepts: list[str] = Field(
        description=(
            "A list of key financial concepts or terms that will be introduced or "
            "explained in this activity. Each concept should be a short phrase or "
            "single word, e.g., 'budgeting', 'compound interest', 'emergency fund'."
        ),
    )
    content: str = Field(
        description=(
            "A comprehensive, user-friendly teaching explanation that covers each "
            "concept listed in 'concepts'. This content should clearly define and "
            "explain each concept, describe how they are related, and provide context "
            "for why they matter to the user. The explanation should be tailored to "
            "the user's background and designed to help them understand the knowledge "
            "needed to successfully complete the activity."
        )
    )


class ActivityStep(BaseModel):
    index: int = Field(
        description=(
            "The step number within the activity, starting from 1. Steps should be "
            "ordered sequentially to guide the user through the activity."
        ),
    )
    title: str = Field(
        description=(
            "A short, descriptive title for this step. It should summarize the main "
            "action or focus of the step, e.g., 'List Your Monthly Expenses'."
        ),
    )
    content: str = Field(
        description=(
            "A clear, actionable instruction or explanation for this step. This "
            "should guide the user on what to do, think about, or discuss."
        ),
    )
    step_objective: str = Field(
        description=(
            "A brief statement of the specific learning or action objective for this "
            "step. It should clarify what the user will achieve or understand by "
            "completing this step."
        ),
    )


class Activity(BaseModel):
    title: str = Field(
        description=(
            "The name of the activity. This should be engaging and clearly indicate "
            "the main topic or goal, e.g., 'Creating Your First Budget'."
        ),
    )
    description: str = Field(
        description="A concise background summary for the activity. This should introduce "
        "the main topic, explain its importance, and provide context for why "
        "the user should learn about it, tailored to their personal situation."
    )
    overall_objective: str = Field(
        description=(
            "A summary of the main learning or practical objective of the activity. "
            "It should describe what the user will accomplish or understand by the "
            "end of the activity."
        ),
    )
    background: ActivityBackground = Field(
        description=(
            "Background information for the activity, including key concepts and a "
            "contextual introduction tailored to the user's situation."
        ),
    )
    steps: list[ActivityStep] = Field(
        description=(
            "A list of sequential steps that make up the activity. Each step should "
            "be clear, actionable, and build towards the overall objective."
        ),
    )
    glossary: dict[str, str] | None = Field(
        default=None,
        description=(
            "A dictionary of key terms and their definitions used in this activity. "
            "Helps users understand jargon and technical language."
        ),
    )
    alternative_methods: list[str] | None = Field(
        default=None,
        description=(
            "Suggestions for non-technical or alternative ways to complete the activity "
            "if the user is not comfortable with the primary method (e.g., using pen and paper instead of a spreadsheet)."
        ),
    )

    level: ActivityLevel = Field(
        default=ActivityLevel.Beginner,
        description=(
            "The level of the activity. This helps categorize the activity and provide "
            "appropriate guidance for the user."
        ),
    )

    def as_xml(self) -> str:
        return format_as_xml(self)


class Activities(BaseModel):
    activities: list[Activity] = Field(  # noqa: F821
        description=(
            "A list of all generated activities. Each activity should be tailored "
            "to the user's context and designed to help them achieve their financial goals."
        ),
    )


class OnboardingDataComplete(BaseModel):
    """All relevant information collected during the onboarding process."""

    # 1. Life Stage
    life_stage: Literal["Student", "Professional", "Retired", "Parent"] = Field(
        description=(
            "The user's current stage of life. "
            "Examples: 'Student', 'Working professional', 'Retired', 'Parent', etc. "
            "This helps adapt financial education to the user's situation. "
            "Should be filled when the user shares this information. "
            "Leave as None if not yet provided."
        ),
    )

    # 2. Profession
    profession: str = Field(
        description=(
            "The user's current profession or occupation. "
            "This helps provide relevant financial examples and analogies. "
            "Should be filled when the user shares their job, career, or main activity. "
            "Leave as None if not yet provided."
        ),
    )

    # 3. Age Range
    age_range: Literal[
        "0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"
    ] = Field(
        description=(
            "The user's age range, such as '20-29', '30-39', etc. "
            "This helps contextualize financial advice for different life stages. "
            "Should be filled when the user provides their age or age group. "
        ),
    )

    # 4. Personal Context
    personal_context: PersonalContext = Field(
        description=(
            "Additional personal information to further personalize financial education. "
            "Includes hobbies and family status. "
            "Should be filled as the user shares more about their personal life. "
        ),
    )

    # 5. Financial Goals
    financial_goals: list[str] = Field(
        description=(
            "A list of the user's main financial goals. "
            "Examples: 'Save for a house', 'Build an emergency fund', 'Plan for retirement', etc. "
            "Should be filled as the user shares their financial objectives. "
        ),
    )

    # 6. Financial Interests
    financial_interests: list[str] = Field(
        description=(
            "Topics or areas of finance the user is interested in learning about. "
            "Examples: 'Investing', 'Budgeting', 'Debt management', etc. "
            "Should be filled as the user expresses their interests. "
        ),
    )

    # 7. Financial Concerns
    financial_concerns: list[str] = Field(
        description=(
            "Common financial worries, doubts, or challenges the user faces. "
            "Examples: 'Managing debt', 'Understanding investments', 'Saving enough', etc. "
            "Should be filled as the user shares their concerns. "
        ),
    )

    # 8. Financial Knowledge Level
    financial_knowledge_level: Literal[
        "Basic", "Intermediate", "Advanced", "Unknown"
    ] = Field(
        "Unknown",
        description=(
            "The user's self-assessed level of financial knowledge. "
            "Possible values: 'Basic', 'Intermediate', 'Advanced'. "
            "This helps adjust the complexity of explanations. "
            "Should be filled when the user shares their comfort level with financial topics. "
        ),
    )

    # 9. Previous Experience
    previous_experience: list[str] = Field(
        description=(
            "Relevant previous experience the user has with financial products, services, or education. "
            "Examples: 'Has invested in stocks', 'Attended a finance workshop', etc. "
            "Should be filled as the user shares their background. "
        ),
    )

    def as_xml(self) -> str:
        return format_as_xml(self)


async def create_activities_from_onboarding_data(
    onboarding_data: OnboardingDataComplete,
):
    llm = ChatOpenAI(model="o3-2025-04-16")

    system_prompt = """\
You are an expert financial educator and curriculum designer. Your task is to create a set of highly tailored, step-by-step teaching activities for a user, based on their onboarding information. The activities should be cohesive, relevant, and designed to help the user learn new financial concepts by connecting them to their personal context, goals, and environment.

Guidelines:
1. **Personalization**: Use the user's life stage, profession, age range, hobbies, family status, financial goals, interests, concerns, knowledge level, and previous experience to make the activities as relevant and engaging as possible.
2. **Cohesion**: The activities should form a logical sequence, with each activity building on the previous one, leading the user toward their stated financial goals.
3. **Clarity**: Each activity must have a clear title, an overall objective, and a concise background that introduces the key concepts and explains why they matter for the user.
4. **Step-by-Step Structure**: Break down each activity into clear, numbered steps. Each step should have:
    - An index (starting from 1)
    - A descriptive title
    - A short, actionable instruction or explanation
    - A specific step objective
5. **Contextualization**: Use examples, analogies, and scenarios that are familiar to the user, based on their profession, hobbies, and life situation. Reference family status where relevant.
6. **Progression**: Start with foundational concepts if the user's knowledge is basic, or introduce more advanced topics if they are experienced. Always connect new concepts to what the user already knows or has experienced.
7. **Engagement and Reflection**: Make the activities interactive and thought-provoking, encouraging the user to reflect, apply, or discuss what they learn. Include at least one step in each activity that prompts the user to reflect on their feelings, motivations, or challenges related to the topic.
8. **Accessibility**: Avoid overwhelming the user with too much information at once. If technical tools (like spreadsheets or scripts) are suggested, also offer a non-technical alternative.
9. **Jargon and Definitions**: Clearly define any financial or technical jargon used, either in the background or as a glossary step.
10. **Adaptation**: If the user already has experience with a topic, suggest ways to deepen or adapt the activity for their level.
11. **Output Format**: Return the activities as a structured JSON object matching the provided schema (Activities), with all required fields filled.

Your output will be used as the basis for an interactive learning experience, where an AI will guide the user through each activity and step in conversation.

Example activity titles:
- "Building Your First Budget as a Software Engineer"
- "Understanding Emergency Funds: Why and How"
- "Investing Basics: Getting Started with What You Know"

Be creative, empathetic, and practical. Focus on helping the user achieve their financial goals in a way that feels relevant and achievable in their real life, and that increases their financial literacy and confidence.
"""

    activities = await llm.with_structured_output(
        schema=Activities, strict=True
    ).ainvoke(
        [
            ("system", system_prompt),
            ("user", onboarding_data.model_dump_json(indent=2)),
        ]
    )

    if not isinstance(activities, Activities):
        raise ValueError("Invalid activities structure")

    return activities


if __name__ == "__main__":
    import asyncio

    async def main():
        onboarding_data = onboarding_data = OnboardingDataComplete(
            life_stage="Professional",
            profession="Software Engineer",
            age_range="30-39",
            personal_context=PersonalContext(
                hobbies=["reading", "cycling"],
                family_status="Single",
            ),
            financial_goals=["Save for a house", "Build an emergency fund"],
            financial_interests=["Investing", "Budgeting"],
            financial_concerns=["Managing debt", "Saving enough"],
            financial_knowledge_level="Intermediate",
            previous_experience=[
                "Has invested in stocks",
                "Attended a finance workshop",
            ],
        )

        activities = await create_activities_from_onboarding_data(onboarding_data)
        print(activities.model_dump_json(indent=2))

    asyncio.run(main())
