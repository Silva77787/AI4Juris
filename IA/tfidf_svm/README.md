# TFIDF_SVM

## Treinar e Guardar Modelos

Dentro da pasta IA:

```bash
export DGSISCRAPER_DB_DSN="postgresql://dgsi:dgsi@localhost:5433/dgsi"

uv run python -m tfidf_svm.train_tfidf_svm \
  --ids-json dgsi_scraper/decision_ids_by_class_ALLSOURCES.json \
  --table public.dgsi_documents \
  --text-col text_plain \
  --id-col id \
  --min-class-count 100 \
  --cv-folds 5 \
  --ngram-max 3 \
  --min-df 5 \
  --max-df 0.90 \
  --C 1.0 \
  --class-weight balanced \
  --out-dir models \
  --prefix tfidf_svm_min100_cv5 \
  --save-report
```

## Testar .txt sem decisão nos modelos treinados

Dentro da pasta IA:

```bash
uv run python -m tfidf_svm.tfidf_svm_predict_from_file \           
  --file tfidf_svm/test_NEGADA.txt \
  --artifacts-dir models \
  --prefix tfidf_svm_min100_cv5
```