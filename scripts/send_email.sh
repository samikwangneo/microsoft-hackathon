#!/usr/bin/env bash
#
# send_email.sh — send a plain-text email for PatchPilot.
#
# Usage:
#   send_email.sh --to <addr> --subject <subject> [--from <addr>] [--body-file <path>]
#
# The body is read from --body-file if given, otherwise from stdin.
#
# Delivery strategy (first that works wins):
#   1. If SMTP_* env vars are set and `curl` is available, send via SMTP.
#   2. Else if `sendmail` is available, pipe an RFC-822 message to it.
#   3. Else fall back to writing the message to the local outbox directory
#      (PATCHPILOT_OUTBOX, default ./outbox) so a demo run always produces an
#      artifact and never silently fails.
#
# SMTP env vars (all required to use strategy 1):
#   SMTP_URL       e.g. smtps://smtp.gmail.com:465
#   SMTP_USER      SMTP username
#   SMTP_PASSWORD  SMTP password / app token
#
set -euo pipefail

TO=""
SUBJECT=""
FROM="${PATCHPILOT_FROM:-patchpilot@localhost}"
BODY_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --to)        TO="$2"; shift 2 ;;
    --subject)   SUBJECT="$2"; shift 2 ;;
    --from)      FROM="$2"; shift 2 ;;
    --body-file) BODY_FILE="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$TO" || -z "$SUBJECT" ]]; then
  echo "Error: --to and --subject are required" >&2
  exit 2
fi

# Read body from file or stdin into a temp file.
BODY_TMP="$(mktemp)"
trap 'rm -f "$BODY_TMP"' EXIT
if [[ -n "$BODY_FILE" ]]; then
  cat "$BODY_FILE" > "$BODY_TMP"
else
  cat > "$BODY_TMP"
fi

build_message() {
  printf 'From: %s\n' "$FROM"
  printf 'To: %s\n' "$TO"
  printf 'Subject: %s\n' "$SUBJECT"
  printf 'Content-Type: text/plain; charset=UTF-8\n'
  printf '\n'
  cat "$BODY_TMP"
}

# Strategy 1: SMTP via curl.
if [[ -n "${SMTP_URL:-}" && -n "${SMTP_USER:-}" && -n "${SMTP_PASSWORD:-}" ]] && command -v curl >/dev/null 2>&1; then
  MSG_TMP="$(mktemp)"
  build_message > "$MSG_TMP"
  if curl --silent --show-error --ssl-reqd \
        --url "$SMTP_URL" \
        --user "${SMTP_USER}:${SMTP_PASSWORD}" \
        --mail-from "$FROM" \
        --mail-rcpt "$TO" \
        --upload-file "$MSG_TMP"; then
    rm -f "$MSG_TMP"
    echo "Email sent to $TO via SMTP"
    exit 0
  fi
  rm -f "$MSG_TMP"
  echo "SMTP send failed; falling back" >&2
fi

# Strategy 2: local sendmail.
if command -v sendmail >/dev/null 2>&1; then
  if build_message | sendmail -t; then
    echo "Email sent to $TO via sendmail"
    exit 0
  fi
  echo "sendmail failed; falling back" >&2
fi

# Strategy 3: write to the outbox.
OUTBOX="${PATCHPILOT_OUTBOX:-./outbox}"
mkdir -p "$OUTBOX"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUTFILE="${OUTBOX}/email-${STAMP}.txt"
build_message > "$OUTFILE"
echo "No mail transport available — wrote email to $OUTFILE"
exit 0
