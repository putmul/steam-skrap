from database.database import Database


class FakeCursor:
    def __init__(self):
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append((query, params))

    def fetchone(self):
        return None

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FakeConnection:
    def __init__(self):
        self.cursor_object = FakeCursor()
        self.committed = False

    def cursor(self):
        return self.cursor_object

    def commit(self):
        self.committed = True

    def rollback(self):
        pass

    def close(self):
        pass


def test_database_can_check_blocked_app_without_real_mariadb():
    connection = FakeConnection()
    database = Database(connection=connection)
    assert database.is_blocked(123) is False
    assert connection.cursor_object.queries
