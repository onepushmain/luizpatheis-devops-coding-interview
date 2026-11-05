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

## CI/CD

GitHub Actions builds, tests, and deploys the API to GKE with Helm. A manual workflow handles rollback.
See [docs/ci-cd.md](docs/ci-cd.md) for the flow, the secrets and variables, and the design decisions.
