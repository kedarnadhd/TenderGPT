# def create_chunks(pages, chunk_size=2000):
#     chunks = []

#     for page in pages:
#         text = page["text"]

#         for i in range(0, len(text), chunk_size):
#             chunk = text[i:i+chunk_size]
#             chunks.append(chunk)

#     return chunks