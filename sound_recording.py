#####
import sounddevice as sd
import soundfile as sf
import numpy as np

import scipy
import librosa
import webrtcvad
import noisereduce as nr

import time
import threading

from pathlib import Path
from datetime import datetime


# ==========================================
# Audio Configuration
# ==========================================

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"

BLOCK_DURATION = 0.1
BLOCK_SIZE = int(SAMPLE_RATE * BLOCK_DURATION)

AUDIO_SUBTYPE = "PCM_16"

MIN_RECORDING_DURATION = 0.5
MAX_RECORDING_DURATION = 30

SILENCE_DURATION = 1

VAD_FRAME_DURATION_MS = 30
VAD_FRAME_SAMPLES = int(
    SAMPLE_RATE * VAD_FRAME_DURATION_MS / 1000
)

VAD_AGGRESSIVENESS = 2

ENABLE_NOISE_REDUCTION = True

OUTPUT_FOLDER = Path("recorded_commands")
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


# ==========================================
# Voice Recorder Class
# ==========================================

class VoiceRecorder:

    def __init__(self):

        self.recording = False
        self.audio_data = []

        self.start_time = None
        self.speech_start_time = None

        self.stream = None

        self.lock = threading.Lock()

        self.stop_event = threading.Event()
        self.stop_thread = None

        self.finalizing = False

        self.audio = None
        self.processed_audio = None

        self.audio_path = None
        self.original_audio_path = None

        self.total_frames = 0

        self.output_folder = OUTPUT_FOLDER

        # GUI callback
        self.on_finished = None

        # Recording state
        self.speech_detected = False
        self.silence_duration = 0.0

        # VAD buffer
        self.vad_buffer = np.array([], dtype=np.float32)

        self.vad = webrtcvad.Vad(
            VAD_AGGRESSIVENESS
        )

        self.recording_id = None
        self.last_success = False

        print("Voice Recorder initialized successfully.")

    # ======================================
    # Start Recording
    # ======================================

    def start_recording(self):

        with self.lock:

            if (
                self.recording
                or self.stream is not None
                or self.finalizing
            ):

                print("Recording is already running.")
                return False

            # Reset previous recording data
            self.audio_data = []

            self.audio = None
            self.processed_audio = None

            self.audio_path = None
            self.original_audio_path = None

            self.total_frames = 0

            self.start_time = time.monotonic()
            self.speech_start_time = None

            self.speech_detected = False
            self.silence_duration = 0.0

            self.vad_buffer = np.array(
                [],
                dtype=np.float32
            )

            self.recording_id = datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )

            self.last_success = False

            self.stop_event.clear()

            try:

                self.stream = sd.InputStream(
                    samplerate=SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype=DTYPE,
                    blocksize=BLOCK_SIZE,
                    callback=self._audio_callback
                )

                self.recording = True

                self.stream.start()

                # Start the automatic stop watcher
                self.stop_thread = threading.Thread(
                    target=self._watch_stop,
                    daemon=True
                )

                self.stop_thread.start()

                print("Microphone monitoring started.")
                print("Waiting for speech...")

                return True

            except Exception as e:

                print("Recording start error:", e)

                self.recording = False

                if self.stream is not None:

                    try:
                        self.stream.close()
                    except Exception:
                        pass

                self.stream = None

                return False

    # ======================================
    # Audio Callback
    # ======================================

    def _audio_callback(
        self,
        indata,
        frames,
        time_info,
        status
    ):

        if status:
            print("Audio callback status:", status)

        if not self.recording:
            raise sd.CallbackStop

        # Add incoming samples to VAD buffer
        incoming_audio = indata[:, 0].copy()

        self.vad_buffer = np.concatenate(
            (
                self.vad_buffer,
                incoming_audio
            )
        )

        # Process complete 30 ms frames
        while len(self.vad_buffer) >= VAD_FRAME_SAMPLES:

            frame = self.vad_buffer[
                :VAD_FRAME_SAMPLES
            ]

            self.vad_buffer = self.vad_buffer[
                VAD_FRAME_SAMPLES:
            ]

            # Convert float audio to PCM 16-bit
            pcm_frame = np.clip(
                frame,
                -1.0,
                1.0
            )

            pcm_frame = (
                pcm_frame * 32767
            ).astype(np.int16)

            frame_bytes = pcm_frame.tobytes()

            # Detect speech
            try:

                is_speech = self.vad.is_speech(
                    frame_bytes,
                    SAMPLE_RATE
                )

            except Exception as e:

                print("VAD error:", e)
                continue

            # ==================================
            # Speech Detected
            # ==================================

            if is_speech:

                if not self.speech_detected:

                    self.speech_detected = True

                    self.speech_start_time = (
                        time.monotonic()
                    )

                    print("Speech detected.")
                    print("Recording started.")

                self.silence_duration = 0.0

            # ==================================
            # Silence Detected
            # ==================================

            elif self.speech_detected:

                self.silence_duration += (
                    VAD_FRAME_DURATION_MS / 1000
                )

            # ==================================
            # Save Audio Only After Speech
            # ==================================

            if self.speech_detected:

                self.audio_data.append(
                    frame.copy()
                )

                self.total_frames += len(frame)

                # Calculate recording duration
                current_duration = (
                    time.monotonic()
                    - self.speech_start_time
                )

                # ==================================
                # Maximum Recording Duration
                # ==================================

                if current_duration >= MAX_RECORDING_DURATION:

                    print(
                        "Maximum recording duration reached."
                    )

                    self.recording = False
                    self.stop_event.set()

                    raise sd.CallbackStop

                # ==================================
                # Automatic Stop After Silence
                # ==================================

                if (
                    self.silence_duration
                    >= SILENCE_DURATION
                ):

                    print(
                        "Silence detected for 2.5 seconds."
                    )

                    print(
                        "Recording stopped automatically."
                    )

                    self.recording = False
                    self.stop_event.set()

                    raise sd.CallbackStop

        if not self.recording:
            raise sd.CallbackStop

    # ======================================
    # Automatic Stop Watcher
    # ======================================

    def _watch_stop(self):

        self.stop_event.wait()

        self.finalize_recording()

    # ======================================
    # Combine Audio Blocks
    # ======================================

    def combine_audio(self):

        if not self.audio_data:

            print("No speech was recorded.")

            return False

        self.audio = np.concatenate(
            self.audio_data
        ).reshape(-1)

        duration = (
            len(self.audio) / SAMPLE_RATE
        )

        print(
            f"Recorded duration: {duration:.2f} seconds"
        )

        if duration < MIN_RECORDING_DURATION:

            print("Recording is too short.")

            return False

        print(
            "Audio blocks combined successfully."
        )

        return True

    # ======================================
    # Save Original Audio
    # ======================================

    def save_original_audio(self):

        if self.audio is None:
            return False

        filename = (
            f"original_{self.recording_id}.wav"
        )

        self.original_audio_path = (
            self.output_folder / filename
        )

        try:

            sf.write(
                str(self.original_audio_path),
                self.audio,
                SAMPLE_RATE,
                subtype=AUDIO_SUBTYPE
            )

            print(
                "Original audio saved successfully:",
                self.original_audio_path
            )

            return True

        except Exception as e:

            print("Original audio save error:", e)

            return False

    # ======================================
    # Noise Reduction
    # ======================================

    def reduce_noise(self):

        if self.audio is None:
            return False

        if not ENABLE_NOISE_REDUCTION:

            self.processed_audio = self.audio.copy()

            print("Noise reduction is disabled.")

            return True

        try:

            self.processed_audio = nr.reduce_noise(
                y=self.audio,
                sr=SAMPLE_RATE
            )

            print("Noise reduction completed successfully.")

            return True

        except Exception as e:

            print("Noise reduction error:", e)

            return False

    # ======================================
    # Save Processed Audio
    # ======================================

    def save_audio(self):

        if self.processed_audio is None:
            return False

        filename = (
            f"command_{self.recording_id}.wav"
        )

        self.audio_path = (
            self.output_folder / filename
        )

        try:

            sf.write(
                str(self.audio_path),
                self.processed_audio,
                SAMPLE_RATE,
                subtype=AUDIO_SUBTYPE
            )

            print(
                "Processed audio saved successfully:",
                self.audio_path
            )

            return True

        except Exception as e:

            print("Processed audio save error:", e)

            return False

    # ======================================
    # Notify GUI
    # ======================================

    def notify_finished(
        self,
        success,
        error_message=None
    ):

        if self.on_finished is None:
            return

        try:

            self.on_finished({

                "success": success,

                "audio_path": (
                    str(self.audio_path)
                    if success and self.audio_path
                    else None
                ),

                "original_audio_path": (
                    str(self.original_audio_path)
                    if self.original_audio_path
                    else None
                ),

                "error": error_message

            })

            print("[VoiceRecorder] GUI notification sent.")

        except Exception as e:

            print(
                "[VoiceRecorder] GUI callback error:",
                e
            )

    # ======================================
    # Finalize Recording
    # ======================================

    def finalize_recording(self):

        with self.lock:

            if self.finalizing:
                return

            self.finalizing = True
            self.recording = False

            stream = self.stream

        success = False
        error_message = None

        try:

            # Stop and close microphone stream
            if stream is not None:

                try:
                    stream.stop()
                except Exception:
                    pass

                try:
                    stream.close()
                except Exception:
                    pass

            print("Recording stream closed.")

            # Combine recorded audio
            if not self.combine_audio():

                raise RuntimeError(
                    "No valid speech recording was produced."
                )

            # Save original audio
            if not self.save_original_audio():

                raise RuntimeError(
                    "Could not save original audio."
                )

            # Apply noise reduction
            if not self.reduce_noise():

                raise RuntimeError(
                    "Noise reduction failed."
                )

            # Save processed audio
            if not self.save_audio():

                raise RuntimeError(
                    "Could not save processed audio."
                )

            print(
                "Audio finalization completed successfully."
            )

            success = True

        except Exception as e:

            error_message = str(e)

            print(
                "Finalization error:",
                e
            )

        finally:

            with self.lock:

                self.recording = False
                self.stream = None
                self.finalizing = False

            self.last_success = success

            print("Recording stream finalized.")

            # Notify GUI after finalization
            self.notify_finished(
                success,
                error_message
            )

    # ======================================
    # Manual Stop
    # ======================================

    def stop_recording(self):

        with self.lock:

            if self.finalizing:
                return True

            if self.stream is None:
                return False

            if not self.recording and not self.stop_event.is_set():
                return False

            print("Manual stop requested.")

            self.recording = False
            self.stop_event.set()

            return True

    # ======================================
    # Record Command
    # ======================================

    def record_command(self):

        started = self.start_recording()

        if not started:
            return None

        try:

            self.stop_event.wait()

            if self.stop_thread is not None:
                self.stop_thread.join()

        except KeyboardInterrupt:

            print("Recording interrupted by user.")

            self.stop_recording()

            if self.stop_thread is not None:
                self.stop_thread.join()

        if self.last_success:

            return self.audio_path

        return None


# ==========================================
# Create Recorder Instance
# ==========================================

recorder = VoiceRecorder()


# ==========================================
# Standalone Recording Test
# ==========================================

if __name__ == "__main__":

    print("\nStarting voice recording test...")

    started = recorder.start_recording()

    if started:

        print("\nSpeak whenever you are ready.")
        print("The microphone is waiting for speech.")
        print("Recording will stop after 2.5 seconds of silence.")
        print("Maximum speech recording duration: 30 seconds.")

        try:

            recorder.stop_event.wait()

            if recorder.stop_thread is not None:
                recorder.stop_thread.join()

        except KeyboardInterrupt:

            print("\nManual stop requested.")

            recorder.stop_recording()

            if recorder.stop_thread is not None:
                recorder.stop_thread.join()

        print("\nRecording test finished.")

        print(
            "Recording result:",
            recorder.last_success
        )

        print(
            "Original audio:",
            recorder.original_audio_path
        )

        print(
            "Processed audio:",
            recorder.audio_path
        )

    else:

        print("Could not start recording.")