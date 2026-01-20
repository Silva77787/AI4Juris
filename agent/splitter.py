from ollama import chat
from agent.decision_table import db_connect, insert_decision, delete_all_decisions


def split(text):

  prompt = 'Função do agente: extrair EXCLUSIVAMENTE e DE FORMA PASSIVA a parte DECISÓRIA/DISPOSITIVO de um documento jurídico em português, limitando-se a COPIAR texto existente. Regras absolutas e inegociáveis: NÃO reescrever, NÃO resumir, NÃO corrigir, NÃO traduzir, NÃO normalizar, NÃO remover palavras, NÃO acrescentar palavras, NÃO ajustar pontuação, NÃO alterar maiúsculas/minúsculas, NÃO alterar quebras de linha; a saída deve ser uma cópia literal do excerto original. Considera como decisão apenas o segmento que contém comandos decisórios expressos (ex.: “DECISÃO”, “DISPOSITIVO”, “III - Decisão”, “Pelo exposto”, “Nestes termos”, “Assim”, “Julgo”, “Decido”, “Determino”, “Defere-se”, “Indefere-se”, incluindo custas, penas, medidas, prazos, notificações, arquivamentos), excluindo sempre relatório, fundamentação, factos, enquadramento jurídico, doutrina, jurisprudência citada e decisões de outros tribunais apenas referidas. Delimitação obrigatória: o excerto começa no título decisório ou na primeira frase inequivocamente decisória e termina imediatamente antes de assinaturas, datas, locais, identificação do juiz/conselheiro ou rodapés administrativos. Em reclamações, despachos ou decisões processuais, a decisão pode não apreciar o mérito e ainda assim é decisão. Se houver várias decisões narradas, extrai APENAS a decisão proferida neste documento. Formato de saída crítico: devolver SOMENTE texto puro, sem JSON, sem Markdown, sem cabeçalhos, sem comentários, sem introduções, sem explicações; o conteúdo devolvido deve ser exatamente o que seria guardado num ficheiro .txt. Se não for possível identificar com segurança um bloco decisório, devolve saída vazia e absolutamente mais nada. Input: '+ text

  stream = chat(
      model='gpt-oss:20b',
      messages=[{'role': 'user', 'content': prompt}],
      stream=True,
  )

  full_response = ""

  for chunk in stream:
    full_response += chunk.message.content

  print(full_response)

  return full_response

def main():
    conn = db_connect()
    print("Connected to DB", flush=True)

    delete_all_decisions(conn)

    cur = conn.cursor()
    cur.execute("SELECT text_plain, id FROM dgsi_documents;")

    for text_plain, id in cur:
        res = split(text_plain)
        insert_decision(conn, document_id=id, decision_text=res)
        print(f"Inserted decision for document id {id}", flush=True)

    cur.close()
    conn.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        print("CRASH:", repr(e), flush=True)
        traceback.print_exc()
        raise

