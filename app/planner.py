class planner:
    """
    Planner is an agent tool that can be used to plan out a series of steps to accomplish a task. It can be used to break down a complex task into smaller, more manageable steps, and to create a plan for how to accomplish the task.
    """
    def __init__(self):
        # todolist is a list of steps that the planner has generated for the task. Each step is a tuple of a string that describes the step, and an integer that indicates the step's status: 0, incomplete; 1, complete; -1, failed.
        self.todolist = []
        
    def add_steps(self, steps_text: str):
        # The LLM in planning mode will generate a list of steps in the form of a numbered list separated by newlines, e.g. "1. Step one\n2. Step two\n3. Step three". This function takes that text and adds each step to the todolist as an incomplete step.
        steps = steps_text.split("\n")
        for step in steps:
            self.todolist.append((step, 0))
    
    def stringify(self) -> str:
        # This helper function returns a string representation of the planner's current todolist, with each step and its status. For example, if the todolist is [("Step one", 0), ("Step two", 1), ("Step three", -1)], the string representation would be:
        # "1. Step one [incomplete]\n2. Step two [complete]\n3. Step three [failed]"
        result = ""
        for i, (step, status) in enumerate(self.todolist):
            status_str = "incomplete" if status == 0 else "complete" if status == 1 else "failed"
            result += f"{i+1}. {step} [{status_str}]\n"
        return result.strip()

    def update_state(self, step_index: int, new_status: int):
        # This function updates the status of a step in the todolist. It takes the index of the step to update (0-based) and the new status (0, 1, or -1). It updates the status of the specified step in the todolist.
        if 0 <= step_index < len(self.todolist):
            step, _ = self.todolist[step_index]
            self.todolist[step_index] = (step, new_status)