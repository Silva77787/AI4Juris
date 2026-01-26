# KNN

## Criar embeddings para documentos referentes às classes selecionadas

```bash
export DGSISCRAPER_DB_DSN="postgresql://dgsi:dgsi@localhost:5433/dgsi"

uv run python -m knn.index_embeddings_for_ids \
  --decision-json dgsi_scraper/decision_ids_by_class_ALLSOURCES.json \
  --batch-size 500
```