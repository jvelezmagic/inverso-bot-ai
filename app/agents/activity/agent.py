from typing import Annotated, Literal

from langchain_core.messages import BaseMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_core.tools.base import InjectedToolCallId
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph, add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.types import Command
from pydantic import BaseModel, Field
from pydantic_ai import format_as_xml

from app.agents.activity.create import (
    Activity,
    ActivityBackground,
    ActivityStep,
    OnboadingDataComplete,
)
from app.agents.onboarding import PersonalContext

Messages = Annotated[list[BaseMessage], add_messages]

type BotResponse = dict[Literal["messages"], list[BaseMessage]]


class Configuration(BaseModel):
    """The configurable fields for the chatbot."""

    user_full_name: str = Field(default="John Doe")

    @classmethod
    def from_runnable_config(
        cls, config: RunnableConfig | None = None
    ) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )

        values = {key: values for key, values in configurable.items() if key}

        return cls(**values)


class ActivityStepProgress(BaseModel):
    index: int = Field(
        description=(
            "The step number within the activity, starting from 1. Steps should be "
            "ordered sequentially to guide the user through the activity."
        ),
    )
    status: Literal["Not started", "In progress", "Completed"] = Field(
        description=(
            "The current status of the step. Possible values: 'Not started', 'In progress', 'Completed'."
        ),
    )


class ActivityProgress(BaseModel):
    steps: list[ActivityStepProgress] = Field(
        description=(
            "A list of the current progress of each step in the activity. "
            "Each step should be marked as 'Not started', 'In progress', or 'Completed'."
        ),
    )


def get_activity_progress(
    left_progress: ActivityProgress | None = None,
    rigth_progress: ActivityProgress | None = None,
) -> ActivityProgress | None:
    match left_progress, rigth_progress:
        case None, None:
            return None
        case None, rigth_progress:
            return rigth_progress
        case left_progress, None:
            return left_progress
        case left_progress, rigth_progress:
            return rigth_progress


class ChatActivityState(BaseModel):
    messages: Messages
    onboading_data: OnboadingDataComplete = Field(
        default=OnboadingDataComplete(
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
        ),
        description="Onboarding data",
    )
    activity: Activity = Field(
        default=Activity(
            title="Rapid Emergency Fund Blueprint for the Solo Engineer",
            description=(
                "Build a resilient emergency fund tailored to your single‑income, "
                "tech‑professional lifestyle so unexpected costs never derail your "
                "house‑saving plans."
            ),
            overall_objective=(
                "Have a fully funded, 6‑month emergency fund housed in the right account "
                "and an automated system to keep it on track."
            ),
            background=ActivityBackground(
                concepts=[
                    "emergency fund",
                    "living expenses",
                    "liquidity",
                    "opportunity cost",
                ],
                content=(
                    "An emergency fund is a cash buffer (usually 3–6 months of essential "
                    "living expenses) you can tap when life throws surprises—job loss, "
                    "medical bills, bike repairs. Liquidity means how quickly you can "
                    "access money without losing value; emergency funds need high liquidity "
                    "(think high‑yield savings accounts). While cash earns less than "
                    "investments (opportunity cost), it shields you from selling stocks at "
                    "a loss. As a single software engineer, you rely solely on your income, "
                    "so a 6‑month cushion minimizes risk and protects your bigger goal: "
                    "buying a house."
                ),
            ),
            steps=[
                ActivityStep(
                    index=1,
                    title="Tally Your Core Living Expenses",
                    content=(
                        "Export the last 3 months of transactions from your bank or budgeting "
                        "app. Write or code a quick script to categorize rent, food, utilities, "
                        "insurance, transport, and minimum debt payments. Average each category "
                        "to get one month of core costs."
                    ),
                    step_objective="Establish an accurate monthly baseline for essential expenses.",
                ),
                ActivityStep(
                    index=2,
                    title="Set Your Fund Size Target",
                    content=(
                        "Multiply the monthly core cost by 6 (or 4 if you feel your job is "
                        "ultra‑stable, 9 if you want extra security). Note the final dollar "
                        "amount; this is your emergency‑fund ‘definition of done’."
                    ),
                    step_objective="Define a specific, measurable emergency‑fund goal.",
                ),
                ActivityStep(
                    index=3,
                    title="Pick a Parking Spot",
                    content=(
                        "Compare at least two high‑yield savings accounts (HYSA) or "
                        "money‑market funds. Prioritize FDIC/NCUA insurance, same‑day "
                        "withdrawal, and APY. Open the chosen account and nickname it "
                        "“Safety Net”."
                    ),
                    step_objective="Select a liquid, low‑risk account for the fund.",
                ),
                ActivityStep(
                    index=4,
                    title="Automate the Cashflow",
                    content=(
                        "Set up an automatic transfer from checking each payday for 10–15% "
                        "of net income (adjust if you’re also allocating to house savings). "
                        "Treat it like a non‑negotiable bill."
                    ),
                    step_objective=(
                        "Create a default system that funds the emergency account without manual effort."
                    ),
                ),
                ActivityStep(
                    index=5,
                    title="Stress‑Test & Reflect",
                    content=(
                        "Imagine a sudden layoff or $3k bike accident bill. Would 6 months "
                        "feel sufficient? Journal one paragraph on your emotional reaction "
                        "to these scenarios and any tweaks you’d make."
                    ),
                    step_objective=(
                        "Evaluate psychological comfort and refine the target or timeline."
                    ),
                ),
                ActivityStep(
                    index=6,
                    title="Schedule Quarterly Health Checks",
                    content=(
                        "Add a recurring calendar event to verify balance, APY, and "
                        "contribution rate. Adjust if expenses or income change."
                    ),
                    step_objective=(
                        "Ensure the fund stays right‑sized and optimized over time."
                    ),
                ),
            ],
            glossary={
                "Emergency fund": "Cash reserve for unexpected expenses or income gaps.",
                "Liquidity": "Ease and speed of converting assets to cash without loss.",
                "Opportunity cost": "Potential gains you miss by choosing one option over another.",
                "HYSA": "High‑yield savings account offering higher interest than regular savings.",
            },
            alternative_methods=[
                "Use a paper ledger instead of a spreadsheet for expense tallying.",
                "If automation feels scary, set a monthly phone reminder to transfer funds manually.",
            ],
        )
    )
    progress: Annotated[ActivityProgress | None, get_activity_progress] = Field(
        default=None,
        description="Activity progress",
    )


@tool
async def update_activity_progress(  # type: ignore
    tool_call_id: Annotated[
        str,
        InjectedToolCallId,
    ],
    progress: ActivityProgress,
):
    """Update the progress of the activity. Full progress is required to be provided even if there are not started steps."""
    return Command(  # type: ignore
        update={
            "progress": progress.model_dump(),
            "messages": [
                ToolMessage(
                    "Sucessfully looked up user progress",
                    tool_call_id=tool_call_id,
                )
            ],
        },
    )


tools = [update_activity_progress]
tool_node = ToolNode(tools=tools)


async def chat_activity(
    state: ChatActivityState, config: RunnableConfig
) -> BotResponse:
    configuration = Configuration.from_runnable_config(config)

    messages = state.messages
    onboarding_data = state.onboading_data
    activity = state.activity
    progress = state.progress

    if progress is None:
        progress = ActivityProgress(
            steps=[
                ActivityStepProgress(index=i, status="Not started")
                for i in range(1, len(activity.steps) + 1)
            ]
        )

    onboarding_data_str = format_as_xml(onboarding_data)
    activity_str = format_as_xml(activity)
    progress_str = format_as_xml(progress)

    system_prompt = """\
You are InversaAI, an expert, friendly, and highly adaptive financial learning companion. Your mission is to guide the user step-by-step through a personalized financial activity, making the experience interactive, practical, and confidence-building.

**Your Role:**
- Act as a coach, mentor, and explainer—never just a lecturer.
- Use the user's onboarding data, current activity, and progress to tailor your responses.
- Make each step clear, actionable, and relevant to the user's real life, profession, and goals.
- Encourage reflection, questions, and honest discussion about challenges or feelings.

**How to Respond:**
- Focus on short, interactive, and engaging responses. Avoid long explanations unless the user asks for more detail.
- **Haz solo una pregunta clara y concreta por turno.** Espera la respuesta del usuario antes de avanzar o preguntar algo más.
- Prioritize asking questions, checking understanding, and gathering information from the user to help them progress.
- Always greet the user by their first name when starting a new session or activity.
- Clearly state which step the user is on, and briefly summarize the overall activity objective only if needed.
- For each step:
    - Explain the purpose and importance of the step in simple, relatable terms, but keep it concise.
    - Give clear, actionable instructions.
    - Offer examples or analogies relevant to the user's background (profession, hobbies, family status), but keep them brief.
    - If the user seems stuck or unsure, offer encouragement, alternative methods, or break the step down further, pero solo una opción o sugerencia a la vez.
    - Prompt the user to reflect or share their thoughts, especially on steps involving feelings or motivations.
- If the user asks for definitions or clarification, provide concise, jargon-free explanations, using the glossary if available.
- If the user completes a step, celebrate their progress and guide them to the next step.
- If the user wants to skip, adapt, or revisit a step, support their choice and adjust the plan accordingly.
- If technical tools are suggested, always offer a non-technical alternative.
- Keep the conversation positive, empathetic, and focused on building the user's financial confidence.

**Importante:**
La mayor parte de la información estática (título de la actividad, descripción, objetivos, lista de pasos, glosario y perfil del usuario) siempre está visible en la interfaz. **No repitas esta información a menos que el usuario la solicite.**  
**Concéntrate en interactuar, medir y recopilar información del usuario. Haz tus respuestas cortas, prácticas y conversacionales. Haz solo una pregunta por turno.**

**Context Available:**
- You have access to the user's onboarding data, the full activity structure, and their current progress.
- Use this information to personalize every response and make the learning journey feel unique and supportive.

**Rules for Updating Progress:**
- You must call the `update_activity_progress` tool **immediately** after the user completes a step, marks a step as done, or explicitly indicates they have finished a task for a step.
- If the user goes back, repeats, or changes the status of a step (for example, marks a previous step as incomplete or wants to redo it), you must also call the tool to reflect the new status.
- If the user skips a step, update the progress to reflect this and call the tool.
- Any time the status of any step changes (for example, from "Not started" to "In progress", or from "In progress" to "Completed"), you must update the progress using the tool.
- Do **not** call the tool if there has been no change in the status of any steps.
- When you call the tool, always send the full, updated status of all steps, not just the one that changed.

    **Examples:**
    - If the user says they have finished Step 1, mark that step as "Completed" and call the tool.
    - If the user wants to go back to Step 2 and redo it, mark that step as "In progress" and call the tool.
    - If the user decides to skip Step 3, update the progress to reflect this and call the tool.

**Output Format:**
- Respond conversationally, as if you are speaking directly to the user.
- When referencing steps, use their titles and numbers for clarity.
- If you need to update progress or use a tool, do so as instructed by the system.


Begin by welcoming the user and introducing the activity. Then, guide them through the first step, making sure they understand what to do and why it matters.

You are InversaAI—the user's trusted guide to mastering their financial goals, one step at a time.

<onboarding_data>
{onboarding_data}
</onboarding_data>

<activity>
{activity}
</activity>

<progress>
{progress}
</progress>

Now, take a deep breath and let's get started!
"""

    prompt = ChatPromptTemplate.from_messages(  # type: ignore
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    llm = ChatOpenAI(temperature=0.0, model="gpt-4.1")
    llm_with_tools = llm.bind_tools(tools=tools)
    llm_with_tools = prompt | llm_with_tools

    response = await llm_with_tools.ainvoke(
        {  # type: ignore
            "messages": [("system", system_prompt)] + messages,
            "onboarding_data": onboarding_data_str,
            "activity": activity_str,
            "progress": progress_str,
        }
    )

    return {
        "messages": [response],
    }


chat_activity_agent_builder = StateGraph(
    state_schema=ChatActivityState,
)

chat_activity_agent_builder.add_node("chat_activity", chat_activity)
chat_activity_agent_builder.add_node("tools", tool_node)

chat_activity_agent_builder.set_entry_point("chat_activity")
chat_activity_agent_builder.add_conditional_edges("chat_activity", tools_condition)
chat_activity_agent_builder.add_edge("tools", "chat_activity")
chat_activity_agent_builder.add_edge("chat_activity", END)


def get_graph(checkpointer: AsyncPostgresSaver | None = None) -> CompiledStateGraph:
    return chat_activity_agent_builder.compile(checkpointer=checkpointer)
