from collections import deque
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torchaudio
from torch import nn


@dataclass
class Config:
    # feature parameters
    fs = 16000
    n_fft = 512
    n_hop = 512
    feature_epsilon = 1e-6

    # raw output smoothing parameters
    max_segment_duration = 15
    max_recursion_depth = 8
    ring_buffer_len = 7
    ring_buffer_threshold_num = 4
    sad_threshold = 0.7
    force_segmentation_margin_frames = 70

    # one-sided segment detection parameters
    segment_terminative_silence = 0.3


class FeatureExtractor(nn.Module):
    def __init__(self):
        super().__init__()
        self.feature_epsilon = Config.feature_epsilon
        self.spectrogram = torchaudio.transforms.Spectrogram(
            n_fft=Config.n_fft,
            hop_length=Config.n_hop,
        )

    def forward(self, x):
        # x of the shape 1xT
        mfb = self.spectrogram(x)
        lmfb = torch.log10(mfb + self.feature_epsilon)
        return lmfb


class SAD:
    def __init__(self):
        # audio buffer
        self.input_audio_buffer = torch.zeros(1, 0)
        self.step = 0
        # SAD model utils
        self.feature_extractor = FeatureExtractor()
        model_path = Path(__file__).parent / "uni_128_freq_res_512.pt"
        self.model = torch.jit.load(model_path)
        self.model.eval()
        self.state = torch.zeros(1, 1, 64)
        # post processing algorithm
        self.ring_buffer = deque(maxlen=Config.ring_buffer_len)
        self.triggered = False
        self.agg_result = []
        self.voiced_frames = []

    def get_audio_buffer_duration(self):
        return self.input_audio_buffer.size(1) / Config.fs

    def check_input_type(self, audio):
        if isinstance(audio, np.ndarray):
            return torch.from_numpy(audio).float().unsqueeze(0)
        return audio

    @torch.inference_mode()
    def __call__(self, audio):
        audio_tensor = self.check_input_type(audio)
        # calculate number valid steps and crop valid part of the buffer
        self.input_audio_buffer = torch.cat(
            (self.input_audio_buffer, audio_tensor),
            dim=1,
        )
        valid_steps = (
            self.input_audio_buffer.size(1) - int(self.step * Config.n_hop)
        ) // Config.n_hop
        start_index = int(self.step * Config.n_hop)
        end_index = start_index + int(valid_steps * Config.n_hop)
        tmp_audio_tensor = self.input_audio_buffer[:, start_index:end_index]
        # run model
        spect = self.feature_extractor(tmp_audio_tensor)
        spect = spect[:, :, :-1]
        # run model
        raw_output, self.state = self.model(spect, self.state)
        sad_probs = raw_output[0, :, 1]
        # post processing
        segments = self.apply_ring_buffer_smoothing(sad_probs)
        return segments

    def get_time(self, steps):
        return steps * Config.n_hop / Config.fs

    def apply_ring_buffer_smoothing(self, sad_probs):
        segments = []
        binarized_sad_probs = sad_probs > Config.sad_threshold
        iterator = zip(sad_probs, binarized_sad_probs)
        for sad_prob, is_speech in iterator:
            frame = {"index": self.step, "is_speech": is_speech, "sad_prob": sad_prob}
            self.step += 1
            self.ring_buffer.append(frame)
            if not self.triggered:
                num_voiced = len(
                    [frame for frame in self.ring_buffer if frame["is_speech"]]
                )
                if num_voiced > Config.ring_buffer_threshold_num:
                    self.voiced_frames = [frame for frame in self.ring_buffer]
                    self.triggered = True
                    self.ring_buffer.clear()
            else:
                self.voiced_frames.append(frame)
                num_unvoiced = len(
                    [frame for frame in self.ring_buffer if not frame["is_speech"]]
                )
                if num_unvoiced > Config.ring_buffer_threshold_num:
                    segments.append(self.postprocess_rb_result())
                    # TODO: force segmentation in case the current segment exceeds a limit
                    self.voiced_frames = []
                    self.triggered = False
                    self.ring_buffer.clear()
        return segments

    def postprocess_rb_result(self):
        start_time = self.get_time(self.voiced_frames[0]["index"])
        end_time = self.get_time(self.voiced_frames[-1]["index"] + 1)
        start_index = int(start_time * Config.fs)
        end_index = int(end_time * Config.fs)
        return {
            "start": start_time,
            "end": end_time,
            "duration": end_time - start_time,
            "audio": self.input_audio_buffer[0, start_index:end_index].numpy(),
        }
