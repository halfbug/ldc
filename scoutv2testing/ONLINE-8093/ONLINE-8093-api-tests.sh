#!/usr/bin/env bash
# ONLINE-8093 API checks against dev. Read-only on Laravel (the one POST fails validation before any write);
# every rag check is refused before the body is read or a model is called, so nothing here costs AI credits
# or writes data.
#
# Usage (in your own terminal):
#   export SWO_TOKEN='eyJ...'                 # teacher token (Authorization header, without "Bearer ")
#   export ADMIN_TOKEN='eyJ...'               # optional: district admin with both Scout flags
#   export SCHOOL_ADMIN_TOKEN='eyJ...'        # optional: school admin with both Scout flags
#   export NOFLAG_TOKEN='eyJ...'              # optional: a teacher without feature_frontend_ai_assistant
#   export GW_URL='https://<api-id>.execute-api.us-west-2.amazonaws.com/dev/v3/assistant/thread/listing?host=...'
#                                             # optional: a sidebar request copied from the Network tab
#   export CORE_URL='https://<id>.lambda-url.us-west-2.on.aws/assistant/v2/turn?host=...'
#                                             # optional: a chat turn request copied from the Network tab
#   bash ONLINE-8093-api-tests.sh

set -u
API="${API:-https://dev2-online-api.studiesweekly.com/api/ai}"
PASS=0; FAIL=0; SKIP=0

if [ -z "${SWO_TOKEN:-}" ]; then echo "Set SWO_TOKEN first (see the top of this file)."; exit 2; fi

# [METHOD=GET] check <name> <expected status> <token or ""> <url> <body> [text the response must contain]
check() {
    local name="$1" want="$2" token="$3" url="$4" body="$5" expect="${6:-}" method="${METHOD:-POST}"
    local auth=() data=()
    [ -n "$token" ] && auth=(-H "Authorization: Bearer ${token#Bearer }")
    [ "$method" != "GET" ] && data=(--data-raw "$body")
    local out code
    out=$(curl -s -w $'\n%{http_code}' -X "$method" "$url" "${auth[@]}" \
        -H 'Accept: application/json' -H 'Content-Type: application/json' \
        -H 'Origin: https://dev2-online.studiesweekly.com' "${data[@]}")
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
METHOD=GET check "Guest is unauthenticated (user/credits)"      401 ""           "$API/user/credits" ''
METHOD=GET check "200: teacher credits"                         200 "$SWO_TOKEN" "$API/user/credits" '' 'credit'
METHOD=GET check "403: teacher on admin/context"                403 "$SWO_TOKEN" "$API/admin/context" ''
big=$(python3 -c 'import json;print(json.dumps({"response":{"x":"a"*(513*1024)}}))')
check "422: stats response over 512 KB (nothing written)"       422 "$SWO_TOKEN" "$API/stats" "$big" 'may not be larger than 512 KB'

# AiUnusedRoutesRemovedTest: every one of these is gone.
check            "404: removed POST generate/question"          404 "$SWO_TOKEN" "$API/generate/question" '{}'
check            "404: removed POST article/difficulty"         404 "$SWO_TOKEN" "$API/article/difficulty" '{}'
check            "404: removed POST adapt"                      404 "$SWO_TOKEN" "$API/adapt" '{}'
METHOD=GET check "404: removed GET random-article"              404 "$SWO_TOKEN" "$API/random-article" ''
check            "404: removed POST credits/purchase"           404 "$SWO_TOKEN" "$API/credits/purchase" '{}'
METHOD=GET check "404: removed GET credits/expire"              404 "$SWO_TOKEN" "$API/credits/expire" ''
check            "404: removed POST feedback"                   404 "$SWO_TOKEN" "$API/feedback" '{"rating":1,"ai_feature":"adapt_content"}'
METHOD=GET check "404: removed GET credits/packages"            404 "$SWO_TOKEN" "$API/credits/packages" ''
check            "404: removed POST user/credits/redeem"        404 "$SWO_TOKEN" "$API/user/credits/redeem" '{"code":"unused"}'
METHOD=GET check "404: removed GET search-index/1"              404 "$SWO_TOKEN" "$API/search-index/1" ''

if [ -n "${ADMIN_TOKEN:-}" ]; then
    METHOD=GET check "404: district admin on teacher-only user/credits" 404 "$ADMIN_TOKEN" "$API/user/credits" ''
    METHOD=GET check "200: district admin admin/context"        200 "$ADMIN_TOKEN" "$API/admin/context" ''
else skip "district admin: user/credits 404, admin/context 200" ADMIN_TOKEN; fi
if [ -n "${SCHOOL_ADMIN_TOKEN:-}" ]; then
    METHOD=GET check "404: school admin on teacher-only user/credits" 404 "$SCHOOL_ADMIN_TOKEN" "$API/user/credits" ''
    METHOD=GET check "200: school admin admin/context"          200 "$SCHOOL_ADMIN_TOKEN" "$API/admin/context" ''
else skip "school admin: user/credits 404, admin/context 200" SCHOOL_ADMIN_TOKEN; fi
if [ -n "${NOFLAG_TOKEN:-}" ]; then
    METHOD=GET check "404: AI flag off (user/credits)"          404 "$NOFLAG_TOKEN" "$API/user/credits" ''
else skip "404: AI flag off (user/credits)" NOFLAG_TOKEN; fi

echo
if [ -n "${GW_URL:-}" ] && [[ "$GW_URL" != *"/v3/assistant/thread/"* ]]; then
    echo "GW_URL must be a sidebar request (…/v3/assistant/thread/listing?host=…) copied from the Network tab."
    echo "Got: ${GW_URL%%\?*}"
    FAIL=$((FAIL + 1))
elif [ -n "${GW_URL:-}" ]; then
    base="${GW_URL%%/v3/assistant/*}"; query="?${GW_URL#*\?}"
    echo "== API Gateway: $base (13s between calls)"
    RAG_PAUSE=13
    check "400: thread/messages without thread_id"              400 "$SWO_TOKEN" "$base/v3/assistant/thread/messages$query" '{}' 'thread_id is required'
    check "404: unprefixed /assistant route is gone"            404 "$SWO_TOKEN" "$base/assistant/thread/listing$query" '{}' 'Not Found'
    check "404: /v3/generate is gone"                           404 "$SWO_TOKEN" "$base/v3/generate$query" '{}' 'Not Found'
    check "404: /v3/generate-from-topic is gone"                404 "$SWO_TOKEN" "$base/v3/generate-from-topic$query" '{}' 'Not Found'
    RAG_PAUSE=
else
    skip "API Gateway checks (4)" GW_URL
fi

echo
if [ -n "${CORE_URL:-}" ] && [[ "$CORE_URL" != *"/assistant/v2/turn"* ]]; then
    echo "CORE_URL must be a chat turn request (…/assistant/v2/turn?host=…) copied from the Network tab."
    echo "Got: ${CORE_URL%%\?*}"
    FAIL=$((FAIL + 1))
elif [ -n "${CORE_URL:-}" ]; then
    root="${CORE_URL%%/assistant/v2/turn*}"; query="?${CORE_URL#*\?}"
    echo "== Function URL: $root (13s between calls; auth is checked before the body, so no model call)"
    RAG_PAUSE=13
    check "401: no token on /v2/turn"                           401 ""           "$root/assistant/v2/turn$query" '{}' 'not_signed_in'
    check "403: teacher on the admin door"                      403 "$SWO_TOKEN" "$root/assistant/v2/admin/turn$query" '{}' 'scout_off'
    check "404: path outside /assistant/v2/"                    404 "$SWO_TOKEN" "$root/assistant/v1/turn$query" '{}' 'not_found'
    RAG_PAUSE=
else
    skip "Function URL checks (3)" CORE_URL
fi

echo
echo "PASS $PASS  FAIL $FAIL  SKIP $SKIP"
[ "$FAIL" -eq 0 ]
