import cloud_enum


def test_build_names_deduplicates_colliding_inputs(monkeypatch):
    monkeypatch.setattr('builtins.print', lambda *args, **kwargs: None)

    names = cloud_enum.build_names(['Example', 'example'], ['dev', 'dev'])

    assert len(names) == len(set(names))
    assert 'example' in names
    assert 'exampledev' in names
    assert 'devexample' in names


def test_build_names_skips_empty_keywords(monkeypatch):
    monkeypatch.setattr('builtins.print', lambda *args, **kwargs: None)

    assert cloud_enum.build_names(['!!!'], []) == []


def test_build_names_strips_domain_suffixes_from_mutations_by_default(monkeypatch):
    monkeypatch.setattr('builtins.print', lambda *args, **kwargs: None)

    names = cloud_enum.build_names(['portal.example.com'], ['dev'])

    assert 'portal.example.com' in names
    assert 'portal' in names
    assert 'portal-dev' in names
    assert 'dev.portal' in names
    assert 'portal.example.com-dev' not in names
    assert 'dev.portal.example.com' not in names


def test_build_names_can_include_domain_suffixes_in_mutations(monkeypatch):
    monkeypatch.setattr('builtins.print', lambda *args, **kwargs: None)

    names = cloud_enum.build_names(['portal.example.com'], ['dev'],
                                   include_domain_suffixes=True)

    assert 'portal.example.com' in names
    assert 'portal.example.com-dev' in names
    assert 'dev.portal.example.com' in names
