uv pip install -e .

PROJECT=$(gcloud config get-value project)
export GOOGLE_CLOUD_PROJECT=$PROJECT

python -m integrator.main
