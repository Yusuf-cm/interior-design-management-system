from . import test_execution_migration


class ScopeMigrationTests(test_execution_migration.ExecutionMigrationTests):
    """Exercise upgrade, rollback and re-upgrade with pre-existing financial records."""
    old = [('operations', '0006_alter_quote_status_project_quoteevent_workitem_and_more')]
    new = [('operations', '0007_scopechange')]
