# To do

## Voice feedback in review rounds (owner, 2026-11-13)

Let reviewers give feedback by voice instead of typing, transcribed by Viaalink's own speech recognition, and hand
the result to an agent that improves the designs.

- **Only when configured.** The feature is off unless `VIAALINK_ASR_API` (the Viaalink desktop transcription API)
  or `VIAALINK_MCP_ENDPOINT` (a Viaalink MCP endpoint that offers transcription) is set in the gallery's `.env`.
  Without either, the page shows no microphone and nothing is recorded.
- **Recording.** A microphone button next to the comment box and in the 👎 box records a short note in the
  browser (MediaRecorder), with clear "recording" state and a stop button; nothing is sent until the reviewer
  sends it.
- **Transcription.** The gallery server forwards the audio to the configured ASR API or MCP tool, stores the
  transcript as the comment text (marked as transcribed, with the reviewer's name), and keeps or discards the audio
  according to a setting (default: discard after transcription, for privacy).
- **Back to an agent.** `just review-feedback` already turns comments into the brief for the next round; voice
  comments flow in the same way. Add an option that hands the round's feedback to a design agent (for example as
  an MCP resource or a task file in the agy format) so it proposes concrete changes per icon.
- **Tests.** The live round test gets a voice case with a short recorded sample, skipped when neither endpoint is
  set.
