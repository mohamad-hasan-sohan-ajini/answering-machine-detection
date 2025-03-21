# Description: Audio matching class to match key audio segment in query audio segment.

import numpy as np
import torch
import torchaudio

from utils import get_logger, retrieve_wav


class AudioMatching:
    def __init__(
        self,
        sample_rate: int = 16000,
        n_mels: int = 80,
        n_fft: int = 512,
        hop_length: int = 256,
        key_duration: float = 0.5,
        std_threshold: float = 3.0,
    ):
        self.sample_rate = sample_rate
        self.n_mels = n_mels
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.key_duration = key_duration
        self.std_threshold = std_threshold
        self.logger = get_logger()
        self.transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
        )

    def compute_cross_correlation(
        self,
        key_segment: torch.Tensor,
        query_segment: torch.Tensor,
    ) -> bool:
        """Compute cross correlation between key and query segments.

        Args:
            key_segment (torch.Tensor): key segment of shape (1, Tk)
            query_segment (torch.Tensor): query segment of shape (1, Tq)

        Returns:
            bool: True if key segment is found in query segment.
        """
        # check query segment length
        if query_segment.shape[1] < int(self.key_duration * self.sample_rate):
            self.logger.warning("query segment is too short")
            return False
        # select center piece of key segment
        if key_segment.shape[1] > int(self.key_duration * self.sample_rate):
            self.logger.info("select center piece of key segment")
            center = key_segment.shape[1] // 2
            start = center - int(self.key_duration * self.sample_rate) // 2
            end = center + int(self.key_duration * self.sample_rate) // 2
            key_segment = key_segment[:, start:end]
        else:
            self.logger.warning("key segment is too short")
            return False
        # compute mel spectrogram
        mel_key = torch.log10(self.transform(key_segment) + 1).unsqueeze(0)
        mel_query = torch.log10(self.transform(query_segment) + 1).unsqueeze(0)
        # Perform the convolution/cross correlation
        cross_correlation = (
            torch.nn.functional.conv2d(
                mel_query,
                mel_key,
            )
            .squeeze()
            .numpy()
        )
        return cross_correlation

    def decide_similarity(self, cross_correlation: torch.Tensor) -> bool:
        """Decide if key segment is found in query segment."""
        # check if there is a match
        mean, std = cross_correlation.mean(), cross_correlation.std()
        self.logger.info(f"{mean = }\t{std = }, {cross_correlation.max() = }")
        is_peak = cross_correlation > (mean + self.std_threshold * std)
        if sum(is_peak).item():
            self.logger.info("key segment found in query segment")
            return True
        self.logger.info("key segment not found in query segment")
        return False

    def match_segments(self, key_np_array: np.ndarray, query_wav_obj: str) -> bool:
        """Match key segment in query segment.

        Args:
            key_np_array (np.ndarray): key wav file numpy array ()
            query_wav_obj (str): path to query wav file located in object storage

        Returns:
            bool: True if key segment is found in query segment.
        """
        # convert key_np_array to torch tencor
        key_segment = torch.from_numpy(key_np_array).unsqueeze(0)
        # retrieve segments
        query_segment = retrieve_wav(query_wav_obj)
        if query_segment.shape[0] == 0:
            self.logger.warning("query segment is empty")
            return False
        # compute cross correlation
        cross_correlation = self.compute_cross_correlation(key_segment, query_segment)
        return self.decide_similarity(cross_correlation)


if __name__ == "__main__":
    audio2_path = (
        "../audio-pattern-matching/files/669a071b-520f-4dc1-8a43-1c7500a1e658-.wav"
    )
    audio1_path = (
        "../audio-pattern-matching/files/43807aaf-17d7-4f14-9de6-fd82f80f0f39-.wav"
    )

    audio1, fs = torchaudio.load(audio1_path)
    audio2, fs = torchaudio.load(audio2_path)

    from sad.sad_model import SAD

    sad = SAD()
    sad_result1 = sad.handle([open(audio1_path, "rb").read()])[0]

    audio_matching = AudioMatching()
    segment1 = audio1[
        :,
        int(sad_result1[0]["start"] * audio_matching.sample_rate) : int(
            sad_result1[-1]["end"] * audio_matching.sample_rate
        ),
    ]
    print(
        segment1.shape,
        audio2.shape,
    )
    cross_correlation = audio_matching.compute_cross_correlation(segment1, audio2)
    matching_result = audio_matching.decide_similarity(cross_correlation)
    print(f"{matching_result = }")
