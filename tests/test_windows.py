from quiz_assistant.windows import WindowInfo, filter_window_records


def test_filter_window_records_excludes_hidden_untitled_and_own_window():
    records = [
        (10, "Chrome - 题目", True),
        (11, "", True),
        (12, "Hidden", False),
        (13, "Assistant", True),
    ]

    result = filter_window_records(records, own_hwnd=13)

    assert result == [WindowInfo(hwnd=10, title="Chrome - 题目")]


def test_filter_window_records_trims_titles_and_sorts_case_insensitively():
    records = [(1, " zeta ", True), (2, "Alpha", True)]

    result = filter_window_records(records)

    assert result == [
        WindowInfo(hwnd=2, title="Alpha"),
        WindowInfo(hwnd=1, title="zeta"),
    ]

