"""The open-ended part of the personal questionnaire.

Written answers become corpus documents, so they feed the same text-to-taste extraction as
papers (taste/extract.py). `kind` follows the corpus convention: "research" answers are
direct evidence about research decisions; "other" answers are down-weighted life evidence
that can still reveal dispositions such as risk tolerance or frugality.

The forced-choice trade-off items are not here: they are the personal track's seed pairs
(taste/trackp.py), served and recorded through trackp so the user model sees the same rows
whether answered here, in a terminal or in chat.

Wording rule: each question asks what the person does or believes, without naming a
"right" answer or the profile features it informs.
"""
from __future__ import annotations

QUESTIONS = [
    {"id": "focus", "kind": "research",
     "text": "What area do you work in, and what question are you most trying to answer right now?"},
    {"id": "proud", "kind": "research",
     "text": "Describe a project you are proud of. What made it good research, in your view?"},
    {"id": "trust_own", "kind": "research",
     "text": "When one of your experiments gives a striking result, what do you check before you believe it?"},
    {"id": "abandon", "kind": "research",
     "text": "When do you drop a research direction? Describe a time you did, or a time you stayed too long."},
    {"id": "control_realism", "kind": "research",
     "text": "How do you weigh a clean, controlled setup against one that looks like real deployment? "
             "Give an example if you can."},
    {"id": "many_vs_few", "kind": "research",
     "text": "Would you rather run one careful experiment or many quick ones? What decides it for you?"},
    {"id": "disagree", "kind": "research",
     "text": "What is a common view in your field that you disagree with, and why?"},
    {"id": "trust_others", "kind": "research",
     "text": "What makes you trust, or distrust, someone else's paper?"},
    {"id": "resources", "kind": "research",
     "text": "How do you decide how much time, compute or money a question deserves?"},
    {"id": "novelty", "kind": "research",
     "text": "How do you feel about following up on established results versus starting something nobody has tried?"},
    {"id": "decisions_life", "kind": "other",
     "text": "Outside research, how do you make big decisions (a move, a purchase, a career change)?"},
    {"id": "hobbies", "kind": "other",
     "text": "What do you do for fun, and what do you like about it?"},
]

BY_ID = {q["id"]: q for q in QUESTIONS}
