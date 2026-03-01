import os

import openai
from openai import OpenAI

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
client = OpenAI()


def ask(prompt: str) -> str:
    response = openai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
    )

    return (response.choices[0].message.content or "").strip()

def generate_output(contract, input_dir="./input", output_dir="./output"):
    prompt = f"""
You are a professional service provider.

Goals:
- Protect margin
- Maintain reliability reputation
- Accept only economically rational deals
- Avoid price collapse

Rules:
- Never accept offers below your reservation price.
- Gradually concede when close to agreement.
- Reject clearly exploitative offers.
- If within 3% of your acceptable range, accept.

Respond ONLY with JSON:
{
  "action": "ACCEPT" | "PROPOSE" | "REJECT",
  "proposal": { ... }  // only if PROPOSE
}
"""

    response = client.responses.create(
        model="gpt-4.1",
        input=prompt
    )

    return response.output_text
