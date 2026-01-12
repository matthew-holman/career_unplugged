from app.workers import job_analyser


class DummySession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


class DummyHandler:
    def __init__(self) -> None:
        self.saved = 0

    def save_all(self, jobs) -> None:
        self.saved += len(jobs)


def test_job_analyser_flushes_batch() -> None:
    session = DummySession()
    handler = DummyHandler()
    pending = [object()]

    remaining = job_analyser._flush_pending_jobs(
        session,
        handler,
        pending,
        batch_size=2,
        force=True,
    )

    assert remaining == []
    assert session.commits == 1
    assert handler.saved == 1
