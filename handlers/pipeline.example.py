"""
handlers/pipeline.py  -  Example handler module.

Each function receives the full payload dict:
  {
    "continue": True,
    "action": "process",
    "task": "export_csv"
  }
"""

def run_pipeline(payload: dict):
    """Called when action='process' for subject 'Data Pipeline'."""
    # Add your pipeline logic here
    # e.g., kick off a data processing job, call an API, etc.

def export_to_csv(payload: dict):
    """Called when task='export_csv' for subject 'Data Pipeline'."""
    # Add your CSV export logic here
