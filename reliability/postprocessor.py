

def verify_answer_in_context(answer, context):

    if answer.lower() in context.lower():
        return answer
    
    return "Not Found"