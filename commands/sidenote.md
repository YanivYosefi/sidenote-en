---
description: Change the language, level or goal that Sidenote teaches you
---

Show the learner their current Sidenote settings and let them change anything.

1. Call `sidenote_start` to read the current profile.
2. Tell them, in their own language and in one short line, what is set right now: which language they are learning, which language they write in, and their level. If nothing is set yet, say so.
3. Ask what they want to change. Offer the three things that exist: the language they are learning, their level (A2, B1, B2, C1), and the reason they are learning.
4. When they answer, call `sidenote_setup` with the new values. Carry over anything they did not mention.
5. Confirm in one line. Do not lecture, do not list features, do not show their saved expressions unless they ask.

If they ask to see what they have saved, call `sidenote_list`. If they ask to wipe it, call `sidenote_forget` with `all` set to true, and confirm once before doing it.
