"""A module containing unit tests for the issue_metrics module.

This module contains unit tests for the functions in the issue_metrics module
that measure and analyze metrics of GitHub issues. The tests use mock GitHub
issues and comments to test the functions' behavior.

Classes:
    TestSearchIssues: A class to test the search_issues function.
    TestGetPerIssueMetrics: A class to test the get_per_issue_metrics function.
    TestGetEnvVars: A class to test the get_env_vars function.
    TestMain: A class to test the main function.

"""

import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from issue_metrics import (
    IssueWithMetrics,
    get_env_vars,
    get_owners_and_repositories,
    get_per_issue_metrics,
    measure_time_to_close,
    measure_time_to_first_response,
    search_issues,
)


class TestSearchIssues(unittest.TestCase):
    """Unit tests for the search_issues function.

    This class contains unit tests for the search_issues function in the
    issue_metrics module. The tests use the unittest module and the unittest.mock
    module to mock the GitHub API and test the function in isolation.

    Methods:
        test_search_issues_with_owner_and_repository: Test that search_issues with owner/repo returns the correct issues.
        test_search_issues_with_just_owner_or_org: Test that search_issues with just an owner/org returns the correct issues.

    """

    def test_search_issues_with_owner_and_repository(self):
        """Test that search_issues with owner/repo returns the correct issues."""

        # Set up the mock GitHub connection object
        mock_issues = [
            MagicMock(title="Issue 1"),
            MagicMock(title="Issue 2"),
        ]

        # simulating github3.structs.SearchIterator return value
        mock_search_result = MagicMock()
        mock_search_result.__iter__.return_value = iter(mock_issues)
        mock_search_result.ratelimit_remaining = 30

        mock_connection = MagicMock()
        mock_connection.search_issues.return_value = mock_search_result

        # Call search_issues and check that it returns the correct issues
        repo_with_owner = {"owner": "owner1", "repository": "repo1"}
        owners_and_repositories = [repo_with_owner]
        issues = search_issues("is:open", mock_connection, owners_and_repositories)
        self.assertEqual(issues, mock_issues)

    def test_search_issues_with_just_owner_or_org(self):
        """Test that search_issues with just an owner/org returns the correct issues."""

        # Set up the mock GitHub connection object
        mock_issues = [
            MagicMock(title="Issue 1"),
            MagicMock(title="Issue 2"),
            MagicMock(title="Issue 3"),
        ]

        # simulating github3.structs.SearchIterator return value
        mock_search_result = MagicMock()
        mock_search_result.__iter__.return_value = iter(mock_issues)
        mock_search_result.ratelimit_remaining = 30

        mock_connection = MagicMock()
        mock_connection.search_issues.return_value = mock_search_result

        # Call search_issues and check that it returns the correct issues
        org = {"owner": "org1"}
        owners = [org]
        issues = search_issues("is:open", mock_connection, owners)
        self.assertEqual(issues, mock_issues)


class TestGetOwnerAndRepository(unittest.TestCase):
    """Unit tests for the get_owners_and_repositories function.

    This class contains unit tests for the get_owners_and_repositories function in the
    issue_metrics module. The tests use the unittest module and the unittest.mock
    module to mock the GitHub API and test the function in isolation.

    Methods:
        test_get_owners_with_owner_and_repo_in_query: Test get both owner and repo.
        test_get_owners_and_repositories_with_repo_in_query: Test get just owner.
        test_get_owners_and_repositories_without_either_in_query: Test get neither.
        test_get_owners_and_repositories_with_multiple_entries: Test get multiple entries.
    """

    def test_get_owners_with_owner_and_repo_in_query(self):
        """Test get both owner and repo."""
        result = get_owners_and_repositories("repo:owner1/repo1")
        self.assertEqual(result[0].get("owner"), "owner1")
        self.assertEqual(result[0].get("repository"), "repo1")

    def test_get_owner_and_repositories_without_repo_in_query(self):
        """Test get just owner."""
        result = get_owners_and_repositories("org:owner1")
        self.assertEqual(result[0].get("owner"), "owner1")
        self.assertIsNone(result[0].get("repository"))

    def test_get_owners_and_repositories_without_either_in_query(self):
        """Test get neither."""
        result = get_owners_and_repositories("is:blah")
        self.assertEqual(result, [])

    def test_get_owners_and_repositories_with_multiple_entries(self):
        """Test get multiple entries."""
        result = get_owners_and_repositories("repo:owner1/repo1 org:owner2")
        self.assertEqual(result[0].get("owner"), "owner1")
        self.assertEqual(result[0].get("repository"), "repo1")
        self.assertEqual(result[1].get("owner"), "owner2")
        self.assertIsNone(result[1].get("repository"))

    def test_get_owners_and_repositories_with_org(self):
        """Test get org as owner."""
        result = get_owners_and_repositories("org:owner1")
        self.assertEqual(result[0].get("owner"), "owner1")
        self.assertIsNone(result[0].get("repository"))

    def test_get_owners_and_repositories_with_user(self):
        """Test get user as owner."""
        result = get_owners_and_repositories("user:owner1")
        self.assertEqual(result[0].get("owner"), "owner1")
        self.assertIsNone(result[0].get("repository"))


class TestGetEnvVars(unittest.TestCase):
    """Test suite for the get_env_vars function."""

    @patch.dict(
        os.environ,
        {"GH_TOKEN": "test_token", "SEARCH_QUERY": "is:issue is:open repo:user/repo"},
    )
    def test_get_env_vars(self):
        """Test that the function correctly retrieves the environment variables."""

        # Call the function and check the result
        search_query = get_env_vars(test=True).search_query
        gh_token = get_env_vars(test=True).gh_token
        gh_token_expected_result = "test_token"
        search_query_expected_result = "is:issue is:open repo:user/repo"
        self.assertEqual(gh_token, gh_token_expected_result)
        self.assertEqual(search_query, search_query_expected_result)

    def test_get_env_vars_missing_query(self):
        """Test that the function raises a ValueError
        if the SEARCH_QUERY environment variable is not set."""
        # Unset the SEARCH_QUERY environment variable
        os.environ.pop("SEARCH_QUERY", None)

        # Call the function and check that it raises a ValueError
        with self.assertRaises(ValueError):
            get_env_vars(test=True)


class TestGetPerIssueMetrics(unittest.TestCase):
    """Test suite for the get_per_issue_metrics function."""

    @patch.dict(
        os.environ,
        {
            "GH_TOKEN": "test_token",
            "SEARCH_QUERY": "is:issue is:open repo:user/repo",
            "HIDE_AUTHOR": "true",
            "HIDE_LABEL_METRICS": "true",
            "HIDE_TIME_TO_ANSWER": "true",
            "HIDE_TIME_TO_CLOSE": "true",
            "HIDE_TIME_TO_FIRST_RESPONSE": "true",
        },
    )
    def test_get_per_issue_metrics_with_hide_envs(self):
        """
        Test that the function correctly calculates the metrics for
        a list of GitHub issues where HIDE_* envs are set true
        """

        # Create mock data
        mock_issue1 = MagicMock(
            title="Issue 1",
            html_url="https://github.com/user/repo/issues/1",
            user={"login": "alice"},
            state="open",
            comments=1,
            created_at="2023-01-01T00:00:00Z",
        )

        mock_comment1 = MagicMock()
        mock_comment1.created_at = datetime.fromisoformat("2023-01-02T00:00:00Z")
        mock_issue1.issue.comments.return_value = [mock_comment1]
        mock_issue1.issue.pull_request_urls = None

        mock_issue2 = MagicMock(
            title="Issue 2",
            html_url="https://github.com/user/repo/issues/2",
            user={"login": "bob"},
            state="closed",
            comments=1,
            created_at="2023-01-01T00:00:00Z",
            closed_at="2023-01-04T00:00:00Z",
        )

        mock_comment2 = MagicMock()
        mock_comment2.created_at = datetime.fromisoformat("2023-01-03T00:00:00Z")
        mock_issue2.issue.comments.return_value = [mock_comment2]
        mock_issue2.issue.pull_request_urls = None

        issues = [
            mock_issue1,
            mock_issue2,
        ]

        # Call the function and check the result
        with unittest.mock.patch(  # type:ignore
            "issue_metrics.measure_time_to_first_response",
            measure_time_to_first_response,
        ), unittest.mock.patch(  # type:ignore
            "issue_metrics.measure_time_to_close", measure_time_to_close
        ):
            (
                result_issues_with_metrics,
                result_num_issues_open,
                result_num_issues_closed,
            ) = get_per_issue_metrics(
                issues,
                env_vars=get_env_vars(test=True),
            )
        expected_issues_with_metrics = [
            IssueWithMetrics(
                "Issue 1",
                "https://github.com/user/repo/issues/1",
                "alice",
                None,
                None,
                None,
                None,
            ),
            IssueWithMetrics(
                "Issue 2",
                "https://github.com/user/repo/issues/2",
                "bob",
                None,
                None,
                None,
                None,
            ),
        ]
        expected_num_issues_open = 1
        expected_num_issues_closed = 1
        self.assertEqual(result_num_issues_open, expected_num_issues_open)
        self.assertEqual(result_num_issues_closed, expected_num_issues_closed)
        self.assertEqual(
            result_issues_with_metrics[0].time_to_first_response,
            expected_issues_with_metrics[0].time_to_first_response,
        )
        self.assertEqual(
            result_issues_with_metrics[0].time_to_close,
            expected_issues_with_metrics[0].time_to_close,
        )
        self.assertEqual(
            result_issues_with_metrics[1].time_to_first_response,
            expected_issues_with_metrics[1].time_to_first_response,
        )
        self.assertEqual(
            result_issues_with_metrics[1].time_to_close,
            expected_issues_with_metrics[1].time_to_close,
        )

    @patch.dict(
        os.environ,
        {
            "GH_TOKEN": "test_token",
            "SEARCH_QUERY": "is:issue is:open repo:user/repo",
            "HIDE_AUTHOR": "false",
            "HIDE_LABEL_METRICS": "false",
            "HIDE_TIME_TO_ANSWER": "false",
            "HIDE_TIME_TO_CLOSE": "false",
            "HIDE_TIME_TO_FIRST_RESPONSE": "false",
        },
    )
    def test_get_per_issue_metrics_without_hide_envs(self):
        """
        Test that the function correctly calculates the metrics for
        a list of GitHub issues where HIDE_* envs are set false
        """

        # Create mock data
        mock_issue1 = MagicMock(
            title="Issue 1",
            html_url="https://github.com/user/repo/issues/1",
            user={"login": "alice"},
            state="open",
            comments=1,
            created_at="2023-01-01T00:00:00Z",
        )

        mock_comment1 = MagicMock()
        mock_comment1.created_at = datetime.fromisoformat("2023-01-02T00:00:00Z")
        mock_issue1.issue.comments.return_value = [mock_comment1]
        mock_issue1.issue.pull_request_urls = None

        mock_issue2 = MagicMock(
            title="Issue 2",
            html_url="https://github.com/user/repo/issues/2",
            user={"login": "bob"},
            state="closed",
            comments=1,
            created_at="2023-01-01T00:00:00Z",
            closed_at="2023-01-04T00:00:00Z",
        )

        mock_comment2 = MagicMock()
        mock_comment2.created_at = datetime.fromisoformat("2023-01-03T00:00:00Z")
        mock_issue2.issue.comments.return_value = [mock_comment2]
        mock_issue2.issue.pull_request_urls = None

        issues = [
            mock_issue1,
            mock_issue2,
        ]

        # Call the function and check the result
        with unittest.mock.patch(  # type:ignore
            "issue_metrics.measure_time_to_first_response",
            measure_time_to_first_response,
        ), unittest.mock.patch(  # type:ignore
            "issue_metrics.measure_time_to_close", measure_time_to_close
        ):
            (
                result_issues_with_metrics,
                result_num_issues_open,
                result_num_issues_closed,
            ) = get_per_issue_metrics(
                issues,
                env_vars=get_env_vars(test=True),
            )
        expected_issues_with_metrics = [
            IssueWithMetrics(
                "Issue 1",
                "https://github.com/user/repo/issues/1",
                "alice",
                timedelta(hours=9),
                None,
                None,
                None,
            ),
            IssueWithMetrics(
                "Issue 2",
                "https://github.com/user/repo/issues/2",
                "bob",
                timedelta(hours=18),
                timedelta(days=3),
                None,
                None,
            ),
        ]
        expected_num_issues_open = 1
        expected_num_issues_closed = 1
        self.assertEqual(result_num_issues_open, expected_num_issues_open)
        self.assertEqual(result_num_issues_closed, expected_num_issues_closed)
        self.assertEqual(
            result_issues_with_metrics[0].time_to_first_response,
            expected_issues_with_metrics[0].time_to_first_response,
        )
        self.assertEqual(
            result_issues_with_metrics[0].time_to_close,
            expected_issues_with_metrics[0].time_to_close,
        )
        self.assertEqual(
            result_issues_with_metrics[1].time_to_first_response,
            expected_issues_with_metrics[1].time_to_first_response,
        )
        self.assertEqual(
            result_issues_with_metrics[1].time_to_close,
            expected_issues_with_metrics[1].time_to_close,
        )

    @patch.dict(
        os.environ,
        {
            "GH_TOKEN": "test_token",
            "SEARCH_QUERY": "is:issue is:open repo:user/repo",
            "IGNORE_USERS": "alice",
        },
    )
    def test_get_per_issue_metrics_with_ignore_users(self):
        """
        Test that the function correctly filters out issues with authors in the IGNORE_USERS variable
        """

        # Create mock data
        mock_issue1 = MagicMock(
            title="Issue 1",
            html_url="https://github.com/user/repo/issues/1",
            user={"login": "alice"},
            state="open",
            comments=1,
            created_at="2023-01-01T00:00:00Z",
        )

        mock_comment1 = MagicMock()
        mock_comment1.created_at = datetime.fromisoformat("2023-01-02T00:00:00Z")
        mock_issue1.issue.comments.return_value = [mock_comment1]
        mock_issue1.issue.pull_request_urls = None

        mock_issue2 = MagicMock(
            title="Issue 2",
            html_url="https://github.com/user/repo/issues/2",
            user={"login": "bob"},
            state="closed",
            comments=1,
            created_at="2023-01-01T00:00:00Z",
            closed_at="2023-01-04T00:00:00Z",
        )

        mock_comment2 = MagicMock()
        mock_comment2.created_at = datetime.fromisoformat("2023-01-03T00:00:00Z")
        mock_issue2.issue.comments.return_value = [mock_comment2]
        mock_issue2.issue.pull_request_urls = None

        issues = [
            mock_issue1,
            mock_issue2,
        ]

        # Call the function and check the result
        with unittest.mock.patch(  # type:ignore
            "issue_metrics.measure_time_to_first_response",
            measure_time_to_first_response,
        ), unittest.mock.patch(  # type:ignore
            "issue_metrics.measure_time_to_close", measure_time_to_close
        ):
            (
                result_issues_with_metrics,
                result_num_issues_open,
                result_num_issues_closed,
            ) = get_per_issue_metrics(
                issues,
                env_vars=get_env_vars(test=True),
                ignore_users=["alice"],
            )
        expected_issues_with_metrics = [
            IssueWithMetrics(
                "Issue 2",
                "https://github.com/user/repo/issues/2",
                "bob",
                timedelta(hours=18),
                timedelta(days=3),
                None,
                None,
            ),
        ]
        expected_num_issues_open = 0
        expected_num_issues_closed = 1
        self.assertEqual(result_num_issues_open, expected_num_issues_open)
        self.assertEqual(result_num_issues_closed, expected_num_issues_closed)
        self.assertEqual(
            result_issues_with_metrics[0].time_to_first_response,
            expected_issues_with_metrics[0].time_to_first_response,
        )
        self.assertEqual(
            result_issues_with_metrics[0].time_to_close,
            expected_issues_with_metrics[0].time_to_close,
        )


class TestDiscussionMetrics(unittest.TestCase):
    """Test suite for the discussion_metrics function."""

    def setUp(self):
        # Mock a discussion dictionary
        self.issue1 = {
            "title": "Issue 1",
            "url": "github.com/user/repo/issues/1",
            "user": {
                "login": "alice",
            },
            "createdAt": "2023-01-01T00:00:00Z",
            "comments": {
                "nodes": [
                    {
                        "createdAt": "2023-01-02T00:00:00Z",
                    }
                ]
            },
            "answerChosenAt": "2023-01-04T00:00:00Z",
            "closedAt": "2023-01-05T00:00:00Z",
        }

        self.issue2 = {
            "title": "Issue 2",
            "url": "github.com/user/repo/issues/2",
            "user": {
                "login": "bob",
            },
            "createdAt": "2023-01-01T00:00:00Z",
            "comments": {"nodes": [{"createdAt": "2023-01-03T00:00:00Z"}]},
            "answerChosenAt": "2023-01-05T00:00:00Z",
            "closedAt": "2023-01-07T00:00:00Z",
        }

    @patch.dict(
        os.environ,
        {"GH_TOKEN": "test_token", "SEARCH_QUERY": "is:issue is:open repo:user/repo"},
    )
    def test_get_per_issue_metrics_with_discussion(self):
        """
        Test that the function correctly calculates
        the metrics for a list of GitHub issues with discussions.
        """

        issues = [self.issue1, self.issue2]
        metrics = get_per_issue_metrics(
            issues, discussions=True, env_vars=get_env_vars(test=True)
        )

        # get_per_issue_metrics returns a tuple of
        # (issues_with_metrics, num_issues_open, num_issues_closed)
        self.assertEqual(len(metrics), 3)

        # Check that the metrics are correct, 0 issues open, 2 issues closed
        self.assertEqual(metrics[1], 0)
        self.assertEqual(metrics[2], 2)

        # Check that the issues_with_metrics has 2 issues in it
        self.assertEqual(len(metrics[0]), 2)

        # Check that the issues_with_metrics has the correct metrics,
        self.assertEqual(metrics[0][0].time_to_answer, timedelta(days=3))
        self.assertEqual(metrics[0][0].time_to_close, timedelta(days=4))
        self.assertEqual(metrics[0][0].time_to_first_response, timedelta(hours=9))
        self.assertEqual(metrics[0][1].time_to_answer, timedelta(days=4))
        self.assertEqual(metrics[0][1].time_to_close, timedelta(days=6))
        self.assertEqual(metrics[0][1].time_to_first_response, timedelta(hours=18))

    @patch.dict(
        os.environ,
        {
            "GH_TOKEN": "test_token",
            "SEARCH_QUERY": "is:issue is:open repo:user/repo",
            "HIDE_AUTHOR": "true",
            "HIDE_LABEL_METRICS": "true",
            "HIDE_TIME_TO_ANSWER": "true",
            "HIDE_TIME_TO_CLOSE": "true",
            "HIDE_TIME_TO_FIRST_RESPONSE": "true",
        },
    )
    def test_get_per_issue_metrics_with_discussion_with_hide_envs(self):
        """
        Test that the function correctly calculates
        the metrics for a list of GitHub issues with discussions
        and HIDE_* env vars set to True
        """

        issues = [self.issue1, self.issue2]
        metrics = get_per_issue_metrics(
            issues, discussions=True, env_vars=get_env_vars(test=True)
        )

        # get_per_issue_metrics returns a tuple of
        # (issues_with_metrics, num_issues_open, num_issues_closed)
        self.assertEqual(len(metrics), 3)

        # Check that the metrics are correct, 0 issues open, 2 issues closed
        self.assertEqual(metrics[1], 0)
        self.assertEqual(metrics[2], 2)

        # Check that the issues_with_metrics has 2 issues in it
        self.assertEqual(len(metrics[0]), 2)

        # Check that the issues_with_metrics has the correct metrics,
        self.assertEqual(metrics[0][0].time_to_answer, None)
        self.assertEqual(metrics[0][0].time_to_close, None)
        self.assertEqual(metrics[0][0].time_to_first_response, None)
        self.assertEqual(metrics[0][1].time_to_answer, None)
        self.assertEqual(metrics[0][1].time_to_close, None)
        self.assertEqual(metrics[0][1].time_to_first_response, None)


if __name__ == "__main__":
    unittest.main()
