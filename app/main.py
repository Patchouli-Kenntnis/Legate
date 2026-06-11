"""Legate CLI — interactive conversation menu."""

from config import GPT_MODEL, GPT_MODEL_CONTEXT_WINDOW
from settings import fmt_limit, get_settings, save_settings
from tools.update_planner import reset_planner, set_planner_notes, set_planner_state
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
        print("[S] Settings")
        print("[Q] Quit")
        choice = input("> ").strip().lower()

        if choice == "n":
            _new_conversation()
        elif choice == "l":
            _list_conversations()
        elif choice == "s":
            _settings_menu()
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
    settings = get_settings()
    state = AgentState(
        max_token_budget=settings.max_token_budget,
        max_iter=settings.max_iterations,
        context_window=GPT_MODEL_CONTEXT_WINDOW[GPT_MODEL],
    )
    conv = ConversationManager.new(user_input, GPT_MODEL, state)
    print(f"Created conversation: {conv.id} — {conv.title}")
    primary_agent_loop(user_input, conv, settings.max_iterations)


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


def _settings_menu():
    settings = get_settings()
    fields = [
        ("max_token_budget", "Token budget", True),
        ("max_context_tokens", "Max context size (tokens)", True),
        ("max_iterations", "Max iterations per run", True),
        ("keep_recent_blocks", "Recent blocks kept verbatim", False),
        ("spill_threshold", "Tool output spill threshold (chars)", False),
    ]
    while True:
        print("\n--- Settings ---")
        for idx, (name, label, allows_unlimited) in enumerate(fields, 1):
            value = fmt_limit(getattr(settings, name))
            suffix = "  (-1 = unlimited)" if allows_unlimited else ""
            print(f"[{idx}] {label:<36} {value}{suffix}")
        print("[B] Back")
        choice = input("> ").strip().lower()

        if choice in ("b", ""):
            return

        try:
            idx = int(choice)
            name, label, allows_unlimited = fields[idx - 1]
        except (ValueError, IndexError):
            print("Invalid choice.")
            continue

        raw = input(f"New value for '{label}': ").strip()
        try:
            value = int(raw)
        except ValueError:
            print("Invalid number.")
            continue

        if value == -1 and allows_unlimited:
            pass
        elif name == "keep_recent_blocks" and value < 1:
            print("Must be >= 1.")
            continue
        elif name == "spill_threshold" and value < 1000:
            print("Must be >= 1000.")
            continue
        elif value < 1:
            print("Must be a positive integer (or -1 for unlimited where allowed).")
            continue

        setattr(settings, name, value)
        save_settings()
        print(f"{label} set to {fmt_limit(value)}.")


def _continue_conversation(conv: ConversationData):
    print(f"\nContinuing conversation: {conv.title}")
    print(f"  Iterations so far: {conv.state.completed_iter}")
    print(f"  Tokens used: {conv.state.used_tokens}/{fmt_limit(conv.state.max_token_budget)}")

    # Restore planner state and notes
    set_planner_state([s.model_dump() for s in conv.planner])
    set_planner_notes(conv.notes)

    user_input = input("Enter your next prompt: ").strip()
    if not user_input:
        print("Empty prompt, returning to menu.")
        return

    primary_agent_loop(user_input, conv, conv.state.max_iter)


if __name__ == "__main__":
    cli_menu()

