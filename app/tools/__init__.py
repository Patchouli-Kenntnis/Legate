from . import run_bash, read_file, write_file

_modules = [run_bash, read_file, write_file]

TOOLS = [m.schema for m in _modules]
TOOL_HANDLERS = {m.schema["function"]["name"]: m.handler for m in _modules}
