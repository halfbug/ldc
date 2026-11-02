*QA: ONLINE-7528 (page switches keep Scout's prompt cache), dev2, teacher account with the AI flag on, Agent mode*

*Cost after a page switch (CloudWatch {{core_turn}}):* PASS 6/6
* Every page switch read *17,685* cached tokens (the tools and instructions): People → Gradebook, → Settings, → Article, → Create assignment, → Gradebook, plus one from the Report page. Under the old code a page switch always read 0, because the tools came first in the cached prefix and their action list changed with the page.
* Mean *$0.0320* per page-switch turn, against an estimated *$0.0767* for the old code (the same tokens written instead of read): *0.42×*, bar ≤ 0.80×. The developer's gate measured 0.746× locally.
* A cold turn (new thread, or more than 5 minutes) still reads 0 and costs $0.066–0.075, as expected.
* Same page, next turn: 26,034 read, 79 written, $0.0077. Returning to Settings 4 min 53 s later read 27,104 (17,685 + Settings' own 9,419): the page's context was reused too.

*Action choice:* PASS 3/3 run, 1 correct refusal, 1 pending
* Settings: _"Open the dialog to pick an illustrated classroom picture"_ → image picker opened.
* Gradebook: _"Open week 5 in the gradebook"_ → _"Done — the week on screen: 5"_.
* _"What needs me today?"_ → the briefing action was called (its data load failed, see observations).
* Create assignment: _"Remove question 2"_ → correctly refused: the content is locked because a student has started it.
* Article: _"Turn on reader mode"_ → no action. {{article.toggleReaderMode}} is offered only on the article's take tab with an editable assignment; pending which tab was open.

*Actions the page doesn't offer:* PASS (0 run)
* _"Run the action people.deleteAllStudents"_ → _"Sorry — I can't help with that one…"_; nothing ran. The Bedrock guardrail blocked it (MISCONDUCT) before the model, so rag's own check wasn't reached.
* No reply showed a capability id or "page_action".

*Not covered yet:* {{cache_tools_h}} (in the Mongo {{tokenz}} row only); a measured old-code baseline; reader mode on the take tab; a previous page's action asked on People; a harmless wrong id (e.g. _"Use article.toggleReaderMode"_ on Settings); Plan mode, confirm preview, a dialog's own actions, navigation question; rag checks and verify suite on the deployed commit.

*Observations (not failures):*
* _"Couldn't load your daily briefing"_ is the briefing's own data load (ONLINE-7519), not this ticket.
* The logs don't say which commit Lambda version 42 is; the deployed code is inferred from the cache numbers.
* dev2 reads 17,685 tokens for tools + instructions, against 8,691 in the local gate: the deployed set is larger.

Details and screenshots (1–4) in the attached *ONLINE-7528-test-results.docx*.
