"""Terminal REPL for trying the coach: python -m coach --customer CUST00001"""

import argparse
import os

from coach.agent import chat


def main():
    parser = argparse.ArgumentParser(description="Chat with the finance coach in the terminal.")
    parser.add_argument(
        "--customer",
        default=os.getenv("COACH_CUSTOMER_ID"),
        help="ID of the customer whose data the coach may read (or set COACH_CUSTOMER_ID)",
    )
    customer_id = parser.parse_args().customer

    messages = []
    if customer_id:
        print(f"Finance coach for {customer_id}. Ctrl+D to quit.")
    else:
        print("Finance coach (no customer set, so it cannot read any transactions). Ctrl+D to quit.")
    while True:
        try:
            user_input = input("\nyou> ").strip()
        except EOFError:
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        print(f"\ncoach> {chat(messages, customer_id=customer_id)}")


if __name__ == "__main__":
    main()
