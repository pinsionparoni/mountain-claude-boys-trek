"""Terminal REPL for trying the coach: python -m coach [CUSTOMER_ID]"""

import sys

from coach.agent import COACH_MODEL, chat


def main():
    customer_id = sys.argv[1] if len(sys.argv) > 1 else "CUST00001"
    messages = []
    print(f"Finance coach ({COACH_MODEL}) for {customer_id}. Ctrl+D to quit.")
    while True:
        try:
            user_input = input("\nyou> ").strip()
        except EOFError:
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        print(f"\ncoach> {chat(messages, customer_id)}")


if __name__ == "__main__":
    main()
