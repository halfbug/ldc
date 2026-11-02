*QA: ONLINE-8093 (Scout release 2), local stack on ONLINE-5385_scout_release_2 (swo 41ace7e971, rag de38e41b), utteacher / utdistrictadmin / utschooladmin, automated Playwright run*

*Teacher Scout:* PASS 5/5
* Chat list loads with no thread errors.
* _"Write a short lesson plan for my students about reading a map."_ → answered; one generated title from {{POST /assistant/thread}}; no student name in it; no "K-12".
* History article _"War in the Americas"_ (French and Indian War): _"Make a lesson plan on this article."_ → lesson plan written, *no content check*.
* Stop before the first token → _"You stopped this answer before it started."_
* Search your chats → the opened chat is highlighted and scrolled into view in the sidebar.

*Admin Scout (Insights):* PASS 6/6
* District and School Insights open with figures; *Ask Scout About These Figures* offered.
* Questions go through {{/assistant/v2/admin/turn}} (200); the district answer covers the district, the school answer only the admin's school.
* Reopening a chat and asking again works with no _"I couldn't find that conversation."_ (the chat was the admin's own, so the new-chat path wasn't exercised).

*API (Laravel api/ai):* PASS 14/15
* 401 guest; teacher credits 200; teacher on {{admin/context}} 403; school admin credits 404 and {{admin/context}} 200.
* {{POST stats}} over 512 KB → 422 _"may not be larger than 512 KB"_.
* All 10 removed routes → 404 (generate/question, article/difficulty, adapt, random-article, credits/purchase, credits/expire, feedback, credits/packages, user/credits/redeem, search-index/1).
* The 1 failure: {{utdistrictadmin}} also holds the teacher role, so credits answer 200. Not a defect.

*Findings:* none from this run (code-review findings are on the MRs).

*Not covered yet:* gateway and Function URL checks (no API Gateway locally); flag-off teacher; old pre-release chat (no v1 chats locally); chip-started chat continued by typing; manual cases 5-8, 11, 13, 19, 25, 27-29.

*Observations (not failures):*
* Local setup: {{FEATURE_FRONTEND_AI_ADMIN_ASSISTANT = true}} added to backend/.env; no local queue worker, so the Insights figures job was run once by hand.
* One early teacher turn failed with "The AI service returned an error" (ref 90385ded-bd58-4a08-89c9-7704ec9b0c74, model_error, 0 model calls); not reproduced.
* A reopened stopped-before-start answer shows only "Stopped"; the sentence isn't kept.

Attached: {{ONLINE-8093-test-results.docx}} (screenshots 01-10).
