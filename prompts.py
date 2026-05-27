FIELD_PROMPT = """
You are a procurement analyst.

Extract only the value for:

{field}

If not found, return "Not Found".

Tender Text:
{text}
"""