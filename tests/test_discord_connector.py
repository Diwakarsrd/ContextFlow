from contextflow.connectors.discord.connector import DiscordConnector


def test_discord_connector_mock_mode():
    connector = DiscordConnector()
    # Should automatically fall back to mock mode if no token is provided
    connector.authenticate()

    resources = list(connector.discover())
    assert len(resources) == 1
    assert resources[0] == "mock_channel"

    raw_records = list(connector.fetch(resources[0]))
    assert len(raw_records) == 1
    assert raw_records[0]["author"]["username"] == "DeveloperOne"

    normalized = connector.normalize(raw_records[0])
    assert normalized.id == "discord_msg_9999"
    assert "DeveloperOne" in normalized.content
    assert normalized.metadata["source"] == "discord"


def test_discord_connector_pipeline():
    connector = DiscordConnector()
    results = list(connector.sync())
    assert len(results) == 1
    assert results[0].metadata["source"] == "discord"
