# Click Behavior Redesign

**Date:** 2026-06-02
**Status:** Approved, implemented

## Summary

Change the video tracking canvas cursor and click feedback: crosshair → hollow red dot cursor, red filled dot → hollow green dot on click, fix "dot carries to next frame" bug, and add hold-drag tracking.

## Changes

### Cursor
- **Before:** `Qt.CrossCursor`
- **After:** Custom 20px hollow red circle (`#ff453a` outline, 2px pen, no fill, center hotspot)

### Click feedback
- **Before:** Red filled circle (`MarkDotItem`, `#ff453a`, radius 5, black outline) shown after frame advance
- **After:** Hollow green circle (`#30d158` outline, 2px pen, no fill) shown on press

### Click flow

| Event | Before | After |
|---|---|---|
| Press | Nothing in tracking mode | Show hollow green dot at cursor position |
| Drag | Nothing in tracking mode | Green dot follows cursor |
| Release | Record mark, advance frame, show red dot on *next* frame | Record mark, advance frame (dot cleared by frame navigation) |

### Frame cleanliness
- Root cause: `show_click_feedback` called after `_advance_frame`, so dot appeared on the advanced frame
- Fix: visual feedback on `mousePressEvent` (before advance), naturally cleared by `_go_to_frame → clear_click_feedback`

### Persistent marks
- No change. Navigating back shows hollow red squares (`MarkSquareItem`) via `set_marks`.

### Autoclicker
- No change. Autoclicker calls `_record_click_at` directly, bypasses `mousePressEvent`, so no green dot flash at high CPS.
