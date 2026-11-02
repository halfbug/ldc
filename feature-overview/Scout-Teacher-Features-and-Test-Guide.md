# Scout: What Teachers Can Do — Feature List and Test Guide

**As of:** 23 October 2026
**For:** QA, product, support, and anyone demoing Scout
**Source:** the 75 `[AI Project]` Jira tickets (see `Scout-Feature-Overview.md` for the engineering view)

Scout is the AI assistant inside Studies Weekly Online. A teacher opens it from the top bar and talks to it in plain words. This guide lists everything a teacher can do with Scout, gives example questions to type, and gives step-by-step tests for each feature.

---

## How to use this guide

Each feature has:

- **What the teacher can do:** the feature in plain words.
- **Where:** the page to start on.
- **Try asking:** example questions to type into Scout. Swap in your own class, student and publication names.
- **How to test:** steps to follow.
- **Expected result:** what should happen. If anything else happens, log a bug with the **thread id** (Scout's message menu → copy thread id) and the page URL.
- **Tickets:** the Jira tickets behind the feature.

**Status labels**

| Label | Meaning |
|---|---|
| ✅ Live | Built and passed QA. |
| 🧪 In QA | Built, ticket is in Testing. Test it, but expect rough edges. |
| 🔒 Hidden | Built and in production, but switched off for teachers until final QA (grading features, ONLINE-7865). Needs the grading flag. |
| 🏫 Admin | For district and school admins only. |

---

## Before you start

### Accounts and flags

| You need | Why |
|---|---|
| A **teacher** account on dev2 with `FEATURE_FRONTEND_AI_ASSISTANT` on | Every Scout feature is behind this flag. With it off, Scout must not appear at all. |
| `FEATURE_FRONTEND_AI_CUSTOM_LESSON_PLANS` on | Custom lesson plans, weekly plans, the plan part of lesson packs. |
| `FEATURE_PLANNING_CALENDAR` on | Yearly planning calendar. |
| `FEATURE_FRONTEND_AI_ASSISTED_GRADING` on | 🔒 Grading features (section J). |
| A **district admin** and a **school admin** account, district with `FEATURE_FRONTEND_AI_ADMIN_ASSISTANT` on | 🏫 Admin Scout (section K). |
| A teacher **without** the AI flag | To check non-AI users see no change. |

### Test data that makes the tests meaningful

- A teacher with **at least two active classes**, each with students and at least one publication.
- **Submitted work**: graded assessments over the last few weeks, some missing and late work, and some written (open response) answers waiting in Grade Now.
- One class whose **start and end dates are still the create-form defaults**, to test that Scout asks instead of guessing.
- At least one **drawing question** with submissions.
- The teacher's profile/classroom has a **grade and state** set (and one class where they are blank).

### Checks that apply to every test

Run these on any feature where they make sense. They are Scout's core promises.

1. **Student names never leave the browser.** Open DevTools → Network, send a question that names a student, and open the request to `/v2/turn`. You should see codes like `Student K7QF2M`, never a real name, username or password. The reply on screen shows the real name again.
2. **Nothing changes without approval.** Any change (assign, move, save, schedule, grade) must show a **confirmation card** first. Pressing **Not now** or closing it must change nothing.
3. **Evidence is shown.** Anything Scout says about a student or class comes with the numbers or work behind it, and a way to open that work.
4. **Honest "nothing found".** When nothing relevant exists, Scout says so. It does not pad the answer with unrelated items.
5. **Reopening a conversation** (Scout's history list) shows the same answers, cards and drafts.
6. **No-flag teacher sees nothing new.** Log in as the teacher without the AI flag and check the page looks as before.

---

## A. Getting started

### 1. Open Scout, move it, and keep it while you work ✅

**What the teacher can do:** Open Scout from any page, drag the window anywhere, and keep it open while moving around SWO.
**Where:** Any teacher page under `/beta/`.
**How to test:**
1. Click the Scout icon in the top bar.
2. Drag the Scout window by its header to another part of the screen.
3. Navigate to another page (for example, from Classrooms to an article).
4. Open a dropdown inside Scout (for example, *Question types* in the question form).

**Expected result:** The window opens, moves, and stays open with the same conversation after navigation. Scout's own dropdowns and dialogs always appear in front of the Scout window.
**Tickets:** ONLINE-6806, ONLINE-7584

### 2. The "Meet Scout" tour ✅

**What the teacher can do:** Take a short guided tour of Scout.
**How to test:**
1. Start the Meet Scout tour (first visit, or from Scout's help).
2. Step through with **Next/Back**, then with the **arrow keys**; press **Esc** to close.
3. Resize the window and scroll during a step.

**Expected result:** Each step highlights exactly one element, with the rest of the page dimmed. The highlight and popup move smoothly together and stay aligned when you resize or scroll. Esc closes the tour. The classroom intro tour is unchanged.
**Tickets:** ONLINE-7523

### 3. Ask about the page you are on ✅

**What the teacher can do:** Ask Scout about what is on screen without copying and pasting anything.
**Where:** Any page: an article, the table of contents, the gradebook, People, a report.
**Try asking:**
- "What is this page?"
- "Summarize this article."
- "Where is the vocabulary for this week?"
- "Who hasn't turned this in?" (article Grade tab)
- "Summarize how the class did." (article Grade tab)

**How to test:**
1. Open an article, ask "Summarize this article."
2. Open the article's **Grade** tab, ask "Who hasn't turned this in?"
3. Open the gradebook and ask "Which students are below 60%?"

**Expected result:** Answers come from what is on screen, with correct names and numbers. Scout never says "this page has no student data" on a page that clearly shows students.
**Tickets:** ONLINE-6857

### 4. Suggestion chips that fit the current step ✅

**What the teacher can do:** Click a suggestion chip instead of typing.
**How to test:**
1. Open **Create Classroom**. On step 1, check the chips (fill in details, suggest dates). Go to step 3 and check "Create the classroom" appears **only** there.
2. Open **Customized Content** create. Check the chips change between step 1 (instructions, due date), step 2 (add/generate questions) and step 3 (who gets it).
3. On an article, switch between tabs (Highlights, Grade).
4. Click every chip shown.

**Expected result:** Every chip acts on what is on screen. No chip offers a later step's action early. At most 5 chips show. Every chip works when clicked.
**Tickets:** ONLINE-7522

### 5. Conversation history, rename and feedback ✅

**What the teacher can do:** Reopen old conversations, rename them, and rate answers with thumbs up/down.
**How to test:**
1. Open Scout's **History** list, rename a conversation, reopen it.
2. On any answer, click **thumbs down**. Pick a reason (Not factually correct / Didn't follow instructions / Offensive/Unsafe / Other), type a comment (max 500 characters), submit.
3. As an admin, open **AI Playground → Reports → Feedback**. Open the negative feedback entry.

**Expected result:** The renamed conversation shows its new name and the same messages. The feedback is saved. The admin report shows the user, the prompt and the AI's reply, and Scout failed turns are listed with enough detail to reproduce.
**Tickets:** ONLINE-6282, ONLINE-6553, ONLINE-7495, ONLINE-7577

---

## B. Finding teaching content

### 6. Find articles, resources and media in plain words ✅

**What the teacher can do:** Describe what they need and get matching content from every publication they have, from any page.
**Where:** Any page.
**Try asking:**
- "Do I have anything on Rosa Parks?"
- "Something about how plants make food from sunlight, grade 4."
- "A video under 3 minutes about the water cycle."
- "Anything aligned to 4-LS1-1."
- "Which of my publications covers ecosystems?"
- "Find me an article about penguins." (it should return **articles**, not only media)

**How to test:**
1. Ask each question from a page that is **not** the publication's own page.
2. Ask for a topic your school has **no** content on (for example "photosynthesis" on a social-studies-only account).
3. Click a result card.

**Expected result:** Each result shows its type, grade, publication and a one-line reason it matched. Scout says where it searched. A topic with no content gets a clear "nothing found", not unrelated items. Content in a publication your school does not own is never shown as available. Clicking a result opens the right item or the right Search tab.
**Tickets:** ONLINE-7511, ONLINE-7507, ONLINE-6841

### 7. Find resources by publication, unit or week ✅

**What the teacher can do:** Ask for printables, assessments, rubrics, images, videos or audio for a specific week.
**Try asking:**
- "Find the weekly assessment for 4th Grade Social Studies, unit 2, week 3."
- "Printables for week 5."
- "Videos for week 3."
- "Find audio about Martin Luther King Jr."

**How to test:** Ask each question naming a real publication/unit/week from the test account, then open the results.
**Expected result:** Results come only from that week and are of the type asked for, or Scout clearly says none exist (for example, if there is no audio on the topic).
**Tickets:** ONLINE-7490

### 8. Preview videos, images, audio and PDFs inside the chat ✅

**What the teacher can do:** Watch, look at or listen to results without leaving Scout.
**How to test:**
1. Ask "Show me videos about volcanoes."
2. Play a video inline; click an image; play an audio clip; open a PDF/printable.
3. Ask for something that returns 20 results and click **Show more**.

**Expected result:** The first few results have rich previews; each type has its own label (Video, Image, Audio, PDF, Printable, Rubric, Assessment). Items without a thumbnail show an icon card. The chat stays responsive. The reply text summarises instead of repeating the list.
**Tickets:** ONLINE-7499

### 9. Build a teaching set ✅

**What the teacher can do:** Ask for a ready set of materials for a lesson, then swap pieces.
**Try asking:**
- "Build me a teaching set on the water cycle for grade 3."
- "Swap the video for something shorter."
- "Remove the worksheet."

**Expected result:** Items are grouped by type (with an organizer where one fits), each with its reason. Swapping or removing changes only that item.
**Tickets:** ONLINE-7511

### 10. Search from the Search page ✅

**What the teacher can do:** On the Search page, ask Scout to search and it runs the page's own search.
**How to test:**
1. Open the **Search** page and ask "Find videos about penguins."
2. Ask "What do we have on penguins?"
3. Go to a publication's table of contents and ask "Find videos about penguins."

**Expected result:** Step 1 runs the page search filtered to videos. Step 2 still gets Scout's own answer. On the table of contents, Scout answers as it normally does.
**Tickets:** ONLINE-7581

---

## C. Changing the reading level of an article

### 11. Level text: rewrite an article 1 or 2 grades lower ✅

**What the teacher can do:** Get an easier version of an article for students who need it.
**Where:** An article page (**Level text** button), or ask in chat.
**Try asking:**
- "Level this article down one grade."
- "Rewrite this for grade 2."

**How to test:**
1. Open a **grade 4** article. Click **Level text**. Check it offers grade 3 and grade 2. Pick 1 grade down.
2. Open a **grade 2** article: only grade 1 should be offered.
3. Open a **kindergarten** and a **grade 1** article: the button should not appear.
4. Open an **assessment** article and click Level text.
5. In Customized Content, add a Text block with pasted text and ask Scout to level it.

**Expected result:** The levelled text appears in Scout and keeps the article's vocabulary words. The original article does not change for students. On an assessment, a yellow warning appears before levelling. For pasted text with no known grade, Scout first asks which grade it is (K–8) and waits for an answer.
**Tickets:** ONLINE-7853, ONLINE-6301 (training to improve levelling, ONLINE-6300, is not started)

---

## D. Questions and assignments

### 12. Generate questions from an article (one or up to five) ✅

**What the teacher can do:** Write quiz questions from a chosen article, one at a time or as a set.
**Where:** Customized Content create/edit → "Save time with the AI Question Generator!" box, or ask in chat.
**Try asking:**
- "Make 5 questions on this week's article."
- "Write 3 multiple choice questions about Rules at School."

**How to test:**
1. Open the AI Question Generator form. Choose a grade (required), optionally a publication and topic, number of questions **1**, then **3**, then **5**, with one type and then several types.
2. Untick one question and click **Add**.
3. Use **+Add › Question** (single question) as before.
4. Reopen the conversation.

**Expected result:** The right number and types are generated, each multiple choice question has exactly one correct answer, and questions come from the chosen article. Only ticked questions are added, in order, and they match the cards. Single-question generation is unchanged. Scout says what it assumed (for example "Grade 3 (your usual), Texas standards (your profile)").
**Tickets:** ONLINE-6797, ONLINE-7567

### 13. Choose the depth of knowledge (DOK) mix 🧪

**What the teacher can do:** Ask for more recall or more reasoning questions.
**How to test:**
1. In the multi-question form, set **Depth of knowledge** to *Any*, then *Mostly recall (DOK 1)*, *Mixed (DOK 1–3)*, *Mostly reasoning (DOK 2–3)*, generating 5 questions each time.
2. In chat: "Make question 3 harder." / "Add a DOK 3 question."
3. Add the questions to the assignment and check the saved text.

**Expected result:** *Any* behaves like before. *Mixed* includes at least one DOK 1 and one DOK 2–3 question. Each card shows a DOK label, but the label is **not** added to the saved question text.
**Tickets:** ONLINE-7757

### 14. Drawing and Hot Text questions 🧪

**What the teacher can do:** Have Scout write Drawing and Hot Text questions too.
**How to test:**
1. Generate a set that includes **Drawing** and **Hot Text**.
2. Add them, save, and open the assignment as a student.

**Expected result:** Both save and look like hand-made blocks. Hot Text passages are word-for-word from the article and the answer key grades correctly. Drawing questions come with a model-answer checklist for the teacher and do not give away the answer.
**Tickets:** ONLINE-7767

### 15. Draft, check and reuse whole assignments ✅

**What the teacher can do:** Ask for a complete assignment, check it before assigning, or reuse an old one.
**Try asking:**
- "Create a 5-question exit ticket on Tools and Safety: two multiple choice, two short answer, one open response."
- "Add two harder questions at the end."
- "Check this quiz before I assign it."
- "Reuse my Mindsets quiz from last year and update it for this week's article."
- "Help me clean up my old test assignments."

**How to test:** Ask each, edit the draft, then assign it.
**Expected result:** The draft has a title, instructions, questions, answer keys, points and suggested standards, in the mix asked for. It is saved as a **draft only**; assigning shows a confirmation card. The check names each problem question and a fix, and never changes the assignment by itself. Including a drawing question tells the teacher it cannot get grading help yet.
**Tickets:** ONLINE-7514

### 16. Suggest standards for your own questions ✅

**What the teacher can do:** Get standards suggested for questions they wrote, and accept them in one click.
**Where:** Customized Content → edit view (a question with no standard), or ask in chat.
**How to test:**
1. Add a question with no standard, e.g. "Match each type of source to an example of it." Click **Suggest standards**.
2. Add a non-curriculum question, e.g. "Which penguin is a chef?", and suggest again.
3. Use **Accept**, **Dismiss** and **Accept all**.

**Expected result:** Suggestions are real codes from the teacher's state, each with a short reason, plus the note "Suggested by AI. It can make mistakes, so please review before accepting." Nothing is attached until accepted; an accepted standard looks like a hand-picked one. The non-curriculum question gets no suggestion, with a reason.
**Tickets:** ONLINE-7532

---

## E. Lessons and planning

### 17. Custom lesson plans and weekly plans ✅

**What the teacher can do:** Turn a Studies Weekly lesson plan into their own: class time, success criteria, standards and notes. Save, edit and print it.
**Where:** Publication → week resources → **Customize lesson plan / Plan this lesson**, or ask in chat. Saved plans live under the class's **Lesson plans** page.
**Try asking:**
- "Make a 45-minute lesson plan for this article."
- "Plan this week for my class."

**How to test:**
1. From a week's resources, open the lesson plan form. Set minutes, add a success criterion, pick standards, add a note. Generate.
2. Save, reopen from **Lesson plans**, edit, print.
3. Try an article that previously failed ("Activity 3: Waddle Leaders of Antarctica", Testing 6–8, Lesson 1).
4. Generate for a week that has a Studies Weekly lesson plan, and for one that has none.

**Expected result:** The plan fits the minutes and uses the article and Studies Weekly's own plan. Where a week has no SW lesson plan, Scout says it worked from the articles. Saved plans show the week number (for example "Week 18"). No raw Markdown symbols appear, and the grade comes from the article, not a guess.
**Tickets:** ONLINE-7404, ONLINE-7752, ONLINE-7854, ONLINE-7524

### 18. A lesson pack in one request ✅

**What the teacher can do:** Get a lesson plan, worksheet, exit ticket and slides together.
**Try asking:**
- "Make a lesson pack for this lesson: plan, worksheet, exit ticket and slides."
- "Make the exit ticket shorter." (refine one part)

**Expected result:** All four parts appear in one go (or Scout says how it is splitting the work), share the same grade and goal, and the worksheet and exit ticket use the plan's vocabulary. If one part fails, the others stay and a retry is offered. Refining one part changes only that part.
**Tickets:** ONLINE-7761

### 19. Lesson walkthrough slides from the article 🧪

**What the teacher can do:** Get a slide walkthrough built from the Studies Weekly article, to present in the existing walkthrough player.
**Try asking:**
- "Make a lesson walkthrough for this article."
- "Make slides for week 5."

**How to test:** Create from an article, from a week, and from chat. Edit slide text, reorder and delete slides. Present it at 1280×720 and full screen. Reopen the conversation.
**Expected result:** Every fact on a slide comes from the article. Edits survive reopening. It plays in the walkthrough player. Existing Studies Weekly walkthroughs are unchanged.
**Tickets:** ONLINE-7759

### 20. Where is my class? Plan the next weeks, catch up ✅

**What the teacher can do:** Ask where a class is compared with where it should be, get the next lesson, plan coming weeks, and rebuild the plan after lost time.
**Where:** Any page.
**Try asking:**
- "Where is my class compared with where it should be?"
- "Where are we in Science?"
- "Plan my next two weeks across Science and Well-Being."
- "We lost a week to testing. Rebuild the plan so we finish by June."
- "Help a student who was absent last week catch up."
- "I'm teaching photosynthesis tomorrow. I have 30 minutes. Help me prepare."

**How to test:**
1. Ask "Where is my class…" for a class with real dates.
2. Ask it for the class whose dates are still the defaults.
3. Ask for a replan and look at the proposal; press **Not now**, then ask again and approve.

**Expected result:** Scout states the expected week, the actual week and the next lesson. For the class with default dates, it **asks** for the first/last day instead of guessing. A replan shows each change with its reason and changes nothing until approved; applied changes can be undone. A prep pack fits the minutes given and links its sources.
**Tickets:** ONLINE-7515 (see the developer guide §11.5 for the full call sequence)

### 21. Yearly planning calendar ✅

**What the teacher can do:** Lay a publication's weeks onto real school dates, import the school calendar, and have Scout's pacing use it.
**Where:** Class publication page → **Plan the year**. Needs `FEATURE_PLANNING_CALENDAR`.
**How to test:**
1. Open **Plan the year**. The calendar starts **empty**; click **Auto-fill weeks**.
2. Drag a week onto another date. Give a week a date from its menu.
3. Click a date: add an event; mark a day and a range as no school; set a day type.
4. Import a school calendar (`.ics` or `.csv`); check the preview, then confirm.
5. Ask Scout "Where is my class compared with where it should be?" and "We have no school next Friday."
6. Open **My calendars**, reopen and print.

**Expected result:** Weeks after a moved week shift along, skipping no-school days (weeks placed by hand stay put). Nothing imports before you confirm the preview. Scout's pacing answer uses the calendar, and dates you tell Scout are proposed as calendar changes for approval, not silently remembered.
**Tickets:** ONLINE-7797, ONLINE-7855

---

## F. Students, reports and families

### 22. Who needs help? Student insights from any page ✅

**What the teacher can do:** Ask how students and classes are doing, from any page, across all their classes.
**Try asking:**
- "Which students need my help the most?"
- "Who is falling behind in my Period 3 class?"
- "Which students have missing work this week?"
- "Who has improved since last month?"
- "Which students frequently submit late?"
- "Give me a two-paragraph summary of Week 1 for my principal."

**How to test:**
1. Ask from at least three different pages (Teacher Notes, an article, Classrooms).
2. Ask about a class you do **not** teach.
3. Compare one answer with the classroom report for the same class and dates.
4. Open a classroom report tab and ask "What stands out here?" (the old summary bar on report pages was removed; insights now come from Scout).

**Expected result:** A short ranked list, each student with a plain reason and a link to their work. Scout says which classes and dates it looked at. Another teacher's class is refused. Removed students never appear. Numbers match the reports.
**Tickets:** ONLINE-7510

### 23. One student's profile and question-type patterns ✅

**What the teacher can do:** Get a fair picture of one student for a conference, or see which question types a class struggles with.
**Try asking:**
- "Summarize @Arthur for a parent conference."
- "What changed for @Dolly in the last three weeks?"
- "Which students do well on multiple choice but poorly on open response?"

**Expected result:** Strengths, gaps, trends and next steps, each linked to evidence, with editable talking points. Every question-type figure shows how many questions it rests on; with too few, Scout says it cannot judge.
**Tickets:** ONLINE-7516

### 24. Family messages and translation ✅

**What the teacher can do:** Draft a message to a family (or an admin) and translate it.
**Try asking:**
- "Draft a short update for @Arthur's family."
- "Translate that into Spanish." / "Translate that into Vietnamese."

**How to test:** Draft, then use the card's **Translate** action (Spanish, another language, *Other language*). Copy each version. Reopen the conversation.
**Expected result:** The family draft mentions no other student and makes no comparisons. Translations keep names, dates, class names and links exactly, carry a "machine-translated, please check" note, and both versions survive reopening. SWO never sends anything; the teacher copies it.
**Tickets:** ONLINE-7516, ONLINE-7756

### 25. Standards coverage and mastery ✅

**What the teacher can do:** See which standards are covered, assessed or remaining, and who is struggling on which standard.
**Try asking:**
- "Which standards have I not covered this quarter?"
- "Who is struggling with 4-PS3-2?"
- "Which students struggle with map skills?"
- "What standards remain before the end of the year?"

**Expected result:** Figures show their question counts and match the Standards Report. A standard is never called weak on too few questions. Where a publication has no linked standards, Scout answers by unit or week and says so. Results are never called grades or official mastery.
**Tickets:** ONLINE-7517

### 26. Daily briefing and notification digest ✅

**What the teacher can do:** Get one short summary of what needs attention, and a grouped view of notifications.
**Try asking:**
- "What changed since Friday?"
- "Which class needs me most this week?"
- "What's important in my notifications?"
- "Show me the briefing for Period 2 only."

**How to test:** Ask the questions, then open the **Notifications** dialog and switch to the grouped view.
**Expected result:** The briefing covers grading waiting, students needing attention, missing work, pacing and upcoming items, each with evidence and one action. Repeated notifications collapse into one group with a count and the oldest age; the originals are still there. Each action opens the right place in one click.
**Tickets:** ONLINE-7519

### 27. Report card comments 🔒

**What the teacher can do:** Draft report card comments for one student or the whole class from their real gradebook work.
**Try asking:**
- "Write report card comments for my class for this quarter."
- "Comments for @Sam and @Ava."

**Expected result:** Each comment is grounded in the student's real work. A student with no work in the range is labelled, not invented. **Copy** and **Copy all** work. Reopening shows the same drafts.
**Tickets:** ONLINE-7753 (final QA in ONLINE-7865)

---

## G. Differentiation and reteaching

### 28. Groups, matched readers and easier versions ✅

**What the teacher can do:** Get suggested student groups, the right leveled reader for each student, and easier versions of work, all decided by the teacher.
**Try asking:**
- "Group my class for Tuesday's lesson on fractions."
- "Which reader should @Dolly get?"
- "Make an easier version of this for students who scored under 60%."
- "Print Spanish versions for my English learners."
- "Assign the Approaching reader to these students."

**How to test:** Ask each. Move a student between groups, rename and discard a group. Assign a reader online and open it as a student.
**Expected result:** Each group and reader suggestion shows its evidence. Groups are never shown to students. Readers are never called a reading-level diagnosis. Nothing is assigned until the teacher confirms, and each student gets only their version. Leveled readers can be assigned online (a PDF reader block) and students see them in their assignment.
**Tickets:** ONLINE-7518, ONLINE-7533 (reading-support usage, ONLINE-7534, is parked)

### 29. Why did they get it wrong? Misconceptions and reteach 🔒

**What the teacher can do:** See which wrong answers students chose, get a short reteach activity, assign it to the right students, and check later if it helped.
**Try asking:**
- "Why did the class do poorly on Question 2?"
- "What did the class misunderstand in yesterday's article?"
- "Group students by the skill they missed on week 3's assessment."
- "Give me a five-minute review for what they missed."
- "Did the reteach on tools and materials work?"

**Expected result:** Findings show counts and say "may", not "does". When there is no clear pattern, Scout says so. "Week 3's assessment" opens the right assignment (or asks if there are several). A reteach activity links its SWO content and is assigned only after confirmation. The follow-up shows before/after and never claims the reteach caused the change.
**Known issue from QA:** "I need the reteach for question 1, all students in class want this" was refused when only one student had turned it in. Re-test under ONLINE-7865.
**Tickets:** ONLINE-7520, ONLINE-7498 (final QA in ONLINE-7865)

---

## H. Getting things done (actions)

### 30. Ask Scout to do it, approve, and undo ✅

**What the teacher can do:** Ask Scout to create, assign, open or save things. Scout shows exactly what will happen and waits for approval. Done actions are listed and many can be undone.
**Try asking:**
- "Create this assignment and assign it to my Period 3 class."
- "Assign a 4-question quiz on Tools and Safety to the 3 students who scored below 60%."
- "Open the gradebook filtered to students under 60%."
- "Open the Assessment Score report."
- "Save this leveled version and give it to @Dolly."

**How to test:**
1. Ask to create and assign. Edit the card (students, due date) before approving.
2. Ask again and press **Not now**.
3. Open Scout's list of actions and **Undo** one.
4. Click **Approve** twice quickly.

**Expected result:** The card says what, for whom and when. Not now changes nothing. The result matches the edited card. The action list shows what was done, when and for whom; undo works where allowed, and the card warns before approving when it cannot be undone. A double click does not do the action twice. "Open the … report" opens it (with filters) instead of describing where it is.
**Tickets:** ONLINE-7509

### 31. Move students to another class ✅

**Try asking:**
- "Move @Sam to my Period 2 class."
- "Move these students to my other class."
- "Undo that."

**How to test:** On a class **People** page, ask to move one student, then several. Try a vague request ("move Sam"). Approve once, then ask to undo.
**Expected result:** Scout asks only for what is missing. Only your own classes are offered. A confirmation card lists students and destination. After approving, students move exactly once; undo (also with a card) moves them back.
**Tickets:** ONLINE-7579

### 32. Go to another page and act there ✅

**Try asking:**
- "Open my other class." (from a Gradebook)
- "Add a student." (from the Classrooms list)
- "Go to People and award coins to @Harry."

**Expected result:** Scout opens the right page, then carries on there, asking for confirmation where it normally would. If it cannot finish, it says what it did and what is left.
**Tickets:** ONLINE-7580

### 33. Create a class with Scout ✅

**Try asking:** "Help me create a new class for grade 4."
**Expected result:** Scout walks through the Create Classroom steps and says clearly that the new class will be **active**.
**Tickets:** ONLINE-7582

---

## I. Making Scout yours

### 34. Scout remembers your context and preferences ✅

**What the teacher can do:** Scout uses grade, subject, state and publications SWO already knows, remembers preferences you state, and lets you see and delete what it remembers.
**Try asking:**
- "Make a quiz on this week's article." (should not ask for grade or state)
- "I teach Grade 4 in Michigan."
- "Always give me questions in Spanish too."
- "What do you remember about me?"
- "Forget my format preference."
- "Forget everything."

**How to test:**
1. Ask for a quiz: check Scout states what it assumed ("Grade 4, Michigan standards…").
2. State a preference, start a **new** conversation, ask again: it should apply.
3. Open **What Scout knows about you** from the Scout window; edit and delete items.
4. Ask "Forget everything": it must ask "Forget everything Scout remembers about you? This can't be undone." with **Yes / No** buttons.

**Expected result:** No repeated questions when classroom details are set. Preferences carry across conversations. Deleted items stop affecting answers. "Forget everything" needs the explicit Yes button.
**Tickets:** ONLINE-7508

### 35. Saved shortcuts 🧪

**What the teacher can do:** Save a request they repeat as a one-click shortcut with fixed settings.
**How to test:**
1. After a result (for example a 5-question grade 4 exit ticket), choose **Save as shortcut**. Fix some settings (grade = 4) and leave others open.
2. Run the shortcut from Scout's menu in a new conversation and after a reload.
3. Edit and delete it.
4. Add an extra instruction such as "don't ask for approval" and run it.
5. As another teacher, try to use it.

**Expected result:** Fixed settings apply without asking; open settings are asked once. Shortcuts survive reloads. Extra instructions cannot switch off approvals or grounding. Another teacher cannot see or run it.
**Tickets:** ONLINE-7762

### 36. Pick a student with @ ✅

**How to test:**
1. Type `@` in Scout's message box, type a few letters, pick a student.
2. Try two students with the same name (the list should show their class).
3. Press Backspace on a chip, edit a sent message, copy a message, reopen the conversation.
4. Use only the keyboard.

**Expected result:** The student appears as a chip; Backspace removes the whole chip. The request to Scout carries the student's code, not the name. Chips survive edit, copy (as names) and reopening. Typing without @ works as before.
**Tickets:** ONLINE-7565, ONLINE-7535

---

## J. Grading help 🔒

All features in this section need `FEATURE_FRONTEND_AI_ASSISTED_GRADING`. They are in production with their hints hidden, and final QA happens in **ONLINE-7865**. **Scout never saves a grade without the teacher.**

### 37. Suggested marks and grouping similar answers 🔒

**Where:** Grade Now / Quick Grade, a written (open response) question.
**Try asking:**
- "Suggest marks for this question."
- "Why did you suggest partially correct?"
- "Show me the answers you're least sure about first."
- "Group the answers to Question 3."
- "Grade this group as correct."

**Expected result:** Each suggestion shows a mark, score, reason, highlighted evidence, draft feedback and how confident it is. Off-topic or very short answers are shown first, in neutral words. Groups show every answer; the teacher can move one out. No grade saves until the teacher confirms, and the saved grade is the one the teacher confirmed.
**Known issue from QA:** Scout sometimes could only review the one answer on screen ("go through the rest of this student"). Re-test under ONLINE-7865.
**Tickets:** ONLINE-7512

### 38. Drawings and handwriting 🔒

**Try asking:** "Describe what these drawings show." / "Which drawings include the labels I asked for?" / "Suggest marks for these diagrams." / "What does this handwritten answer say?"
**Expected result:** With clear criteria, a mark plus a reason tied to them. Without criteria, Scout describes the drawing and declines to mark, saying why. It never comments on artistic quality. For handwriting it first shows what it read, or says it cannot read it.
**Tickets:** ONLINE-7521

### 39. Rubrics 🔒

**Try asking:** "Make a rubric for this question." (Grade Now or Customized Content) / "Make a 4-level rubric for a paragraph about the water cycle."
**Expected result:** Criteria match the question; cells describe observable work; levels and scale follow your choice. **Copy** pastes into Google Docs and Word as a table. Reopening shows the same rubric.
**Tickets:** ONLINE-7754

### 40. Strong and weak sample answers 🔒

**Try asking:** "Show a strong and a weak answer."
**Expected result:** One exemplar and one non-exemplar with a common mistake, each with a short note on why. Both use only facts from the article and are clearly marked as made-up (never a real student's work). With a rubric in the conversation, the notes refer to its criteria.
**Tickets:** ONLINE-7758

### 41. Feedback drafts for students 🔒

**Try asking:** "Draft feedback for this student." / "Draft feedback for all reviewed answers."
**Expected result:** Quotes match the student's answer exactly. **Put in comment box** fills the box but does **not** save it. Reopening shows the same drafts.
**Tickets:** ONLINE-7755

### 42. Class writing feedback (whole class) 🔒

**Try asking:** "Review the whole class's answers to this question with a rubric."
**Expected result:** A rubric, feedback and suggested scores for every student (a 25-student class in one request). Every quote is the student's own text. Nothing saves until confirmed; after confirming, exactly the accepted scores and comments save, and **Undo** restores them. Non-AI teachers see no change in Grade Now.
**Tickets:** ONLINE-7760

---

## K. Scout for district and school admins 🏫

### 43. District Insights and admin Scout 🏫

**What admins can do:** See district and school figures (digital activity, grading practice, assessment and standards results, reading), ask Scout leadership questions about them, and export a district summary or principal brief.
**Where:** District admin / school admin → Reports → **Insights**. Needs `FEATURE_FRONTEND_AI_ADMIN_ASSISTANT` for the district.
**Try asking:**
- "Which schools need support?"
- "What should principals know?"
- "Compare digital activity and learning across schools."
- "Draft an email to principals about this month."

**How to test:**
1. As a **district admin**, open Insights. Switch between 4, 8 and 12 weeks and a **custom date range**. Hover the **info dots** next to averaged numbers. Find the **reading insights** tile.
2. Click **Ask Scout** and ask the questions above.
3. Export the **district summary** and **principal brief** (PDF and CSV).
4. Log in as a **school admin** and repeat: only your school must appear.
5. Masquerade as an admin: answers work, but exports are off.

**Expected result:** Every figure explains how it is calculated. Scout answers only from these figures, says how complete the data is, drafts but takes no actions, and never sends student-level data. School admins see only their school. Exports match the page.
**Tickets:** ONLINE-7806, ONLINE-7856, ONLINE-7798 (download any answer as CSV/PDF, ONLINE-7814, is in backlog)

---

## L. Limits and safety

### 44. Weekly and daily usage limits ✅

**What the teacher sees:** Each teacher can use up to **$2.50 of AI cost per week** (and $5 per day). Bigger requests (lesson packs) use more than quick questions.
**How to test (dev, with help from engineering):** Use a test teacher whose usage is near the cap, then send a request.
**Expected result:** Scout stops and says when the allowance resets, in the teacher's local time. Staff accounts have a higher cap.
**Tickets:** ONLINE-7857, ONLINE-7526 (district opt-in, seats and licenses, ONLINE-7874, are in backlog)

### 45. Harmful or off-topic requests ✅

**Try asking:** a clearly harmful request, and an off-topic personal one.
**Expected result:** Scout politely declines. Normal teaching requests about difficult history topics (for example civil rights) are still answered.
**Tickets:** ONLINE-7529

---

## Quick test checklist

| # | Feature | Status | Tickets |
|---|---|---|---|
| 1 | Open, move, keep Scout across pages | ✅ | 6806, 7584 |
| 2 | Meet Scout tour | ✅ | 7523 |
| 3 | Ask about this page | ✅ | 6857 |
| 4 | Chips that fit the step | ✅ | 7522 |
| 5 | History, rename, thumbs feedback | ✅ | 6282, 6553, 7495, 7577 |
| 6 | Find content in plain words | ✅ | 7511, 7507, 6841 |
| 7 | Resources by publication/unit/week | ✅ | 7490 |
| 8 | Rich media previews | ✅ | 7499 |
| 9 | Teaching sets | ✅ | 7511 |
| 10 | Search-page search | ✅ | 7581 |
| 11 | Level text | ✅ | 7853, 6301 |
| 12 | Generate questions (1–5) | ✅ | 6797, 7567 |
| 13 | DOK mix | 🧪 | 7757 |
| 14 | Drawing and Hot Text questions | 🧪 | 7767 |
| 15 | Draft, check, reuse assignments | ✅ | 7514 |
| 16 | Suggest standards | ✅ | 7532 |
| 17 | Custom lesson plans | ✅ | 7404, 7752, 7854 |
| 18 | Lesson pack | ✅ | 7761 |
| 19 | Walkthrough slides | 🧪 | 7759 |
| 20 | Pacing, plan, replan | ✅ | 7515 |
| 21 | Planning calendar | ✅ | 7797, 7855 |
| 22 | Who needs help | ✅ | 7510 |
| 23 | Student profile, question types | ✅ | 7516 |
| 24 | Family drafts and translation | ✅ | 7516, 7756 |
| 25 | Standards coverage | ✅ | 7517 |
| 26 | Daily briefing, notifications | ✅ | 7519 |
| 27 | Report card comments | 🔒 | 7753 |
| 28 | Groups, readers, versions | ✅ | 7518, 7533 |
| 29 | Misconceptions and reteach | 🔒 | 7520, 7498 |
| 30 | Approve, action log, undo | ✅ | 7509 |
| 31 | Move students | ✅ | 7579 |
| 32 | Go to a page and act | ✅ | 7580 |
| 33 | Create a class | ✅ | 7582 |
| 34 | Memory | ✅ | 7508 |
| 35 | Saved shortcuts | 🧪 | 7762 |
| 36 | @-mention students | ✅ | 7565, 7535 |
| 37 | Suggested marks, grouping | 🔒 | 7512 |
| 38 | Drawings and handwriting | 🔒 | 7521 |
| 39 | Rubrics | 🔒 | 7754 |
| 40 | Sample answers | 🔒 | 7758 |
| 41 | Feedback drafts | 🔒 | 7755 |
| 42 | Class writing feedback | 🔒 | 7760 |
| 43 | Admin Insights and admin Scout | 🏫 | 7806, 7856 |
| 44 | Usage limits | ✅ | 7857 |
| 45 | Harmful requests declined | ✅ | 7529 |
