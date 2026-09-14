from contextflow.connectors.gitlab.connector import GitLabConnector


def test_gitlab_connector_mock_mode():
    connector = GitLabConnector()
    connector.authenticate()

    resources = list(connector.discover())
    assert "issues" in resources
    assert "merge_requests" in resources

    raw_records = list(connector.fetch("issues"))
    assert len(raw_records) == 1
    assert raw_records[0]["title"] == "Update architectural documentation"

    normalized = connector.normalize(raw_records[0])
    assert normalized.id == "gitlab_issues_101"
    assert "Update architectural documentation" in normalized.content
    assert normalized.metadata["state"] == "opened"


def test_gitlab_connector_pipeline():
    connector = GitLabConnector()
    results = list(connector.sync())
    # Should yield results for both 'issues' and 'merge_requests' discovery resources
    assert len(results) == 2
