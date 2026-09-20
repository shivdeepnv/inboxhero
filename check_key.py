import argparse

import anthropic

import config


def mask(key):
    return f"{key[:10]}...{key[-4:]}"


def check(key):
    client = anthropic.Anthropic(api_key=key, max_retries=0)
    try:
        client.messages.create(model=config.MODEL, max_tokens=1, messages=[{"role": "user", "content": "hi"}])
        return "ACTIVE"
    except anthropic.AuthenticationError:
        return "INVALID (401): key rejected or revoked"
    except anthropic.PermissionDeniedError:
        return "NO PERMISSION (403)"
    except anthropic.RateLimitError:
        return "VALID, but rate limited right now (429)"
    except anthropic.NotFoundError:
        return f"VALID, but model {config.MODEL} not found (404)"
    except anthropic.BadRequestError as e:
        return f"VALID, but request rejected (often no credit): {e.message}"
    except anthropic.APIConnectionError:
        return "NETWORK ERROR: could not reach the API"
    except anthropic.APIStatusError as e:
        return f"ERROR {e.status_code}"


def main():
    parser = argparse.ArgumentParser(description="Check which Anthropic API keys are usable")
    parser.add_argument("--file", help="text file with one key per line (blank lines and # comments ignored)")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            keys = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    elif config.ANTHROPIC_API_KEY:
        keys = [config.ANTHROPIC_API_KEY]
    else:
        raise SystemExit("No key found. Set ANTHROPIC_API_KEY in .env or pass --file keys.txt")

    print(f"model used for the test: {config.MODEL}\n")
    for key in keys:
        print(f"{mask(key)}  {check(key)}")


if __name__ == "__main__":
    main()
