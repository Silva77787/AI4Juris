from agent.decision_table import db_connect, insert_decision, delete_all_decisions
from dotenv import load_dotenv
import os
import json
import ollama


def split(text):
    load_dotenv()

    prompt = 'Função do agente: extrair EXCLUSIVAMENTE e DE FORMA PASSIVA a parte DECISÓRIA/DISPOSITIVO de um documento jurídico em português, limitando-se a COPIAR texto existente. Regras absolutas e inegociáveis: NÃO reescrever, NÃO resumir, NÃO corrigir, NÃO traduzir, NÃO normalizar, NÃO remover palavras, NÃO acrescentar palavras, NÃO ajustar pontuação, NÃO alterar maiúsculas/minúsculas, NÃO alterar quebras de linha; a saída deve ser uma cópia literal do excerto original. Considera como decisão apenas o segmento que contém comandos decisórios expressos (ex.: "DECISÃO", "DISPOSITIVO", "III - Decisão", "Pelo exposto", "Nestes termos", "Assim", "Julgo", "Decido", "Determino", "Defere-se", "Indefere-se", incluindo custas, penas, medidas, prazos, notificações, arquivamentos), excluindo sempre relatório, fundamentação, factos, enquadramento jurídico, doutrina, jurisprudência citada e decisões de outros tribunais apenas referidas. Delimitação obrigatória: o excerto começa no título decisório ou na primeira frase inequivocamente decisória e termina imediatamente antes de assinaturas, datas, locais, identificação do juiz/conselheiro ou rodapés administrativos. Em reclamações, despachos ou decisões processuais, a decisão pode não apreciar o mérito e ainda assim é decisão. Se houver várias decisões narradas, extrai APENAS a decisão proferida neste documento. Formato de saída crítico: devolver SOMENTE texto puro, sem JSON, sem Markdown, sem cabeçalhos, sem comentários, sem introduções, sem explicações; o conteúdo devolvido deve ser exatamente o que seria guardado num ficheiro .txt. Se não for possível identificar com segurança um bloco decisório, devolve saída vazia e absolutamente mais nada. Input: '+ text

    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
    response = ollama.chat(model=model_name, messages=[{"role": "user", "content": prompt}])
    decision_text = response['message']['content']
    print(decision_text)
    return decision_text

def main():
    conn = db_connect()
    print("Connected to DB", flush=True)

    with open("agent/decision_ids_by_class_ALLSOURCES.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    rows = []
    for cls, items in data["ids_by_class"].items():
        for item in items:
            rows.append({
                "deci": cls,
                "id": int(item["id"]),
                "source": item.get("source"),
                "variant": item.get("variant"),
            })

    sql = """
        WITH input AS (
        SELECT *
        FROM jsonb_to_recordset(%s::jsonb)
            AS x(deci text, id bigint, source text, variant text)
        )
        SELECT
        input.deci,
        input.id,
        d.text_plain,
        input.source,
        input.variant,
        (d.id IS NOT NULL) AS exists_in_db
        FROM input
        LEFT JOIN dgsi_documents d
        ON d.id = input.id
        ORDER BY input.deci, input.id;
    """

    delete_all_decisions(conn)

    cur = conn.cursor()
    cur.execute(sql, (json.dumps(rows),))

    for deci, id, text_plain, source, variant, exists_in_db in cur:
        res = split(text_plain)
        insert_decision(conn, document_id=id, decision_text=res, final_decision=deci)
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
