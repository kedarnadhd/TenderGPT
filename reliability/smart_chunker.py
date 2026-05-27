from langchain_text_splitters import RecursiveCharacterTextSplitter


# --------------------------------
# TOC FILTER
# --------------------------------
def is_toc_chunk(text):

    text_lower = text.lower()

    toc_keywords = [
        "contents",
        "table of contents",
        "list of contents",
    ]
    # direct TOC keyword
    if any(k in text_lower for k in toc_keywords):
        return True

    # dotted TOC formatting
    dotted_lines = text.count("....")

    if dotted_lines > 15:
        return True

    return False


# --------------------------------
# SMART CHUNKER
# --------------------------------
def create_smart_chunks(pages):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 900,
        chunk_overlap = 120,
        separators= [
            "\n\n",
            "\n",
            ".",
            " ",
            ""
        ]
    )

    all_chunks = []
    metadata = []

    for page in pages:

        text = page["text"]

        if page["page"] % 25 == 0:
            print(f"Processed {page['page']} pages...")

        if is_toc_chunk(text):
            print("SKIPPED PAGE:", page["page"])
            continue

        chunks = splitter.split_text(text)

        for chunk in chunks:

            if not chunk.strip():
                continue

            # remove tiny noisy chunks
            if len(chunk.strip()) < 80:
                continue

            all_chunks.append(chunk)

            metadata.append({
                "page": page["page"]
            })

    return all_chunks, metadata