

def attach_source_page(docs):

    if not docs:
        return None
    
    return docs[0].metadata.get("page")