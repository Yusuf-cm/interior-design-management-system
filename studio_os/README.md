# Studio.OS development workspace

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

## Connected workspace
A local interface now covers today's actions, customers, inquiries, site visits,
assessments and internal quotation review. See [WORKSPACE_GUIDE.md](WORKSPACE_GUIDE.md)
for account setup, launch commands and the walkthrough. The tutorial frontend is not used.
No Node build is required to run the interface.

The workspace now also records manual customer decisions and supports project planning,
assigned work, blockers and progress. Handover and scope-change approval remain separate
future gates; no messaging, signing, purchasing or payment is automated.
