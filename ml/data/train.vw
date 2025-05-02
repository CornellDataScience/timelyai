# Training data for time recommendation system
# Format: action:cost:probability | features
# action: time slot index (0-32 for 30-minute slots from 6:00 to 22:00)
# cost: 0 for accepted, 1 for rejected
# probability: 20% of week for task (task_duration / (16 * 7))
# features:
#   event_type: type of event (hw, meeting, project, workout)
#   task_duration: duration in hours
#   hours_until_due: hours until deadline
#   daily_free_time: hours of free time per day
#   day_of_week: 0-6 (Monday-Sunday)
#   is_weekend: 0 or 1
#   time_of_day: current hour + minute/60

# Example 1: Homework (accepted)
0:0:0.013 | event_type:hw task_duration:1.0 hours_until_due:4 daily_free_time:4.5 day_of_week:2 is_weekend:0 time_of_day:9.5

# Example 2: Sleep (rejected)
1:1:0.009 | event_type:sleep task_duration:1.0 hours_until_due:999 daily_free_time:4.5 day_of_week:2 is_weekend:0 time_of_day:9.5

# Example 3: Meeting (accepted)
2:0:0.004 | event_type:meeting task_duration:0.5 hours_until_due:2 daily_free_time:6.0 day_of_week:1 is_weekend:0 time_of_day:8.5

# Example 4: Reading (rejected)
3:1:0.013 | event_type:reading task_duration:1.5 hours_until_due:48 daily_free_time:5.0 day_of_week:3 is_weekend:0 time_of_day:10.0

# Example 5: Homework (accepted)
4:0:0.018 | event_type:hw task_duration:2.0 hours_until_due:24 daily_free_time:3.0 day_of_week:4 is_weekend:0 time_of_day:9.0

# Example 6: Relax (rejected)
5:1:0.004 | event_type:relax task_duration:0.5 hours_until_due:999 daily_free_time:4.0 day_of_week:5 is_weekend:0 time_of_day:12.0

# Example 7: Homework (accepted)
6:0:0.009 | event_type:hw task_duration:1.0 hours_until_due:12 daily_free_time:5.5 day_of_week:6 is_weekend:1 time_of_day:8.0

# Example 8: Meeting (accepted)
7:0:0.009 | event_type:meeting task_duration:1.0 hours_until_due:6 daily_free_time:4.0 day_of_week:0 is_weekend:0 time_of_day:14.0

# Example 9: Reading (rejected)
8:1:0.009 | event_type:reading task_duration:1.0 hours_until_due:72 daily_free_time:6.0 day_of_week:2 is_weekend:0 time_of_day:16.0

# Example 10: Homework (accepted)
9:0:0.022 | event_type:hw task_duration:2.5 hours_until_due:36 daily_free_time:3.5 day_of_week:3 is_weekend:0 time_of_day:10.5
