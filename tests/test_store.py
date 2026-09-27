"""SQLite tasks/sessions plus JSON backup round-trip."""
from pomotux.store import Store


def test_task_crud(tmp_path):
    s = Store(tmp_path / "t.db")
    t = s.add_task("write tests")
    assert t.title == "write tests" and not t.done
    assert len(s.list_tasks()) == 1
    s.toggle_task(t.id)
    assert s.list_tasks() == []  # done tasks hidden by default
    assert len(s.list_tasks(include_done=True)) == 1
    s.delete_task(t.id)
    assert s.list_tasks(include_done=True) == []


def test_sessions_and_stats(tmp_path):
    s = Store(tmp_path / "t.db")
    t = s.add_task("focus work")
    s.log_session("focus", 1500, t.id)
    s.bump_pomodoros(t.id)
    assert s.today_focus() == 1
    assert s.streak_days() == 1
    assert len(s.focus_last_7_days()) == 7
    assert sum(s.focus_last_7_days()) == 1
    assert s.get_task(t.id).pomodoros == 1


def test_export_import_roundtrip(tmp_path):
    s = Store(tmp_path / "a.db")
    t = s.add_task("keep me")
    s.log_session("focus", 1500, t.id)
    backup = tmp_path / "b.json"
    s.export_json(backup)
    s2 = Store(tmp_path / "c.db")
    s2.import_json(backup)
    tasks = s2.list_tasks(include_done=True)
    assert [t.title for t in tasks] == ["keep me"]
    assert s2.today_focus() == 1
