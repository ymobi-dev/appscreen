#!/bin/bash
# Validates hero proportions for the biblia365 pipeline.
# Text block (top 480 rows only, phone never enters) is found by row profiling:
# a row counts as text when >= ~3% of its pixels are bright after thresholding.
# Reports txtTop/txtBottom, screenTop/screenBottom, gapToPhone and title<->sub gap.
# Exit code 1 if any hero's text overlaps the phone (gap < 20px).
# Usage: bash validate-heroes.sh [device] [variant] [locale]
set -u
cd "$(dirname "$0")" || exit 1
DEV="${1:-android-phone}"
VARIANT="${2:-navy-glow}"
LOCALE="${3:-pt-BR}"
DIR="output/$DEV/$VARIANT/$LOCALE"

# Canvas geometry per device (keep in sync with hero-config.cjs PLATFORMS).
case "$DEV" in
  iphone-6.9)  W=1320; H=2868 ;;
  *)           W=1080; H=1920 ;;
esac
CX=$((W / 2))
TEXT_MAX=$((H * 25 / 100))   # text lives in the top quarter
PHONE_MIN=$((H * 25 / 100))
PHONE_MAX=$((H - 30))

FAIL=0
printf "%-8s %-19s %-19s %-9s\n" hero "txtTop/txtBottom" "screenTop/Bottom" "gapToPhone"
for f in "$DIR"/hero-*.png; do
  n=$(basename "$f" .png)
  # --- text block via row profile -----------------------------------------
  # Green-channel mask: text (white/warm) has G > 55%; the aurora variant's
  # orange background has G ~47% so it never counts as text.
  txtTop=0; txtBottom=0
  for y in $(seq 0 8 $TEXT_MAX); do
    m=$(magick "$f" -crop ${W}x8+0+$y +repage -channel G -separate +channel \
      -threshold 55% -format "%[fx:int(mean*255)]" info: 2>/dev/null)
    if [ -n "$m" ] && [ "$m" -ge 8 ] 2>/dev/null; then
      if [ "$txtTop" -eq 0 ]; then txtTop=$((y + 4)); fi
      txtBottom=$((y + 4))
    fi
  done
  # --- phone screen via center-column scan --------------------------------
  screenTop=0
  for y in $(seq $PHONE_MIN 8 $PHONE_MAX); do
    px=$(magick "$f" -crop 1x1+$CX+$y +repage -format "%[fx:int(mean*255)]" info: 2>/dev/null)
    if [ -n "$px" ] && [ "$px" -gt 120 ] 2>/dev/null; then screenTop=$y; break; fi
  done
  screenBottom=0
  for y in $(seq $PHONE_MAX -8 $PHONE_MIN); do
    px=$(magick "$f" -crop 1x1+$CX+$y +repage -format "%[fx:int(mean*255)]" info: 2>/dev/null)
    if [ -n "$px" ] && [ "$px" -gt 120 ] 2>/dev/null; then screenBottom=$y; break; fi
  done
  gapToPhone=$((screenTop - txtBottom))
  if [ "$gapToPhone" -lt 20 ] 2>/dev/null; then FAIL=1; fi
  printf "%-8s %-19s %-19s %-9s\n" "$n" "$txtTop/$txtBottom" "$screenTop/$screenBottom" "$gapToPhone"
done
echo "---"
if [ "$FAIL" -eq 1 ]; then echo "FAIL: texto invade o mockup em algum hero"; exit 1; fi
echo "OK: sem sobreposição"
