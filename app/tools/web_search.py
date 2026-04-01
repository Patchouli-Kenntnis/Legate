from ddgs import DDGS

DEBUG_PRINT = True
DEFAULT_MAX_RESULTS = 5


def web_search(query: str, max_results: int = DEFAULT_MAX_RESULTS) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        if DEBUG_PRINT:
            print(f"[web_search] Query: {query!r} → {len(results)} results")
        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.get('title', 'No title')}")
            lines.append(f"   URL: {r.get('href', '')}")
            lines.append(f"   {r.get('body', '')}")
        return "\n".join(lines)
    except Exception as e:
        print(f"Error during web search: {e}")
        return f"Error occurred: {e}"


schema = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Searches the internet using DuckDuckGo and returns the top results, including titles, URLs, and snippets. Use this to look up current information, facts, documentation, or anything that requires internet access.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up, e.g. 'Python asyncio tutorial'",
                },
                "max_results": {
                    "type": "integer",
                    "description": f"Maximum number of results to return (default: {DEFAULT_MAX_RESULTS})",
                },
            },
            "required": ["query"],
        },
    }
}

handler = lambda args: web_search(args["query"], args.get("max_results", DEFAULT_MAX_RESULTS))
