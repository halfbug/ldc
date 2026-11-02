#!/usr/bin/env bash
# ONLINE-7532 API checks against dev2. Read-only on Laravel; the rag checks all fail validation
# before any model call, so nothing here costs AI credits or writes data.
#
# Usage (in your own terminal):
#   export SWO_TOKEN='eyJ...'                 # teacher token (Authorization header, without "Bearer ")
#   export CLASSROOM_ID='<uuid>'              # optional: a classroom this teacher teaches
#   export OTHER_CLASSROOM_ID='<uuid>'        # optional: another district's / school's classroom
#   export OTHER_ASSIGNMENT_ID='<id>'         # optional: another teacher's customized content
#   export STUDENT_TOKEN='eyJ...'             # optional: a student's token
#   export ADMIN_TOKEN='eyJ...'               # optional: a non-teacher admin's token
#   export NOFLAG_TOKEN='eyJ...'              # optional: a teacher without feature_frontend_ai_assistant
#   export RAG_URL='https://.../v2/standards/suggest?host=...'   # optional: copied from the Network tab
#   bash ONLINE-7532-api-tests.sh

set -u
API="${API:-https://dev2-online-api.studiesweekly.com/api/ai/standards/candidates}"
PASS=0; FAIL=0; SKIP=0

if [ -z "${SWO_TOKEN:-}" ]; then echo "Set SWO_TOKEN first (see the top of this file)."; exit 2; fi

# check <name> <expected status> <token or ""> <url> <body> [text the response must contain]
check() {
    local name="$1" want="$2" token="$3" url="$4" body="$5" expect="${6:-}"
    local auth=()
    [ -n "$token" ] && auth=(-H "Authorization: Bearer ${token#Bearer }")
    local out code
    out=$(curl -s -w $'\n%{http_code}' -X POST "$url" "${auth[@]}" \
        -H 'Accept: application/json' -H 'Content-Type: application/json' \
        -H 'Origin: https://dev2-online.studiesweekly.com' --data-raw "$body")
    code="${out##*$'\n'}"; out="${out%$'\n'*}"
    if [ "$code" = "$want" ] && { [ -z "$expect" ] || printf '%s' "$out" | grep -qF -- "$expect"; }; then
        PASS=$((PASS + 1)); printf 'PASS  %-58s %s\n' "$name" "$code"
    else
        FAIL=$((FAIL + 1)); printf 'FAIL  %-58s got %s, want %s %s\n' "$name" "$code" "$want" "${expect:+containing \"$expect\"}"
    fi
    printf '      %s\n' "$(printf '%s' "$out" | head -c 300)"
    [ -n "${RAG_PAUSE:-}" ] && sleep "$RAG_PAUSE"
    return 0
}

skip() { SKIP=$((SKIP + 1)); printf 'SKIP  %-58s (set %s)\n' "$1" "$2"; }

echo "== Laravel: $API"
check "Guest is unauthenticated"                         401 ""           "$API" '{"search_text":"rivers"}'
check "422: search_text missing"                         422 "$SWO_TOKEN" "$API" '{}' 'search text field is required'
check "422: classroom_id is not a uuid"                  422 "$SWO_TOKEN" "$API" '{"classroom_id":"abc","search_text":"rivers"}'
check "422: grade out of range (13)"                     422 "$SWO_TOKEN" "$API" '{"grade":13,"search_text":"rivers"}'
check "422: assignment_id is 0"                          422 "$SWO_TOKEN" "$API" '{"assignment_id":0,"search_text":"rivers"}'
check "404: unknown classroom"                           404 "$SWO_TOKEN" "$API" '{"classroom_id":"00000000-0000-4000-8000-000000000000","search_text":"rivers"}'
check "200: chat-shaped ask, grade 4, no classroom"      200 "$SWO_TOKEN" "$API" '{"grade":4,"search_text":"primary and secondary sources"}'

if [ -n "${CLASSROOM_ID:-}" ]; then
    check "200: own classroom"                           200 "$SWO_TOKEN" "$API" "{\"classroom_id\":\"$CLASSROOM_ID\",\"search_text\":\"rivers settlers\"}"
else skip "200: own classroom" CLASSROOM_ID; fi
if [ -n "${OTHER_CLASSROOM_ID:-}" ]; then
    check "403: another district's / school's classroom" 403 "$SWO_TOKEN" "$API" "{\"classroom_id\":\"$OTHER_CLASSROOM_ID\",\"search_text\":\"rivers\"}"
else skip "403: another district's / school's classroom" OTHER_CLASSROOM_ID; fi
if [ -n "${OTHER_ASSIGNMENT_ID:-}" ] && [ -n "${CLASSROOM_ID:-}" ]; then
    check "403: another teacher's customized content"    403 "$SWO_TOKEN" "$API" "{\"classroom_id\":\"$CLASSROOM_ID\",\"assignment_id\":$OTHER_ASSIGNMENT_ID,\"search_text\":\"rivers\"}"
else skip "403: another teacher's customized content" "OTHER_ASSIGNMENT_ID and CLASSROOM_ID"; fi
if [ -n "${STUDENT_TOKEN:-}" ]; then
    check "403: student"                                 403 "$STUDENT_TOKEN" "$API" '{"search_text":"rivers"}'
else skip "403: student" STUDENT_TOKEN; fi
if [ -n "${ADMIN_TOKEN:-}" ]; then
    check "403: admin who is not a teacher"              403 "$ADMIN_TOKEN" "$API" '{"search_text":"rivers"}'
else skip "403: admin who is not a teacher" ADMIN_TOKEN; fi
if [ -n "${NOFLAG_TOKEN:-}" ]; then
    check "404: AI flag off hides the route"             404 "$NOFLAG_TOKEN" "$API" '{"search_text":"rivers"}'
else skip "404: AI flag off hides the route" NOFLAG_TOKEN; fi

echo
if [ -n "${RAG_URL:-}" ] && [[ "$RAG_URL" != *"/v2/standards/suggest"* ]]; then
    echo "RAG_URL must be the Suggest Standards request (…/assistant/v2/standards/suggest?host=…),"
    echo "copied from the Network tab after clicking Suggest Standards. Got: ${RAG_URL%%\?*}"
    FAIL=$((FAIL + 1))
elif [ -n "${RAG_URL:-}" ]; then
    echo "== rag: ${RAG_URL%%\?*}"
    echo "   (13s between calls: rag allows 5 standards requests a minute and counts invalid ones too)"
    RAG_PAUSE=13
    many=$(python3 -c 'import json;print(json.dumps({"questions":[{"ref":f"q{i}","text":"Why do rivers flood?"} for i in range(31)]}))')
    long=$(python3 -c 'import json;print(json.dumps({"questions":[{"ref":"q1","text":"a"*2001}]}))')
    check "422: no questions"                            422 "$SWO_TOKEN" "$RAG_URL" '{"questions":[]}' 'Send at least one question.'
    check "422: 31 questions (cap is 30)"                422 "$SWO_TOKEN" "$RAG_URL" "$many" 'Send at most 30 questions'
    check "422: duplicate ref"                           422 "$SWO_TOKEN" "$RAG_URL" '{"questions":[{"ref":"q1","text":"a"},{"ref":"q1","text":"b"}]}' 'Each question ref must be unique.'
    check "422: empty text"                              422 "$SWO_TOKEN" "$RAG_URL" '{"questions":[{"ref":"q1","text":""}]}' 'Every question needs a ref and its text.'
    check "422: text over 2000 characters"               422 "$SWO_TOKEN" "$RAG_URL" "$long" 'at most 2000 characters'
    check "422: assignment_id not a number"              422 "$SWO_TOKEN" "$RAG_URL" '{"questions":[{"ref":"q1","text":"Why do rivers flood?"}],"assignment_id":"abc"}' 'assignment_id must be a number.'
    check "400: body is not JSON (deployed front door)"                     400 "$SWO_TOKEN" "$RAG_URL" 'not json' "couldn't be read"
else
    skip "rag validation checks (7)" RAG_URL
fi

echo
echo "PASS $PASS  FAIL $FAIL  SKIP $SKIP"
[ "$FAIL" -eq 0 ]
