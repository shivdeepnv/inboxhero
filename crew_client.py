import time

import config
import tracelog as trace
from crewai import Agent, Crew, LLM, Task


class LLMFailure(Exception):
    pass


def make_agent(role, goal, backstory, max_tokens=300):
    llm = LLM(model=f"anthropic/{config.MODEL}", api_key=config.require_api_key(),
              temperature=0, max_tokens=max_tokens)
    return Agent(role=role, goal=goal, backstory=backstory, llm=llm, allow_delegation=False, verbose=False)


def ask(agent, description, expected_output, parse, cap, label):
    """Run one task and return parse(raw). parse raises ValueError on bad output, which is retried."""
    last_error = None
    for attempt in range(config.MAX_RETRIES):
        try:
            task = Task(description=description, expected_output=expected_output, agent=agent)
            result = Crew(agents=[agent], tasks=[task], verbose=False).kickoff()
            return parse(str(getattr(result, "raw", result)))
        except Exception as e:
            if "AuthenticationError" in str(e) or "authentication_error" in str(e):
                raise SystemExit("Anthropic rejected the API key (401). Run `python check_key.py` and fix .env.")
            last_error = e
            trace.log(cap, "llm_error", message_id=label, for_message=label, attempt=attempt + 1, error=str(e)[:200])
            if attempt < config.MAX_RETRIES - 1:
                rate_limited = "429" in str(e) or "rate" in str(e).lower()
                time.sleep(max(15, config.REQUEST_DELAY_S) if rate_limited else config.REQUEST_DELAY_S * 2 ** attempt)
    raise LLMFailure(f"{config.MAX_RETRIES} attempts failed: {str(last_error)[:80]}")
