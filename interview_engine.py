from openai import OpenAI
import json
from datetime import datetime

print("NEW VERSION IS RUNNING")

client = OpenAI()

OPENING_QUESTION = "How do you usually think about giving money to charity or helping other people financially?"
CLOSING_QUESTION = "Looking back at this conversation, what do you think is the main reason people sometimes sound more generous than they really are?"
OPTIONAL_CLOSING_QUESTION = "Is there anything important about how people talk about donation versus how they actually act that we have not discussed yet?"

TOPICS = [
    {
        "name": "General motives and hesitation around donation",
        "objective": "Understand what makes giving easier or harder.",
        "core_question": "What usually makes someone more willing, or less willing, to give money to charity?"
    },
    {
        "name": "Gap between what people say and what they do",
        "objective": "Explore why people may say they would donate more than they actually do.",
        "core_question": "In what kinds of situations do people say they would give more than they actually end up giving?"
    },
    {
        "name": "Social judgment and interviewer effects",
        "objective": "Explore whether talking to a human versus an AI changes what people say.",
        "core_question": "How, if at all, does talking to another person change the way people talk about generosity or donation?"
    },
    {
        "name": "Personal realistic donation choice",
        "objective": "Bring the participant to a concrete personal choice involving real money.",
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
- If the participant is speaking generally about "people," you may gently ask whether that also applies to them personally.
- Do not ask more than one question.
- Return only the question text.
"""

TOPIC_PROMPT = """
You are a neutral research interviewer conducting a semi-structured interview about charitable giving, donation decisions, and the gap between what people say and what they actually do.

Your task is to generate exactly one short transition question that moves the conversation from the previous topic to the next topic in a natural way.

Rules:
- Ask exactly one question.
- Keep it short, natural, and easy to answer aloud.
- Make it open-ended whenever possible.
- Be neutral and non-judgmental.
- Do not sound robotic or abrupt.
- Return only the question text.
"""

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

def save_transcript(transcript):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"transcript_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(transcript, f, indent=2, ensure_ascii=False)
    return filename

def main():
    transcript = []
    turn_number = 1

    print("\nAI:", OPENING_QUESTION)
    transcript.append({
        "turn": turn_number,
        "speaker": "AI",
        "type": "opening",
        "topic": "opening",
        "text": OPENING_QUESTION
    })
    turn_number += 1

    user_answer = input("You: ").strip()
    transcript.append({
        "turn": turn_number,
        "speaker": "participant",
        "type": "response",
        "topic": "opening",
        "text": user_answer
    })
    turn_number += 1

    for i, topic in enumerate(TOPICS):
        if i == 0:
            ai_question = topic["core_question"]
        else:
            ai_question = generate_transition(
                previous_topic=TOPICS[i - 1]["name"],
                next_topic=topic["name"],
                next_topic_objective=topic["objective"],
                recent_history=format_recent_history(transcript)
            )

        print("\nAI:", ai_question)
        transcript.append({
            "turn": turn_number,
            "speaker": "AI",
            "type": "core_question" if i == 0 else "transition",
            "topic": topic["name"],
            "text": ai_question
        })
        turn_number += 1

        user_answer = input("You: ").strip()
        transcript.append({
            "turn": turn_number,
            "speaker": "participant",
            "type": "response",
            "topic": topic["name"],
            "text": user_answer
        })
        turn_number += 1

        for probe_num in range(MAX_PROBES_PER_TOPIC):
            probe_question = generate_probe(
                current_topic=topic["name"],
                topic_objective=topic["objective"],
                last_response=user_answer,
                recent_history=format_recent_history(transcript)
            )

            print("\nAI:", probe_question)
            transcript.append({
                "turn": turn_number,
                "speaker": "AI",
                "type": "probe",
                "topic": topic["name"],
                "text": probe_question
            })
            turn_number += 1

            user_answer = input("You: ").strip()
            transcript.append({
                "turn": turn_number,
                "speaker": "participant",
                "type": "response",
                "topic": topic["name"],
                "text": user_answer
            })
            turn_number += 1

    print("\nAI:", CLOSING_QUESTION)
    transcript.append({
        "turn": turn_number,
        "speaker": "AI",
        "type": "closing",
        "topic": "closing",
        "text": CLOSING_QUESTION
    })
    turn_number += 1

    user_answer = input("You: ").strip()
    transcript.append({
        "turn": turn_number,
        "speaker": "participant",
        "type": "response",
        "topic": "closing",
        "text": user_answer
    })
    turn_number += 1

    print("\nAI:", OPTIONAL_CLOSING_QUESTION)
    transcript.append({
        "turn": turn_number,
        "speaker": "AI",
        "type": "closing_optional",
        "topic": "closing",
        "text": OPTIONAL_CLOSING_QUESTION
    })
    turn_number += 1

    user_answer = input("You: ").strip()
    transcript.append({
        "turn": turn_number,
        "speaker": "participant",
        "type": "response",
        "topic": "closing",
        "text": user_answer
    })

    filename = save_transcript(transcript)
    print(f"\nInterview finished. Transcript saved to: {filename}")

if __name__ == "__main__":
    main()