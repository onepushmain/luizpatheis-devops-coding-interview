# devops-coding-exercise

## Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### API

To run the API development server, you can run:

```bash
cd api
python -m fastapi dev --app app --port 8000
```

For more details about the API server, check [api/README.md](api/README.md)
