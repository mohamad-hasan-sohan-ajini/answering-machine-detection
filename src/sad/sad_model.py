import io
from collections import deque
from pathlib import Path

import torch
import torchaudio

torch.set_num_threads(1)

N_FFT = 320
FS = 16000
FEATURE_EPSILON = 1e-6
RING_BUFFER_LEN = 11
MAX_SEGMENT_DURATION = 15
RING_BUFFER_THRESHOLD_NUM = 7
SAD_THRESHOLD = 0.7
MAX_RECURSION_DEPTH = 20
FORCE_SEGMENTATION_MARGIN_FRAMES = 100
MODEL_NAME = str(Path(__file__).parent / 'spect32old_00600.pt')


class SAD:
    def __init__(self):
        self.device = torch.device('cpu')
        self.model = torch.jit.load(MODEL_NAME, map_location=self.device)
        self.model.eval()
        self.spectrogram = torchaudio.transforms.Spectrogram(n_fft=N_FFT, hop_length=N_FFT)

    def extract_feature(self, x):
        # x of the shape 1xT
        spect = self.spectrogram(x)
        log_spect = torch.log10(spect + FEATURE_EPSILON)
        return log_spect

    def postprocess_rb_result(self, voiced_frames, sad_probs):
        hop_time = N_FFT / FS
        start_index = voiced_frames[0]['index']
        start_time = start_index * hop_time
        end_index = voiced_frames[-1]['index'] + 1
        end_time = end_index * hop_time
        return {
            'start': start_time,
            'end': end_time,
            'duration': end_time - start_time,
            'sad_probs': sad_probs[start_index:end_index],
            'recursion_depth': 2,
        }

    def apply_ring_buffer_segmentation(self, segment):
        sad_probs = segment['sad_probs']
        ring_buffer = deque(maxlen=RING_BUFFER_LEN)
        triggered = False
        result = []
        voiced_frames = []
        binarized_sad_probs = sad_probs > SAD_THRESHOLD
        for index, (sad_prob, is_speech) in enumerate(zip(sad_probs, binarized_sad_probs)):
            frame = {'index': index, 'is_speech': is_speech, 'sad_prob': sad_prob}
            ring_buffer.append(frame)
            if not triggered:
                num_voiced = len([frame for frame in ring_buffer if frame['is_speech']])
                if num_voiced > RING_BUFFER_THRESHOLD_NUM:
                    triggered = True
                    voiced_frames = [frame for frame in ring_buffer]
                    ring_buffer.clear()
            else:
                voiced_frames.append(frame)
                num_unvoiced = len([frame for frame in ring_buffer if not frame['is_speech']])
                if num_unvoiced > RING_BUFFER_THRESHOLD_NUM:
                    triggered = False
                    result.append(self.postprocess_rb_result(voiced_frames, sad_probs))
                    ring_buffer.clear()
                    voiced_frames = []
        if voiced_frames:
            result.append(self.postprocess_rb_result(voiced_frames, sad_probs))
        return result

    def apply_force_segmentation(self, segment):
        hop_time = N_FFT / FS
        sad_probs = segment['sad_probs'].clone()
        sad_probs[-FORCE_SEGMENTATION_MARGIN_FRAMES:] = 1.
        sad_probs[:FORCE_SEGMENTATION_MARGIN_FRAMES] = 1.
        min_index = sad_probs.argmin().item()
        duration = (min_index + 1) * hop_time
        return [
            {
                'start': segment['start'],
                'end': segment['start'] + duration,
                'duration': duration,
                'sad_probs': segment['sad_probs'][:min_index],
                'recursion_depth': segment['recursion_depth'] + 1,
            },
            {
                'start': segment['start'] + duration,
                'end': segment['end'],
                'duration': segment['duration'] - duration,
                'sad_probs': segment['sad_probs'][min_index:],
                'recursion_depth': segment['recursion_depth'] + 1,
            },
        ]

    def preprocess(self, batch):
        return [self.extract_feature(torchaudio.load(io.BytesIO(i))[0]) for i in batch]

    @torch.inference_mode
    def infer_model(self, batch):
        return [self.model(spect)[0, :, 1] for spect in batch]

    def chunk_segments(self, batch):
        results = []
        for pred in batch:
            segment = {
                'start': 0.0,
                'end': pred.size(0) * N_FFT / FS,
                'duration': pred.size(0) * N_FFT / FS,
                'sad_probs': pred,
                'recursion_depth': 1,
            }
            segments = self.apply_ring_buffer_segmentation(segment)
            while any([segment['duration'] > MAX_SEGMENT_DURATION for segment in segments]):
                tmp_segments = []
                for segment in segments:
                    if segment['duration'] <= MAX_SEGMENT_DURATION:
                        tmp_segments.append(segment)
                    else:
                        tmp_segments.extend(self.apply_force_segmentation(segment))
                segments = tmp_segments
                if any([segment['recursion_depth'] > MAX_RECURSION_DEPTH for segment in segments]):
                    break
            for segment in segments:
                segment.pop('sad_probs')
                segment['duration'] = round(segment['duration'], 2)
            results.append(segments)
        return results

    def postprocess(self, batch):
        return batch

    def handle(self, batch):
        batch = self.preprocess(batch)
        batch = self.infer_model(batch)
        batch = self.chunk_segments(batch)
        batch = self.postprocess(batch)
        return batch
