from pathlib import Path

from kunity_yamae.guards.addressables_guard import AddressablesGuard


def test_resources_changed_files_warn_for_any_resources_folder(tmp_path: Path) -> None:
    guard = AddressablesGuard(tmp_path, {})

    issues = guard.check(["Packages/com.example/Runtime/Resources/Neutral.prefab"], "")

    assert len(issues) == 1
    assert issues[0]["guard"] == "resources_addressables"
    assert "Resources folder" in issues[0]["message"]
    assert "Assets/Resources" not in issues[0]["message"]


def test_resources_load_resolves_package_resources_without_assets_root_warning(
    tmp_path: Path,
) -> None:
    resource = tmp_path / "Packages" / "com.example" / "Runtime" / "Resources" / "Neutral.asset"
    resource.parent.mkdir(parents=True)
    resource.write_text("neutral", encoding="utf-8")
    guard = AddressablesGuard(tmp_path, {})

    issues = guard.check([], '+        Resources.Load("Neutral");\n')

    assert not [
        issue
        for issue in issues
        if issue["guard"] == "resources_addressables" and "may not exist" in issue["message"]
    ]


def test_addressables_literals_emit_generic_verification_messages(tmp_path: Path) -> None:
    guard = AddressablesGuard(tmp_path, {})
    diff = "\n".join(
        [
            '+        Addressables.LoadAssetAsync<GameObject>("hero/player");',
            '+        Addressables.LoadAssetsAsync<Sprite>("ui/icons", sprite => {});',
            '+        Addressables.LabelExists("featured-content");',
            '+        Addressables.LoadSceneAsync("arena-night", LoadSceneMode.Additive);',
        ]
    )

    issues = guard.check([], diff)
    messages = [issue["message"] for issue in issues]

    assert any("Addressables key 'hero/player'" in message for message in messages)
    assert any("Addressables key/list 'ui/icons'" in message for message in messages)
    assert any("Addressables label 'featured-content'" in message for message in messages)
    assert any("Addressables scene key 'arena-night'" in message for message in messages)
    assert all("groups" not in message.lower() for message in messages)
    assert all("catalog" not in message.lower() for message in messages)


def test_addressables_nonliteral_expressions_are_not_overclaimed(tmp_path: Path) -> None:
    guard = AddressablesGuard(tmp_path, {})
    diff = "\n".join(
        [
            "+        Addressables.LoadAssetAsync<GameObject>(heroKey);",
            "+        Addressables.LoadAssetsAsync<Sprite>(runtimeLabels, sprite => {});",
            "+        Addressables.LabelExists(labelName);",
            "+        Addressables.LoadSceneAsync(sceneKey, LoadSceneMode.Additive);",
        ]
    )

    issues = guard.check([], diff)

    assert not [
        issue for issue in issues if issue["guard"] == "resources_addressables"
    ]
