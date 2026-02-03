import os
from datetime import date
from crewai import LLM, Agent, Crew, Process, Task
from tools.availability_tool import AvailabilityTool

class TataAgent:
    """TataAgent - An agent that manages Tata's availability."""

    SUPPORTED_CONTENT_TYPES = ["text/plain"]

    def __init__(self):
        """Initializes the TataAgent."""
        if os.getenv("GOOGLE_API_KEY"):
            self.llm = LLM(
                model="gemini/gemini-2.5-flash-lite",
                api_key=os.getenv("GOOGLE_API_KEY"),
            )
        else:
            raise ValueError("Variable de entorno 'GOOGLE_API_KEY' no establecida.")

        self.tata_assistant = Agent(
            role="Tata Personal Scheduling Assistant",
            goal="Consulta el calendario de Tata y resuelve cualquier duda sobre su disponibilidad.",
            backstory=(
                "Eres un asistente muy eficiente y educado. Tu única tarea es gestionar la agenda de Tata."
                "Eres un experto en usar la herramienta de verificación de disponibilidad del calendario para saber cuándo está libre el tata."
                "Nunca te metes en conversaciones fuera del horario de programación."
            ),
            verbose=True,
            allow_delegation=False,
            tools=[AvailabilityTool()],
            llm=self.llm,
        )

    def invoke(self, question: str) -> str:
        """Kicks off the crew to answer a scheduling question."""
        task_description = (
            f"Responder la pregunta del usuario sobre la disponibilidad de Tata. El usuario pregunto: '{question}'. "
            f"La fecha de hoy es {date.today().strftime('%Y-%m-%d')}."
        )

        check_availability_task = Task(
            description=task_description,
            expected_output="Una respuesta cortes y concisa a la pregunta del usuario sobre la disponibilidad, basada en el resultado de la herramienta de calendario.",
            agent=self.tata_assistant,
        )

        crew = Crew(
            agents=[self.tata_assistant],
            tasks=[check_availability_task],
            process=Process.sequential,
            verbose=True,
        )
        result = crew.kickoff()
        return str(result)