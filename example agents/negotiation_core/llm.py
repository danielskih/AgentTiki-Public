import os

import openai


OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def ask(prompt: str) -> str:
    response = openai.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    return (response.choices[0].message.content or "").strip()
