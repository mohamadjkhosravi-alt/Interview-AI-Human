from openai import OpenAI
from fastapi import FastAPI
from pydantic import BaseModel
import json
from datetime import datetime
from pathlib import Path

client = OpenAI()
app = FastAPI()

OPENING_QUESTION = "How do you usually think about giving money to charity or helping other people financially?"
CLOSING_QUESTION = "Looking back at this conversation, what do you think is the main reason people sometimes sound more generous than they really are?"
OPTIONAL_CLOSING_QUESTION = "Is there anything important about how people talk about donation versus how they actually act that we have not discussed yet?"

TOPICS = [
    {
        "name": "General motives and hesitation around donation",
        "objective": "Understand what makes giving easier or harder, including trust, financial comfort, and perceived impact.",
        "core_question": "What usually makes someone more willing, or less willing, to give money to charity?"
    },
    {
        "name": "Gap between what people say and what they do",
        "objective": "Explore why people may say they would donate more than they actually do, and what creates the gap between stated generosity and real behavior.",
        "core_question": "In what kinds of situations do people say they would give more than they actually end up giving?"
    },
    {
        "name": "Social judgment and interviewer effects",
        "objective": "Explore whether talking to a human versus an AI changes what people say, and whether social judgment affects responses.",
        "core_question": "How, if at all, does talking to another person change the way people talk about generosity or donation?"
    },
    {
        "name": "Personal realistic donation choice",
        "objective": "Bring the participant to a concrete personal choice involving real money and understand the reasoning behind that choice.",
        "core_question": "If you personally were given $10 and could choose how much to keep and how much to donate to a real charity, what do you think you would actually do?"
    }
]

MAX_PROBES_PER_TOPIC = 2

PROBING_PROMPT = """
You are a neutral research interviewer conducting a semi-structured interview about charitable giving, donation decisions, and the gap between what people say and what they actually do.

Your task is to generate exactly one short follow-up question based on the participant's last response.

Rules:
- Ask exactly one question.
- Keep the question short, natural, and easy to answer aloud.
- The question must be open-ended whenever possible.
- Do not ask yes/no questions unless clarification is absolutely necessary.
- Be neutral and non-judgmental.
- Do not pressure the participant to sound generous or moral.
- Do not praise, criticize, or suggest a socially desirable answer.
- Stay within the current topic.
- If the answer is vague, ask for clarification.
- If the answer is meaningful but shallow, ask a deeper follow-up.
- If the participant is speaking generally about "people," you may gently ask whether that also applies to them personally, but do not do this aggressively.
- Do not repeat earlier wording unless necessary.
- Do not ask more than one question.
- Do not explain your reasoning.
- Return only the question text.
"""

TOPIC_PROMPT = """
You are a neutral research interviewer conducting a semi-structured interview about charitable giving, donation decisions, and the gap between what people say and what they actually do.

Your task is to generate exactly one short transition question that moves the conversation from the previous topic to the next topic in a natural way.

Rules:
- Ask exactly one question.
- The question should smoothly introduce the next topic.
- Keep it short, natural, and easy to answer aloud.
- Make it open-ended whenever possible.
- Be neutral and non-judgmental.
- Do not sound robotic or abrupt.
- Do not summarize too much.
- Do not ask more than one question.
- Do not explain your reasoning.
- Return only the question text.
"""

DATA_DIR = Path("interview_data")
DATA_DIR.mkdir(exist_ok=True)

SESSIONS = {}


class StartInterviewRequest(BaseModel):
    participant_id: str


class NextQuestionRequest(BaseModel):
    participant_id: str
    participant_response: str


def ask_llm(prompt: str) -> str:
    response = client.responses.create(
        model="gpt-5",
        input=prompt
    )
    return response.output_text.strip()


def generate_probe(current_topic: str, topic_objective: str, last_response: str, recent_history: str = "") -> str:
    prompt = f"""
{PROBING_PROMPT}

Current interview topic:
{current_topic}

Topic objective:
{topic_objective}

Participant's last response:
{last_response}

Relevant recent conversation:
{recent_history}
"""
    return ask_llm(prompt)


def generate_transition(previous_topic: str, next_topic: str, next_topic_objective: str, recent_history: str = "") -> str:
    prompt = f"""
{TOPIC_PROMPT}

Previous topic:
{previous_topic}

Next topic:
{next_topic}

Next topic objective:
{next_topic_objective}

Relevant recent conversation:
{recent_history}
"""
    return ask_llm(prompt)


def format_recent_history(transcript, last_n=6):
    recent = transcript[-last_n:]
    lines = []
    for turn in recent:
        lines.append(f"{turn['speaker']}: {turn['text']}")
    return "\n".join(lines)


def save_transcript(participant_id: str):
    if participant_id not in SESSIONS:
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = DATA_DIR / f"{participant_id}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(SESSIONS[participant_id]["transcript"], f, indent=2, ensure_ascii=False)
    return str(filename)


def add_turn(participant_id: str, speaker: str, turn_type: str, topic: str, text: str):
    session = SESSIONS[participant_id]
    session["turn_number"] += 1
    session["transcript"].append({
        "turn": session["turn_number"],
        "speaker": speaker,
        "type": turn_type,
        "topic": topic,
        "text": text
    })


@app.get("/")
def home():
    return {"status": "ok", "message": "Interview server is running"}


@app.post("/start")
def start_interview(request: StartInterviewRequest):
    participant_id = request.participant_id

    SESSIONS[participant_id] = {
        "participant_id": participant_id,
        "turn_number": 0,
        "current_topic_index": -1,
        "probe_count": 0,
        "stage": "opening",
        "interview_finished": False,
        "transcript": []
    }

    add_turn(
        participant_id=participant_id,
        speaker="AI",
        turn_type="opening",
        topic="opening",
        text=OPENING_QUESTION
    )

    return {
        "participant_id": participant_id,
        "question": OPENING_QUESTION,
        "question_type": "opening",
        "topic": "opening",
        "interview_finished": False
    }


@app.post("/next")
def next_question(request: NextQuestionRequest):
    participant_id = request.participant_id
    participant_response = request.participant_response.strip()

    if participant_id not in SESSIONS:
        return {"error": "participant_id not found. Start interview first."}

    session = SESSIONS[participant_id]

    if session["interview_finished"]:
        return {
            "question": None,
            "question_type": "finished",
            "topic": "finished",
            "interview_finished": True
        }

    current_topic_name = "opening" if session["current_topic_index"] == -1 else TOPICS[session["current_topic_index"]]["name"]

    add_turn(
        participant_id=participant_id,
        speaker="participant",
        turn_type="response",
        topic=current_topic_name,
        text=participant_response
    )

    recent_history = format_recent_history(session["transcript"])

    # opening -> first topic core question
    if session["stage"] == "opening":
        session["current_topic_index"] = 0
        session["probe_count"] = 0
        session["stage"] = "topic"

        topic = TOPICS[0]
        question = topic["core_question"]

        add_turn(
            participant_id=participant_id,
            speaker="AI",
            turn_type="core_question",
            topic=topic["name"],
            text=question
        )

        return {
            "question": question,
            "question_type": "core_question",
            "topic": topic["name"],
            "interview_finished": False
        }

    # inside topics
    if session["stage"] == "topic":
        topic = TOPICS[session["current_topic_index"]]

        # if probes left, ask probe
        if session["probe_count"] < MAX_PROBES_PER_TOPIC:
            question = generate_probe(
                current_topic=topic["name"],
                topic_objective=topic["objective"],
                last_response=participant_response,
                recent_history=recent_history
            )
            session["probe_count"] += 1

            add_turn(
                participant_id=participant_id,
                speaker="AI",
                turn_type="probe",
                topic=topic["name"],
                text=question
            )

            return {
                "question": question,
                "question_type": "probe",
                "topic": topic["name"],
                "interview_finished": False
            }

        # move to next topic
        session["current_topic_index"] += 1
        session["probe_count"] = 0

        # if there is another topic, ask transition into it
        if session["current_topic_index"] < len(TOPICS):
            previous_topic = topic["name"]
            next_topic = TOPICS[session["current_topic_index"]]

            question = generate_transition(
                previous_topic=previous_topic,
                next_topic=next_topic["name"],
                next_topic_objective=next_topic["objective"],
                recent_history=recent_history
            )

            add_turn(
                participant_id=participant_id,
                speaker="AI",
                turn_type="transition",
                topic=next_topic["name"],
                text=question
            )

            return {
                "question": question,
                "question_type": "transition",
                "topic": next_topic["name"],
                "interview_finished": False
            }

        # if no more topics, ask closing
        session["stage"] = "closing_main"

        add_turn(
            participant_id=participant_id,
            speaker="AI",
            turn_type="closing",
            topic="closing",
            text=CLOSING_QUESTION
        )

        return {
            "question": CLOSING_QUESTION,
            "question_type": "closing",
            "topic": "closing",
            "interview_finished": False
        }

    # after closing main -> optional closing
    if session["stage"] == "closing_main":
        session["stage"] = "closing_optional"

        add_turn(
            participant_id=participant_id,
            speaker="AI",
            turn_type="closing_optional",
            topic="closing",
            text=OPTIONAL_CLOSING_QUESTION
        )

        return {
            "question": OPTIONAL_CLOSING_QUESTION,
            "question_type": "closing_optional",
            "topic": "closing",
            "interview_finished": False
        }

    # after optional closing -> finish and save
    if session["stage"] == "closing_optional":
        session["interview_finished"] = True
        file_path = save_transcript(participant_id)

        return {
            "question": None,
            "question_type": "finished",
            "topic": "finished",
            "interview_finished": True,
            "transcript_file": file_path
        }

    return {"error": "Unexpected state"}


@app.get("/session/{participant_id}")
def get_session(participant_id: str):
    if participant_id not in SESSIONS:
        return {"error": "participant_id not found"}
    return SESSIONS[participant_id]


@app.post("/save/{participant_id}")
def manual_save(participant_id: str):
    if participant_id not in SESSIONS:
        return {"error": "participant_id not found"}
    file_path = save_transcript(participant_id)
    return {"saved_to": file_path}