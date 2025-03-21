import numpy as np
import torch
import torchaudio

from utils import get_logger


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
        self.mel_spectrogram = torchaudio.transforms.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
        )

    def compute_cross_correlation(
        self,
        key_segment: np.ndarray,
        query_segment: np.ndarray,
    ) -> bool:
        """Compute cross correlation between key and query segments.

        Args:
            key_segment (np.ndarray): key segment of shape (1, Tk)
            query_segment (np.ndarray): query segment of shape (1, Tq)

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
        mel_key = torch.log10(self.mel_spectrogram(key_segment) + 1).unsqueeze(0)
        mel_query = torch.log10(self.mel_spectrogram(query_segment) + 1).unsqueeze(0)
        # Perform the convolution/cross correlation
        cross_correlation = torch.nn.functional.conv2d(
            mel_query,
            mel_key,
        ).squeeze()
        # check if there is a match
        mean, std = cross_correlation.mean(), cross_correlation.std()
        self.logger.info(f"{mean = }\t{std = }, {cross_correlation.max() = }")
        is_peak = cross_correlation > (mean + self.std_threshold * std)
        if sum(is_peak).item():
            self.logger.info("key segment found in query segment")
            return True
        self.logger.info("key segment not found in query segment")
        return False
