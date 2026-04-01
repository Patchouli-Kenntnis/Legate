from . import run_bash, read_file, write_file, append_file, update_planner

_modules = [run_bash, read_file, write_file, append_file, update_planner]

TOOLS = [m.schema for m in _modules]
TOOL_HANDLERS = {m.schema["function"]["name"]: m.handler for m in _modules}
