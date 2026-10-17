# Studio.OS clean backend

Independent implementation. Does not import tutorial models, migrations or database. Django/DRF chosen for the application layer; domain policies are pure Python and tested independently.

Run domain tests: `python -m unittest discover -s studio_os/tests -v` from repository root.

No production integration, payments, legal commitments or outbound messages.


## Local verification
From the repository root:

```sh
python -m pip install -r studio_os/requirements.txt
python -m studio_os.manage check
python -m studio_os.manage makemigrations --check --dry-run
python -m studio_os.manage test studio_os.operations -v 2
python -m unittest discover -s studio_os/tests -v
```

Only the isolated SQLite database is configured. See
[API_WORKFLOW.md](API_WORKFLOW.md) for the current API contract.
