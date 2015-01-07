#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Effects and filters for audio buffer data"""

import numpy as np

import librosa.core
import librosa.decompose
import librosa.util
from . import cache


@cache
def hpss(y):
    '''Decompose an audio time series into harmonic and percussive components.

    This function automates the STFT->HPSS->ISTFT pipeline, and ensures that
    the output waveforms have equal length to the input waveform ``y``.

    :usage:
        >>> # Load a waveform
        >>> y, sr = librosa.load(librosa.util.example_audio_file())
        >>> y_harmonic, y_percussive = librosa.effects.hpss(y)

    :parameters:
      - y : np.ndarray [shape=(n,)]
          audio time series

    :returns:
      - y_harmonic : np.ndarray [shape=(n,)]
          audio time series of the harmonic elements

      - y_percussive : np.ndarray [shape=(n,)]
          audio time series of the percussive elements

    .. seealso:: :func:`librosa.decompose.hpss`
    '''

    # Compute the STFT matrix
    stft = librosa.core.stft(y)

    # Decompose into harmonic and percussives
    stft_harm, stft_perc = librosa.decompose.hpss(stft)

    # Invert the STFTs.  Adjust length to match the input.
    y_harm = librosa.util.fix_length(librosa.istft(stft_harm, dtype=y.dtype),
                                     len(y))
    y_perc = librosa.util.fix_length(librosa.istft(stft_perc, dtype=y.dtype),
                                     len(y))

    return y_harm, y_perc


@cache
def harmonic(y):
    '''Extract harmonic elements from an audio time-series.

    :usage:
        >>> # Load a waveform
        >>> y, sr = librosa.load(librosa.util.example_audio_file())
        >>> y_harmonic = librosa.effects.harmonic(y)

    :parameters:
      - y : np.ndarray [shape=(n,)]
          audio time series

    :returns:
      - y_harmonic : np.ndarray [shape=(n,)]
          audio time series of just the harmonic portion

    .. seealso:: :func:`librosa.decompose.hpss`, :func:`librosa.effects.hpss`,
        :func:`librosa.effects.percussive`
    '''

    # Compute the STFT matrix
    stft = librosa.core.stft(y)

    # Remove percussives
    stft_harm = librosa.decompose.hpss(stft)[0]

    # Invert the STFTs
    y_harm = librosa.util.fix_length(librosa.istft(stft_harm, dtype=y.dtype),
                                     len(y))

    return y_harm


@cache
def percussive(y):
    '''Extract percussive elements from an audio time-series.

    :usage:
        >>> # Load a waveform
        >>> y, sr = librosa.load(librosa.util.example_audio_file())
        >>> y_percussive = librosa.effects.percussive(y)

    :parameters:
      - y : np.ndarray [shape=(n,)]
          audio time series

    :returns:
      - y_percussive : np.ndarray [shape=(n,)]
          audio time series of just the percussive portion

    .. seealso:: :func:`librosa.decompose.hpss`, :func:`librosa.effects.hpss`,
        :func:`librosa.effects.percussive`
    '''

    # Compute the STFT matrix
    stft = librosa.core.stft(y)

    # Remove harmonics
    stft_perc = librosa.decompose.hpss(stft)[1]

    # Invert the STFT
    y_perc = librosa.util.fix_length(librosa.istft(stft_perc, dtype=y.dtype),
                                     len(y))

    return y_perc


@cache
def time_stretch(y, rate):
    '''Time-stretch an audio series by a fixed rate.

    :usage:
        >>> # Load a waveform
        >>> y, sr = librosa.load(librosa.util.example_audio_file())
        >>> # Compress to be twice as fast
        >>> y_fast = librosa.effects.time_stretch(y, 2.0)
        >>> # Or half the original speed
        >>> y_slow = librosa.effects.time_stretch(y, 0.5)

    :parameters:
      - y : np.ndarray [shape=(n,)]
          audio time series

      - rate : float > 0 [scalar]
          Stretch factor.  If ``rate > 1``, then the signal is sped up.
          If ``rate < 1``, then the signal is slowed down.

    :returns:
      - y_stretch : np.ndarray [shape=(rate * n,)]
          audio time series stretched by the specified rate

    .. seealso:: :func:`librosa.core.phase_vocoder`,
      :func:`librosa.effects.pitch_shift`
    '''

    # Construct the stft
    stft = librosa.stft(y)

    # Stretch by phase vocoding
    stft_stretch = librosa.phase_vocoder(stft, rate)

    # Invert the stft
    y_stretch = librosa.istft(stft_stretch, dtype=y.dtype)

    return y_stretch


@cache
def pitch_shift(y, sr, n_steps, bins_per_octave=12):
    '''Pitch-shift the waveform by ``n_steps`` half-steps.

    :usage:
        >>> # Load a waveform
        >>> y, sr = librosa.load(librosa.util.example_audio_file())
        >>> # Shift up by a major third (four half-steps)
        >>> y_third = librosa.effects.pitch_shift(y, sr, n_steps=4)
        >>> # Shift down by a tritone (six half-steps)
        >>> y_tritone = librosa.effects.pitch_shift(y, sr, n_steps=-6)
        >>> # Shift up by 3 quarter-tones
        >>> y_three_qt = librosa.effects.pitch_shift(y, sr, n_steps=3,
                                                     bins_per_octave=24)


    :parameters:
      - y : np.ndarray [shape=(n,)]
          audio time-series

      - sr : int > 0 [scalar]
          audio sampling rate of ``y``

      - n_steps : float [scalar]
          how many (fractional) half-steps to shift ``y``

      - bins_per_octave : float > 0 [scalar]
          how many steps per octave

    :returns:
      - y_shift : np.ndarray [shape=(n,)]
          The pitch-shifted audio time-series

    .. seealso:: :func:`librosa.core.phase_vocoder`,
      :func:`librosa.effects.time_stretch`
    '''

    rate = 2.0 ** (-float(n_steps) / bins_per_octave)

    # Stretch in time, then resample
    y_shift = librosa.resample(time_stretch(y, rate),
                               float(sr) / rate,
                               sr)

    # Crop to the same dimension as the input
    return librosa.util.fix_length(y_shift, len(y))


@cache
def remix(y, intervals, align_zeros=True):
    '''Remix an audio signal by re-ordering time intervals.

    :usage:
        >>> # Load in the example track and reverse the beats
        >>> y, sr = librosa.load(librosa.util.example_audio_file())
        >>> # Compute beats
        >>> _, beat_frames = librosa.beat.beat_track(y=y, sr=sr,
                                                     hop_length=512)
        >>> # Convert from frames to sample indices
        >>> beat_samples = librosa.frames_to_samples(beat_frames)
        >>> # Generate intervals from consecutive events
        >>> intervals = librosa.util.frame(beat_samples, frame_length=2,
                                           hop_length=1).T
        >>> # Reverse the beat intervals
        >>> y_out = librosa.effects.remix(y, intervals[::-1])

    :parameters:
        - y : np.ndarray [shape=(t,) or (2, t)]
            Audio time series

        - intervals : iterable of tuples (start, end)
            An iterable (list-like or generator) where the `i`th item
            ``intervals[i]`` indicates the start and end (in samples)
            of a slice of ``y``.

        - align_zeros : boolean
            If `True`, interval boundaries are mapped to the closest
            zero-crossing in ``y``.  If ``y`` is stereo, zero-croessings
            are computed after converting to mono.

    :returns:
        - y_remix : np.ndarray [shape=(d,) or (2, d)]
            ``y`` remixed in the order specified by ``intervals``
    '''

    # Validate the audio buffer
    librosa.util.valid_audio(y, mono=False)

    y_out = []

    if align_zeros:
        y_mono = librosa.core.to_mono(y)
        zeros = np.nonzero(librosa.core.zero_crossings(y_mono))[-1]

    clip = [Ellipsis] * y.ndim

    for interval in intervals:

        if align_zeros:
            interval = zeros[librosa.util.match_events(interval, zeros)]

        clip[-1] = slice(interval[0], interval[1])

        y_out.append(y[clip])

    return np.concatenate(y_out, axis=-1)
