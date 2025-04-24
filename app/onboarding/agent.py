import datetime
from typing import Annotated, Literal

import trustcall
from langchain_core.callbacks.manager import (
    adispatch_custom_event,
)
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph, add_messages
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

Messages = Annotated[list[BaseMessage], add_messages]

type BotResponse = dict[Literal["messages"], list[BaseMessage]]


class Configuration(BaseModel):
    """The configurable fields for the chatbot."""

    user_full_name: str = Field(default="John Doe")
    current_date: datetime.date = Field(default_factory=datetime.date.today)

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


class PersonalContext(BaseModel):
    hobbies: list[str] = Field(
        default_factory=list,
        description=(
            "A list of the user's hobbies or personal interests. "
            "This helps personalize financial examples and advice. "
            "Should be filled with activities the user enjoys in their free time, "
            "such as sports, reading, music, travel, etc. "
            "Leave empty if the user has not shared this information yet."
        ),
    )
    family_status: Literal["Single", "Married", "Divorced", "With children"] | None = (
        Field(
            None,
            description=(
                "The user's current family or relationship status. "
                "Examples: 'Single', 'Married', 'Divorced', 'With children', etc. "
                "This information helps tailor financial guidance to the user's life situation. "
                "Should be filled when the user shares this context, otherwise leave as None."
            ),
        )
    )


def get_missing_fields(model: BaseModel, prefix: str = "") -> list[str]:
    missing: list[str] = []
    for field_name, field in model.__fields__.items():
        value = getattr(model, field_name)
        full_name = f"{prefix}.{field_name}" if prefix else field_name

        # Si es un modelo anidado, revisa recursivamente
        if isinstance(value, BaseModel):
            missing += get_missing_fields(value, prefix=full_name)
        # Si es una lista, considera faltante si está vacía y no es opcional
        elif isinstance(value, list):
            if not value and (
                field.default_factory is not None or field.default is not None
            ):
                # Solo marca como faltante si la lista está vacía y no es opcional
                missing.append(full_name)
        # Si es string, considera faltante si es None o vacío
        elif isinstance(value, str):
            if not value:
                missing.append(full_name)
        # Si es None y no tiene default, es faltante
        elif value is None:
            missing.append(full_name)
    return missing


def get_nested_attr(obj: object, attr_path: str):
    """Get nested attribute from an object using dot notation."""
    attrs = attr_path.split(".")
    for attr in attrs:
        if obj is None:
            return None
        obj = getattr(obj, attr, None)
    return obj


class OnboardingData(BaseModel):
    """All relevant information collected during the onboarding process."""

    # 1. Life Stage
    life_stage: Literal["Student", "Professional", "Retired", "Parent"] | None = Field(
        None,
        description=(
            "The user's current stage of life. "
            "Examples: 'Student', 'Working professional', 'Retired', 'Parent', etc. "
            "This helps adapt financial education to the user's situation. "
            "Should be filled when the user shares this information. "
            "Leave as None if not yet provided."
        ),
    )

    # 2. Profession
    profession: str | None = Field(
        None,
        description=(
            "The user's current profession or occupation. "
            "This helps provide relevant financial examples and analogies. "
            "Should be filled when the user shares their job, career, or main activity. "
            "Leave as None if not yet provided."
        ),
    )

    # 3. Age Range
    age_range: (
        Literal[
            "0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"
        ]
        | None
    ) = Field(
        None,
        description=(
            "The user's age range, such as '20-29', '30-39', etc. "
            "This helps contextualize financial advice for different life stages. "
            "Should be filled when the user provides their age or age group. "
            "Leave as None if not yet provided."
        ),
    )

    # 4. Personal Context
    personal_context: PersonalContext | None = Field(
        default_factory=lambda: PersonalContext(hobbies=[], family_status=None),
        description=(
            "Additional personal information to further personalize financial education. "
            "Includes hobbies and family status. "
            "Should be filled as the user shares more about their personal life. "
            "Leave as default if not yet provided."
        ),
    )

    # 5. Financial Goals
    financial_goals: list[str] = Field(
        default_factory=list,
        description=(
            "A list of the user's main financial goals. "
            "Examples: 'Save for a house', 'Build an emergency fund', 'Plan for retirement', etc. "
            "Should be filled as the user shares their financial objectives. "
            "Leave empty if not yet provided."
        ),
    )

    # 6. Financial Interests
    financial_interests: list[str] = Field(
        default_factory=list,
        description=(
            "Topics or areas of finance the user is interested in learning about. "
            "Examples: 'Investing', 'Budgeting', 'Debt management', etc. "
            "Should be filled as the user expresses their interests. "
            "Leave empty if not yet provided."
        ),
    )

    # 7. Financial Concerns
    financial_concerns: list[str] = Field(
        default_factory=list,
        description=(
            "Common financial worries, doubts, or challenges the user faces. "
            "Examples: 'Managing debt', 'Understanding investments', 'Saving enough', etc. "
            "Should be filled as the user shares their concerns. "
            "Leave empty if not yet provided."
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
            "Leave as None if not yet provided."
        ),
    )

    # 9. Previous Experience
    previous_experience: list[str] = Field(
        default_factory=list,
        description=(
            "Relevant previous experience the user has with financial products, services, or education. "
            "Examples: 'Has invested in stocks', 'Attended a finance workshop', etc. "
            "Should be filled as the user shares their background. "
            "Leave empty if not yet provided."
        ),
    )

    # # 10. Onboarding Completed (internal flag)
    onboarding_completed: bool = Field(
        default=False,
        description=(
            "Indicates whether all required onboarding information has been collected. "
            "Should be set to True only when all key fields are filled. "
            "Automatically managed by the onboarding process."
        ),
    )


def latest_onboarding_data(
    onboarding_data: OnboardingData | None, new_onboarding_data: OnboardingData | None
) -> OnboardingData:
    match onboarding_data, new_onboarding_data:
        case None, None:
            return OnboardingData(
                profession=None,
                age_range=None,
                life_stage=None,
                financial_goals=[],
                financial_interests=[],
                financial_concerns=[],
                financial_knowledge_level="Unknown",
                previous_experience=[],
                personal_context=PersonalContext(hobbies=[], family_status=None),
                onboarding_completed=False,
            )
        case None, new_onboarding_data:
            return new_onboarding_data
        case onboarding_data, None:
            return onboarding_data
        case onboarding_data, new_onboarding_data:
            return new_onboarding_data


class State(BaseModel):
    messages: Messages
    onboarding_data: Annotated[OnboardingData | None, latest_onboarding_data] = Field(
        default=None,
        description="Datos del onboarding",
    )


async def chat_onboarding(state: State, config: RunnableConfig) -> BotResponse:
    configuration = Configuration.from_runnable_config(config)

    messages = state.messages

    if state.onboarding_data is None:
        state.onboarding_data = OnboardingData(
            profession=None,
            age_range=None,
            life_stage=None,
            financial_goals=[],
            financial_interests=[],
            financial_concerns=[],
            financial_knowledge_level="Unknown",
            previous_experience=[],
            personal_context=PersonalContext(hobbies=[], family_status=None),
            onboarding_completed=False,
        )

    llm = ChatOpenAI(temperature=0.0, model="gpt-4.1")

    collected_information = "\n".join(
        f"{field}: {getattr(state.onboarding_data, field)}"
        for field in state.onboarding_data.__fields__
        if getattr(state.onboarding_data, field)
        and field not in get_missing_fields(state.onboarding_data)
    )

    missing_information = "\n".join(
        # f"{field}: {getattr(state.onboarding_data, field)}\nDescripción: {OnboardingData.__fields__[field].description}"
        f"{field}: {get_nested_attr(state.onboarding_data, field)}\nDescripción: {OnboardingData.model_fields[field.split('.')[0]].description}"
        for field in get_missing_fields(state.onboarding_data)
    )

    if missing_information:
        system_prompt = """\
    You are InversoAI, a friendly and empathetic financial assistant. 
    Your main goal is to help {user_full_name} understand personal finance concepts 
    in a simple and relatable way.

    You always speak in English and refer to yourself as 'InversoAI'.

    Begin by warmly greeting the user. Then, guide the conversation to collect key onboarding information, 
    such as their life stage, profession, age range, personal context, financial goals, interests, concerns, 
    knowledge level, and previous experience.

    **Follow the preestablished order of these topics as much as possible**:
    1. Life stage
    2. Profession
    3. Age range


    However, be flexible! If the conversation naturally flows to a different topic, or if changing the order 
    would make the interaction smoother and more engaging, feel free to adapt. Your priority is to make the 
    conversation feel natural, memorable, and enjoyable—not like filling out a form or paperwork.

    Ask only ONE open-ended question at a time, and wait for the user's answer before moving on. 
    Avoid overwhelming the user with multiple questions at once. Be patient, encouraging, and make the user 
    feel comfortable sharing information.

    As you progress, use the information you already know about the user to personalize your examples and explanations. 
    Here is the information collected so far:
    <collected_information>
    {collected_information}
    </collected_information>

    You still need to obtain the following information to complete onboarding:
    <missing_information>
    {missing_information}
    </missing_information>

    When you have ALL the context, introduce relevant financial concepts for the user. 
    Always explain with examples and analogies related to their experience, profession, or interests. 
    Break down complex topics into simple, clear steps, and frequently check if the user is understanding.

    If the user seems confused or asks for clarification, rephrase your explanations and offer additional examples. 
    Encourage questions and maintain a supportive, non-judgmental environment.

    Never give specific investment, legal, or tax advice. Focus on education and general guidance. 
    If a topic is outside your scope, kindly suggest consulting a qualified professional.

    Your responses should always be:
    - Friendly and approachable
    - Clear and jargon-free
    - Personalized to the user's context
    - Motivating and supportive
    - Focused on education, not direct advice

    Do not mark onboarding as completed if there is still missing information.

    Today is {current_date}.
    """

        system_message = system_prompt.format(
            user_full_name=configuration.user_full_name,
            current_date=configuration.current_date,
            collected_information=collected_information,
            missing_information="\n".join(get_missing_fields(state.onboarding_data)),
        )

        response = await llm.ainvoke([("system", system_message)] + messages)

        return {
            "messages": [response],
        }
    else:
        system_prompt = """\
You are InversoAI, a friendly and empathetic financial assistant.
Your main goal is to help {user_full_name} understand personal finance concepts
in a simple and relatable way.

You always speak in English and refer to yourself as 'InversoAI'.
You already collected all the information needed to complete an onboarding process in our platform.

Inform the user that the onboarding process is already completed in a friendly and empathetic way.
Tell them that you are exited to help them achieve their financial goals and that you are ready to assist them.

Close telling them that you are going to create customized learning activities for them and that you hope to see them soon."""

        system_message = system_prompt.format(
            user_full_name=configuration.user_full_name,
            current_date=configuration.current_date,
        )

        response = await llm.ainvoke([("system", system_message)] + messages)

        return {
            "messages": [response],
        }


async def collect_onboarding_data(state: State, config: RunnableConfig):
    if state.onboarding_data is None:
        state.onboarding_data = OnboardingData(
            profession=None,
            age_range=None,
            life_stage=None,
            financial_goals=[],
            financial_interests=[],
            financial_concerns=[],
            financial_knowledge_level="Unknown",
            previous_experience=[],
            personal_context=PersonalContext(hobbies=[], family_status=None),
            onboarding_completed=False,
        )

    llm = ChatOpenAI(
        temperature=0.0,
        # model="gpt-4.1",
        # model="gpt-4o-mini-2024-07-18",
        model="gpt-4.1-mini-2025-04-14",
        # model="gpt-4.1-nano-2025-04-14",
    )

    extractor = trustcall.create_extractor(
        llm=llm,
        tools=[OnboardingData],
        tool_choice="OnboardingData",
    )

    response = await extractor.ainvoke(
        {
            "messages": state.messages,
            "existing": {"OnboardingData": state.onboarding_data.model_dump()},
        }
    )
    extracted_data = response["responses"]
    final_onboarding_data = (
        extracted_data[0] if extracted_data else state.onboarding_data
    )

    onboarding_completed = getattr(final_onboarding_data, "onboarding_completed", False)
    if onboarding_completed:
        await adispatch_custom_event(
            "onboarding_completed",
            final_onboarding_data.model_dump(),
        )

    return {"onboarding_data": final_onboarding_data}


onboarding_agent_builder = StateGraph(
    state_schema=State,
)

onboarding_agent_builder.add_node("collect_onboarding_data", collect_onboarding_data)
onboarding_agent_builder.add_node("chat_onboarding", chat_onboarding)

onboarding_agent_builder.set_entry_point("collect_onboarding_data")
onboarding_agent_builder.add_edge("collect_onboarding_data", "chat_onboarding")
onboarding_agent_builder.add_edge("chat_onboarding", END)


def get_graph(checkpointer: AsyncPostgresSaver | None = None) -> CompiledStateGraph:
    return onboarding_agent_builder.compile(checkpointer=checkpointer)
