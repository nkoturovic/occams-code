---
description: Show YOLO mode status and how to use it safely
---
Explain YOLO mode for this setup:

- `oc --yolo` enables temporary permission allow-all for one session only.
- Permissions are automatically restored when the session exits.
- For normal mode, launch without `--yolo`.

Also show this command snippet:

```bash
oc --yolo            # temporary auto-approve (restored on exit)
oc                   # normal permission mode
```

$ARGUMENTS
