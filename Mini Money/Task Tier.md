# Task Tier Breakdown — Mini Money

Currency-agnostic reward model. All values are percentages of a parent-defined base budget (`parent\_defined\_base`), set once per child in whatever currency they use.

`payout\_amount = (task\_percentage / 100) \* parent\_defined\_base`

## Model

- **Primary tasks** — calculated against the budget; total payout across all primary task completions in a period cannot exceed the budget.

- **Secondary tasks** — extra tasks that become available based on parent-defined rules; paid separately, not capped against the primary budget.

### Tier split descriptors

- Daily: these are tasks that comes into effect at 00:00am and needs to be completed by 11:59 pm

  - These tasks can be toggled to be Weekday only or Weekend including(default selection)

  - Weekday tasks will have the % split over 5 days vs the 7 days for Weekend including daily tasks

- Weekly: these are tasks that comes into effect at 00:00am on a monday and needs to be completed by sunday 11:59 pm.

  - These tasks can be set to be on a specific day(De or can be completed anytime before the weekly timing rules

  - The user has the ability to set the recurring to be Bi-Weekly which will split the occurance across the select days with a maximum of 3 days that can be selected

- Monthly :these are tasks that comes into effect at 00:00am on the 1st day of the month and needs to be completed by last day of the month by 11:59 pm.

  - These tasks can be set to be on a specific day or can be completed anytime before the weekly timing rules

  - The user has the ability to set the recurring to be Bi-Monthly which will split the occurance across the select days with a maximum of 2 weeks that can be selected


### Tier split (open decision — currently uniform across age bands, override if needed)

- Daily tier: 40% of monthly primary budget

- Weekly tier: 35% of monthly primary budget

- Monthly tier: 25% of monthly primary budget

- In the event that a tier is not used, e.g no monthly task has been set, then the % split will move across the remaining categories

### Earn Rules

When a Minor fails to submit a task as completed by the required deadline, the parent will be prompted to either mark the task as complete or incomplete.

- In the event that the minor failed to complete the task,and the parent confirmed this as incomplete, the share for the day will be deducted from the budget.

- In the event that the minor failed to complete 5 tasks, the parent will be prompted to review the activity of the minor. Should the parent fiond the minor did not complete the tasks vs completing the task but not marking it on the app, the Parent may freeze the earning and set a probationary period in which the minor will need to complete set tasks before earning can resume. The days missed will not be compensate.

  - The Rate will be reduced during the probationary period and will be for a maximum of 5 days as long as the 5 days do not overlap into the new month. Normal rate will auto enable once the probationary period has been completed.

### Occurrence assumptions

- Daily task: 21 - 30 occurrences/month

- Weekly task: 4.3 – 8.6 occurrences/month

- Monthly task: 1 - 2 occurrence/month

Per-completion % = (tier share allocated to task) / (expected occurrences per month)


## Ages 6–9

### Daily tier (7 tasks, relative weight total = 18, gets 40% of budget)

| Task | Relative weight | Monthly share (of 40%) | Occurrences/mo | Per-completion % |
| - | - | - | - | - |
| Make bed | 2 | 4.4% | 30 | 0.148% |
| Brush teeth (both times) | 1 | 2.2% | 30 | 0.074% |
| Pack school bag | 2 | 4.4% | 30 | 0.148% |
| Feed pet | 3 | 6.7% | 30 | 0.222% |
| Tidy toys | 3 | 6.7% | 30 | 0.222% |
| Set the table | 2 | 4.4% | 30 | 0.148% |
| Read for 15 min | 5 | 11.1% | 30 | 0.370% |


### Weekly tier (1 task, gets 35% of budget)

| Task | Occurrences/mo | Per-completion % |
| - | - | - |
| Weekly room tidy (deeper clean) | ~4.3 | 8.14% |


### Monthly tier (25% of budget — currently unassigned)

| Task | Occurrences/mo | Per-completion % |
| - | - | - |
| *(none assigned — 25% unclaimed unless a task is added)* | 1 | — |



## Ages 10–13

### Daily tier (2 tasks: homework, dishes — relative weight total = 10, gets 40% of budget)

| Task | Relative weight | Monthly share (of 40%) | Occurrences/mo | Per-completion % |
| - | - | - | - | - |
| Includes all daily tasks of the previous ages as well as the below |
| Homework completed on time | 5 | 20% | 30 | 0.667% |
| Dishes after dinner | 5 | 20% | 30 | 0.667% |


### Weekly tier (5 tasks — relative weight total = 58, gets 35% of budget)

| Task | Relative weight | Monthly share (of 35%) | Occurrences/mo | Per-completion % |
| - | - | - | - | - |
| Take out trash | 8 | 4.83% | 4.3 | 1.123% |
| Vacuum a room | 15 | 9.05% | 4.3 | 2.105% |
| Water plants/garden | 5 | 3.02% | 4.3 | 0.702% |
| Laundry (sort + fold own clothes) | 20 | 12.07% | 4.3 | 2.807% |
| Help with grocery unpacking | 10 | 6.03% | 4.3 | 1.402% |


### Monthly tier (1 task, gets 25% of budget)

| Task | Occurrences/mo | Per-completion % |
| - | - | - |
| Budget check-in with parent | 1 | 25% |



## Ages 14–18

### Daily tier (0 tasks assigned — 40% currently unclaimed)

| Task | Occurrences/mo | Per-completion % |
| - | - | - |
| Includes all of the previous ages daily tasks  | 30 | — |


### Weekly tier (5 tasks — relative weight total = 190, gets 35% of budget)

| Task | Relative weight | Monthly share (of 35%) | Occurrences/mo | Per-completion % |
| - | - | - | - | - |
| Cook a family meal | 40 | 7.37% | 4.3 | 1.714% |
| Mow lawn/yard work | 50 | 9.21% | 4.3 | 2.142% |
| Deep clean bathroom | 30 | 5.53% | 4.3 | 1.286% |
| Car washing | 40 | 7.37% | 4.3 | 1.714% |
| Tutor/help younger sibling with homework | 30 | 5.53% | 4.3 | 1.286% |


### Monthly tier (1 task, gets 25% of budget)

| Task | Occurrences/mo | Per-completion % |
| - | - | - |
| Manage own budget plan / savings goal review | 1 | 25% |



## Secondary tasks (not capped against primary budget — availability rule-gated)

| Age band | Task | Suggested rate | Frequency |
| - | - | - | - |
| 14–18 | Errand/babysitting | 50 | As-needed |





## Payment Rules

1. All payments made will be for work completed the previous month to allow for all calculations and funds to be accounted for. 

2. It is recommended that the parent cover the 1st month while the minor adjusts to the app and assigned tasks
