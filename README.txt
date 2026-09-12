JARVIS UI v4

Run the normal assistant:
    python main.py

Open the standalone settings editor:
    python ui_settings.py

Open the standalone layout editor:
    python ui_layout.py

Main UI behavior:
- Compact startup is the Arc Reactor only.
- Window background remains 100% transparent in compact mode.
- Reactor graphic defaults to 60% opacity.
- Click the reactor to open Quick Actions.
- Quick Actions contains chat log + command textbox; Enter sends and clears the textbox.
- Settings contains extended reactor controls and opens the full Settings window.
- Layout Editor can select existing UI widgets, change position/size/visibility/opacity/color/text, add Text/Button/Panel/Separator elements, drag custom elements, and save them to config/ui_layout.json.
- Settings persist in config/api_keys.json.

Optional Phase 1 service layer:
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8010

The service layer is additive: the existing `python main.py` desktop launcher
remains the default. It currently provides health, conversation persistence,
and WebSocket transport for future provider and agent modules.

Voice providers:
Open the Settings window and choose `fish_audio` under Speech engine. Enter
your Fish Audio API key, model ID (for example `s1`), reference voice ID,
endpoint, output format, and latency preference. Credentials are stored in
`config/api_keys.json`; keep that file private. Fish Audio uses the
`Authorization: Bearer` request format and requires internet access.

Edge TTS voice:
Choose `edgetts` and enter an Edge voice name in the Voice field. The default
is `en-GB-RyanNeural`, a refined British English voice. Speaking speed and
pitch settings are converted to Edge TTS rate and pitch controls.

Voice architecture:
`core/voice.py` exposes `VoiceProfile`, `VoiceMode`, `TextToSpeech`,
`SpeechToText`, `WakeWordDetector`, `VoiceActivityDetector`, and
`PronunciationManager`. `VoiceDirector` provides queued, interruptible speech
and context delivery modes while `ExistingTTSAdapter` lets current providers
be replaced without changing assistant code.
