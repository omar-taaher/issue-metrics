"""A module for measuring the time it takes to get the first response to a GitHub issue.

This module provides functions for measuring the time it takes to get the first response
to a GitHub issue, as well as calculating the average time to first response for a list
of issues.

Functions:
    measure_time_to_first_response(
        issue: Union[github3.issues.Issue, None],
        discussion: Union[dict, None]
        pull_request: Union[github3.pulls.PullRequest, None],
    ) -> Union[timedelta, None]:
        Measure the time to first response for a single issue or a discussion.
    get_stats_time_to_first_response(
        issues: List[IssueWithMetrics]
    ) -> Union[timedelta, None]:
        Calculate stats describing time to first response for a list of issues with metrics.

"""

from datetime import datetime, timedelta
from typing import List, Union

import github3
import numpy
from classes import IssueWithMetrics


def measure_time_to_first_response(
    issue: Union[github3.issues.Issue, None],  # type: ignore
    discussion: Union[dict, None],
    pull_request: Union[github3.pulls.PullRequest, None] = None,
    ready_for_review_at: Union[datetime, None] = None,
    ignore_users: Union[List[str], None] = None,
) -> Union[timedelta, None]:
    """Measure the time to first response for a single issue, pull request, or a discussion.

    Args:
        issue (Union[github3.issues.Issue, None]): A GitHub issue.
        discussion (Union[dict, None]): A GitHub discussion.
        pull_request (Union[github3.pulls.PullRequest, None]): A GitHub pull request.
        ignore_users (List[str]): A list of GitHub usernames to ignore.

    Returns:
        Union[timedelta, None]: The time to first response for the issue/discussion.

    """
    first_review_comment_time = None
    first_comment_time = None
    earliest_response = None
    issue_time = None
    if ignore_users is None:
        ignore_users = []

    # Get the first comment time
    if issue:
        comments = issue.issue.comments(
            number=20, sort="created", direction="asc"
        )  # type: ignore
        for comment in comments:
            if ignore_comment(
                issue.issue.user,
                comment.user,
                ignore_users,
                comment.created_at,
                ready_for_review_at,
            ):
                continue
            first_comment_time = comment.created_at
            break

        # Check if the issue is actually a pull request
        # so we may also get the first review comment time
        if pull_request:
            review_comments = pull_request.reviews(number=50)  # type: ignore
            try:
                for review_comment in review_comments:
                    if ignore_comment(
                        issue.issue.user,
                        review_comment.user,
                        ignore_users,
                        review_comment.submitted_at,
                        ready_for_review_at,
                    ):
                        continue
                    first_review_comment_time = review_comment.submitted_at
                    break
            except TypeError as e:
                print(
                    f"An error occurred processing review comments. Perhaps the review contains a ghost user. {e}"
                )

        # Figure out the earliest response timestamp
        if first_comment_time and first_review_comment_time:
            earliest_response = min(first_comment_time, first_review_comment_time)
        elif first_comment_time:
            earliest_response = first_comment_time
        elif first_review_comment_time:
            earliest_response = first_review_comment_time
        else:
            return None

        # Get the created_at time for the issue so we can calculate the time to first response
        if ready_for_review_at:
            issue_time = ready_for_review_at
        else:
            issue_time = datetime.fromisoformat(issue.created_at)

    if discussion and len(discussion["comments"]["nodes"]) > 0:
        earliest_response = datetime.fromisoformat(
            discussion["comments"]["nodes"][0]["createdAt"]
        )
        issue_time = datetime.fromisoformat(discussion["createdAt"])

    if earliest_response and issue_time:
        time_between_issue_and_first_comment: timedelta | None = businessDuration(issue_time,earliest_response)
        return time_between_issue_and_first_comment

    return None


def ignore_comment(
    issue_user: github3.users.User,
    comment_user: github3.users.User,
    ignore_users: List[str],
    comment_created_at: datetime,
    ready_for_review_at: Union[datetime, None],
) -> bool:
    """Check if a comment should be ignored."""

    user_is_ignored: bool = comment_user.login in ignore_users
    user_is_a_bot: bool = str(comment_user.type.lower()) == "bot"
    user_is_issue_creator: bool = str(comment_user.login) == str(issue_user.login)
    issue_was_created_before_ready_for_review: bool = False
    is_pending_comment: bool = not isinstance(comment_created_at, datetime)
    if ready_for_review_at and not is_pending_comment:
        issue_was_created_before_ready_for_review = (
            comment_created_at < ready_for_review_at
        )
    result: bool = (
        user_is_ignored
        or user_is_a_bot
        or user_is_issue_creator
        or is_pending_comment
        or issue_was_created_before_ready_for_review
    )
    return result


def get_stats_time_to_first_response(
    issues: List[IssueWithMetrics],
) -> Union[dict[str, timedelta], None]:
    """Calculate the stats describing time to first response for a list of issues.

    Args:
        issues (List[IssueWithMetrics]): A list of GitHub issues with metrics attached.

    Returns:
        Union[Dict{String: datetime.timedelta}, None]: The stats describing time to first response for the issues in seconds.

    """
    response_times = []
    none_count = 0
    for issue in issues:
        if issue.time_to_first_response:
            response_times.append(issue.time_to_first_response.total_seconds())
        else:
            none_count += 1

    if len(issues) - none_count <= 0:
        return None

    average_seconds_to_first_response = numpy.round(numpy.average(response_times))
    med_seconds_to_first_response = numpy.round(numpy.median(response_times))
    ninety_percentile_seconds_to_first_response = numpy.round(
        numpy.percentile(response_times, 90, axis=0)
    )

    stats = {
        "avg": timedelta(seconds=average_seconds_to_first_response),
        "med": timedelta(seconds=med_seconds_to_first_response),
        "90p": timedelta(seconds=ninety_percentile_seconds_to_first_response),
    }

    # Print the average time to first response converting seconds to a readable time format
    print(
        f"Average time to first response: {timedelta(seconds=average_seconds_to_first_response)}"
    )

    return stats



def businessDuration(start: datetime, end: datetime) -> timedelta:
    # Define the working day start and end time
    workday_start = 9  # 9 AM
    workday_end = 18   # 6 PM

    # Initialize the total duration
    total_duration = timedelta()

    # Loop through each day from start to end
    current = start
    while current < end:
        # Skip non-working days (Friday=4, Saturday=5)
        if current.weekday() in [4, 5]:
            current += timedelta(days=1)
            current = current.replace(hour=workday_start, minute=0, second=0, microsecond=0)
            continue
        
        # Get the current day work start and end time
        current_start = current.replace(hour=workday_start, minute=0, second=0, microsecond=0)
        current_end = current.replace(hour=workday_end, minute=0, second=0, microsecond=0)
        
        # If current day is the start day, adjust the start time
        if current.date() == start.date():
            current_start = max(current, current_start)
        
        # If current day is the end day, adjust the end time
        if current.date() == end.date():
            current_end = min(end, current_end)

        # Calculate the time spent within working hours
        if current_start < current_end:
            total_duration += current_end - current_start

        # Move to the next day
        current += timedelta(days=1)
        current = current.replace(hour=workday_start, minute=0, second=0, microsecond=0)

    return total_duration
