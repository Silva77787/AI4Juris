from ollama import chat

def split(text):

  stream = chat(
      model='gpt-oss:20b',
      messages=[{'role': 'user', 'content':f"Do documento que se segue, preciso que me dês as partes que apresentam o tipo de documento, e a decisão para esse tipo de documento, caso haja.  Mostra só as partes pedidas. Não escrevas nada que não está no texto. Só quero citações das partes relevantes. Documento:{text}"}],
      stream=True,
  )

  full_response = ""

  for chunk in stream:
    full_response += chunk.message.content

  return full_response
