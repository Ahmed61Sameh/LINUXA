# Module 2: Speech-to-Text

Part of the Sound Operating System project (controlling the OS by voice).
This module takes the path of a WAV file that contains a spoken command and
returns the transcribed text, a confidence score, and an error code if
something goes wrong. It uses faster-whisper (Whisper "small") and runs
locally on the CPU.

## Where it fits

Recording module -> WAV file -> **this module** -> text -> command
understanding (Module 3) -> security checks (Module 5) -> execution
(Module 6). Module 8 connects them.

Input contract with the Recording module: one sentence per WAV file,
16 kHz, mono, 16-bit. The wake word only opens the interface and is not
recorded in the file. Recording starts right after and stops after about
2.5 seconds of silence.

## Install

    pip install -r requirements.txt

The first run downloads the model (about 460 MB).

## Usage

    from stt import speech_to_text
    result = speech_to_text("recordings/cmd1.wav")
    if result["ok"]:
        print(result["text"])

## Using it from another module

stt.py imports stt_config.py, so both files must be importable. From a script
outside this folder, add the folder to the path first:

    import sys
    sys.path.append("module2_stt")
    from stt import speech_to_text

The model is loaded on the first call and kept in memory, so the first command
is slower. Call `stt.get_model()` once at startup to avoid that delay.

## Output

A dictionary with the same fields in every case:

| Field | Meaning |
|---|---|
| ok | True only if the text can be trusted (no error) |
| text | The transcription (also returned with LOW_CONFIDENCE) |
| language | Detected language code |
| language_probability | How sure Whisper is about the language |
| confidence | Approximate score from 0 to 1 (not a real accuracy) |
| duration | Length of the audio in seconds |
| processing_time | Seconds spent on the file |
| error | None, or one of the codes below |
| detail | Human-readable reason for the error |

## Error codes

The function never raises exceptions. Problems come back as codes.

| Code | When | What the caller should do |
|---|---|---|
| FILE_NOT_FOUND | The path does not exist | Check the path |
| NO_SPEECH | Nothing was recognized (silence, or only a known hallucination) | Ask the user to speak again |
| LOW_CONFIDENCE | Text found, but confidence is below the threshold | Text is still returned: ask the user to confirm or repeat |
| INTERNAL_ERROR | Any unexpected failure (bad setting, corrupt file, model problem) | Read `detail` |

## How the confidence score works

For every segment Whisper gives two numbers: how sure it is about the words
(`avg_logprob`) and the chance that the segment is not speech at all
(`no_speech_prob`). They are combined into one number between 0 and 1 and
averaged over the segments. It is an estimate, not a measured accuracy.
A wrong transcript can still get a fairly high score (0.64 on a wrong
sentence in our tests), so confidence alone must not be the only safety check.

## Settings (stt_config.py)

| Setting | Value | Why |
|---|---|---|
| MODEL_SIZE | "small" | More accurate than "base" on our sentences |
| LANGUAGE_MODE | "best_of_two" | Runs Arabic and English, keeps the more confident result |
| CONFIDENCE_THRESHOLD | 0.6 | Chosen from the benchmark table on the Recording module files (see Results) |
| VAD_FILTER | True | Removes silence before decoding; clearly better on the Recording module files |
| INITIAL_PROMPT | App names (Chrome, Spotify, ...) | Helps Whisper spell English app names |
| WAKE_WORDS | [] | The wake word is not in the recorded file |
| MODEL_DIR | None | Default download location. Set a folder path to store the model elsewhere (for example when the C: drive is full) |

## Decisions and why

- **Model size:** "small" beat "base" in every setting we compared.
- **Language mode:** automatic detection guessed wrong languages on short
  clips (Portuguese, German, Danish, Hebrew). Forcing Arabic fixed that but
  hurt English. best_of_two keeps both.
- **VAD filter on:** on short phone clips it made no difference, but on the
  Recording module files (about 2.5 seconds of silence after the speech) it
  lowered the wrong-word rate from 57% to 38%, raised the confidence, and
  cut the processing time roughly in half.
- **Threshold 0.6:** 0.7 was chosen on phone recordings but was too strict on
  the Recording module files. At 0.6, sentences with real errors are rejected
  and the ones that pass keep the intended command. We prefer asking the user
  to repeat over running a wrong command.
- **Short prompt:** a long prompt made Whisper invent text on silence.
- **Audio format:** early recordings were WhatsApp voice messages (heavily
  compressed) and gave poor results, which may be partly due to the
  compression (not proven). We now use uncompressed WAV.

## Results

Early test on phone recordings (20 sentences, 5 per group):

| Setting | Wrong words |
|---|---|
| base + automatic language | 94% |
| small + automatic language | 88% |
| small + Arabic only | 72% |
| small + best_of_two | 64% |

Recording module files (20 sentences, 4 to 6 seconds each, laptop microphone,
possibly a different speaker), small + best_of_two:

| VAD filter | Wrong words | Time per sentence |
|---|---|---|
| Off | 57% | 11 to 14 seconds |
| On (used) | 38% | 5 to 9 seconds |

With VAD on: English 0%, Modern Standard Arabic 30%, mixed 40%, Egyptian
Arabic 80%.

Threshold with VAD on: at 0.6, 11 of 20 sentences pass. 8 match the reference
exactly. 3 differ in wording but, in our reading, keep the same command
("يفتح المتصفح", "افتح المتصفح" for "افتحلي المتصفح", and "Open Chrome" for
"افتح كروم"). The 3 sentences with real errors have confidence 0.50 to 0.55
and are rejected. 2 correct sentences are rejected. At 0.7, 6 correct sentences
are rejected, and at 0.8 everything is rejected.

Silence and noise files: [fill in: NO_SPEECH or LOW_CONFIDENCE].

## Limits

- 20 short sentences, one speaker. The threshold was chosen on the same
  sentences, so the numbers are optimistic.
- Egyptian Arabic is the weakest group.
- Confidence does not catch every wrong transcript: Module 3 should tolerate
  small spelling errors and Module 5 should verify commands.
- The function does not check the WAV format by itself. Use `check_wav.py`.

## Files

| File | Purpose |
|---|---|
| stt.py | The main function and helpers |
| stt_config.py | All settings |
| test_stt.py | Logic tests with a fake model (no download needed) |
| benchmark.py | Accuracy measurement on test_cases.csv |
| test_cases.csv | The 20 test sentences with their group |
| check_wav.py | Checks a WAV file (rate, channels, level) |
| check_csv.py | Checks that all files in test_cases.csv exist |
| results/ | Saved benchmark outputs |
| experiments/ | Early experiments |

## Testing

    python test_stt.py                     logic tests
    python benchmark.py small best_of_two  accuracy (arguments: size, language mode)
    python check_wav.py file.wav           check a recording

The audio files listed in test_cases.csv are not included in this repository,
so benchmark.py and check_csv.py need those files placed in an "audio" folder.
test_stt.py runs without any audio.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| ModuleNotFoundError: faster_whisper | Running with the system Python (for example the editor's Run button) | Activate the venv and run from the terminal |
| ModuleNotFoundError: stt_config | The folder is not on the Python path | See "Using it from another module" |
| Arabic shows as ???? in the terminal | Terminal encoding only | Open the output file in an editor (it is UTF-8) |
| WinError 112, not enough space | The C: drive is full; model cache and temp files go there by default | Set HF_HOME, TMP and TEMP to a folder on another drive, and set MODEL_DIR |
| TypeError ... 'metadata_errors' | Incompatible version of the av library | pip install --no-cache-dir "av<17" |
| FILE_NOT_FOUND on a file that exists | Hidden extension, for example t1.mp4.mp4 | Check the real name with `dir` |
| INTERNAL_ERROR: bad LANGUAGE_MODE | Typo in the setting (for example bast_of_two) | Use auto, ar, en or best_of_two |
| INTERNAL_ERROR: TypeError generate() incompatible arguments | INITIAL_PROMPT is not a plain string (written inside { } or with a trailing comma) | Make it a string in quotes |
| LOW_CONFIDENCE on a correct sentence | Confidence is below the threshold by design | Ask the user to repeat, or tune the threshold in stt_config.py |
| Invented text on silence | Whisper hallucination, usually with low confidence | The threshold catches most; add the phrase to HALLUCINATIONS; keep the prompt short |
| Warning: Ignoring invalid distribution ~v | Leftover folder from an interrupted install | Delete the folders starting with ~v in env\Lib\site-packages |