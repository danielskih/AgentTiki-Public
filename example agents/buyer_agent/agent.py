import time

import api
from fsm import FSM, load_state, save_state

POLL_INTERVAL_SECONDS = 5
TERMINAL_STATES = {"ACCEPTED", "FAILED"}


def ensure_auth(ctx, max_retries=3):
    actor_id = ctx.get("actor_id")
    api_key = ctx.get("api_key")

    if actor_id and api_key:
        api.configure_credentials(actor_id, api_key)
        return True

    print("[AUTH] No stored credentials. Registering buyer actor...")

    for attempt in range(1, max_retries + 1):
        try:
            response = api.register_actor()
        except Exception as exc:
            print(f"[AUTH] Register attempt {attempt} failed: {exc}")
            time.sleep(min(2 ** attempt, 10))
            continue

        actor_id = response.get("actor_id") if isinstance(response, dict) else None
        api_key = response.get("api_key") if isinstance(response, dict) else None

        if actor_id and api_key:
            ctx["actor_id"] = actor_id
            ctx["api_key"] = api_key
            save_state(ctx)
            api.configure_credentials(actor_id, api_key)
            print(f"[AUTH] Registered buyer actor: {actor_id}")
            return True

        print(f"[AUTH] Register attempt {attempt} returned invalid payload: {response}")
        time.sleep(min(2 ** attempt, 10))

    return False


def main():
    ctx = load_state()
    ctx.setdefault("state", "IDLE")

    if not ensure_auth(ctx):
        print("[AUTH] Unable to authenticate buyer agent. Exiting loop.")
        return

    save_state(ctx)

    while True:
        ctx = load_state()

        actor_id = ctx.get("actor_id")
        api_key = ctx.get("api_key")
        if actor_id and api_key:
            api.configure_credentials(actor_id, api_key)
        else:
            if not ensure_auth(ctx, max_retries=1):
                print("[AUTH] Authentication unavailable. Exiting loop.")
                break

        state = ctx.get("state", "IDLE")
        print(f"[LOOP] Current state: {state}")

        if state in TERMINAL_STATES:
            print(f"Agent finished with state: {state}\nExiting loop.")
            break

        handler = FSM.get(state)
        if not handler:
            raise RuntimeError(f"Unknown state: {state}")

        try:
            new_state = handler(ctx)
        except Exception as exc:
            print(f"[ERROR] state handler failed ({state}): {exc}")
            new_state = "FAILED"

        if new_state != state:
            print(f"[TRANSITION] {state} -> {new_state}")
            ctx["state"] = new_state

        save_state(ctx)
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
