from quiz_assistant.runtime import prepare_qt_runtime


def test_prepare_qt_runtime_preloads_system_icu_on_windows(tmp_path):
    system_root = tmp_path / "Windows"
    icu = system_root / "System32" / "icuuc.dll"
    icu.parent.mkdir(parents=True)
    icu.touch()
    loaded = []

    prepare_qt_runtime(
        platform_name="win32",
        system_root=system_root,
        loader=loaded.append,
    )

    assert loaded == [str(icu)]


def test_prepare_qt_runtime_does_nothing_off_windows(tmp_path):
    loaded = []

    prepare_qt_runtime(
        platform_name="linux",
        system_root=tmp_path,
        loader=loaded.append,
    )

    assert loaded == []
