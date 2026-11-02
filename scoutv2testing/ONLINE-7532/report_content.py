# ONLINE-7532 test-results report content. Built by ../make_test_results_docx.py ONLINE-7532

title = doc.add_paragraph()
run = title.add_run("ONLINE-7532: Suggest Standards — QA Test Results")
run.bold = True
run.font.size = Pt(18)
run.font.color.rgb = NAVY
sub = doc.add_paragraph()
run = sub.add_run("Scout AI standards suggestions for a teacher's own customized-content questions")
run.font.color.rgb = GREY

doc.add_heading("Summary", level=1)
table([1.6, 4.9], ["Item", "Detail"], [
    ["Ticket", "ONLINE-7532"],
    ["Environment", "dev2 (branch ONLINE-5385_scout_ai_integration, swo-3.0 + rag)"],
    ["Account", "Teacher account with the AI feature flag on"],
    ["Page", "Teacher → Classroom → Customized Content → Edit View (question list)"],
    ["Date", "29 Sep 2026"],
    ["Overall result", "PASS: UI 6/6, API 15/15, chat information asks 3/3 returned no AI suggestion. 1 finding: the standard lookup misses standards the week itself links (see Findings)."],
])

doc.add_heading("UI results", level=1)
table([0.35, 2.3, 3.05, 0.8], ["#", "Scenario", "Observed", "Result"], [
    ["1", "Suggest Standards shown on the question list when a question has no standard",
     "The \"Suggest Standards\" button (with Scout's mark) appears above the list", "PASS"],
    ["2", "Educational question gets a suggestion from the state catalogue",
     "\"Match each type of source to an example of it.\" → 4.19(A), a Texas standard, with its description and a "
     "short reason", "PASS"],
    ["3", "Disclaimer shown with the suggestion set",
     "\"Suggested by AI. It can make mistakes, so please review before accepting.\" shown under the button", "PASS"],
    ["4", "Teacher controls each suggestion",
     "Accept and Dismiss on each suggestion, plus \"Accept All (1)\"; nothing is attached until clicked", "PASS"],
    ["5", "Non-curriculum question gets no suggestion",
     "\"Which penguin is a chef?\" → no standard; list note \"No Studies Weekly standard matches these "
     "questions…\" and the per-question reason", "PASS"],
    ["6", "Teacher can still attach a standard by hand",
     "\"+ Attach Standard\" stays on every question; the normal flow is not blocked", "PASS"],
])

doc.add_heading("API results", level=1)
p = doc.add_paragraph("Run with ONLINE-7532-api-tests.sh against dev2 using the teacher's own token (Texas teacher, "
                      "grade 4 classroom). Every call is read-only; the rag checks fail validation before any model call.")
doc.add_heading("Laravel: POST /api/ai/standards/candidates", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["Guest (no token)", "401", "Unauthenticated.", "PASS"],
    ["search_text missing", "422", "The search text field is required.", "PASS"],
    ["classroom_id not a UUID", "422", "The classroom id must be a valid UUID.", "PASS"],
    ["grade 13", "422", "The grade must be between 0 and 12.", "PASS"],
    ["assignment_id 0", "422", "The assignment id must be at least 1.", "PASS"],
    ["Unknown classroom", "404", "Classroom not found.", "PASS"],
    ["Chat-style ask, grade 4, no classroom", "200", "state TX, grade 4, social studies + science candidates", "PASS"],
    ["Teacher's own classroom", "200", "state TX, grade 4, science + social studies candidates", "PASS"],
])
doc.add_heading("rag: POST /assistant/v2/standards/suggest", level=2)
table([2.9, 0.7, 2.1, 0.8], ["Check", "Status", "Response", "Result"], [
    ["No questions", "422", "Send at least one question.", "PASS"],
    ["31 questions (cap is 30)", "422", "Send at most 30 questions at a time.", "PASS"],
    ["Duplicate ref", "422", "Each question ref must be unique.", "PASS"],
    ["Empty question text", "422", "Every question needs a ref and its text.", "PASS"],
    ["Question over 2000 characters", "422", "A question may be at most 2000 characters.", "PASS"],
    ["6th request within a minute (rate limit)", "429",
     "You're moving fast! Scout can take 5 standards suggestion requests a minute. Please try again in 27 seconds.",
     "PASS"],
    ["Body is not JSON", "400", "The request couldn't be read. (deployed front door, same for every endpoint)",
     "PASS"],
    ["assignment_id not a number", "422", "assignment_id must be a number.", "PASS"],
])
doc.add_heading("Not covered yet", level=2)
table([4.6, 1.1, 0.8], ["Check", "Expected", "Result"], [
    ["Student token", "403", "Not covered"],
    ["Admin who is not a teacher", "403", "Not covered"],
    ["Another district's / school's classroom", "403", "Not covered"],
    ["Another teacher's customized content", "403", "Not covered"],
    ["Teacher without the AI flag: no button, no request; route hidden", "404", "Not covered"],
    ["35 questions in the UI: one request carrying the first 30", "See test plan", "Not covered"],
])

doc.add_heading("Chat: information asks (no AI suggestions)", level=1)
doc.add_paragraph("Asked in the SWO Assistant on publication 568 (Week 1: I Am a Member of a Community). The ticket "
                  "requires that an information ask is answered only from SWO data and never returns AI suggestions.")
table([2.3, 3.4, 0.8], ["Ask", "Observed", "Result"], [
    ["Which standards does this week cover?",
     "Answered from the week's Teacher Resources: TX K.13(C), K.14(C), K.14(D), K.8(A). No suggestion card, no "
     "disclaimer, nothing presented as an AI suggestion.", "PASS"],
    ["What articles are aligned to TX K.13(C)?",
     "No AI suggestion. Says nothing in the materials is linked to K.13(C) and shows a search result (TX WB b.13.B, "
     "Health grade 3) while stating it is not an alignment.", "PASS"],
    ["What articles are aligned to TX K.14(D)?",
     "No AI suggestion. Same pattern: \"Not in this publication\"; shows TX WB b.14.D (Health grade 4) as not a "
     "match.", "PASS"],
])
doc.add_heading("Chat: explicit suggestion ask", level=1)
table([2.3, 3.4, 0.8], ["Check", "Observed", "Result"], [
    ["Ask: \"Suggest standards for this question: How did rivers shape where early settlers lived?\"",
     "A \"Suggested standards\" card is shown", "PASS"],
    ["Disclaimer in chat", "The card opens with \"Suggested by AI. It can make mistakes, so please review before "
     "accepting.\" (shown with literal underscores, see Findings)", "PASS"],
    ["Code from the teacher's state catalogue",
     "\"From the TX standards in the Studies Weekly catalogue\": 4.7(A), grade 4, settlement and geographic "
     "factors, with a reason", "PASS"],
    ["Not presented as a Studies Weekly alignment", "Reply says \"a suggestion, not an official Studies Weekly "
     "alignment\"", "PASS"],
    ["Reply never says the standard was added", "Reply says \"I've added an AI-suggested standard…\"", "FAIL"],
])

doc.add_heading("Chat: declines", level=1)
table([2.3, 3.4, 0.8], ["Ask", "Observed", "Result"], [
    ["Give me Common Core standards for fractions",
     "Says Common Core is not in the catalogue and offers the teacher's Texas standards instead. No CCSS codes.",
     "PASS"],
    ["Suggest standards for: remind me to call Jamie's mom at 5",
     "Declined as a personal reminder; offers suggestions for a curriculum topic instead. No codes.", "PASS"],
])

doc.add_heading("Findings", level=1)
doc.add_heading("1. Standard lookup contradicts the week's own standards", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Title", "Standard lookup says no content is linked to K.13(C) / K.14(D), but the week lists both"],
    ["Severity", "Medium: the answer is wrong, but no AI suggestion is made and nothing is written"],
    ["Steps", "1. Open publication 568, Week 1, ask \"Which standards does this week cover?\" → lists TX K.13(C) "
              "and K.14(D). 2. In a new chat on the same publication, ask \"What articles are aligned to TX "
              "K.13(C)?\" (and K.14(D))."],
    ["Expected", "Week 1: I Am a Member of a Community (publication 568) is named as linked to each code."],
    ["Actual", "\"Not in this publication… I don't have anything in your Studies Weekly materials actually linked to "
               "K.13(C)\"; only an unrelated Health standard is shown."],
    ["Scope note", "The explicit-ask rule this ticket owns held (0 suggestions). The miss is in the standard lookup "
                   "(search_curriculum), so it may belong to a separate ticket. Cause not yet investigated."],
])

doc.add_heading("2. Chat reply says the suggested standard was \"added\"", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Medium: goes against the ticket's \"nothing is added without a click\" rule, in wording only"],
    ["Steps", "Open Scout chat and ask \"Suggest standards for this question: How did rivers shape where early "
              "settlers lived?\""],
    ["Expected", "The reply says the suggestions are in the card to review. The suggest_standards tool tells the model: "
                 "\"never that you added or attached them\" (rag commit 64099335)."],
    ["Actual", "\"I've added an AI-suggested standard for that question in the card above\". Nothing was saved; the "
               "wording is wrong. It also says \"above\" although the card is below the reply."],
    ["Scope note", "The rule is only an instruction to the model, and the model broke it. A fixed reply that "
                   "doesn't depend on the model would prevent this."],
])
doc.add_heading("3. Italic markers show as literal underscores in the suggestions card", level=2)
table([1.4, 5.1], ["Item", "Detail"], [
    ["Severity", "Low: cosmetic, but it is the disclaimer the ticket requires"],
    ["Actual", "\"_Suggested by AI. It can make mistakes, so please review before accepting._\" and each reason "
               "(\"_Question asks how a geographic factor…_\") show with the underscores."],
    ["Cause", "rag's card markdown (suggest_standards.py, _markdown) wraps the disclaimer and reasons in _…_, and "
              "frontend-v3's renderer (utils/safeMarkdown.ts) supports **bold** but no italics."],
    ["Fix options", "Emit plain text (or **bold** for the disclaimer) from rag, or add italic support to "
                    "safeMarkdown."],
])

doc.add_heading("Screenshots", level=1)
doc.add_heading("1. Suggestion returned for an educational question", level=2)
image("01-suggestion-returned.png", "Suggest Standards → 4.19(A) (Texas) with description, reason, Accept / Dismiss, Accept All (1) "
               "and the AI disclaimer.")
doc.add_heading("2. No suggestion for a non-curriculum question", level=2)
image("02-no-match.png", "\"Which penguin is a chef?\" — no standard suggested; the list and the question both say why, and "
               "Attach Standard is still available.")

doc.add_heading("3. Chat: which standards does this week cover", level=2)
image("03-chat-week-standards.png", "Answered from the week's Teacher Resources: TX K.13(C), K.14(C), K.14(D), K.8(A). "
      "No suggestion card.", width=4.6)
doc.add_heading("4. Chat: articles aligned to TX K.13(C)", level=2)
image("04-chat-aligned-K13C.png", "No AI suggestion, but it says nothing is linked to K.13(C), which screenshot 3 "
      "lists for this week.", width=4.6)
doc.add_heading("5. Chat: articles aligned to TX K.14(D)", level=2)
image("05-chat-aligned-K14D.png", "Same pattern for K.14(D), also listed in screenshot 3.", width=4.4)

doc.add_heading("6. Chat: explicit suggestion ask", level=2)
image("06-chat-explicit-suggestion.png", "Suggested standards card with the disclaimer and TX 4.7(A). The reply says "
      "\"I've added\" (finding 2), and the underscores show literally (finding 3).", width=5.2)

doc.add_heading("7. Chat: Common Core ask", level=2)
image("07-chat-common-core.png", "Common Core declined; Texas standards offered instead.", width=5.2)
doc.add_heading("8. Chat: non-educational ask", level=2)
image("08-chat-non-educational.png", "Personal reminder declined; no standard suggested.", width=4.6)

doc.add_heading("Notes", level=1)
for text in (
    "Screenshots #3 and #5 on the Jira comment are the same image, so it appears once here.",
    "The suggested code 4.19(A) is a Texas code, matching the teacher's state catalogue (TX).",
    "Observation: rag's rate limit counts invalid requests too (it is checked before the body). The page never "
    "sends invalid requests, so this only affects direct API testing.",
    "Observation: the first Texas candidate has code \"1\" (a science strand heading, not a specific standard). "
    "If it is ever suggested, the teacher would see a chip reading \"1\".",
    "Observation: the Common Core reply refers to the teacher in the third person (\"this teacher's standards "
    "catalogue… their Texas state standards\") while talking to them. Wording only.",
    "Observation: dev2's 404 response includes the exception class and server file path (debug output on). "
    "Expected on dev, not on staging or production.",
):
    doc.add_paragraph(text, style="List Bullet")
