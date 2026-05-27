import re

def validate_currency(value):

    pattern = r'[\₹₹]?\s?[\d,]+'

    if re.search(pattern, value):
        return True
    
    return False


def validate_date(value):

    pattern = r'\d{1,2}[./-]\d{1,2}[./-]\d{2,4}'

    if re.search(pattern, value):
        return True
    
    return False