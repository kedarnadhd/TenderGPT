def smart_search(db, query, aliases=None):

    docs_with_scores = db.similarity_search_with_score(
        query,
        k=10
    )

    reranked = []

    for doc, score in docs_with_scores:

        text = doc.page_content.lower()

        boost = 0

        # exact query
        if query.lower() in text:
            boost += 5

        # alias matching
        if aliases:
            for a in aliases:
                if a.lower() in text:
                    boost += 3

        final_score = score - (boost * 0.1)

        reranked.append((doc, final_score))

    reranked = sorted(reranked, key=lambda x: x[1])

    return [doc for doc, _ in reranked[:5]]