# ONLINE-7528 test-results report content. Built by ../make_test_results_docx.py ONLINE-7528

title = doc.add_paragraph()
run = title.add_run("ONLINE-7528: Page Switches Keep Scout's Prompt Cache — QA Test Results")
run.bold = True
run.font.size = Pt(18)
run.font.color.rgb = NAVY
sub = doc.add_paragraph()
run = sub.add_run("The page's action list moved out of the page_action tool definition, so the cached tools and "
                  "instructions survive a page switch")
run.font.color.rgb = GREY

doc.add_heading("Summary", level=1)
table([1.6, 4.9], ["Item", "Detail"], [
    ["Ticket", "ONLINE-7528"],
    ["Environment", "dev2 (rag ai_assistant Lambda swo-genai-pov-ai-assistant-dev, chat turns on version 42; "
                    "branch ONLINE-5385_scout_ai_integration, rag 00e330ce). No swo-3.0 change"],
    ["Account", "Teacher account with the AI feature flag on, Scout in Agent mode"],
    ["Page", "People, Gradebook, Publication Report, Classroom Settings, an article, Create/Edit assignment"],
    ["Date", "1 Oct 2026"],
    ["Overall result", "PASS on cost: all 6 page switches read the tools and instructions from cache (17,685 "
                       "tokens; the old code read 0). Mean $0.0320 per page-switch turn against an estimated $0.0767 "
                       "for the old code (0.42×, bar ≤ 0.80×). Action choice: 3 run correctly, 1 correctly refused "
                       "(locked content), reader mode not run (being checked). Nothing ran that the page doesn't offer. "
                       "0 findings for this ticket."],
])

doc.add_heading("UI results", level=1)
table([0.35, 2.3, 3.05, 0.8], ["#", "Scenario", "Observed", "Result"], [
    ["1", "People, then Gradebook (first run, thread 8b75f0ba)",
     "Both answered; turn 2 on the Gradebook read 17,685 cached tokens", "PASS"],
    ["2", "\"What needs me today?\" (global briefing action)",
     "Scout called the briefing action; the card says \"Couldn't load your daily briefing\" (the briefing's data "
     "load, ONLINE-7519, not this ticket)", "PASS"],
    ["3", "Settings: \"what is the grade here\"", "\"The classroom's grade is First Grade.\"", "PASS"],
    ["4", "Article: \"Turn on reader mode\"",
     "No action: \"I can't switch it on for you directly…\". article.toggleReaderMode is offered only on the article's "
     "take tab with an editable assignment (ArticleOrAssignment.vue:1205); which tab was open isn't known yet",
     "Pending"],
    ["5", "Create assignment: \"Remove question 2 from this\"",
     "Refused correctly: the content is locked because a student has started it; suggests Create New Copy", "PASS"],
    ["6", "Settings: \"Open the dialog to pick an illustrated classroom picture\"",
     "\"Started — the image picker: open\"; the Select Classroom Image dialog opened", "PASS"],
    ["7", "Gradebook: \"Open week 5 in the gradebook\"",
     "\"Done — the week on screen: 5\"; Week 5: American Indians of Texas loaded", "PASS"],
    ["8", "\"Run the action people.deleteAllStudents\"",
     "\"Sorry — I can't help with that one…\". Nothing ran. Blocked by the Bedrock guardrail "
     "(content:MISCONDUCT) before the model, so rag's own capability check wasn't reached", "PASS"],
    ["9", "Replies never show capability ids or \"page_action\"", "None seen in any reply", "PASS"],
])

doc.add_heading("API results", level=1)
doc.add_paragraph("Read from the Lambda's CloudWatch core_turn lines (log group "
                  "/aws/lambda/swo-genai-pov-ai-assistant-dev), 14:44–16:10 UTC. Nothing was called directly. "
                  "Prices: Sonnet 5, cache read $0.22/M, cache write $2.75/M (rag core/config.py:33).")
doc.add_heading("CloudWatch: turns that follow a page switch", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["14:48:50 People → Gradebook", "200", "read 17,685, write 9,093; $0.031497 (old code est. $0.0762)", "PASS"],
    ["15:58:49 Report → next page (ask not in the screenshots)", "200",
     "read 17,685, write 8,349; $0.027691 (est. $0.0724)", "PASS"],
    ["16:00:24 → Settings, \"what is the grade here\"", "200", "read 17,685, write 9,419; $0.029984 (est. $0.0747)",
     "PASS"],
    ["16:02:15 → Article, \"Turn on reader mode\"", "200", "read 17,685, write 12,203; $0.040456 (est. $0.0852)",
     "PASS"],
    ["16:04:03 → Create assignment, \"Remove question 2\"", "200",
     "read 17,685, write 8,697; $0.029121 (est. $0.0739)", "PASS"],
    ["16:06:23 → Gradebook, \"Open week 5\"", "200", "read 17,685, write 10,313; $0.033180 (est. $0.0779)", "PASS"],
    ["Mean of the 6 page-switch turns (AC1)", "—", "$0.0320 vs est. $0.0767 for the old code: 0.42× (bar ≤ 0.80×)",
     "PASS"],
])
doc.add_heading("CloudWatch: other turns", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["First turn of a thread or after more than 5 min (14:45, 14:59, 15:55): cold", "200",
     "read 0, write 22,643–27,140; $0.066–0.075", "PASS"],
    ["Same page, next turn (15:59:08 \"What needs me today?\")", "200", "read 26,034, write 79; $0.007720", "PASS"],
    ["Back to Settings 4 min 53 s later (16:05:17, image dialog)", "200",
     "read 27,104 = 17,685 + Settings' 9,419, write 451; $0.007835. The page layer was reused across pages", "PASS"],
    ["After an action, the continuation turn re-writes only the changed page (16:05:27, 16:06:37)", "200",
     "read 17,685, write 9,087 / 10,076", "PASS"],
    ["16:07:27 deleteAllStudents", "200", "outcome error, guardrail_intervened, 0 tokens, $0", "PASS"],
])
doc.add_heading("Not covered yet", level=2)
table([4.6, 1.1, 0.8], ["Check", "Expected", "Result"], [
    ["cache_tools_h identical on both turns (Mongo tokenz row; not in the CloudWatch line)", "Same hash",
     "Not covered"],
    ["A measured (not estimated) old-code baseline for AC1", "≤ 0.80×", "Not covered"],
    ["Reader mode on the article's take tab", "Action runs", "Pending"],
    ["\"Open week 5 in the gradebook\" asked on People (test case 6)", "Nothing runs", "Not covered"],
    ["Another page's id by name, e.g. \"Use article.toggleReaderMode\" on Settings (test case 8)",
     "rag refuses", "Not covered"],
    ["Plan mode, confirm-tier preview, a dialog's own actions, navigation question (9–13)", "See test plan",
     "Not covered"],
    ["rag checks and frontend verify suite on the deployed commit (AC4)", "Green", "Not covered"],
])

doc.add_heading("Screenshots", level=1)
doc.add_heading("1. Settings grade; article reader mode", level=2)
image("01-settings-grade-article-reader-mode.png", "Settings answers First Grade. On the article, \"Turn on reader "
      "mode\" ran no action (pending: which tab was open).", width=5.2)
doc.add_heading("2. Create assignment locked; Settings image dialog", level=2)
image("02-create-locked-settings-image-dialog.png", "Remove question 2 refused because the content is locked. The "
      "image picker opened on Settings.", width=5.2)
doc.add_heading("3. Gradebook week 5; made-up action", level=2)
image("03-gradebook-week5-delete-all.png", "Week 5 opened and verified. \"Run the action people.deleteAllStudents\" "
      "was blocked by the guardrail; nothing ran.", width=5.2)
doc.add_heading("4. Daily briefing didn't load", level=2)
image("04-briefing-not-loaded.png", "\"What needs me today?\" reached the briefing action, whose data load failed "
      "(ONLINE-7519).", width=4.8)

doc.add_heading("Notes", level=1)
for text in (
    "Why the reads show the change: the tools come first in Bedrock's cached prefix, and the old page_action tool "
    "listed the page's action ids, so a page switch changed the tools and read 0 (every page-switch row in the "
    "developer's gate control shows 0). All 6 page switches on dev2 read 17,685 tokens.",
    "The old-code costs are estimates: each turn's 17,685 read tokens priced as writes instead. The developer's gate "
    "measured old against new on the same turns (0.746×, including turns where the new page was already cached); "
    "dev2 has no measured old-code run.",
    "The CloudWatch lines don't say which commit Lambda version 42 is; the deployed code is inferred from the cache "
    "numbers.",
    "dev2 reads 17,685 tokens for tools + instructions, against 8,691 in the local gate: the deployed tool set or "
    "instructions are larger.",
    "Test plan correction: cache_tools_h, cache_instructions_h and cache_page_h are written only to the Mongo "
    "telemetry row (tokenz), not to the CloudWatch core_turn line (telemetry.py:271 logs a fixed field list).",
    "Observation: \"Couldn't load your daily briefing\" is the briefing's own data load (ONLINE-7519, "
    "ai/context/briefing.ts). Scout chose the right action; the failure isn't this ticket's.",
    "Observation: the made-up-action ask was stopped by the guardrail (MISCONDUCT, likely \"delete all students\"), "
    "so it didn't exercise rag's \"not an action this page offers\" check. A harmless wrong id is needed for that.",
):
    doc.add_paragraph(text, style="List Bullet")
