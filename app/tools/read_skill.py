import tomllib
import os

DEBUG_PRINT = True

SKILLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills")
CATALOG_PATH = os.path.join(SKILLS_DIR, "SKILLS.toml")


def read_skill(skill_name: str) -> str:
    """
    Look up a skill by name in the SKILLS.toml catalog and return its full description.
    """
    try:
        with open(CATALOG_PATH, "rb") as f:
            catalog = tomllib.load(f)
    except Exception as e:
        return f"Error reading skill catalog: {e}"

    entries = catalog.get("skills", [])
    match = None
    for entry in entries:
        if entry["name"].lower() == skill_name.lower():
            match = entry
            break

    if not match:
        available = ", ".join(e["name"] for e in entries)
        return f"Skill '{skill_name}' not found. Available skills: {available}"

    skill_path = os.path.join(os.path.dirname(CATALOG_PATH), "..", match["path"].removeprefix("app/skills/"))
    skill_path = os.path.normpath(skill_path)

    # Resolve relative to the project root as the catalog stores paths like "app/skills/..."
    if not os.path.isfile(skill_path):
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        skill_path = os.path.normpath(os.path.join(project_root, match["path"]))

    try:
        with open(skill_path, "rb") as f:
            skill_data = tomllib.load(f)
    except Exception as e:
        return f"Error reading skill file at {skill_path}: {e}"

    name = skill_data.get("name", skill_name)
    intro = skill_data.get("intro", "")
    description = skill_data.get("description", "")

    if DEBUG_PRINT:
        print(f"[read_skill] Loaded skill: {name}")

    return f"Skill: {name}\nIntro: {intro}\n\n{description}"


schema = {
    "type": "function",
    "function": {
        "name": "read_skill",
        "description": (
            "Reads the full description of a skill by name. Skills are predefined knowledge modules "
            "that provide detailed guidelines and best practices for specific domains (e.g., 'Python Debugging', "
            "'Web Research'). Use this tool when you need domain-specific guidance to complete a task well. "
            "Call with the exact skill name from the catalog."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "skill_name": {
                    "type": "string",
                    "description": "The name of the skill to read, e.g. 'Python Debugging' or 'Web Research'.",
                },
            },
            "required": ["skill_name"],
        },
    }
}

handler = lambda args: read_skill(args["skill_name"])
