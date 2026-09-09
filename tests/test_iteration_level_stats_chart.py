from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_research_yield_chart_uses_iterations_not_calendar_days():
    stats_js = (ROOT / "site" / "stats.js").read_text(encoding="utf-8")

    assert "function buildIterationRows" in stats_js
    assert "payload.extraRuns || []" in stats_js
    assert "iterationNumber" in stats_js
    assert "ultime 30 iterazioni" in stats_js
    assert "Risultati unici e nuovi candidati per iterazione" in stats_js
    assert "Risultati unici e nuovi candidati per giorno" not in stats_js


def test_daily_calendar_view_remains_day_based():
    stats_js = (ROOT / "site" / "stats.js").read_text(encoding="utf-8")

    assert "function renderDailyTable" in stats_js
    assert "calendarWindow(rows, 30)" in stats_js
