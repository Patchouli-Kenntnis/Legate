"""Legate CLI — interactive conversation menu."""

from config import GPT_MODEL, GPT_MODEL_CONTEXT_WINDOW, MAX_AGENT_ITERATIONS
from tools.update_planner import reset_planner, set_planner_state
from persist import AgentState, ConversationData, ConversationManager
from agent import primary_agent_loop


# ---------------------------------------------------------------------------
# CLI Menu
# ---------------------------------------------------------------------------

def cli_menu():
    while True:
        print("\n=== Legate ===")
        print("[N] New conversation")
        print("[L] List conversations")
        print("[Q] Quit")
        choice = input("> ").strip().lower()

        if choice == "n":
            _new_conversation()
        elif choice == "l":
            _list_conversations()
        elif choice == "q":
            print("Goodbye.")
            break
        else:
            print("Invalid choice.")


def _new_conversation():
    user_input = input("Enter your prompt: ").strip()
    if not user_input:
        print("Empty prompt, returning to menu.")
        return

    reset_planner()
    state = AgentState(
        max_token_budget=150_000,
        max_iter=MAX_AGENT_ITERATIONS,
        context_window=GPT_MODEL_CONTEXT_WINDOW[GPT_MODEL],
    )
    conv = ConversationManager.new(user_input, GPT_MODEL, state)
    print(f"Created conversation: {conv.id} — {conv.title}")
    primary_agent_loop(user_input, conv, MAX_AGENT_ITERATIONS)


def _list_conversations():
    convs = ConversationManager.list_all()
    if not convs:
        print("No saved conversations.")
        return

    print(f"\n{'#':<4} {'Title':<50} {'Updated':<20} {'Tokens':>8}")
    print("-" * 86)
    for idx, c in enumerate(convs, 1):
        updated = c.updated_at.strftime("%Y-%m-%d %H:%M")
        title = c.title[:48] + ".." if len(c.title) > 50 else c.title
        print(f"{idx:<4} {title:<50} {updated:<20} {c.state.used_tokens:>8}")

    print("\nEnter a number to continue, 'D <number>' to delete, or 'B' to go back.")
    action = input("> ").strip().lower()

    if action == "b" or action == "":
        return

    if action.startswith("d "):
        try:
            num = int(action.split()[1])
            if 1 <= num <= len(convs):
                target = convs[num - 1]
                confirm = input(f"Delete '{target.title}'? [y/N] ").strip().lower()
                if confirm == "y":
                    ConversationManager.delete(target.id)
                    print("Deleted.")
                else:
                    print("Cancelled.")
            else:
                print("Invalid number.")
        except (ValueError, IndexError):
            print("Invalid input.")
        return

    try:
        num = int(action)
        if 1 <= num <= len(convs):
            _continue_conversation(convs[num - 1])
        else:
            print("Invalid number.")
    except ValueError:
        print("Invalid input.")


def _continue_conversation(conv: ConversationData):
    print(f"\nContinuing conversation: {conv.title}")
    print(f"  Iterations so far: {conv.state.completed_iter}")
    print(f"  Tokens used: {conv.state.used_tokens}/{conv.state.max_token_budget}")

    # Restore planner state
    set_planner_state([s.model_dump() for s in conv.planner])

    user_input = input("Enter your next prompt: ").strip()
    if not user_input:
        print("Empty prompt, returning to menu.")
        return

    primary_agent_loop(user_input, conv, conv.state.max_iter)


if __name__ == "__main__":
    cli_menu()

