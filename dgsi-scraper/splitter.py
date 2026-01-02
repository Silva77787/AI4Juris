from ollama import chat
from ollama import Client

filename = 'test.txt'
file = open(filename, encoding="utf8")
data = file.read()

client = Client(
  host='http://localhost:11434',
)

prompt = (
    "Do documento que se segue, preciso que me dês as partes que apresentam o tipo de documento, e a decisão para esse tipo de documento. Documento: "
    f"{data}"
)

stream = chat(
    model='gpt-oss:20b',
    messages=[{'role': 'user', 'content':f"Do documento que se segue, preciso que me dês as partes que apresentam o tipo de documento, e a decisão para esse tipo de documento, caso haja.  Mostra só as partes pedidas. Não escrevas nada que não está no texto. Só quero citações das partes relevantes. Documento:{data}"}],
    stream=True,
)

full_response = ""

for chunk in stream:
  full_response += chunk.message.content

print("\n\n--- RESPONSE STORED IN VARIABLE ---")
print(full_response)