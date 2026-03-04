"""
Local test: find the best OpenAI model for CEO lookups (esp. 2024/2025).
Run with:
  conda run -n data-company-gcc python3 HelperFIles/test_openai_ceo.py
"""

import os
from openai import OpenAI

# ── API Key ────────────────────────────────────────────────────────────────────
os.environ["OPENAI_API_KEY"] = (
    "sk-proj-AguSkarzjgLCw9D-jCOwsxMkNzcXE5Niu82ZPv6z2rTQwK2F4gpI30RmyVWEndqkbZbaHrcAI9T3Blbk"
    "FJkEpotD_87OqBK7or2hZjWYxW5JGuhGZ80-KDPHacGGi4pDvDsLf5SlcZoo5ykJGUU-2Y7bjP8A"
)

client = OpenAI()

MODELS = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4o-2024-11-20",
    "gpt-4-turbo",
]

TEST_CASES = [
    # (company_name, ticker, year, expected)
    ("Johnson & Johnson", "JNJ",  2022, "Joaquin Duato"),
    ("Johnson & Johnson", "JNJ",  2023, "Joaquin Duato"),
    ("Johnson & Johnson", "JNJ",  2024, "Joaquin Duato"),
    ("Johnson & Johnson", "JNJ",  2025, "Joaquin Duato"),
    ("Apple Inc",         "AAPL", 2024, "Tim Cook"),
]

# ── Prompt variants to test ────────────────────────────────────────────────────
PROMPTS = {
    "strict_sec": (
        # Original prompt — too restrictive (training cutoff triggers "unknown")
        "You are an expert in SEC filings and US corporate history. "
        "When asked about a CEO, answer based on who was named as "
        "Chief Executive Officer in that company's SEC filings "
        "(10-K annual report or DEF 14A proxy statement) for that year. "
        "Respond only with the person's exact full name. "
        "No explanation, no titles, no punctuation.",
        lambda company, ticker, year: (
            f"Who was the CEO of {company} (ticker: {ticker}) "
            f"in {year} according to their SEC filings? "
            f'Reply with ONLY the full name (e.g. "John Smith"). '
            f"If you are not certain, reply with exactly: unknown"
        ),
    ),
    "best_guess": (
        # Production prompt — no SEC anchor, no unknown escape, "during year" framing
        "You are an expert in US public company leadership. "
        "When asked who the CEO of a company was for a given year, "
        "respond with the name of the person who served as CEO "
        "for most of that year, based on your training data. "
        "Answer from whatever point in the year your training data covers; "
        "you do not need data for December 31 to answer. "
        "Respond ONLY with the person's exact full name. "
        "No explanation, no titles, no punctuation. "
        "Only reply \"unknown\" if the company genuinely had no CEO "
        "or you have absolutely no information about that company.",
        lambda company, ticker, year: (
            f"Who was the CEO of {company} (ticker: {ticker}) "
            f"during fiscal year {year}? "
            f'Reply with ONLY the full name (e.g. "John Smith").'
        ),
    ),
}


def ask(model, system_prompt, user_fn, company, ticker, year):
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_fn(company, ticker, year)},
            ],
            max_tokens=60,
            temperature=0,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"ERROR: {e}"


# ── Run tests ──────────────────────────────────────────────────────────────────
header = f"{'Prompt':<22} {'Model':<24} {'Company':<22} {'Year':<6} {'Response':<35} OK?"
print(f"\n{header}")
print("-" * len(header))

for prompt_name, (sys_prompt, user_fn) in PROMPTS.items():
    for model in MODELS:
        for company, ticker, year, expected in TEST_CASES:
            raw = ask(model, sys_prompt, user_fn, company, ticker, year)
            ok = "✓" if expected.lower() in raw.lower() else "✗"
            print(
                f"{prompt_name:<22} {model:<24} {company:<22} {year:<6} {raw:<35} {ok}")
        print()
    print()
