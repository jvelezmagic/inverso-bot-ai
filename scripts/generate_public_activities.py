import asyncio
from typing import TypedDict

import tqdm.asyncio

from app.activity.create_from_concepts import create_activity_from_concepts
from app.activity.models import Activity, ActivityLevel
from app.activity.repository import ActivityRepository
from app.database.session import SessionLocal


class ActivityData(TypedDict):
    title: str
    concepts: list[str]
    guided_description: str


data: dict[ActivityLevel, list[ActivityData]] = {
    ActivityLevel.Beginner: [
        {
            "title": "Introducción a las finanzas personales",
            "concepts": ["Finanzas personales", "Hábitos financieros"],
            "guided_description": "Acompaña a Laura, una joven profesionista que acaba de recibir su primer salario, mientras descubre cómo organizar su dinero y sentar las bases de una vida financiera saludable.",
        },
        {
            "title": "Establecimiento de metas financieras SMART",
            "concepts": ["Metas SMART", "Planificación financiera básica"],
            "guided_description": "Usaremos el caso de Carlos, quien desea comprar una motocicleta en un año, para mostrar cómo convertir un sueño en un objetivo financiero SMART (específico, medible, alcanzable, relevante y con límite de tiempo).",
        },
        {
            "title": "Presupuesto y control de gastos",
            "concepts": ["Presupuesto", "Registro de gastos", "Control financiero"],
            "guided_description": "Ana y Diego, una pareja que vive junta por primera vez, necesitan equilibrar gastos de renta, comida y ocio. Diseñarás con ellos un presupuesto mensual sencillo y descubrirás métodos para no salirte del plan.",
        },
        {
            "title": "Ahorro y fondo de emergencia",
            "concepts": ["Ahorro", "Fondo de emergencia", "Disciplina financiera"],
            "guided_description": "Imagina que pierdes tu empleo de forma imprevista. Construiremos un fondo de emergencia paso a paso y compararemos métodos de ahorro para diferentes niveles de ingreso.",
        },
        {
            "title": "Interés compuesto y crecimiento del dinero",
            "concepts": ["Interés compuesto", "Crecimiento del capital"],
            "guided_description": "Verás cómo un pequeño depósito mensual puede multiplicarse con el tiempo gracias al interés compuesto, usando la historia de un estudiante que inicia con 500 MXN al mes.",
        },
        {
            "title": "Uso responsable de tarjetas de crédito",
            "concepts": ["Crédito", "Tasa de interés", "Historial crediticio"],
            "guided_description": "Guiarás a Sofía en su primera experiencia con una tarjeta de crédito: límites, fechas de corte y formas de evitar intereses moratorios.",
        },
        {
            "title": "Manejo de deudas y estrategias de pago",
            "concepts": ["Deuda", "Estrategias de pago", "Consolidación"],
            "guided_description": "Compararemos el método bola de nieve y el método avalancha ayudando a Pedro a pagar tres deudas distintas sin afectar su flujo de efectivo.",
        },
        {
            "title": "Seguros personales básicos",
            "concepts": ["Seguro de vida", "Seguro de salud", "Protección financiera"],
            "guided_description": "Elabora con Mariana un minianálisis costo-beneficio para contratar un seguro de gastos médicos mayores y uno de vida, considerando su presupuesto limitado.",
        },
        {
            "title": "Conceptos fiscales personales básicos",
            "concepts": ["Impuestos", "Deducciones", "Declaración de impuestos"],
            "guided_description": "A través del caso de un freelance descubrirás qué ingresos se declaran, posibles deducciones y cuándo conviene usar la declaración pre-llenada del SAT.",
        },
        {
            "title": "Alfabetización financiera digital",
            "concepts": [
                "Banca en línea",
                "Aplicaciones financieras",
                "Seguridad digital",
            ],
            "guided_description": "Explorarás con una adulta mayor cómo usar apps bancarias, evitar fraudes y activar la autenticación de dos factores.",
        },
    ],
    ActivityLevel.Intermediate: [
        {
            "title": "Inversión en renta fija y renta variable",
            "concepts": ["Bonos", "Acciones", "Rentabilidad"],
            "guided_description": "Gestionarás un portafolio simulado de 50 000 MXN, repartiendo entre CETES y acciones mexicanas conocidas, para comparar rendimientos y riesgos.",
        },
        {
            "title": "Diversificación y asignación de activos",
            "concepts": [
                "Diversificación",
                "Asignación de activos",
                "Cartera equilibrada",
            ],
            "guided_description": "Diseñarás tres carteras (conservadora, balanceada y agresiva) para un inversionista de 35 años, analizando correlaciones y volatilidad histórica.",
        },
        {
            "title": "Fondos de inversión y ETFs",
            "concepts": ["Fondos mutuos", "ETFs", "Costo total"],
            "guided_description": "Evaluarás el impacto de comisiones (TER) en dos ETFs similares que replican el S&P/BMV IPC, proyectando el costo a 10 años.",
        },
        {
            "title": "Análisis fundamental y técnico",
            "concepts": ["Análisis fundamental", "Análisis técnico", "Valoración"],
            "guided_description": "A partir de los estados financieros de una empresa de consumo y su gráfico de precios, aplicarás P/E, RSI y medias móviles para decidir si comprar o vender.",
        },
        {
            "title": "Planificación para la jubilación",
            "concepts": ["Planes de pensiones", "Retiro", "Ahorro a largo plazo"],
            "guided_description": "Ayuda a una profesionista independiente de 30 años a calcular cuánto necesita ahorrar mensualmente para jubilarse a los 65 con el 80 % de su ingreso actual.",
        },
        {
            "title": "Gestión del riesgo e indicadores",
            "concepts": ["Riesgo financiero", "Beta", "Desviación estándar"],
            "guided_description": "Compararás dos acciones con betas distintas para determinar cuál se ajusta mejor a la tolerancia de riesgo de un inversionista moderado.",
        },
        {
            "title": "Inflación y poder adquisitivo",
            "concepts": ["Inflación", "Índice de precios", "Valor real"],
            "guided_description": "Simularás el impacto de 5 % de inflación anual sobre 1 000 MXN durante 15 años y analizarás estrategias para preservar poder adquisitivo.",
        },
        {
            "title": "Criptomonedas y activos digitales",
            "concepts": ["Bitcoin", "Blockchain", "Volatilidad"],
            "guided_description": "Crearás un miniportafolio con 2 % de BTC y 98 % de renta fija para observar cómo la volatilidad cripto afecta la rentabilidad global.",
        },
        {
            "title": "Planificación fiscal intermedia",
            "concepts": ["Eficiencia fiscal", "Diferimiento", "Beneficios fiscales"],
            "guided_description": "Revisarás cómo las cuentas personales para el retiro (AFORE, PPR) permiten diferir impuestos y aumentar la tasa interna de retorno.",
        },
        {
            "title": "Seguros avanzados",
            "concepts": [
                "Seguro de vida completo",
                "Seguro de propiedad",
                "Cobertura amplia",
            ],
            "guided_description": "Analizarás la póliza de una pyme, detectando exclusiones y calculando la suma asegurada adecuada para maquinaria crítica.",
        },
    ],
    ActivityLevel.Advanced: [
        {
            "title": "Derivados financieros: opciones y futuros",
            "concepts": ["Opciones", "Futuros", "Apalancamiento"],
            "guided_description": "Cubrirás la posición de un productor de maíz con futuros sobre maíz y usarás opciones put para limitar pérdidas ante caídas de precio.",
        },
        {
            "title": "Apalancamiento y margen",
            "concepts": ["Apalancamiento", "Cuenta margen", "Riesgo ampliado"],
            "guided_description": "Simularás la compra de acciones con 50 % de margen, midiendo el efecto de una caída del 15 % en el precio sobre el capital propio.",
        },
        {
            "title": "Coberturas (hedging) y gestión de cartera",
            "concepts": ["Cobertura", "Hedging", "Protección de cartera"],
            "guided_description": "Implementarás una cobertura con ETFs inversos para una cartera de acciones tecnológicas durante un periodo de alta volatilidad.",
        },
        {
            "title": "Modelos de valoración avanzados",
            "concepts": ["CAPM", "Black-Scholes", "Flujos de efectivo descontados"],
            "guided_description": "Valorarás una opción call europea sobre una acción mexicana aplicando Black-Scholes y verificarás la prima teórica frente a la del mercado.",
        },
        {
            "title": "Gestión de carteras cuantitativa",
            "concepts": [
                "Algoritmos de inversión",
                "Trading cuantitativo",
                "Backtesting",
            ],
            "guided_description": "Desarrollarás un sencillo algoritmo momentum 12-2 y lo someterás a backtesting con datos de la BMV de los últimos 10 años.",
        },
        {
            "title": "Finanzas corporativas avanzadas",
            "concepts": ["WACC", "Fusiones y adquisiciones", "Valor presente neto"],
            "guided_description": "Calcularás el WACC de una empresa manufacturera, luego evaluarás la viabilidad de adquirir un competidor usando VPN.",
        },
        {
            "title": "Mercados internacionales y tipo de cambio",
            "concepts": ["Mercados globales", "Tipo de cambio", "Riesgo país"],
            "guided_description": "Analizarás el impacto de la apreciación del USD/MXN sobre las utilidades de una empresa exportadora mexicana y diseñarás una cobertura con forwards.",
        },
        {
            "title": "Regulación, cumplimiento y ética financiera",
            "concepts": ["Regulación financiera", "Cumplimiento", "Ética"],
            "guided_description": "Examinarás un caso de lavado de dinero para identificar banderas rojas y proponer controles internos conforme a la Ley AML mexicana.",
        },
        {
            "title": "Finanzas conductuales avanzadas",
            "concepts": [
                "Sesgos cognitivos",
                "Psicología del inversor",
                "Toma de decisiones",
            ],
            "guided_description": "Detectarás sesgos de confirmación y exceso de confianza en las decisiones de inversión de un gestor y diseñarás nudges para mitigarlos.",
        },
        {
            "title": "Finanzas sostenibles y ESG",
            "concepts": ["Inversión ESG", "Sostenibilidad", "Responsabilidad social"],
            "guided_description": "Evaluarás una emisión de bonos verdes, verificando criterios de sostenibilidad y midiendo el impacto ambiental reportado.",
        },
    ],
}


async def create(
    level: ActivityLevel,
    activity: ActivityData,
):
    generated_activity = await create_activity_from_concepts(
        level=level,
        concepts=activity["concepts"],
        guided_description=activity["guided_description"],
        user_context=None,
    )

    async with SessionLocal() as session:
        repository = ActivityRepository(session)
        await repository.create_public_activity(
            Activity(
                user_id=None,
                title=generated_activity.title,
                description=generated_activity.description,
                overall_objective=generated_activity.overall_objective,
                background=generated_activity.background.model_dump(),
                steps=[step.model_dump() for step in generated_activity.steps],
                glossary=generated_activity.glossary,
                alternative_methods=generated_activity.alternative_methods,
                level=generated_activity.level,
            )
        )

    return None


async def craete_rate_limited(
    level: ActivityLevel,
    activity: ActivityData,
    semaphore: asyncio.Semaphore,
):
    try:
        async with semaphore:
            return await create(level, activity)
    except Exception as e:
        print(f"Error creating activity: {e}")


async def main():
    max_concurrency = 10
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = [
        craete_rate_limited(
            level=level,
            activity=activity,
            semaphore=semaphore,
        )
        for level, activities in data.items()
        for activity in activities
    ]

    await tqdm.asyncio.tqdm.gather(*tasks, total=len(tasks))

    print("All tasks completed")


if __name__ == "__main__":
    asyncio.run(main())
