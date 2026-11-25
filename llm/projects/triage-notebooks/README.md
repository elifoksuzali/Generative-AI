# triage-notebooks

Jupyter notebooks that build the dataset for a **customer-message triage** model:
the goal is to automatically route/label incoming customer messages (e.g. by
department or request type) so support teams can prioritize them. The notebooks
cover the full data path — extract → clean → assemble → label — and feed the
`finetune_unsloth.py` fine-tuning step that produces a quantized `triage-gguf`
model.

## Pipeline

```
MySQL (customer messages / tickets)
        │   Excrat.ipynb
        ▼
raw message dump
        │   Cleaner.ipynb   (strip e-mails, HTML, signatures, greetings, names)
        ▼
cleaned text
        │   Genel.ipynb / t1.ipynb / t2.ipynb   (filter by responder, split, label)
        ▼
labeled train/eval dataset  (DatasetTrain.ipynb)
        │
        ▼
fine-tune with Unsloth  →  triage-gguf model   (finetune_unsloth.py, outside this folder)
```

## Notebooks

| Notebook | Purpose |
|----------|---------|
| `Excrat.ipynb` | Extract raw messages/tickets from the MySQL database |
| `Cleaner.ipynb` | Clean & normalize text — remove e-mail addresses, HTML, signatures, greeting phrases and agent names |
| `Genel.ipynb` | General dataset assembly and filtering |
| `DatasetTrain.ipynb` | Build the labeled train/eval dataset and the label map (message → department) |
| `t1.ipynb`, `t2.ipynb` | Per-responder subsets and labeling experiments |

## Requirements

- Python 3.10+, Jupyter
- `pandas`, `mysql-connector-python`
- Fine-tuning (separate script): `unsloth`, `transformers`, a CUDA GPU

```bash
pip install jupyter pandas mysql-connector-python
```

## Configuration

Database credentials must be supplied via the shared `.env` (see the repo root)
rather than hardcoded in cells. Example:

```env
DB_HOST=...  DB_USER=...  DB_PASSWORD=...  DB_NAME=...
```

## Privacy notes

- **Notebook outputs were cleared** in this copy, because saved cell outputs
  embedded real customer messages and personal data. Re-run the notebooks against
  your own database to regenerate them.
- **DB credentials were replaced** with placeholders.
- **Employee names were anonymized** (e.g. real agent names → `Agent One`,
  `Manager One`, `agent1`…). If you add new names while working, anonymize them
  before committing.

## Running

Open the notebooks in order (`Excrat` → `Cleaner` → `Genel`/`t1`/`t2` →
`DatasetTrain`) in Jupyter or VS Code, after setting your `.env`.
