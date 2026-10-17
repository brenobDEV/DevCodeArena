from django.db.migrations import AddField, AlterField
from django.db.migrations.recorder import MigrationRecorder


def _column_exists(schema_editor, model, field_name):
    table = model._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        tables = schema_editor.connection.introspection.table_names(cursor)
        if table not in tables:
            return False
        columns = schema_editor.connection.introspection.get_table_description(cursor, table)
    column_name = model._meta.get_field(field_name).column
    return any(column.name == column_name for column in columns)


def _peer_migration_applied(schema_editor, app_label, migration_name):
    applied = MigrationRecorder(schema_editor.connection).applied_migrations()
    return (app_label, migration_name) in applied


class SharedAddField(AddField):
    def __init__(self, model_name, name, field, preserve_default=True, *, peer_migration):
        super().__init__(model_name, name, field, preserve_default)
        self.peer_migration = peer_migration

    def deconstruct(self):
        name, args, kwargs = super().deconstruct()
        kwargs["peer_migration"] = self.peer_migration
        return name, args, kwargs

    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if _column_exists(schema_editor, model, self.name):
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)
        if _peer_migration_applied(schema_editor, app_label, self.peer_migration):
            return
        if not _column_exists(schema_editor, model, self.name):
            return
        super().database_backwards(app_label, schema_editor, from_state, to_state)


class SharedAlterField(AlterField):
    def __init__(self, model_name, name, field, preserve_default=True, *, peer_migration):
        super().__init__(model_name, name, field, preserve_default)
        self.peer_migration = peer_migration

    def deconstruct(self):
        name, args, kwargs = super().deconstruct()
        kwargs["peer_migration"] = self.peer_migration
        return name, args, kwargs

    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if _peer_migration_applied(schema_editor, app_label, self.peer_migration):
            return
        super().database_backwards(app_label, schema_editor, from_state, to_state)
