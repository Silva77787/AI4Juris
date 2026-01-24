# DGSI Scraper — AI4Juris

Recolha jurisprudência do portal DGSI (Direção-Geral da Política de Justiça) e armazenamento dos documentos numa base de dados PostgreSQL, usando Docker.

## INSTALAÇÃO DO AMBIENTE PYTHON

A partir da raiz do projeto (AI4Juris):

```bash
uv sync
```

## INICIAR POSTGRESQL COM DOCKER

A partir da raiz do projeto (AI4Juris):

```bash
docker compose up -d
docker compose ps
docker logs -n 30 dgsi_postgres
```

A base de dados fica acessível em:  
- host: localhost  
- porta: 5433  
- database: dgsi  
- user: dgsi  
- password: dgsi  

## CONFIGURAR LIGAÇÃO À BASE DE DADOS

Exportar a variável de ambiente usada pelo scraper:

```bash
export DGSISCRAPER_DB_DSN="postgresql://dgsi:dgsi@localhost:5433/dgsi"
```

O schema é criado automaticamente na primeira execução.

## EXECUTAR O SCRAPER (CONFIGURAÇÃO FINAL)

Distribuição equilibrada (~10.000 documentos):

```bash
uv run python scrape.py --source-limits "dgsi_stj=1700,dgsi_sta=1700,dgsi_trp=1100,dgsi_trl=1100,dgsi_tc_ate_1998=500,dgsi_tca_sul=650,dgsi_tca_norte=650,dgsi_tre=550,dgsi_trc=550,dgsi_trg=700,dgsi_jpaz=450,dgsi_clausulas_abusivas=250,dgsi_jcon=300"
```

Características:  
- UPSERT por URL (não duplica documentos)  
- Pode ser interrompido e retomado  
- Limites contam apenas documentos novos  

## VERIFICAR DADOS NA BASE DE DADOS

```bash
docker exec -it dgsi_postgres psql -U dgsi -d dgsi
```

Dentro do psql:

```sql
\dt
SELECT COUNT(*) FROM dgsi_documents;
SELECT source, COUNT(*) FROM dgsi_documents GROUP BY source ORDER BY COUNT(*) DESC;
```

## CRIAR DUMP (BACKUP) DA BASE DE DADOS

Guardar o dump dentro da pasta dgsi-scraper:

```bash
cd dgsi-scraper
docker exec dgsi_postgres pg_dump -U dgsi -d dgsi --format=custom --no-owner --no-privileges > dgsi_dump_$(date +%Y%m%d_%H%M).dump
```

## RESTAURAR A BASE DE DADOS (NOUTRO PC)

A partir da raiz do projeto (AI4Juris): 

```bash
docker compose up -d
cd dgsi-scraper
docker exec -i dgsi_postgres pg_restore -U dgsi -d dgsi --clean --if-exists < dgsi_dump_YYYYMMDD_HHMM.dump
```
(substituir pelo nome correto do dump)

Verificação:

```bash
docker exec -it dgsi_postgres psql -U dgsi -d dgsi -c "SELECT COUNT(*) FROM dgsi_documents;"
```

## LIMPAR A BASE DE DADOS (SE NECESSÁRIO)

Apagar apenas os dados:

```bash
docker exec -it dgsi_postgres psql -U dgsi -d dgsi -c "TRUNCATE TABLE dgsi_documents RESTART IDENTITY;"
```

OU apagar tudo (dados + volume):

```bash
docker compose down -v
docker compose up -d
```

## SAMPLES DE TEXTO (OPCIONAL)

Por defeito o scraper NÃO guarda samples em disco.

Para ativar:

```bash
python scrape.py --save-samples-dir samples_txt
```

## EXTRAIR E LIMPAR CLASSES DE DECISÃO

### Ranking bruto das decisões

```bash
export DGSISCRAPER_DB_DSN="postgresql://dgsi:dgsi@localhost:5433/dgsi"

uv run python dgsi_scraper/decision_rank.py \
  --csv-out dgsi_scraper/output/decision_ranking.csv \
  --json-out dgsi_scraper/output/decision_ranking.json \
  --show-top 9999
```

### Limpeza das classes de decisão

O ranking bruto contém muito ruído (datas, símbolos, frases incompletas, texto em minúsculas, etc.).
Este passo aplica uma limpeza baseada em heurísticas simples (CAPS, tamanho, etc.).

```bash
uv run python dgsi_scraper/decision_clean.py \
  --input dgsi_scraper/output/decision_ranking.csv \
  --csv-out dgsi_scraper/output/decision_classes_clean.csv \
  --json-out dgsi_scraper/output/decision_classes_clean.json
```

## NOTAS FINAIS

- text_plain contém o texto integral completo  
- text_gzip é a versão comprimida  
- O scraper é idempotente e seguro para reexecuções