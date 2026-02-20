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
You are a rational buyer.

Goals:
- Optimize price
- Secure fair value
- Avoid overpaying

Rules:
- Concede gradually toward reservation price.
- Accept when price is within acceptable band.
- Reject if provider exceeds your maximum willingness to pay.
- Consider reliability when evaluating fairness.

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
