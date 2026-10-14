import tiktoken


encoding = tiktoken.get_encoding("cl100k_base")

text = "What is my savings account balance?"

token_ids = encoding.encode(text)

print("Original text:", text)
print("Token IDs:", token_ids)
print("Token count:", len(token_ids))

print("\nIndividual tokens:")

for token_id in token_ids:
    token_bytes = encoding.decode_single_token_bytes(token_id)
    print(token_id, "->", repr(token_bytes))
