"""Tests for the Content creation team."""

from unittest.mock import patch

from argus.teams.content import create_content_team


class TestContentTeam:
    """Tests for Content Team creation and configuration."""

    @patch("argus.teams.content.SqliteDb")
    @patch("argus.teams.content.create_writer_agent")
    @patch("argus.teams.content.create_researcher_agent")
    @patch("argus.teams.content.create_leader_model")
    def test_create_content_team(
        self,
        mock_leader_model,
        mock_researcher,
        mock_writer,
        mock_db_cls,
    ):
        """Content team has correct name, mode, and member count."""
        team = create_content_team()

        assert team.name == "Content Team"
        assert team.mode == "coordinate"
        assert len(team.members) == 2
        assert team.markdown is True
        assert team.add_history_to_context is True

    @patch("argus.teams.content.SqliteDb")
    @patch("argus.teams.content.create_writer_agent")
    @patch("argus.teams.content.create_researcher_agent")
    @patch("argus.teams.content.create_leader_model")
    def test_content_team_has_instructions(
        self,
        mock_leader_model,
        mock_researcher,
        mock_writer,
        mock_db_cls,
    ):
        """Content team has non-empty instructions."""
        team = create_content_team()

        assert team.instructions is not None
        assert len(team.instructions) > 0

    @patch("argus.teams.content.SqliteDb")
    @patch("argus.teams.content.create_writer_agent")
    @patch("argus.teams.content.create_researcher_agent")
    @patch("argus.teams.content.create_leader_model")
    def test_content_team_uses_coordinate_mode(
        self,
        mock_leader_model,
        mock_researcher,
        mock_writer,
        mock_db_cls,
    ):
        """Content team uses coordinate mode for task delegation."""
        team = create_content_team()

        assert team.mode == "coordinate"
