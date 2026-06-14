"""
Legacy VAD/Whisper pipeline entry point.

The old `ai.router` path has been removed from the active architecture. The
stable runtime is now `main.py -> Pipeline -> ai.live_session.LiveSession`.
Keep this file as a clear stop sign for older launch commands instead of
silently importing deleted modules.
"""


def main():
    print(
        "Legacy test_pipeline is disabled.\n"
        "Start the current backend with: python backend/main.py"
    )


if __name__ == "__main__":
    main()
