"""Terminal REPL for trying the coach: python -m coach"""

from coach.agent import chat


def main():
    messages = []
    print("Finance coach. Ctrl+D to quit.")
    while True:
        try:
            user_input = input("\nyou> ").strip()
        except EOFError:
            break
        if not user_input:
            continue
        messages.append({"role": "user", "content": user_input})
        print(f"\ncoach> {chat(messages)}")


if __name__ == "__main__":
    main()
