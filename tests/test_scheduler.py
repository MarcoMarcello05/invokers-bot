from invokers_bot.goals import Goal
from invokers_bot.scheduler import TaskScheduler


def test_scheduler_picks_highest_utility():
    s = TaskScheduler()
    goals = [
        Goal("arena", priority=3, expected_value=2, resource_cost=1, risk=0),
        Goal("claim_reward", priority=5, expected_value=3, resource_cost=0, risk=0),
    ]
    assert s.choose_goal(goals).name == "claim_reward"


def test_scheduler_returns_none_for_non_positive_utility():
    s = TaskScheduler()
    goals = [Goal("expensive", priority=1, expected_value=0, resource_cost=3, risk=0)]
    assert s.choose_goal(goals) is None
