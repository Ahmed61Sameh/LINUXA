import time
import queue
import threading

import numpy as np
import sounddevice as sd
import librosa
import joblib


MODEL_PATH = "linksa_svm_v30.joblib"

SR = 16000

WINDOW_SECONDS = 3.5
WINDOW_SAMPLES = int(SR * WINDOW_SECONDS)

BLOCK_SECONDS = 0.1
BLOCK_SAMPLES = int(SR * BLOCK_SECONDS)


SPEECH_RMS_THRESHOLD = 0.012

END_SILENCE_SECONDS = 0.35

MIN_SPEECH_SECONDS = 0.20

MAX_SPEECH_SECONDS = 2.8



THRESHOLD = 65.0

COOLDOWN_SECONDS = 1.5

N_MELS = 64
N_FFT = 512
HOP_LENGTH = 160



print("Loading Linksa V30 model...")

model = joblib.load(MODEL_PATH)

linksa_index = list(model.classes_).index(1)

print("Linksa V30 model loaded successfully.")



END_SILENCE_BLOCKS = max(
    1,
    int(END_SILENCE_SECONDS / BLOCK_SECONDS)
)

MIN_SPEECH_BLOCKS = max(
    1,
    int(MIN_SPEECH_SECONDS / BLOCK_SECONDS)
)

MAX_SPEECH_BLOCKS = max(
    1,
    int(MAX_SPEECH_SECONDS / BLOCK_SECONDS)
)



def predict_linksa(audio):

    mel = librosa.feature.melspectrogram(
        y=audio,
        sr=SR,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        n_mels=N_MELS,
        power=2.0,
    )

    db = np.clip(
        librosa.power_to_db(mel, ref=np.max),
        -80,
        0,
    )

    features = (
        db.flatten()
        .astype(np.float32)
        .reshape(1, -1)
    )

    probabilities = model.predict_proba(features)[0]

    return float(
        probabilities[linksa_index] * 100
    )




def make_centered_window(speech):

    speech = np.asarray(
        speech,
        dtype=np.float32
    )

    if len(speech) > WINDOW_SAMPLES:

        speech = speech[:WINDOW_SAMPLES]

    window = np.zeros(
        WINDOW_SAMPLES,
        dtype=np.float32
    )

    start = (
        WINDOW_SAMPLES - len(speech)
    ) // 2

    window[
        start:start + len(speech)
    ] = speech

    return window




class WakeWordListener:

    def __init__(
        self,
        on_detected=None,
        on_error=None
    ):

        self.on_detected = on_detected
        self.on_error = on_error

        self.running = False

        self.stop_event = threading.Event()

        self.thread = None

        self.lock = threading.Lock()

        self.audio_queue = queue.Queue(
            maxsize=40
        )

        self.speech_chunks = []

        self.in_speech = False

        self.silence_blocks = 0

        self.last_detection = 0.0


    def reset_state(self):

        self.speech_chunks = []

        self.in_speech = False

        self.silence_blocks = 0

        while not self.audio_queue.empty():

            try:
                self.audio_queue.get_nowait()

            except queue.Empty:
                break



    def audio_callback(
        self,
        indata,
        frames,
        time_info,
        status
    ):

        if status:
            print(f"Audio status: {status}")

        block = indata[:, 0].copy()

        try:

            self.audio_queue.put_nowait(block)

        except queue.Full:

            pass


    def process_block(self, block):

        rms = float(
            np.sqrt(np.mean(block ** 2))
        )

        if rms >= SPEECH_RMS_THRESHOLD:

            if not self.in_speech:

                self.in_speech = True

                self.speech_chunks = []

                self.silence_blocks = 0

            self.speech_chunks.append(block)

            self.silence_blocks = 0

        elif self.in_speech:

            self.speech_chunks.append(block)

            self.silence_blocks += 1

        if not self.in_speech:

            return None

        speech_blocks = (
            len(self.speech_chunks)
            - self.silence_blocks
        )

        if (
            self.silence_blocks < END_SILENCE_BLOCKS
            and speech_blocks < MAX_SPEECH_BLOCKS
        ):

            return None

        speech = np.concatenate(
            self.speech_chunks
        )

        speech = speech[
            :speech_blocks * BLOCK_SAMPLES
        ]

        self.in_speech = False

        self.speech_chunks = []

        self.silence_blocks = 0

        if (
            len(speech)
            < MIN_SPEECH_BLOCKS * BLOCK_SAMPLES
        ):

            return None

        window = make_centered_window(speech)

        score = predict_linksa(window)

        print(
            f"Speech detected — "
            f"Linksa score: {score:.2f}%"
        )

        now = time.monotonic()

        if (
            score >= THRESHOLD
            and now - self.last_detection >= COOLDOWN_SECONDS
        ):

            self.last_detection = now

            print(
                f"\n>>> LINKSA DETECTED "
                f"({score:.2f}%) <<<\n"
            )

            return score

        return None



    def start(self):

        with self.lock:

            if self.running:

                print("Wake Word is already running.")

                return False

            self.reset_state()

            self.stop_event.clear()

            self.running = True

            self.thread = threading.Thread(
                target=self._listen_loop,
                daemon=True
            )

            self.thread.start()

        print("Wake Word listening started.")

        return True



    def stop(self):

        if not self.running:

            return False

        print("Stopping Wake Word listener...")

        self.stop_event.set()

        return True



    def _listen_loop(self):

        detected_score = None

        error = None

        try:

            with sd.InputStream(
                samplerate=SR,
                channels=1,
                dtype="float32",
                blocksize=BLOCK_SAMPLES,
                callback=self.audio_callback,
            ):

                print("Wake Word microphone stream opened.")

                while not self.stop_event.is_set():

                    try:

                        block = self.audio_queue.get(
                            timeout=0.2
                        )

                    except queue.Empty:

                        continue

                    detected_score = self.process_block(
                        block
                    )

                    if detected_score is not None:

                        break

        except Exception as e:

            error = e

            print(
                f"Wake Word error: {e}"
            )

        finally:

            # The microphone stream is closed here.
            # Recording can safely open the microphone afterward.

            with self.lock:

                self.running = False

                self.thread = None

            print("Wake Word microphone stream closed.")

        # Notify the main program after closing the stream.

        if detected_score is not None:

            if self.on_detected is not None:

                try:

                    self.on_detected(
                        detected_score
                    )

                except Exception as e:

                    print(
                        f"Detection callback error: {e}"
                    )

        if error is not None:

            if self.on_error is not None:

                try:

                    self.on_error(error)

                except Exception as e:

                    print(
                        f"Error callback failed: {e}"
                    )



def linksa_detected(score):

    print(
        f"Callback received. Linksa score: {score:.2f}%"
    )


def wake_word_error(error):

    print(
        f"Listener error: {error}"
    )


if __name__ == "__main__":

    listener = WakeWordListener(
        on_detected=linksa_detected,
        on_error=wake_word_error
    )

    listener.start()

    try:

        while listener.running:

            time.sleep(0.1)

        # Keep the test process alive after detection
        # so the callback result remains visible.

        if listener.thread is not None:

            listener.thread.join()

    except KeyboardInterrupt:

        listener.stop()

        if listener.thread is not None:

            listener.thread.join()

        print("Wake Word test stopped.")