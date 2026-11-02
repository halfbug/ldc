# Scout release 2 (ONLINE-5385_scout_release_2) test-results report. Built by ../make_test_results_docx.py SCOUT-RELEASE-2

title = doc.add_paragraph()
run = title.add_run("Scout Release 2 — QA Test Results by Ticket")
run.bold = True
run.font.size = Pt(18)
run.font.color.rgb = NAVY
sub = doc.add_paragraph()
run = sub.add_run("swo !6354 and rag !101: round 2 tech debt, the ONLINE-8093 cleanup and the features on the branch, "
                  "tested end to end as a teacher, a district admin and a school admin")
run.font.color.rgb = GREY

doc.add_heading("Summary", level=1)
table([1.6, 4.9], ["Item", "Detail"], [
    ["Tickets", "ONLINE-5385, 7494, 7761, 7767, 7806, 7854, 7857, 7970, 8027, 8050–8064, 8093, 8095"],
    ["Environment", "Local stack on the release heads: swo-3.0 f556f63883 (frontend-v3 https://localhost:3002/beta, "
                    "Laravel :3001) and rag 24e95372 (ai_assistant, real Bedrock) with the dev guardrails: strict "
                    "z6mtpcbzm5x1 v16 plus curriculum u5k53i63fu9b v4, the same as dev2"],
    ["Accounts", "utteacher (Teacher A), utdistrictadmin, utschooladmin, cypressteacher (the other teacher for T5)"],
    ["How", "Playwright 1.63.0 suite in ~/ldc/e2e/tests/release2 (30 tests: 4 API, 26 UI), plus rag's offline checks "
            "and the lock checks. Every screenshot was read against its expected result, not only the test status"],
    ["Date", "28 Oct 2026"],
    ["Overall result", "18 tickets pass in what was tested, 4 pass with a finding, 2 fail in part (ONLINE-7854 "
                       "slides, ONLINE-7761 lesson pack) and 3 couldn't be tested locally (ONLINE-8095, 7857, 7494). "
                       "8 findings (the slides block is the most serious), 4 observations."],
])

doc.add_heading("Results by ticket", level=1)
table([1.05, 3.05, 1.4, 1.0], ["Ticket", "What was checked", "Screenshots", "Result"], [
    ["ONLINE-8027", "Window minimize / restore / maximize / close / reopen; Shift+Enter, Enter sends, Send turns into "
                    "Stop; reply footer (Copy, thumbs); sidebar rename, pin, search, delete; What Scout Can Do and "
                    "Tours; edit an earlier question and resend", "1–9", "PASS (finding 3)"],
    ["ONLINE-8051", "New Chat while answering sends /v2/turn/cancel (200) and the new chat works; switching chats "
                    "while answering cancels with no reply in the wrong chat; Stop before the first token (earlier run)",
     "10–11", "PASS"],
    ["ONLINE-5385", "A second tab sending in a chat that is still answering gets \"Scout is still answering your last "
                    "message…\" as a plain reply, with no failure card; the first tab's answer is kept", "12–13",
     "PASS"],
    ["ONLINE-8050", "Double-clicking Approve sends one confirm (200) and the card shows Approved once", "14",
     "PASS (drift not covered)"],
    ["ONLINE-8057", "Declining a proposed change sends no confirm and the card shows Declined", "15–16", "PASS"],
    ["ONLINE-7970", "District Insights builds for 8 weeks in 15 s and a fresh 12-week window in 15 s, with no error",
     "17–18", "PASS"],
    ["ONLINE-8053", "catalog-search answers 200 thirty times, then 429; a District Summary CSV export downloads with "
                    "no rate-limit message; a second tab loads Scout", "19", "PASS"],
    ["ONLINE-8054", "A stats response over 512 KB and an action preview over the cap both answer 422", "—", "PASS"],
    ["ONLINE-8055", "The redeem route (and the other removed AI routes) answer 404", "—", "PASS"],
    ["ONLINE-7806", "District admin: What Scout Can Do lists the admin questions; \"Which schools need support?\" "
                    "answers through /assistant/v2/admin/turn. School admin asks on School Insights", "20–22",
     "PASS"],
    ["ONLINE-8060", "Three admin questions in a row all answer, with no limit message. The 11th-in-a-minute limit "
                    "is covered by rag's check_throttle (pass), not run in the browser", "23", "PASS"],
    ["ONLINE-7767", "Drawing question on the article's picture with a checklist: written. Hot Text: Scout says it "
                    "can't write Hot Text (parked by design, cd4e7c64). Water-cycle drawing with no article open: no "
                    "activities treated as articles, but this teacher has no water-cycle article locally", "24–26",
     "PASS for Drawing (finding 5)"],
    ["ONLINE-7854", "\"Make slides for this week.\" on a war article: \"The slides didn't generate\" (twice). "
                    "\"Make a lesson plan from this article's Studies Weekly plan\": a Weekly Plan card", "27–28",
     "FAIL (finding 1)"],
    ["ONLINE-7761", "\"Make a lesson pack: plan, worksheet and exit ticket\": PARTLY DONE: exit ticket written, "
                    "worksheet failed with Retry offered, plan not one of the parts", "29", "PARTIAL (finding 2)"],
    ["ONLINE-8093", "T1 chip then typing, no 409; T2 reload; T3 one POST /assistant/thread; T5 another teacher gets 404; "
                    "T6 two history articles × lesson plan + 5 questions; T7 three harmful asks blocked; T10 no "
                    "\"K-12\"; T12 levelling; removed routes 404", "30–39", "PASS (finding 4)"],
    ["ONLINE-8052, 8056", "Regression only: every turn in this session loaded teacher context and finished, with "
                          "no hang", "—", "PASS"],
    ["ONLINE-8059", "uv lock --check passes for the root and ai_assistant locks", "—", "PASS"],
    ["ONLINE-8061", "check_route_errors passes; every failure the UI showed was a plain sentence with a reference id",
     "35–37", "PASS"],
    ["ONLINE-8062", "The prune-cap check (deleted from the branch) passes against today's code: 0 failures", "—",
     "PASS (finding 6)"],
    ["ONLINE-8063, 8064", "check_client_reuse and the lease checks pass in run_checks.sh (113/113)", "—", "PASS"],
    ["ONLINE-8058", "frontend-v3/scripts/check-core-events.mjs still reads the deleted docs/ScoutCoreV2.md", "—",
     "FAIL (finding 7)"],
    ["ONLINE-8095", "No Mini Books category and no K–2 class in the local data", "—", "Not covered"],
    ["ONLINE-7857", "The local stack has no daily-usage table, so spend caps aren't counted locally", "—",
     "Not covered"],
    ["ONLINE-7494", "Production content export and sync configuration; nothing to test in a browser", "—",
     "Not covered"],
])

doc.add_heading("API and service checks", level=1)
doc.add_heading("Laravel api/ai (Playwright API project)", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["ONLINE-8054: POST stats, response over 512 KB", "422", "may not be larger than 512 KB", "PASS"],
    ["ONLINE-8054: POST actions/preview, params over 512 KB", "422", "Validation error", "PASS"],
    ["ONLINE-8055 / 8093: redeem, credits/purchase, adapt, generate/question, credits/packages, search-index/1",
     "404 ×6", "Not Found", "PASS"],
    ["ONLINE-8053: GET catalog-search ×32 in a minute", "200 ×30, then 429", "Too Many Attempts", "PASS"],
    ["ONLINE-8093 T5: cypressteacher reads utteacher's v2 thread", "404",
     "I couldn't find that conversation. (not_found)", "PASS"],
])
doc.add_heading("rag at 24e95372", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["tests/run_checks.sh (includes check_throttle, check_route_errors, check_client_reuse, check_stop)", "113/113",
     "all checks passed", "PASS"],
    ["uv lock --check (root and lambdas/ai_assistant)", "ok", "Resolved 68 / 81 packages", "PASS"],
    ["ONLINE-8062 check_prune_cap.py (restored from 9d89f178, run against today's code)", "0 failures",
     "A refused prune deletes nothing and exits 1; --force-large-prune runs", "PASS"],
])
doc.add_heading("Not covered yet", level=2)
table([4.6, 1.1, 0.8], ["Check", "Expected", "Result"], [
    ["ONLINE-8095: Scout finds Mini Books for a K–2 class and assigns one (needs dev2 data)", "MB readers", "Not covered"],
    ["ONLINE-7857: a teacher over $2.50 a week is stopped with the reset time (needs the usage table)", "Refused",
     "Not covered"],
    ["ONLINE-8050: drift: change the item in another tab, then approve the updated preview", "Approves once",
     "Not covered"],
    ["ONLINE-8060: the 11th admin turn in a minute (unit check passes)", "429", "Not covered"],
    ["ONLINE-8093 T4 old pre-release chats (no v1 chats locally), T8, T9 (articles 28215/28216), T11 Custom "
     "Lesson Plan form, T13 grading", "See QA guide", "Not covered"],
    ["Flag-off teacher (the local AI flag is environment-wide)", "No Scout", "Not covered"],
    ["Gateway and Function URL front doors (local rag is FastAPI only)", "See ONLINE-8093.md", "Not covered"],
])

doc.add_heading("Findings", level=1)
doc.add_heading("1. Slides for a history article are blocked by the strict guardrail (ONLINE-8093, ONLINE-7854)", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "High: the history-lesson fix the release ships does not cover slides; a war week gets no slides"],
    ["Steps", "Teacher → Week 25: The French and Indian War → \"War in the Americas\" → Scout: \"Make slides for "
              "this week.\""],
    ["Expected", "A slide deck (the curriculum guardrail profile, as for lesson plans and questions on the same page)."],
    ["Actual", "\"I'll put together a set of slides…\" then \"Hmm, that didn't go through\" / \"The slides didn't "
               "generate — sorry about that.\" Reproduced twice."],
    ["Cause", "rag log: the guardrail classifier labelled the ask OTHER, so the turn ran on the strict profile (C0), "
              "and the output was blocked with topic:Violence:BLOCKED (16:34:15 and 16:43:11). Lesson plans and "
              "questions on the same article were labelled CURRICULUM (profile R2) and answered."],
])
doc.add_heading("2. A lesson pack drops the plan, fails the worksheet and shares no objective (ONLINE-7761)", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Medium"],
    ["Steps", "On \"War in the Americas\": \"Make a lesson pack for this lesson: plan, worksheet and exit ticket. "
              "Grade 4, 45 minutes.\""],
    ["Expected", "Three parts sharing the plan's objective and vocabulary (AC2); a failed part leaves the others "
                 "intact with a retry (AC3)."],
    ["Actual", "Card \"PARTLY DONE\": exit ticket done; \"The worksheet could not be written; use Retry\". The "
               "stored pack (thread 25c1259d…) has parts_asked [worksheet, exit_ticket] (no plan), objective \"\" "
               "and vocabulary [], and the artifact saved as the worksheet holds the lesson plan text."],
    ["Scope note", "AC3 (retry offered) holds. AC1/AC2 do not for this ask. Not investigated further."],
])
doc.add_heading("3. Renaming a chat right after its first reply fails (pre-existing)", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Medium: the sidebar shows \"Whoops! Something went wrong. Retry Now\""],
    ["Steps", "New chat → ask anything → as soon as the reply finishes, rename the chat from the sidebar."],
    ["Actual", "PUT /assistant/thread answers 500: \"'307b05fb-…' is not a valid ObjectId\"."],
    ["Cause", "A new chat's row starts with a placeholder id (crypto.randomUUID() in useAiChat.ts titleNewThread) "
              "until POST /assistant/thread returns, which happens after the first reply. A rename in that window "
              "sends the placeholder. The same code is on master (ONLINE-6857, ONLINE-7535), so it is not a "
              "release-2 regression. rag also answers 500 where 404 fits."],
])
doc.add_heading("4. After a reload, a typed answer to Scout's question is not shown (ONLINE-8093 T2)", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Low"],
    ["Steps", "On an article, click the chip \"Change the reading level\" (Scout asks which grade), type \"Make it "
              "shorter for grade 3\", then reload and reopen the chat."],
    ["Expected", "Both turns show exactly as seen (QA guide T2)."],
    ["Actual", "The rewrite is there, but the teacher's typed message is no longer shown as their own bubble."],
    ["Cause", "The typed text answered the paused question, so it is stored as an action_result (resolution "
              "answered), not as a user row, and the replay doesn't render it as a message."],
])
doc.add_heading("5. Hot Text is parked but ONLINE-7767 still promises it", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Low: scope, not a defect"],
    ["Actual", "\"I don't have a Hot Text question type available to create here\". hot_text is in PARKED_TYPES "
               "(rag cd4e7c64, 2026-10-09: failed its gate twice), so the tool doesn't offer it."],
    ["Fix", "Update the ticket's title and acceptance criteria to Drawing only, or un-park Hot Text after a passing "
            "gate."],
])
doc.add_heading("6. ONLINE-8062's only check was deleted from the branch", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Low: test coverage"],
    ["Actual", "rag 648067e3 (ONLINE-5385, \"Remove the finished experiment studies nothing reads\") removed "
               "experiments/content_sync/check_prune_cap.py. The prune cap code is still there, untested. The "
               "restored check passes against today's code."],
])
doc.add_heading("7. ONLINE-8058's event check reads a deleted doc", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Low"],
    ["Actual", "frontend-v3/scripts/check-core-events.mjs:21 still defaults to docs/ScoutCoreV2.md, which ONLINE-8093 "
               "deleted, so the check cannot run."],
])
doc.add_heading("8. A lesson-plan ask returns a weekly plan (ONLINE-7854)", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Low"],
    ["Actual", "\"Make a lesson plan from this article's Studies Weekly lesson plan\" → \"Your weekly plan is "
               "ready\" with a WEEKLY PLAN card for Week 25. Whether it follows the Studies Weekly plan's sequence "
               "was not checked."],
])

doc.add_heading("Screenshots", level=1)
SHOTS = [
    ("01-ONLINE-8027-01-window-open.png", "ONLINE-8027: Scout open beside the Classrooms page."),
    ("02-ONLINE-8027-02-window-maximized.png", "ONLINE-8027: maximized; restore and close followed."),
    ("03-ONLINE-8027-03-send-became-stop.png", "ONLINE-8027: Send turned into Stop while answering."),
    ("04-ONLINE-8027-04-reply-footer.png", "ONLINE-8027: reply footer with Copy and thumbs."),
    ("05-ONLINE-8027-05-sidebar-renamed-pinned.png", "ONLINE-8027: chat renamed \"QA rename …\" and pinned."),
    ("06-ONLINE-8027-06-sidebar-search.png", "ONLINE-8027: Search your chats finds the renamed chat."),
    ("07-ONLINE-8027-07-what-scout-can-do.png", "ONLINE-8027: What Scout Can Do with Tours."),
    ("08-ONLINE-8027-08-edited-and-resent.png", "ONLINE-8027: edited question (2/2, Edited) and its new answer."),
    ("09-ONLINE-8027-rename-race-whoops.png", "Finding 3: rename right after the first reply → \"Whoops! "
                                              "Something went wrong\"."),
    ("10-ONLINE-8051-01-new-chat-after-cancel.png", "ONLINE-8051: New Chat mid-answer; the new chat answers."),
    ("11-ONLINE-8051-02-switched-chat-clean.png", "ONLINE-8051: switched chat mid-answer; nothing leaked in."),
    ("12-ONLINE-5385-01-second-tab-still-answering.png", "ONLINE-5385: second tab gets \"Scout is still "
                                                        "answering…\" as a plain reply."),
    ("13-ONLINE-5385-02-first-tab-answer-kept.png", "ONLINE-5385: the first tab keeps its answer."),
    ("14-ONLINE-8050-01-approved-once.png", "ONLINE-8050: double-clicked Approve → Approved once (one confirm)."),
    ("15-ONLINE-8057-01-approval-card.png", "ONLINE-8057: the approval card before deciding."),
    ("16-ONLINE-8057-02-declined.png", "ONLINE-8057: Declined; nothing applied."),
    ("17-ONLINE-7970-01-default-window.png", "ONLINE-7970: District Insights, 8 weeks, built in 15 s."),
    ("18-ONLINE-7970-02-12-week-window.png", "ONLINE-7970: fresh 12-week window, built in 15 s."),
    ("19-ONLINE-8053-01-export-downloaded.png", "ONLINE-8053: District Summary CSV downloaded; no rate limit."),
    ("20-ONLINE-7806-01-admin-what-scout-can-do.png", "ONLINE-7806: What Scout Can Do on Insights."),
    ("21-ONLINE-7806-02-admin-answer.png", "ONLINE-7806: \"Which schools need support?\" answered from the figures."),
    ("22-ONLINE-7806-03-school-admin-answer.png", "ONLINE-7806: school admin's answer on School Insights."),
    ("23-ONLINE-8060-01-admin-questions-in-a-row.png", "ONLINE-8060: three admin questions in a row, all answered."),
    ("24-ONLINE-7767-01-drawing-on-picture.png", "ONLINE-7767: Drawing question with a picture background written."),
    ("25-ONLINE-7767-02-hot-text.png", "Finding 5: Hot Text is not offered (parked)."),
    ("26-ONLINE-7767-03-no-article-water-cycle.png", "ONLINE-7767: no activities treated as articles; no "
                                                     "water-cycle article in this teacher's publications."),
    ("27-ONLINE-7854-slides-failed.png", "Finding 1: \"The slides didn't generate\" on the war article."),
    ("28-ONLINE-7854-02-lesson-plan-from-sw-plan.png", "Finding 8: a lesson-plan ask returns a Weekly Plan card."),
    ("29-ONLINE-7761-01-lesson-pack.png", "Finding 2: lesson pack PARTLY DONE; worksheet failed."),
    ("30-ONLINE-8093-T1-chip-result.png", "ONLINE-8093 T1: the chip \"Change the reading level\" asks which grade."),
    ("31-ONLINE-8093-T1-chip-then-typed.png", "ONLINE-8093 T1/T12: typed \"Make it shorter for grade 3\" → "
                                              "rewritten for grade 3."),
    ("32-ONLINE-8093-T2-after-reload.png", "ONLINE-8093 T2 / finding 4: after reload the rewrite stays; the typed "
                                           "message is not shown."),
    ("33-ONLINE-8093-T6-history-28021.png", "ONLINE-8093 T6: \"War in the Americas\": lesson plan and 5 questions, "
                                            "no content check."),
    ("34-ONLINE-8093-T6-history-28121.png", "ONLINE-8093 T6: \"The Battle of Bunker Hill\": same."),
    ("35-ONLINE-8093-T7-harmful-1.png", "ONLINE-8093 T7: weapon instructions blocked (content check)."),
    ("36-ONLINE-8093-T7-harmful-2.png", "ONLINE-8093 T7: bullying message blocked."),
    ("37-ONLINE-8093-T7-harmful-3.png", "ONLINE-8093 T7: hiding self-harm blocked."),
    ("38-ONLINE-8093-T10-grades.png", "ONLINE-8093 T10: grades answer with no \"K-12\"."),
    ("39-ONLINE-8093-T12-levelling.png", "ONLINE-8093 T12: levelling asks for the grade (rewrite shown in 31)."),
]
for n, (file, caption) in enumerate(SHOTS, start=1):
    doc.add_heading(f"{n}. {file.split('-', 1)[1].rsplit('.', 1)[0]}", level=2)
    image(file, caption, width=5.2)

doc.add_heading("Notes", level=1)
for text in (
    "Guardrails: the local rag ran with the dev guardrails (strict v16, curriculum v4) on a second instance (:8003) "
    "that the browser reached through a port forward; the original :8002 instance (no guardrail) was left running.",
    "Correction to the 26 Oct ONLINE-8093 report: its history-article pass ran with no guardrail configured, so it "
    "proved nothing. This run repeats it with the dev guardrails (T6, pass).",
    "Local setup: FEATURE_FRONTEND_AI_ADMIN_ASSISTANT is set in backend/.env; a queue worker for the report queue "
    "is running in the API container so Insights figures build.",
    "Data created locally: an assignment of \"War in the Americas\" for Demo Classroom (due 6 Nov), saved copies "
    "in Customized Content, and test chats for utteacher and the admins.",
    "Observation: a blocked harmful ask shows the apology plus a red \"Didn't Finish\" card with Ask Again; Ask "
    "Again is pointless for a blocked ask.",
    "Observation: local spend caps are not counted (daily usage update fails with ResourceNotFoundException: no "
    "local DynamoDB table), so ONLINE-7857 can't be tested locally.",
    "Observation: Scout refuses general-knowledge asks (\"Name one planet\") as outside Studies Weekly content; "
    "by design.",
    "Observation: in T6, one internal call was blocked as Biometric Identification but the teacher still got the "
    "answer.",
):
    doc.add_paragraph(text, style="List Bullet")
