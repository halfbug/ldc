# Scout (AI Assistant): Feature Progress Overview

**As of:** 22 October 2026
**Scope:** the 75 `[AI Project]` tickets in the Jira export (`JIRA (1).csv`)
**Code:** `swo-3.0` (Laravel `backend` and Nuxt 3 `frontend-v3`) and `rag` (AI service, `lambdas/ai_assistant`)

---

## 1. Summary

| | |
|---|---|
| Tickets in scope | **75** |
| Done | **65** (87%) |
| In QA (Testing) | **4**: DOK question mix, lesson walkthrough slides, saved shortcuts, Drawing and Hot Text questions |
| Selected for development | **3**: text-leveler training, reading-support tracking, rag code cleanup |
| Backlog | **3**: Scout exports (CSV/PDF), grading release, access and licensing |
| Commits tagged to these tickets | **2,536** in `swo-3.0` (Apr–Oct 2026) and **1,935** in `rag` (Jul–Oct 2026) |
| In production | Teacher Scout, Planning Calendar and Admin Scout were checked in production on 15–16 Oct. Grading features shipped on 15 Oct with their hints hidden (see ONLINE-7865). |

**Status of each feature area**

| # | Feature area | Tickets | Status |
|---|---|---|---|
| 1 | Page awareness and the Scout window | 12 | ✅ Done |
| 2 | Trust, safety and student privacy | 6 | ✅ Done |
| 3 | Memory and personalisation | 2 | ✅ Done · 🧪 Shortcuts in QA |
| 4 | Teacher-confirmed actions | 4 | ✅ Done |
| 5 | Content discovery and search | 5 | ✅ Done |
| 6 | Article leveling | 3 | ✅ Done · ⏸ Leveler training not started |
| 7 | Question generation and assignment drafting | 6 | ✅ Done · 🧪 2 in QA |
| 8 | Lesson planning, slides, lesson packs and planning calendar | 9 | ✅ Done · 🧪 Walkthrough slides in QA |
| 9 | Student insights, reports and family communication | 6 | ✅ Done |
| 10 | Differentiation and reteaching | 5 | ✅ Done · ⏸ Support tracking parked |
| 11 | Grading assistance | 7 | 🟡 Built and in production with hints hidden; release work in ONLINE-7865 |
| 12 | Scout for administrators | 4 | ✅ Done · 📋 Exports in backlog |
| 13 | Cost, speed and model choice | 7 | ✅ Done · 📋 Licensing in backlog |
| 14 | Feedback and quality loop | 4 | ✅ Done |
| 15 | Infrastructure and housekeeping | 3 | ✅ Done · ⏸ rag cleanup not started |

Some tickets fall into more than one area. Each ticket is listed once below, under its main area.

**Key numbers to share**

- **Model choice:** Scout Core v2, the streaming engine that serves chat turns, runs **Claude Sonnet 5** as its main model and **Claude Haiku 4.5** for quick checks. An earlier study of the original v1 assistant (ONLINE-6859, August) measured Nova Micro at about $0.0004 per turn with 90.5% correct action choice, against 93.4% for Haiku. That study also showed the invented-URL problem was fixed in code, not by a larger model.
- **Running cost (ONLINE-7526, 7857):** a turn costs about **$0.02** on average. Each teacher is capped at **$5 per day** and **$2.50 per week**. A medium-use teacher year comes to about **$80 per seat**.
- **Cost per tool (ONLINE-7857):** lesson pack $0.08 · weekly plan $0.09 · slides $0.05 · question set $0.04 · report cards $0.03 · leveling $0.015 · quick question $0.013 · class feedback about $0.22 per run.
- **Prompt size (ONLINE-7588):** each chat call used to repeat a 17.7k-token prompt. The restructure moved to a shared core of about 5.2k tokens, with each feature's rules loaded only with that feature.
- **Safety (ONLINE-7529):** the guardrail now runs on the tier Terraform declares. Before the fix, 3 of 60 harmful test requests got through. On the declared tier, 0 of 60 did.

**Open items and next steps**

1. **ONLINE-7865 (grading release):** finish, verify and run QA on 9 grading-related features, then turn their hints back on.
2. **ONLINE-7874 (access and licensing):** district opt-in, seats assigned by district admins, school-year licenses and pilots. This is required before selling Scout.
3. **ONLINE-7814 (exports):** CSV and PDF download of any Scout answer, one shared export path for teachers and admins.
4. **ONLINE-7801 (rag cleanup):** one test runner with CI, dead code removed, one settings module. This prepares `rag` for an outside senior review.
5. **ONLINE-6300 (leveler training)** and **ONLINE-7534 (reading-support tracking):** both need requirements or privacy sign-off first.
6. **4 tickets in QA:** ONLINE-7757, 7759, 7762, 7767.

---

## 2. How Scout is built (one paragraph for context)

Components on each page publish what they show, such as the subject, the view and any lists ("surfaces"), along with the actions the teacher can take there ("capabilities"). The `rag` AI service reads this page card, decides on an answer or proposes an action, and streams the reply. **Actions run in the browser and are checked against the app's real state before Scout reports success.** Any change to data needs the teacher's confirmation. Student names never leave the browser: the model sees pseudonyms such as `Student 3`, and real names are put back only on screen. Laravel handles credits, audit, figures (insights, pacing, admin) and the confirmed-action handlers.

| Layer | Main files |
|---|---|
| Page context (browser) | `frontend-v3/ai/context/types.ts`, `executor.ts`, `pageCard.ts`, `index.ts`, `roster.ts` |
| Chat UI | `frontend-v3/ai/components/AiAssistantDialog.vue`, `ai/composables/useAiChat.ts`, `ai/services/coreStream.ts`, `ai/services/aiHttp.ts` |
| AI service | `rag/lambdas/ai_assistant/src/core/runtime.py` (`_run_turn`), `core/loop.py` (`_run_loop`), `core/prompts/constitution.py`, `core/tools/*`, `core/engines/*`, `routers/core_router.py` |
| Laravel | `backend/routes/api.php` (prefix `ai`), `app/Services/ScoutActions/Handlers/*`, `app/Services/StudentInsights/*`, `app/Http/Controllers/AiController.php` |

---

## 3. Features in detail

Legend: **Parent** = the original feature ticket · **Improvement** = extends or polishes a parent · **Follow-up** = gap or bug found after the parent shipped.
When a parent ticket's "What it does" cell is empty, the ticket is too large to sum up in two lines. The paragraph at the top of its section describes it.
Files and functions come from the commits tagged with each ticket. Test-only and experiment files are left out. Paths were checked against the latest release branch, `ONLINE-5385_scout_release_2`, in both repos; the checked-out branches (`swo-3.0`: `ONLINE-5385_scout_round2`, `rag`: `ONLINE-7875_ttft_floor_test`) may not contain every file.

---

### 3.1 Page awareness and the Scout window

Scout knows which page the teacher is on and what it shows, stays open as the teacher moves between pages, and offers suggestions that fit the current step.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-6857 | Page/DOM awareness for the AI assistant |  | Done | **Parent** (umbrella: 1,796 swo and 1,105 rag commits) |
| ONLINE-6806 | Chat modal persistent across pages and movable | Scout's chat window stays open when the teacher moves to another page. The teacher can drag it anywhere on the screen and keep working. | Done | Improvement |
| ONLINE-7522 | SCOUT-H: hints match the current step or tab | The suggestions Scout shows match the exact step or tab the teacher is on. It no longer suggests things that can't be done yet. | Done | Improvement |
| ONLINE-7580 | SCOUT-NA: go to another page and act there in one request | A teacher can ask for something that lives on another page, such as "open my gradebook and show week 5". Scout opens that page and finishes the task there. | Done | Follow-up |
| ONLINE-7581 | SCOUT-SP: on the Search page, use the page's own search | On the Search page, a request like "find videos about penguins" runs the page's own search, so results show on the page the teacher is already using. | Done | Follow-up |
| ONLINE-7582 | SCOUT-CA: say a new class is created as active | When Scout helps create a class, it now says clearly that the new class will be active. | Done | Follow-up |
| ONLINE-7584 | SCOUT-Z: Scout's dropdowns stay above the Scout window | Fixes a display bug where a dropdown inside Scout could open behind the Scout window and could not be used. | Done | Follow-up (bug) |
| ONLINE-7577 | SCOUT-UI: design-review polish | A visual polish pass after the design review: spacing, text, buttons and cards look consistent and match the SWO design. | Done | Improvement |
| ONLINE-7523 | SCOUT-T: Meet Scout spotlight tour | Improves the "Meet Scout" guided tour. The page dims around each highlighted item, and the tour moves smoothly from step to step. | Done | Improvement |
| ONLINE-7565 | @-mention students in the message box | Teachers type @ to pick a student from a list. Scout then knows exactly which student is meant, even with nicknames, typos or two students with the same name. | Done | Improvement |

**swo-3.0 (frontend-v3)**

| File | Key functions / purpose |
|---|---|
| `ai/context/types.ts`, `ai/context/index.ts` | Surface and capability types; the public entry point for the AI module |
| `ai/context/executor.ts` | `execute`, `persistenceNote`, `runDeclineHook`: runs an action and re-checks app state before reporting success |
| `ai/context/pageCard.ts` | `buildPageCard`, `publishedContent`: the page snapshot sent with each turn |
| `ai/components/AiAssistantDialog.vue` | Chat window; `formatAiContent`, `saveArtifact`, `onHeaderPointerDown` |
| `ai/composables/useAiChat.ts`, `useAiActions.ts`, `useAiThreads.ts` | Chat engine, action state, conversation history |
| `ai/composables/useAiWindow.ts`, `ai/components/AiAssistantRoot.vue`, `ai/composables/useAiPersistence.ts` | Window that stays open across pages and can be moved (6806); `placeForTour` |
| `ai/context/chatSuggestions.ts`, `scoutAbilities.ts`, `actionCategories.ts` | `buildChatSuggestions`, `starterPrompts`, `HINTLESS_CAPABILITIES` (7522) |
| `ai/context/openFor.ts` | `openForNextStep`, `openForCapability`: open a page, then act there (7580) |
| `ai/zIndex.ts` | `raiseLayer`, `nextZ`, `isScoutOverlay` (7584) |
| `ai/composables/useTourSpotlight.ts`, `ai/components/AiTourSpotlight.vue`, `components/SiteTour.vue` | `panelRectsFor`, `cardPositionFor`, `scoutIntro` (7523) |
| `ai/components/AiStudentMentions.vue`, `ai/context/mentions.ts` | `mentionCandidates`, `mentionRows` (7565) |
| `components/global/TheNavbar.vue`, `components/global/NavbarAiSurface.vue` | Global navigation surface; `aiRunNavAction`, `aiOpenDestination` |
| Per-page surfaces: `components/ArticleOrAssignment.vue`, `publication/PublicationResources.vue`, `classroom/people/StudentsList.vue`, `classroom/ClassroomsList.vue`, `grade/gradebook.vue`, `dialogs/QuickGradeDialog.vue`, … | Each page publishes its own facts and actions |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/runtime.py` | `_run_turn`, `deterministic_continuation`, `_system_blocks` |
| `src/core/loop.py` | `_run_loop`, `ModelCaller`, `build_request` |
| `src/core/tools/page_action.py` | `PageActionTool`: proposes a browser action |
| `src/core/prompts/constitution.py` | `mode_block`, `page_search_block` (7581), `acting_block` |
| `src/core/context/build.py` | `build_context` |
| `src/services/assistant_service.py`, `src/routers/assistant_router.py` | Assistant API, threads and streaming |

---

### 3.2 Trust, safety and student privacy

Scout says where it looked, hides weak matches, shows the evidence behind anything it says about a student, and never sends student names to the model.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-7507 | SCOUT-01: honest, evidence-based Scout |  | Done | **Parent** |
| ONLINE-7535 | Stable student aliases across tabs and conversations | Each student keeps the same anonymous code across tabs and reopened conversations. Scout can never mix up two students. | Done | Follow-up |
| ONLINE-7529 | SCOUT-G: guardrail on the declared tier, catches every harmful request | Scout's safety filter now runs at the strength we specified. In testing it blocked all 60 harmful requests; before the fix, 3 got through. | Done | Improvement |
| ONLINE-7578 | SCOUT-PR: production-readiness fixes from the 2 Oct audit | A set of safety, privacy and reliability fixes found in a review before go-live, such as stricter permission checks and limits on bulk actions. | Done | Follow-up (go-live) |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `frontend-v3/ai/context/evidence.ts` | `recordEvidence`, `evidenceFor`, `studentReportLink` |
| `frontend-v3/ai/context/roster.ts` | `aliasFor`, `swapTypedNames`, `pseudonymiseTypedNames`, `studentKey` (7535) |
| `frontend-v3/ai/context/studentNames.ts` | `nameGate`, `resolveName`, `nameGateReply` |
| `frontend-v3/ai/components/AiStudentEvidence.vue`, `AiSearchedLine.vue` | Evidence beside each claim; "where Scout searched" line |
| `frontend-v3/ai/pageApi.ts`, `components/global/NavbarAiSurface.vue` | Audit fixes (7578): `aiDestinations`, `aiFullStudent` |
| `backend/app/Http/Controllers/AiController.php` | `failureContext` (7578) |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/context/relevance.py` | `judge`, `score`: relevance floor for search results (7507) |
| `src/core/tools/search_curriculum.py` | `resolve_outcome`, `_relevant`, `render` |
| `src/core/name_claim.py`, `name_scrub.py`, `student_wording.py`, `aliases.py` | Screens that block names and unsupported claims about students |
| `src/core/standards_claim.py`, `ability_claim.py`, `bare_codes.py`, `leak.py` | Output screens |
| `src/core/guardrail.py` | `guardrail_truly_blocked`, `guardrail_output_only_block` (7529) |
| `infra/swo/modules/bedrock-guardrails/main.tf`, `curriculum.tf` | Guardrail tier (7529) |
| `src/core/prompt_registry.py` / `.json` | Rule registry; most of the 7578 fixes |

---

### 3.3 Memory and personalisation

Scout uses what SWO already knows (grade, subject, state, publications), remembers preferences the teacher states, and lets the teacher save repeated requests as one-click shortcuts.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-7508 | SCOUT-02: Scout remembers teacher context |  | Done | **Parent** |
| ONLINE-7762 | SCOUT-SC: saved Scout shortcuts with fixed settings | Teachers can save a request they repeat often, such as "exit ticket, 5 questions, grade 4", as a one-click shortcut with its settings fixed. | **Testing** | Improvement |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `backend/app/Services/Ai/TeacherContext.php` | `profile`, `teaching`, `classrooms`, `describe` |
| `backend/app/Models/ScoutMemory.php`, `app/Actions/Ai/SaveScoutMemory.php` | Stored memories |
| `backend/app/Http/Requests/Ai/ScoutShortcutRules.php` | `shortcutRules`, `checkWording`, `settingsToStore` (7762) |
| `frontend-v3/ai/stores/scoutMemory.ts` | `fetchContext`, `createMemory`, `updateMemory`, `deleteMemory` |
| `frontend-v3/ai/components/ScoutMemoryPanel.vue` | "What Scout knows about me" panel; `forgetAll` |
| `frontend-v3/ai/context/scoutShortcuts.ts`, `ai/components/AiShortcutEditor.vue`, `ai/context/drawerCatalogue.ts` | `proposeShortcut`, `usedSettings`, `cardForShortcut` (7762) |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/context/teacher.py` | `render_teacher_block`, `describe_assumed`, `forgotten_since` |
| `src/core/tools/remember.py`, `forget.py`, `memory_client.py` | `RememberTool`, `ForgetTool`, `create_memory`, `delete_memory` |
| `src/core/context/shortcut.py` | `parse_shortcut`, `with_shortcut` (7762) |
| `src/core/tools/generate_questions.py` | `_resolved_grade`, `_resolved_types`, `_resolved_count`: remembered defaults |

---

### 3.4 Teacher-confirmed actions

Scout can take actions, such as creating or assigning work, moving students or awarding coins. Before each one it shows exactly what will happen and waits for the teacher to confirm. Actions are logged, and many can be undone.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-7509 | SCOUT-03: teacher-confirmed actions |  | Done | **Parent** |
| ONLINE-7579 | SCOUT-MV: move students to another class from Scout | Teachers can ask Scout to move students to another of their classes. Scout shows a confirmation card first and makes the change only after the teacher approves. | Done | Follow-up |
| ONLINE-7533 | SCOUT-LR: assign leveled readers online (PDF reader block) | Teachers can assign a leveled reader (Approaching, On level or Above) to specific students to read online, not only print it. | Done | Follow-up (of 7518) |
| ONLINE-7580 | Go to another page and act there | A teacher can ask for something that lives on another page, such as "open my gradebook and show week 5". Scout opens that page and finishes the task there. | Done | (listed in 3.1) |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `frontend-v3/ai/context/scoutActions.ts` | `scoutActionCapabilities`, `assignmentIn`, `moveDestinations`, `undoCandidate` |
| `frontend-v3/ai/services/actionsClient.ts` | `previewAction`, `confirmAction`, `logPageOpen` |
| `frontend-v3/ai/components/AiActionPreview.vue`, `AiActionLog.vue` | Confirmation card; record of actions |
| `frontend-v3/ai/context/effects.ts`, `templates.ts` | `AI_CAPABILITY_EFFECTS`, `AI_RESULT_TEMPLATES` |
| `frontend-v3/ai/context/intentGuard.ts` | `intentMisroute`, `undoByHandMisroute` (7579) |
| `backend/app/Services/ScoutActions/Handlers/AssignHandler.php` | `editPreview`, `executeEdit`, `alreadyAssigned` |
| `backend/app/Actions/Classrooms/SetStudentsDropped.php`, `app/Enums/AiActionType.php` | Move students (7579); action types |
| `backend/app/Actions/Ai/GetAssistantActionHistory.php` | Action history |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/runtime.py` | `assigned_where_call`, `direct_args`, `category_direct_call` |
| `src/core/tools/page_action.py`, `ask_user.py` | Pause the turn for a browser action or a question to the teacher |
| `src/core/tools/draft_assignment.py` | `DraftAssignmentTool` |

---

### 3.5 Content discovery and search

Teachers describe what they want in plain words and Scout finds it across every publication they have: articles, lesson plans, printables, assessments, media and standards. Results show rich previews and can be grouped into a teaching set.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-6841 | AI assistant chat result improvements (stay on topic, correct tab) | Makes Scout's search answers stay on topic. Asking for an article returns articles, not images or videos, and each link opens the right tab. | Done | **Parent** (early) |
| ONLINE-7511 | SCOUT-05: unified content discovery and teaching sets |  | Done | **Parent** |
| ONLINE-7490 | Filter teacher resources by publication, unit, week | Teachers can ask for resources by publication, unit or week, for example "the weekly assessment for unit 2, week 3", and get exactly those items. | Done | Improvement |
| ONLINE-7499 | Rich media previews in chat search results | Search results show previews: videos play, images open larger, audio plays, and PDFs show a thumbnail, without leaving the chat. | Done | Improvement |
| ONLINE-7581 | Search page uses the page's own search | On the Search page, a request like "find videos about penguins" runs the page's own search, so results show on the page the teacher is already using. | Done | (listed in 3.1) |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `frontend-v3/ai/services/contentResults.ts` | `useContentResults`, `resultHref`, `MAX_RICH_PREVIEWS` |
| `frontend-v3/ai/components/AiContentResults.vue`, `AiResultPreview.vue`, `AiResultCard.vue` | Result list and previews; `onIntersect` (lazy loading) |
| `frontend-v3/ai/utils/kindLabels.ts` | `kindLabel`: Video, Image, Audio, PDF, Printable, … |
| `frontend-v3/ai/components/AiTeachingSet.vue`, `ai/services/teachingSet.ts` | `teachingSetView`, `revise` |
| `frontend-v3/ai/context/tocPrintables.ts`, `tocWeekJump.ts` | `weekPrintables`, `weeksMatching` (7490) |
| `backend/app/Console/Commands/UploadPdfThumbnails.php`, `backend/app/Services/ThumbnailService.php` | Printable thumbnails, taken from the worksheet PDF URL (7499; the earlier `WorksheetThumbnailService` was removed on 28 Sep) |
| `backend/app/Console/Commands/ExportAiContent.php`, `app/Support/AiExport/PublicationStructure.php` | Exports the content index with unit and week placement |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/tools/search_curriculum.py` | `SearchCurriculumTool`, `resolve_place`, `plan_query`, `render` |
| `src/core/context/structure.py` | `resolve`, `Place`, `week_label` (7490) |
| `src/core/context/search.py`, `discovery.py` | `query`, `dedupe`, `reason_for`, `group_hits` |
| `src/core/tools/build_teaching_set.py` | `BuildTeachingSetTool`, `build`, `revise` |
| `commands/content_placements.py` | Unit and week placement of content (7490) |

---

### 3.6 Article leveling

Scout rewrites an article at a lower reading level. A Level text button on the article opens Scout with the leveling prompt already set.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-6301 | Unknown grade of text: ask the teacher to choose K–8 | When a teacher wants to level text whose grade Scout doesn't know, Scout first asks which grade (K–8) the text is written for. | Done | **Parent** (early) |
| ONLINE-7853 | Level text button: 1 or 2 grades down, grade rules, assessment warning | Adds a Level text button beside articles. It rewrites the article 1 or 2 grades lower, follows grade rules, and warns before leveling an assessment. | Done | Improvement |
| ONLINE-6300 | AI text leveler training (±2 grades, from SW publications) | Plans to train the leveler on Studies Weekly's own articles so its rewrites match each grade more closely. Not started; requirements still need to be agreed. | **Selected** | Improvement (needs a requirements meeting) |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `frontend-v3/ai/context/articleLevel.ts` | `levelDownChoices`, `FREE_TEXT_TARGET_GRADES`, `recordLevelledArticleFromAdapted` |
| `frontend-v3/ai/intents/adaptArticle.ts`, `ai/services/adaptClient.ts` | `adaptArticle`, `sourceGradeToken` |
| `frontend-v3/ai/components/results/AdaptedArticleResult.vue` | Levelled article result |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/tools/level_article.py` | `LevelArticleTool`, `_ask` (asks for the grade when it is unknown), `target_options`, `resolve_target` |
| `src/core/engines/level.py` | `level_article`, `revise_levelled` |
| `src/core/guidelines/leveler.py`, `src/routers/level_router.py` | Leveling rules; `level_target_grades` |

---

### 3.7 Question generation and assignment drafting

Scout writes questions from a chosen article (one or up to five at a time, in 9 of the editor's 13 question types, with Drawing and Hot Text in QA), drafts whole assignments, checks their quality, and suggests standards for teachers' own questions.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-6797 | Question generator: choose the article, one correct answer, standards | Improves the question generator from customer feedback. Teachers choose the article the questions come from, multiple-choice questions have one correct answer, and standards are available. | Done | **Parent** (early) |
| ONLINE-7514 | SCOUT-08: assignment creation (draft, check, reuse) |  | Done | **Parent** |
| ONLINE-7532 | SCOUT-SS: suggest standards for a teacher's own questions | On request, Scout suggests learning standards for questions the teacher wrote. The teacher accepts or rejects them in one step. | Done | Improvement |
| ONLINE-7567 | Generate several questions at once for Customized Content | The question generator in Customized Content can write up to 5 questions at once instead of one at a time. | Done | Improvement |
| ONLINE-7757 | SCOUT-DOK: depth-of-knowledge mix in question sets | Teachers can choose how much recall versus reasoning a question set has (depth of knowledge). Each question shows its level. | **Testing** | Improvement |
| ONLINE-7767 | SCOUT-QT: Drawing and Hot Text question types | The question generator can now also write Drawing and Hot Text questions, two question types it could not write before. | **Testing** | Improvement |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `frontend-v3/ai/intents/generateQuestion.ts`, `generateQuestionSet.ts`, `questionSetShape.ts` | `generateQuestionSetIntent`, `questionSetRequest`, `questionSetDok` |
| `frontend-v3/ai/components/AiFlowCard.vue`, `results/QuestionSetResult.vue`, `results/QuestionResult.vue` | Question form and result cards |
| `frontend-v3/ai/questionBlocks.ts` | `AI_QUESTION_TYPES`, `inferQuestionType`, `questionPatch` |
| `frontend-v3/ai/context/assignmentCreate.ts`, `ai/services/assignmentDraft.ts` | `planDetails`, `draftMissing`, `draftToParams` |
| `frontend-v3/components/teachers/assignments/TeacherAssignmentEditForm.vue`, `components/BlockButton.vue` | Editor integration; `handleGenerateQuestionsChatApplied` |
| `frontend-v3/ai/components/AiSuggestStandards.vue`, `AiBlockStandardSuggestions.vue`, `ai/stores/standardSuggestions.ts` | Suggest and accept standards (7532) |
| `backend/app/Http/Controllers/AiStandardsController.php`, `app/Services/Standards/CandidateSlice.php`, `app/Policies/AiStandardSuggestionPolicy.php` | Candidate standards, scoped by publication subject |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/engines/questions.py` | `generate_questions`, `plan_slots`, `plan_dok`, `revise_questions`, `build_new_type` |
| `src/core/tools/generate_questions.py` | `GenerateQuestionsTool` |
| `src/core/tools/draft_assignment.py`, `check_assignment.py`, `assignments_client.py` | `DraftAssignmentTool`, `CheckAssignmentTool` |
| `src/core/engines/assignment_review.py` | `review`, `doubtful_keys`, `write_fixes` |
| `src/core/tools/suggest_standards.py`, `src/core/standards_suggest.py`, `src/core/engines/standards.py` | `SuggestStandardsTool`, `suggest_for_questions` |
| `src/core/guidelines/questions.py`, `src/schemas/topic_question_models.py` | Question rules; request and response schema |

---

### 3.8 Lesson planning, slides, lesson packs and the planning calendar

Teachers customise Studies Weekly lesson plans to their own time and standards, plan a week, generate a full lesson pack (plan, worksheet, exit ticket and slides), and lay a publication's weeks onto real school dates. Scout's pacing reads that calendar.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-7404 | AI: custom lesson plan | Teachers customise a Studies Weekly lesson plan to their own class time, success criteria, standards and notes, and save it in SWO. | Done | **Parent** |
| ONLINE-7515 | SCOUT-09: pacing, lesson preparation and week planning |  | Done | **Parent** |
| ONLINE-7797 | Yearly planning calendar (real dates, import school calendar) | A planning calendar for each class lays a publication's weeks onto real school dates and can import the school calendar. Scout's pacing advice uses it. | Done | **Parent** |
| ONLINE-7524 | SCOUT-L: rename lesson-plan tables with `ai_` | Renames the lesson-plan database tables so all AI-related data is grouped under one recognisable name. No visible change for teachers. | Done | Follow-up (housekeeping) |
| ONLINE-7752 | Lesson plans: unreadable articles, Markdown showing, guessed grade | Fixes lesson plans that failed for some articles, drafts that showed formatting symbols, and a grade that was guessed instead of taken from the article. | Done | Follow-up (bug) |
| ONLINE-7761 | SCOUT-PK: lesson pack in one request | One request produces a whole lesson pack: lesson plan, worksheet, exit ticket and slides, all for the same grade and goal. | Done | Improvement |
| ONLINE-7854 | Build on Studies Weekly's own lesson plans; richer slides | Lesson plans, weekly plans and lesson packs now start from Studies Weekly's own lesson plans instead of only the article text. Slides carry more content. | Done | Improvement |
| ONLINE-7855 | Planning calendar: start empty with Auto-fill, week numbers, day types | The planning calendar starts empty, with an Auto-fill weeks button. Saved lesson plans show their week number, and days can be marked by type (for example, no school). | Done | Follow-up |
| ONLINE-7759 | SCOUT-SL: lesson walkthrough drafted from the article | Scout drafts a slide presentation (lesson walkthrough) from the Studies Weekly article. The teacher edits it and presents it in the existing player. | **Testing** | Improvement |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `frontend-v3/pages/teacher/classrooms/[classroom_id]/lesson-plans/{index,create,[lesson_plan_id]}.vue` | Lesson plan list, create and edit pages; `generate`, `save`, `print` |
| `frontend-v3/components/lessonPlans/LessonPlanComposeModal.vue`, `utils/lessonPlanCompose.ts` | Compose form; `noArticleTextFailure`, `composeGrade` (7752) |
| `frontend-v3/utils/lessonPlanEditorHtml.ts`, `utils/lessonPlanPanel.ts`, `ai/context/lessonPlanArticle.ts` | Markdown and HTML conversion; reading article text |
| `frontend-v3/components/publication/PublicationResources.vue` | `openLessonCompose`, `openWeekCompose`, `planThisLessonPath` |
| `backend/app/Actions/TeacherLessonPlans/SaveTeacherLessonPlan.php`, `app/Http/Requests/TeacherLessonPlan/StoreRequest.php` | Save, versioning and provenance |
| `backend/database/migrations/2026_09_27_120000_rename_teacher_lesson_plans_tables_to_ai_prefix.php` | Table rename (7524) |
| `frontend-v3/ai/context/pacing.ts`, `backend/app/Services/Pacing/ClassPacing.php`, `PacingStatement.php`, `app/Http/Controllers/PacingController.php` | `formatPacing`, `analyse`, `expected` / `actual`, `replan` |
| `backend/app/Services/ScoutActions/Handlers/ReplanHandler.php` | Confirmed replan |
| `frontend-v3/ai/services/lessonPack.ts`, `ai/services/slideDeck.ts`, `ai/components/AiArtifactCard.vue` | `packView`, `deckView`, `print` (7761, 7759) |
| `backend/app/Services/ScoutAssignments/ArticleSlideSource.php`, `WeekSlideSource.php`, `WalkthroughDraft.php` | Slide sources from articles and weeks (7759, 7854) |
| `frontend-v3/pages/teacher/classrooms/[classroom_id]/calendar/[publication_id].vue` | Planning calendar page; `writePlacements`, `saveDay` |
| `frontend-v3/components/calendar/PlanningCalendar{DayDialog,ImportDialog,DayCell,Legend}.vue`, `utils/planningCalendar.ts` | `autoFillRows`, `DAY_KINDS`, `importFileProblem` |
| `frontend-v3/ai/context/scoutCalendar.ts`, `backend/app/Services/PlanningCalendar/CalendarOverview.php` | `formatCalendar`, `formatBehind` |
| `backend/app/Services/ScoutActions/Handlers/CalendarScheduleHandler.php` | Confirmed calendar changes |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/engines/compose.py`, `src/core/prompts/engines/compose.py` | `compose`, `assess_criteria_support`, `revise_document`, `customization_rules` |
| `src/core/tools/write_artifact.py` | `WriteArtifactTool`, `_grade_for_write` (7752) |
| `src/core/tools/prepare_lesson.py` | `PrepareLessonTool`, `build_pack` |
| `src/core/tools/lesson_pack.py` | `make_pack`, `_run_part`, `_settle_grade` (7761) |
| `src/core/engines/plan_build.py` | `build`, `valid_additions`: builds on the SW lesson plan (7854) |
| `src/core/tools/make_slides.py`, `src/core/engines/slides.py`, `week_slides.py` | `write_deck`, `check_slide`, `render_skeleton` (7759, 7854) |
| `src/core/engines/read_calendar.py` | `CalendarOutcome`, `parse_day`: reads an imported school calendar (7797) |
| `src/utils/publication_scope.py` | `scope_request` |

---

### 3.9 Student insights, reports and family communication

From any page, a teacher can ask who needs help, how a class is doing, how a student is doing, or how standards are covered. Answers show their evidence. Scout also drafts daily briefings, report card comments and family messages, which it can translate.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-7510 | SCOUT-04: student performance insights from any page |  | Done | **Parent** |
| ONLINE-7516 | SCOUT-10: student profiles, question-type patterns, family drafts | Gives a quick picture of one student (strengths, gaps, trends) for conferences, shows results by question type, and drafts messages to families or administrators. | Done | Improvement |
| ONLINE-7517 | SCOUT-11: standards coverage and mastery | Shows which standards have been taught and assessed, and how the class and each student are doing on them, without reading the full standards report. | Done | Improvement |
| ONLINE-7519 | SCOUT-13: daily briefing and notification digest | A short daily summary of what needs attention (grading, students at risk, missing work, pacing). Notifications are grouped so they are quicker to act on. | Done | Improvement |
| ONLINE-7753 | SCOUT-RC: report card comments from the gradebook | Scout drafts report card comments for one student or a whole class, based on the student's real work in the gradebook. | Done | Improvement (QA moves to 7865) |
| ONLINE-7756 | SCOUT-TR: translate family message drafts | Family message drafts can be translated (Spanish first, plus other common languages). The teacher gets the original and the translation side by side. | Done | Follow-up (of 7516) |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `backend/app/Services/StudentInsights/StudentInsights.php`, `Measures.php` | `forTeacher`, `classWide`, `perStudent`, `average` |
| `backend/app/Services/StudentInsights/StudentProfile.php` | `recentResults`, `engagement` (7516) |
| `backend/app/Services/StudentInsights/StandardsInsights.php`, `StandardFacts.php`, `StandardResults.php`, `StandardLinks.php` | `coverage`, `lowestStudents` (7517) |
| `backend/app/Http/Requests/Ai/StudentInsightsRequest.php`, `InsightWindowRules.php` | Validation and date windows |
| `frontend-v3/ai/context/studentInsights.ts`, `studentProfile.ts`, `standardsInsights.ts` | `formatInsights`, `reasonLine`, `formatStudentProfile`, `formatStandards` |
| `frontend-v3/ai/services/studentInsightsClient.ts` | `fetchStudentInsights`, `fetchStudentProfile`, `fetchStandardsInsights` |
| `frontend-v3/components/global/TheNavbar.vue` | `aiInsightsClassroomId`: insights are asked from Scout on any page (the report-page "What stands out" bar was removed on 28 Sep; insights stay in Scout) |
| `frontend-v3/ai/context/briefing.ts`, `notificationGroups.ts`, `ai/components/AiBriefingCard.vue`, `AiNotificationGroups.vue` | `formatBriefing`, `groupNotifications` (7519) |
| `frontend-v3/ai/context/reportCards.ts`, `ai/services/reportCardRun.ts`, `ai/components/AiReportCardCard.vue` | `runReportCardComments`, `studentEvidence` (7753) |
| `frontend-v3/ai/context/drafts.ts`, `commentWording.ts` | `screenDraft`, `reportCardDraft`, `screenCommentWording` |
| `frontend-v3/ai/context/draftTranslation.ts`, `ai/services/translateDraftRun.ts`, `ai/components/AiFamilyTranslationCard.vue` | `checkTranslation`, `runTranslateDraft` (7756) |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/prompts/constitution.py` | Rules for wording about students |
| `src/core/student_subject.py` | `profiled_subject`, `strip_aliases` |
| `src/core/name_claim.py`, `name_scrub.py` | `scrub_chat_request`: no names in requests or drafts |

---

### 3.10 Differentiation and reteaching

Scout suggests flexible groups from evidence, matches leveled readers to each student, explains which wrong answers students chose and what that may mean, and assigns reteach activities after the teacher confirms.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-7518 | SCOUT-12: groups, matched readers and versions |  | Done | **Parent** |
| ONLINE-7520 | SCOUT-14: misconception analysis and reteaching loop |  | Done | **Parent** (QA moves to 7865) |
| ONLINE-7498 | Reteach groups by skill or standard, with a levelled article per group | From an assessment, Scout groups students by the skill or standard they missed. It suggests a reteach activity, and an easier article where helpful, for each group. | Done | Follow-up (QA moves to 7865) |
| ONLINE-7533 | Assign leveled readers online | Teachers can assign a leveled reader (Approaching, On level or Above) to specific students to read online, not only print it. | Done | (listed in 3.4) |
| ONLINE-7534 | SCOUT-SU: record which reading supports students use | Would record which reading supports students actually use (such as audio reading) so Scout can suggest supports. Paused until privacy sign-off. | **Selected** (parked) | Follow-up; needs privacy sign-off |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `backend/app/Services/Differentiation/GroupSuggestions.php`, `LeveledReaders.php` | `selectBasis`, `thirds`, `versionFor` |
| `frontend-v3/ai/context/differentiation.ts`, `ai/services/differentiationClient.ts`, `ai/components/AiDifferentiationCard.vue` | `formatGroups`, `formatReaders`, `fetchGroups`, `applyRosterSplit` |
| `frontend-v3/ai/context/readerGrade.ts`, `ai/context/catalog.ts` | `readersOfferedFor` (7533) |
| `backend/app/Http/Controllers/MisconceptionsController.php`, `app/Services/Misconceptions/ReteachFollowUp.php` | `plans`, `followUp` |
| `backend/app/Models/AiReteachPlan.php`, migration `2026_09_28_120000_create_ai_reteach_plans_table.php` | Reteach plans |
| `backend/app/Services/ScoutActions/Handlers/ReteachAssignHandler.php` | Confirmed reteach assignment, with undo |
| `backend/app/Services/Misconceptions/SkillGroups.php`, `WeekAssessments.php`, `app/Http/Controllers/SkillGroupsController.php` | `forTeacher`, `resolve` ("week N's assessment") (7498) |
| `frontend-v3/ai/context/misconceptions.ts`, `reteach.ts`, `skillGroups.ts` | `formatMisconceptions`, `reteachCapabilities`, `formatSkillGroups` |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/engines/misconceptions.py` | `group_misconceptions` |
| `src/core/tools/draft_assignment.py` | `_level_for_more_support`, `_version_base` (7518) |
| `src/routers/core_router.py` | `misconceptions` endpoint |

---

### 3.11 Grading assistance (built, release pending)

Scout suggests marks and draft feedback for written answers and drawings, groups similar answers so they are graded once, writes rubrics and sample answers, and reviews a whole class's writing. **The teacher always confirms, and Scout never saves a grade on its own.** These features shipped to production on 15 Oct behind `FEATURE_FRONTEND_AI_ASSISTED_GRADING` with their hints hidden. ONLINE-7865 now covers verification and release for all of them.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-7512 | SCOUT-06: grading assistance for written answers |  | Done (hidden) | **Parent** |
| ONLINE-7521 | SCOUT-15: grading drawings and handwritten responses | Extends grading suggestions to drawings and photographed handwriting, only where the question has clear criteria. The teacher still decides the grade. | Done (hidden) | Improvement |
| ONLINE-7754 | SCOUT-RB: rubric for a written question or assignment | Scout writes a rubric for a written question or assignment, based on the actual question and article. It copies cleanly into Docs or Word. | Done (hidden) | Improvement |
| ONLINE-7755 | SCOUT-FB: Grade Now drafts feedback for the student | In Grade Now, Scout drafts written feedback for each student from their actual answer. The teacher reviews it before it goes in the comment box. | Done (hidden) | Improvement |
| ONLINE-7758 | SCOUT-EX: exemplar and non-exemplar answers | Scout writes a strong and a weak sample answer to a written question, so teachers can show students what good work looks like. | Done (hidden) | Improvement |
| ONLINE-7760 | SCOUT-CW: class writing feedback in Grade Now | For a whole class's written answers, Scout drafts a rubric, feedback for each student and suggested scores. The teacher reviews everything before saving. | Done (hidden) | Improvement |
| ONLINE-7865 | Scout grading: finish, verify and release | One ticket to finish, test and fully release all grading features. They are in production but hidden until this is done. | **Backlog** | Follow-up (release) |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `frontend-v3/components/dialogs/QuickGradeDialog.vue` | `aiGradeGroup`, `aiSuggestBatch`, `aiMoveOutOfGroup`, `aiOpenCommentBox` |
| `frontend-v3/components/blocks/ReviewQuestionBlock.vue` | `aiSuggestGrade`, `aiAcceptProposal` |
| `frontend-v3/ai/context/grading.ts`, `quickGrade.ts`, `drawingGrading.ts` | `readProposals`, `capConfidence`, `planDrawingBatch` |
| `frontend-v3/ai/services/gradingClient.ts` | `groupAnswers`, `reviewDrawings` |
| `frontend-v3/ai/components/results/GradeProposalStrip.vue`, `DrawingProposalStrip.vue` | Proposal strips |
| `frontend-v3/ai/utils/rubric.ts`, `ai/components/AiRubricTable.vue` | `rubricView`, `copyRubric` (7754) |
| `frontend-v3/ai/utils/sampleAnswers.ts`, `ai/components/AiSampleAnswers.vue` | `sampleAnswersView` (7758) |
| `frontend-v3/ai/context/feedbackDrafts.ts`, `ai/components/AiFeedbackDraftsCard.vue` | `feedbackCard`, `screenFeedbackDraft` (7755) |
| `frontend-v3/ai/context/classFeedback.ts`, `ai/components/AiClassFeedbackCard.vue` | `planClassSave`, `executeClassSave` (7760) |
| `backend/app/Services/ScoutActions/Handlers/ClassFeedbackSaveHandler.php` | Confirmed class save |
| `backend/app/Models/SubmissionResponse.php` | `aiGradingProposal`, `getAiProposedConfidenceAttribute` |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/engines/grade.py`, `src/core/prompts/engines/grade.py` | `grade_answers`, `_grade_chunk` |
| `src/core/engines/group.py` | `group_ideas`: groups similar answers |
| `src/core/engines/grade_drawings.py` | `review_drawings` (7521) |
| `src/core/tools/grade_answers.py` | `GradeAnswersTool` |
| `src/core/tools/rubric_artifact.py`, `src/core/engines/rubric.py` | `rubric_data`, `render_markdown` (7754) |
| `src/core/tools/sample_answers_artifact.py`, `src/core/engines/sample_answers.py` | `samples_data` (7758) |
| `src/core/guidelines/grading.py`, `src/routers/core_router.py` | `grade`, `group`, `grade_drawings` endpoints |

---

### 3.12 Scout for administrators

District and school admins get a District Insights page and a Scout that answers leadership questions from figures our code computes. The model sees only school, class and teacher totals, never student rows. Scout also drafts a district summary and a principal brief, exportable as PDF or CSV.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-7798 | Admin Scout: plan (question list, data completeness, privacy) | The plan for an administrator version of Scout: which leadership questions it should answer, whether our data supports them, and the privacy rules. | Done | **Parent** (plan) |
| ONLINE-7806 | Admin Scout: district and school figures, 14 questions, summary, brief, classroom practice |  | Done (checked in production) | **Parent** (build) |
| ONLINE-7856 | District Insights: explain averages, custom date range, reading tile | District Insights explains how each averaged number is calculated, allows a custom date range, and adds a reading-comprehension tile. | Done | Follow-up |
| ONLINE-7814 | Scout exports: any answer as CSV or PDF | Would let teachers and admins download any Scout answer: numbers as a spreadsheet (CSV) and text as a PDF. Not started. | **Backlog** | Improvement |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `backend/app/Http/Controllers/AdminInsightsController.php` | `index`, `context`, `export`, `walkthroughs`, `windowFilters` |
| `backend/app/Services/AdminInsights/AdminDigest.php`, `DistrictFigures.php`, `FigureStore.php`, `AdminExports.php` | `build`, `reading`, `getOrQueue`, `csv`, `pdf` |
| `backend/app/Jobs/Ai/BuildAdminDistrictFigures.php`, `app/Console/Commands/PrewarmAdminFigures.php` | Figure computation in the background (7856) |
| `frontend-v3/components/insights/InsightsPage.vue` | `askScout`, `windowFilters`, `coverageNote` |
| `frontend-v3/components/districtadmin/reports/ReportTabs.vue`, `schooladmin/reports/SchoolReportTabs.vue` | `show_insights` tab |
| `frontend-v3/utils/aiAssistantAccess.ts` | `showAdminAssistant`, `scoutAudience` |
| `frontend-v3/ai/scout.ts`, `ai/stores/aiAssistant.ts`, `ai/services/coreAudience.ts` | `askScoutAboutInsights`, `openAdmin`, `setAudience` |

**rag**

| File | Key functions / purpose |
|---|---|
| `src/core/admin/turn.py` | `run_admin_turn`, `stream_admin_turn`, `context_block`, `date_range` |
| `src/core/admin/tools.py` | `AdminFigures`, `AdminExport` |
| `src/core/admin/constitution.py`, `src/core/admin/screens.py` | Admin rules; `Provenance` and `Claims` screens |
| `src/routers/core_router.py` | `admin_turn` |

---

### 3.13 Cost, speed and model choice

The work in this area measured what Scout costs, made it cheaper and faster, and capped spending per teacher.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-6859 | Model comparison report: accuracy and cost (Nova Micro vs larger) | A report comparing AI models on accuracy, speed and cost. For the original v1 assistant, it found the low-cost model got about 90% of requests right at a small fraction of the cost. Scout Core v2 later moved to Claude models. | Done | **Parent** (research) |
| ONLINE-7526 | SCOUT-S: dollar cap, cache the conversation, measure real turns | Lowers Scout's cost per question and speeds up replies by reusing work already done in a conversation. Adds a daily dollar limit per teacher. | Done | **Parent** |
| ONLINE-7528 | SCOUT-P: page switches stop re-paying the cached prompt | Moving between pages no longer makes Scout re-send a large block of instructions, which lowers cost. What Scout can do on each page is unchanged. | Done | Follow-up (of 7526) |
| ONLINE-7588 | SCOUT-PA: prompt restructure (shared core, rules travel with the feature) | Reorganises Scout's instructions so each feature's rules load only when that feature is used. Every question costs less and the prompt stops growing with each new feature. | Done | Improvement |
| ONLINE-7525 | SCOUT-C: shared response cache and cheaper labelling for evaluations | Saves money during internal testing: repeated test questions reuse earlier answers, and each test run shows its cost before it starts. | Done | Improvement (test cost) |
| ONLINE-7857 | Measured cost per tool and a weekly usage cap per teacher | Measures what each Scout feature costs, and limits each teacher to $2.50 of AI cost per week (about $80 a year for a typical teacher). | Done | Improvement |
| ONLINE-7874 | Access and licensing: district opt-in, seats, school-year licenses, pilots | Would let districts switch Scout on, buy and assign seats to teachers, renew yearly and run 30-day pilots. Required before selling Scout; not started. | **Backlog** | Follow-up (split from 7857) |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `docs/AiAssistantModelEvaluation.md` | Full model comparison (6859) |
| `frontend-v3/ai/utils/errorMessages.ts` | `limitMessage`, `weeklyResetMessage` (7857) |
| `backend/app/Http/Controllers/AiController.php`, `app/Models/User.php` | `hasStaffEmail` (staff exempt from the cap) |

**rag**

| File | Key functions / purpose |
|---|---|
| `experiments/model_eval/` | Scripts behind the model comparison (6859) |
| `src/services/daily_usage_service.py` | `record_usage`, `check_spend_limits`, `_spend_this_week`, `settle_usage` |
| `src/core/lambda_stream.py` | `CoreAuthMiddleware`, `CreditsVerifier`, `check_daily_limit` |
| `src/core/loop.py` | `with_history_cache_point`, `build_request` (7526) |
| `src/core/cache_layers.py` | `fingerprints` |
| `src/core/tools/page_action.py` | `_spec`: page actions moved out of the cached tool definition (7528) |
| `src/core/prompt_registry.py` / `.json`, `src/core/prompts/constitution.py` | Rule registry and shared core (7588) |
| `lambdas/authorizer/src/services/credits_service.py`, `auth_service.py` | Credit checks at API Gateway |
| `infra/swo/modules/cloudwatch-dashboard/main.tf` | Per-turn cost and latency dashboard |

---

### 3.14 Feedback and quality loop

Teachers rate answers with thumbs up or down and give a reason. Admins review negative feedback and failed turns, and a reviewed case can be turned into a regression test.

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-6282 | AI thumbs up/down (feedback modal) | Adds thumbs up and down to Scout's answers. A thumbs down opens a short form asking what was wrong. | Done | **Parent** (early) |
| ONLINE-6553 | AI feedback report: show negative feedback content | In the AI feedback report, admins can open a negative rating and see the exact AI text that was flagged and who flagged it. | Done | Improvement |
| ONLINE-7495 | Quality loop from thumbs-down and failed turns | Gives the team a review list of poorly rated answers and failed requests. Real problems can be added to our automatic test set. | Done | Improvement |
| ONLINE-7744 | `AiScoutFeedbackReportTest` flaky due to a shared Redis cache | Fixes an automated test that failed at random. No change for users. | Done | Follow-up (test fix) |

**swo-3.0**

| File | Key functions / purpose |
|---|---|
| `frontend-v3/ai/components/AiMessageActions.vue`, `ai/composables/useAiFeedback.ts`, `components/dialogs/FeedbackFormInline.vue` | Thumbs up/down and reasons (6282) |
| `backend/app/Http/Controllers/AiReportController.php` | `getFeedbackResponse`, `getFeedbackAssistant`, `getFeedbackAssistantFailures` |
| `frontend-v3/pages/teacher/account/ai-playground/reports-feedback.vue` | `loadFeedback`, `copyTestCase` |
| `frontend-v3/components/dialogs/NegativeFeedbackDialog.vue` | Negative feedback detail (6553) |
| `frontend-v3/utils/scoutTestCase.ts`, `ai/services/failedTurnLog.ts` | `buildTestCase`: promote a case to the regression set (7495) |

**rag**

| File | Key functions / purpose |
|---|---|
| `experiments/teacher_eval/tasks.py`, `fixtures/reviewed_cases.json` | `_reviewed_cases`: reviewed cases join the evaluation set |

---

### 3.15 Infrastructure and housekeeping

| Ticket | Title | What it does | Status | Role |
|---|---|---|---|---|
| ONLINE-7497 | Terraform: upgrade AWS provider to 6.x | Updates our cloud infrastructure tooling to the current version and removes a manual workaround. No change for users. | Done | Housekeeping |
| ONLINE-7801 | rag cleanup: one test runner and CI, dead code out, one settings module | Would tidy the AI service's code for an outside review: one way to run the tests, unused code removed and clearer structure. Not started. | **Selected** | Housekeeping (needs decisions before phases 7–8) |
| ONLINE-7524 | Rename lesson-plan tables with `ai_` | Renames the lesson-plan database tables so all AI-related data is grouped under one recognisable name. No visible change for teachers. | Done | (listed in 3.8) |

**rag:** `infra/swo/versions.tf`, `infra/swo/bootstrap/versions.tf`, `infra/swo/modules/ecs-fargate-task/main.tf` (7497).

---

## 4. Full ticket index

| Ticket | Title (short) | Status | Feature area | swo commits | rag commits |
|---|---|---|---|---|---|
| ONLINE-6282 | Thumbs up/down | Done | 3.14 | n/a | n/a |
| ONLINE-6300 | Text leveler training | Selected | 3.6 | n/a | 1 |
| ONLINE-6301 | Unknown grade of text | Done | 3.6 | n/a | n/a |
| ONLINE-6553 | Negative feedback report | Done | 3.14 | 2 | n/a |
| ONLINE-6797 | Question generator improvements | Done | 3.7 | n/a | n/a |
| ONLINE-6806 | Chat modal persistent and movable | Done | 3.1 | n/a | n/a |
| ONLINE-6841 | Chat result improvements | Done | 3.5 | n/a | n/a |
| ONLINE-6857 | Page/DOM awareness (umbrella) | Done | 3.1 | 1,796 | 1,105 |
| ONLINE-6859 | Model comparison report | Done | 3.13 | n/a | n/a |
| ONLINE-7404 | Custom lesson plan | Done | 3.8 | 63 | 23 |
| ONLINE-7490 | Resources by publication, unit, week | Done | 3.5 | 10 | 21 |
| ONLINE-7495 | Quality loop | Done | 3.14 | 7 | 1 |
| ONLINE-7497 | Terraform AWS provider 6.x | Done | 3.15 | n/a | 1 |
| ONLINE-7498 | Reteach groups by skill or standard | Done | 3.10 | 8 | 12 |
| ONLINE-7499 | Rich media previews | Done | 3.5 | 12 | 7 |
| ONLINE-7507 | SCOUT-01 Honest, evidence-based | Done | 3.2 | 14 | 34 |
| ONLINE-7508 | SCOUT-02 Remembers teacher context | Done | 3.3 | 14 | 46 |
| ONLINE-7509 | SCOUT-03 Teacher-confirmed actions | Done | 3.4 | 64 | 12 |
| ONLINE-7510 | SCOUT-04 Student insights | Done | 3.9 | 35 | 26 |
| ONLINE-7511 | SCOUT-05 Content discovery and teaching sets | Done | 3.5 | 27 | 48 |
| ONLINE-7512 | SCOUT-06 Grading written answers | Done (hidden) | 3.11 | 21 | 22 |
| ONLINE-7514 | SCOUT-08 Assignment creation | Done | 3.7 | 44 | 16 |
| ONLINE-7515 | SCOUT-09 Pacing and week planning | Done | 3.8 | 19 | 20 |
| ONLINE-7516 | SCOUT-10 Student profiles and family drafts | Done | 3.9 | 13 | 12 |
| ONLINE-7517 | SCOUT-11 Standards coverage | Done | 3.9 | 12 | 10 |
| ONLINE-7518 | SCOUT-12 Differentiation | Done | 3.10 | 17 | 11 |
| ONLINE-7519 | SCOUT-13 Daily briefing | Done | 3.9 | 10 | 7 |
| ONLINE-7520 | SCOUT-14 Misconceptions and reteach | Done | 3.10 | 12 | 11 |
| ONLINE-7521 | SCOUT-15 Grading drawings | Done (hidden) | 3.11 | 8 | 5 |
| ONLINE-7522 | SCOUT-H Hints per step or tab | Done | 3.1 | 10 | 5 |
| ONLINE-7523 | SCOUT-T Spotlight tour | Done | 3.1 | 11 | n/a |
| ONLINE-7524 | SCOUT-L `ai_` table rename | Done | 3.8 | 2 | n/a |
| ONLINE-7525 | SCOUT-C Evaluation cache | Done | 3.13 | n/a | 7 |
| ONLINE-7526 | SCOUT-S Cost and speed | Done | 3.13 | n/a | 10 |
| ONLINE-7528 | SCOUT-P Page-switch caching | Done | 3.13 | n/a | 4 |
| ONLINE-7529 | SCOUT-G Guardrail tier | Done | 3.2 | n/a | 7 |
| ONLINE-7532 | SCOUT-SS Suggest standards | Done | 3.7 | 12 | 18 |
| ONLINE-7533 | SCOUT-LR Leveled readers online | Done | 3.4 | 6 | 9 |
| ONLINE-7534 | SCOUT-SU Reading-support usage | Selected (parked) | 3.10 | n/a | n/a |
| ONLINE-7535 | Stable student aliases | Done | 3.2 | 35 | 5 |
| ONLINE-7565 | @-mention students | Done | 3.1 | 4 | n/a |
| ONLINE-7567 | Several questions at once | Done | 3.7 | 10 | 11 |
| ONLINE-7577 | SCOUT-UI Design polish | Done | 3.1 | 15 | n/a |
| ONLINE-7578 | SCOUT-PR Production readiness | Done | 3.2 | 62 | 87 |
| ONLINE-7579 | SCOUT-MV Move students | Done | 3.4 | 3 | 3 |
| ONLINE-7580 | SCOUT-NA Navigate and act | Done | 3.1 | 5 | 12 |
| ONLINE-7581 | SCOUT-SP Search page search | Done | 3.1 | n/a | 7 |
| ONLINE-7582 | SCOUT-CA New class is active | Done | 3.1 | 1 | 1 |
| ONLINE-7584 | SCOUT-Z Dropdown layering | Done | 3.1 | 1 | n/a |
| ONLINE-7588 | SCOUT-PA Prompt restructure | Done | 3.13 | 1 | 17 |
| ONLINE-7744 | Flaky feedback report test | Done | 3.14 | 2 | n/a |
| ONLINE-7752 | Lesson plan form fixes | Done | 3.8 | 7 | 7 |
| ONLINE-7753 | SCOUT-RC Report card comments | Done | 3.9 | 11 | 13 |
| ONLINE-7754 | SCOUT-RB Rubrics | Done (hidden) | 3.11 | 4 | 8 |
| ONLINE-7755 | SCOUT-FB Student feedback drafts | Done (hidden) | 3.11 | 7 | 11 |
| ONLINE-7756 | SCOUT-TR Translate family drafts | Done | 3.9 | 10 | 12 |
| ONLINE-7757 | SCOUT-DOK DOK mix | Testing | 3.7 | 4 | 23 |
| ONLINE-7758 | SCOUT-EX Exemplar answers | Done (hidden) | 3.11 | 2 | 12 |
| ONLINE-7759 | SCOUT-SL Lesson walkthrough | Testing | 3.8 | 11 | 22 |
| ONLINE-7760 | SCOUT-CW Class writing feedback | Done (hidden) | 3.11 | 10 | 6 |
| ONLINE-7761 | SCOUT-PK Lesson pack | Done | 3.8 | 11 | 65 |
| ONLINE-7762 | SCOUT-SC Saved shortcuts | Testing | 3.3 | 9 | 9 |
| ONLINE-7767 | SCOUT-QT Drawing and Hot Text | Testing | 3.7 | 4 | 11 |
| ONLINE-7797 | Yearly planning calendar | Done | 3.8 | 86 | 3 |
| ONLINE-7798 | Admin Scout plan | Done | 3.12 | n/a | n/a |
| ONLINE-7801 | rag code-structure cleanup | Selected | 3.15 | n/a | n/a |
| ONLINE-7806 | Admin Scout build | Done | 3.12 | 29 | 14 |
| ONLINE-7814 | Scout exports CSV/PDF | Backlog | 3.12 | n/a | n/a |
| ONLINE-7853 | Level text button | Done | 3.6 | 2 | 2 |
| ONLINE-7854 | Build on SW lesson plans; richer slides | Done | 3.8 | 6 | 116 |
| ONLINE-7855 | Calendar Auto-fill, day types | Done | 3.8 | 9 | 1 |
| ONLINE-7856 | District Insights follow-ups | Done | 3.12 | 5 | 1 |
| ONLINE-7857 | Cost per tool and weekly cap | Done | 3.13 | 2 | 4 |
| ONLINE-7865 | Grading release | Backlog | 3.11 | n/a | n/a |
| ONLINE-7874 | Access and licensing | Backlog | 3.13 | n/a | n/a |

*n/a means no commits carry this ticket key. The early tickets (6282, 6301, 6797, 6806, 6841) were built before per-ticket commit tagging, or under the ONLINE-6857 umbrella. Their files in section 3 show where that work lives in the current code. 6798 and 6859 produced a plan and a report, not code. Commit counts include every branch.*
