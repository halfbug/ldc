# ONLINE-8093 test-results report content. Built by ../make_test_results_docx.py ONLINE-8093

title = doc.add_paragraph()
run = title.add_run("ONLINE-8093: Scout Release 2 — QA Test Results")
run.bold = True
run.font.size = Pt(18)
run.font.color.rgb = NAVY
sub = doc.add_paragraph()
run = sub.add_run("Cleanup, guardrail, write_artifact, LangChain removal and round 2 tech debt; teacher, district admin "
                  "and school admin, end to end")
run.font.color.rgb = GREY

doc.add_heading("Summary", level=1)
table([1.6, 4.9], ["Item", "Detail"], [
    ["Ticket", "ONLINE-8093 (swo !6354, rag !101)"],
    ["Environment", "Local stack: swo-3.0 41ace7e971 and rag de38e41b (both ONLINE-5385_scout_release_2), "
                    "frontend-v3 https://localhost:3002/beta, Laravel :3001, rag ai_assistant :8002 (FastAPI, "
                    "no API Gateway), real Bedrock"],
    ["Accounts", "utteacher (teacher), utdistrictadmin (district admin), utschooladmin (school admin), seeded "
                 "local accounts"],
    ["Pages", "Teacher: Classrooms and an article page (Week 25: The French and Indian War). Admin: District "
              "Insights and School Insights"],
    ["How", "Automated Playwright suite ~/ldc/e2e (1.63.0, Chromium), run with ./run.sh --project=api and "
            "--project=ui"],
    ["Date", "26 Oct 2026"],
    ["Overall result", "PASS: UI 11/11 run (2 not covered), API 14/15 run (1 fails on a multi-role account, "
                       "not a defect; 4 not covered: no gateway / Function URL locally, no flag-off account). "
                       "0 defects from this run; 3 observations."],
])

doc.add_heading("UI results", level=1)
doc.add_paragraph("Each row is one Playwright test; real Scout turns were sent (E2E_AI_TURNS=1).")
table([0.45, 2.2, 3.05, 0.8], ["#", "Scenario", "Observed", "Result"], [
    ["2", "Sidebar loads with no errors",
     "Chat list loads (POST /assistant/thread/listing 200), no 4xx/5xx on any thread request. Locally rag is "
     "called directly, so the /v3 path check was off (E2E_EXPECT_V3=0)", "PASS"],
    ["1, 3, 9", "Plain turn, one title, no student name, no \"K-12\"",
     "\"Write a short lesson plan for my students about reading a map.\" → reply builds a set from \"Models of the "
     "World\"; one POST /assistant/thread after the turn returned the generated title; no \"Student N\" in it; "
     "no \"K-12\" or \"content check\" in the reply", "PASS"],
    ["4", "History article not stopped by the content check",
     "On \"War in the Americas\" (French and Indian War): \"Make a lesson plan on this article.\" → \"Your lesson "
     "plan is ready. Grade 4\" with a Lesson Plan card; no content-check text anywhere", "PASS"],
    ["15", "Stop before the first token",
     "Stop pressed straight after Send → \"You stopped this answer before it started.\" with Stopped and Retry",
     "PASS"],
    ["14", "Chat opened from search is revealed in the sidebar",
     "Search your chats → \"Water\" → 4 results; opening the last one highlights its row and scrolls it into view",
     "PASS"],
    ["16", "District Insights opens; Ask Scout offered",
     "District Insights with figures (3 of 12 teachers, 97% from 736 results); Ask Scout About These Figures shown",
     "PASS"],
    ["16", "District question goes through the admin door",
     "POST /assistant/v2/admin/turn 200; reply lists Utah School District 1 classes with no scored assessment; "
     "scope chip \"Insights · 8 weeks · All grades · All schools\"", "PASS"],
    ["17", "School Insights opens; Ask Scout offered",
     "School Insights with figures (1 of 7 teachers, 99% from 672 results) and the Classes table", "PASS"],
    ["17", "School question goes through the admin door",
     "POST /assistant/v2/admin/turn 200; reply limited to the admin's school; scope chip without a School filter",
     "PASS"],
    ["18", "Reopened chat then a new question (district)",
     "Turn 200 and no \"I couldn't find that conversation.\" The reopened chat was the admin's own, so the "
     "new-chat branch (admin_can_continue = false) wasn't exercised", "PASS"],
    ["18", "Reopened chat then a new question (school)", "Same as above", "PASS"],
])

doc.add_heading("API results", level=1)
doc.add_paragraph("Run with ~/ldc/e2e --project=api against the local Laravel. Read-only; the one POST fails "
                  "validation, so nothing is written.")
doc.add_heading("Laravel: api/ai", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["Guest on GET user/credits", "401", "Unauthenticated", "PASS"],
    ["Teacher GET user/credits", "200", "credit, user_id, publication_ids, raised_spend_cap", "PASS"],
    ["Teacher GET admin/context", "403", "Forbidden (can:ai-admin-insights)", "PASS"],
    ["School admin GET user/credits / admin/context", "404 / 200", "Teacher-only credits hidden; admin context "
     "returned", "PASS"],
    ["District admin GET user/credits / admin/context", "200 / 200",
     "utdistrictadmin also holds the teacher role, so credits answer 200 (see Notes)", "FAIL (test assumption)"],
    ["POST stats with a response over 512 KB", "422", "The response field may not be larger than 512 KB.", "PASS"],
    ["10 removed routes: generate/question, article/difficulty, adapt, random-article, credits/purchase, "
     "credits/expire, feedback, credits/packages, user/credits/redeem, search-index/1", "404 ×10",
     "Not Found", "PASS"],
])
doc.add_heading("Not covered yet", level=2)
table([4.6, 1.1, 0.8], ["Check", "Expected", "Result"], [
    ["Gateway: unprefixed /assistant/*, /v3/generate, /v3/generate-from-topic gone; /v3 thread route answers "
     "(local stack has no API Gateway)", "404 / 400", "Not covered"],
    ["Function URL: no token, path outside /assistant/v2/, teacher on the admin door (local FastAPI has no "
     "Function URL front door)", "401 / 404 / 403", "Not covered"],
    ["Teacher without the AI flag (no such local account)", "404", "Not covered"],
    ["#12 old pre-release chat opens with its messages (utteacher has no v1 chats locally; "
     "core_legacy_threads empty)", "Messages shown", "Not covered"],
    ["#10 chip-started chat continued by typing (no chip label chosen)", "No 409", "Not covered"],
    ["Manual cases: 5-8 guardrail/shortcut/plan parsing, 11 chip during a typed turn, 13 old chip thread, "
     "19 exports, 25 throttles, 27 single session, 28 fixed apology, 29 docs walk-through", "See test plan",
     "Not covered"],
])

doc.add_heading("Findings", level=1)
doc.add_paragraph("No defect was found in this run. The code-review findings for both MRs are in "
                  "mr-review-comments.md and are not repeated here.")

doc.add_heading("Screenshots", level=1)
doc.add_heading("1. Teacher: lesson plan reply (cases 1, 3, 9)", level=2)
image("01-teacher-lesson-plan.png", "Scout builds a map-reading set from \"Models of the World\" and turns it into a "
      "short lesson plan. The chat is in the sidebar under Today.")
doc.add_heading("2. Teacher: chat list loads (case 2)", level=2)
image("02-teacher-sidebar.png", "Sidebar with earlier chats, including generated titles such as \"Classrooms: "
      "Utah Capital…\" and \"Lesson Plan: War in the A…\".")
doc.add_heading("3. Teacher: history article not blocked (case 4)", level=2)
image("03-history-article.png", "Week 25: The French and Indian War, \"War in the Americas\". The lesson plan is "
      "written and no content check appears.")
doc.add_heading("4. Teacher: Stop before the first token (case 15)", level=2)
image("04-stop-before-first-token.png", "\"You stopped this answer before it started.\" with Stopped and Retry.")
doc.add_heading("5. Teacher: search your chats (case 14)", level=2)
image("05-search-results.png", "Search for \"Water\" lists four chats.")
doc.add_heading("6. Teacher: chat from search revealed (case 14)", level=2)
image("06-search-reveal.png", "The opened chat is highlighted at the bottom of the sidebar. Its stopped answer "
      "shows only \"Stopped\" (see Notes).")
doc.add_heading("7. District admin: District Insights (case 16)", level=2)
image("07-district-insights.png", "Figures ready after the queued figures job ran; Ask Scout About These Figures "
      "enabled.")
doc.add_heading("8. District admin: Scout answer (case 16)", level=2)
image("08-district-admin-reply.png", "Admin door answer: there is no assignment pacing in the data, so it lists "
      "classes with no scored assessment in the window.")
doc.add_heading("9. School admin: School Insights (case 17)", level=2)
image("09-school-insights.png", "School figures and the Classes table, no School filter.")
doc.add_heading("10. School admin: Scout answer (case 17)", level=2)
image("10-school-admin-reply.png", "Answer limited to the admin's school; scope chip \"Insights · 8 weeks · All "
      "grades\".")

doc.add_heading("Notes", level=1)
for text in (
    "Local setup needed for this run: FEATURE_FRONTEND_AI_ADMIN_ASSISTANT = true added to backend/.env (then "
    "config:clear), so the admin accounts get admin Scout; the one queued BuildAdminDistrictFigures job was "
    "processed with queue:work --queue=report --stop-when-empty (no queue worker runs locally, so Insights "
    "otherwise stays on \"Preparing Figures\" and Ask Scout stays disabled).",
    "The browser runs in Docker and reaches the host's rag on :8002 through a port forward in run.sh "
    "(E2E_FORWARD_PORTS=8002).",
    "Observation: utdistrictadmin holds both the district admin and the teacher roles (role ids 49 and 50), so "
    "GET api/ai/user/credits answers 200 for it. The first run answered 404 for the same account, most likely "
    "from the cached roles memo (User::getRoles). Not part of this ticket.",
    "Observation: one early teacher turn failed with \"The AI service returned an error\" (reference "
    "90385ded-bd58-4a08-89c9-7704ec9b0c74; telemetry error_code model_error, 0 model calls, 11 s). Every later "
    "turn completed in about 3 s, and Bedrock answered from the same credentials, so it wasn't reproduced.",
    "Observation: reopening a chat whose answer was stopped before it started shows an empty bubble with "
    "\"Stopped\"; the sentence \"You stopped this answer before it started.\" is not kept (screenshot 6).",
    "Observation: a \"Meet Scout\" tour dialog opens on an account's first Scout use and covers the window; the "
    "suite dismisses it with Maybe Later.",
):
    doc.add_paragraph(text, style="List Bullet")
