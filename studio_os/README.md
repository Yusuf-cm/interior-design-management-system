# Studio.OS clean backend

Independent implementation. Does not import tutorial models, migrations or database. Django/DRF chosen for the application layer; domain policies are pure Python and tested independently.

Run domain tests: `python -m unittest discover -s studio_os/tests -v` from repository root.

No production integration, payments, legal commitments or outbound messages.
