# Track P: a trade-off gate for the personal questionnaire

The earlier item gate treated an 80% blind-model preference as evidence that a question measured generic research sense. It rejected 16 of Ethan's 21 answers. A six-vote Luna repeat on hand rewrites rejected nine more and appeared to pass seven only because the model favored a display position. Vote parity is neither necessary nor sufficient for a useful taste question.

## Decision

Before an item is shown, a reviewer other than the person answering records a concrete benefit and cost for **each** option in the item's stated situation. The reviewer passes the item if both actions are feasible, keep the environment's required behavior opportunity, compete for the same time or budget, and have a plausible reason a careful researcher might choose them. The reviewer rejects an item if one action is dominated or breaks a requirement. A preference for one valid action, however strong, does not reject it. This is a qualitative item-quality check, not an estimate of how people will answer.

The review is a shared sidecar keyed by the question, context and pole texts. Its decisions are `pass`, `reject`, or `superseded`. A pass needs the four benefit/cost statements. An unanswered item with no review is not shown. Old Sonnet and Luna votes remain in `agreement.jsonl` as an audit of the discarded gate; they do not determine eligibility. No model calls are needed to review an item.

## Ethan's 21 questions

Keep all 21 old item rows and all 21 human answers. Mark the 16 questions being rewritten `superseded`, so an old answer is never mapped onto new wording. Keep five reviewed original items. Add 16 reviewed replacements, each with its old pair as `parent`. This yields 21 active questions: five already answered and 16 to ask Ethan. Update the bank to give future respondents the revised wording, but do not collect or infer their answers.

Each replacement describes an actual choice with a shared constraint. Options name what evidence the researcher would gain and what they give up. Scenario questions use the environment's behavior opportunity, rather than generic references to "the test". The reviewer records why each option is defensible. The gate does not assert that respondents will split evenly; answer and recheck data will show whether an item is informative.
