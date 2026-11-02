*QA: ONLINE-7532 (Suggest standards), dev2, teacher account with the AI flag on (Texas, grade 4 class)*

*UI (Customized Content → Edit View):* PASS 6/6
* *Suggest Standards* appears when a question has no standard.
* Educational question _"Match each type of source to an example of it."_ → suggested *4.19(A)* (Texas, the teacher's state) with its description and a short reason.
* AI disclaimer shown: _"Suggested by AI. It can make mistakes, so please review before accepting."_
* *Accept / Dismiss* on each suggestion and *Accept All (1)*; nothing is attached until clicked.
* Non-curriculum question _"Which penguin is a chef?"_ → no suggestion. The list and the question both say why.
* *+ Attach Standard* is still available; the normal flow isn't blocked.

*API:* PASS 15/15
* Laravel {{POST /api/ai/standards/candidates}}: 401 guest, 422 ×4 (missing search_text, bad classroom_id, grade 13, assignment_id 0), 404 unknown classroom, 200 for a chat-style ask and for the teacher's own classroom (state TX, grade 4).
* rag {{POST /assistant/v2/standards/suggest}}: 422 for an empty list, *31 questions (30 cap)*, duplicate ref, empty text, >2000 chars, non-numeric assignment_id; 400 for a non-JSON body.
* *Rate limit:* 6th request in a minute → 429 _"Scout can take 5 standards suggestion requests a minute…"_

*Chat, information asks:* PASS 3/3 (no AI suggestion on any)
* _"Which standards does this week cover?"_ → answered from the week's Teacher Resources (TX K.13(C), K.14(C), K.14(D), K.8(A)). No suggestion card.
* _"What articles are aligned to TX K.13(C)?"_ and _"…TX K.14(D)?"_ → no suggestion card; nearby search results are shown and stated not to be alignments.

*Chat, explicit suggestion ask:* PASS with 2 defects
* _"Suggest standards for this question: How did rivers shape where early settlers lived?"_ → *Suggested standards* card, opens with the disclaimer, "From the TX standards in the Studies Weekly catalogue": *4.7(A)* (grade 4, settlement and geographic factors) with a reason. The reply calls it "a suggestion, not an official Studies Weekly alignment".

*Chat, declines:* PASS 2/2
* _"Give me Common Core standards for fractions"_ → says Common Core isn't in the catalogue and offers Texas standards instead. No CCSS codes.
* _"Suggest standards for: remind me to call Jamie's mom at 5"_ → declined as a personal reminder. No codes.

*Findings:*
# *Chat reply says "I've added an AI-suggested standard…" (medium).* 
  Nothing is saved, but the tool tells the model "never that you added or attached them" (rag 64099335), and the ticket's rule is that nothing is added without a click. It also says "card above" although the card is below.
# *Literal underscores in the card (low).* 
The disclaimer and each reason show wrapped in visible underscores: rag's card markdown uses underscore italics, and frontend-v3's {{safeMarkdown.ts}} supports bold but not italics.
# *Standard lookup contradicts the week (medium, likely the lookup rather than this ticket):* 
on publication 568, the week-standards answer lists TX K.13(C) and K.14(D) for Week 1, but asking which articles are aligned to either code answers _"Not in this publication… I don't have anything … actually linked to K.13(C)"_. Expected: Week 1: I Am a Member of a Community is named. Cause not yet investigated.

*Not covered yet:* 403 for student / non-teacher admin / other district or school / other teacher's content; flag-off user; the 35-question UI run.

*Observations (not failures):*
* rag's rate limit also counts invalid requests. The page never sends invalid requests, so only API testing is affected.
* The first Texas candidate has code "1" (a science strand heading). If it is ever suggested, the chip would read "1".
* The Common Core reply refers to the teacher in the third person ("this teacher's standards catalogue… their Texas state standards"). Wording only.
* dev2's 404 response includes the exception and server file path (debug output on); fine for dev, not for staging or prod.

Details and screenshots (1–8) in the attached *ONLINE-7532-test-results.docx*.
