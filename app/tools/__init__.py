from . import run_bash, read_file, write_file, append_file, update_planner, web_search, create_subagent

subagent_modules = [run_bash, read_file, write_file, append_file, web_search]
primary_agent_module = [create_subagent, update_planner]

SUBAGENT_TOOLS = [m.schema for m in subagent_modules]
SUBAGENT_TOOL_HANDLERS = {m.schema["function"]["name"]: m.handler for m in subagent_modules}
PRIMARY_TOOLS = [m.schema for m in primary_agent_module]
PRIMARY_TOOL_HANDLERS = {m.schema["function"]["name"]: m.handler for m in primary_agent_module}