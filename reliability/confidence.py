

def calculate_confidence(method, value):

    if value == "Not Found":
        return 0.0
    
    if method == "regex":
        return 0.95
    
    if method == "semantic":
        return 0.80
    
    if method == "llm": 
        return 0.65
    
    return 0.5